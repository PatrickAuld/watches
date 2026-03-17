# Plan 06: End-to-End Integration

**Depends on:** Plan 04 (Watch Companion App), Plan 05 (Phone App)

---

## Intent

Plans 01-05 build the individual pieces. This plan wires them together into the complete flow and addresses the remaining concerns: validation tokens, CI for all app modules, activation UX, update flow, and rollback.

This is where the pipeline becomes real: a commit to a face module triggers a CI build, produces a release, which the phone app discovers, downloads, transfers to the watch, and the watch installs it.

---

## Why a separate integration plan

Each piece (CI, watch app, phone app) can be built and tested somewhat independently. But the end-to-end flow introduces concerns that span all pieces:
- Validation tokens are generated during CI build, embedded in releases, consumed by the watch app
- CI needs to build not just faces but also the phone and watch apps
- Activation UX touches both phone and watch
- Update detection spans GitHub releases, phone state, and watch state

Separating these cross-cutting concerns into their own plan keeps Plans 01-05 focused.

---

## Changes

### 1. Validation token generation

The Watch Face Push API requires a validation token when calling `addWatchFace()`. The token is generated at build time by the `validator-push` library, which validates the face APK against the Watch Face Format spec and produces a signed token.

**New directory:** `buildSrc/`

```
buildSrc/
├── build.gradle.kts
└── src/main/kotlin/
    └── ValidateWatchFaceTask.kt
```

**`buildSrc/build.gradle.kts`:**
```kotlin
plugins {
    `kotlin-dsl`
}

repositories {
    google()
    mavenCentral()
    maven("https://jitpack.io")  // required for validator-push transitive dep
}

dependencies {
    implementation("com.google.android.wearable.watchface.validator:validator-push:1.0.0-alpha08")
    implementation("com.android.tools.build:gradle-api:9.0.0")
}
```

**`ValidateWatchFaceTask.kt`:**
- Custom Gradle task that takes a face APK as input
- Runs the validator-push tool against the APK
- Outputs a validation token file
- Registered as a post-build task on each face module

**Token packaging:**
- The validation token is saved alongside the APK in the build outputs
- CI uploads the token as part of the release assets
- The phone app downloads the token alongside the APK
- The phone transfers the token to the watch alongside the APK
- The watch companion passes the token to `addWatchFace()`

