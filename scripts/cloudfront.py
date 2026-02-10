"""AWS CloudFront metric extraction via CloudWatch."""

import json
import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta, timezone

UTC_PLUS_8 = timezone(timedelta(hours=8))


def build_metric_query(distribution_id: str, metric_name: str = 'BytesDownloaded') -> list[dict]:
    """Build CloudWatch metric-data-queries JSON structure."""
    return [
        {
            'Id': 'cf_bytes',
            'MetricStat': {
                'Metric': {
                    'Namespace': 'AWS/CloudFront',
                    'MetricName': metric_name,
                    'Dimensions': [
                        {'Name': 'DistributionId', 'Value': distribution_id},
                        {'Name': 'Region', 'Value': 'Global'},
                    ],
                },
                'Period': 3600,
                'Stat': 'Sum',
            },
            'ReturnData': True,
        }
    ]


def convert_dates_to_utc(start_date: str, end_date: str) -> tuple[str, str]:
    """Convert UTC+8 date strings to UTC start/end times for CloudWatch API.

    Args:
        start_date: "2026-01-25" (interpreted as start of day in UTC+8)
        end_date: "2026-01-31" (interpreted as end of day in UTC+8)

    Returns:
        Tuple of (start_time_utc, end_time_utc) in ISO format.
        e.g. ("2026-01-24T16:00:00Z", "2026-01-31T16:00:00Z")
    """
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=UTC_PLUS_8)
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=UTC_PLUS_8)
    end_dt = end_dt + timedelta(days=1)

    start_utc = start_dt.astimezone(UTC)
    end_utc = end_dt.astimezone(UTC)

    return (
        start_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
        end_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
    )


def aggregate_hourly_to_daily(timestamps: Sequence[str], values: Sequence[float]) -> dict[str, int]:
    """Aggregate hourly CloudWatch data to daily totals in UTC+8.

    Args:
        timestamps: List of ISO format timestamps (UTC)
        values: Corresponding hourly byte counts

    Returns:
        Dict mapping "MM/DD" -> total bytes for that UTC+8 day
    """
    daily: dict[str, float] = {}
    for ts_str, val in zip(timestamps, values):
        utc_dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        local_dt = utc_dt.astimezone(UTC_PLUS_8)
        day_key = local_dt.strftime('%m/%d')
        daily[day_key] = daily.get(day_key, 0) + val

    return {k: int(v) for k, v in sorted(daily.items())}


def fetch_cloudfront_bytes(
    distribution_id: str,
    start_date: str,
    end_date: str,
    region: str = 'us-east-1',
) -> dict[str, int]:
    """Fetch BytesDownloaded from CloudWatch for a CloudFront distribution.

    Args:
        distribution_id: CloudFront distribution ID string
        start_date: "2026-01-25" (UTC+8 date)
        end_date: "2026-01-31" (UTC+8 date)
        region: AWS region for CloudWatch API

    Returns:
        {"01/25": 1190984349883, "01/26": 714746078518, ...}
    """
    queries = build_metric_query(distribution_id)
    start_utc, end_utc = convert_dates_to_utc(start_date, end_date)

    cmd = [
        'aws',
        'cloudwatch',
        'get-metric-data',
        '--region',
        region,
        '--metric-data-queries',
        json.dumps(queries),
        '--start-time',
        start_utc,
        '--end-time',
        end_utc,
        '--output',
        'json',
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
    data = json.loads(result.stdout)

    metric_results = data['MetricDataResults'][0]
    timestamps = metric_results['Timestamps']
    values = metric_results['Values']

    return aggregate_hourly_to_daily(timestamps, values)
