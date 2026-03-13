# Watch Face Workflow Plan

## Goal

Build a single repository that supports two modes of work:

1. **Fast iteration in a static website** for experimental watch-face design
2. **Production packaging as individual Wear OS projects** once a design is accepted

This repo should make it cheap to explore many unusual watch faces, while keeping the production path structured and repeatable.

## Constraints

- Entire project lives in **one GitHub repository**
- Early design iteration happens in a **static website**
- Each watch design gets its **own page** in that site
- Shared site utilities handle:
  - time control
  - device framing
  - common watch preview behavior
- Once a design is accepted, each watch face gets its **own Wear OS Gradle project** in the same repo
- Gradle projects do **not** need publishing automation
- Most watches will be **experimental / non-standard**
- Mainline work should support requests like:
  - “make a new watch”
  - “iterate on this existing watch”
- The static site should deploy somewhere quickly viewable for feedback
- All production watch faces must target **Google Pixel Watch**
- All production watch faces must use **WFF v4**
- All production watch faces must use **XML-only format**

---

## Working Model

### Phase 1: Prototype in browser

Every new idea starts as a page in the static site.

That page should:
- render inside a circular watch viewport
- use shared time utilities
- support fixed or live time
- optionally simulate common watch states
- make visual review fast and precise

The browser preview is the main surface for rapid iteration.

### Phase 2: Promote to Wear OS project

Once a design direction is accepted, create a dedicated Wear OS Gradle project for it.

Each accepted face should:
- have its own isolated module/project
- contain its own WFF v4 XML assets
- build independently from other watch faces
- share only minimal common build infrastructure

This keeps experimentation cheap and production clean.

---

## Repository Structure

Recommended structure:

```text
watches/
  README.md
  WATCHFACE_WORKFLOW_PLAN.md

  docs/
    workflow.md
    naming.md
    pixel-watch-target.md
    wff-v4-rules.md

  prototypes/
    site/
      package.json
      src/
        app/
        pages/
          index.html
          faces/
            atlas.html
            mono-grid.html
            orbital.html
        components/
          WatchFrame.*
          Dial.*
          Hands.*
          Complication.*
        lib/
          time/
          render/
          device/
          preview/
        assets/
      public/
      scripts/

  faces/
    atlas/
      spec/
        face.yaml
        notes.md
      preview/
        snapshots/
      wear/
        build.gradle.kts
        src/main/
          AndroidManifest.xml
          watchface/
            watchface.xml
            assets/

    mono-grid/
      spec/
      preview/
      wear/

    orbital/
      spec/
      preview/
      wear/

  templates/
    prototype/
    wear-wff-v4/

  scripts/
    new-face
    new-variant
    promote-face
    validate-wff
    build-face
    build-all-faces
    screenshot-prototype

  gradle/
  settings.gradle.kts
  build.gradle.kts
```

---

## Design Principles

### 1. One stable identity per watch face

Each watch face should have:
- a stable slug, e.g. `atlas`, `mono-grid`, `orbital`
- a human-readable title
- a lifecycle state
- a prototype page
- an optional Wear OS module once promoted

This slug should be used consistently across:
- folder names
- routes
- module names
- generated scripts
- artifact naming

### 2. Prototype first

The prototype site should be the center of gravity during early work.

Rationale:
- iteration is faster in browser than on-device
- feedback is easier with deploy previews
- multiple experimental branches stay cheap
- only good designs graduate into Wear OS modules

### 3. Production modules stay isolated

Each accepted face should be its own Gradle project/module.

Rationale:
- unusual watches can diverge without contaminating each other
- per-face builds are easier to reason about
- individual faces can be archived or replaced cleanly
- module generation can be automated

### 4. Prototype designs should remain translatable to WFF XML

Because final watch faces must be **WFF v4 XML-only**, prototype work should bias toward primitives that can later map into WFF cleanly.

Prefer:
- layered composition
- SVG-like geometry
- declarative transforms
- stateful but structured layouts
- precomputed assets when needed

Avoid depending too heavily on:
- browser-only rendering tricks
- arbitrary canvas logic with no XML equivalent
- complex physics-driven animation
- effects that cannot survive conversion to WFF XML

Experimental visuals are fine, but production candidates must still be representable in the required final format.

---

## Lifecycle States

Each watch face should move through explicit states:

### `prototype`
- browser-only
- unstable
- optimized for fast feedback

### `candidate`
- likely to become a real Wear OS watch face
- visual structure becoming stable
- should be reviewed for WFF compatibility

### `production`
- has dedicated Wear OS module
- builds cleanly
- uses WFF v4 XML-only assets
- targets Pixel Watch

### `archived`
- kept for reference
- not active
- may remain viewable in prototype history

This prevents the repo from turning into an unstructured pile of half-finished experiments.

---

## Prototype Site Requirements

The prototype site should act as a **watch-face lab**, not just a static set of pages.

### Shared utilities should include

#### Time controls
- live time mode
- fixed time mode
- scrub to arbitrary time
- jump to canonical test times such as:
  - `00:00`
  - `10:10`
  - `11:59`
  - `23:59`

#### Device preview
- circular crop
- Pixel Watch-focused viewport
- safe inset visualization
- consistent scale and centering

#### Preview modes
- interactive mode preview
- ambient mode preview
- optional low-power simplification preview

#### Data mocks
Common simulated data should be available where useful:
- date
- battery
- steps
- heart rate
- weather
- next event