**Shared module update:**
- Add a metadata field to the install request message that includes the token file path
- `DataLayerPaths` may need a second channel for the token, or the token can be embedded in the install request message (it's small)

### 2. CI for all app modules

**File:** `.github/workflows/build-wear.yml`

Extend with additional jobs:

```yaml
build-watch-companion:
  needs: build-sundial  # face APK needed for token generation
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-java@v4
      with:
        distribution: 'temurin'
        java-version: '17'
    - uses: gradle/actions/setup-gradle@v4
    - run: yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses || true
    - run: ./gradlew :apps:watch:assembleDebug
    - uses: actions/upload-artifact@v4
      with:
        name: watch-companion-debug
        path: apps/watch/build/outputs/apk/debug/*.apk
        retention-days: 90

build-phone-app:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-java@v4
      with:
        distribution: 'temurin'
        java-version: '17'
    - uses: gradle/actions/setup-gradle@v4
    - run: yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses || true
    - run: ./gradlew :apps:phone:assembleDebug
    - uses: actions/upload-artifact@v4
      with:
        name: phone-app-debug
        path: apps/phone/build/outputs/apk/debug/*.apk
        retention-days: 90
```

**Updated publish-release job:**
- Downloads all artifacts (face APK, metadata, validation token, watch companion APK, phone APK)
- Creates release with all assets
- Release includes: face APK, metadata.json, validation token, watch companion APK, phone APK

### 3. Activation UX

**Watch companion changes:**
- After successful `addWatchFace()` or `updateWatchFace()`, report the installed package name and version to the phone
- Expose "activate" action in the companion activity
- On activate: call `WatchFacePushManager.setWatchFaceAsActive()`, requires `SET_PUSHED_WATCH_FACE_AS_ACTIVE` permission

**Phone app changes:**
- After successful install, show "Set as active" button on the install result screen
- Tapping sends a `MESSAGE_REQUEST_ACTIVATE` message to the watch
- Watch companion receives it and calls `setActive()`
- Status is reported back

**New shared constant:**
```kotlin
const val MESSAGE_REQUEST_ACTIVATE = "/watchface/request-activate"
```

### 4. Update detection and flow

**Phone app changes to `WatchFaceRepository`:**
- Compare `versionCode` from installed state with `versionCode` from latest release
- If release `versionCode` > installed `versionCode`, mark as `update_available`
- UI shows "Update" button instead of "Install"

**Watch companion changes:**
- `WatchFaceInstaller.update()` calls `updateWatchFace()` instead of `addWatchFace()`
- Reports success/failure back to phone

**Phone install request message:**
- Include `isUpdate: Boolean` flag
- Watch companion routes to `install()` or `update()` accordingly

### 5. Rollback support

**Phone app changes:**
- Keep last 3 downloaded APKs per face in app-internal storage
- Build list screen shows all available builds, not just the latest
- User can select any build to install, even an older one
- Installing an older version uses `updateWatchFace()` (same as an update, just with an older APK)

**Storage management:**
- On new download, if more than 3 APKs exist for a face, delete the oldest
- Total cache size should not exceed a reasonable limit (e.g., 50 MB) — WFF faces are small so this is unlikely to be an issue

### 6. Release signing (future refinement)

For now, all builds use debug signing. When ready for persistent signing:

**GitHub Secrets:**
- `KEYSTORE_BASE64` — base64-encoded keystore file
- `KEYSTORE_PASSWORD` — keystore password
- `KEY_ALIAS` — key alias
- `KEY_PASSWORD` — key password

**CI changes:**
- Decode keystore from secret
- Pass signing config to Gradle
- Build release variants instead of (or in addition to) debug

**Build config changes:**
- Add a `release` signing config that reads from environment variables or a local keystore file

This is not critical for personal sideloading but becomes important if the face APKs need consistent signing across builds.

---

## Verification

### Unit verification
```bash
./gradlew :apps:watch:assembleDebug :apps:phone:assembleDebug :faces:sundial:wear:assembleDebug
```
All three modules build.

### End-to-end verification

1. Push a face change to main
2. CI builds and creates a GitHub Release with APK + metadata + token
3. Install phone app on phone, watch companion on watch
4. Open phone app → face list shows Sundial
5. Tap Sundial → build list shows the latest build
6. Tap "Install" → download starts, transfer completes, install succeeds
7. Tap "Set as active" → watch switches to Sundial face
8. Push another face change → CI creates new release
9. Open phone app → Sundial shows "Update available"
10. Tap "Update" → download, transfer, update succeeds
11. Watch face updates in place

### Rollback verification
12. Navigate to Sundial build list → select an older build
13. Tap "Install" → older version installs successfully
14. Watch face reverts to the older design

---

## Risks

1. **`validator-push` on JitPack** — The validator-push library has a transitive dependency on a JitPack artifact. JitPack availability can be flaky. If it fails in CI, the build should not be blocked — make token generation optional with a clear warning.
2. **Token validity duration** — It's unclear if validation tokens expire. If they do, old releases become unusable. This needs testing.
3. **Watch Face Push API version requirements** — The API may require a minimum Wear OS services version that's newer than what's on the watch. Check the runtime API level and fail gracefully.
4. **Signing identity for updates** — `updateWatchFace()` may require that the new APK is signed with the same key as the original install. If debug signing keys differ between builds (e.g., different CI runner), updates may fail. This is a strong argument for release signing sooner rather than later.
