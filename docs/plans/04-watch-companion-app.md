# Plan 04: Watch Companion App

**Depends on:** Plan 03 (App Infrastructure)
**Blocks:** Plan 06 (End-to-End Integration)
**Parallel with:** Plan 05 (Phone App) — can be developed simultaneously

---

## Intent

The watch companion app is the piece that actually installs watch faces. It runs on the Pixel Watch, receives APK files from the phone via the Wear Data Layer, and calls `WatchFacePushManager` to install, update, remove, or activate watch faces.

Without this app, there is no programmatic path from "APK exists" to "face is installed on the watch." The Watch Face Push API is watch-side only — the phone cannot remotely install a face.

---

## Why this design

### Single-purpose companion, not a bundled marketplace

The original delivery plan considered a marketplace-style app that bundles face APKs as assets. That approach (used in Google's official WatchFacePush sample) works well when faces are known at build time, but it means every face update requires rebuilding and reinstalling the marketplace app.

For a personal deployment where faces evolve frequently, a thin companion that receives APKs dynamically is better:
- New face builds arrive from the phone without touching the watch app
- The watch app only needs to be installed once (and updated rarely)
- The phone is the browsing/selection surface, not the watch

### Minimal UI

The watch companion's primary job is background service work: receive APKs, install them. The UI is secondary — a status screen showing installed faces and connection state. Most interaction happens on the phone.

### WatchFacePushManager isolation

The Push API is alpha and may change. All API calls go through a `WatchFaceInstaller` wrapper class. If the API surface changes, only that class needs updating. The rest of the app works with simple domain concepts: "install this APK", "list installed faces", "activate this face."

---

## Module structure

```
apps/watch/
├── build.gradle.kts
└── src/main/
    ├── AndroidManifest.xml
    ├── res/
    │   ├── values/strings.xml
    │   └── xml/wear.xml          # capability declaration
    └── java/com/patrickauld/watches/companion/
        ├── CompanionActivity.kt
        ├── WatchFaceInstaller.kt
        └── DataLayerListener.kt
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
    namespace = "com.patrickauld.watches.companion"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.patrickauld.watches.companion"
        minSdk = 36
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
    implementation(libs.watchface.push)
    implementation(libs.play.services.wearable)
    implementation(libs.wear.compose.material)
    implementation(libs.wear.compose.foundation)
    implementation(libs.activity.compose)
    implementation(libs.lifecycle.runtime.compose)
    implementation(libs.lifecycle.viewmodel.compose)
    implementation(libs.core.ktx)
}
```

### 2. `AndroidManifest.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-feature android:name="android.hardware.type.watch" />

    <uses-permission android:name="com.google.wear.permission.PUSH_WATCH_FACES" />
    <uses-permission android:name="com.google.wear.permission.SET_PUSHED_WATCH_FACE_AS_ACTIVE" />

    <application
        android:label="@string/app_name"
        android:supportsRtl="true">

        <meta-data
            android:name="com.google.android.wearable.standalone"
            android:value="false" />

        <activity
            android:name=".CompanionActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <service
            android:name=".DataLayerListener"
            android:exported="true">
            <intent-filter>
                <action android:name="com.google.android.gms.wearable.CHANNEL_EVENT" />
                <action android:name="com.google.android.gms.wearable.MESSAGE_RECEIVED" />
                <data
                    android:scheme="wear"
                    android:host="*" />
            </intent-filter>
        </service>

        <meta-data
            android:name="com.google.android.gms.version"
            android:value="@integer/google_play_services_version" />
    </application>
</manifest>
```

### 3. `res/xml/wear.xml`

Capability declaration so the phone app can discover this companion:

```xml
<resources>
    <string-array name="android_wear_capabilities">
        <item>watch_companion</item>
    </string-array>
</resources>
```

### 4. `DataLayerListener.kt`

**Role:** Background service that receives APK data from the phone app.

**Responsibilities:**
- Extends `WearableListenerService`
- Overrides `onChannelOpened()` to receive APK bytes via `ChannelClient`
- Reads the incoming stream, saves APK to app-local storage
- Overrides `onMessageReceived()` for control messages (install request with metadata)
- After receiving APK + metadata, delegates to `WatchFaceInstaller`
- Sends status back to phone via `MessageClient`

**Data flow:**
1. Phone opens a channel on `CHANNEL_WATCHFACE_APK` path
2. Phone streams APK bytes through the channel
3. Listener saves bytes to `context.filesDir/watchfaces/<slug>.apk`
4. Phone sends a message on `MESSAGE_REQUEST_INSTALL` with JSON metadata (slug, packageName, isUpdate)
5. Listener calls `WatchFaceInstaller.install()` or `.update()`
6. Listener sends result back on `MESSAGE_INSTALL_STATUS`

### 5. `WatchFaceInstaller.kt`

**Role:** Wrapper around `WatchFacePushManager`.

**API surface:**
```kotlin
class WatchFaceInstaller(private val context: Context) {

    suspend fun install(apkPath: String, validationToken: String?): Result<Unit>
    suspend fun update(packageName: String, apkPath: String): Result<Unit>
    suspend fun remove(packageName: String): Result<Unit>
    suspend fun setActive(packageName: String): Result<Unit>
    suspend fun listInstalled(): Result<List<InstalledFace>>
}

data class InstalledFace(
    val packageName: String,
    val versionCode: Long,
    val isActive: Boolean
)
```

**Implementation notes:**
- Uses `WatchFacePushManager.createAsync()` to get the manager instance
- `install()` calls `addWatchFace()` with the APK file and optional validation token
- `update()` calls `updateWatchFace()` with the package name and new APK
- `setActive()` calls `setWatchFaceAsActive()`
- All methods return `Result<>` to surface errors without throwing
- Validation tokens may be null initially (Plan 06 adds token generation)

### 6. `CompanionActivity.kt`

**Role:** Minimal Compose UI for status and manual control.

**Screens:**
- **Installed faces list** — shows faces installed via Push API, with version and active state
- **Connection status** — shows whether phone app is reachable
- **Per-face actions** — activate, remove

This is intentionally minimal. The phone is the primary interaction surface.

### 7. Update `settings.gradle.kts`

Add:
```kotlin
include(":apps:watch")
```

---

## Permissions model

The Watch Face Push API requires two runtime permissions:
- `PUSH_WATCH_FACES` — required for `addWatchFace()` and `updateWatchFace()`
- `SET_PUSHED_WATCH_FACE_AS_ACTIVE` — required for `setWatchFaceAsActive()`

The companion activity should request these permissions on first launch. The `DataLayerListener` service should check permissions before attempting install and send a "permission required" status to the phone if they're not granted.

---

## Verification

```bash
./gradlew :apps:watch:assembleDebug
```

**Expected outcomes:**
- Build succeeds
- APK produced at `apps/watch/build/outputs/apk/debug/`
- APK installs on a Pixel Watch via `adb install`
- App appears in the watch launcher
- Capability `watch_companion` is advertised (verifiable from phone-side `CapabilityClient`)

**Integration test (requires paired phone with Plan 05 app):**
- Phone discovers watch companion
- Phone transfers a test APK
- Watch receives and installs the face
- Face appears in the watch face picker

---

## Risks

1. **`wear-watchface-push` API instability** — Alpha library. Method signatures may change. The `WatchFaceInstaller` wrapper limits the blast radius.
2. **Permission UX on watch** — Runtime permission dialogs on Wear OS are small and awkward. Consider requesting permissions immediately on first launch with a clear explanation screen.
3. **Background service limits** — Wear OS has aggressive battery optimization. `WearableListenerService` is exempt from some limits but long operations should complete promptly. APK saves should be streamed, not buffered entirely in memory.
4. **APK storage space** — Watch storage is limited. The companion should delete old APK files after successful installation. Only keep the latest per face.
