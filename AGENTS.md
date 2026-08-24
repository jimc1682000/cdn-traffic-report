# Agents

## cdn-report

Generates CDN traffic reports from Akamai Control Center and AWS CloudFront.

**Skill:** `/cdn:cdn-report`

### Capabilities
- Automates Akamai Control Center browser navigation
- Extracts Traffic by Hostname KPI cards (Edge/Origin/Midgress/Offload)
- Extracts Traffic by Geography table data
- Fetches CloudFront BytesDownloaded via AWS CloudWatch CLI
- Weekly spreadsheet row includes LIVETV as CloudFront raw bytes (not Akamai live)

### Configuration
All settings are in `config/settings.yaml`:
- Browser path and session info
- Akamai report types with CP codes and units
- Geography countries filter
- CloudFront distribution and region

Weekly Akamai dates use UTC+0 (`timezone=Greenwich`) and `cpcodes=all`. LIVETV is CloudFront BytesDownloaded raw bytes. See `docs/adr/0002-weekly-utc0-all-and-cloudfront-livetv.md`.
