# Plan 01: Local Build Stabilization

**Depends on:** nothing
**Blocks:** Plan 02 (CI Build Pipeline)

---

## Intent

Before CI can build watch face modules, the local build must work reliably. Today the Sundial WFF v4 module has correct structure but the build environment is underspecified: no `gradle.properties`, a minimal `.gitignore`, and an `applicationId` that doesn't match the Watch Face Push convention.

This plan makes the local build reproducible, aligns the face module with the Watch Face Push contract, and establishes patterns that future face modules will follow.

---

## Why this matters

A CI pipeline that builds Gradle projects is only as reliable as the local build it mirrors. If the local build requires undocumented env vars, manual SDK installs, or implicit assumptions, the CI will be fragile. Getting this right first means CI (Plan 02) can be straightforward.

The `applicationId` change is done here rather than later because:
- It changes the APK identity, which affects everything downstream
- Doing it early avoids a disruptive rename after other systems depend on the current ID
- The Watch Face Push API requires this pattern, so all face APKs must conform before any install testing

---

## Design decisions

### applicationId convention

Watch Face Push requires: `<companion_package>.watchfacepush.<slug>`

The watch companion app (Plan 04) will use `com.patrickauld.watches.companion`. Therefore face APKs use:
```
com.patrickauld.watches.companion.watchfacepush.<slug>
```

For Sundial: `com.patrickauld.watches.companion.watchfacepush.sundial`

The `namespace` (used for R class generation) stays separate from `applicationId`. It can remain `com.patrickauld.watches.sundial` or be updated to match — the choice is cosmetic since `hasCode=false` modules don't generate much code.

### minSdk

The delivery plan targets Pixel Watch on Wear OS 6 (SDK 36). The official Watch Face Push sample uses `minSdk = 33` for face APKs for broader compatibility. Since this is a single-device deployment, keeping `minSdk = 36` is fine and avoids questions about untested configurations.

### Minification

WFF v4 XML-only modules have `hasCode=false`. The `validator-push` tool (used later in Plan 06) expects no DEX files in the APK. Enabling `isMinifyEnabled = true` strips the empty DEX that AGP generates by default. This should be enabled on both debug and release builds.

---

## Changes

### 1. Expand `.gitignore`

**File:** `.gitignore`
**Current contents:** `.gradle/` and `.tools/`

**Add:**
```
local.properties
build/
*.apk
.idea/
*.iml
```

**Why:** `local.properties` contains the developer's `sdk.dir` path (machine-specific). `build/` directories are generated output. IDE files are personal configuration.

### 2. Create `gradle.properties`

**New file:** `gradle.properties`
```properties
org.gradle.jvmargs=-Xmx2g -XX:MaxMetaspaceSize=512m
android.useAndroidX=true
```

**Why:** Without explicit JVM args, Gradle uses conservative defaults that can cause OOM on larger builds. `android.useAndroidX=true` is required by modern AndroidX libraries that the app modules (Plans 04-05) will use. Setting it now avoids a disruptive change later.

### 3. Update Sundial `build.gradle.kts`

**File:** `faces/sundial/wear/build.gradle.kts`

Changes:
- `applicationId` → `com.patrickauld.watches.companion.watchfacepush.sundial`
- `isMinifyEnabled = true` for both debug and release build types

**Updated file should look like:**
```kotlin
plugins {
    alias(libs.plugins.android.application)
}

android {
    enableKotlin = false
    namespace = "com.patrickauld.watches.sundial"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.patrickauld.watches.companion.watchfacepush.sundial"
        minSdk = 36
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        debug {
            isMinifyEnabled = true
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}
```

### 4. Update Sundial `AndroidManifest.xml`

**File:** `faces/sundial/wear/src/main/AndroidManifest.xml`

The manifest uses `package` attribute and metadata. Since `applicationId` is set in `build.gradle.kts`, the manifest `package` attribute is used only for R class generation and doesn't need to change. However, verify that no hardcoded references to the old package name exist.

---

## Verification

```bash
./gradlew :faces:sundial:wear:assembleDebug
```

**Expected outcome:**
- Build succeeds
- APK produced at `faces/sundial/wear/build/outputs/apk/debug/`
- APK `applicationId` is `com.patrickauld.watches.companion.watchfacepush.sundial` (verify with `aapt dump badging`)

---

## Pattern for future faces

Every new face module follows this template:
1. Create `faces/<slug>/wear/build.gradle.kts` with `applicationId = "com.patrickauld.watches.companion.watchfacepush.<slug>"`
2. Add `include(":faces:<slug>:wear")` to `settings.gradle.kts`
3. Use the same SDK levels, minification settings, and `hasCode=false` pattern

This is documented in `templates/wear-wff-v4/README.md` and should be updated after this plan is implemented.
