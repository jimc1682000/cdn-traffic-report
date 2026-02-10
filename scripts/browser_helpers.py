"""agent-browser wrapper functions."""

import contextlib
import json
import subprocess

from scripts.config import AB_BIN, SESSION

# Global options set during init_browser
_global_opts: list[str] = []


def exec_ab(*args: str) -> str:
    """Run agent-browser with session only (no global opts), return stdout."""
    cmd = [AB_BIN, '--session', SESSION, *args]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
    return result.stdout.strip()


def run_ab(*args: str) -> str:
    """Run agent-browser with global browser options, return stdout."""
    return exec_ab(*_global_opts, *args)


def ab_eval(js: str) -> str:
    """Execute JavaScript via agent-browser eval."""
    return run_ab('eval', js)


def ab_mouse_click(x: int, y: int) -> None:  # pragma: no cover
    """Perform mouse click at (x, y) via move→down→up."""
    run_ab('mouse', 'move', str(x), str(y))
    run_ab('mouse', 'down')
    run_ab('mouse', 'up')


def ab_screenshot(path: str) -> None:  # pragma: no cover
    """Take screenshot and save to path."""
    run_ab('screenshot', path)


def get_element_center(js_selector: str) -> tuple[int, int]:
    """Get center coordinates of element via getBoundingClientRect.

    Args:
        js_selector: JS expression that returns an element,
            e.g. "document.querySelector('.my-btn')"

    Returns:
        (x, y) center coordinates
    """
    js = f"""
    (() => {{
        const el = {js_selector};
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return {{x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)}};
    }})()
    """
    raw = ab_eval(js)
    data = json.loads(raw)
    if data is None:
        raise ValueError(f'Element not found: {js_selector}')
    return data['x'], data['y']


def init_browser(state_file: str, url: str, headed: bool = False) -> None:  # pragma: no cover
    """Initialize browser session and navigate to URL.

    Always closes any existing daemon first, then launches fresh with --state
    to ensure cookies from the state file are loaded.
    """
    global _global_opts

    # Close any existing daemon so --state will be applied on fresh launch
    _global_opts = []
    with contextlib.suppress(subprocess.CalledProcessError):
        run_ab('close')

    _global_opts = ['--state', state_file]
    if headed:
        _global_opts.append('--headed')
    run_ab('open', url)


REPORT_HASH = {
    'Traffic by Hostname': '#/predefined/traffic-by-hostname-2',
    'Traffic by Geography': '#/predefined/traffic-by-geography',
}


def navigate_to_report(report_name: str) -> None:  # pragma: no cover
    """Navigate to a specific report via URL hash change.

    Uses window.location.hash to switch reports within the SPA.
    Do NOT include query string parameters — they cause permission errors.
    """
    import time

    # Check if already on the correct report
    title = ab_eval("document.querySelector('h2')?.textContent?.trim() || ''")
    if report_name in title:
        return

    hash_path = REPORT_HASH[report_name]
    ab_eval(f"window.location.hash = '{hash_path}'")
    time.sleep(8)

    # Verify navigation succeeded
    new_title = ab_eval("document.querySelector('h2')?.textContent?.trim() || ''")
    if report_name not in new_title:
        # Retry once
        ab_eval(f"window.location.hash = '{hash_path}'")
        time.sleep(8)
        retry_title = ab_eval("document.querySelector('h2')?.textContent?.trim() || ''")
        if report_name not in retry_title:
            raise RuntimeError(f'Failed to navigate to {report_name!r} after retry (got {retry_title!r})')


def close_browser() -> None:  # pragma: no cover
    """Close the browser session."""
    run_ab('close')
