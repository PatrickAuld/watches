# Sundial

Geometric watch face concept based on a single line crossing the circular dial.

## Intent

The line does all the work:
- it divides the face into light and shadow
- one endpoint lands on the outer edge at the current hour position
- the opposite endpoint marks the sun's position in the sky
- the shaded region is the circular section bounded by that chord which contains the bottom 6:00 point
- the effect should feel like a stylized sundial shadow rather than a conventional hand set

## Initial assumptions

- location is fixed to Alameda, California
- solar position is computed from date/time plus location
- first prototype is intentionally sparse and diagrammatic
- the hour endpoint should be emphasized with a circle marker
- the opposite endpoint should not be separately marked

## Design direction

Keep it clean:
- no numbers
- no words
- no center dot
- no decorative complications
- subtle hour tick lines only
- strong contrast between illuminated and shadowed halves
- the lower region should read as a genuine shadowed area, not just a flat color block
- the line should feel precise and inevitable

## Current WFF implementation note

The first Android/WFF implementation is intentionally a static, preview-faithful composition.
It captures the Sundial visual language, but does not yet reproduce the browser prototype's dynamic Alameda sun-position geometry in pure WFF XML.
