# ADR-0002: 週報 Akamai 用 UTC+0 ALL，LIVETV 用 CloudFront raw bytes

## Status
**Accepted** - 2026-08-24

## Context
### 問題描述
週流量試算表填了近三個月後，新抓的數字偶爾對不上（例如 08/09 edge 120.13 vs 120.68）。排查時出現過幾種互相衝突的假設：

- Akamai 日期窗該用 UTC+8（台灣日曆週）還是 UTC+0（腳本 URL `timezone=Greenwich`）
- summary edge 該不該扣 home（`1982571`）與 test（`1060913`）
- 表上的 LIVETV 被對到 Akamai `live` CP `1065721`（常為 0 / N/A），CloudFront BytesDownloaded 有抓進 JSON 卻沒進填表列

### 業務影響
- 時區或扣 CP 一旦改錯，新列會跟 5–6 月已填、且重抓仍剛好的列斷開
- 填表漏 CloudFront 時，LIVETV 欄會被填成 Akamai live 的 0

### 技術背景
- `scripts/akamai_report.py` 的 URL hash 使用 `timezone=Greenwich`、當天 `T00:00:00Z`–`T23:59:59Z`（UTC+0 日曆週）
- `summary` 的 `cp_codes` 是 `ALL`（帳號 37 個 CP 全選，含 home / test）
- `scripts/cloudfront.py` 把日期當 UTC+8 再轉 UTC 打 CloudWatch，日切是 UTC+8
- `scripts/csv_writer.py` 的週報欄位原本沒有 CloudFront；`live流量GB` 對應 Akamai `live`

## Decision
1. **Akamai 週報維持 UTC+0 + `cpcodes=all`。** 不改成 `Asia/Taipei`，也不從 edge 扣 home / test。
2. **試算表 LIVETV 是 CloudFront `BytesDownloaded` 的 raw bytes**（該週 `daily_bytes` 加總），不是 Akamai `live`。
3. 完整週報（不帶 `--type`）必須把 CloudFront 寫進 `weekly.csv`，填表輸出也要帶日切 raw bytes，避免只列 Akamai 欄位。

### 設計細節
- Akamai：既有 hash（`timezone=Greenwich`）不動
- CloudFront：既有 UTC+8 日切不動（與 Akamai 週窗差 8 小時；LIVETV 欄單獨存在，不跟 Akamai edge 對齊時區）
- `csv_writer` 新增欄 `LIVETV流量`（整數 bytes）。沒跑 cloudfront 時留空白，與 geo 欄相同，避免寫成 0 假裝有抓

### 範例
```text
# 週報（Akamai UTC+0 ALL + CloudFront）
uv run python -m scripts.akamai_report --start 2026-08-09 --end 2026-08-15 \
    --reuse-browser --close-when-done

# LIVETV流量 = sum(cloudfront.daily_bytes)
```

## Alternatives Considered

### 1. 改 Akamai 為 UTC+8（Asia/Taipei）
**優點**：對齊台灣日曆週，也對齊 CloudFront 日切

**缺點**：
- 5–6 月已填列與 UTC+0 ALL 剛好（05/03、05/10、05/24、05/31、06/21、06/28）
- UTC+8 重抓只有 06/07 剛好，其餘週差約 0.2–0.7 TB（8 小時窗，不是 parser 漂）

**為何不採用**：會跟已填歷史斷開。

### 2. edge = ALL − home(`1982571`) − test(`1060913`)
**優點**：08/02 UTC+8 的 125.76 對得上某一格手填

**缺點**：同一規則套不到 08/09 的 120.13；5–6 月剛好的列是未扣的 ALL

**為何不採用**：單週巧合，不是表的定義。

### 3. 把 LIVETV 當成 Akamai `live`（`1065721`）
**優點**：欄位名都有 live

**缺點**：該 CP 近數月多為 0 / N/A；真正要填的是 CloudFront bytes

**為何不採用**：名稱撞車，填表會一直漏 CF。

## Consequences

### Positive
✅ 新週報與 5–6 月歷史同一套 Akamai 規則
✅ LIVETV 有明確來源與單位（CloudFront raw bytes）
✅ 拒絕 UTC+8 / 扣 CP 的理由寫下來，避免下次重查

### Negative
⚠️ Akamai 週窗（UTC+0）與 CloudFront 日切（UTC+8）不一致
⚠️ `live流量GB`（Akamai）與 `LIVETV流量`（CloudFront）兩欄並存，名稱仍接近

### Mitigation
- ADR 與 CLAUDE.md / skill 寫明兩套時區與兩欄差異
- 填表輸出同時給 LIVETV 週合計與逐日 raw bytes

## Implementation
- **檔案**: `docs/adr/0002-weekly-utc0-all-and-cloudfront-livetv.md`、`scripts/csv_writer.py`、`scripts/akamai_report.py`（行為不變，仍跑 cloudfront）、`skills/cdn-report/SKILL.md`、`README.md`、`CLAUDE.md`
- **測試**: `tests/test_csv_writer.py`
- **配置**: 不改 `timezone=Greenwich`；不改 CloudFront UTC+8 轉換

## References
- 2026-08 週報對帳：試算表近三個月 vs UTC+0 ALL 重抓
- `scripts/akamai_report.py` `_build_report_hash`
- `scripts/cloudfront.py` `convert_dates_to_utc` / `aggregate_hourly_to_daily`

## Notes
Akamai KPI 在日期窗套對時與卡上數字一致。對不上的週（例如 07/19、08/09 edge）比較像填表當下資料尚未結完或單格抄錯，不是 selector 系統性偏差。5 月中旬以前的週在 2026-08-24 重抓會因資料過期被 Akamai 打回近兩日窗，不能拿來否定歷史剛好列。

---
**Last Updated**: 2026-08-24
**Author**: Jimmy Chen
**Reviewers**:
