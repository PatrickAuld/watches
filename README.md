# watches

Browser-first watch-face lab with a path to individual Wear OS watch-face projects.

## Milestone 1 status

Implemented:
- monorepo-style repo skeleton
- static prototype site under `prototypes/site/`
- shared Pixel Watch preview frame
- shared time control utilities
- sample prototype face: `atlas`
- initial metadata spec: `faces/atlas/spec/face.yaml`
- GitHub Pages deployment from pushes to `main`

## Prototype site

Local structure:
- `prototypes/site/index.html`
- `prototypes/site/faces/atlas.html`

Published via GitHub Pages from `main`.

## Build artifacts

Wear modules can be built in GitHub Actions and uploaded as downloadable artifacts.
The initial workflow targets the existing `sundial` Wear module and is meant to be extended face-by-face as production modules are added.

## Docs

- `WATCHFACE_WORKFLOW_PLAN.md`
- `docs/workflow.md`
- `docs/wff-v4-reference.md`
- `docs/wff-samples-notes.md`
- `docs/android-stage-scaffold.md`
- `docs/personal-watchface-delivery-plan.md`
- `docs/personal-phone-app-plan.md`
- `docs/artifact-publication-plan.md`
- `docs/deployment-workflow-outline.md`

## Planned next layer

The repo now reserves `apps/phone/` for a future personal Android phone app that can act as the operator-facing surface for CI-built watch artifacts.

That directory is intentionally documentation-first until the artifact publication contract is chosen.
