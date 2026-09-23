# Watches development

Work directly on `main` by default; Patrick explicitly prefers this repository workflow. WFF v4 XML under `faces/<slug>/watchface.xml` is the sole face definition. Each face has `face.yaml` and optional `assets/`; do not create a separate browser implementation or copy XML into tracked Android resources.

For a new face, create its canonical XML, metadata, and notes. The preview and release scripts discover it automatically. Use `status: draft` until it passes device validation, then set `status: promoted`. Target Pixel Watch, WFF v4, resource-only face APKs.

Commands:

```bash
python3 scripts/build-site.py --check
python3 scripts/build-site.py
python3 -m http.server --directory _site 8000
./gradlew :watchface:assembleDebug -PfaceSlug=sundial
./gradlew :apps:phone:assembleDebug :apps:watch:assembleDebug
```

GitHub Actions validates promoted APKs using the official Watch Face Push validator, publishes a catalog only with stable signing secrets, and deploys the generated preview site. The paired phone/watch apps use one package identity and one signing key. A phone send is not a successful install until the watch reports the result.

Screenshots or mockups marked broken are evidence of a regression, not a design target. Record durable design feedback in the face's `notes.md`.
