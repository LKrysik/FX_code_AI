# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Reorganized test structure to mirror src/ architecture
- Reorganized documentation into logical categories
- Moved historical documents to docs/archive/
- Renamed documentation files for consistency

### Added
- docs/INDEX.md - Complete documentation map
- CONTRIBUTING.md - Contribution guidelines
- CHANGELOG.md - Version history
- tests/fixtures/ - Shared test data
- .claude/instructions.md - AI guidance

### Fixed
- QuestDB Python client integration (v4.0.0+ compatibility)
- Pinned questdb dependency to prevent breaking changes

## [0.2.0] - 2025-10-27

### Added
- Sprint 16: Indicator System Consolidation
- StreamingIndicatorEngine as primary indicator calculation engine
- QuestDB as single source of truth for data persistence
- CLAUDE.md comprehensive development guide

### Changed
- Migrated from CSV to QuestDB for data storage
- Consolidated indicator calculation logic
- Improved memory management patterns

### Deprecated
- CSV-based data storage (use QuestDB)
- Legacy indicator engines (use StreamingIndicatorEngine)

## [0.1.0] - 2025-10-01

### Added
- Initial release
- FastAPI backend with WebSocket support
- Next.js 14 frontend with TypeScript
- QuestDB time-series database integration
- Real-time indicator calculation
- Strategy builder with 4-section pattern
- MEXC exchange integration
- Data collection and backtesting capabilities

---

## Change Categories

- **Added** - New features
- **Changed** - Changes in existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Security vulnerabilities
