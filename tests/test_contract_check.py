"""Tests for contract_check module — diff logic and selector escaping."""

import json

from scripts.contract_check import CONTRACTS, _check_and_record, diff_baseline


# ---------------------------------------------------------------------------
# _check_and_record
# ---------------------------------------------------------------------------
def test_check_and_record_found(mocker):
    """Selector with enough matches should record found=True."""
    mocker.patch('scripts.contract_check.check_selector', return_value=5)
    results = []
    _check_and_record('akam-single-kpi', 'KPI cards', 'hostname', 4, results)
    assert len(results) == 1
    assert results[0]['found'] is True
    assert results[0]['count'] == 5


def test_check_and_record_missing(mocker):
    """Selector with too few matches should record found=False."""
    mocker.patch('scripts.contract_check.check_selector', return_value=2)
    results = []
    _check_and_record('.single-kpi__title', 'KPI title', 'hostname', 4, results)
    assert results[0]['found'] is False
    assert results[0]['count'] == 2


def test_check_and_record_zero(mocker):
    """Zero matches should record found=False."""
    mocker.patch('scripts.contract_check.check_selector', return_value=0)
    results = []
    _check_and_record('table.missing', 'Missing table', 'geography', 1, results)
    assert results[0]['found'] is False


# ---------------------------------------------------------------------------
# diff_baseline
# ---------------------------------------------------------------------------
def test_diff_baseline_missing_file(tmp_path, mocker):
    """Missing baseline file should return exit code 2."""
    mocker.patch('scripts.contract_check.BASELINE_PATH', tmp_path / 'nonexistent.json')
    exit_code = diff_baseline([])
    assert exit_code == 2


def test_diff_baseline_all_ok(tmp_path, mocker):
    """All selectors still found should return exit code 0."""
    baseline = {
        'timestamp': '2026-02-10T00:00:00',
        'results': [
            {'selector': 'akam-single-kpi', 'page': 'hostname', 'count': 4, 'found': True},
        ],
    }
    baseline_path = tmp_path / 'baseline.json'
    baseline_path.write_text(json.dumps(baseline))
    mocker.patch('scripts.contract_check.BASELINE_PATH', baseline_path)

    results = [{'selector': 'akam-single-kpi', 'description': 'KPI card', 'page': 'hostname', 'count': 4, 'found': True}]
    assert diff_baseline(results) == 0


def test_diff_baseline_broken(tmp_path, mocker):
    """Selector that was found but now missing should return exit code 1."""
    baseline = {
        'timestamp': '2026-02-10T00:00:00',
        'results': [
            {'selector': '.single-kpi__value', 'page': 'hostname', 'count': 4, 'found': True},
        ],
    }
    baseline_path = tmp_path / 'baseline.json'
    baseline_path.write_text(json.dumps(baseline))
    mocker.patch('scripts.contract_check.BASELINE_PATH', baseline_path)

    results = [{'selector': '.single-kpi__value', 'description': 'KPI value', 'page': 'hostname', 'count': 0, 'found': False}]
    assert diff_baseline(results) == 1


def test_diff_baseline_count_decreased(tmp_path, mocker):
    """Decreased count (but still found) should return exit code 0 (warning only)."""
    baseline = {
        'timestamp': '2026-02-10T00:00:00',
        'results': [
            {'selector': '.akam-calendar-body-cell-content', 'page': 'hostname', 'count': 62, 'found': True},
        ],
    }
    baseline_path = tmp_path / 'baseline.json'
    baseline_path.write_text(json.dumps(baseline))
    mocker.patch('scripts.contract_check.BASELINE_PATH', baseline_path)

    results = [
        {'selector': '.akam-calendar-body-cell-content', 'description': 'Calendar cells', 'page': 'hostname', 'count': 30, 'found': True},
    ]
    assert diff_baseline(results) == 0


def test_diff_baseline_new_selector(tmp_path, mocker):
    """New selector not in baseline should return exit code 0."""
    baseline = {
        'timestamp': '2026-02-10T00:00:00',
        'results': [],
    }
    baseline_path = tmp_path / 'baseline.json'
    baseline_path.write_text(json.dumps(baseline))
    mocker.patch('scripts.contract_check.BASELINE_PATH', baseline_path)

    results = [{'selector': '.new-element', 'description': 'New element', 'page': 'hostname', 'count': 3, 'found': True}]
    assert diff_baseline(results) == 0


# ---------------------------------------------------------------------------
# CONTRACTS structure
# ---------------------------------------------------------------------------
def test_contracts_has_expected_pages():
    """CONTRACTS should cover both hostname and geography pages."""
    pages = {c[2] for c in CONTRACTS}
    assert 'hostname' in pages
    assert 'geography' in pages


def test_contracts_all_have_positive_min_count():
    """All expected_min_count values should be > 0."""
    for _sel, _desc, _page, _phase, min_count in CONTRACTS:
        assert min_count > 0
