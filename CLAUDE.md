# AGENTS.md

This repository designs and packages experimental watch faces. **WFF v4 XML is the source of truth** for each face. The `wff-web` npm package renders XML in-browser for fast iteration. Gradle builds produce WearOS APKs for promoted faces.

## Core workflow

1. **Edit WFF XML** at `faces/<slug>/watchface.xml`
2. **Preview in browser** using the preview site (`preview/`) which renders XML via `wff-web`
3. **Promote to WearOS** by adding a `wear/` Gradle module when the design is accepted

Do not jump straight into Wear OS scaffolding unless the user explicitly asks for that.

## Face directory layout

Each face is self-contained under `faces/<slug>/`:

```
faces/<slug>/
  watchface.xml        # WFF v4 XML (source of truth)
  assets/              # images referenced by XML (PNGs etc.)
  face.yaml            # metadata: intent, design language, status
  notes.md             # longer-form design rationale and history
```

Promoted faces additionally get:

```
faces/<slug>/wear/     # WearOS Gradle module
```

The `wear/` module's Gradle build copies `watchface.xml` and `assets/` into Android resource dirs at build time. The canonical files are never duplicated in git.

## Non-negotiable constraints

All production watch faces in this repo must:
- target **Google Pixel Watch**
- use **WFF v4**
- use **XML-only** format (no Kotlin in face modules)

If an idea cannot plausibly be represented in WFF v4 XML, call that out early.

## When asked to create a new watch

Default behavior:
1. Create a new lowercase kebab-case slug
2. Create `faces/<slug>/watchface.xml` with initial WFF v4 XML
3. Create `faces/<slug>/face.yaml` with metadata (status: `draft` or `prototype`)
4. Create `faces/<slug>/notes.md` with design intent
5. Add entry to `preview/faces.json`

Do **not** create a `wear/` module unless explicitly requested.

## When asked to iterate on an existing watch

Edit `faces/<slug>/watchface.xml` directly. Preview changes via the preview site.

If the user wants a variant, create a new slug (e.g., `atlas-thin`, `orbital-bold`).

## Face metadata (face.yaml)

The `face.yaml` file provides agent context across sessions. Required fields:

```yaml
id: slug-name
name: Display Name
status: draft | prototype | promoted | archived
platformTarget: pixel-watch
display:
  shape: round
  baseResolution: 450
  safeInset: 24
wff:
  version: 4
  xmlOnly: true
style:
  family: style-family-name
  background: "#hex"
  accent: "#hex"
description: >
  One-paragraph description of the face concept.
designNotes: >
  Visual constraints and design language.
implementationNotes: >
  Technical details about the WFF XML implementation.
```

## Preview site

The preview site at `preview/` renders WFF XML in-browser using `wff-web`.

- Single-page app, no build step, loads `wff-web` from CDN
- Face list comes from `preview/faces.json` (must be updated when adding/removing faces)
- Fetches `faces/<slug>/watchface.xml` and assets at runtime
- Controls: face picker, time input, live/fixed mode, ambient toggle, animation
- Deployed to GitHub Pages on push to `main`

To preview locally: `npx serve .` from the repo root, then open `http://localhost:3000/preview/`

## Promotion to WearOS

When a face is accepted for production:

1. Create `faces/<slug>/wear/build.gradle.kts` with copy tasks that pull from the canonical XML/assets
2. Add `AndroidManifest.xml`, `strings.xml`, `watch_face_info.xml`, `preview.xml` to the wear module
3. Add `include(":faces:<slug>:wear")` to `settings.gradle.kts`
4. Update `face.yaml` status to `promoted`

The Gradle copy tasks ensure the wear module always uses the canonical XML. Copied files are gitignored.

## Feedback handling rules

User-provided screenshots and mockups are important evidence, but are **not automatically the target design**.

Interpret them based on the user's framing:
- if presented as the desired direction, treat as a target reference
- if presented as broken/distorted/incorrect, treat as a regression to avoid
- when screenshot evidence and text conflict, prefer the user's latest explicit intent

When a user shares feedback, update the relevant `notes.md` with specifics.

## Naming rules

Use lowercase kebab-case slugs only (e.g., `atlas`, `mono-grid`, `orbital-night`).

Use the same slug consistently across:
- face directory name
- face.yaml id
- Wear OS module naming
- preview/faces.json

## Device assumptions

Target: Google Pixel Watch
- Round display, 450px baseline resolution, 24px safe inset

## Deployment

- Preview site: GitHub Pages, deployed from `preview/` + `faces/` on push to `main`
- WearOS builds: GitHub Actions, triggered by changes to face XML/assets/wear modules

## Build-before-push rule

Always run the relevant build or validation before pushing:
- For WearOS changes: `./gradlew :faces:<slug>:wear:assembleDebug`
- For preview site changes: verify the site loads correctly via local server

## Preferred behavior for agents

- Optimize for iteration speed
- Keep production constraints visible
- Edit XML directly rather than describing changes
- Use the preview site to verify visual changes
- Persist design decisions in `face.yaml` and `notes.md`
- Call out when a design is hard to realize in WFF v4 XML
