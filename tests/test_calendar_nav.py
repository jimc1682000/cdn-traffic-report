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
