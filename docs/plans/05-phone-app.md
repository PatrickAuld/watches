# Plan 05: Phone App

**Depends on:** Plan 03 (App Infrastructure)
**Blocks:** Plan 06 (End-to-End Integration)
**Parallel with:** Plan 04 (Watch Companion App) — can be developed simultaneously

---

## Intent

The phone app is the personal operator console. It fetches watch face builds from GitHub Releases, presents them for selection, downloads the chosen APK, and transfers it to the watch companion app for installation.

The phone is the right surface for browsing and selection because:
- It has a full-size screen for previewing faces and reading metadata
- It has reliable network access for fetching artifacts
- It's already paired with the watch via Bluetooth
- It avoids putting any network or browsing logic on the resource-constrained watch

---

## Why this design

### GitHub Releases as the artifact source

Plan 02 publishes face APKs and `metadata.json` to GitHub Releases. The phone app consumes these releases via the GitHub API.

For a **public repo**: no auth needed. Release assets are publicly downloadable.
For a **private repo**: a personal access token (PAT) with `repo` scope is needed. For single-user personal deployment, hardcoding the token in the app (or storing it in app preferences on first launch) is acceptable. This is Patrick's app on Patrick's phone accessing Patrick's repo.

### Wear Data Layer for transfer

The phone communicates with the watch companion using:
- **`CapabilityClient`** — discovers whether the watch companion is installed and reachable
- **`ChannelClient`** — streams APK bytes to the watch (large file transfer)
- **`MessageClient`** — sends control messages (install request, status responses)

This is the standard Android Wear communication stack. No Bluetooth sockets, no custom protocols.

### Compose Material 3 for UI

Standard modern Android phone UI. Single-activity, Compose-based. No fragments, no XML layouts.

---

## Module structure

```
apps/phone/
├── build.gradle.kts
└── src/main/
    ├── AndroidManifest.xml
    ├── res/
    │   └── values/strings.xml
    └── java/com/patrickauld/watches/phone/
        ├── MainActivity.kt
        ├── ui/
        │   ├── FaceListScreen.kt
        │   ├── BuildListScreen.kt
        │   └── InstallScreen.kt
        ├── data/
        │   ├── GitHubArtifactSource.kt
        │   └── WatchFaceRepository.kt
        └── sync/
            └── WatchTransfer.kt
```

---

## Changes

### 1. `build.gradle.kts`

```kotlin
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.compose.compiler)
}

android {
    namespace = "com.patrickauld.watches.phone"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.patrickauld.watches.phone"
        minSdk = 30
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    buildFeatures {
        compose = true
    }
}

dependencies {
    implementation(project(":apps:shared"))
    implementation(libs.play.services.wearable)
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.material3)
    implementation(libs.compose.ui.tooling.preview)
    implementation(libs.activity.compose)
    implementation(libs.lifecycle.runtime.compose)
    implementation(libs.lifecycle.viewmodel.compose)
    implementation(libs.core.ktx)
}
```

**Note:** No HTTP client library is listed. The GitHub API can be consumed with `java.net.HttpURLConnection` for this simple use case (list releases, download assets). If that proves awkward, add OkHttp or Ktor later. Avoid adding dependencies speculatively.

### 2. `AndroidManifest.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />

    <application
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/Theme.Material3.DayNight">

        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <meta-data
            android:name="com.google.android.gms.version"
            android:value="@integer/google_play_services_version" />
    </application>
