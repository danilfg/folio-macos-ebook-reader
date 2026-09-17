# Changelog

## 0.3.4 — 2026-09-17

- Restored the reader UI from the last verified v0.3.2 code after the failed v0.3.3 build.
- Renamed the `TOC` tab to `Contents`.
- Reworked sidebar tab selection into a softer rounded pill without a rectangular outline.
- Made the currently opened book visibly highlighted in the library.
- Added a compact `×` button to each library row to remove the entry without deleting the original file.
- Library books now open with a single click.
- Removed the visible dropdown indicator from the zoom magnifier button.
- `Fit Height` now anchors the current page to the viewport instead of leaving the reader between two pages.
- Kept v0.3.4 UX changes in a small compatibility layer on top of the verified reader core.

## 0.3.3 — not released

- This build was not published because CI detected a corrupted non-printable character in `window_ui.py`.

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

### Removed
- `Install.command` end-user installation flow. Releases are distributed as DMG files.
