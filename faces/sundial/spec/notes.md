# Sundial

Geometric watch face concept based on a single line crossing the circular dial.

## Intent

The line does all the work:
- it divides the face into light and shadow
- one endpoint lands on the outer edge at the current hour position
- the opposite endpoint marks the sun's position in the sky
- the effect should feel like a stylized sundial shadow rather than a conventional hand set

## Initial assumptions

- location is fixed to Alameda, California
- solar position is computed from date/time plus location
- first prototype is intentionally sparse and diagrammatic
- hour endpoint should be emphasized with a circle marker
- the sun endpoint should remain visible even when the sun is low, but should read differently if it is below the horizon

## Design direction

Keep it clean:
- no unnecessary text clutter
- no decorative complications
- strong contrast between illuminated and shadowed halves
- the line should feel precise and inevitable
