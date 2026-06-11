---
tech:
  - Python 3.11
  - agent-browser
  - Akamai
  - AWS CloudFront
  - Claude Code Plugin
  - 1Password
  - pytest / codecov
highlights:
  - title: SPA 瀏覽器自動化
    desc: Akamai Control Center 是純 SPA，無官方 API。以 agent-browser 驅動 Chromium，直接擷取 KPI 卡片與地理流量表格 DOM 數值。
  - title: 1Password TOTP 整合
    desc: 自動從 op CLI 讀取帳密與 TOTP OTP，登入後保持瀏覽器開著讓 session cookie 維持有效，避免每次重新登入。
  - title: Claude Code Plugin
    desc: 包裝成 /cdn:cdn-report skill，AI agent 可直接調用取得 CDN 流量數據，無需手動操作報表介面。
  - title: URL Hash 參數化
    desc: 透過 URL hash 帶入 cpcodes / start / end / timezone，跳過 calendar 與 CP 選擇器 UI，降低 Akamai 前端改版影響面。
  - title: Contract Check
    desc: 跑 contract_check 驗證 DOM selector 是否仍存在，偵測 Akamai UI 改版前的影響範圍，避免靜默失效。
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
