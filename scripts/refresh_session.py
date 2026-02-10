"""Refresh Akamai session — check cookie validity and re-login if needed.

Usage:
    uv run python -m scripts.refresh_session          # auto-detect
    uv run python -m scripts.refresh_session --force   # force re-login
"""

import argparse
import contextlib
import json
import os
import subprocess
import sys
import time

from scripts.browser_helpers import exec_ab
from scripts.config import AKAMAI_URL, STATE_FILE


def _close_browser() -> None:
    with contextlib.suppress(subprocess.CalledProcessError):
        exec_ab('close')


def _save_state() -> None:
    """Save current browser cookies + localStorage to state file."""
    # Get cookies
    raw_cookies = exec_ab('cookies', 'get', '--json')
    cookies_data = json.loads(raw_cookies)
    cookies = cookies_data.get('data', {}).get('cookies', [])

    # Get localStorage
    raw_storage = exec_ab('storage', 'local', '--json')
    storage_data = json.loads(raw_storage)
    local_items = storage_data.get('data', {}).get('data', {})

    # Build state file in Playwright storageState format
    state = {
        'cookies': cookies,
        'origins': [
            {
                'origin': 'https://control.akamai.com',
                'localStorage': [{'name': k, 'value': v} for k, v in local_items.items()],
            }
        ],
    }

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.chmod(STATE_FILE, 0o600)
    print(f'[session] State saved to {STATE_FILE} ({len(cookies)} cookies)')


def _check_logged_in() -> bool:
    """Check if the current page is the reports page (not login)."""
    url = exec_ab('get', 'url')
    url = url.strip('"')
    return '/apps/auth/' not in url and '/login' not in url


def refresh_session(force: bool = False) -> bool:
    """Check and refresh Akamai session.

    Returns True if session is valid after the process.
    """
    _close_browser()

    if not force:
        # Try opening with existing state
        print('[session] Opening browser with saved state...')
        exec_ab('--state', STATE_FILE, 'open', AKAMAI_URL)
        time.sleep(8)

        if _check_logged_in():
            print('[session] Session is valid — cookies still active.')
            _save_state()
            _close_browser()
            return True

        print('[session] Session expired — need to re-login.')
        _close_browser()
        time.sleep(2)

    # Open headed browser for manual login
    print('[session] Opening headed browser for login...')
    exec_ab('--headed', 'open', AKAMAI_URL)
    time.sleep(5)

    print('[session] Please log in to Akamai Control Center in the browser.')
    print('[session] After you see the Reports page, press Enter here...')
    sys.stdin.readline()

    # Verify login succeeded
    if not _check_logged_in():
        print('[session] ERROR: Still on login page. Please try again.')
        _close_browser()
        return False

    # Save state
    _save_state()
    _close_browser()
    print('[session] Done — session refreshed successfully.')
    return True


def main():
    parser = argparse.ArgumentParser(description='Refresh Akamai session cookies')
    parser.add_argument('--force', action='store_true', help='Force re-login (skip validity check)')
    args = parser.parse_args()

    success = refresh_session(force=args.force)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
