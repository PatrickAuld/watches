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

When the user provides a rendered screenshot or annotated mockup, first determine whether the image is being shown as:
- the intended direction, or
- a broken / distorted / failed result

After image-based feedback:
- update the face notes/reference files
- record what the image confirmed
- record what the image revealed as wrong
- align future prototype work to the user's latest explicit intent, not a naive assumption that every screenshot is canonical
