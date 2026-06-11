# ADR-0001: Akamai Session 登入與瀏覽器重用策略

## Status
**Accepted** - 2026-06-11

## Context
### 問題描述
Akamai Control Center 的 session cookies 是 session-only(瀏覽器關閉即失效)。
原本 `refresh_session` 存 state 檔、之後 reopen 還原登入,但 session-only cookie 無法靠
saved state 還原 → reopen 後仍停在 login 頁,`akamai_report` 接著報
`Apply button not found`。

此外手動登入用 `sys.stdin.readline()` 等使用者按 Enter,在非 TTY shell(如 Claude Code
的 `!` 前綴)會立即收到 EOF → 不等待 → 直接判失敗。

### 業務影響
- 週報自動化卡在登入,無法可靠取數
- 手動登入流程在常用的非互動環境直接壞掉

### 技術背景
- 取數走 agent-browser daemon;`--state` 只對 selector/部分 cookie 有用
- repo 既有風格以 subprocess 串接外部 CLI(agent-browser、aws)
- Akamai 帳號有 TOTP(存於 1Password),`op` CLI 可取 OTP

## Decision
採「**登入一次,保持瀏覽器開啟,交由 `akamai_report --reuse-browser` 接手,全部跑完才關**」
的 session 模型。登入支援兩條路:

1. **1Password 自動登入(預設、opt-in)**:`op` CLI 取 username/password/TOTP,驅動登入表單;
   secret 直接 pipe 進瀏覽器、不進 log;欄位以 purpose(USERNAME/PASSWORD/OTP)擷取。
2. **手動 fallback**:輪詢頁面狀態直到登入完成(取代 `stdin.readline()`)。

### 設計細節
- `refresh_session` 不再關瀏覽器;新增 `akamai_report --close-when-done` 在所有報表後關閉
- op 走 4 條件守門:`非 --manual` + 有 `onepassword` config + `enabled: true` + `op` 已安裝;
  任一不符或 op 報錯 → 退手動
- `onepassword` config 僅存 item/account 參照(非 secret),template 預設 `enabled: false`
- TOTP 6 格 `otp-code-0..5`;React 控制的 input 用 native setter + dispatch input event 填入

### 範例
```bash
uv run python -m scripts.refresh_session            # op 自動登入(瀏覽器留開)
uv run python -m scripts.akamai_report --start <s> --end <e> --reuse-browser --close-when-done
```

## Alternatives Considered

### 1. Saved-state 還原登入(原方案)
**缺點**:session-only cookie 無法還原。
**為何不採用**:實測 reopen 後仍是 login 頁,根本不可行。

### 2. 強制 op / 全自動登入
**優點**:流程最短。
**缺點**:逼所有使用者裝 `op` 並設定 1Password。
**為何不採用**:op 應為 opt-in,需保留手動 fallback,不增加非 op 使用者門檻。

### 3. 手動登入續用 `stdin.readline()`
**缺點**:非 TTY shell 收 EOF 立即失敗。
**為何不採用**:改為輪詢頁面狀態,非互動環境也可用。

## Consequences

### Positive
✅ session 不再因 reopen 失效,取數可靠
✅ 非 TTY 環境(`!` 前綴、pipe)也能完成手動登入
✅ 有 op 者全自動;無 op 者照舊手動,**不強制**

### Negative
⚠️ op 路徑依賴 `op` CLI 安裝 + 1Password 整合(互動式 keyring)
⚠️ reuse-browser 流程需使用者記得 `--close-when-done` 收尾

### Mitigation
- 全面 fallback(任何 op 失敗都退手動)
- README / CLAUDE.md 同步說明流程與旗標

## Implementation
- **檔案**:`scripts/refresh_session.py`、`scripts/akamai_report.py`、`scripts/config.py`
- **測試**:`tests/test_refresh_session.py`(114 unit tests pass);op/browser 屬 side-effect,不單測
- **配置**:`config/settings.yaml` 的 `onepassword` 區塊(template 預設關閉)
- **監控**:登入失敗 print 訊息 + `exit 1`

## References
- PR #14
- commit `6f4e8d3`

## Notes
未來若要 headless / cron 無人值守自動跑,op 的互動式 keyring 不適用,需改用
service account 或其他非互動憑證。

---
**Last Updated**: 2026-06-11
**Author**: Jimmy Chen
**Reviewers**:
