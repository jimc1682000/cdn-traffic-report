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
    DOC_COLUMNS,
    GEO_COLUMNS,
    SPREADSHEET_COLUMNS,
    append_weekly_row,
    doc_row,
    flatten_results,
    format_paste_blocks,
    livetv_rows,
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
        _result('geography', geography={'ID': 9.87, 'TW': 2.10, 'SG': 0.05}),
        {
            'date_range': {'start': '2026-05-03', 'end': '2026-05-09'},
            'type': 'cloudfront',
            'daily_bytes': {'05/03': 100, '05/04': 250},
        },
    ]
    row = flatten_results(results)

    assert row[COL_YEAR] == 2026
    assert row[COL_PERIOD] == '05/03 - 05/09'
    assert row[COL_EDGE] == 13.45
    assert row[COL_ORIGIN] == 5.67
    assert row[COL_ID] == 9.87
    assert row[COL_TW] == 2.10
    assert row[COL_SG] == 0.05
    assert row[COL_V1] == 0
    assert row[COL_V3] == 11.23
    assert row[COL_TRAILER] == 3.40
    assert row[COL_LIVE] == 0  # 0.0 -> 0 (integral float collapsed)
    assert row[COL_TVA] == 4.10
    assert row[COL_HOME] == 10.50
    # CloudFront belongs to the LiveTV tabs, not the weekly row (sheet col N is BI).
    assert list(row) == SPREADSHEET_COLUMNS
    assert len(row) == 13


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
        _result('summary', {'edge': 123.45, 'origin': 45.6}),
        _result('geography', geography={}),
    ]
    row = flatten_results(results)
    for col in GEO_COLUMNS:
        assert row[col] == '', f'{col} should be blank for empty geo report'


def test_small_decimal_geo_value_preserved():
    """SG = 0.01 must survive the number formatter (not collapsed to 0)."""
    results = [_result('geography', geography={'ID': 98.76, 'TW': 21.09, 'SG': 0.01})]
    row = flatten_results(results)
    assert row[COL_SG] == 0.01
    assert row[COL_ID] == 98.76


def test_integral_float_collapsed_but_decimals_kept():
    results = [_result('summary', {'edge': 5.0, 'origin': 22.22})]
    row = flatten_results(results)
    assert row[COL_EDGE] == 5
    assert isinstance(row[COL_EDGE], int)
    assert row[COL_ORIGIN] == 22.22


def test_geo_blank_when_akamai_window_incomplete():
    """Akamai geo data ends before the week does -> blank, not partial numbers."""
    geo = _result('geography', geography={'ID': 6.21, 'TW': 2.33, 'SG': 0.01})
    geo['data_complete'] = False
    row = flatten_results([_result('summary', {'edge': 13.45}), geo])
    for col in GEO_COLUMNS:
        assert row[col] == '', f'{col} should be blank for incomplete geo window'


def test_geo_kept_when_completeness_unknown():
    """No data_complete flag (marker not found on page) -> keep the values."""
    row = flatten_results([_result('geography', geography={'ID': 9.87, 'TW': 2.15, 'SG': 0.05})])
    assert row[COL_ID] == 9.87


def _cloudfront(start: str, end: str, daily: dict) -> dict:
    return {'date_range': {'start': start, 'end': end}, 'type': 'cloudfront', 'daily_bytes': daily}


def test_cloudfront_window_does_not_change_period():
    """CloudFront runs on the shifted LiveTV window; the period stays the Akamai week."""
    results = [
        _result('summary', {'edge': 13.45}, start='2026-10-18', end='2026-10-24'),
        _cloudfront('2026-10-19', '2026-10-25', {'10/19': 1}),
    ]
    row = flatten_results(results)
    assert row[COL_PERIOD] == '10/18 - 10/24'


def test_doc_row_order_and_blank_geo():
    results = [
        _result('summary', {'edge': 13.45, 'origin': 5.67}),
        _result('v3', {'edge': 11.23}),
        _result('trailer', {'edge': 3.41}),
        _result('tva', {'edge': 4.12}),
        _result('live', {'edge': 0.0}),
        _result('home', {'edge': 10.52}),
    ]
    assert [name for name, _ in DOC_COLUMNS][-1] == 'Home流量GB'
    assert doc_row(flatten_results(results)) == ['05/03 - 05/09', 13.45, '', '', '', 11.23, 3.41, 0, 4.12, 10.52]


