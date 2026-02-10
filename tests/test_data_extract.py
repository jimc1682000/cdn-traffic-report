"""Tests for data_extract module."""

import pytest

from scripts.data_extract import build_report_output, bytes_to_tb, convert_unit, parse_traffic_value


@pytest.mark.parametrize(
    ('text', 'expected_value', 'expected_unit'),
    [
        ('170.82 Terabytes', 170.82, 'TB'),
        ('43.89 Gigabytes', 43.89, 'GB'),
        ('64.14 %', 64.14, '%'),
        ('1,234.56 Terabytes', 1234.56, 'TB'),
    ],
)
def test_parse_traffic_value(text, expected_value, expected_unit):
    value, unit = parse_traffic_value(text)
    assert value == expected_value
    assert unit == expected_unit


@pytest.mark.parametrize(
    ('text',),
    [
        ('invalid',),
        ('',),
        ('no_space_unit',),
    ],
)
def test_parse_traffic_value_invalid(text):
    with pytest.raises(ValueError, match='Cannot parse traffic value'):
        parse_traffic_value(text)


@pytest.mark.parametrize(
    ('byte_count', 'expected'),
    [
        (168776644787204, 168.78),
        (31398058511, 0.03),
        (0, 0.0),
        (1, 0.0),
    ],
)
def test_bytes_to_tb(byte_count, expected):
    assert bytes_to_tb(byte_count) == expected


@pytest.mark.parametrize(
    ('value', 'from_unit', 'to_unit', 'expected'),
    [
        (100.0, 'TB', 'TB', 100.0),
        (1.0, 'TB', 'GB', 1000.0),
        (1000.0, 'GB', 'TB', 1.0),
        (1.0, 'TB', 'MB', 1000000.0),
    ],
)
def test_convert_unit(value, from_unit, to_unit, expected):
    assert convert_unit(value, from_unit, to_unit) == expected


def test_convert_unit_invalid_unit():
    with pytest.raises(KeyError):
        convert_unit(1.0, 'TB', '%')


def test_build_report_output_structure():
    output = build_report_output(
        report_type='type_a',
        label='Test Report',
        start_date='2026-01-25',
        end_date='2026-01-31',
        traffic={'edge': 170.82, 'origin': 61.25},
        unit='TB',
    )
    assert output['type'] == 'type_a'
    assert output['label'] == 'Test Report'
    assert output['date_range']['start'] == '2026-01-25'
    assert output['date_range']['end'] == '2026-01-31'
    assert output['traffic']['edge'] == 170.82
    assert output['unit'] == 'TB'
    assert 'geography' not in output


def test_build_report_output_with_geography():
    output = build_report_output(
        report_type='type_b',
        label='Test All',
        start_date='2026-01-25',
        end_date='2026-01-31',
        traffic={'edge': 197.9},
        unit='TB',
        geography={'US': 100.0, 'JP': 50.0, 'KR': 10.0},
    )
    assert 'geography' in output
    assert output['geography']['US'] == 100.0
    assert output['geography']['JP'] == 50.0
    assert output['geography']['KR'] == 10.0


def test_build_report_output_geography_type():
    """Geography as independent report type: traffic is empty, geography is present."""
    output = build_report_output(
        report_type='geography',
        label='Geo Report',
        start_date='2026-01-25',
        end_date='2026-01-31',
        traffic={},
        unit='TB',
        geography={'US': 100.0, 'JP': 50.0, 'KR': 10.0},
    )
    assert output['type'] == 'geography'
    assert output['label'] == 'Geo Report'
    assert output['traffic'] == {}
    assert output['unit'] == 'TB'
    assert 'geography' in output
    assert output['geography']['US'] == 100.0
