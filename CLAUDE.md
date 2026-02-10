# CDN Traffic Report

CDN traffic report automation for Akamai Control Center and AWS CloudFront.

## Quick Start

```bash
uv sync
uv run pytest tests/ -v
uv run python -m scripts.akamai_report --start 2026-01-25 --end 2026-01-31 --type <type>
```

## Project Structure

- `config/settings.yaml` — All configuration (CP codes, browser settings, CloudFront)
- `config/settings.yaml.template` — Configuration template with placeholder values
- `scripts/` — Python modules for browser automation and CLI
- `tests/` — pytest tests with golden data in `tests/golden/`
- `profiles/` — Browser state files (gitignored)
- `output/` — Report output files (gitignored)

## Report Types

Report type names are defined in `config/settings.yaml`. Two reserved type names:

- **`geography`** — runs on Akamai "Traffic by Geography" page (requires `geo_countries`)
- **`cloudfront`** — fetches AWS CloudWatch BytesDownloaded (no browser needed)

All other type names are user-defined and run on Akamai "Traffic by Hostname" page.
See `config/settings.yaml.template` for examples.

## Testing Protocol

Any code change that affects report logic, config loading, browser automation, or data extraction **must** pass both layers before considered complete:

### 1. Unit Tests (必跑)

```bash
uv run pytest tests/ -v
uv run ruff check scripts/ tests/
```

### 2. E2E Test (重大改動後必跑)

重大改動包括：修改 `config.py`、`akamai_report.py`、`cpcode_select.py`、`calendar_nav.py`、`data_extract.py`、`browser_helpers.py`、`cloudfront.py`，或 `config/settings.yaml`。

```bash
# 先確認 session 有效
uv run python -m scripts.refresh_session

# 跑全部報表（golden data 日期）
uv run python -m scripts.akamai_report --start 2026-01-25 --end 2026-01-31 --headed
```

#### Golden Data 管理

E2E 驗證基準保存在 `tests/golden/report_*.json`（gitignored，不進 git）。

**產生 golden data：**
```bash
uv run python -m scripts.akamai_report --start 2026-01-25 --end 2026-01-31 --headed --save-golden
```

`--save-golden` 會將每筆報表結果存為 `tests/golden/report_{type}.json`。

**讀取 golden data：** 使用 `tests/conftest.py` 提供的 `load_golden_report(type)` / `save_golden_report(type, data)` 工具函式。

### Session 管理

Akamai session cookies 是 session-only（瀏覽器關閉即失效），需要定期刷新：

```bash
uv run python -m scripts.refresh_session          # 自動檢測有效性
uv run python -m scripts.refresh_session --force   # 強制重新登入
```

## Key Conventions

- Settings are in `config/settings.yaml`, not hardcoded in Python
- Dates are UTC+8 (Taiwan), converted to UTC for CloudWatch API
- Browser automation uses `agent-browser` CLI via subprocess
- Pure logic functions are unit-testable; browser functions require agent-browser
- Use `uv` for dependency management (not pip)
