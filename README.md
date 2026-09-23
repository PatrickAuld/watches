# Watches

Design Wear OS 6 watch faces in one XML file per face, preview that same XML on the web, then package and send validated APKs to a Pixel Watch from an Android phone.

## Author a face

```text
faces/<slug>/
  watchface.xml    Canonical WFF v4 source
  assets/          Android drawable resources referenced by the XML
  face.yaml        Name, status, and design context
  notes.md         Design history
```

The browser and Android build read `watchface.xml` directly. A face with `status: draft` appears in the preview; changing it to `status: promoted` enables CI packaging and publication. No per-face Gradle module or manually edited face list is needed.

```bash
python3 scripts/build-site.py
python3 -m http.server --directory _site 8000
# open http://localhost:8000
python3 scripts/build-site.py --check
./gradlew :watchface:assembleDebug -PfaceSlug=sundial
```

The preview uses [wff-web](https://github.com/PatrickAuld/wff_web). It simulates the face, while the official validator and a physical watch establish platform compatibility. Some WFF features are not implemented in the browser renderer.

## Install on a watch

The [phone and watch apps](apps/) are a paired Android app. Install both builds signed with the same key. The phone fetches the latest validated GitHub Release catalog, downloads the exact selected face APK, checks its SHA-256, sends it over the Wear Data Layer, and waits for confirmation from Watch Face Push on the watch. Open the watch app to grant activation permission before selecting **Set as active** on the phone. The platform allows the app to claim an active face once; if you later switch to another developer's face, select this face manually in the watch picker.

The phone's **Automatic updates** switch checks the installed face twice daily and sends a newer validated build when the watch is connected and charging. It updates the current face only; selecting another design is always a deliberate action.

Wear OS 6 (API 36) is required for WFF v4 and Watch Face Push. The build uses a single Push slot, replacing the app's previous face when another is selected.

## Publishing

CI builds the paired apps and validates promoted faces. An immutable GitHub Release is published when these four repository secrets are configured:

- `WATCHES_KEYSTORE_B64`: base64 encoded stable Android keystore
- `WATCHES_KEYSTORE_PASSWORD`
- `WATCHES_KEY_ALIAS`
- `WATCHES_KEY_PASSWORD`

Use a key you retain. Changing it breaks updates of existing installs. CI uses it to sign all three package types; without it, CI still builds and validates but does not publish. The [artifact contract](docs/artifact-metadata-contract.md) describes `catalog.json`. See [workflow details](docs/workflow.md).
