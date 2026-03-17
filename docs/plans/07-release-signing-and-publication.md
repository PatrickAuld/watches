# Plan 07: Release Signing and Publication

**Depends on:** Plan 06 (End-to-End Integration)

---

## Intent

Plans 01-06 establish the end-to-end mechanics of building watch-face artifacts, discovering them in the phone app, transferring them to the watch, and installing them with Watch Face Push.

This plan hardens the pipeline for real personal use by defining:
- stable signing for updateable watch-face APKs
- durable publication targets beyond transient CI artifacts
- a release manifest the phone app can trust
- promotion rules between debug experimentation and personal release builds

Without this layer, the system works only as an experimental build pipeline. With it, the system becomes a reliable personal distribution channel.

---

## Why a separate publication/signing plan

The earlier plans intentionally focus on functionality first:
- can the face build?
- can the phone discover it?
- can the watch install it?

Publication and signing add a second class of concerns:
- update continuity across builds
- persistent hosting and metadata stability
- release retention and rollback
- trust boundaries between CI, phone app, and watch app

These concerns are cross-cutting enough that they deserve their own plan instead of being diluted into the implementation plans.

---

## Problems this plan solves

### 1. Debug signing is not enough

If builds are signed inconsistently, update flows can fail.
For a personal watch-face pipeline, repeated installs and updates must preserve signing identity.

### 2. CI artifacts are not a stable application contract

GitHub workflow artifacts are excellent for CI validation, but they are not the ideal long-term source of truth for the phone app because:
- retention is time-limited
- URLs are not the cleanest durable interface
- they are closer to CI internals than to a release channel

### 3. The phone app needs a stable catalog

The phone app should consume a stable, explicit manifest for available builds, not infer state from ad hoc CI outputs.

---

## Release model

Adopt a two-tier model.

## Tier 1: CI build artifacts

Purpose:
- validate the build
- provide temporary debugging outputs
- support short-lived review or manual inspection

Properties:
- debug builds are acceptable
- retention can stay GitHub-managed
- phone app should not depend on this tier directly

## Tier 2: Personal release channel

Purpose:
- durable installable builds for Patrick
- stable metadata contract for the phone app
- consistent signing for update support

Properties:
- signed with a stable personal release key
- published to a durable endpoint
- includes a release manifest
- appropriate place to attach validation token outputs

---

## Recommended publication target

### Primary recommendation: GitHub Releases + release manifest

Use GitHub Releases as the first durable publication target.

Why:
- already native to the repo
- simple human inspection
- stable per-release assets
- easy to automate from GitHub Actions
- no extra storage service required in the first version

### Manifest strategy

For app consumption, generate a machine-readable release manifest in addition to raw assets.

Recommended release assets:
- face APK
- validation token
- metadata JSON for that build
- release manifest JSON for the release as a whole
- optionally preview image if available

The phone app should read the manifest, not scrape release asset lists directly.

---

## Signing policy

## 1. Separate release signing for pushed watch faces

Use a stable signing key dedicated to personal watch-face release artifacts.

Reasons:
- update continuity across releases
- cleaner separation from debug and local-only builds
- aligns with the expectation that pushed faces be signed consistently

## 2. Keep debug and release distinct

### Debug builds
Use for:
- local development
- CI verification
- fast experiments

### Release builds
Use for:
- phone-app-visible installable channel
- durable GitHub Releases publication
- anything expected to update in place on the watch

## 3. Secret handling

GitHub Actions should read release signing material from secrets.

Expected secrets:
- `WATCHFACE_KEYSTORE_BASE64`
- `WATCHFACE_KEYSTORE_PASSWORD`
- `WATCHFACE_KEY_ALIAS`
- `WATCHFACE_KEY_PASSWORD`

Never commit keystore material into the repository.

---

## Manifest contract

Introduce a release-level manifest, for example:

