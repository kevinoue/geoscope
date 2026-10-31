# GeoScope GS-1

A shape synthesizer styled as a vintage oscilloscope. Dial a triangle's sides
and watch it redraw in phosphor; array copies into a connected lattice inside
a wireframe sphere; rotate a tesseract through the fourth dimension — and hear
the geometry while you do it.

**Run it:** https://kevinoue.com/geoscope/ — or just open `index.html`.
One self-contained file: no libraries, no build step, no network.

![GeoScope](https://kevinoue.com/geoscope/) <!-- screenshot lives on the site -->

## What it does

- **Twelve shapes** — triangle (sides A/B/C), rectangle, polygon, circle, star,
  the four platonic solids with XYZ stretch, a torus, a 3-D Lissajous curve,
  and a tesseract with ROT XW / ROT YW knobs plus a LEVELS knob that stacks
  cubes along the w-axis.
- **ARRAY** fills a spherical lattice outward from center; **CONNECT** sets the
  pitch per axis to the shape's own extent so copies fuse — cubes share faces,
  rectangles tile like brickwork.
- **Every knob has a vary box** — check it and that one variable flows on its
  own. Rotation boxes spin their axis at SPIN rate; bounded knobs wander on
  smooth noise paced by the VARY group's RATE and DEPTH.
- **Three audio voices** (headphones recommended):
  - *OUTLINE* — the shape traced as stereo XY audio, oscilloscope music run in
    reverse. Feed the output into a real scope in XY mode and it draws the shape.
  - *SPACE* — the gap between the shape's silhouette and its surround, swept
    around a full circle; it breathes and glides.
  - *DRUM* — the shape struck as a physical object: exact membrane modes for the
    rectangle and circle (Bessel zeros), Weyl's-law spectra from true area and
    perimeter for other flat shapes, struck-bar partials for the wireframes.
    The rider dot is the mallet — one strike per lap.
- **PITCH SOURCE** lets a live variable (perimeter, size, rotation, copy count)
  bend the pitch around the FREQ knob.
- **LYNCHPINS** inverts the display: the space *between* the shapes glows and
  the shapes carve darkness through it.
- **Per-trace beam mixer** — independent GLOW and PHOSPHOR for the shape, both
  derived circles, and the sphere.
- **MEMORY** — presets auto-named from the shape and its variables
  (`TRIANGLE_A25_B32_C40`), stored in your browser.

Drag the screen to orbit, scroll to zoom, double-click a knob to reset it.
Knobs turn two ways: grab the rim for 1:1 circular tracking, grab the middle
for a vertical fader drag (hold Shift for fine).

## Tests

Headless regression suite drives the panel with synthetic pointer events and
asserts magnitudes (knob sweeps, lattice pitch, drum mode counts, audio pan):

```bash
python3 -m venv venv && ./venv/bin/pip install playwright
./venv/bin/playwright install chromium
./venv/bin/python tests/test_geoscope.py
```

## License

MIT — see [LICENSE](LICENSE). GeoScope is freeware: use it, share it, fork it.
If you fork it or build something on top of it, I'd genuinely love to hear
about it — kev.oue@gmail.com.
