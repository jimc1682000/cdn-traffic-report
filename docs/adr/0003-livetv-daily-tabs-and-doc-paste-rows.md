# ADR-0003: LiveTV 改填每日分頁，週報輸出 Sheet / Doc 兩種貼上列

## Status
**Accepted** - 2026-10-27

取代 [ADR-0002](0002-weekly-utc0-all-and-cloudfront-livetv.md) 的 Decision 2、3（LIVETV 週合計欄）。ADR-0002 的 Decision 1（Akamai UTC+0 + `cpcodes=all`）不變。

## Context
### 問題描述
2026-10-27 對照週報 Doc 與流量試算表後發現，ADR-0002 假設的 `LIVETV流量` 週合計欄並不存在：

- 試算表 `weekly` 分頁只有 A:M 13 欄，N 欄起是 BI 欄位。`weekly.csv` 的第 14 欄 `LIVETV流量` 整列貼上會蓋掉 BI 數字
- LiveTV 實際填在 `LiveTV`（÷1024³）與 `LiveTV monthy`（÷1e9 + 7 日均）兩個分頁，每天一列 `date, raw bytes`，週報 Doc 的兩張 LiveTV 圖連結這兩個分頁
- 週報 Doc 的週流量表是 `weekly` 的值複本，少了 年度 / origin / v1，欄名是 `Home流量GB`
- Akamai Traffic by Geography 的資料比 hostname 晚好幾天。2026-10-27 抓 10/18–10/24 時，頁面標示 `Available data ends: October 23, 2026, 6:00 AM (UTC +00:00)`，ID+TW+SG 明顯少於 edge，但數字本身看起來正常

### 業務影響
- 照 `weekly.csv` 貼會覆蓋 BI 欄
- LiveTV 每日列要手算，容易漏日或填錯日期
- 不完整的地區流量會被當成正式數字填進週報

### 技術背景
- LiveTV 分頁在 10/11–10/17 那週填到 10/18（週日），10/18–10/24 那週使用者指定填到 10/25：都是 Akamai 週（日–六）往後一天（一–日）
- CloudFront 日切仍是 UTC+8（`scripts/cloudfront.py`）

## Decision
1. `weekly.csv` 與 Sheet 貼上列只到 `home流量GB`（A:M 13 欄），移除 `LIVETV流量`
2. 完整週報跑完後印出三段 tab 分隔區塊：Sheet `weekly` A:M、Doc 週表 10 欄、LiveTV 分頁 A:B 的每日 `YYYY-MM-DD, raw bytes`
3. 完整週報的 CloudFront 窗改成 Akamai 週各往後一天（`--start + 1` ~ `--end + 1`），可用 `--livetv-start` / `--livetv-end` 覆寫；`--type cloudfront` 仍照給定日期
4. Geography 讀頁面上的 `Available data ends`，早於週末 23:59 UTC 就判定不完整：JSON 保留部分數字與 `data_ends` / `data_complete`，貼上列與 CSV 的 ID/TW/SG 留空。找不到這段文字時保留數字並印警告，避免 UI 改版時默默丟資料

### 設計細節
- `scripts/csv_writer.py`：`SPREADSHEET_COLUMNS` 13 欄、`DOC_COLUMNS`、`livetv_rows`、`format_paste_blocks`；週標籤只看非 CloudFront 的 `date_range`
- `scripts/cloudfront.py`：`livetv_window`
- `scripts/data_extract.py`：`parse_data_ends`、`is_window_complete`、`extract_data_ends`（讀 `document.body.innerText`，不新增 selector）
- 舊的 14 欄 header 會由既有的 `_migrate_legacy_header` 改寫成 13 欄

### 範例
```text
uv run python -m scripts.akamai_report --start 2026-10-18 --end 2026-10-24 \
    --reuse-browser --close-when-done
# [geography] WARNING: data ends 2026-10-23T06:00:00Z, before 2026-10-24 23:59 UTC; ID/TW/SG left blank
# [cloudfront] Fetching CloudFront metrics: 2026-10-19 to 2026-10-25
```

## Alternatives Considered

### 1. 保留 `LIVETV流量` 週合計欄
**優點**：不用改 CSV 格式

**缺點**：試算表沒有這欄，貼上會蓋到 BI 欄；圖表要的是每日資料

**為何不採用**：跟實際試算表不符。

### 2. 腳本直接讀 Sheet 最後填到的日期決定 LiveTV 窗
**優點**：不用推斷「往後一天」的規則

**缺點**：腳本要多一份 Google 憑證與 Sheets 讀取；目前只有兩週的觀察，規則簡單

**為何不採用**：先用可覆寫的預設值，等之後做自動寫入 Sheet 時再一起處理。

### 3. 地區流量不完整時照填並加註
**優點**：Doc 上至少有數字

**缺點**：數字看起來合理，讀者不會發現少了兩天

**為何不採用**：寧可留空等重抓。

## Consequences

### Positive
✅ 貼上列與試算表 / Doc 欄位一一對應，不再蓋到 BI 欄
✅ LiveTV 每日列直接可貼，日期帶年份
✅ 地區流量延遲會被明確標出來

### Negative
⚠️ LiveTV「往後一天」只根據兩週觀察推斷
⚠️ Doc 的兩張連結圖表仍要手動按「更新」：Docs API（revision 20261021）沒有刷新連結圖表的請求

### Mitigation
- `--livetv-start` / `--livetv-end` 可覆寫
- 地區流量留空後，等 Akamai 補完再跑 `--type geography`

## Implementation
- **檔案**: `scripts/csv_writer.py`、`scripts/cloudfront.py`、`scripts/data_extract.py`、`scripts/akamai_report.py`、`tests/mock_site/index.html`
- **測試**: `tests/test_csv_writer.py`、`tests/test_cloudfront.py`、`tests/test_data_extract.py`、`tests/test_mock_integration.py`
- **配置**: 無

## References
- 2026-10-27 週報 Doc 的 CDN 流量區塊
- 流量試算表：`weekly`、`LiveTV`、`LiveTV monthy` 分頁

## Notes
2026-10-27 重抓 10/11–10/17：edge、ID、TW 都比表上小幅上修（晚到資料）；Home 反而比表上少，原因未查明。

---
**Last Updated**: 2026-10-27
**Author**: Jimmy Chen
**Reviewers**:
