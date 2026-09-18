# Validation status — Lexumi 0.2.0

Date: 2026-09-17.

## Verified in the current workspace

- Python syntax compilation succeeds for the modified engine, UI, tests and macOS build script.
- Eight non-Qt reader/storage/worker integration tests pass with PyMuPDF 1.26.7.
- PDF, EPUB, FB2, FB2.ZIP, TXT, CBZ and image render/export paths are covered by those tests.
- Password and permission handling, text encodings, search wrapping and persistent library state are covered.
- The DjVu export implementation has been changed to the documented native `ddjvu -format=pdf` single-pass path.

## Requires macOS / CI validation

- PySide6 UI integration tests (PySide6 is not installed in the execution sandbox used for this revision).
- Real mouse-wheel / trackpad behavior on macOS.
- Apple Silicon PyInstaller bundle creation.
- Bundled DjVuLibre dependency audit on macOS.
- DMG mounting and drag-to-Applications flow.
- Developer ID signing / Apple notarization when credentials are configured.
- Large real-world DjVu export speed and size comparison.

GitHub Actions files are included so these checks can run in the repository on supported hosted runners.
