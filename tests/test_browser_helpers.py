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
