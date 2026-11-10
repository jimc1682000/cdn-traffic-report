---
name: cdn-report
description: Generate traffic reports from Akamai Control Center and AWS CloudFront
arguments: <start_date> <end_date> [type]
---

# CDN Traffic Report

Generate traffic reports from Akamai Control Center and AWS CloudFront.

## Usage

```
/cdn:cdn-report <start_date> <end_date> [type]
```

**Arguments:**
- `start_date` - Start date in YYYY-MM-DD format (required)
- `end_date` - End date in YYYY-MM-DD format (required)
- `type` - Report type name from `config/settings.yaml` (optional, runs all if omitted)

**Examples:**
```
/cdn:cdn-report 2026-01-25 2026-01-31
/cdn:cdn-report 2026-01-25 2026-01-31 geography
/cdn:cdn-report 2026-01-25 2026-01-31 cloudfront
```

## Instructions

1. Parse ARGUMENTS to extract start_date, end_date, and optional type
2. Run the Python script:
   ```bash
   cd $PROJECT_DIR
   uv run python -m scripts.akamai_report --start <start_date> --end <end_date> [--type <type>] [--headed]
   ```
3. Read the output JSON file from `output/report_<start>_<end>.json`
4. Present the results in a formatted table.

**Spreadsheet fill-in (default when the user is filling the weekly sheet):**

Akamai week is UTC+0 + `cpcodes=all` (do not switch to UTC+8, do not subtract home/test). Always include CloudFront. **LiveTV is CloudFront BytesDownloaded daily raw bytes, never Akamai `live`.** A full run fetches CloudFront for the Akamai week shifted one day later (Sun–Sat → Mon–Sun).

A full run prints three tab-separated paste blocks at the end of its log; relay them as-is:

1. Sheet `weekly` A:M (13 columns, insert at row 2). Columns N+ are BI — never add a LIVETV column.
2. Doc weekly table (10 columns: period, edge, ID, TW, SG, v3, Trailer/EPK, live, TVA, Home).
3. Sheet `LiveTV` / `LiveTV monthy` A:B: `YYYY-MM-DD<TAB>raw bytes` per UTC+8 day; columns C/D are formulas to extend.

If the log shows `[geography] WARNING: data ends ...`, ID/TW/SG are blank on purpose: Akamai geo data lags. Tell the user and re-run `--type geography` later. After the sheet is updated, the two linked LiveTV charts in the Doc need 「工具 → 已連結的物件 → 全部更新」.

**For Akamai hostname reports:**

| Metric | Value |
|--------|-------|
| Type | {type} |
| Label | {label} |
| Date Range | {start} ~ {end} |
| Edge | {edge} {unit} |
| Origin | {origin} {unit} |
| Midgress | {midgress} {unit} |
| Offload | {offload} % |

**For geography report:**

| Country | Traffic (TB) |
|---------|-------------|
| {cc} | {value} |
| ... | ... |

**For CloudFront report:**

| Date | Bytes Downloaded |
|------|-----------------|
| MM/DD | {bytes} |
| ... | ... |

## Report Types

Type names are defined in `config/settings.yaml`. Two reserved types:

| Type | Source | Description |
|------|--------|-------------|
| `geography` | Akamai | Traffic by Geography (see config) |
| `cloudfront` | AWS | BytesDownloaded (see config) |

All other types are user-defined and run on Akamai's "Traffic by Hostname" page.
