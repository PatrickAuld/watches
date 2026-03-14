# Personal Watch Face Delivery Plan

High-level plan for supporting a private, personal deployment workflow where GitHub builds watch faces and Patrick can install them onto a Pixel Watch through a phone app, without relying on a self-hosted CI runner.

## Goal

Support this end-to-end flow:

1. design and iterate in the browser prototype lab
2. promote accepted faces into WFF v4 Wear OS modules
3. build those watch-face artifacts in GitHub Actions
4. make selected artifacts available to a personal Android phone app
5. use the phone app plus a paired watch app to install or update the watch face on Patrick's Pixel Watch

This is explicitly a **single-user / personal deployment** model, not a public marketplace or Play-first product.

---

## Why this architecture

A direct GitHub-to-watch deployment path is awkward because:
- GitHub-hosted runners cannot naturally reach private watch hardware
- self-hosted runners add infrastructure overhead
- ADB-based deployment from CI is the wrong abstraction for a long-term personal workflow

A phone-driven install model is cleaner because:
- the phone is already the natural control plane for the watch
- GitHub only needs to build and publish artifacts
- the phone app can provide a personal installation UX
- the watch app can use the documented Wear OS watch-face install/update path

---

## Core system pieces

## 1. Prototype layer

Current repo surface:
- `prototypes/site/`
- GitHub Pages deployment

Purpose:
- fast visual iteration
- feedback and review
- design exploration before any Android packaging work

This remains the primary design surface.

---

## 2. Production watch-face modules

Current repo surface:
- `faces/<slug>/wear/`

Purpose:
- package accepted faces as WFF v4 XML-only Wear OS modules
- one face per module/project
- clean Gradle/CI boundaries

Immediate rule:
- each committed face must remain isolated
- no giant mixed watch-face app for production faces

---

## 3. CI artifact build layer

Planned GitHub Actions role:
- build real Wear modules with Gradle
- emit watch-face APK artifacts
- preserve metadata per build

Near-term outputs:
- debug APKs for rapid testing
- metadata describing face, commit, build type, timestamp, version

Longer-term outputs:
- signed release artifacts
- validation outputs/tokens required for the final install path

---

## 4. Personal Android phone app

Planned repo surface:
- `apps/phone/`

Purpose:
- present a private catalog of available watch-face builds
- fetch chosen artifacts from the selected publication source
- communicate with the paired watch
- trigger install/update of a chosen face

This app is the personal operator console.

It should eventually support:
- list of available faces
- list of available builds per face
- preview image / commit / notes
- install latest
- update existing install
- possibly rollback to an older build

---

## 5. Paired Wear OS companion app

Planned repo surface:
- likely `apps/watch/` or another clearly named companion module

Purpose:
- receive artifacts from the phone app
- invoke the documented watch-face install/update API on the watch
- manage installation state and activation state

Important architectural note:
- the phone app is **not enough by itself**
- the actual install/update API runs on the watch side
- so the system needs a paired watch app, not just a phone app

---

## Required platform path

The intended install path is:
- **Watch Face Push** on Wear OS 6
- WFF v4 watch-face artifacts
- phone/watch communication over the Wear Data Layer

That means the final deployment model should assume:
- Wear OS 6 support on the target watch
- WFF v4 packaging rules
- signed and validated watch-face artifacts
- phone app + watch app cooperation

---

## Planned delivery flow

## Phase A: design and acceptance

1. create or update prototype under `prototypes/site/`
2. review visually via GitHub Pages
3. accept a design direction
4. promote that face into `faces/<slug>/wear/`

## Phase B: production packaging

1. implement the face in WFF v4 XML
2. build locally with the Gradle wrapper
3. validate and refine until the module is buildable

## Phase C: CI build pipeline

1. GitHub Actions builds `:faces:<slug>:wear`
2. CI uploads the built artifact
3. CI records metadata for that artifact
4. later CI may also publish a durable catalog

## Phase D: personal install workflow

1. phone app fetches chosen artifact + metadata
2. phone app checks paired watch app availability
3. phone app transfers the artifact to the watch
4. watch app installs or updates the face
5. watch app optionally activates the installed face

---

## Repo work required

## 1. Finish Wear build reliability

Needed:
- stable Gradle-wrapper-based build path
- documented local JDK usage
- successful build for the Sundial face
- repeatable pattern for future faces

## 2. Add GitHub Actions build workflow for wear modules

Needed:
- build selected `faces/<slug>/wear` modules
- upload APK artifacts
- preserve build metadata

## 3. Decide durable artifact publication strategy

Possible options:
- GitHub Releases
- GitHub Pages-hosted static catalog
- another simple private artifact endpoint

Short-term recommendation:
- start with GitHub Actions artifacts
- add durable publication only after the phone app contract is chosen

## 4. Reserve app surfaces

Needed:
- keep `apps/phone/` for the Android phone app
- add a watch companion app surface when implementation starts
- avoid speculative module sprawl before the contract is clear

## 5. Define artifact contract

Need a stable metadata shape that includes at least:
- face slug
- face name
- git commit SHA
- build type
- version
- timestamp
- artifact location
- later: signing/validation metadata if needed by the install path

---

## Functional requirements for the phone app

The phone app should eventually be able to:
- discover available watch-face builds
- show enough metadata to choose safely
- download or fetch a selected build
- detect the paired watch companion app
- initiate install/update on the watch
- show success/failure and current state

Non-goals for the first version:
- public distribution
- user accounts beyond Patrick's needs
- marketplace features
- arbitrary watch-face editing inside the phone app

---

## Functional requirements for the watch app

The watch companion app should eventually be able to:
- receive an artifact from the phone app
- persist it safely
- call the official install/update API
- report results back to the phone app
- manage activation logic when supported

Non-goals for the first version:
- browsing a store directly on the watch
- full watch-side editing UX
- anything beyond installation/update support

---

## Risks and open questions

## 1. Dynamic WFF implementation complexity

Some prototype ideas, like Sundial, may be visually simple but mathematically awkward in pure WFF XML.

We need to keep distinguishing between:
- prototype truth
- first practical WFF implementation
- eventual refined production behavior

## 2. Artifact publication contract

Workflow artifacts are useful now, but may not be the right long-term app-facing contract.

We need to choose whether the phone app ultimately consumes:
- GitHub Releases
- a Pages-hosted JSON catalog
- another durable endpoint

## 3. Signing and validation flow

The final install path will require a clear signing/validation process for watch-face artifacts.
This must be designed explicitly, not improvised later.

## 4. Activation UX

Installing a face and switching the active face are related but not identical concerns.
The UX and permission model for activation needs its own pass.

---

## Recommended implementation order

## Step 1
Finish the local Gradle-wrapper-based build path for existing Wear modules.

## Step 2
Add CI that builds and uploads wear-module artifacts.

## Step 3
Define the artifact metadata contract and publication plan.

## Step 4
Create the first minimal phone app scaffold.

## Step 5
Create the minimal watch companion app scaffold.

## Step 6
Implement artifact transfer and install/update flow.

## Step 7
Refine activation and update UX.

---

## Practical next step

The next concrete repo milestone should be:

**Build artifacts in GitHub Actions for `faces/<slug>/wear/`, with stable metadata, while continuing to refine the first real watch-face module.**

That keeps the work grounded and avoids overbuilding the app side before the production watch-face modules are actually healthy.
