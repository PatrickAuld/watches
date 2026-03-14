# Android Stage Scaffold

This repo now includes the first production-stage scaffold for a real Wear OS watch face.

## Added

### Root build wiring
- `settings.gradle.kts`
- `build.gradle.kts`
- `gradle/libs.versions.toml`

### First Wear OS module
- `faces/sundial/wear/`
  - `build.gradle.kts`
  - `src/main/AndroidManifest.xml`
  - `src/main/res/raw/watchface.xml`
  - `src/main/res/xml/watch_face_info.xml`
  - `src/main/res/values/strings.xml`
  - `src/main/res/drawable/preview.xml`

## What this scaffold is

This is a **real WFF v4 module scaffold**, not yet a full faithful implementation of the browser prototype.

It establishes:
- one-face-per-module structure
- WFF v4 manifest packaging
- resource-only watch face setup
- starter watch face XML file

## What is still limited

For `sundial`, the current `watchface.xml` is now a more faithful **static first implementation** of the visual design, but it still does not perform full dynamic solar geometry in WFF XML.

Remaining gap:
- the line/chord is still fixed to the preview composition
- the shadow segment is still fixed to the preview composition
- the hour marker is still fixed to the preview composition
- the Alameda-specific sun calculation from the browser prototype has not yet been expressed in pure WFF XML

Those pieces need a second pass once the exact WFF-v4 expression/transform strategy is chosen.

## Why scaffold first

This separates two tasks cleanly:
1. repository / Gradle / manifest setup
2. actual watch-face XML implementation

That is the right order for this repo because multiple faces will eventually exist side by side.

## Next implementation step

Turn `faces/sundial/wear/src/main/res/raw/watchface.xml` from placeholder geometry into a proper WFF realization of the Sundial design.
