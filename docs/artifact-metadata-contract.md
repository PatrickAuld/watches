# Validated release contract

Each signed GitHub Release contains `catalog.json`, `phone-debug.apk`, `watch-debug.apk`, and one APK per promoted face. The phone app finds face APKs by the exact filename in the catalog, not by scanning `*.apk`.

```json
{
  "schemaVersion": 1,
  "commitSha": "full Git SHA",
  "timestamp": "ISO 8601 UTC",
  "faces": [{
    "slug": "sundial",
    "name": "Sundial",
    "apk": "sundial-42.apk",
    "packageName": "com.patrickauld.watches.companion.watchfacepush.sundial",
    "sha256": "hex digest of the exact APK bytes",
    "validationToken": "token returned by Google's official validator",
    "versionCode": 42,
    "versionName": "0.1.42"
  }]
}
```

The validator runs on the finished signed APK. Publishing fails if validation fails or produces no token. The phone verifies the digest after download and the watch verifies it again after transfer. The watch reports the installed package and version; only that acknowledgement counts as success.

Old releases without `catalog.json` are ignored. A future schema version must preserve existing fields or teach the phone app how to read the new contract.
