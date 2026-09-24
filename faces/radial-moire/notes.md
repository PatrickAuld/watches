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
comes from two static PNG resources and WFF transforms.

Check the browser preview with **Animate** enabled and the Pixel Watch in
interactive mode. Millisecond-driven rendering costs more battery than the
old 1 Hz stepping; evaluate performance on the physical watch. Ambient mode
hides the decorative moving plate. Regenerate assets with
`python3 faces/radial-moire/generate_assets.py` (NumPy and Pillow).
