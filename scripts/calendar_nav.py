"""Calendar navigation logic for Akamai date range picker."""

import re
import time
from datetime import datetime

from scripts.browser_helpers import ab_eval, run_ab

MONTH_NAMES = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
]


def _parse_month_str(month_str: str) -> tuple[int, int]:
    """Parse 'Nov 2025' or 'November 2025' or 'Dec' into (year, month_index).

    Returns:
        (year, month) where month is 1-12
    """
    parts = month_str.strip().split()
    if len(parts) != 2:
        raise ValueError(f'Cannot parse month string: {month_str!r}')
    month_name, year_str = parts
    year = int(year_str)

    for i, name in enumerate(MONTH_NAMES):
        if name.startswith(month_name):
            return year, i + 1

    raise ValueError(f'Unknown month: {month_name!r}')


def calculate_nav_clicks(current_months: dict[str, str], target_month: str) -> int:
    """Calculate number of arrow clicks to reach target month.

    Pure logic function - no browser interaction.

    Args:
        current_months: {"left": "Nov 2025", "right": "Dec 2025"}
        target_month: e.g. "Jan 2026" or "January 2026"

    Returns:
        Number of clicks. Positive = forward, negative = backward.
    """
    right_year, right_month = _parse_month_str(current_months['right'])
    target_year, target_m = _parse_month_str(target_month)

    right_total = right_year * 12 + right_month
    target_total = target_year * 12 + target_m

    return target_total - right_total


def get_displayed_months() -> dict[str, str]:
    """Read calendar month headers from snapshot.

    The Akamai calendar has two month buttons: left and right.
    Snapshot shows them as button "December" + button "2025" and button "January" + button "2026".

    Returns:
        {"left": "December 2025", "right": "January 2026"}
    """
    snapshot = run_ab('snapshot')
    # Find month+year button pairs in the calendar grid area
    # Pattern: button "MonthName" followed by button "Year"
    month_pattern = r'button "(' + '|'.join(MONTH_NAMES) + r')"'
    year_pattern = r'button "(\d{4})"'

    months = re.findall(month_pattern, snapshot)
    years = re.findall(year_pattern, snapshot)

    if len(months) >= 2 and len(years) >= 2:
        return {
            'left': f'{months[0]} {years[0]}',
            'right': f'{months[1]} {years[1]}',
        }
    raise ValueError(f'Could not find calendar months in snapshot. Found months={months}, years={years}')


def click_calendar_arrow(direction: str) -> None:
    """Click forward or back arrow on calendar.

    The back arrow is the first unlabeled button before the left month.
    The forward arrow is the second unlabeled button after the right month.
    We use snapshot refs to find them.
    """
    snapshot = run_ab('snapshot')
    # Find all button refs in the calendar area
    # Back button comes before month buttons, forward after
    # Pattern: button [ref=eXXX] with just an img child (no text)
    # From the snapshot we know: back=e130, forward=e173 pattern
    # But refs change, so we find by position relative to month buttons

    # Find the month button refs
    month_refs = re.findall(r'button "(?:' + '|'.join(MONTH_NAMES) + r')" \[ref=(e\d+)\]', snapshot)

    if direction == 'back':
        # Back arrow is the button[ref] right before the first month button
        if month_refs:
            first_month_ref = month_refs[0]
            # Find the button ref just before it
            all_button_refs = re.findall(r'button \[ref=(e\d+)\]', snapshot)
            for i, ref in enumerate(all_button_refs):
                # Check if the next notable element is our first month
                ref_num = int(ref[1:])
                first_month_num = int(first_month_ref[1:])
                if ref_num < first_month_num and (
                    i + 1 >= len(all_button_refs) or int(all_button_refs[i + 1][1:]) >= first_month_num
                ):
                    run_ab('click', f'@{ref}')
                    return
        raise ValueError('Could not find back arrow button')
    else:
        # Forward arrow is the button[ref] right after the second month+year
        if len(month_refs) >= 2:
            second_month_ref = month_refs[1]
            all_button_refs = re.findall(r'button \[ref=(e\d+)\]', snapshot)
            second_month_num = int(second_month_ref[1:])
            for ref in all_button_refs:
                ref_num = int(ref[1:])
                # The forward button is the next plain button after the second month's year button
                if ref_num > second_month_num + 1:
                    run_ab('click', f'@{ref}')
                    return
        raise ValueError('Could not find forward arrow button')


def click_day_cell(calendar_index: int, day: int) -> None:
    """Click a specific day in the left (0) or right (1) calendar grid.

    Uses JS to find calendar body tables and click the matching day button.
    calendar_index: 0 = left calendar, 1 = right calendar.
    """
    ab_eval(f"""(() => {{
        const tables = document.querySelectorAll('table');
        const calTables = [];
        tables.forEach(t => {{
            const ths = Array.from(t.querySelectorAll('th')).map(h => h.textContent.trim());
            if (ths.includes('Sun') && ths.includes('Mon')) calTables.push(t);
        }});
        if (calTables.length < {calendar_index + 1}) return 'no calendar table';
        const table = calTables[{calendar_index}];
        const cells = table.querySelectorAll('.akam-calendar-body-cell-content');
        for (const cell of cells) {{
            if (cell.textContent.trim() === '{day}') {{
                cell.click();
                return 'clicked {day}';
            }}
        }}
        return 'day {day} not found';
    }})()""")


def set_date_range(start_date: str, end_date: str) -> None:
    """Set date range on Akamai calendar.

    Assumes the calendar/filter panel is already open (it opens by default).

    Args:
        start_date: "2026-01-25"
        end_date: "2026-01-31"
    """
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    start_month_str = start_dt.strftime('%B %Y')
    end_month_str = end_dt.strftime('%B %Y')

    # Navigate to start month
    current = get_displayed_months()
    clicks = calculate_nav_clicks(current, start_month_str)

    direction = 'forward' if clicks > 0 else 'back'
    for _ in range(abs(clicks)):
        click_calendar_arrow(direction)
        time.sleep(0.5)

    # Click start day - determine which calendar panel it's in
    current = get_displayed_months()
    left_year, left_month = _parse_month_str(current['left'])
    if left_year == start_dt.year and left_month == start_dt.month:
        click_day_cell(0, start_dt.day)
    else:
        click_day_cell(1, start_dt.day)

    time.sleep(0.5)

    # Navigate to end month if different
    if end_month_str != start_month_str:
        current = get_displayed_months()
        clicks = calculate_nav_clicks(current, end_month_str)
        direction = 'forward' if clicks > 0 else 'back'
        for _ in range(abs(clicks)):
            click_calendar_arrow(direction)
            time.sleep(0.5)

    # Click end day
    current = get_displayed_months()
    left_year, left_month = _parse_month_str(current['left'])
    if left_year == end_dt.year and left_month == end_dt.month:
        click_day_cell(0, end_dt.day)
    else:
        click_day_cell(1, end_dt.day)

    time.sleep(0.5)