```json
{
  "schemaVersion": 1,
  "channel": "personal-release",
  "generatedAt": "2026-03-17T00:00:00Z",
  "commitSha": "...",
  "releaseTag": "sundial-v0.2.0-build.57",
  "faces": [
    {
      "slug": "sundial",
      "name": "Sundial",
      "versionCode": 2,
      "versionName": "0.2.0",
      "buildType": "release",
      "apk": "sundial-release.apk",
      "metadata": "sundial-metadata.json",
      "validationToken": "sundial-validation-token.bin",
      "preview": "sundial-preview.png"
    }
  ]
}
```

### Why a release-level manifest matters

It gives the phone app one stable file to fetch and reason about.

The phone app can then:
- show available faces
- detect updates
- map a face slug to the correct APK/token assets
- avoid hard-coded assumptions about release-asset naming

---

## Publication workflow

## Phase A: CI build

Current build workflow remains responsible for:
- building modules
- verifying artifacts
- generating per-build metadata

## Phase B: promotion to personal release

Add a promotion workflow that:
- selects the desired build outputs
- signs release APKs if not already signed in the build job
- generates validation token outputs
- creates or updates a GitHub Release
- attaches the release manifest and face-specific assets

This promotion step can be either:
- automatic on push to `main`, or
- manual via `workflow_dispatch`

### Recommendation

Start with **manual promotion**.

Reason:
- safer while the face/install pipeline is still evolving
- avoids publishing every intermediate build as a durable personal release
- keeps Patrick in control of which builds become installable releases

---

## Release channels

Support at least two conceptual channels.

### `debug-ci`
- transient
- workflow artifacts only
- not intended for the phone app

### `personal-release`
- durable
- signed
- visible to the phone app
- used for actual watch installs and updates

Later, if useful, add:
- `experimental`
- `stable`

But do not overbuild channel complexity early.

---

## Phone app behavior under this plan

The phone app should:
- consume only the release manifest from the personal-release channel
- treat release assets as authoritative
- compare installed `versionCode` with manifest `versionCode`
- support reinstall/update/rollback among published releases

The phone app should **not** depend on workflow artifact URLs.

---

## Watch app behavior under this plan

The watch app remains simple:
- receive APK + validation token
- install or update
- report result

It should not need to know anything about GitHub Releases directly.

---

## Rollback model

Durable publication enables clean rollback.

Recommended rollback rule:
- every published personal release remains installable until manually pruned
- phone app may expose the latest N releases per face
- rollback is implemented as selecting an older signed release and pushing it as an update

This only works reliably if signing identity is stable.

---

## Cleanup and retention policy

### CI artifacts
- short retention is fine
- e.g. 30 to 90 days

### Personal releases
- keep until intentionally pruned
- because Patrick is the only consumer, storage pressure should be low

### Manifest schema
- additive evolution only
- old app versions should ignore unknown fields

---

## Verification

### Build verification
- release variant builds successfully in CI
- validation token is generated successfully
- release assets are uploaded successfully

### Update verification
1. install release version N via phone/watch flow
2. publish release version N+1 with same signing identity
3. phone app shows update available
4. update succeeds on watch without reinstall gymnastics

### Rollback verification
1. install release version N+1
2. choose release version N from phone app
3. update/rollback succeeds

---

## Risks

1. **Signing drift**
   - if keystore handling changes accidentally, updates may fail
2. **Validator-push availability**
   - if token generation tooling is brittle, release publication may need graceful degradation
3. **Release sprawl**
   - publishing every build as durable release can clutter history
4. **Manifest drift**
   - app and CI must stay aligned on manifest schema

---

## Deliverables

This plan should eventually produce:
- release signing config for watch-face modules
- a promotion workflow for GitHub Releases
- release manifest generation
- documentation for release channels and rollback

---

## Recommended next step after this plan

After Plan 07, the next concrete step should be:

**implement manual personal-release publication for a single face (`sundial`) with signed assets and a release manifest.**

That is the smallest useful durable-distribution milestone.
