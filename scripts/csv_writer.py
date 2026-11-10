"""Flatten per-report results into one weekly CSV row matching the
manual tracking spreadsheet, plus the paste-in blocks for the weekly Doc.

Spreadsheet columns (sheet `weekly` A:M, header text matches the sheet for paste-in):
    年度 | CDN 每周流量TB | edge流量 | origin流量 | ID | TW | SG |
    v1流量 TB | v3流量 TB | Trailer/EPK | live流量GB | TVA流量GB | home流量GB

Column N onwards in the sheet belongs to BI, so the row stops at M.

Mapping rules:
- 年度           : YYYY from start_date
- CDN 每周流量TB : "MM/DD - MM/DD" period from start/end_date
- edge流量       : summary.traffic.edge      (TB)
- origin流量     : summary.traffic.origin    (TB)
- ID/TW/SG       : geography.geography[...]  (TB) — blank when geo data absent
                   or Akamai reports the window as incomplete (data_complete False)
- v1流量 TB      : fixed 0 (legacy, no CP code yet)
- v3流量 TB      : v3.traffic.edge           (TB)
- Trailer/EPK    : trailer.traffic.edge      (configured unit)
- live流量GB     : live.traffic.edge         (GB) — Akamai CP, not CloudFront
- TVA流量GB      : tva.traffic.edge          (GB)
- home流量GB     : home.traffic.edge         (GB)

CloudFront is not part of the weekly row: LiveTV goes into the sheet's `LiveTV`
and `LiveTV monthy` tabs as one `date, raw bytes` row per UTC+8 day.

Number formatting: integral floats are written without the trailing ".0"
(e.g. 0.0 -> 0), while genuine decimals are preserved (e.g. 0.01 stays 0.01).
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

# Column header constants — keep in sync with the tracking spreadsheet.
COL_YEAR = '年度'
COL_PERIOD = 'CDN 每周流量TB'
COL_EDGE = 'edge流量'
COL_ORIGIN = 'origin流量'
COL_ID = 'ID'
COL_TW = 'TW'
COL_SG = 'SG'
COL_V1 = 'v1流量 TB'
COL_V3 = 'v3流量 TB'
COL_TRAILER = 'Trailer/EPK'
COL_LIVE = 'live流量GB'
COL_TVA = 'TVA流量GB'
COL_HOME = 'home流量GB'

SPREADSHEET_COLUMNS = [
    COL_YEAR,
    COL_PERIOD,
    COL_EDGE,
    COL_ORIGIN,
    COL_ID,
    COL_TW,
    COL_SG,
    COL_V1,
    COL_V3,
    COL_TRAILER,
    COL_LIVE,
    COL_TVA,
    COL_HOME,
]

# The weekly Doc table drops 年度 / origin / v1 and capitalises Home.
DOC_COLUMNS = [
    (COL_PERIOD, COL_PERIOD),
    (COL_EDGE, COL_EDGE),
    (COL_ID, COL_ID),
    (COL_TW, COL_TW),
    (COL_SG, COL_SG),
    (COL_V3, COL_V3),
    (COL_TRAILER, COL_TRAILER),
    (COL_LIVE, COL_LIVE),
    (COL_TVA, COL_TVA),
    ('Home流量GB', COL_HOME),
]

# Geography columns are left blank (not 0) when no geo data is available.
GEO_COLUMNS = (COL_ID, COL_TW, COL_SG)

_EDGE_BY_TYPE = {
    'summary': (COL_EDGE, COL_ORIGIN),
    'v3': (COL_V3, None),
    'trailer': (COL_TRAILER, None),
    'tva': (COL_TVA, None),
    'live': (COL_LIVE, None),
    'home': (COL_HOME, None),
}


def _parse_date(s: str) -> date:
    return datetime.strptime(s, '%Y-%m-%d').date()


def _week_label(start: str, end: str) -> str:
    s, e = _parse_date(start), _parse_date(end)
    return f'{s.month:02d}/{s.day:02d} - {e.month:02d}/{e.day:02d}'


def _fmt_num(v):
    """Drop the trailing ".0" on integral floats; keep real decimals intact.

    0.0 -> 0, 5.0 -> 5, but 0.01 -> 0.01 and 123.45 -> 123.45. Non-numeric
    values (e.g. blank geo cells, the period label) pass through unchanged.
    """
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def flatten_results(results: list[dict]) -> dict:
    """Build a single row dict keyed by SPREADSHEET_COLUMNS from per-report results."""
    row = dict.fromkeys(SPREADSHEET_COLUMNS, 0)
    # Geo stays blank unless that report actually ran.
    for col in GEO_COLUMNS:
        row[col] = ''

    start_date = end_date = None
    for r in results:
        # CloudFront uses its own (shifted) LiveTV window, not the Akamai week.
        if r.get('type') == 'cloudfront':
            continue
        dr = r.get('date_range') or {}
        if dr.get('start'):
            start_date = dr['start']
        if dr.get('end'):
            end_date = dr['end']

    if start_date:
        row[COL_YEAR] = _parse_date(start_date).year
    if start_date and end_date:
        row[COL_PERIOD] = _week_label(start_date, end_date)

    for r in results:
        rtype = r.get('type')
        traffic = r.get('traffic') or {}

        if rtype in _EDGE_BY_TYPE:
            edge_col, origin_col = _EDGE_BY_TYPE[rtype]
            if 'edge' in traffic:
                row[edge_col] = traffic['edge']
            if origin_col and 'origin' in traffic:
                row[origin_col] = traffic['origin']

        # Partial geo numbers look plausible but undercount, so leave them blank.
        if rtype == 'geography' and r.get('data_complete') is not False:
            geo = r.get('geography') or {}
            for country in GEO_COLUMNS:
                if country in geo:
                    row[country] = geo[country]

    return {k: _fmt_num(v) for k, v in row.items()}


def doc_row(row: dict) -> list:
    """Reorder a flattened row into the weekly Doc table's columns."""
    return [row[col] for _, col in DOC_COLUMNS]


