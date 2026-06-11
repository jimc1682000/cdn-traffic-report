"""Refresh Akamai session — log in and leave the browser open for reuse.

Akamai session cookies are session-only: they die when the browser closes, so
a saved state file cannot restore a logged-in session. The working model is to
log in once and hand the *live* browser to `akamai_report --reuse-browser`.

Login strategy:
1. 1Password auto-login (default, when ``onepassword.enabled``): read username,
   password and TOTP via the ``op`` CLI and drive the login form. Secrets are
   piped straight into the browser and never printed.
2. Manual fallback: open the headed browser and poll until you finish logging
   in by hand. This works under non-TTY shells (e.g. Claude Code ``!``) because
   it polls the page instead of blocking on stdin.

On success the browser is LEFT OPEN. Then run:
    uv run python -m scripts.akamai_report --start ... --end ... \
        --reuse-browser --close-when-done

Usage:
    uv run python -m scripts.refresh_session          # auto-detect, login if needed
    uv run python -m scripts.refresh_session --force   # force re-login
    uv run python -m scripts.refresh_session --manual  # skip op, manual login
"""

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys
import time

from scripts.browser_helpers import exec_ab
from scripts.config import AKAMAI_URL, ONEPASSWORD_CONFIG, STATE_FILE

# Waits (seconds) between login steps and for the manual-login poll loop.
WAIT_PAGE = 6
WAIT_STEP = 5
MANUAL_POLL_INTERVAL = 3
MANUAL_POLL_TIMEOUT = 240


def _close_browser() -> None:  # pragma: no cover
    with contextlib.suppress(subprocess.CalledProcessError):
        exec_ab('close')


def _save_state() -> None:
    """Save current browser cookies + localStorage to state file (best-effort)."""
    raw_cookies = exec_ab('cookies', 'get', '--json')
    cookies_data = json.loads(raw_cookies)
    cookies = cookies_data.get('data', {}).get('cookies', [])

    raw_storage = exec_ab('storage', 'local', '--json')
    storage_data = json.loads(raw_storage)
    local_items = storage_data.get('data', {}).get('data', {})

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
    """Return True if the current page is past auth (not login/challenge)."""
    url = exec_ab('get', 'url').strip('"')
    return '/apps/auth/' not in url and '/login' not in url


# ---------------------------------------------------------------------------
# 1Password auto-login
# ---------------------------------------------------------------------------
def _op_available() -> bool:  # pragma: no cover
    return shutil.which('op') is not None


