"""Flatten per-report results into one weekly CSV row matching the
manual tracking spreadsheet.

Spreadsheet columns (left to right, header text matches the sheet for paste-in):
    年度 | CDN 每周流量TB | edge流量 | origin流量 | ID | TW | SG |
    v1流量 TB | v3流量 TB | Trailer/EPK | live流量GB | TVA流量GB | home流量GB

Mapping rules:
- 年度           : YYYY from start_date
- CDN 每周流量TB : "MM/DD - MM/DD" period from start/end_date
- edge流量       : summary.traffic.edge      (TB)
- origin流量     : summary.traffic.origin    (TB)
- ID/TW/SG       : geography.geography[...]  (TB) — blank when geo data absent
- v1流量 TB      : fixed 0 (legacy, no CP code yet)
- v3流量 TB      : v3.traffic.edge           (TB)
- Trailer/EPK    : trailer.traffic.edge      (configured unit)
- live流量GB     : live.traffic.edge         (GB)
- TVA流量GB      : tva.traffic.edge          (GB)
- home流量GB     : home.traffic.edge         (GB)

Number formatting: integral floats are written without the trailing ".0"
(e.g. 0.0 -> 0), while genuine decimals are preserved (e.g. 0.01 stays 0.01).
"""

from __future__ import annotations

import csv
from datetime import date, datetime
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

    0.0 -> 0, 5.0 -> 5, but 0.01 -> 0.01 and 181.11 -> 181.11. Non-numeric
    values (e.g. blank geo cells, the period label) pass through unchanged.
    """
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def flatten_results(results: list[dict]) -> dict:
    """Build a single row dict keyed by SPREADSHEET_COLUMNS from per-report results."""
    row = dict.fromkeys(SPREADSHEET_COLUMNS, 0)
    # Geo columns stay blank unless real country data shows up.
    for col in GEO_COLUMNS:
        row[col] = ''

    start_date = end_date = None
    for r in results:
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

        if rtype == 'geography':
            geo = r.get('geography') or {}
            for country in GEO_COLUMNS:
                if country in geo:
                    row[country] = geo[country]

    return {k: _fmt_num(v) for k, v in row.items()}


def append_weekly_row(results: list[dict], csv_path: Path) -> Path:
    """Append a flattened row to weekly.csv. Writes header on first creation."""
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    row = flatten_results(results)
    write_header = not csv_path.exists()

    with open(csv_path, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=SPREADSHEET_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    return csv_path
