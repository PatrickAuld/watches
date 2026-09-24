# Radial moiré

Hour and minute pointers appear where a stationary ink engraving for each
pointer meets a moving transparent slit plate. The engraving and plate share
a curved radial grating. The source image contains only etched lines within
each pointer's silhouette; WFF composes it with a separately rotated `MASK`
group. No pre-rendered hand frames or opacity switching remain.

The plate turns clockwise at 1.125 degrees per second, driven by
`[SECOND_MILLISECOND]`. Its 80-fold angular symmetry makes one 4.5-degree
registration cycle repeat every four seconds, including across the minute
boundary. A faint engraving on the dial follows the same plate orientation.
The hand substrates rotate to the actual time, while their slit masks
counter-rotate to remain aligned with the globally moving plate. Residual
translucency prevents a hand from vanishing at an interference trough.

The field combines 80 angular cycles with a radial progression and two
nonlinear ripples. Slightly different curvature in the moving plate produces
traveling beats where its lines meet the ink. The whole plate interaction
comes from static PNG resources and WFF transforms.

A second plate has its own curvature and turns at 0.45 degrees per minute.
The faint version crosses the static dial engraving while a transparent
`slow_veil` multiplies into both hand masks. The 800-minute rotation spans
exactly 360 degrees, so its reset is seamless. A glance a few minutes later
shows another arrangement of broad beats while the fast four-second motion
continues over it.

Check the browser preview with **Animate** enabled and the Pixel Watch in
interactive mode. Millisecond-driven rendering costs more battery than the
old 1 Hz stepping; evaluate performance on the physical watch. The interactive
dial uses dark ink on white paper. Ambient mode hides the dial, both moving
plates, and the interactive hand groups. Separate static, light-on-black
interference hand assets rotate only with the hour and minute; the screen
remains black and the plate textures do not move. Regenerate assets with
`python3 faces/radial-moire/generate_assets.py` (NumPy and Pillow).
