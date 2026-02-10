# Agents

## cdn-report

Generates CDN traffic reports from Akamai Control Center and AWS CloudFront.

**Skill:** `/cdn:cdn-report`

### Capabilities
- Automates Akamai Control Center browser navigation
- Extracts Traffic by Hostname KPI cards (Edge/Origin/Midgress/Offload)
- Extracts Traffic by Geography table data
- Fetches CloudFront BytesDownloaded via AWS CloudWatch CLI

### Configuration
All settings are in `config/settings.yaml`:
- Browser path and session info
- Akamai report types with CP codes and units
- Geography countries filter
- CloudFront distribution and region
