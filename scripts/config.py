"""Report type configs and constants, loaded from config/settings.yaml."""

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SETTINGS_FILE = _PROJECT_ROOT / 'config' / 'settings.yaml'


def _load_settings() -> dict:
    """Load settings from YAML config file."""
    with open(_SETTINGS_FILE, encoding='utf-8') as f:
        return yaml.safe_load(f)


_settings = _load_settings()

# Browser settings
AB_BIN = os.path.expandvars(_settings['browser']['ab_bin'])
if not os.environ.get('CDN_SKIP_AB_CHECK') and not Path(AB_BIN).exists() and not shutil.which(AB_BIN):
    raise FileNotFoundError(f'agent-browser binary not found: {AB_BIN}')  # pragma: no cover
SESSION = _settings['browser']['session']
STATE_FILE = str(_PROJECT_ROOT / _settings['browser']['state_file'])
AKAMAI_URL = _settings['akamai_url']


@dataclass
class ReportConfig:
    label: str
    cp_codes: list[str]
    unit: str
    geo_countries: list[str] = field(default_factory=list)


def _validate_cp_codes(cp_codes: list[str], report_name: str) -> None:
    """Validate CP codes are 'ALL' or numeric strings."""
    for code in cp_codes:
        if code != 'ALL' and not code.isdigit():
            raise ValueError(f'Invalid CP code {code!r} in report {report_name!r}: must be numeric or "ALL"')


def _build_report_types(raw: dict) -> dict[str, ReportConfig]:
    """Build ReportConfig dict from raw YAML report_types section."""
    result = {}
    for name, cfg in raw.items():
        cp_codes = cfg['cp_codes']
        _validate_cp_codes(cp_codes, name)
        result[name] = ReportConfig(
            label=cfg['label'],
            cp_codes=cp_codes,
            unit=cfg['unit'],
            geo_countries=cfg.get('geo_countries', []),
        )
    return result


REPORT_TYPES: dict[str, ReportConfig] = _build_report_types(_settings['report_types'])


@dataclass
class CloudFrontConfig:
    distribution_id: str
    region: str
    metric_name: str


CLOUDFRONT_CONFIG = CloudFrontConfig(
    distribution_id=_settings['cloudfront']['distribution_id'],
    region=_settings['cloudfront']['region'],
    metric_name=_settings['cloudfront']['metric_name'],
)
