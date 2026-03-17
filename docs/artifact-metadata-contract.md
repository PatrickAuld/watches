# Artifact Metadata Contract

## Overview

Each CI build of a watch face module produces a `metadata.json` file alongside the APK. This file is uploaded as a GitHub Release asset and consumed by the phone app to discover and display available builds.

## Schema

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `slug` | string | face directory name | Machine identifier, e.g. `sundial` |
| `name` | string | face display name | Human-readable name |
| `commitSha` | string | `github.sha` | Full git commit SHA |
| `buildType` | string | build variant | `debug` or `release` |
| `versionName` | string | `build.gradle.kts` | Semantic version |
| `versionCode` | number | `build.gradle.kts` | Monotonic integer |
| `timestamp` | string | build time | ISO 8601 UTC |
| `runId` | string | `github.run_id` | GitHub Actions run ID |
| `runNumber` | number | `github.run_number` | Monotonic build number |

## Example

```json
{
  "slug": "sundial",
  "name": "Sundial",
  "commitSha": "abc123def456789...",
  "buildType": "debug",
  "versionName": "0.1.0",
  "versionCode": 1,
  "timestamp": "2026-03-17T14:30:00Z",
  "runId": "12345678",
  "runNumber": 42
}
```

## Versioning policy

- Fields may be added but not removed
- Consumers should ignore unknown fields
- The `slug` field is the primary key for identifying which face a build belongs to

## Future extensions

These fields will be added in later plans:

- `validationToken` — Watch Face Push validation token path (Plan 06)
- `signingKeyFingerprint` — for release builds (Plan 06)

## Consumption

The phone app fetches `metadata.json` from GitHub Release assets to build a catalog of available face builds. It uses the `slug` to group builds by face and `versionCode` to detect updates.
