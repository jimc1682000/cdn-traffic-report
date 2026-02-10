# CDN Traffic Report vs Akamai Reports — 專案比較

兩個專案都是為了取得 Akamai CDN 流量數據並產生報表，但採用完全不同的技術路線。

## 總覽

| 面向 | cdn-traffic-report | akamai-reports |
|------|-------------------|----------------|
| **取數方式** | 瀏覽器自動化 (agent-browser) | Akamai V2 API (EdgeGrid) |
| **CloudFront** | AWS CloudWatch CLI | 無 |
| **地理流量** | 瀏覽器抓取 Akamai Geography 頁面表格 | V2 Emissions API（國家篩選） |
| **認證方式** | Session Cookie（瀏覽器登入） | `.edgerc` EdgeGrid 憑證 |
| **設定格式** | YAML (`settings.yaml`) | JSON (`config.json`) |
| **依賴管理** | uv | pip + requirements-test.txt |
| **使用介面** | Claude Code Skill (`/cdn:cdn-report`) + CLI | 僅 CLI |
| **整合形態** | Claude Code Plugin（可被 AI agent 調用） | 獨立腳本 |
| **任務管理** | 無（直接 CLI） | Taskfile |
| **Python 版本** | 3.11+ | 3.8+ |
| **測試數量** | 49 個 | 153+ 個 |
| **測試覆蓋率** | — | 90%+ |

## Claude Code Plugin 與 AI Agent 整合

cdn-traffic-report 不只是一組腳本，它是一個 **Claude Code Plugin**，設計為可被 AI agent 直接調用的技能。

### Plugin 架構

```
cdn-traffic-report/
├── .claude-plugin/plugin.json    ← Plugin 清單（name: "cdn"）
├── skills/cdn-report/SKILL.md    ← Skill 定義（指令、參數、輸出格式）
├── AGENTS.md                     ← Agent 能力文件
├── CLAUDE.md                     ← 專案指引（含 E2E 測試協議）
└── scripts/                      ← 底層實作
```

### 使用方式差異

| 面向 | cdn-traffic-report | akamai-reports |
|------|-------------------|----------------|
| **人類使用** | `uv run python -m scripts.akamai_report ...` | `python traffic.py ...` |
| **AI agent 使用** | `/cdn:cdn-report 2026-01-25 2026-01-31` | 無（需手動下指令） |
| **輸出消費者** | AI agent 讀取 JSON → 格式化表格呈現 | 人類讀取終端機輸出 |
| **可組合性** | 可被其他 skill/workflow 串接 | 獨立執行 |

### Skill 互動流程

```
使用者: /cdn:cdn-report 2026-01-25 2026-01-31

Claude Code:
  1. 解析 SKILL.md 取得指令模板
  2. 執行 uv run python -m scripts.akamai_report --start ... --end ...
  3. 讀取 output/report_*.json
  4. 依 SKILL.md 定義的格式化規則產出表格
  5. 回傳結構化結果給使用者
```

這代表 cdn-traffic-report 是 **AI-native 工具**：它的設計不僅考慮人類直接執行，更考慮了作為 AI agent 的一個能力模組被自動調用。akamai-reports 則是傳統的 CLI 工具，使用者必須自己跑指令、讀輸出。

## 技術路線比較

### cdn-traffic-report — 瀏覽器自動化 + AI Skill

```
使用者 → /cdn:cdn-report → Claude Code Agent
                            ├── 執行 scripts (agent-browser)
                            │   ├── Akamai Control Center SPA
                            │   │   ├── 操作日曆選日期
                            │   │   ├── 選擇 CP codes
                            │   │   ├── 讀取 KPI 卡片 (DOM)
                            │   │   └── 讀取地理流量表格 (DOM)
                            │   └── AWS CLI → CloudWatch → CloudFront
                            └── 讀取 JSON → 格式化表格 → 回傳使用者
```

**核心特點：**
- **Claude Code Plugin** — AI agent 可直接調用的技能
- 直接操作 Akamai Control Center 網頁 UI
- 需要維護 session cookie（瀏覽器關閉即失效）
- 透過 DOM 解析取得 KPI 數值（edge/origin/midgress/offload）
- 支援 headed 模式可目視除錯
- 同時支援 Akamai + CloudFront 兩個 CDN

