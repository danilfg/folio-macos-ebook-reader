# Releasing Lexumi

Lexumi releases are built from Git tags by `.github/workflows/release.yml` on GitHub's Apple Silicon `macos-14` runner.

## Standard release

1. Update `lexumi/__init__.py` and `CHANGELOG.md`.
2. Merge the release commit to `main`.
3. Create and push a matching tag, for example:

```bash
git tag v0.2.0
git push origin v0.2.0
```

The workflow builds `dist/Lexumi-macOS-arm64.dmg`, creates its SHA-256 file and publishes both files to a GitHub Release automatically.

Users download the versioned DMG from the stable latest-release page:

```text
https://github.com/danilfg/lexumi/releases/latest
```

Release assets are versioned as `Lexumi-<version>-macOS-arm64.dmg`.

## Developer ID signing and notarization

The workflow can also produce a properly signed/notarized build. Configure these GitHub Actions repository secrets:

- `MACOS_CERTIFICATE` — base64-encoded Developer ID Application `.p12`
- `MACOS_CERTIFICATE_PASSWORD` — password for the `.p12`
- `LEXUMI_CODESIGN_IDENTITY` — full Developer ID Application identity used by `codesign`
- `APPLE_ID` — Apple developer account email
- `APPLE_TEAM_ID` — Apple Developer Team ID
- `APPLE_APP_PASSWORD` — app-specific password accepted by `notarytool`

Without those secrets, the workflow still produces an ad-hoc-signed DMG, but Gatekeeper can require the user to right-click the app and choose **Open** on first launch.

## Manual upload alternative

If you build a DMG locally, open the GitHub repository → **Releases** → **Draft a new release**, choose/create a tag and drag `Lexumi-macOS-arm64.dmg` into the **Attach binaries** area. Publish only after the DMG and checksum are attached.
