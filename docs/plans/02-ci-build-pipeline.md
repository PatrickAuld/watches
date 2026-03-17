# Plan 02: CI Build Pipeline

**Depends on:** Plan 01 (Local Build Stabilization)
**Blocks:** Plan 05 (Phone App — needs published artifacts to fetch)

---

## Intent

Once the local build is reliable, GitHub Actions should build watch face modules automatically and publish the results. This plan creates the CI workflow, defines the artifact metadata contract, and establishes durable publication via GitHub Releases.

The phone app (Plan 05) will consume these published artifacts. CI is the bridge between "face module committed to repo" and "face available for installation on the watch."

---

## Why this design

### Why GitHub Actions, not something else?

The repo is already on GitHub. Actions is zero-additional-infrastructure. The prototype site already deploys via Actions. Keeping all CI in one place is simpler.

### Why GitHub Releases for durable publication?

GitHub Actions workflow artifacts expire (default 90 days, max configurable). For a phone app to reliably fetch builds, artifacts need a stable URL that doesn't expire.

Options considered:
- **GitHub Actions artifacts** — Ephemeral. Good for CI validation, not for app consumption.
- **GitHub Releases** — Permanent. Each release has assets with stable download URLs. The GitHub API (or `gh` CLI) can list releases programmatically. For a private repo, a personal access token provides access.
- **GitHub Pages static catalog** — Could work, but adds complexity (maintaining a JSON index, deploying it). More moving parts than Releases.
- **External artifact store** — Unnecessary infrastructure for a personal workflow.

GitHub Releases is the right fit: permanent, API-accessible, requires no additional infrastructure.

### Why metadata alongside the APK?

The phone app needs to know what it's looking at: which face, what version, when it was built, from what commit. Embedding this in a JSON file alongside the APK means the app doesn't need to parse the APK or guess from filenames.

---

## Artifact metadata contract

Each CI build produces a `metadata.json` alongside the APK.

### Schema

```json
{
  "slug": "sundial",
  "name": "Sundial",
  "commitSha": "abc123...",
  "buildType": "debug",
  "versionName": "0.1.0",
  "versionCode": 1,
  "timestamp": "2026-03-17T14:30:00Z",
  "runId": "12345678",
  "runNumber": 42
}
```

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `slug` | string | face directory name | Machine identifier, e.g. `sundial` |
| `name` | string | `face.yaml` or `strings.xml` | Human-readable name |
| `commitSha` | string | `${{ github.sha }}` | Full git commit SHA |
| `buildType` | string | build variant | `debug` or `release` |
| `versionName` | string | `build.gradle.kts` | Semantic version |
| `versionCode` | number | `build.gradle.kts` | Monotonic integer |
| `timestamp` | string | build time | ISO 8601 UTC |
| `runId` | string | `${{ github.run_id }}` | GitHub Actions run ID |
| `runNumber` | number | `${{ github.run_number }}` | Monotonic build number |

**Future extensions** (added in Plan 06):
- `validationToken` — Watch Face Push validation token path
- `signingKeyFingerprint` — for release builds

### Documentation

Create `docs/artifact-metadata-contract.md` with the schema definition, examples, and versioning policy.

---

## Changes

### 1. Create GitHub Actions workflow

**New file:** `.github/workflows/build-wear.yml`

```yaml
name: Build Wear Modules

on:
  push:
    branches: [main]
    paths:
      - 'faces/**/wear/**'
      - 'build.gradle.kts'
      - 'settings.gradle.kts'
      - 'gradle/**'
      - 'gradle.properties'
  pull_request:
    paths:
      - 'faces/**/wear/**'
      - 'build.gradle.kts'
      - 'settings.gradle.kts'
      - 'gradle/**'
  workflow_dispatch:

jobs:
  build-sundial:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'

      - name: Setup Gradle
        uses: gradle/actions/setup-gradle@v4

      - name: Accept Android SDK licenses
        run: yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses || true

      - name: Build Sundial debug APK
        run: ./gradlew :faces:sundial:wear:assembleDebug

      - name: Generate build metadata
        run: |
          APK_DIR=faces/sundial/wear/build/outputs/apk/debug
          cat > "$APK_DIR/metadata.json" << EOF
          {
            "slug": "sundial",
            "name": "Sundial",
            "commitSha": "${{ github.sha }}",
            "buildType": "debug",
            "versionName": "0.1.0",
            "versionCode": 1,
            "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
            "runId": "${{ github.run_id }}",
            "runNumber": ${{ github.run_number }}
          }
          EOF

      - name: Upload Sundial artifact
        uses: actions/upload-artifact@v4
        with:
          name: sundial-debug
          path: |
            faces/sundial/wear/build/outputs/apk/debug/*.apk
            faces/sundial/wear/build/outputs/apk/debug/metadata.json
          retention-days: 90

  publish-release:
    needs: build-sundial
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4

      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: sundial-debug
          path: artifacts/sundial

      - name: Create or update release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TAG="sundial-v0.1.0-build.${{ github.run_number }}"
          gh release create "$TAG" \
            --title "Sundial debug build #${{ github.run_number }}" \
            --notes "Automated debug build from commit ${{ github.sha }}" \
            artifacts/sundial/*.apk \
            artifacts/sundial/metadata.json
```

### Design notes on the workflow

**Why separate jobs for build and publish?** The build job runs on PRs (for validation) and on pushes. The publish job only runs on main pushes. Separating them keeps the logic clean.

**Why not a matrix build?** Today there's only one face (Sundial). A matrix adds complexity for no benefit. When more faces are added, the workflow can be extended with a matrix over face slugs, or each face can have its own job. The pattern is easy to extend.

**Why `workflow_dispatch`?** Manual trigger is useful for debugging CI issues without pushing a commit.

**Metadata generation** is inline shell rather than a separate script. For a handful of fields populated from CI context variables, a script adds unnecessary indirection. If the schema grows significantly, extract to a script.

### 2. Document the metadata contract

**New file:** `docs/artifact-metadata-contract.md`

Contents: the schema table above, plus examples, versioning policy ("fields may be added but not removed"), and notes on how the phone app should consume it.

---

## Verification

1. Push a change to `faces/sundial/wear/` on a branch. Open a PR. Verify the `build-sundial` job runs and succeeds.
2. Merge to main. Verify `publish-release` creates a GitHub Release with the APK and `metadata.json` as assets.
3. Download the release assets. Verify `metadata.json` fields are populated correctly.
4. Verify the APK installs on a watch via ADB (smoke test).

---

## Scaling to multiple faces

When a second face is added (e.g. Atlas), the workflow extends by:
1. Adding a parallel build job (`build-atlas`) or a matrix strategy
2. Updating the publish job to handle multiple face artifacts
3. Each face gets its own release tag namespace (`<slug>-v<version>-build.<n>`)

This doesn't need to be designed now. The single-face pattern is correct and extensible.

---

## Risks

1. **SDK 36 availability on `ubuntu-latest`** — AGP 9.0.0 auto-downloads SDK components, but platform 36 may not be available. If the build fails, add `sdkmanager "platforms;android-36"` before the Gradle step.
2. **GitHub Actions runner image changes** — The `ANDROID_HOME` path and pre-installed tools can change between runner image versions. The `actions/setup-java` and `gradle/actions/setup-gradle` actions abstract most of this.
3. **Release tag uniqueness** — The tag `<slug>-v<version>-build.<run_number>` is unique per workflow run. If `versionName` changes, old releases remain accessible.