def _op_username_password(cfg) -> tuple[str, str]:  # pragma: no cover
    """Fetch username + password via op (one call → one Touch ID prompt).

    Field extraction is purpose-based (USERNAME / PASSWORD), robust to the
    field labels (the password label may be e.g. 'newPassword'). Secrets are
    returned for immediate use and never logged.
    """
    raw = subprocess.run(
        ['op', 'item', 'get', cfg.item, '--account', cfg.account, '--format', 'json', '--reveal'],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if raw.returncode != 0:
        raise RuntimeError(f'op item get failed: {raw.stderr.strip()[:200]}')
    data = json.loads(raw.stdout)
    username = password = None
    for f in data.get('fields', []):
        if f.get('purpose') == 'USERNAME':
            username = f.get('value')
        elif f.get('purpose') == 'PASSWORD':
            password = f.get('value')
    if not username or not password:
        raise RuntimeError('op item missing USERNAME/PASSWORD field')
    return username, password


def _op_totp(cfg) -> str:  # pragma: no cover
    """Fetch a fresh TOTP code via op (read late so it is not stale)."""
    r = subprocess.run(
        ['op', 'item', 'get', cfg.item, '--account', cfg.account, '--otp'],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if r.returncode != 0:
        raise RuntimeError(f'op otp failed: {r.stderr.strip()[:200]}')
    return r.stdout.strip()


def _eval_secret(js: str) -> None:  # pragma: no cover
    """Run an eval whose JS embeds a secret.

    On failure, CalledProcessError stringifies the full command — including the
    embedded password/OTP — so never let it propagate. Re-raise a sanitized
    error that carries no credential and no command line.
    """
    try:
        exec_ab('eval', js)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f'browser eval failed (exit {e.returncode})') from None


def _fill_react(selector: str, value: str) -> None:  # pragma: no cover
    """Set a React-controlled input via the native setter + input event."""
    sel, val = json.dumps(selector), json.dumps(value)
    js = (
        '(()=>{const el=document.querySelector(' + sel + '); if(!el)return "no_el";'
        'const set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,"value").set;'
        'set.call(el, ' + val + '); el.dispatchEvent(new Event("input",{bubbles:true}));'
        'el.dispatchEvent(new Event("change",{bubbles:true})); return "ok";})()'
    )
    _eval_secret(js)


def _click_button(text: str) -> str:  # pragma: no cover
    js = (
        '(()=>{const b=[...document.querySelectorAll("button")]'
        '.find(x=>x.textContent.trim()===' + json.dumps(text) + '); if(!b)return "no_btn";'
        'if(b.disabled)return "disabled"; b.scrollIntoView(); b.click(); return "clicked";})()'
    )
    return exec_ab('eval', js).strip('"')


def _fill_totp(code: str) -> None:  # pragma: no cover
    """Fill the 6 segmented OTP boxes (input[name=otp-code-0..5])."""
    js = (
        '(()=>{const code=' + json.dumps(code) + ';'
        'const set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,"value").set;'
        'let ok=0; for(let i=0;i<code.length;i++){'
        'const el=document.querySelector("input[name=otp-code-"+i+"]"); if(!el)continue;'
        'el.focus(); set.call(el, code[i]); el.dispatchEvent(new Event("input",{bubbles:true}));'
        'el.dispatchEvent(new KeyboardEvent("keyup",{bubbles:true,key:code[i]})); ok++;}'
        'return "filled:"+ok;})()'
    )
    _eval_secret(js)


def _op_login(cfg) -> bool:  # pragma: no cover
    """Drive the Akamai login form with 1Password credentials.

    Assumes the browser is already open on the login page. Returns True if
    logged in afterwards.
    """
    print('[session] 1Password auto-login...')
    username, password = _op_username_password(cfg)

    _fill_react('input[name="username"]', username)
    username = None  # noqa: F841 — drop reference promptly
    if _click_button('Next') != 'clicked':
        print('[session] op-login: Next button not found.')
        return False
    time.sleep(WAIT_STEP)

    _fill_react('input[placeholder="password"]', password)
    password = None  # noqa: F841
    if _click_button('Sign in') != 'clicked':
        print('[session] op-login: Sign in button not found.')
        return False
    time.sleep(WAIT_STEP)

    # TOTP challenge — fetch fresh code right before filling.
    code = _op_totp(cfg)
    _fill_totp(code)
    code = None  # noqa: F841
    if _click_button('Done') != 'clicked':
        print('[session] op-login: Done button not found (no TOTP challenge?).')
    time.sleep(WAIT_STEP)

    return _check_logged_in()


def _manual_login(timeout: int = MANUAL_POLL_TIMEOUT) -> bool:  # pragma: no cover
    """Wait for a human to log in via the open headed browser.

    Polls the page instead of blocking on stdin, so it works under non-TTY
    shells (e.g. Claude Code's ``!`` prefix) where readline() returns EOF.
    """
    print('[session] Manual login: log in to Akamai in the open browser window.')
    print(f'[session] Waiting up to {timeout}s for the Reports page to appear...')
    waited = 0
    while waited < timeout:
        if _check_logged_in():
            return True
        time.sleep(MANUAL_POLL_INTERVAL)
        waited += MANUAL_POLL_INTERVAL
    print('[session] Timed out waiting for manual login.')
    return False


def refresh_session(force: bool = False, manual: bool = False) -> bool:  # pragma: no cover
    """Ensure a logged-in Akamai browser session, leaving the browser OPEN.

    Returns True if logged in. The caller should then run
    ``akamai_report --reuse-browser`` against the live session.
    """
    _close_browser()
    time.sleep(1)

    # Open a fresh headed daemon (--state may restore cookies if still valid).
    exec_ab('--state', STATE_FILE, '--headed', 'open', AKAMAI_URL)
    time.sleep(WAIT_PAGE)

    if not force and _check_logged_in():
        print('[session] Session is valid — cookies still active.')
        with contextlib.suppress(Exception):
            _save_state()
        print('[session] Browser left open. Run akamai_report --reuse-browser next.')
        return True

    logged_in = False
    cfg = ONEPASSWORD_CONFIG
    if not manual and cfg and cfg.enabled and _op_available():
        try:
            logged_in = _op_login(cfg)
        except Exception:  # noqa: BLE001 — fall back to manual on any op error
            # Do NOT print the exception: it may embed the command/credential.
            print('[session] 1Password login failed; falling back to manual.')
            logged_in = False

    if not logged_in:
        logged_in = _manual_login()

    if not logged_in:
        print('[session] ERROR: still not logged in.')
        return False

    with contextlib.suppress(Exception):
        _save_state()
    print('[session] Logged in. Browser left open — run akamai_report --reuse-browser next.')
    return True


def main():  # pragma: no cover
    parser = argparse.ArgumentParser(description='Refresh Akamai session (leaves browser open)')
    parser.add_argument('--force', action='store_true', help='Force re-login (skip validity check)')
    parser.add_argument('--manual', action='store_true', help='Skip 1Password; log in manually')
    args = parser.parse_args()

    success = refresh_session(force=args.force, manual=args.manual)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
