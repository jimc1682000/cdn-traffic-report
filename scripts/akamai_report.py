"""Main entry point for Akamai + CloudFront traffic reporting."""

import argparse
import functools
import json
import time
from pathlib import Path

from scripts.browser_helpers import ab_eval, ab_screenshot, close_browser, init_browser, navigate_to_report, run_ab
from scripts.calendar_nav import set_date_range
from scripts.cloudfront import fetch_cloudfront_bytes
from scripts.config import AKAMAI_URL, CLOUDFRONT_CONFIG, REPORT_TYPES, STATE_FILE
from scripts.cpcode_select import CP_EDITOR_ID, select_cp_codes
from scripts.data_extract import (
    build_report_output,
    convert_unit,
    extract_geography_table,
    extract_traffic_cards,
)

# Force unbuffered print so logs appear in real-time
print = functools.partial(print, flush=True)  # noqa: A001

OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'output'
GOLDEN_DIR = Path(__file__).resolve().parent.parent / 'tests' / 'golden'

# Browser automation wait times (seconds)
WAIT_UI_UPDATE = 2
WAIT_REPORT_LOAD = 10
WAIT_BROWSER_INIT = 5


def _setup_report_filters(
    report_type: str,
    report_page: str,
    config,
    start_date: str,
    end_date: str,
) -> None:
    """Navigate to report page and apply date range + CP code filters.

    Shared setup flow for both hostname and geography reports:
    navigate → open filter panel → set date → select CP codes → Apply.
    """
    print(f'[{report_type}] Running: {config.label}')

    navigate_to_report(report_page)

    # Open filter panel (wait command blocks until element appears)
    ab_eval("document.querySelector('app-date-range-preview')?.click()")
    run_ab('wait', f'#{CP_EDITOR_ID}')

    # Set date range
    print(f'[{report_type}] Setting date range: {start_date} to {end_date}')
    set_date_range(start_date, end_date)
    time.sleep(WAIT_UI_UPDATE)

    # Select CP codes
    print(f'[{report_type}] Selecting CP codes: {config.cp_codes}')
    select_cp_codes(config)
    time.sleep(WAIT_UI_UPDATE)

    # Click Apply
    run_ab('scrollintoview', "button:has-text('Apply')")
    run_ab('click', "button:has-text('Apply')")
    time.sleep(WAIT_REPORT_LOAD)


def run_akamai_report(report_type: str, start_date: str, end_date: str) -> dict:
    """Run a single Akamai traffic-by-hostname report type. Browser must already be initialized."""
    config = REPORT_TYPES[report_type]
    _setup_report_filters(report_type, 'Traffic by Hostname', config, start_date, end_date)

    # Extract traffic data
    print(f'[{report_type}] Extracting traffic data...')
    cards = extract_traffic_cards()

    traffic = {}
    for key in ['edge', 'origin', 'midgress', 'offload']:
        if key in cards:
            val = cards[key]['value']
            src_unit = cards[key]['unit']
            if src_unit == '%':
                traffic[key] = val
            elif src_unit != config.unit:
                traffic[key] = convert_unit(val, src_unit, config.unit)
            else:
                traffic[key] = val

    # Take screenshot
    screenshot_path = str(OUTPUT_DIR / f'{report_type}_{start_date}_{end_date}.png')
    ab_screenshot(screenshot_path)
    print(f'[{report_type}] Screenshot: {screenshot_path}')

    return build_report_output(
        report_type=report_type,
        label=config.label,
        start_date=start_date,
        end_date=end_date,
        traffic=traffic,
        unit=config.unit,
    )


def run_geography_report(start_date: str, end_date: str) -> dict:
    """Run geography report (Traffic by Geography). Browser must already be initialized."""
    config = REPORT_TYPES['geography']
    _setup_report_filters('geography', 'Traffic by Geography', config, start_date, end_date)

    # Extract geography data
    print('[geography] Extracting geography data...')
    geography = extract_geography_table(config.geo_countries)

    # Take screenshot
    screenshot_path = str(OUTPUT_DIR / f'geography_{start_date}_{end_date}.png')
    ab_screenshot(screenshot_path)
    print(f'[geography] Screenshot: {screenshot_path}')

    return build_report_output(
        report_type='geography',
        label=config.label,
        start_date=start_date,
        end_date=end_date,
        traffic={},
        unit=config.unit,
        geography=geography,
    )


def run_cloudfront_report(start_date: str, end_date: str) -> dict:
    """Run CloudFront BytesDownloaded report."""
    print(f'[cloudfront] Fetching CloudFront metrics: {start_date} to {end_date}')
    daily = fetch_cloudfront_bytes(
        distribution_id=CLOUDFRONT_CONFIG.distribution_id,
        start_date=start_date,
        end_date=end_date,
        region=CLOUDFRONT_CONFIG.region,
    )
    return {
        'date_range': {'start': start_date, 'end': end_date},
        'type': 'cloudfront',
        'label': 'CloudFront',
        'distribution_id': CLOUDFRONT_CONFIG.distribution_id,
        'daily_bytes': daily,
    }


def main():
    parser = argparse.ArgumentParser(description='Akamai + CloudFront Traffic Report')
    parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument(
        '--type',
        choices=list(REPORT_TYPES.keys()) + ['cloudfront'],
        help='Report type (omit for all)',
    )
    parser.add_argument('--headed', action='store_true', help='Run browser in headed mode')
    parser.add_argument('--output', help='Output JSON file path')
    parser.add_argument('--save-golden', action='store_true', help='Save each result as golden data in tests/golden/')
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Determine which reports to run
    if args.type:
        types_to_run = [args.type]
    else:
        types_to_run = list(REPORT_TYPES.keys()) + ['cloudfront']

    # Separate Akamai hostname, geography, and CloudFront types
    akamai_hostname_types = [t for t in types_to_run if t not in ('cloudfront', 'geography')]
    run_geo = 'geography' in types_to_run
    run_cf = 'cloudfront' in types_to_run

    results = []

    # Run all Akamai reports in a single browser session
    if akamai_hostname_types or run_geo:
        init_browser(STATE_FILE, AKAMAI_URL, headed=args.headed)
        time.sleep(WAIT_BROWSER_INIT)
        try:
            for report_type in akamai_hostname_types:
                result = run_akamai_report(report_type, args.start, args.end)
                results.append(result)
                print(json.dumps(result, ensure_ascii=False, indent=2))

            if run_geo:
                result = run_geography_report(args.start, args.end)
                results.append(result)
                print(json.dumps(result, ensure_ascii=False, indent=2))
        finally:
            close_browser()

    # Run CloudFront (no browser needed)
    if run_cf:
        result = run_cloudfront_report(args.start, args.end)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # Save output
    output_path = args.output or str(OUTPUT_DIR / f'report_{args.start}_{args.end}.json')
    output_parent = Path(output_path).parent
    if not output_parent.exists():
        output_parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results if len(results) > 1 else results[0], f, ensure_ascii=False, indent=2)
    print(f'\nOutput saved: {output_path}')

    # Save golden data (one file per report type)
    if args.save_golden:
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        for result in results:
            rtype = result.get('type', 'unknown')
            golden_path = GOLDEN_DIR / f'report_{rtype}.json'
            with open(golden_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f'Golden saved: {golden_path}')

    return results


if __name__ == '__main__':
    main()
