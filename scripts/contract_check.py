"""Contract check: verify Akamai DOM selectors still exist.

Connects to real Akamai Control Center and checks that all selectors
used by the automation scripts are present with expected element counts.

Usage:
    uv run python -m scripts.contract_check --headed            # run check
    uv run python -m scripts.contract_check --headed --save     # save baseline
    uv run python -m scripts.contract_check --headed --diff     # compare to baseline
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from scripts.browser_helpers import ab_eval, close_browser, init_browser, navigate_to_report, run_ab
from scripts.calendar_nav import set_date_range
from scripts.config import AKAMAI_URL, STATE_FILE

BASELINE_PATH = Path(__file__).resolve().parent.parent / 'tests' / 'golden' / 'contract_baseline.json'

WAIT_REPORT_LOAD = 15
WAIT_KPI_POLL = 2
WAIT_KPI_MAX_RETRIES = 10

# (css_selector, description, page, phase, expected_min_count)
# phase: 'data' = check after page data loads, 'filter' = check after filter panel opens
CONTRACTS = [
    ('akam-single-kpi', 'KPI card element', 'hostname', 'data', 4),
    ('.single-kpi__title', 'KPI title', 'hostname', 'data', 4),
    ('.single-kpi__value', 'KPI value', 'hostname', 'data', 4),
    ('.single-kpi__unit', 'KPI unit', 'hostname', 'data', 4),
    ('app-date-range-preview', 'Filter trigger', 'hostname', 'data', 1),
    ('#cpcodes-filter-editor', 'CP code editor', 'hostname', 'filter', 1),
    ("input[placeholder='CP codes']", 'CP code search', 'hostname', 'filter', 1),
    ('.akam-calendar-body-cell-content', 'Calendar day cells', 'hostname', 'filter', 28),
    ('table.cdk-table.akam-table', 'Geography table', 'geography', 'data', 1),
]


def check_selector(selector: str) -> int:  # pragma: no cover
    """Return count of elements matching CSS selector."""
    escaped = selector.replace("'", "\\'")
    raw = ab_eval(f"document.querySelectorAll('{escaped}').length")
    try:
        return int(raw)
    except (ValueError, TypeError):
        return 0


def _check_and_record(selector: str, description: str, page: str, min_count: int, results: list[dict]) -> None:
    """Check a single selector and append result."""
    count = check_selector(selector)
    found = count >= min_count
    status = 'OK' if found else 'MISSING'
    icon = '\u2705' if found else '\u274c'
    print(f'  {icon} [{status}] {description}: {selector} (found={count}, expected>={min_count})')
    results.append({
        'selector': selector,
        'description': description,
        'page': page,
        'count': count,
        'expected_min': min_count,
        'found': found,
    })


def _wait_for_data(indicator_selector: str) -> None:  # pragma: no cover
    """Poll until data elements appear or timeout."""
    for i in range(WAIT_KPI_MAX_RETRIES):
        count = check_selector(indicator_selector)
        if count > 0:
            print(f'  (data loaded after {(i + 1) * WAIT_KPI_POLL}s)')
            return
        time.sleep(WAIT_KPI_POLL)
    print(f'  (data not loaded after {WAIT_KPI_MAX_RETRIES * WAIT_KPI_POLL}s, checking anyway)')


def run_checks(headed: bool) -> list[dict]:  # pragma: no cover
    """Run all contract checks against live Akamai.

    For each page:
      1. Navigate to report page
      2. Open filter panel → check 'filter' selectors (calendar, CP codes)
      3. Click Apply to trigger data load → check 'data' selectors (KPI, geo table)
    """
    init_browser(STATE_FILE, AKAMAI_URL, headed=headed)
    time.sleep(5)

    results = []

    try:
        for page in ['hostname', 'geography']:
            page_contracts = [(s, d, p, ph, m) for s, d, p, ph, m in CONTRACTS if p == page]
            if not page_contracts:
                continue

            # Navigate
            report_name = 'Traffic by Hostname' if page == 'hostname' else 'Traffic by Geography'
            navigate_to_report(report_name)
            time.sleep(WAIT_REPORT_LOAD)

            # Open filter panel
            ab_eval("document.querySelector('app-date-range-preview')?.click()")
            run_ab('wait', '#cpcodes-filter-editor')
            time.sleep(2)

            # Check 'filter' phase selectors while panel is open
            for selector, description, pg, phase, min_count in page_contracts:
                if phase == 'filter':
                    _check_and_record(selector, description, pg, min_count, results)

            # Set date range to a known-good period (ensures data exists)
            set_date_range('2026-01-25', '2026-01-31')
            time.sleep(1)

            # Ensure CP codes are selected (filters don't carry over between reports)
            ab_eval("""(() => {
                const editor = document.getElementById('cpcodes-filter-editor');
                const spans = editor.querySelectorAll('span');
                for (const s of spans) {
                    if (s.textContent.trim().startsWith('Select:')) { s.click(); break; }
                }
            })()""")
            time.sleep(1)

            # Click Apply to trigger data load
            run_ab('scrollintoview', "button:has-text('Apply')")
            run_ab('click', "button:has-text('Apply')")
            time.sleep(WAIT_REPORT_LOAD)

            # Poll for data
            if page == 'hostname':
                _wait_for_data('akam-single-kpi')
            else:
                _wait_for_data('table.cdk-table.akam-table')

            # Check 'data' phase selectors after data loads
            for selector, description, pg, phase, min_count in page_contracts:
                if phase == 'data':
                    _check_and_record(selector, description, pg, min_count, results)
    finally:
        close_browser()

    return results


def save_baseline(results: list[dict]) -> None:  # pragma: no cover
    """Save results as baseline JSON."""
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    baseline = {
        'timestamp': datetime.now(UTC).isoformat(),
        'results': results,
    }
    BASELINE_PATH.write_text(json.dumps(baseline, indent=2) + '\n')
    print(f'\nBaseline saved: {BASELINE_PATH}')


def diff_baseline(results: list[dict]) -> int:
    """Compare results against saved baseline. Returns exit code."""
    if not BASELINE_PATH.exists():
        print(f'\nNo baseline found at {BASELINE_PATH}. Run with --save first.')
        return 2

    baseline = json.loads(BASELINE_PATH.read_text())
    baseline_map = {r['selector']: r for r in baseline['results']}

    print(f"\nComparing to baseline from {baseline['timestamp']}:")
    exit_code = 0

    for result in results:
        sel = result['selector']
        if sel not in baseline_map:
            print(f'  \U0001f195 NEW: {result["description"]}: {sel} (count={result["count"]})')
            continue
        old = baseline_map[sel]
        if old['found'] and not result['found']:
            print(f'  \U0001f534 BROKEN: {result["description"]}: {sel} (was {old["count"]}, now {result["count"]})')
            exit_code = 1
        elif result['count'] < old['count']:
            print(f'  \u26a0\ufe0f  WARNING: {result["description"]}: {sel} count decreased ({old["count"]} -> {result["count"]})')
        else:
            print(f'  \u2705 OK: {result["description"]}: {sel} ({result["count"]})')

    return exit_code


def main():  # pragma: no cover
    parser = argparse.ArgumentParser(description='Akamai DOM selector contract check')
    parser.add_argument('--headed', action='store_true', help='Run browser in headed mode')
    parser.add_argument('--save', action='store_true', help='Save results as baseline')
    parser.add_argument('--diff', action='store_true', help='Compare against saved baseline')
    args = parser.parse_args()

    print('Running contract checks...\n')
    results = run_checks(headed=args.headed)

    passed = sum(1 for r in results if r['found'])
    total = len(results)
    print(f'\nResults: {passed}/{total} selectors found')

    if args.save:
        save_baseline(results)

    if args.diff:
        exit_code = diff_baseline(results)
        sys.exit(exit_code)

    if passed < total:
        sys.exit(1)


if __name__ == '__main__':
    main()
