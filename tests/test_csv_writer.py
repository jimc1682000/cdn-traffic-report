"""Tests for scripts.csv_writer — weekly spreadsheet row flattening + CSV append."""

import csv
from pathlib import Path

from scripts.csv_writer import (
    COL_EDGE,
    COL_HOME,
    COL_ID,
    COL_LIVE,
    COL_ORIGIN,
    COL_PERIOD,
    COL_SG,
    COL_TRAILER,
    COL_TVA,
    COL_TW,
    COL_V1,
    COL_V3,
    COL_YEAR,
    GEO_COLUMNS,
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

    assert row[COL_YEAR] == 2026
    assert row[COL_PERIOD] == '05/03 - 05/09'
    assert row[COL_EDGE] == 13.45
    assert row[COL_ORIGIN] == 5.67
    assert row[COL_ID] == 9.87
    assert row[COL_TW] == 2.10
    assert row[COL_SG] == 0.03
    assert row[COL_V1] == 0
    assert row[COL_V3] == 11.23
    assert row[COL_TRAILER] == 3.40
    assert row[COL_LIVE] == 0  # 0.0 -> 0 (integral float collapsed)
    assert row[COL_TVA] == 4.10
    assert row[COL_HOME] == 10.50


def test_geo_columns_blank_when_geo_data_absent():
    """No geography report at all -> ID/TW/SG blank, not 0."""
    results = [_result('summary', {'edge': 100.0, 'origin': 50.0})]
    row = flatten_results(results)

    assert row[COL_EDGE] == 100
    assert row[COL_ORIGIN] == 50
    for col in GEO_COLUMNS:
        assert row[col] == '', f'{col} should be blank when geo absent'
    # Non-geo missing types remain 0 (legacy v1, genuine zeros).
    for col in (COL_V1, COL_V3, COL_TRAILER, COL_LIVE, COL_TVA, COL_HOME):
        assert row[col] == 0, f'{col} should default to 0'


def test_geo_columns_blank_when_geo_report_present_but_empty():
    """Geography report ran but extracted nothing (data lag) -> blank cells."""
    results = [
        _result('summary', {'edge': 181.11, 'origin': 62.9}),
        _result('geography', geography={}),
    ]
    row = flatten_results(results)
    for col in GEO_COLUMNS:
        assert row[col] == '', f'{col} should be blank for empty geo report'


def test_small_decimal_geo_value_preserved():
    """SG = 0.01 must survive the number formatter (not collapsed to 0)."""
    results = [_result('geography', geography={'ID': 151.28, 'TW': 25.47, 'SG': 0.01})]
    row = flatten_results(results)
    assert row[COL_SG] == 0.01
    assert row[COL_ID] == 151.28


def test_integral_float_collapsed_but_decimals_kept():
    results = [_result('summary', {'edge': 5.0, 'origin': 66.56})]
    row = flatten_results(results)
    assert row[COL_EDGE] == 5
    assert isinstance(row[COL_EDGE], int)
    assert row[COL_ORIGIN] == 66.56


def test_flatten_unknown_type_ignored():
    results = [
        _result('summary', {'edge': 10.0}),
        _result('mystery', {'edge': 999.0}),
    ]
    row = flatten_results(results)
    assert row[COL_EDGE] == 10
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


def test_append_blank_geo_cells_written_empty(tmp_path: Path):
    csv_path = tmp_path / 'weekly.csv'
    results = [_result('summary', {'edge': 181.11, 'origin': 62.9})]
    append_weekly_row(results, csv_path)

    with open(csv_path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    assert rows[0][COL_ID] == ''
    assert rows[0][COL_TW] == ''
    assert rows[0][COL_SG] == ''
    assert rows[0][COL_LIVE] == '0'


def test_append_creates_parent_dir(tmp_path: Path):
    csv_path = tmp_path / 'nested' / 'dir' / 'weekly.csv'
    results = [_result('summary', {'edge': 1.0})]

    append_weekly_row(results, csv_path)

    assert csv_path.exists()


def test_week_label_zero_pads_single_digit_days():
    results = [_result('summary', {'edge': 1.0}, start='2026-01-05', end='2026-01-11')]
    row = flatten_results(results)
    assert row[COL_PERIOD] == '01/05 - 01/11'


def test_empty_results_returns_zero_row():
    row = flatten_results([])
    assert row[COL_YEAR] == 0
    assert row[COL_PERIOD] == 0
    for col in GEO_COLUMNS:
        assert row[col] == ''
    for col in (COL_EDGE, COL_ORIGIN, COL_V1, COL_V3, COL_TRAILER, COL_LIVE, COL_TVA, COL_HOME):
        assert row[col] == 0
