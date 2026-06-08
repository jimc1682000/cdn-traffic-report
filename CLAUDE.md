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
uv run pytest tests/ -v -m "not integration"
uv run ruff check scripts/ tests/
```

### 2. Integration Tests (改動 selector/擷取邏輯後必跑)

使用本地 mock 站台 + agent-browser 驗證 DOM selector 與 JS 擷取邏輯：

```bash
uv run pytest tests/test_mock_integration.py -v
```

Mock 站台位於 `tests/mock_site/`，精確複製 Akamai SPA 的 DOM 結構。測試透過 `window.__mockState` 追蹤互動狀態。

### 3. Contract Check (定期執行)

連線真實 Akamai 驗證 DOM selector 是否存在：

```bash
uv run python -m scripts.contract_check --headed            # 執行檢查
uv run python -m scripts.contract_check --headed --save     # 存 baseline
uv run python -m scripts.contract_check --headed --diff     # 比對 baseline
```

Baseline 存於 `tests/golden/contract_baseline.json`。

### 4. E2E Test (重大改動後必跑)

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

Akamai session cookies 是 session-only（瀏覽器關閉即失效），無法靠 saved state 還原。
流程：`refresh_session` 登入後**保持瀏覽器開啟**，交給 `akamai_report --reuse-browser` 接手，
全部跑完用 `--close-when-done` 才關。

```bash
uv run python -m scripts.refresh_session          # 預設 1Password op 自動登入（瀏覽器留開）
uv run python -m scripts.refresh_session --force   # 強制重新登入
uv run python -m scripts.refresh_session --manual  # 跳過 op，手動登入（輪詢頁面，非 TTY 也可用）

# 接手跑報表，跑完關瀏覽器
uv run python -m scripts.akamai_report --start <s> --end <e> --reuse-browser --close-when-done
```

- **1Password 自動登入（預設）**：`config/settings.yaml` 的 `onepassword` 區塊填 op item/account
  參照（非 secret）。`op` CLI 讀取帳號/密碼/TOTP 自動填入，secret 不進 log。
- **手動 fallback**：op 不可用/失敗/`--manual` → 開 headed 瀏覽器並輪詢，等你手動登入完成。

## Key Conventions

- Settings are in `config/settings.yaml`, not hardcoded in Python
- Dates are UTC+8 (Taiwan), converted to UTC for CloudWatch API
- Browser automation uses `agent-browser` CLI via subprocess
- Pure logic functions are unit-testable; browser functions require agent-browser
- Use `uv` for dependency management (not pip)
