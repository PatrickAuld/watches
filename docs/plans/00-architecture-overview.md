# Plan 00: Architecture Overview

## What this is

This document describes the overall architecture and reasoning for the personal watchface delivery pipeline. It ties together the individual plan documents (01 through 06) into a coherent system.

The individual plans are designed to be implemented in order. Each produces a working, verifiable milestone. Each will be refined into spec documents before implementation begins.

---

## The problem

Patrick designs watch faces in a browser prototype lab, then promotes accepted designs into WFF v4 Wear OS modules. Today, those modules can be built locally with the Gradle wrapper, but there is no path from "module builds" to "face is running on my Pixel Watch" that doesn't involve manual ADB commands against a locally-connected device.

The goal is a clean personal deployment flow:

1. Design in the browser prototype lab
2. Promote into WFF v4 Wear OS modules
3. CI builds those modules automatically
4. A phone app discovers and fetches built artifacts
5. The phone app transfers artifacts to a paired watch companion
6. The watch companion installs or updates the face using the official API

---

## Why this architecture

### Why not ADB from CI?

GitHub-hosted runners can't reach private watch hardware. A self-hosted runner adds infrastructure overhead. ADB is the wrong abstraction for a long-term personal workflow.

### Why phone + watch, not just a watch marketplace app?

The Watch Face Push API (`WatchFacePushManager`) runs on the watch. The simplest possible approach bundles face APKs as assets inside a single watch "marketplace" app and sideloads it via ADB. That works, but it means rebuilding and reinstalling the marketplace app every time a face changes.

The phone + watch architecture is better for personal use because:
- The phone is already the natural control plane for the watch
- New face builds can be fetched over the network without touching the watch app
- The phone provides a comfortable browsing and selection UX
- The watch companion only needs to receive and install, keeping it simple
- Updates don't require a laptop or ADB

### Why Watch Face Push specifically?

Watch Face Push is the official Wear OS 6 API for programmatic watch face installation. It is the documented, supported path for installing WFF v4 watch faces outside the Play Store. The alternatives (direct APK install via `PackageInstaller`, Play Store distribution) either don't work for WFF faces or add unnecessary overhead for a single-user workflow.

---

## Key architectural finding

The Watch Face Push API imposes a specific contract:

1. **Watch-side only** — `WatchFacePushManager.addWatchFace()`, `updateWatchFace()`, `removeWatchFace()`, and `setWatchFaceAsActive()` all run on the watch. There is no phone-side API.

2. **applicationId convention** — Watch face APKs must use the pattern `<marketplace_package>.watchfacepush.<face_slug>`. For this project, that means face APKs use IDs like `com.patrickauld.watches.companion.watchfacepush.sundial`.

3. **Validation tokens** — The API requires a validation token generated at build time using the `validator-push` library. The token must accompany the APK when calling `addWatchFace()`.

4. **Phone-to-watch transfer** — Since the API is watch-side, the phone must transfer APK bytes to the watch. The Wear Data Layer (`ChannelClient` for large transfers, `MessageClient` for control messages) is the standard mechanism.

---

## System pieces

```
┌─────────────────────────────────────────────────────────┐
│  GitHub                                                 │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │ faces/*/wear/ │───▶│ CI Workflow   │──▶ GitHub Release│
│  │ (WFF v4 XML) │    │ (build+meta) │    (APK + JSON)  │
│  └──────────────┘    └──────────────┘                   │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│  Phone                                                  │
│  ┌──────────────────────────────┐                       │
│  │ apps/phone/                  │                       │
│  │ - fetch releases from GitHub │                       │
│  │ - browse available faces     │                       │
│  │ - download APK + token       │                       │
│  │ - transfer to watch          │──── Data Layer ────┐  │
│  └──────────────────────────────┘                    │  │
└──────────────────────────────────────────────────────┼──┘
                                                       │
┌──────────────────────────────────────────────────────┼──┐
│  Watch                                               │  │
│  ┌──────────────────────────────┐                    │  │
│  │ apps/watch/                  │◀───────────────────┘  │
│  │ - receive APK from phone     │                       │
│  │ - call WatchFacePushManager  │                       │
│  │ - install / update / activate│                       │
│  │ - report status to phone     │                       │
│  └──────────────────────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

---

## Plan documents

| Plan | Title | Purpose |
|------|-------|---------|
| [01](01-local-build-stabilization.md) | Local Build Stabilization | Reliable Gradle builds, applicationId alignment, gitignore hygiene |
| [02](02-ci-build-pipeline.md) | CI Build Pipeline | GitHub Actions builds wear modules, uploads artifacts, publishes releases |
| [03](03-app-infrastructure.md) | App Infrastructure | Version catalog, shared module, Gradle multi-module setup for apps |
| [04](04-watch-companion-app.md) | Watch Companion App | Wear OS app that receives faces and calls WatchFacePushManager |
| [05](05-phone-app.md) | Phone App | Android app that fetches builds from GitHub and transfers to watch |
| [06](06-end-to-end-integration.md) | End-to-End Integration | Validation tokens, CI for all apps, activation UX, update/rollback |

---

## Dependency order

```
01 ──▶ 02 ──▶ 03 ──▶ 04 ──▶ 05 ──▶ 06
                      ▲
                      │
                      └── 03 is a prerequisite for both 04 and 05
```

Plans 04 and 05 can be developed in parallel once 03 is complete, but 06 requires both to be functional.

---

## Scope boundaries

This pipeline is explicitly **single-user / personal deployment**. Non-goals:
- Public distribution or Play Store
- User accounts or auth beyond Patrick's needs
- Marketplace features
- Multi-device fleet management

Design choices should favor simplicity over generality.

---

## Risks tracked across plans

1. **`wear-watchface-push` alpha status** — API may change. Isolated behind `WatchFaceInstaller` wrapper (Plan 04).
2. **`validator-push` library availability** — May need JitPack. Scaffold without it first, add when stable (Plan 06).
3. **SDK 36 on CI runners** — May need explicit `sdkmanager` installs (Plan 02).
4. **Private repo auth** — Phone app needs GitHub PAT for private repos. Hardcode for personal use (Plan 05).
5. **Signing** — Debug signing for now. Release signing is a Plan 06 refinement.
