# Contributing to Lexumi

Thanks for helping improve Lexumi.

## Before opening a pull request

1. Search existing issues first.
2. Keep UI text in English.
3. Do not add telemetry, cloud upload, DRM circumvention or proprietary book samples.
4. Keep document parsing/rendering in the engine process rather than blocking the Qt UI thread.
5. Add or update tests for behavior changes.

## Development setup

```bash
brew install python@3.12 djvulibre
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py
```

Linux can be used for most tests, but `.app`, signing, notarization and DMG validation require an Apple Silicon Mac.

## Pull requests

Use a focused branch and describe:

- the problem being solved;
- the user-visible behavior before and after;
- formats tested;
- automated tests run;
- macOS version / hardware for UI or packaging changes.

By contributing, you agree that your contribution is provided under the repository's AGPL-3.0-or-later license.
