"""Integration tests using local mock site + agent-browser.

Run with: uv run pytest tests/test_mock_integration.py -v
Requires: agent-browser binary available on PATH or configured in settings.yaml.
"""

import json
import time

import pytest

from scripts.browser_helpers import ab_eval, run_ab
from scripts.calendar_nav import get_displayed_months
from scripts.data_extract import bytes_to_tb, extract_geography_table, extract_traffic_cards

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
class TestMockNavigation:
    def test_navigate_hostname(self, mock_browser):
        ab_eval("window.location.hash = '#/predefined/traffic-by-hostname-2'")
        time.sleep(1)
        title = ab_eval("document.querySelector('h2')?.textContent?.trim() || ''")
        assert 'Traffic by Hostname' in title

    def test_navigate_geography(self, mock_browser):
        ab_eval("window.location.hash = '#/predefined/traffic-by-geography'")
        time.sleep(1)
        title = ab_eval("document.querySelector('h2')?.textContent?.trim() || ''")
        assert 'Traffic by Geography' in title


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------
class TestMockDataExtract:
    def test_extract_traffic_cards(self, mock_browser):
        # Default page is hostname with KPI cards
        cards = extract_traffic_cards()
        assert cards['edge'] == {'value': 170.82, 'unit': 'TB'}
        assert cards['origin'] == {'value': 61.25, 'unit': 'TB'}
        assert cards['midgress'] == {'value': 43.89, 'unit': 'GB'}
        assert cards['offload'] == {'value': 64.14, 'unit': '%'}

    def test_extract_geography_table(self, mock_browser):
        ab_eval("window.location.hash = '#/predefined/traffic-by-geography'")
        time.sleep(1)
        geo = extract_geography_table(['ID', 'TW', 'SG'])
        assert geo['ID'] == bytes_to_tb(168_776_644_787_204)
        assert geo['TW'] == bytes_to_tb(31_398_058_511)
        assert geo['SG'] == bytes_to_tb(5_234_567_890)


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------
class TestMockCalendar:
    def test_get_displayed_months(self, mock_browser):
        # Open filter panel first so calendar is visible
        ab_eval("document.querySelector('app-date-range-preview')?.click()")
        run_ab('wait', '#cpcodes-filter-editor')
        months = get_displayed_months()
        assert months['left'] == 'January 2026'
        assert months['right'] == 'February 2026'

    def test_click_day_cell(self, mock_browser):
        ab_eval("document.querySelector('app-date-range-preview')?.click()")
        run_ab('wait', '#cpcodes-filter-editor')
        # Click day 25 in left calendar (January 2026)
        ab_eval("""(() => {
            const tables = document.querySelectorAll('table');
            const calTables = [];
            tables.forEach(t => {
                const ths = Array.from(t.querySelectorAll('th')).map(h => h.textContent.trim());
                if (ths.includes('Sun') && ths.includes('Mon')) calTables.push(t);
            });
            const table = calTables[0];
            const cells = table.querySelectorAll('.akam-calendar-body-cell-content');
            for (const cell of cells) {
                if (cell.textContent.trim() === '25') { cell.click(); break; }
            }
        })()""")
        time.sleep(0.5)
        state = json.loads(ab_eval('window.__mockState'))
        assert '2026-01-25' in state['selectedDates']


# ---------------------------------------------------------------------------
# CP Codes
# ---------------------------------------------------------------------------
class TestMockCpCodes:
    def _open_filter(self):
        ab_eval("document.querySelector('app-date-range-preview')?.click()")
        run_ab('wait', '#cpcodes-filter-editor')

    def test_select_all(self, mock_browser):
        self._open_filter()
        ab_eval("""(() => {
            const editor = document.getElementById('cpcodes-filter-editor');
            const spans = editor.querySelectorAll('span');
            for (const s of spans) {
                if (s.textContent.trim().startsWith('Select:')) { s.click(); break; }
            }
        })()""")
        time.sleep(0.5)
        state = json.loads(ab_eval('window.__mockState'))
        assert sorted(state['selectedCpCodes']) == ['1415558', '1421896', '578716', '960172']

    def test_deselect_all(self, mock_browser):
        self._open_filter()
        # First select all, then deselect
        ab_eval("""(() => {
            const editor = document.getElementById('cpcodes-filter-editor');
            for (const s of editor.querySelectorAll('span')) {
                if (s.textContent.trim().startsWith('Select:')) { s.click(); break; }
            }
        })()""")
        time.sleep(0.3)
        ab_eval("""(() => {
            const editor = document.getElementById('cpcodes-filter-editor');
            for (const s of editor.querySelectorAll('span')) {
                if (s.textContent.trim().startsWith('Deselect:')) { s.click(); break; }
            }
        })()""")
        time.sleep(0.5)
        state = json.loads(ab_eval('window.__mockState'))
        assert state['selectedCpCodes'] == []

    def test_search_and_select(self, mock_browser):
        self._open_filter()
        # Fill search with a code, then click it via scoped selector
        run_ab('fill', "input[placeholder='CP codes']", '960172')
        time.sleep(1)
        run_ab('click', '#cpcodes-filter-editor >> text=(960172)')
        time.sleep(0.5)
        state = json.loads(ab_eval('window.__mockState'))
        assert '960172' in state['selectedCpCodes']


# ---------------------------------------------------------------------------
# Filter flow
# ---------------------------------------------------------------------------
class TestMockFilterFlow:
    def test_open_filter_and_apply(self, mock_browser):
        # Click filter trigger
        ab_eval("document.querySelector('app-date-range-preview')?.click()")
        # Wait for CP codes editor to appear
        run_ab('wait', '#cpcodes-filter-editor')
        # Click Apply
        run_ab('scrollintoview', "button:has-text('Apply')")
        run_ab('click', "button:has-text('Apply')")
        time.sleep(0.5)
        state = json.loads(ab_eval('window.__mockState'))
        assert state['appliedCount'] == 1
