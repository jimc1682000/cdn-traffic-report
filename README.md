# CDN Traffic Report

[![Tests](https://github.com/jimc1682000/cdn-traffic-report/actions/workflows/test.yml/badge.svg)](https://github.com/jimc1682000/cdn-traffic-report/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/jimc1682000/cdn-traffic-report/graph/badge.svg)](https://codecov.io/gh/jimc1682000/cdn-traffic-report)

自動化 CDN 流量報表工具，從 **Akamai Control Center** 和 **AWS CloudFront** 提取數據。

透過瀏覽器自動化（[agent-browser](https://github.com/nicholasq/agent-browser)）操作 Akamai SPA 儀表板，擷取 KPI 卡片與地理流量表格；同時透過 AWS CloudWatch CLI 取得 CloudFront 指標。

本專案同時是一個 **Claude Code Plugin**，可透過 `/cdn:cdn-report` 技能讓 AI agent 直接調用產出報表。

## 前置需求

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) 套件管理器
- [agent-browser](https://github.com/nicholasq/agent-browser) CLI（Akamai 報表用）
- AWS CLI 並設定 CloudWatch 讀取權限（CloudFront 報表用）
- 具有報表存取權限的 Akamai Control Center 帳號

## 安裝

```bash
git clone <repo-url>
cd cdn-traffic-report
uv sync
```

依範本建立設定檔：

```bash
cp config/settings.yaml.template config/settings.yaml
# 編輯 config/settings.yaml 填入實際值
```

完整設定結構請參閱 `config/settings.yaml.template`。

## 使用方式

### Session 管理（重要）

Akamai session cookies 是 session-only：瀏覽器一關就失效，`agent-browser --state` 也無法還原登入態。
**運作流程：登入一次後保持瀏覽器開著，同 session 內跑報表，全部跑完才關**。

`refresh_session` 會開瀏覽器、登入、**保持開啟**，交給 `akamai_report --reuse-browser` 接手：

```bash
# 1. 登入（預設用 1Password op CLI 自動填帳號/密碼/TOTP；瀏覽器留開）
uv run python -m scripts.refresh_session

# 2. 同 session 跑報表，跑完自動關瀏覽器
uv run python -m scripts.akamai_report --start 2026-05-10 --end 2026-05-16 \
    --reuse-browser --close-when-done
```

登入方式：

- **1Password 自動登入（預設）**：`config/settings.yaml` 的 `onepassword` 區塊填 `op` item/account
  參照（非 secret），`refresh_session` 會用 `op` 讀取帳密+TOTP 自動填入。
- **手動 fallback**：`op` 不可用或 `--manual` 時，開 headed 瀏覽器後**輪詢頁面**直到你手動登入完成
  （不再卡 `stdin`，非 TTY shell 也能用）。
- `--force` 強制重登；`--manual` 跳過 op 走手動。

### 執行報表

```bash
# 全部報表類型（reuse 已登入的 browser daemon）
uv run python -m scripts.akamai_report --start 2026-05-10 --end 2026-05-16 --reuse-browser

# 單一報表類型（settings.yaml 自訂類型名）
uv run python -m scripts.akamai_report --start 2026-05-10 --end 2026-05-16 --reuse-browser --type v3

# 輸出至指定 JSON
uv run python -m scripts.akamai_report --start 2026-05-10 --end 2026-05-16 --reuse-browser --output result.json

# 停用每週 CSV append（預設 append 到 output/weekly.csv）
uv run python -m scripts.akamai_report --start 2026-05-10 --end 2026-05-16 --reuse-browser --weekly-csv ""

# 跑完所有報表後關閉 reuse 的瀏覽器
uv run python -m scripts.akamai_report --start 2026-05-10 --end 2026-05-16 --reuse-browser --close-when-done
```

報表透過 URL hash 直接帶 `cpcodes/start/end/timezone` 參數，跳過原本的 calendar/CP 選擇器 UI，
所以 Akamai UI 改版時影響面較小。

### 每週試算表 CSV

預設執行（不帶 `--type`）會在跑完所有報表後 append 一 row 到 `output/weekly.csv`。
欄位對應人工維護的週流量試算表：

```
年度 | 週期 | edge流量TB | origin流量TB | ID | TW | SG |
v1流量TB | v3流量TB | Trailer/EPK | live流量GB | TVA流量GB | home流量GB
```

來源 report type → 欄位：
- `summary` → edge流量TB, origin流量TB
- `geography` → ID, TW, SG
- `v3` / `trailer` / `tva` / `live` / `home` → 對應欄位（取 edge 值）
- v1 目前固定 0（無對應 CP code）

帶 `--type` 部分執行時不會 append CSV，避免 row 缺欄。

### Claude Code Skill

作為 Claude Code Plugin 使用時，可直接在對話中調用：

```
/cdn:cdn-report 2026-01-25 2026-01-31
/cdn:cdn-report 2026-01-25 2026-01-31 geography
/cdn:cdn-report 2026-01-25 2026-01-31 cloudfront
```

AI agent 會自動執行腳本、讀取 JSON 結果、格式化為表格回傳。

### 報表類型

報表類型名稱在 `config/settings.yaml` 中自訂，兩個保留名稱除外：

| 保留類型 | 來源 | 說明 |
|----------|------|------|
| `geography` | Akamai | 依地理區域的流量分佈（國家明細） |
| `cloudfront` | AWS | 透過 CloudWatch 取得 BytesDownloaded |

其餘類型皆在 Akamai「Traffic by Hostname」頁面執行。

### 輸出格式

報表以 JSON 格式儲存至 `output/`：

```json
{
  "date_range": { "start": "2026-01-25", "end": "2026-01-31" },
  "type": "<type_name>",
  "label": "<label>",
  "traffic": {
    "edge": 12.34,
    "origin": 4.56,
    "midgress": 7.89,
    "offload": 56.78
  },
  "unit": "TB"
}
```

Geography 報表包含國家明細：

```json
{
  "type": "geography",
  "traffic": {},
  "geography": { "CC1": 9.87, "CC2": 2.10, "CC3": 0.03 },
  "unit": "TB"
}
```

## 專案結構

```
.claude-plugin/plugin.json        # Claude Code Plugin 清單
skills/cdn-report/SKILL.md        # Skill 定義（指令、參數、輸出格式）
config/settings.yaml              # 所有設定（gitignored）
config/settings.yaml.template     # 設定範本
scripts/
  akamai_report.py                # 主程式進入點與 CLI
  config.py                       # YAML 設定載入
  browser_helpers.py              # agent-browser 封裝函式
  calendar_nav.py                 # Akamai 日曆日期選擇自動化
  cpcode_select.py                # CP code 篩選器選擇
  data_extract.py                 # KPI 卡片與地理表格資料擷取
  cloudfront.py                   # AWS CloudWatch 指標取得
  refresh_session.py              # Session cookie 管理
  contract_check.py               # DOM selector 合約檢查
tests/                            # pytest 單元測試
  mock_site/                      # 本地 mock Akamai SPA（integration tests）
profiles/                         # 瀏覽器狀態檔（gitignored）
output/                           # 報表輸出檔（gitignored）
```

## 測試

```bash
# 單元測試（排除 integration）
uv run pytest tests/ -v -m "not integration"

# Integration tests（需要 agent-browser）
uv run pytest tests/test_mock_integration.py -v

# Lint
uv run ruff check scripts/ tests/
```

### Contract Check

連線真實 Akamai 驗證 DOM selector 是否仍存在，用於偵測 UI 改版：

```bash
uv run python -m scripts.contract_check --headed            # 執行檢查
uv run python -m scripts.contract_check --headed --save     # 存 baseline
uv run python -m scripts.contract_check --headed --diff     # 比對 baseline
```

## 延伸閱讀

- [與 akamai-reports 的比較](COMPARISON.md) — API 路線 vs 瀏覽器自動化路線

## 授權

[MIT](LICENSE)
