# Folio — macOS Ebook & Document Reader

**Folio is a free, open-source, offline ebook and document reader for macOS Apple Silicon.** Read **PDF, DjVu, EPUB, FB2, MOBI, XPS, CBZ, TXT and images** in one app with continuous vertical scrolling, search, bookmarks, print preview, zoom controls and PDF export.

[![macOS Apple Silicon](https://img.shields.io/badge/macOS-Apple%20Silicon-000000?logo=apple)](https://github.com/danilfg/folio-macos-ebook-reader/releases/latest)
[![Release](https://img.shields.io/github/v/release/danilfg/folio-macos-ebook-reader)](https://github.com/danilfg/folio-macos-ebook-reader/releases/latest)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![CI](https://github.com/danilfg/folio-macos-ebook-reader/actions/workflows/ci.yml/badge.svg)](https://github.com/danilfg/folio-macos-ebook-reader/actions/workflows/ci.yml)

## Download Folio for macOS

**Apple Silicon (M1, M2, M3, M4 and newer):**

**[Download the latest Folio DMG](https://github.com/danilfg/folio-macos-ebook-reader/releases/latest/download/Folio-macOS-arm64.dmg)**

1. Download `Folio-macOS-arm64.dmg` from GitHub Releases.
2. Open the DMG.
3. Drag **Folio.app** to **Applications**.
4. Open Folio and drop a book into the window.

Folio targets **macOS 14 Sonoma or newer**. Release builds bundle the required DjVu command-line tools, so end users do not need Python, Homebrew or `Install.command`.

> If a release is built without an Apple Developer ID certificate, macOS may show the standard unidentified-developer warning. Right-click Folio → **Open** for that build. Maintainers can enable Developer ID signing and notarization through repository secrets; see [Releasing](docs/RELEASING.md).

## Why Folio

Folio is intended for people who want a lightweight **Mac ebook reader**, **DjVu reader**, **PDF reader** and general-purpose offline document viewer without uploading books to a cloud service.

- **Continuous vertical scrolling** — wheel and trackpad scrolling work through the whole book instead of page-by-page navigation only.
- **Fast lazy rendering** — only visible and nearby pages are rendered, which keeps large textbooks responsive.
- **PDF, DjVu, EPUB, FB2, MOBI and more** in one library.
- **Text search** with page highlighting where the source format exposes text coordinates.
- **Bookmarks and reading position** stored locally.
- **Chrome-style print preview step** before the native macOS print dialog.
- **Zoom controls** in the toolbar and bottom-right reader controls.
- **Export as…** menu, currently with optimized PDF export.
- **Private by design** — no account, no telemetry, no cloud upload.

## Supported formats

| Format | Engine | Notes |
|---|---|---|
| PDF | MuPDF / PyMuPDF | Password-protected PDFs supported; document permissions are respected |
| DjVu / DJV | DjVuLibre | Direct page rendering, hidden-text search, optimized one-pass PDF export |
| EPUB | MuPDF | DRM-free EPUB |
| FB2 / FB2.ZIP | MuPDF | One FB2 file per ZIP |
| MOBI / PRC | MuPDF | Legacy Mobipocket support; no DRM |
| XPS / OXPS | MuPDF | Support depends on the document |
| CBZ | MuPDF | ZIP-based comics |
| TXT | Folio + MuPDF | UTF-8, UTF-16 BOM and Windows-1251 |
| PNG/JPEG/TIFF/BMP/GIF/SVG | MuPDF | Static image viewing |

Not supported: DRM, AZW3/KFX, CHM, CBR/RAR, DOC/DOCX and OCR generation.

## DjVu → PDF export

Folio 0.2 replaced the old page-by-page PNG export path. DjVu export now uses **DjVuLibre's native multi-page PDF output in a single pass**, at 160 DPI with quality 80 compression. This avoids encoding every page to PNG first and is designed to be dramatically faster and smaller for large scanned books.

The exported PDF contains rendered page images. Existing hidden DjVu OCR text is not currently copied into the PDF output.

## Screenshots

Put current application screenshots in [`docs/screenshots/`](docs/screenshots/README.md). Recommended files:

- `reader-light.png` — main continuous reader view
- `reader-dark.png` — dark mode
- `print-preview.png` — print preview
- `export-menu.png` — Export as… menu

Once the first current screenshot is added, place this near the top of the README:

```html
<p align="center"><img src="docs/screenshots/reader-light.png" alt="Folio macOS ebook reader showing a PDF or DjVu book" width="1000"></p>
```

Also upload a 1280×640 project image in **GitHub → Settings → General → Social preview**. That image is used when the repository is shared on social networks and messengers.

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| ⌘O | Open books |
| ⌘⇧O | Add a folder |
| ← / → | Previous / next page |
| ⌘F | Search in the book |
| ⌘D | Add / remove bookmark |
| ⌘P | Print with preview |
| ⌘⇧S | Export as PDF |
| ⌘+ / ⌘- | Zoom in / out |
| ⌘0 | 100% zoom |
| ⌘B | Show / hide sidebar |
| ⌘⇧F | Full screen |

## Build from source

Development dependencies:

```bash
brew install python@3.12 djvulibre
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Run tests (the suite generates its small redistributable fixtures automatically):

```bash
python -m unittest discover -s tests -v
```

Build a standalone Apple Silicon app and DMG:

```bash
pip install pyinstaller==6.16.0
python build_macos.py --dmg --output dist
```

Output:

```text
dist/Folio.app
dist/Folio-macOS-arm64.dmg
```

The build script asks PyInstaller to bundle `ddjvu`, `djvused`, `djvutxt`, `djvudump` and their linked libraries, then verifies that the app does not retain Homebrew library paths.

## Architecture

- `folio/app.py` — PySide6 desktop UI, continuous reader and print preview
- `folio/engine.py` — document engine running in a separate process over JSON Lines
- `folio/storage.py` — local SQLite library, reading position and bookmarks
- `build_macos.py` — Apple Silicon `.app` + DMG release builder
- `.github/workflows/ci.yml` — automated test suite
- `.github/workflows/release.yml` — tag-driven macOS DMG release build

## Privacy

Folio opens local files and stores only library references, reading positions and bookmarks in a local SQLite database. It does not upload books, require an account or contain application telemetry.

Library data on macOS:

```text
~/Library/Application Support/Folio/library.sqlite3
```

## Contributing

Issues and pull requests are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md). For security issues, use [SECURITY.md](SECURITY.md) rather than a public issue.

## License

Folio source code is licensed under **GNU AGPL-3.0-or-later**. See [LICENSE](LICENSE) and [THIRD_PARTY.md](THIRD_PARTY.md) for dependency licensing details.
