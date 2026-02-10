# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
