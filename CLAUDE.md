# GeoScope GS-1

An oscilloscope-styled shape synthesizer. **One self-contained file** —
`index.html` holds all CSS and JS, no libraries, no build step. That is a
feature, not an accident: keep it single-file.

- **Live:** https://kevinoue.com/geoscope/ (freeware, MIT + friendly fork-notify
  ask in LICENSE)
- **Also published as a claude.ai artifact:**
  https://claude.ai/code/artifact/22f8e123-2961-4992-8b52-e8aaced87ff0
  (the artifact flavor omits the doctype/head/body skeleton — the wrapper adds it)

## Deploy

The site is a plain Caddy `file_server` on the Synology NAS. scp does NOT work
against DSM — pipe through ssh:

```bash
cat index.html | ssh -i ~/.ssh/id_ed25519_nas PROXIMA@192.168.50.3 \
  "cat > /volume1/docker/kevinoue/site/geoscope/index.html"
```

No restart needed; Caddy serves from disk. The portfolio card lives in
`/volume1/docker/kevinoue/site/index.html` (single file, images inlined —
back it up as `index.html.bak-<date>` before touching it, their convention).

## Tests

```bash
./venv/bin/python tests/test_geoscope.py   # venv: pip install playwright
```

The suite's philosophy (borrowed from Aurora): drive controls with synthetic
pointer events and assert **magnitudes**, not just that something changed.
Keep it green; it covers knob gestures, vary gating, lattice pitch, all three
audio voices, declick, presets, and fps.

## Architecture notes (the ones that prevent regressions)

- **Rendering:** Canvas 2D, hand-rolled 3D projection, additive 'lighter'
  compositing. Each trace channel (CH1 shape / CH2 outer / CH3 inner / sphere)
  accumulates in its own offscreen layer with independent glow + phosphor fade;
  `beamC` is their per-frame composite. LYNCHPINS carves from that composite.
- **Depth batching:** copies bucket into 4 depth bins; one Path2D per
  (bucket, channel) keeps stroke calls ~constant regardless of lattice size.
- **Near-plane:** segments are *clipped* at NEAR, never culled whole — that is
  what makes the zoom flythrough possible.
- **Audio:** two phase-locked oscillator pairs crossfade on every wavetable
  change (never call setPeriodicWave on the audible pair — it clicks, worst at
  low Hz). A geometry signature skips updates when nothing moved. DRUM voice
  mutes the pairs and fires throwaway osc+gain partials per strike.
- **Camera:** zoom is set-and-stay (knob + wheel share one value). Kevin
  explicitly rejected auto-framing tied to content extent — do not reintroduce.
- **Kevin's vocabulary:** "lynchpins" = the in-between structures; the glow
  belongs *inside the geometry's mass*, never the whole sphere.
- Knob gestures copied from Aurora's Knob.tsx: rim grab = circular 1:1,
  middle = vertical fader, Shift = fine, 270° sweep bounded / endless for
  rotations. Every value knob carries a vary checkbox (VARY map).
