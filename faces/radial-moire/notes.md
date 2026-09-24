# Radial moiré

The hour and minute pointers are not solid watch-hand graphics. Each engraving stores four small angular offsets, interlaced into curved radial bands. The transparent slit mask for the current phase exposes one set of slices. WFF rotates the entire interaction around the dial pivot to follow the current time, compensating for the small encoded angular offset. The visible plate advances on each second.

The radial field uses `r + 5.7 sin(3θ + r/52) + 2.1 sin(7θ - r/79)` with a 22.5-unit pitch. These non-linear arcs preserve the printed-plate mechanism of barrier-grid animation. The hand segments appear only after two resources are composed by a WFF `MASK` group.

The phase change is deliberately stepped at 1 Hz. Evaluate legibility and aliasing at Pixel Watch resolution. Promotion enables the official WFF validator and installable APK pipeline; physical watch rendering remains to be checked.

Regenerate the PNG assets with `python3 faces/radial-moire/generate_assets.py` (NumPy and Pillow).
