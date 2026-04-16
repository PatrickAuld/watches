# AGENTS.md

This repository is for designing and packaging experimental watch faces with a **browser-first iteration workflow** and a **Wear OS production path**.

## Core workflow

This repo does not use PRs or long-lived branches as the normal workflow. Default to working directly on `main` unless Patrick explicitly asks otherwise.

Always think in two phases:

1. **Prototype first** in the static site
2. **Promote later** into a dedicated Wear OS project when the design is accepted

Do not jump straight into Wear OS scaffolding unless the user explicitly asks for that.

## Non-negotiable constraints

All production watch faces in this repo must:
- target **Google Pixel Watch**
- use **WFF v4**
- use **XML-only** format

If a prototype idea cannot plausibly be represented in that production model, call that out early.

## Repository intent

This repo is expected to contain:
- a static prototype site under `prototypes/site/`
- one page per watch design during iteration
- one metadata spec per watch face under `faces/<slug>/spec/`
- eventually, one Wear OS Gradle project per accepted face

## Current implementation baseline

Milestone 1 is in place:
- static prototype lab scaffold
- shared Pixel Watch framing
- shared time controls
- one sample face: `atlas`
- initial metadata spec format
- GitHub Pages deploy on pushes to `main`

Respect that structure when making changes.

## When asked to create a new watch

Default behavior:
1. create a new stable slug
2. add a new prototype page under `prototypes/site/faces/`
3. add/update its metadata under `faces/<slug>/spec/face.yaml`
4. wire it into the prototype lab index
5. keep the first iteration lightweight and easy to review

Unless explicitly requested, do **not** create a Wear OS module yet.

## When asked to iterate on an existing watch

Prefer modifying the browser prototype first.

If the user wants a branch of an idea, create a variant with a clear stable slug, for example:
- `atlas-thin`
- `atlas-night`
- `orbital-bold`

Do not let temporary filenames become long-term canonical ids by accident.

## Feedback handling rules

For watch-face iteration, user-provided screenshots and mockups are important evidence, but they are **not automatically the target design**.

Interpret them based on the user's framing:
- if the user presents an image as the desired direction, treat it as a target reference
- if the user presents an image as broken, distorted, unorganized, or incorrect, treat it as a regression/example to avoid
- when screenshot evidence and text conflict, prefer the user's latest explicit intent about whether the image is a goal or a problem

When a user shares feedback imagery, update the relevant face notes with specifics such as:
- what should be preserved
- what should be corrected or removed
- bezel layout and numeral positions
- marker geometry and placement
- hand style and proportions
- branding/text placement
- mascot/logo placement and scale
- anything intentionally asymmetric vs accidentally distorted

## Naming rules

Use lowercase kebab-case slugs only.

Examples:
- `atlas`
- `mono-grid`
- `orbital-night`

Use the same slug consistently across:
- prototype route
- metadata directory
- future Wear OS module naming
- screenshots and generated assets

## Prototype site guidance

The prototype site is the primary review surface.

Prefer:
- simple static HTML/CSS/JS unless stronger tooling is needed
- declarative rendering
- SVG-first approaches for dial geometry
- deterministic controls for time and mode
- designs that can later map into WFF XML

Prototype pages should usually expose:
- fixed vs live time
- canonical test times
- ambient vs interactive mode when relevant
- Pixel Watch framing

## Device assumptions

Prototype against a Pixel Watch baseline.

Keep consistent assumptions for:
- round display
- safe inset
- baseline resolution
- centered composition
- legibility

If changing device assumptions, update the shared utilities and metadata accordingly.

## Promotion to production

Once a watch face is accepted, the intended model is:
- its own Wear OS Gradle project/module
- isolated from other watch faces
- WFF v4 XML assets only

Do not mix multiple production faces into one ad hoc module unless explicitly instructed.

## Deployment

The prototype site should remain viewable via **GitHub Pages**.

Current default:
- deploy from pushes to `main`
- publish the contents of `prototypes/site/`

If you change site structure, preserve or intentionally update the Pages workflow.

## Documentation discipline

When making structural changes, update the relevant docs:
- `README.md`
- `WATCHFACE_WORKFLOW_PLAN.md`
- `docs/workflow.md`
- this file (`AGENTS.md`)

Keep docs aligned with the actual repo layout.

## Build-before-push rule

Always run the relevant build or validation step before pushing changes.

This is mandatory.

At minimum:
- for prototype-site changes, run an appropriate sanity check for the changed files
- for Wear OS / Gradle changes, run the relevant Gradle build task
- do not push code that has not been locally checked in the most relevant available way

If a build cannot be run, call that out explicitly before pushing.

## Preferred behavior for future agents

- optimize for iteration speed
- keep production constraints visible
- avoid overengineering early prototypes
- preserve clean slugs and structure
- make it easy for Patrick to review visual changes quickly
- call out when a design is likely to be hard to realize in WFF v4 XML
