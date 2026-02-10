"""Tests for calendar_nav module."""

import pytest

from scripts.calendar_nav import _parse_month_str, calculate_nav_clicks


@pytest.mark.parametrize(
    ('current', 'target', 'expected'),
    [
        ({'left': 'Nov 2025', 'right': 'Dec 2025'}, 'Jan 2026', 1),
        ({'left': 'Nov 2025', 'right': 'Dec 2025'}, 'Mar 2026', 3),
        ({'left': 'Feb 2026', 'right': 'Mar 2026'}, 'Jan 2026', -2),
        ({'left': 'Dec 2025', 'right': 'Jan 2026'}, 'Jan 2026', 0),
        ({'left': 'November 2025', 'right': 'December 2025'}, 'January 2026', 1),
        ({'left': 'Jan 2026', 'right': 'Feb 2026'}, 'Dec 2026', 10),
    ],
)
def test_calculate_nav_clicks(current, target, expected):
    assert calculate_nav_clicks(current, target) == expected


def test_parse_month_str_invalid_no_year():
    with pytest.raises(ValueError, match='Cannot parse month string'):
        _parse_month_str('January')


def test_parse_month_str_invalid_month_name():
    with pytest.raises(ValueError, match='Unknown month'):
        _parse_month_str('Smarch 2026')


# ---------------------------------------------------------------------------
# _parse_month_str edge cases
# ---------------------------------------------------------------------------
def test_parse_month_str_empty_string():
    with pytest.raises(ValueError, match='Cannot parse month string'):
        _parse_month_str('')


def test_parse_month_str_three_parts():
    with pytest.raises(ValueError, match='Cannot parse month string'):
        _parse_month_str('Jan 25 2026')


def test_parse_month_str_whitespace_only():
    with pytest.raises(ValueError, match='Cannot parse month string'):
        _parse_month_str('   ')


def test_parse_month_str_non_numeric_year():
    with pytest.raises(ValueError):
        _parse_month_str('Jan abcd')


def test_parse_month_str_abbreviated_match():
    """Abbreviated month names should match (startsWith logic)."""
    year, month = _parse_month_str('Jan 2026')
    assert year == 2026 and month == 1


# ---------------------------------------------------------------------------
# calculate_nav_clicks additional cases
# ---------------------------------------------------------------------------
def test_calculate_nav_clicks_large_backward():
    """Navigate backward across year boundary."""
    current = {'left': 'Jun 2027', 'right': 'Jul 2027'}
    assert calculate_nav_clicks(current, 'Jan 2026') == -18
