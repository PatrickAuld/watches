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

### Publish the phone app on Google Play

The `Publish phone app to Google Play` workflow uploads a signed Android App Bundle through the Google Play Developer API. Pushing a tag such as `phone-v0.1.0` submits a production release. `workflow_dispatch` can upload to `internal`, `alpha`, `beta`, or `production`. Production tags use a 100% rollout unless the `PLAY_PRODUCTION_ROLLOUT` repository variable is set to `10`, `25`, `50`, or `100`.

Complete these Play Console steps once before running the workflow:

1. Create the Play app with package name `com.patrickauld.watches.companion`, complete identity verification and the store listing, and upload the initial app bundle from Play Console. The Publishing API requires an existing app with an uploaded artifact and cannot submit required legal consents.
2. Enroll in Play App Signing and provide the stable `WATCHES_KEYSTORE` key as the app-signing key. The phone and watch builds share a package name; the installed builds need the same app signature for Wear Data Layer communication. The default Google-generated key will not match the current watch and face signer.
3. Complete the Play policy forms, including the privacy policy at `https://patrickauld.github.io/watches/privacy.html`, Data safety, content rating, target audience, and ads declarations. The phone app links to the published policy from its face list.
4. If the developer account is a personal account created after November 13, 2023, run a closed test with at least 12 testers opted in for 14 continuous days and apply for production access.

Configure Google Play API access with a Google Cloud project, the Google Play Developer API, and a service account granted app-release permissions in Play Console. Set up GitHub Workload Identity Federation restricted to this repository and the release workflow. Add these repository variables:

- `PLAY_WIF_PROVIDER`: full Workload Identity Provider resource name
- `PLAY_SERVICE_ACCOUNT`: service-account email
- `PLAY_PRODUCTION_ROLLOUT`: optional default rollout percentage for production tags

Generate a separate upload keystore, register its certificate as the app's upload key in Play Console (App integrity), and add these repository secrets:

- `PLAY_UPLOAD_KEYSTORE_B64`: base64-encoded Play upload keystore
- `PLAY_UPLOAD_KEYSTORE_PASSWORD`
- `PLAY_UPLOAD_KEY_ALIAS`
- `PLAY_UPLOAD_KEY_PASSWORD`

The secret `PLAY_UPLOAD_KEYSTORE_B64` is the base64 encoding of the keystore file. Keep the keystore and passwords backed up securely. The upload key signs the `.aab`; Google Play signs delivered APKs with the app-signing key. Keep the upload key separate from `WATCHES_KEYSTORE`. The workflow generates a monotonic `versionCode` from the GitHub Actions run number and attempt. It publishes release notes from the workflow input or the version name by default.
