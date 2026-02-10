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
4. Present the results in a formatted table:

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
