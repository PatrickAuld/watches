# Plan 03: App Infrastructure

**Depends on:** Plan 01 (Local Build Stabilization)
**Blocks:** Plan 04 (Watch Companion App), Plan 05 (Phone App)

---

## Intent

The watch companion app and phone app both need Kotlin, Jetpack Compose, the Wear Data Layer, and (for the watch) the Watch Face Push library. Before scaffolding either app, the Gradle build system needs to support these dependencies.

This plan expands the version catalog, creates a shared constants module for Data Layer paths, and prepares `settings.gradle.kts` for the new modules.

---

## Why a separate plan for this

Dependency management and multi-module Gradle configuration are foundational. Getting versions, repositories, and shared modules right before writing app code avoids a class of problems where each app independently declares conflicting versions or duplicates constants.

The shared module is small (a single file of path constants today), but it establishes the pattern: phone and watch apps share a common vocabulary for Data Layer communication. If this vocabulary drifts between apps, messages are silently lost.

---

## Design decisions

### Version catalog over buildscript dependencies

The repo already uses `gradle/libs.versions.toml` for the AGP plugin. Extending it for all dependencies is the modern Gradle convention and gives one place to manage versions.

### Shared module scope

The shared module (`apps/shared/`) contains only Data Layer path constants and capability names. It does not contain:
- UI code (phone and watch UIs are completely different)
- Business logic (each app has its own concerns)
- Serialization models (protocol is simple enough that raw strings suffice)

If the protocol grows, the shared module can expand. But starting minimal avoids the trap of building a shared SDK before the apps exist.

### Repository additions

The `validator-push` library (needed in Plan 06) has a transitive dependency on a JitPack artifact. Rather than adding JitPack to the main repository list now, defer it to Plan 06 when it's actually needed. This plan only adds repositories that are needed for Plans 04-05.

---

## Changes

### 1. Expand version catalog

**File:** `gradle/libs.versions.toml`

```toml
[versions]
androidGradlePlugin = "9.0.0"
kotlin = "2.1.0"
composeBom = "2025.05.00"
wearCompose = "1.5.0"
watchfacePush = "1.0.0-alpha04"
playServicesWearable = "19.0.0"
activityCompose = "1.10.0"
lifecycleRuntime = "2.9.0"
coreKtx = "1.16.0"

[libraries]
compose-bom = { module = "androidx.compose:compose-bom", version.ref = "composeBom" }
compose-ui = { module = "androidx.compose.ui:ui" }
compose-material3 = { module = "androidx.compose.material3:material3" }
compose-ui-tooling-preview = { module = "androidx.compose.ui:ui-tooling-preview" }
wear-compose-material = { module = "androidx.wear.compose:compose-material3", version.ref = "wearCompose" }
wear-compose-foundation = { module = "androidx.wear.compose:compose-foundation", version.ref = "wearCompose" }
watchface-push = { module = "androidx.wear:wear-watchface-push", version.ref = "watchfacePush" }
play-services-wearable = { module = "com.google.android.gms:play-services-wearable", version.ref = "playServicesWearable" }
activity-compose = { module = "androidx.activity:activity-compose", version.ref = "activityCompose" }
lifecycle-runtime-compose = { module = "androidx.lifecycle:lifecycle-runtime-compose", version.ref = "lifecycleRuntime" }
lifecycle-viewmodel-compose = { module = "androidx.lifecycle:lifecycle-viewmodel-compose", version.ref = "lifecycleRuntime" }
core-ktx = { module = "androidx.core:core-ktx", version.ref = "coreKtx" }

[plugins]
android-application = { id = "com.android.application", version.ref = "androidGradlePlugin" }
android-library = { id = "com.android.library", version.ref = "androidGradlePlugin" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
compose-compiler = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
```

**Version choices:**
- Kotlin 2.1.0 — stable, required for Compose compiler plugin integration
- Compose BOM — pins all Compose library versions consistently
- `wear-watchface-push` alpha04 — latest available alpha (verify before implementation)
- `play-services-wearable` 19.0.0 — provides `ChannelClient`, `MessageClient`, `CapabilityClient`

**Note:** Exact versions should be verified against the latest stable/alpha releases at implementation time. The versions above are based on current knowledge and may need adjustment.

### 2. Create shared module

**New file:** `apps/shared/build.gradle.kts`

```kotlin
plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.patrickauld.watches.shared"
    compileSdk = 36

    defaultConfig {
        minSdk = 30  // lowest common denominator (phone app)
    }
}
```

**New file:** `apps/shared/src/main/AndroidManifest.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest />
```

**New file:** `apps/shared/src/main/java/com/patrickauld/watches/shared/DataLayerPaths.kt`

```kotlin
package com.patrickauld.watches.shared

/**
 * Shared constants for Wear Data Layer communication between phone and watch apps.
 *
 * Both apps must use identical paths for messages and channels to connect.
 * Changing a value here requires rebuilding both apps.
 */
object DataLayerPaths {
    /** ChannelClient path for transferring watch face APK bytes from phone to watch. */
    const val CHANNEL_WATCHFACE_APK = "/watchface/apk"

    /** MessageClient path for install/update status reports from watch to phone. */
    const val MESSAGE_INSTALL_STATUS = "/watchface/install-status"

    /** MessageClient path for install requests from phone to watch. */
    const val MESSAGE_REQUEST_INSTALL = "/watchface/request-install"

    /** Capability name advertised by the watch companion app. */
    const val CAPABILITY_WATCH_COMPANION = "watch_companion"
}
```

### 3. Update `settings.gradle.kts`

**File:** `settings.gradle.kts`

Add:
```kotlin
include(":apps:shared")
```

(The watch and phone app includes are added in Plans 04 and 05 respectively.)

---

## Verification

```bash
./gradlew :apps:shared:assemble
```

**Expected outcome:**
- Shared module compiles
- No dependency resolution errors
- Existing Sundial build still works (`./gradlew :faces:sundial:wear:assembleDebug`)

---

## Risks

1. **Version conflicts** — Adding many new dependencies increases the chance of version conflicts. The Compose BOM mitigates this for Compose libraries. Other libraries should use compatible versions.
2. **`wear-watchface-push` availability** — This is an alpha library. If it's not available in the Google Maven repository at implementation time, the shared module and version catalog can still be set up, and the watch app can stub the dependency.
3. **Kotlin version compatibility** — Kotlin 2.1.0 must be compatible with AGP 9.0.0. This is expected but should be verified.
