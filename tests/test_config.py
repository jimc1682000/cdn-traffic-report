"""Tests for config module — YAML loading and report type structure."""

import pytest
import yaml

from scripts.config import _SETTINGS_FILE, CLOUDFRONT_CONFIG, REPORT_TYPES, _build_report_types, _validate_cp_codes


def _load_raw_settings():
    """Load raw YAML settings for value-level assertions."""
    with open(_SETTINGS_FILE, encoding='utf-8') as f:
        return yaml.safe_load(f)


def test_settings_yaml_exists():
    """settings.yaml should exist at the expected path."""
    assert _SETTINGS_FILE.exists()


def test_load_settings_yaml():
    """YAML file should be loadable and return a dict."""
    raw = _load_raw_settings()
    assert isinstance(raw, dict)


def test_settings_has_required_keys():
    """Settings must have all top-level keys."""
    raw = _load_raw_settings()
    for key in ['browser', 'akamai_url', 'report_types', 'cloudfront']:
        assert key in raw, f'Missing key: {key}'


def test_report_types_from_yaml():
    """report_types section should produce valid ReportConfig objects."""
    raw = _load_raw_settings()
    types = _build_report_types(raw['report_types'])
    assert len(types) >= 1
    for cfg in types.values():
        assert cfg.label
        assert isinstance(cfg.cp_codes, list)
        assert cfg.unit in ('TB', 'GB')


def test_all_report_types_match_yaml():
    """REPORT_TYPES keys should match YAML report_types keys."""
    raw = _load_raw_settings()
    assert set(REPORT_TYPES.keys()) == set(raw['report_types'].keys())


def test_geography_is_independent_type():
    """geography should be its own report type with geo_countries."""
    assert 'geography' in REPORT_TYPES
    geo = REPORT_TYPES['geography']
    raw = _load_raw_settings()['report_types']['geography']
    assert geo.label == raw['label']
    assert len(geo.geo_countries) > 0
    assert geo.geo_countries == raw['geo_countries']


def test_non_geo_types_no_geo_countries():
    """Non-geography types should have empty geo_countries."""
    for name, config in REPORT_TYPES.items():
        if name != 'geography':
            assert config.geo_countries == [], f'{name} should not have geo_countries'


def test_cloudfront_config_matches_yaml():
    """CloudFront config should match YAML values."""
    raw = _load_raw_settings()['cloudfront']
    assert CLOUDFRONT_CONFIG.distribution_id == raw['distribution_id']
    assert CLOUDFRONT_CONFIG.region == raw['region']


def test_cp_codes_are_digit_strings():
    """All CP codes should be digit strings (except ALL)."""
    for name, config in REPORT_TYPES.items():
        for code in config.cp_codes:
            if code != 'ALL':
                assert code.isdigit(), f'{name}: CP code {code!r} is not a digit string'


def test_valid_units():
    """All report units should be TB or GB."""
    valid_units = {'TB', 'GB'}
    for name, config in REPORT_TYPES.items():
        assert config.unit in valid_units, f'{name}: invalid unit {config.unit!r}'


def test_cp_codes_match_yaml():
    """Each report type's cp_codes should match YAML values."""
    raw = _load_raw_settings()['report_types']
    for name, config in REPORT_TYPES.items():
        assert config.cp_codes == raw[name]['cp_codes'], f'{name} cp_codes mismatch'


def test_labels_match_yaml():
    """Each report type's label should match YAML values."""
    raw = _load_raw_settings()['report_types']
    for name, config in REPORT_TYPES.items():
        assert config.label == raw[name]['label'], f'{name} label mismatch'


def test_validate_cp_codes_rejects_non_numeric():
    with pytest.raises(ValueError, match='Invalid CP code'):
        _validate_cp_codes(['123', 'abc'], 'test')


def test_validate_cp_codes_accepts_all():
    _validate_cp_codes(['ALL'], 'test')  # should not raise


def test_validate_cp_codes_accepts_numeric():
    _validate_cp_codes(['123456', '789012'], 'test')  # should not raise
