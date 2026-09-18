# Changelog

## 0.4.0 — 2026-09-18

- Renamed the product, UI, package, build artifacts and documentation to **Lexumi**.
- Changed the macOS bundle identifier to `tech.itroadmaps.lexumi` before App Store distribution.
- Renamed release artifacts to `Lexumi-<version>-macOS-arm64.dmg`.
- Added first-run migration of the existing local library database into `~/Library/Application Support/Lexumi`.
- Removed pre-rebrand screenshots so the repository does not display stale branding.


## 0.3.10 — 2026-09-17

- Replaced the native-looking print combo boxes with Lexumi-styled select controls and a cleaner popup menu/chevron.
- An empty `Custom range` now means all pages instead of showing an error.
- Added open-ended page ranges: `5-` prints page 5 through the end, and `-5` prints the beginning through page 5.
- Two-page and six-page N-up layouts now use landscape/wide sheets in both preview and the default printer orientation.
- One-page and four-page N-up layouts remain portrait.
- Added regression tests for empty/open-ended ranges and the 1/2/4/6 orientation rules.

## 0.3.9 — 2026-09-17

- Rebuilt Print Preview in Lexumi's visual style with the preview canvas on the left and print settings on the right.
- `All pages` now creates a preview for the full document instead of showing only the current page.
- Added `Current page` and live `Custom range` support such as `1-5, 8, 11-13`.
- Added `Pages per sheet` options for 1, 2, 4 and 6 pages with live N-up sheet previews.
- Added `Fit to paper`, `Actual size` and custom percentage scale modes.
- Large documents use lazy print-preview rendering: only nearby sheets are rendered and off-screen preview pixmaps are released.
- Actual printing now respects the selected N-up layout, so 2/4/6-page preview layouts are also sent to the printer that way.
- Kept printer selection, paper size, copies and PDF destination in the native macOS print dialog after the Lexumi preview.
- Added regression tests for custom page ranges and 1/2/4/6-page print grids.

## 0.3.8 — 2026-09-17

- Rebuilt the macOS disk image as a branded installer-style DMG using `dmgbuild`.
- The mounted Lexumi volume now uses the Lexumi application icon instead of the generic disk-image appearance.
- The Finder window opens in icon view with `Lexumi.app` on the left and an `Applications` shortcut on the right.
- Added a built-in drag-to-Applications arrow background and fixed icon positions for a more familiar macOS installation flow.
- Kept the existing versioned DMG filename and SHA-256 release asset naming.

## 0.3.7 — 2026-09-17

- Added an optional two-page spread mode with a dedicated toolbar button and View-menu toggle.
- In two-page mode, `Fit Width` calculates the scale for the whole spread so both pages fit side by side.
- `Fit Height` also keeps both pages visible while respecting page height.
- Left/Up and Right/Down navigation moves by spreads in two-page mode (`1–2 → 3–4 → 5–6`).
- Switching between one-page and two-page layouts preserves the current reading position and reuses already rendered page pixmaps while sharper renders load.
- Added integration coverage for two-page layout pairing, spread-aware fit-width scaling, and spread navigation.

## 0.3.6 — 2026-09-17

- Fixed EPUB 2 cover detection when a book contains both `<meta name="cover">` pointing to an image and a guide `type="cover"` pointing to an XHTML title page.
- Real embedded cover images now take priority over cover-page XHTML wrappers.
- Cover-page XHTML/SVG is parsed for an image when no direct embedded-cover manifest entry is available.
- EPUB thumbnails now always fall back to rendering page 1 when no usable embedded cover can be extracted.
- Added regression tests for the EPUB metadata-vs-guide cover case and the missing-cover fallback path.

## 0.3.5 — 2026-09-17

- Added embedded cover extraction for EPUB books so the library shows the real cover instead of the first laid-out text page.
- Added MOBI/PRC cover detection from embedded PalmDB image records, with a first-page fallback when no usable cover is present.
- Added RAR/CBR comic support using macOS libarchive/bsdtar, including RAR archives that were incorrectly named with a `.cbz` extension.
- RAR-based comics now show `CBR` in the library and use the first comic image as their thumbnail.
- Library thumbnails now begin loading immediately in a dedicated preview worker instead of waiting until each book is opened.
- Reduced library row height, thumbnail size, margins, and spacing so substantially more books fit in the sidebar.
- Added `.cbr` to the file picker path handled by the v0.3.5 UI layer.

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

- macOS release assets now include the Lexumi version in the DMG filename, for example `Lexumi-0.3.2-macOS-arm64.dmg`.
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
- Lexumi print preview step before the native macOS print dialog.
- Standalone Apple Silicon DMG build path and automated GitHub release workflow.
- Open-source contribution, security, issue and release documentation.

### Changed
- Application UI is English-only.
- DjVu → PDF export now uses DjVuLibre native multi-page PDF generation in one pass at 160 DPI / quality 80 instead of per-page PNG embedding.

### Removed
- `Install.command` end-user installation flow. Releases are distributed as DMG files.
