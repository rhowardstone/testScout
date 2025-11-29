# Changelog

All notable changes to testScout will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Restructured package from `ai_e2e` to `testscout` with modern src layout
- Extracted AI backends into separate `testscout.backends` module
- Improved modularity and separation of concerns

### Added
- Pluggable backend architecture for easier AI provider integration
- Comprehensive documentation and examples
- CLI tool for autonomous exploration
- Enhanced README with feature comparison

## [0.1.0] - 2025-01-XX

### Added
- Initial release of testScout
- Set-of-Marks (SoM) element discovery
- Google Gemini backend support
- OpenAI GPT-4V backend support
- Natural language actions (`scout.action()`)
- AI-powered assertions (`scout.verify()`)
- Visual assertion helpers (`VisualAssertions`)
- Comprehensive context capture (`Context`)
- Autonomous exploration (`Explorer`)
- Console log capture with framework-specific error detection (React, Vue, Angular)
- Network request/failure tracking
- Screenshot deduplication
- pytest integration
- Batch assertion context manager
- Bug severity classification (CRITICAL, HIGH, MEDIUM, LOW, INFO)
- HTML/JSON/text report generation

### Features
- Hybrid DOM + AI vision approach
- Pluggable AI backends
- Smart retry logic for assertions
- Blank page detection for SPAs
- Support for async and sync Playwright usage
- Type hints throughout codebase

[Unreleased]: https://github.com/rhowardstone/testScout/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/rhowardstone/testScout/releases/tag/v0.1.0
