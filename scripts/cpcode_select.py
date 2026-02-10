"""CP code selection logic for Akamai report sidebar."""

import time

from scripts.browser_helpers import ab_eval, run_ab

CP_EDITOR_ID = 'cpcodes-filter-editor'


def scroll_to_cp_codes() -> None:
    """Scroll the CP codes section into view."""
    run_ab('scrollintoview', f'#{CP_EDITOR_ID}')
    time.sleep(0.5)


def _click_cp_action(action: str) -> None:
    """Click a Select/Deselect link inside the CP codes filter section."""
    scroll_to_cp_codes()
    ab_eval(f"""
    (() => {{
        const editor = document.getElementById('{CP_EDITOR_ID}');
        const spans = editor.querySelectorAll('span');
        for (const s of spans) {{
            if (s.textContent.trim().startsWith('{action}:')) {{
                s.click();
                return 'clicked';
            }}
        }}
        return 'not_found';
    }})()
    """)
    time.sleep(0.5)


def deselect_all() -> None:
    """Click Deselect link inside the CP codes filter section."""
    _click_cp_action('Deselect')


def select_all() -> None:
    """Click Select link inside the CP codes filter section."""
    _click_cp_action('Select')


def search_and_select_cp_code(code: str, retries: int = 3) -> None:
    """Search for a CP code and select its checkbox.

    Uses scoped selector to click within CP codes editor only,
    avoiding ambiguity with the main data table.
    """
    scroll_to_cp_codes()

    for attempt in range(retries):
        # Fill the CP codes search input
        run_ab('fill', "input[placeholder='CP codes']", code)
        time.sleep(2)

        # Click within CP codes editor (scoped to avoid matching data table)
        try:
            run_ab('click', f'#{CP_EDITOR_ID} >> text=({code})')
            break
        except Exception:
            if attempt < retries - 1:
                run_ab('fill', "input[placeholder='CP codes']", '')
                time.sleep(2)
            else:
                raise
    time.sleep(0.3)

    # Clear search
    run_ab('fill', "input[placeholder='CP codes']", '')
    time.sleep(0.5)


def select_cp_codes(config) -> None:
    """Full workflow to select CP codes based on config.

    Args:
        config: ReportConfig instance with cp_codes list.
            If cp_codes is ["ALL"], selects all codes.
            Otherwise, deselects all then searches and selects each code.
    """
    scroll_to_cp_codes()

    if config.cp_codes == ['ALL']:
        select_all()
        return

    deselect_all()
    for code in config.cp_codes:
        search_and_select_cp_code(code)
