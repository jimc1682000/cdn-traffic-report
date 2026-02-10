"""Shared fixtures for tests."""

import json
import time
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread

import pytest

GOLDEN_DIR = Path(__file__).parent / 'golden'
MOCK_SITE_DIR = Path(__file__).parent / 'mock_site'
EMPTY_STATE = MOCK_SITE_DIR / 'empty_state.json'


def pytest_configure(config):
    config.addinivalue_line('markers', 'integration: requires agent-browser binary')


@pytest.fixture(scope='session')
def mock_server():
    """Session-scoped HTTP server serving mock site files."""
    handler = partial(SimpleHTTPRequestHandler, directory=str(MOCK_SITE_DIR))
    server = HTTPServer(('127.0.0.1', 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_address[1]}'
    server.shutdown()


@pytest.fixture
def mock_browser(mock_server):
    """Per-test browser fixture: opens mock site, closes after test."""
    from scripts.browser_helpers import close_browser, init_browser

    init_browser(state_file=str(EMPTY_STATE), url=mock_server, headed=False)
    time.sleep(2)
    yield mock_server
    close_browser()


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