**適用情境：**
- 透過 AI agent 對話式產出報表
- 需要從 Akamai UI 取得 API 無法提供的特定數據
- 需要整合多個 CDN（Akamai + CloudFront）的統一報表

### akamai-reports — API 直接呼叫

```
使用者 → CLI → EdgeGrid 認證 → Akamai V2 Traffic API (time5minutes)
                              → Akamai V2 Emissions API (time1day)
                              → 數據聚合 + 計費預估 → 終端機 + JSON
```

**核心特點：**
- 使用 Akamai V2 Reporting API 直接取數
- EdgeGrid 認證（`.edgerc`），無需瀏覽器
- 支援 V1 vs V2 API 數據比較分析
- 內建計費預估（修正係數 1.0）
- Pydantic schema 驗證、並發查詢、斷路器模式

**適用情境：**
- 純 Akamai 環境的自動化週報
- 需要穩定的 CI/CD 排程（無瀏覽器依賴）
- V1 → V2 API 遷移驗證

## 架構差異

| 面向 | cdn-traffic-report | akamai-reports |
|------|-------------------|----------------|
| **數據來源** | DOM 解析（KPI 卡片、表格） | REST API JSON 回應 |
| **穩定性風險** | UI 改版會壞 | API 規格變更會壞 |
| **執行速度** | 慢（瀏覽器啟動 + 頁面渲染） | 快（~10 秒並發查詢） |
| **無人值守** | 困難（session cookie 過期） | 容易（`.edgerc` 長效） |
| **除錯方式** | `--headed` 看瀏覽器操作 | API 回應日誌 |
| **錯誤復原** | 導覽重試 + RuntimeError | 指數退避重試 + 斷路器 |

## 數據範圍比較

| 數據項 | cdn-traffic-report | akamai-reports |
|--------|-------------------|----------------|
| Edge 流量 | DOM KPI 卡片 | V2 Traffic API |
| Origin 流量 | DOM KPI 卡片 | — |
| Midgress 流量 | DOM KPI 卡片 | — |
| Offload % | DOM KPI 卡片 | — |
| 地理流量 | DOM 表格（國家 → 流量） | V2 Emissions API |
| CloudFront | AWS CloudWatch | — |
| 計費預估 | — | 修正係數 × 總流量 |
| V1 vs V2 比較 | — | CSV 比較工具 |

## 工程品質比較

| 面向 | cdn-traffic-report | akamai-reports |
|------|-------------------|----------------|
| **型別檢查** | 基本 type hints | MyPy 靜態檢查 |
| **設定驗證** | YAML 載入時驗證 | Pydantic model |
| **Linting** | ruff | ruff + pre-commit |
| **版本管理** | 無 | git-cliff + commitizen |
| **架構決策紀錄** | 無 | 有（docs/adr/） |
| **CI 流程** | 無 | Taskfile（`task ci`） |
| **程式碼架構** | 功能模組拆分 | 依賴注入 + 斷路器 + 並發 |

## 互補關係

兩個專案互補而非競爭：

| 角色 | cdn-traffic-report | akamai-reports |
|------|-------------------|----------------|
| **定位** | AI-native 技能模組 | 傳統自動化腳本 |
| **強項** | 跨 CDN 整合、UI-only 數據、agent 可調用 | API 穩定、無人值守、計費預估 |
| **弱項** | session 維護、執行速度慢 | 僅 Akamai、無 UI-only 指標 |

理想的工作流：
1. **日常/週報排程** → `akamai-reports`（API 穩定、cron 免維護）
2. **對話式報表查詢** → `cdn-traffic-report`（`/cdn:cdn-report` 讓 AI 代跑）
3. **跨 CDN 整合報表** → `cdn-traffic-report`（涵蓋 Akamai + CloudFront）
4. **深入分析** → 兩者搭配（API 取原始數據，瀏覽器取 UI 儀表板指標）
