# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- ADR-0002: weekly Akamai stays UTC+0 `cpcodes=all`; spreadsheet LIVETV is CloudFront raw bytes
- `weekly.csv` column `LIVETV流量` (sum of CloudFront `daily_bytes`)
- ADR-0003: LiveTV goes into the daily `LiveTV` / `LiveTV monthy` sheet tabs; full runs print paste blocks for the sheet, the weekly Doc table and the LiveTV tabs
- Geography reads Akamai's `Available data ends` note and leaves ID/TW/SG blank when the week is not fully available
- `--livetv-start` / `--livetv-end` to override the CloudFront window of a full run
- pre-commit hook `no-real-report-data` (`scripts/check_real_data.py`): blocks staged lines that repeat real traffic values, CP codes or the distribution id from local untracked data

### Changed
- Skill / README / CLAUDE.md: fill-in output must include CloudFront; do not map LIVETV to Akamai `live`
- Full runs fetch CloudFront for the Akamai week shifted one day later (Mon–Sun)

### Removed
- `weekly.csv` column `LIVETV流量`: the sheet's column N is BI data, so the row now stops at `home流量GB`
- Legacy `.github/workflows/auto-merge.yml` (GITHUB_TOKEN cannot approve PRs; failed check blocked repo-policy automerge)

## [1.1.0] - 2026-02-10

### Added
- GitHub Actions CI workflow with lint, format check, and unit tests
- Codecov integration for test coverage reporting (100% on testable code)
- Mock site (`tests/mock_site/`) for local integration testing without Akamai
- DOM selector contract check (`scripts/contract_check.py`) for detecting Akamai UI changes
- 103 unit tests covering config, data extraction, calendar nav, CloudFront, browser helpers, session refresh, and contract check
- 10 integration tests using local mock Akamai SPA
- Pre-commit hooks with ruff lint + format
- Dependabot for pip and GitHub Actions dependencies

### Changed
- `config.py`: `AB_BIN` path now expands environment variables via `os.path.expandvars()`
- `config.py`: AB_BIN validation can be skipped with `CDN_SKIP_AB_CHECK` env var for CI

## [1.0.0] - 2026-02-09

### Added
- Akamai Control Center browser automation via agent-browser
- CloudFront BytesDownloaded metric extraction via AWS CloudWatch CLI
- Configurable report types in `config/settings.yaml`
- Geography report with country-level traffic breakdown
- Calendar date range selection automation
- CP code filter selection automation
- Session cookie management with `refresh_session.py`
- Claude Code plugin with `/cdn:cdn-report` skill
- Project comparison document (`COMPARISON.md`)
