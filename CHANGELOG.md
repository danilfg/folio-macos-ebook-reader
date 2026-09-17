# Changelog

## 0.3.3 — 2026-09-17

- Renamed `TOC` to `Contents` and `Marks` to `Bookmarks` for clearer sidebar navigation.
- Replaced rectangular selected-tab styling with a cleaner text + underline treatment.
- Selected books are now clearly highlighted in the library list.
- Added a compact × button to each book row to remove it from the library without opening the context menu.
- Books now open with a single click instead of a double-click.
- Removed the dropdown arrow indicator from the zoom button; the magnifier opens the zoom menu directly.
- `Fit Height` now snaps back to the current page after resizing so the reader does not remain between two pages.
- Bumped the application version to 0.3.3.

## 0.3.2 — 2026-09-17

- macOS release assets now include the Folio version in the DMG filename, for example `Folio-0.3.2-macOS-arm64.dmg`.
- SHA-256 checksum files use the same versioned filename.
- Updated release documentation and download instructions for versioned assets.
- Bumped the application version to 0.3.2.

## 0.3.1 — 2026-09-17

- Reworked the sidebar tabs so short labels fit cleanly in narrow layouts (`Books`, `TOC`, `Marks`).
- Replaced the oversized library preview card with compact book cards that keep a small thumbnail on the left and the title / progress on the right.
- Replaced the zoom combobox with compact toolbar controls: fit-width, fit-height, and a zoom menu button with a clean popup menu.
- Added keyboard page flipping with the arrow keys (Right / Down = next page, Left / Up = previous page).
- Improved zoom responsiveness: existing page images stay visible, rapid zoom changes are debounced, and expensive rerenders only start after the user pauses.
- Bumped the application version to 0.3.1.

All notable changes to Folio are documented here.

## 0.3.0 — 2026-09-17

### Added
- First-page book preview card in the library sidebar.
- Independent background export worker so reading and rendering remain responsive while PDF export runs.
- Modern scrollbar styling without legacy arrow buttons.

### Changed
- Cleaner page navigation controls with spin-box arrows removed and tighter toolbar styling.
- Sidebar tabs use a modern segmented/pill appearance with hover and selected states.
- Toolbar Export button now starts PDF export directly instead of opening a one-item popup menu.
- Zoom preserves the currently rendered page image immediately and refreshes higher-quality pixels in the background, avoiding white-page flashes.
- Version bumped to 0.3.0.

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
- DjVu → PDF export now uses DjVuLibre native multi-page PDF output in a single pass at 160 DPI / quality 80 instead of per-page PNG embedding.
- Version bumped to 0.2.0.

### Removed
- `Install.command` end-user installation flow. Releases are distributed as DMG files.
