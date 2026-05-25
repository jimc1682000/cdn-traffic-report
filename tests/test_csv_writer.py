"""Tests for scripts.csv_writer — weekly spreadsheet row flattening + CSV append."""

import csv
from pathlib import Path

from scripts.csv_writer import (
    SPREADSHEET_COLUMNS,
    append_weekly_row,
    flatten_results,
)


def _result(
    rtype: str,
    traffic: dict | None = None,
    geography: dict | None = None,
    start: str = '2026-05-03',
    end: str = '2026-05-09',
) -> dict:
    out = {
        'date_range': {'start': start, 'end': end},
        'type': rtype,
        'label': rtype,
        'traffic': traffic or {},
        'unit': 'TB',
    }
    if geography is not None:
        out['geography'] = geography
    return out


def test_flatten_all_known_types():
    results = [
        _result('summary', {'edge': 13.45, 'origin': 5.67}),
        _result('v3', {'edge': 11.23}),
        _result('trailer', {'edge': 3.40}),
        _result('tva', {'edge': 4.10}),
        _result('live', {'edge': 0.0}),
        _result('home', {'edge': 10.50}),
        _result('geography', geography={'ID': 9.87, 'TW': 2.10, 'SG': 0.03}),
    ]
    row = flatten_results(results)

    assert row['年度'] == 2026
    assert row['週期'] == '05/03 - 05/09'
    assert row['edge流量TB'] == 13.45
    assert row['origin流量TB'] == 5.67
    assert row['ID'] == 9.87
    assert row['TW'] == 2.10
    assert row['SG'] == 0.03
    assert row['v1流量TB'] == 0
    assert row['v3流量TB'] == 11.23
    assert row['Trailer/EPK'] == 3.40
    assert row['live流量GB'] == 0.0
    assert row['TVA流量GB'] == 4.10
    assert row['home流量GB'] == 10.50


def test_flatten_missing_types_fill_zero():
    results = [_result('summary', {'edge': 100.0, 'origin': 50.0})]
    row = flatten_results(results)

    assert row['edge流量TB'] == 100.0
    assert row['origin流量TB'] == 50.0
    for col in ('ID', 'TW', 'SG', 'v3流量TB', 'Trailer/EPK', 'live流量GB', 'TVA流量GB', 'home流量GB'):
        assert row[col] == 0, f'{col} should default to 0'


def test_flatten_unknown_type_ignored():
    results = [
        _result('summary', {'edge': 10.0}),
        _result('mystery', {'edge': 999.0}),
    ]
    row = flatten_results(results)
    assert row['edge流量TB'] == 10.0
    assert 999.0 not in row.values()


def test_append_writes_header_once(tmp_path: Path):
    csv_path = tmp_path / 'weekly.csv'
    results = [_result('summary', {'edge': 1.0, 'origin': 0.5})]

    append_weekly_row(results, csv_path)
    append_weekly_row(results, csv_path)

    with open(csv_path, encoding='utf-8') as f:
        rows = list(csv.reader(f))

    assert rows[0] == SPREADSHEET_COLUMNS
    assert len(rows) == 3  # header + 2 data rows
    assert rows[1] == rows[2]


def test_append_creates_parent_dir(tmp_path: Path):
    csv_path = tmp_path / 'nested' / 'dir' / 'weekly.csv'
    results = [_result('summary', {'edge': 1.0})]

    append_weekly_row(results, csv_path)

    assert csv_path.exists()


def test_week_label_zero_pads_single_digit_days():
    results = [_result('summary', {'edge': 1.0}, start='2026-01-05', end='2026-01-11')]
    row = flatten_results(results)
    assert row['週期'] == '01/05 - 01/11'


def test_empty_results_returns_zero_row():
    row = flatten_results([])
    assert row['年度'] == 0
    assert row['週期'] == 0
    assert all(row[col] == 0 for col in SPREADSHEET_COLUMNS)
