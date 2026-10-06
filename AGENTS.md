# Watches development

Work directly on `main` by default; Patrick explicitly prefers this repository workflow. WFF v5 XML under `faces/<slug>/watchface.xml` is the sole face definition. Each face has `face.yaml` and optional `assets/`; do not create a separate browser implementation or copy XML into tracked Android resources.

For a new face, create its canonical XML, metadata, and notes. The preview and release scripts discover it automatically. The site has a gallery at the root and one linkable page per face at `faces/<slug>/` (templates in `preview/templates/`); every `faces/<slug>/face.yaml` gets a page, even before it has XML. Use `status: draft` until it passes device validation, then set `status: promoted`. Editable faces (with `UserConfigurations`) must ship a 450×450 `preview.png` picker thumbnail rendered from the canonical XML; with the shared placeholder, long-pressing them on a Pixel Watch hangs at "Starting". `build-site.py --check` enforces this for promoted faces. Target Pixel Watch, WFF v5, resource-only face APKs.

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