</manifest>
```

### 3. `GitHubArtifactSource.kt`

**Role:** Fetches available watch face builds from GitHub Releases.

**Responsibilities:**
- Lists releases from `PatrickAuld/watches` via GitHub REST API (`GET /repos/{owner}/{repo}/releases`)
- Parses release assets to find `metadata.json` and APK files
- Downloads `metadata.json` for each release to build a catalog
- Downloads APK assets on demand (when user selects "install")
- Handles auth (PAT header) for private repos

**Data model:**
```kotlin
data class AvailableBuild(
    val slug: String,
    val name: String,
    val commitSha: String,
    val buildType: String,
    val versionName: String,
    val versionCode: Int,
    val timestamp: String,
    val apkDownloadUrl: String,
    val releaseTag: String
)
```

**Caching strategy:**
- Cache the release list in memory for the session
- Cache downloaded APKs on disk (app-internal storage)
- Pull-to-refresh to update the release list
- No background sync — this is a manual, on-demand workflow

### 4. `WatchFaceRepository.kt`

**Role:** Manages local state across GitHub data and watch install state.

**Responsibilities:**
- Merges available builds (from `GitHubArtifactSource`) with installed state (from watch status messages)
- Provides UI state per face: `not_installed`, `installed`, `update_available`
- Tracks downloaded APK file paths for transfer
- Persists installed face state to SharedPreferences (updated when watch reports status)

### 5. `WatchTransfer.kt`

**Role:** Sends APK files to the watch companion and handles responses.

**Responsibilities:**
- Discovers watch companion via `CapabilityClient.getCapability(CAPABILITY_WATCH_COMPANION)`
- Opens a `ChannelClient` channel on `CHANNEL_WATCHFACE_APK` path
- Streams APK bytes through the channel's `OutputStream`
- After transfer completes, sends install request via `MessageClient` on `MESSAGE_REQUEST_INSTALL`
- Listens for status response on `MESSAGE_INSTALL_STATUS`
- Reports progress and result back to the UI layer

**Error handling:**
- Watch not found → show "Watch companion not installed" with instructions
- Transfer interrupted → show retry option
- Install failed on watch → show error message from watch

### 6. UI Screens

**`FaceListScreen.kt`** — Main screen
- Lists available face slugs (derived from releases)
- Per face: name, latest version, install state badge
- Tap to navigate to build list

**`BuildListScreen.kt`** — Per-face build history
- Lists available builds for a selected face (from releases)
- Per build: version, commit SHA (short), timestamp, build type
- "Install" or "Update" button per build
- Currently installed version highlighted

**`InstallScreen.kt`** — Transfer and install progress
- Shows phases: downloading APK → transferring to watch → installing → done
- Progress indicator for download and transfer
- Success/failure result from watch
- "Set as active" button on success

### 7. Update `settings.gradle.kts`

Add:
```kotlin
include(":apps:phone")
```

---

## UX flow

```
App opens
  └─▶ FaceListScreen
       │  (fetches releases from GitHub)
       │  Shows: Sundial [installed v0.1.0] [update available]
       │
       └─▶ tap face ──▶ BuildListScreen
            │  Shows: build #42 (v0.1.0, abc123, 2026-03-17)
            │         build #41 (v0.1.0, def456, 2026-03-16)
            │
            └─▶ tap "Install" ──▶ InstallScreen
                 │  Downloading APK...  ✓
                 │  Transferring to watch...  ✓
                 │  Installing on watch...  ✓
                 │  [Set as active]
                 │
                 └─▶ done ──▶ back to FaceListScreen
                      (state updated: Sundial [installed v0.1.0])
```

---

## Verification

```bash
./gradlew :apps:phone:assembleDebug
```

**Expected outcomes:**
- Build succeeds
- APK produced at `apps/phone/build/outputs/apk/debug/`
- APK installs on a phone via `adb install`
- App launches and shows face list (empty if no releases exist yet)
- If releases exist, faces are listed with metadata

**Integration test (requires Plan 04 watch app on paired watch):**
- Phone discovers watch companion
- Select a face build, tap install
- APK downloads from GitHub
- APK transfers to watch
- Watch installs the face
- Phone shows success status
- Face appears in watch face picker

---

## Risks

1. **GitHub API rate limits** — Unauthenticated: 60 requests/hour. Authenticated (PAT): 5000/hour. For personal use with manual refreshes, unauthenticated may suffice for a public repo. Private repos require auth regardless.
2. **APK download size** — WFF v4 XML-only faces are small (< 1 MB). Transfer over Bluetooth is fast. No chunking or resume logic needed.
3. **Watch companion not installed** — The phone app must handle the case where the watch companion isn't installed yet and show a clear message. It should not crash or hang.
4. **Data Layer connectivity** — Bluetooth can be unreliable. The transfer should have a timeout and show clear feedback on failure. Consider a simple retry mechanism.
