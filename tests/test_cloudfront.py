"""Tests for cloudfront module."""

from scripts.cloudfront import aggregate_hourly_to_daily, build_metric_query, convert_dates_to_utc


def test_convert_dates_to_utc():
    """UTC+8 dates should convert correctly to UTC start/end times."""
    start_utc, end_utc = convert_dates_to_utc('2026-01-25', '2026-01-31')
    assert start_utc == '2026-01-24T16:00:00Z'
    assert end_utc == '2026-01-31T16:00:00Z'


def test_convert_dates_to_utc_same_day():
    """Single day range."""
    start_utc, end_utc = convert_dates_to_utc('2026-02-01', '2026-02-01')
    assert start_utc == '2026-01-31T16:00:00Z'
    assert end_utc == '2026-02-01T16:00:00Z'


def test_build_metric_query():
    """Verify CloudWatch metric query JSON structure."""
    queries = build_metric_query('DIST_TEST')
    assert len(queries) == 1
    q = queries[0]
    assert q['Id'] == 'cf_bytes'
    assert q['MetricStat']['Metric']['Namespace'] == 'AWS/CloudFront'
    assert q['MetricStat']['Metric']['MetricName'] == 'BytesDownloaded'
    assert q['MetricStat']['Period'] == 3600
    assert q['MetricStat']['Stat'] == 'Sum'
    dims = q['MetricStat']['Metric']['Dimensions']
    assert any(d['Name'] == 'DistributionId' and d['Value'] == 'DIST_TEST' for d in dims)
    assert any(d['Name'] == 'Region' and d['Value'] == 'Global' for d in dims)


def test_aggregate_hourly_to_daily(golden_cloudfront):
    """Aggregate hourly data to daily totals using golden test data."""
    timestamps = golden_cloudfront['input']['timestamps']
    values = golden_cloudfront['input']['values']
    result = aggregate_hourly_to_daily(timestamps, values)
    expected = golden_cloudfront['expected']

    for day, expected_bytes in expected.items():
        assert day in result, f'Missing day {day}'
        assert result[day] == expected_bytes, f'Day {day}: {result[day]} != {expected_bytes}'


def test_aggregate_handles_timezone():
    """Hourly data near midnight UTC correctly assigned to UTC+8 day."""
    timestamps = [
        '2026-02-01T15:00:00+00:00',
        '2026-02-01T16:00:00+00:00',
    ]
    values = [100, 200]
    result = aggregate_hourly_to_daily(timestamps, values)
    assert result.get('02/01') == 100  # 15:00 UTC = 23:00 Feb 1 UTC+8
    assert result.get('02/02') == 200  # 16:00 UTC = 00:00 Feb 2 UTC+8


def test_build_metric_query_custom_metric():
    """Custom metric name should be used."""
    queries = build_metric_query('DIST123', metric_name='BytesUploaded')
    assert queries[0]['MetricStat']['Metric']['MetricName'] == 'BytesUploaded'


def test_aggregate_empty_input():
    """Empty input should return empty dict."""
    result = aggregate_hourly_to_daily([], [])
    assert result == {}


# ---------------------------------------------------------------------------
# aggregate_hourly_to_daily — edge cases
# ---------------------------------------------------------------------------
def test_aggregate_single_hour():
    """Single data point should produce one daily entry."""
    result = aggregate_hourly_to_daily(['2026-01-25T16:00:00+00:00'], [500])
    assert result == {'01/26': 500}  # 16:00 UTC = 00:00 Jan 26 UTC+8


def test_aggregate_negative_values():
    """Negative values should be handled (unusual but valid)."""
    result = aggregate_hourly_to_daily(
        ['2026-01-25T00:00:00+00:00', '2026-01-25T01:00:00+00:00'],
        [100, -50],
    )
    assert result['01/25'] == 50  # Both hours fall on Jan 25 UTC+8


def test_aggregate_midnight_boundary():
    """Values exactly at midnight UTC+8 boundary."""
    result = aggregate_hourly_to_daily(
        ['2026-01-25T15:00:00+00:00', '2026-01-25T16:00:00+00:00'],
        [100, 200],
    )
    # 15:00 UTC = 23:00 Jan 25 UTC+8 → Jan 25
    # 16:00 UTC = 00:00 Jan 26 UTC+8 → Jan 26
    assert result['01/25'] == 100
    assert result['01/26'] == 200


# ---------------------------------------------------------------------------
# convert_dates_to_utc — edge cases
# ---------------------------------------------------------------------------
def test_convert_dates_to_utc_leap_year():
    """Leap year Feb 29 should work."""
    start_utc, end_utc = convert_dates_to_utc('2028-02-29', '2028-02-29')
    assert start_utc == '2028-02-28T16:00:00Z'
    assert end_utc == '2028-02-29T16:00:00Z'


def test_convert_dates_to_utc_year_boundary():
    """Date range spanning year boundary."""
    start_utc, end_utc = convert_dates_to_utc('2025-12-31', '2026-01-01')
    assert start_utc == '2025-12-30T16:00:00Z'
    assert end_utc == '2026-01-01T16:00:00Z'


def test_convert_dates_invalid_format():
    """Invalid date format should raise ValueError from strptime."""
    import pytest

    with pytest.raises(ValueError):
        convert_dates_to_utc('2026/01/25', '2026/01/31')


# ---------------------------------------------------------------------------
# fetch_cloudfront_bytes — error paths (mocked)
# ---------------------------------------------------------------------------
def test_fetch_cloudfront_bytes_aws_error(mocker):
    """AWS CLI CalledProcessError should propagate."""
    import subprocess

    mocker.patch(
        'scripts.cloudfront.subprocess.run',
        side_effect=subprocess.CalledProcessError(1, 'aws', stderr='AccessDenied'),
    )
    import pytest

    from scripts.cloudfront import fetch_cloudfront_bytes

    with pytest.raises(subprocess.CalledProcessError):
        fetch_cloudfront_bytes('DIST123', '2026-01-25', '2026-01-31')


def test_fetch_cloudfront_bytes_timeout(mocker):
    """AWS CLI timeout should propagate."""
    import subprocess

    mocker.patch(
        'scripts.cloudfront.subprocess.run',
        side_effect=subprocess.TimeoutExpired(cmd='aws', timeout=60),
    )
    import pytest

    from scripts.cloudfront import fetch_cloudfront_bytes

    with pytest.raises(subprocess.TimeoutExpired):
        fetch_cloudfront_bytes('DIST123', '2026-01-25', '2026-01-31')


def test_fetch_cloudfront_bytes_success(mocker):
    """Normal path should parse AWS CLI JSON output and return daily totals."""
    import json

    mock_output = json.dumps({
        'MetricDataResults': [{
            'Id': 'cf_bytes',
            'Timestamps': [
                '2026-01-25T16:00:00+00:00',
                '2026-01-25T17:00:00+00:00',
            ],
            'Values': [1000, 2000],
        }],
    })
    mock_result = mocker.MagicMock()
    mock_result.stdout = mock_output
    mocker.patch('scripts.cloudfront.subprocess.run', return_value=mock_result)

    from scripts.cloudfront import fetch_cloudfront_bytes

    result = fetch_cloudfront_bytes('DIST123', '2026-01-25', '2026-01-31')
    # 16:00 UTC = 00:00 Jan 26 UTC+8, 17:00 UTC = 01:00 Jan 26 UTC+8
    assert result == {'01/26': 3000}
