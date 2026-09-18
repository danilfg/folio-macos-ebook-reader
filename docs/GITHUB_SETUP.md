# GitHub repository setup

Use these values when creating the public repository.

## Repository

**Name**

```text
lexumi
```

**Description**

```text
Free open-source offline ebook & document reader for macOS Apple Silicon. Read PDF, DjVu, EPUB, FB2, MOBI, XPS, CBZ & images with continuous scrolling, search, bookmarks, print preview and PDF export.
```

**Visibility:** Public

Do not initialize the GitHub repository with a README, `.gitignore`, or license: all three are already included here.

## Topics

Add these repository topics from the **About** panel on the repository home page:

```text
macos
ebook-reader
pdf-reader
djvu
epub
fb2
mobi
apple-silicon
pyside6
pymupdf
open-source
offline
document-viewer
```

## Images

Application screenshots belong in `docs/screenshots/`. See `docs/screenshots/README.md` for filenames and capture guidance.

For the repository social preview, upload a 1280×640 PNG/JPG from **Settings → Social preview → Edit → Upload an image**.

## First push

After creating the empty repository:

```bash
git remote add origin git@github.com:danilfg/lexumi.git
git branch -M main
git push -u origin main
git push origin v0.2.0
```

Pushing the `v0.2.0` tag starts `.github/workflows/release.yml`. The workflow builds the Apple Silicon DMG and publishes it as a GitHub Release.

## Release download

The stable latest-release page is:

```text
https://github.com/danilfg/lexumi/releases/latest
```

Release assets are versioned:

```text
Lexumi-<version>-macOS-arm64.dmg
```

If a DMG is built manually instead, use the same versioned filename and upload it on **Releases → Draft a new release → Attach binaries**.
