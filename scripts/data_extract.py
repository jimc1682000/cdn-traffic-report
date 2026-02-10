"""Akamai report data extraction and parsing."""

import json
import re

from scripts.browser_helpers import ab_eval

UNIT_MAP = {
    'Terabytes': 'TB',
    'Gigabytes': 'GB',
    'Megabytes': 'MB',
    'Bytes': 'B',
    '%': '%',
}

UNIT_BYTES = {
    'B': 1,
    'MB': 1e6,
    'GB': 1e9,
    'TB': 1e12,
}


def parse_traffic_value(text: str) -> tuple[float, str]:
    """Parse traffic value string into (number, unit).

    Examples:
        "170.82 Terabytes" -> (170.82, "TB")
        "43.89 Gigabytes"  -> (43.89, "GB")
        "64.14 %"          -> (64.14, "%")
    """
    match = re.match(r'([\d,.]+)\s+(.+)', text.strip())
    if not match:
        raise ValueError(f'Cannot parse traffic value: {text!r}')
    value = float(match.group(1).replace(',', ''))
    raw_unit = match.group(2).strip()
    unit = UNIT_MAP.get(raw_unit, raw_unit)
    return value, unit


def convert_unit(value: float, from_unit: str, to_unit: str) -> float:
    """Convert value between units (TB, GB, MB, B)."""
    if from_unit == to_unit:
        return value
    from_bytes = UNIT_BYTES[from_unit]
    to_bytes = UNIT_BYTES[to_unit]
    return round(value * from_bytes / to_bytes, 2)


def bytes_to_tb(byte_count: int | float) -> float:
    """Convert raw bytes to TB, rounded to 2 decimals."""
    return round(byte_count / 1e12, 2)


def extract_traffic_cards() -> dict:  # pragma: no cover
    """Extract Edge/Origin/Midgress/Offload from Akamai KPI cards via JS.

    Reads from akam-single-kpi elements with .single-kpi__title/value/unit.

    Returns:
        {"edge": {"value": 170.82, "unit": "TB"}, "offload": {"value": 64.14, "unit": "%"}, ...}
    """
    js = """
    (() => {
        const kpis = document.querySelectorAll('akam-single-kpi');
        const result = {};
        for (const k of kpis) {
            const title = k.querySelector('.single-kpi__title');
            const value = k.querySelector('.single-kpi__value');
            const unit = k.querySelector('.single-kpi__unit');
            if (title && value) {
                const label = title.textContent.trim().toLowerCase().replace('edge vs. origin', 'offload');
                result[label] = value.textContent.trim() + ' ' + (unit ? unit.textContent.trim() : '');
            }
        }
        return result;
    })()
    """
    raw = ab_eval(js)
    data = json.loads(raw)
    result = {}
    for key, text in data.items():
        val, unit = parse_traffic_value(text.strip())
        result[key] = {'value': val, 'unit': unit}
    return result


def extract_geography_table(countries: list[str]) -> dict[str, float]:  # pragma: no cover
    """Extract geography data from Traffic by Geography report table.

    The table uses class 'cdk-table akam-table' with columns:
    Country/area | Bytes. Empty separator rows exist between data rows.
    """
    js = """
    (() => {
        const table = document.querySelector('table.cdk-table.akam-table');
        if (!table) return {};
        const data = {};
        table.querySelectorAll('tbody tr').forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 2) {
                const country = cells[0]?.textContent?.trim();
                const bytes_val = cells[1]?.textContent?.trim();
                if (country && bytes_val) data[country] = bytes_val;
            }
        });
        return data;
    })()
    """
    raw = ab_eval(js)
    data = json.loads(raw)
    result = {}
    for country in countries:
        if country in data:
            raw_bytes = int(data[country].replace(',', ''))
            result[country] = bytes_to_tb(raw_bytes)
    return result


def build_report_output(
    report_type: str,
    label: str,
    start_date: str,
    end_date: str,
    traffic: dict,
    unit: str,
    geography: dict | None = None,
) -> dict:
    """Build structured output dict for a report."""
    output = {
        'date_range': {'start': start_date, 'end': end_date},
        'type': report_type,
        'label': label,
        'traffic': traffic,
        'unit': unit,
    }
    if geography:
        output['geography'] = geography
    return output
