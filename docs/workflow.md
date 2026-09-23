# Watch face workflow

1. Create `faces/<slug>/watchface.xml` and `face.yaml`; add PNG/WebP/JPEG assets to `assets/` as needed. Android resource names use lowercase letters, digits, and underscores.
2. Run `python3 scripts/build-site.py` and serve `_site/`. The generated face catalog, web XML, and assets come from those canonical files.
3. Iterate with fixed times and ambient mode in the web preview. The browser is an approximation; confirm platform rendering on a real watch.
4. Set `status: promoted` in `face.yaml`. CI builds the single `:watchface` module with `-PfaceSlug=<slug>`, runs Google's Watch Face Push validator, and publishes the resulting APK and validation token with its checksum.
5. Install the signed phone and watch companion APKs. On the phone, choose a face build and wait for the watch's install acknowledgement. For first activation, grant the permission in the watch companion app; later replacements of the active Push slot are immediate.

The build stages XML/assets in `watchface/build/generated/wff/res`. It never writes an Android copy into a face's source directory. Draft XML remains visible on the site without a release. Face status is the only promotion switch.

The legacy plans in `docs/archive/` and `docs/plans/` record earlier design choices; this file and the README describe the current workflow.
