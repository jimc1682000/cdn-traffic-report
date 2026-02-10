"""Tests for browser_helpers module — pure logic and error paths."""

import json
import subprocess

import pytest

from scripts.browser_helpers import REPORT_HASH, get_element_center, navigate_to_report


# ---------------------------------------------------------------------------
# REPORT_HASH
# ---------------------------------------------------------------------------
def test_report_hash_contains_hostname():
    assert 'Traffic by Hostname' in REPORT_HASH


def test_report_hash_contains_geography():
    assert 'Traffic by Geography' in REPORT_HASH


def test_navigate_to_report_invalid_name_raises(mocker):
    """Unknown report name should raise KeyError from REPORT_HASH lookup."""
    mocker.patch('scripts.browser_helpers.ab_eval', return_value='"Some Other Page"')
    with pytest.raises(KeyError):
        navigate_to_report('Traffic by Nonexistent')


# ---------------------------------------------------------------------------
# get_element_center
# ---------------------------------------------------------------------------
def test_get_element_center_null_returns_valueerror(mocker):
    """When JS returns null (element not found), should raise ValueError."""
    mocker.patch('scripts.browser_helpers.ab_eval', return_value='null')
    with pytest.raises(ValueError, match='Element not found'):
        get_element_center("document.querySelector('.missing')")


def test_get_element_center_valid(mocker):
    """Valid bounding rect should return (x, y) tuple."""
    mocker.patch('scripts.browser_helpers.ab_eval', return_value='{"x": 100, "y": 200}')
    x, y = get_element_center("document.querySelector('.btn')")
    assert x == 100
    assert y == 200


def test_get_element_center_invalid_json(mocker):
    """Invalid JSON from ab_eval should raise json.JSONDecodeError."""
    mocker.patch('scripts.browser_helpers.ab_eval', return_value='not json')
    with pytest.raises(json.JSONDecodeError):
        get_element_center("document.querySelector('.btn')")


# ---------------------------------------------------------------------------
# exec_ab timeout
# ---------------------------------------------------------------------------
def test_exec_ab_timeout_propagates(mocker):
    """subprocess.TimeoutExpired should propagate from exec_ab."""
    mocker.patch(
        'scripts.browser_helpers.subprocess.run',
        side_effect=subprocess.TimeoutExpired(cmd='ab', timeout=120),
    )
    from scripts.browser_helpers import exec_ab

    with pytest.raises(subprocess.TimeoutExpired):
        exec_ab('eval', '1+1')


# ---------------------------------------------------------------------------
# exec_ab / run_ab / ab_eval success paths
# ---------------------------------------------------------------------------
def test_exec_ab_returns_stripped_stdout(mocker):
    """exec_ab should return stripped stdout from subprocess."""
    mock_result = mocker.MagicMock()
    mock_result.stdout = '  hello world  '
    mocker.patch('scripts.browser_helpers.subprocess.run', return_value=mock_result)
    from scripts.browser_helpers import exec_ab

    assert exec_ab('test') == 'hello world'


def test_run_ab_delegates_to_exec_ab(mocker):
    """run_ab should delegate to exec_ab with global opts."""
    mocker.patch('scripts.browser_helpers.exec_ab', return_value='result')
    from scripts.browser_helpers import run_ab

    assert run_ab('test') == 'result'


def test_ab_eval_delegates_to_run_ab(mocker):
    """ab_eval should call run_ab with 'eval' + js."""
    mocker.patch('scripts.browser_helpers.run_ab', return_value='42')
    from scripts.browser_helpers import ab_eval

    assert ab_eval('1+1') == '42'
