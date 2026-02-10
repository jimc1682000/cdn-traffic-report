"""Tests for refresh_session module — _check_logged_in and _save_state error paths."""

import json

import pytest


# ---------------------------------------------------------------------------
# _check_logged_in — pure URL-matching logic
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ('url', 'expected'),
    [
        ('https://control.akamai.com/apps/reports/', True),
        ('https://control.akamai.com/apps/reports/#/predefined/traffic-by-hostname-2', True),
        ('https://control.akamai.com/apps/auth/login', False),
        ('https://control.akamai.com/login', False),
        ('https://control.akamai.com/apps/auth/', False),
        ('https://control.akamai.com/', True),
    ],
)
def test_check_logged_in(url, expected, mocker):
    mocker.patch('scripts.refresh_session.exec_ab', return_value=f'"{url}"')
    from scripts.refresh_session import _check_logged_in

    assert _check_logged_in() == expected


def test_check_logged_in_empty_url(mocker):
    """Empty URL (edge case) should be treated as logged in (no /auth/ or /login)."""
    mocker.patch('scripts.refresh_session.exec_ab', return_value='""')
    from scripts.refresh_session import _check_logged_in

    assert _check_logged_in() is True


# ---------------------------------------------------------------------------
# _save_state error paths
# ---------------------------------------------------------------------------
def test_save_state_invalid_cookies_json(mocker):
    """Invalid JSON from cookies command should raise JSONDecodeError."""
    mocker.patch('scripts.refresh_session.exec_ab', return_value='not json')
    from scripts.refresh_session import _save_state

    with pytest.raises(json.JSONDecodeError):
        _save_state()


def test_save_state_missing_data_key(mocker, tmp_path):
    """Missing 'data' key should still work (returns empty via .get())."""
    cookies_json = json.dumps({'other': 'stuff'})
    storage_json = json.dumps({'other': 'stuff'})
    mocker.patch('scripts.refresh_session.exec_ab', side_effect=[cookies_json, storage_json])
    mocker.patch('scripts.refresh_session.STATE_FILE', str(tmp_path / 'state.json'))

    from scripts.refresh_session import _save_state

    _save_state()
    state = json.loads((tmp_path / 'state.json').read_text())
    assert state['cookies'] == []
    assert state['origins'][0]['localStorage'] == []
