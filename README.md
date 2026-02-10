# CDN Traffic Report

Automated CDN traffic reporting tool that extracts data from **Akamai Control Center** and **AWS CloudFront**.

Uses browser automation ([agent-browser](https://github.com/nicholasq/agent-browser)) to navigate Akamai's SPA dashboard, extract KPI cards and geography tables, and fetches CloudFront metrics via AWS CloudWatch CLI.

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- [agent-browser](https://github.com/nicholasq/agent-browser) CLI (for Akamai reports)
- AWS CLI configured with CloudWatch read access (for CloudFront reports)
- An Akamai Control Center account with report access

## Setup

```bash
git clone <repo-url>
cd cdn-traffic-report
uv sync
```

Configure `config/settings.yaml` based on the template:

```bash
cp config/settings.yaml.template config/settings.yaml
# Edit config/settings.yaml with your actual values
```

See `config/settings.yaml.template` for the full configuration structure.

## Usage

### Session Management

Akamai uses session cookies that expire on browser close. Refresh before running reports:

```bash
uv run python -m scripts.refresh_session          # auto-detect validity
uv run python -m scripts.refresh_session --force   # force re-login
```

### Run Reports

```bash
# All report types
uv run python -m scripts.akamai_report --start 2026-01-25 --end 2026-01-31

# Single report type (use type names from your settings.yaml)
uv run python -m scripts.akamai_report --start 2026-01-25 --end 2026-01-31 --type <type>

# With visible browser (for debugging)
uv run python -m scripts.akamai_report --start 2026-01-25 --end 2026-01-31 --headed

# Output to specific file
uv run python -m scripts.akamai_report --start 2026-01-25 --end 2026-01-31 --output result.json
```

### Report Types

Report type names are user-defined in `config/settings.yaml`, except two reserved names:

| Reserved Type | Source | Description |
|---------------|--------|-------------|
| `geography` | Akamai | Traffic by Geography (country breakdown) |
| `cloudfront` | AWS | BytesDownloaded via CloudWatch |

All other types run on Akamai's "Traffic by Hostname" page.

### Output Format

Reports are saved as JSON to `output/`:

```json
{
  "date_range": { "start": "2026-01-25", "end": "2026-01-31" },
  "type": "<type_name>",
  "label": "<label>",
  "traffic": {
    "edge": 170.82,
    "origin": 61.25,
    "midgress": 93.29,
    "offload": 64.14
  },
  "unit": "TB"
}
```

Geography report includes country breakdown:

```json
{
  "type": "geography",
  "traffic": {},
  "geography": { "CC1": 168.78, "CC2": 27.99, "CC3": 0.03 },
  "unit": "TB"
}
```

## Project Structure

```
config/settings.yaml            # All configuration (gitignored)
config/settings.yaml.template   # Configuration template
scripts/
  akamai_report.py              # Main entry point and CLI
  config.py                     # YAML config loader
  browser_helpers.py            # agent-browser wrapper functions
  calendar_nav.py               # Akamai calendar date picker automation
  cpcode_select.py              # CP code filter selection
  data_extract.py               # KPI card and geography table extraction
  cloudfront.py                 # AWS CloudWatch metric fetching
  refresh_session.py            # Session cookie management
tests/                          # pytest unit tests
profiles/                       # Browser state files (gitignored)
output/                         # Report output files (gitignored)
```

## Testing

```bash
# Unit tests
uv run pytest tests/ -v

# Lint
uv run ruff check scripts/ tests/
```

## License

[MIT](LICENSE)
