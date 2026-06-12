---
tech:
  - Python 3.11
  - agent-browser
  - Akamai
  - AWS CloudFront
  - Claude Code Plugin
  - 1Password
  - pytest / codecov
problem:
  - Akamai V2 API 只能取到部分流量指標，但 Control Center 週報需要的多 CP code 彙總、地理流量表、hostname 分類，並沒有穩定對應的 API 端點。
  - 所以改走 browser automation 直接讀 Control Center SPA，再用 URL hash 帶入參數，把對前端操作流程的依賴降到最低。
  - 與直接打 API 的路線取捨，完整比較見 COMPARISON.md（對照 akamai-reports 的 V2 API 版本）。
core:
  - title: SPA 瀏覽器自動化
    desc: Akamai Control Center 是純 SPA、無官方報表 API。以 agent-browser 驅動 Chromium，直接擷取 KPI 卡片與地理流量表格的 DOM 數值，補足 API 拿不到的 UI-only 指標。
  - title: Claude Code Plugin / Skill
    desc: 包裝成 /cdn:cdn-report skill，AI agent 直接調用、跑腳本、讀 JSON、格式化成表格回傳。不只是腳本，是 AI-native、可被 workflow 串接的能力模組。
  - title: 雙層防 UI 改版
    desc: contract_check 對真實 Akamai UI 比對 selector baseline，偵測改版；mock_site 在 CI 用假 SPA 離線驗證 DOM 擷取。改版前先抓到失效，避免靜默產出空值。
extras:
  - title: 1Password TOTP 整合
    desc: 從 op CLI 讀帳密與 TOTP，登入後保持瀏覽器開著維持 session cookie，避免每次重登。
  - title: URL Hash 參數化
    desc: 用 URL hash 帶 cpcodes / start / end / timezone，跳過 calendar 與 CP 選擇器 UI，縮小改版影響面（SPA 自動化的延伸）。
  - title: 週報 CSV 自動化
    desc: 每次完整執行後自動 append 一行到 weekly.csv，欄位對應人工維護的週流量試算表，省去手動抄寫。
cmds:
  - label: "Step 1: Session 登入"
    code: "uv run python -m scripts.refresh_session"
  - label: "Step 2: 產出報表"
    code: "uv run python -m scripts.akamai_report \\\n  --start 2026-05-10 --end 2026-05-16 \\\n  --reuse-browser --close-when-done"
  - label: "Claude Code Skill"
    code: "/cdn:cdn-report 2026-01-25 2026-01-31\n/cdn:cdn-report 2026-01-25 2026-01-31 geography\n/cdn:cdn-report 2026-01-25 2026-01-31 cloudfront"
  - label: "Contract Check"
    code: "uv run python -m scripts.contract_check \\\n  --headed --diff"
---
