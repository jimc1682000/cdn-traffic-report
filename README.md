# CDN Traffic Report

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

### Session 管理

Akamai 使用的 session cookie 會在瀏覽器關閉時失效，執行報表前需先刷新：

```bash
uv run python -m scripts.refresh_session          # 自動偵測有效性
uv run python -m scripts.refresh_session --force   # 強制重新登入
```

### 執行報表

```bash
# 全部報表類型
uv run python -m scripts.akamai_report --start 2026-01-25 --end 2026-01-31

# 單一報表類型（使用 settings.yaml 中定義的類型名稱）
uv run python -m scripts.akamai_report --start 2026-01-25 --end 2026-01-31 --type <type>

# 顯示瀏覽器（除錯用）
uv run python -m scripts.akamai_report --start 2026-01-25 --end 2026-01-31 --headed

# 輸出至指定檔案
uv run python -m scripts.akamai_report --start 2026-01-25 --end 2026-01-31 --output result.json
```

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
    "edge": 170.82,
    "origin": 61.25,
    "midgress": 93.29,
    "offload": 64.14
  },
  "unit": "TB"
}
```

Geography 報表包含國家明細：

```json
{
  "type": "geography",
  "traffic": {},
  "geography": { "CC1": 168.78, "CC2": 27.99, "CC3": 0.03 },
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
