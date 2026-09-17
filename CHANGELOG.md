# Changelog

All notable changes to Folio are documented here.

## 0.2.0 — 2026-09-17

### Added
- Continuous vertical book scrolling with lazy rendering of visible pages.
- Icon-based compact toolbar with hover tooltips.
- Bottom-right zoom controls plus toolbar and View-menu zoom actions.
- Dedicated **Export as…** button/menu; PDF is the first export format.
- Folio print preview step before the native macOS print dialog.
- Standalone Apple Silicon DMG build path and automated GitHub release workflow.
- Open-source contribution, security, issue and release documentation.

### Changed
- Application UI is English-only.
- DjVu → PDF export now uses DjVuLibre native multi-page PDF generation in one pass at 160 DPI / quality 80 instead of per-page PNG embedding.
- Version bumped to 0.2.0.

### Removed
- `Install.command` end-user installation flow. Releases are distributed as DMG files.
