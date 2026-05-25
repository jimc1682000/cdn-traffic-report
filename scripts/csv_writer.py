"""Flatten per-report results into one weekly CSV row matching the
manual tracking spreadsheet.

Spreadsheet columns (left to right):
    年度 | 週期 | edge流量TB | origin流量TB | ID | TW | SG |
    v1流量TB | v3流量TB | Trailer/EPK | live流量GB | TVA流量GB | home流量GB

Mapping rules:
- 年度          : YYYY from start_date
- 週期          : "MM/DD - MM/DD" from start/end_date
- edge流量TB    : summary.traffic.edge      (TB)
- origin流量TB  : summary.traffic.origin    (TB)
- ID/TW/SG      : geography.geography[...]  (TB, matches spreadsheet semantics)
- v1流量TB      : fixed 0 (legacy, no CP code yet)
- v3流量TB      : v3.traffic.edge           (TB)
- Trailer/EPK   : trailer.traffic.edge      (configured unit)
- live流量GB    : live.traffic.edge         (GB)
- TVA流量GB     : tva.traffic.edge          (GB)
- home流量GB    : home.traffic.edge         (GB)
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

SPREADSHEET_COLUMNS = [
    '年度',
    '週期',
    'edge流量TB',
    'origin流量TB',
    'ID',
    'TW',
    'SG',
    'v1流量TB',
    'v3流量TB',
    'Trailer/EPK',
    'live流量GB',
    'TVA流量GB',
    'home流量GB',
]

_EDGE_BY_TYPE = {
    'summary': ('edge流量TB', 'origin流量TB'),
    'v3': ('v3流量TB', None),
    'trailer': ('Trailer/EPK', None),
    'tva': ('TVA流量GB', None),
    'live': ('live流量GB', None),
    'home': ('home流量GB', None),
}


def _parse_date(s: str) -> date:
    return datetime.strptime(s, '%Y-%m-%d').date()


def _week_label(start: str, end: str) -> str:
    s, e = _parse_date(start), _parse_date(end)
    return f'{s.month:02d}/{s.day:02d} - {e.month:02d}/{e.day:02d}'


def flatten_results(results: list[dict]) -> dict:
    """Build a single row dict keyed by SPREADSHEET_COLUMNS from per-report results."""
    row = dict.fromkeys(SPREADSHEET_COLUMNS, 0)

    start_date = end_date = None
    for r in results:
        dr = r.get('date_range') or {}
        if dr.get('start'):
            start_date = dr['start']
        if dr.get('end'):
            end_date = dr['end']

    if start_date:
        row['年度'] = _parse_date(start_date).year
    if start_date and end_date:
        row['週期'] = _week_label(start_date, end_date)

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
            for country in ('ID', 'TW', 'SG'):
                if country in geo:
                    row[country] = geo[country]

    return row


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