Even when designs are highly experimental, shared mock infrastructure speeds iteration.

### Rendering recommendation

Prefer an **SVG-first** or similarly declarative rendering model in the prototype site.

Why:
- radial geometry is easier
- snapshot generation is more deterministic
- conversion to production assets is cleaner
- complex dial layouts are more maintainable

---

## Face Metadata

Each watch face should have a small spec file, for example:

```yaml
id: atlas
name: Atlas
status: prototype
platformTarget: pixel-watch
prototype:
  route: /faces/atlas.html
wff:
  version: 4
  xmlOnly: true
display:
  shape: round
  baseResolution: 450
  safeInset: 24
features:
  ambient: true
  complications: []
```

This metadata becomes the glue between:
- prototype routing
- preview behavior
- build automation
- validation
- eventual Wear OS scaffolding

---

## Gradle / Wear OS Strategy

Use one shared root Gradle build with one per-face project/module for accepted designs.

Example:

```kotlin
include(":faces:atlas:wear")
include(":faces:mono-grid:wear")
include(":faces:orbital:wear")
```

### Why this is the right structure

- builds remain per-face and understandable
- non-standard experiments do not force awkward shared abstractions
- adding a new production face becomes a generated action, not manual build surgery
- faces can evolve independently

### Shared root Gradle config should provide
- common SDK configuration
- shared build conventions
- common validation tasks
- WFF packaging conventions
- common debug settings where useful

Each watch face module should stay thin and specific.

---

## Scripts to Build Early

### `new-face`
Creates a new prototype watch face scaffold.

Should generate:
- `faces/<slug>/spec/face.yaml`
- prototype page/route
- notes placeholder

### `new-variant`
Forks an existing design into a new experimental branch.

Example use:
- `atlas` -> `atlas-thin`
- `orbital` -> `orbital-night`

### `promote-face`
Promotes a prototype/candidate into a Wear OS module.

Should:
- create the `wear/` project structure
- generate manifest/build files
- generate WFF v4 XML skeleton
- register the module in Gradle settings
- preserve the canonical slug

### `validate-wff`
Checks that promoted faces satisfy repo policy:
- WFF version 4
- XML-only assets
- required metadata present
- Pixel Watch target assumptions preserved

### `build-face`
Builds a single face by slug.

### `build-all-faces`
Builds all production faces.

### `screenshot-prototype`
Generates deterministic preview images for review and PRs.

---

## Deployment Strategy for the Prototype Site

The prototype site should deploy automatically so feedback is fast.

### Default deployment choice

Use **GitHub Pages** first.

Reasoning:
- it is already attached to the repository
- it is trivial to host a static site from the same repo
- deployment on pushes to `main` is straightforward
- it keeps the earliest iteration loop simple

Initial deployment policy:
- publish the prototype site with a GitHub Actions workflow
- deploy automatically on pushes to `main`
- keep the site URL stable so feedback can reference exact pages

If later preview environments become important for branch-by-branch review, the deployment target can expand to Vercel, Netlify, or Cloudflare Pages. But the initial plan should assume **GitHub Pages on main-site push**.

The site homepage should list available faces and their states, for example:
- Atlas — prototype
- Mono Grid — candidate
- Orbital — production

That makes review easier and gives a stable language for feedback.

---

## Mainline Development Workflow

Expected normal loop:

1. Request a new watch or a variation of an existing one
2. Generate a new prototype page
3. Deploy/update the static site
4. Review visually and iterate quickly
5. When a design is accepted, promote it into its own Wear OS project
6. Validate WFF v4 / XML-only / Pixel Watch requirements
7. Build that watch independently

This workflow is optimized for many experiments with occasional graduation into production.

---

## Pixel Watch Targeting Policy

All production work should assume a Pixel Watch baseline.

The repo should explicitly document:
- round display assumptions
- baseline preview resolution
- safe insets
- legibility thresholds
- ambient-mode constraints
- any complication-placement rules

A shared device profile in the prototype site should mirror these assumptions so iteration happens against the real target shape.

---

## WFF v4 / XML-Only Policy

This should be treated as non-negotiable production policy.

Every promoted watch face must satisfy:
- Watch Face Format version 4
- XML-only implementation
- Pixel Watch compatibility

This policy should be enforced by documentation and validation scripts rather than memory or convention alone.

---

## Suggested Initial Milestones

### Milestone 1: Foundation
- create monorepo structure
- scaffold prototype site
- add shared watch frame + time utilities
- add one sample face
- define face metadata format

### Milestone 2: Iteration ergonomics
- add face generator
- add variant generator
- add deploy previews
- add prototype screenshots
- add preview controls

### Milestone 3: Production path
- add Wear OS template
- add WFF v4 XML template
- add promotion script
- add validation script

### Milestone 4: CI and discipline
- typecheck/lint/build prototype site
- validate changed watch-face specs
- build changed production faces
- document naming and workflow rules

---

## Bottom Line

The right model for this repo is:

- **one monorepo**
- **one browser-based prototype site** for fast visual iteration
- **one page per watch design**
- **shared preview/time/device utilities**
- **one metadata spec per face**
- **one generated Wear OS Gradle project per accepted face**
- **WFF v4, XML-only, Pixel Watch-targeted by policy**

That supports aggressive experimentation without losing structure when designs graduate into real watch faces.
