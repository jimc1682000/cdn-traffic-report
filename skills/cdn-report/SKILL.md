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

Akamai week is UTC+0 + `cpcodes=all` (do not switch to UTC+8, do not subtract home/test). Always include CloudFront. **LIVETV is CloudFront BytesDownloaded raw bytes, never Akamai `live`.**

Output one paste-ready row matching `weekly.csv` columns, then CloudFront daily raw bytes:

| 年度 | CDN 每周流量TB | edge流量 | origin流量 | ID | TW | SG | v1流量 TB | v3流量 TB | Trailer/EPK | live流量GB | TVA流量GB | home流量GB | LIVETV流量 |
|------|----------------|----------|------------|----|----|----|-----------|-----------|-------------|------------|------------|------------|------------|
| YYYY | MM/DD - MM/DD | … | … | … | … | … | 0 | … | … | … | … | … | sum(daily_bytes) |

CloudFront daily (raw bytes, UTC+8 days):

| Date | Bytes Downloaded |
|------|------------------|
| MM/DD | {bytes} |

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
