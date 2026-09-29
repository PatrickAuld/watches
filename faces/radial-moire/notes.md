# Radial moiré: selectable kinetic plates

The watch editor offers **Eccentric vertical slits**, **Opening petals**, and
**Folding facets**, plus Graphite, Sepia, Atlantic, and Plum palettes. Three
flavors select a plate mechanism when placing the face; the editor exposes
plate and palette as independent settings. `watch_face_info.xml` must have
`Editable=true`, `MultipleInstancesAllowed=true`, and `FlavorsSupported=true`.
The web preview exposes the same two selectors.

The first variant is a stationary vertically ruled substrate and one rotating,
off-center slit disc. The displaced disc axis continually changes registration
with the straight grating, producing wave envelopes. Petal and facet variants
use two distinct radial engravings and a second slow plate. Those lines and
apertures overlap to make the shapes apparently open, contract, and fold; the
shapes are not swapped frames. The fast disc turns 1.5 degrees per second and
returns seamlessly after four minutes. Slow discs turn 0.45 degrees per minute
and return after 800 minutes. Pointers are fixed line engravings in hand-shaped
regions, intersected with the same global slit plates while the hand groups
follow the actual hour and minute.

Interactive mode uses selectable dark ink on a light paper color. Ambient hides every dial and moving plate
and displays only static textured hands on black, changing with the time.
Regenerate with `python3 faces/radial-moire/generate_assets.py`.
