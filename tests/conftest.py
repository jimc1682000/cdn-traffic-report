"""Shared fixtures for tests."""

import json
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).parent / 'golden'


@pytest.fixture
def golden_cloudfront():
    return json.loads((GOLDEN_DIR / 'cloudfront_daily.json').read_text())


def load_golden_report(report_type: str) -> dict | None:
    """Load golden data for a report type. Returns None if file doesn't exist."""
    path = GOLDEN_DIR / f'report_{report_type}.json'
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_golden_report(report_type: str, data: dict) -> Path:
    """Save golden data for a report type."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    path = GOLDEN_DIR / f'report_{report_type}.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    return path