def test_livetv_rows_carry_year_across_new_year():
    cf = _cloudfront('2026-12-30', '2027-01-02', {'12/30': 1, '12/31': 2, '01/01': 3, '01/02': 4})
    assert livetv_rows([cf]) == [
        ('2026-12-30', 1),
        ('2026-12-31', 2),
        ('2027-01-01', 3),
        ('2027-01-02', 4),
    ]


def test_livetv_rows_skip_missing_days_and_other_types():
    cf = _cloudfront('2026-10-19', '2026-10-21', {'10/19': 10, '10/21': 30})
    assert livetv_rows([_result('summary', {'edge': 1.0}), cf]) == [('2026-10-19', 10), ('2026-10-21', 30)]


def test_format_paste_blocks_tab_separated():
    results = [
        _result('summary', {'edge': 13.45, 'origin': 5.67}, start='2026-10-18', end='2026-10-24'),
        _cloudfront('2026-10-19', '2026-10-20', {'10/19': 123456789012, '10/20': 234567890123}),
    ]
    lines = format_paste_blocks(results).splitlines()
    assert '2026\t10/18 - 10/24\t13.45\t5.67\t\t\t\t0' in lines[2]
    assert lines[6].startswith('10/18 - 10/24\t13.45\t\t\t\t')
    assert lines[-2:] == ['2026-10-19\t123456789012', '2026-10-20\t234567890123']


def test_format_paste_blocks_without_cloudfront_has_no_livetv_block():
    text = format_paste_blocks([_result('summary', {'edge': 1.0})])
    assert 'LiveTV' not in text


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
    results = [_result('summary', {'edge': 123.45, 'origin': 45.6})]
    append_weekly_row(results, csv_path)

    with open(csv_path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    assert rows[0][COL_ID] == ''
    assert rows[0][COL_TW] == ''
    assert rows[0][COL_SG] == ''
    assert rows[0][COL_LIVE] == '0'


_LEGACY_HEADER = [
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


def test_append_migrates_legacy_header(tmp_path: Path):
    """Existing weekly.csv with old column names gets its header rewritten."""
    csv_path = tmp_path / 'weekly.csv'
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(_LEGACY_HEADER)
        w.writerow(
            [
                '2026',
                '05/24 - 05/30',
                '111.11',
                '22.22',
                '77.77',
                '33.33',
                '0.01',
                '0',
                '44.44',
                '88.88',
                '0',
                '55.55',
                '66.66',
            ]
        )

    append_weekly_row([_result('summary', {'edge': 100.0})], csv_path)

    with open(csv_path, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))

    assert rows[0] == SPREADSHEET_COLUMNS  # header migrated to new names
    # Legacy data row preserved (column order unchanged).
    assert rows[1][4] == '77.77'
    assert len(rows) == 3  # header + legacy row + newly appended row


def test_append_drops_retired_livetv_header_column(tmp_path: Path):
    """A header written while LIVETV流量 was column 14 is rewritten to the 13 sheet columns."""
    csv_path = tmp_path / 'weekly.csv'
    old_row = ['2026', '01/04 - 01/10', *['1'] * 11, '123456789012']
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow([*SPREADSHEET_COLUMNS, 'LIVETV流量'])
        w.writerow(old_row)

    append_weekly_row([_result('summary', {'edge': 1.0})], csv_path)

    with open(csv_path, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    assert rows[0] == SPREADSHEET_COLUMNS
    # Existing data rows lose the retired column too, so they paste into A:M only.
    assert rows[1] == old_row[:13]
    assert [len(r) for r in rows] == [13, 13, 13]


def test_append_trims_rows_left_wide_by_an_earlier_header_only_migration(tmp_path: Path):
    """Header already 13 columns but an old data row still has the 14th column."""
    csv_path = tmp_path / 'weekly.csv'
    old_row = ['2026', '01/04 - 01/10', *['1'] * 11, '123456789012']
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(SPREADSHEET_COLUMNS)
        w.writerow(old_row)

    append_weekly_row([_result('summary', {'edge': 1.0})], csv_path)

    with open(csv_path, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    assert [len(r) for r in rows] == [13, 13, 13]
    assert rows[1] == old_row[:13]


def test_append_to_empty_existing_file(tmp_path: Path):
    """Existing but empty file: migration no-ops, append still writes a row."""
    csv_path = tmp_path / 'weekly.csv'
    csv_path.touch()  # exists, zero rows

    append_weekly_row([_result('summary', {'edge': 1.0})], csv_path)

    with open(csv_path, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    # write_header was False (file existed) so no header is written; just the row.
    assert len(rows) == 1
    assert rows[0][0] == '2026'


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
