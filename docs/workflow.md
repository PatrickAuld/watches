# Workflow

## Milestone 1

Milestone 1 establishes the browser-first prototype layer.

Implemented pieces:
- monorepo skeleton for prototypes and faces
- static prototype lab under `prototypes/site/`
- shared Pixel Watch framing utilities
- shared time control logic
- sample prototype page for `atlas`
- initial face metadata spec under `faces/atlas/spec/face.yaml`

## Immediate usage

- open the prototype lab at `/prototypes/site/index.html`
- open the sample face at `/prototypes/site/faces/atlas.html`
- review the watch with fixed or live time
- use canonical time checkpoints for design feedback

## Feedback loop rule

When the user provides a rendered screenshot or annotated mockup, treat that image as the current visual source of truth for the face.

After image-based feedback:
- update the face notes/reference files
- record the important visual decisions explicitly
- align future prototype work to the latest image, not stale text descriptions