def livetv_rows(results: list[dict]) -> list[tuple[str, int]]:
    """CloudFront daily bytes as ("YYYY-MM-DD", bytes) rows for the LiveTV tabs.

    daily_bytes is keyed by "MM/DD", so the year comes from the cloudfront
    date_range (walking the range keeps a Dec -> Jan window correct).
    """
    rows = []
    for r in results:
        if r.get('type') != 'cloudfront':
            continue
        daily = r.get('daily_bytes') or {}
        day = _parse_date(r['date_range']['start'])
        end = _parse_date(r['date_range']['end'])
        while day <= end:
            key = f'{day.month:02d}/{day.day:02d}'
            if key in daily:
                rows.append((day.isoformat(), daily[key]))
            day += timedelta(days=1)
    return rows


def format_paste_blocks(results: list[dict]) -> str:
    """Tab-separated blocks to paste into the sheet tabs and the weekly Doc."""
    row = flatten_results(results)

    def tsv(values) -> str:
        return '\t'.join(str(v) for v in values)

    lines = [
        '# Sheet weekly A:M（插在第 2 列）',
        tsv(SPREADSHEET_COLUMNS),
        tsv(row[col] for col in SPREADSHEET_COLUMNS),
        '',
        '# Doc 週表（插在表頭下方）',
        tsv(name for name, _ in DOC_COLUMNS),
        tsv(doc_row(row)),
    ]
    daily = livetv_rows(results)
    if daily:
        lines += ['', '# Sheet LiveTV / LiveTV monthy A:B（C、D 欄是公式，往下延伸）']
        lines += [tsv(d) for d in daily]
    return '\n'.join(lines)


def _migrate_legacy_header(csv_path: Path) -> None:
    """Rewrite the header row in place if it predates the current column names.

    Columns were renamed (e.g. 週期 → 'CDN 每周流量TB', edge流量TB → edge流量) but
    the column *order* is unchanged, so existing data rows stay valid — only the
    header line needs updating. Without this, appending to an existing
    append-only weekly.csv would leave new rows under the legacy header and the
    new SPREADSHEET_COLUMNS names would never appear.
    """
    with open(csv_path, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    if not rows:
        return
    header = rows[0]
    # Only migrate a real header row (both old/new start with 年度). Rewrite when
    # the header differs or a data row still carries the retired trailing
    # LIVETV流量 column, which would otherwise spill into the sheet's BI column.
    width = len(SPREADSHEET_COLUMNS)
    stale = header != SPREADSHEET_COLUMNS or any(len(r) > width for r in rows[1:])
    if header and header[0] == SPREADSHEET_COLUMNS[0] and stale:
        rows = [SPREADSHEET_COLUMNS] + [r[:width] for r in rows[1:]]
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            csv.writer(f).writerows(rows)


def append_weekly_row(results: list[dict], csv_path: Path) -> Path:
    """Append a flattened row to weekly.csv. Writes header on first creation."""
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    row = flatten_results(results)
    write_header = not csv_path.exists()
    if not write_header:
        _migrate_legacy_header(csv_path)

    with open(csv_path, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=SPREADSHEET_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    return csv_path
