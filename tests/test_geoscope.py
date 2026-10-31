import math, sys
from playwright.sync_api import sync_playwright

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(BASE, exist_ok=True)
errors = []

with sync_playwright() as p:
    import os
    shell = os.path.expanduser(
        "~/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell")
    try:
        b = p.chromium.launch()
    except Exception:
        b = p.chromium.launch(executable_path=shell)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.goto(f"file://{ROOT}/index.html")
    pg.wait_for_timeout(2000)
    pg.screenshot(path=f"{BASE}/shot_default.png")

    # --- vertical drag on SIDE A knob (grab the middle): assert magnitude ---
    a0 = pg.evaluate("__gs.P.triangle.a")
    box = pg.locator("#paramKnobs .knob >> nth=0").locator("svg").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    for i in range(1, 11):
        pg.mouse.move(cx, cy - 9.5 * i)  # 95 px up
    pg.mouse.up()
    a1 = pg.evaluate("__gs.P.triangle.a")
    expected = min(5.0, a0 + 95 / 190 * (5 - 0.6))
    print(f"vertical drag: a {a0:.2f} -> {a1:.2f} (expected ~{expected:.2f})")
    assert abs(a1 - expected) < 0.15, "vertical drag magnitude wrong"

    # --- circular drag on ROT X rim: 90 degree sweep tracks 1:1 ---
    box = pg.locator("#motionKnobs .knob >> nth=0").locator("svg").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    r0 = pg.evaluate("__gs.st.rx")
    pg.mouse.move(cx, cy + 18)          # rim grab at 90 deg
    pg.mouse.down()
    for deg in range(95, 185, 5):       # sweep to 180 deg
        a = math.radians(deg)
        pg.mouse.move(cx + 26 * math.cos(a), cy + 26 * math.sin(a))
    pg.mouse.up()
    r1 = pg.evaluate("__gs.st.rx")
    print(f"circular drag: rotate {r0:.1f} -> {r1:.1f} (expected ~{r0+90:.1f})")
    assert abs((r1 - r0) - 90) < 8, "circular drag did not track 1:1"

    # --- degenerate triangle warns ---
    pg.evaluate("__gs.K.p0.set(0.6); __gs.K.p1.set(0.6); __gs.K.p2.set(4)")
    pg.wait_for_timeout(400)
    ro = pg.locator("#readout").inner_text()
    assert "DEGENERATE" in ro, f"no degenerate warning in readout: {ro}"
    print("degenerate warning: OK")

    # --- icosahedron lattice with both circles ---
    pg.evaluate("""
      __gs.setShape('icosa');
      __gs.K.rows.set(2);
      __gs.T.inner.set(true);
      __gs.K.phos0.set(0.75); __gs.K.phos1.set(0.9);
    """)
    pg.wait_for_timeout(1200)
    copies = pg.evaluate("__gs.st && document.querySelector('#readout').textContent")
    print(f"readout: {copies}")
    pg.screenshot(path=f"{BASE}/shot_icosa.png")

    # --- triangle lattice, cranked rows ---
    pg.evaluate("""
      __gs.setShape('triangle');
      __gs.K.p0.set(2.5); __gs.K.p1.set(3.2); __gs.K.p2.set(4.0);
      __gs.K.rows.set(3);
      __gs.K.spacing.set(1.9);
      __gs.T.inner.set(true);
    """)
    pg.wait_for_timeout(1200)
    pg.screenshot(path=f"{BASE}/shot_tri_lattice.png")

    # --- DRIFT: knobs flow, shape morphs, triangle never degenerates,
    #     and the camera holds its point (no breathing with the morph) ---
    pg.evaluate("__gs.K.rows.set(1); __gs.K.p0.setVary(true); __gs.K.p1.setVary(true); __gs.K.p2.setVary(true)")
    v0 = pg.evaluate("[__gs.P.triangle.a, __gs.P.triangle.b, __gs.P.triangle.c]")
    k0 = pg.locator("#paramKnobs .knob >> nth=0").get_attribute("aria-valuenow")
    d0 = pg.evaluate("__gs.st.dist")
    pg.wait_for_timeout(1800)
    v1 = pg.evaluate("[__gs.P.triangle.a, __gs.P.triangle.b, __gs.P.triangle.c]")
    k1 = pg.locator("#paramKnobs .knob >> nth=0").get_attribute("aria-valuenow")
    d1 = pg.evaluate("__gs.st.dist")
    assert abs(d1 - d0) < 0.15, f"zoom breathed during drift: {d0:.2f} -> {d1:.2f}"
    print(f"zoom held steady during drift: {d0:.2f} -> {d1:.2f}")
    moved = max(abs(x - y) for x, y in zip(v0, v1))
    print(f"drift: sides {['%.2f' % x for x in v0]} -> {['%.2f' % x for x in v1]} (max delta {moved:.2f})")
    assert moved > 0.05, "drift did not move the geometry"
    assert k0 != k1, "knob UI did not move with drift"
    assert "DEGENERATE" not in pg.locator("#readout").inner_text(), "drift made a degenerate triangle"
    pg.screenshot(path=f"{BASE}/shot_drift.png")
    pg.evaluate("__gs.K.p0.setVary(false); __gs.K.p1.setVary(false); __gs.K.p2.setVary(false)")

    # --- per-axis rotation knobs exist and act ---
    pg.evaluate("__gs.K.roty.setVary(false); __gs.K.rotz.set(45); __gs.K.rotx.set(0); __gs.K.roty.set(0)")
    assert pg.evaluate("[__gs.st.rx, __gs.st.ry, __gs.st.rz]") == [0, 0, 45]
    print("per-axis rotation: OK")

    # --- vary box gates rotation: uncheck ROT Y -> rotation stops ---
    pg.evaluate("__gs.K.spin.set(60); __gs.K.roty.setVary(false)")
    r0 = pg.evaluate("__gs.st.ry")
    pg.wait_for_timeout(400)
    assert pg.evaluate("__gs.st.ry") == r0, "rotation ran with ROT Y box unchecked"
    pg.evaluate("__gs.K.roty.setVary(true)")
    pg.wait_for_timeout(400)
    r1 = pg.evaluate("__gs.st.ry")
    assert r1 != r0, "rotation did not resume when ROT Y box checked"
    print(f"vary box gates rotation: {r0:.0f} (held) -> {r1:.0f} (running)")

    # --- new shapes build clean: star, tesseract, torus, lissajous ---
    for sh, token in [("star", "STAR"), ("tess", "TESSERACT"), ("torus", "TORUS"), ("liss", "LISSAJOUS")]:
        pg.evaluate(f"__gs.setShape('{sh}')")
        pg.wait_for_timeout(350)
        ro = pg.locator("#readout").inner_text()
        assert token in ro, f"{sh} readout wrong: {ro}"
    pg.evaluate("__gs.setShape('tess'); __gs.K.p2.setVary(true)")  # 4D tumble via XW vary
    pg.wait_for_timeout(600)
    xw0 = pg.evaluate("__gs.P.tess.xw")
    pg.wait_for_timeout(400)
    xw1 = pg.evaluate("__gs.P.tess.xw")
    assert xw1 != xw0, "tesseract XW vary is not rotating in 4D"
    pg.evaluate("__gs.K.p1.set(4)")  # LEVELS: a 4-deep column along w
    pg.wait_for_timeout(400)
    assert "LV 4" in pg.locator("#readout").inner_text(), "tesseract LEVELS not applied"
    pg.screenshot(path=f"{BASE}/shot_tess.png")
    pg.evaluate("__gs.K.p2.setVary(false); __gs.K.p1.set(2); __gs.setShape('triangle')")
    print(f"new shapes OK; tesseract 4D tumble {xw0:.0f} -> {xw1:.0f}, LEVELS knob OK")

    # --- hero: single triangle with both circles, beam still ---
    pg.evaluate("""
      __gs.K.rows.set(0);
      __gs.K.spin.set(0);
      __gs.K.roty.set(25); __gs.K.rotx.set(12); __gs.K.rotz.set(0);
      __gs.K.phos0.set(0.5);
      __gs.T.orbit.set(false);
      __gs.K.p0.set(2.5); __gs.K.p1.set(3.2); __gs.K.p2.set(4.0);
    """)
    pg.wait_for_timeout(1200)
    pg.screenshot(path=f"{BASE}/shot_hero.png")

    # --- deep zoom: wheel and ZOOM knob drive the same value ---
    cbox = pg.locator("#beam").bounding_box()
    pg.mouse.move(cbox["x"] + cbox["width"] / 2, cbox["y"] + cbox["height"] / 2)
    z0 = pg.evaluate("__gs.K.zoom.get()")
    pg.mouse.wheel(0, -800)
    z1 = pg.evaluate("__gs.K.zoom.get()")
    assert z1 > z0, "wheel did not move the zoom knob"
    pg.evaluate("__gs.K.zoom.set(0.95); __gs.K.rows.set(1); __gs.T.orbit.set(true); __gs.K.spin.set(22)")
    pg.wait_for_timeout(1600)
    dist = pg.evaluate("__gs.st.dist")
    print(f"deep zoom: dist {dist:.2f} (camera inside the lattice)")
    assert dist < 3, "camera did not dolly in close"
    pg.screenshot(path=f"{BASE}/shot_close.png")

    # --- audio: the shape is the waveform ---
    pg.locator("#audioBtnBox .tgl >> nth=0").click()
    pg.wait_for_timeout(600)
    au = pg.evaluate("({has: !!__gs.AU.ctx, state: __gs.AU.ctx ? __gs.AU.ctx.state : 'none', dbg: __gs.AU.dbg, on: __gs.AU.on})")
    print(f"audio: ctx={au['state']} on={au['on']} spectrum-energy={au['dbg']:.3f}")
    if au["has"]:
        assert au["dbg"] > 0.05, "waveform spectrum is empty"
        e1 = au["dbg"]
        pg.evaluate("__gs.setShape('circle')")
        pg.wait_for_timeout(500)
        e2 = pg.evaluate("__gs.AU.dbg")
        print(f"audio timbre: triangle {e1:.3f} -> circle {e2:.3f}")
        assert abs(e2 - e1) > 1e-4, "timbre did not change with shape"

        # pitch source dropdown: SIZE drives frequency
        pg.select_option("#modSel", "size")
        pg.evaluate("__gs.setShape('cube'); __gs.K.p0.set(0.6)")
        pg.wait_for_timeout(400)
        f1 = pg.evaluate("__gs.AU.lastF")
        pg.evaluate("__gs.K.p0.set(3.4)")
        pg.wait_for_timeout(400)
        f2 = pg.evaluate("__gs.AU.lastF")
        print(f"pitch mod by SIZE: {f1:.1f} Hz -> {f2:.1f} Hz")
        assert f2 > f1 * 1.5, "size modulation did not raise pitch"

        # scope traces of the live audio, framed for a look
        pg.evaluate("""
          __gs.K.zoom.set(0.25); __gs.K.rows.set(0); __gs.K.spin.set(30);
          __gs.T.orbit.set(false); __gs.K.p0.set(2.2);
        """)
        pg.wait_for_timeout(1000)
        pg.screenshot(path=f"{BASE}/shot_audio.png")

        # SPACE voice: the in-between sounds different from the outline
        o1 = pg.evaluate("__gs.AU.dbg")
        pg.select_option("#voiceSel", "space")
        pg.wait_for_timeout(400)
        o2 = pg.evaluate("__gs.AU.dbg")
        print(f"voice: outline {o1:.3f} -> space {o2:.3f}")
        assert abs(o2 - o1) > 1e-4, "space voice did not change the wave"
        pg.select_option("#voiceSel", "outline")
        pg.select_option("#modSel", "manual")

        # the rider pans the emphasis ear to ear
        pg.evaluate("__gs.K.ride.set(1.0)")
        ps = []
        for _ in range(3):
            ps.append(pg.evaluate("__gs.AU.pan"))
            pg.wait_for_timeout(250)
        print(f"rider pan sweep: {['%.2f' % p for p in ps]}")
        assert max(ps) - min(ps) > 0.02, "rider is not moving the pan"
        pg.evaluate("__gs.T.inv.set(true)")
        assert pg.evaluate("__gs.AU.inv") is True
        pg.evaluate("__gs.T.inv.set(false)")

        # DRUM voice: struck modal synthesis — the rider is the mallet
        pg.evaluate("__gs.setShape('triangle')")
        pg.select_option("#voiceSel", "drum")
        pg.evaluate("__gs.K.ride.set(2.0)")
        s0 = pg.evaluate("__gs.AU.strikes")
        pg.wait_for_timeout(1300)
        s1 = pg.evaluate("__gs.AU.strikes")
        mn = pg.evaluate("__gs.AU.modesN")
        print(f"drum: strikes {s0} -> {s1}, modes per strike {mn}")
        assert s0 >= 1, "no strike on voice switch"
        assert s1 > s0, "drum did not strike on rider laps"
        assert mn >= 10, f"triangle Weyl spectrum too thin: {mn}"
        pg.evaluate("__gs.setShape('circle')")
        pg.wait_for_timeout(700)
        assert pg.evaluate("__gs.AU.modesN") == 12, "circle did not use Bessel drumhead modes"
        pg.select_option("#voiceSel", "outline")
        pg.evaluate("__gs.setShape('cube')")
        print("drum voice: OK")

        # declick: wave morphs by crossfading two pairs, and static geometry
        # must not trigger updates at all
        pg.evaluate("__gs.K.spin.set(0)")
        pg.wait_for_timeout(400)
        act0 = pg.evaluate("__gs.AU.active")
        sig0 = pg.evaluate("__gs.AU.sig")
        pg.wait_for_timeout(500)
        assert pg.evaluate("__gs.AU.active") == act0, "pairs flipped with static geometry"
        assert pg.evaluate("__gs.AU.sig") == sig0, "wave rebuilt with static geometry"
        pg.evaluate("__gs.setShape('tetra')")
        pg.wait_for_timeout(300)
        act1 = pg.evaluate("__gs.AU.active")
        assert pg.evaluate("__gs.AU.pairs.length") == 2 and act1 != act0, "crossfade pair did not alternate"
        print(f"declick: static=no updates, morph=crossfade pair {act0}->{act1}: OK")
        pg.locator("#audioBtnBox .tgl >> nth=0").click()
        pg.evaluate("__gs.setShape('triangle')")
    else:
        print("  (no audio backend in headless shell - visual/logic paths still verified)")
    pg.evaluate("__gs.K.zoom.set(0.12)")

    # --- sphere space: lat/lon lines add/subtract, radius resizes the space ---
    import re
    pg.evaluate("__gs.K.rows.set(2); __gs.K.spin.set(0); __gs.K.ballr.set(14)")
    pg.wait_for_timeout(500)
    c_big = int(re.search(r"COPIES (\d+)", pg.locator("#readout").inner_text()).group(1))
    pg.evaluate("__gs.K.ballr.set(5)")
    pg.wait_for_timeout(500)
    c_small = int(re.search(r"COPIES (\d+)", pg.locator("#readout").inner_text()).group(1))
    print(f"sphere radius capacity: R14 -> {c_big} copies, R5 -> {c_small} copies")
    assert c_small < c_big, "shrinking the sphere did not squeeze out copies"
    pg.evaluate("__gs.K.ballr.set(9); __gs.K.lat.set(10); __gs.K.lon.set(10)")
    pg.wait_for_timeout(400)
    pg.screenshot(path=f"{BASE}/shot_sphere.png")
    pg.evaluate("__gs.K.lat.set(0); __gs.K.lon.set(0)")   # all lines off
    pg.wait_for_timeout(300)
    pg.evaluate("__gs.K.lat.set(5); __gs.K.lon.set(6)")
    print("sphere lat/lon knobs: OK")

    # --- panel grab-scroll: drag empty chassis, controls keep their drags ---
    pg.evaluate("document.querySelector('aside.panel').scrollTop = 0")
    gb = pg.locator("aside.panel .group >> nth=0").bounding_box()
    pg.mouse.move(gb["x"] + 8, gb["y"] + 6)
    pg.mouse.down()
    for i in range(10):
        pg.mouse.move(gb["x"] + 8, gb["y"] + 6 - 20 * i)
    pg.mouse.up()
    s1 = pg.evaluate("document.querySelector('aside.panel').scrollTop")
    print(f"panel grab-scroll: 0 -> {s1:.0f}")
    assert s1 > 50, "panel did not scroll by grabbing the chassis"

    # --- CONNECT: lattice pitch equals the shape's own extent, copies fuse ---
    pg.evaluate("""
      __gs.setShape('cube');
      __gs.K.p0.set(2.2); __gs.K.p1.set(1.0); __gs.K.p2.set(1.0); __gs.K.p3.set(1.0);
      __gs.K.rows.set(1); __gs.K.spacing.set(1.0);
      __gs.K.roty.setVary(false); __gs.K.rotx.set(0); __gs.K.roty.set(0); __gs.K.rotz.set(0);
      __gs.T.connect.set(true); __gs.T.orbit.set(false); __gs.K.spin.set(0);
    """)
    pg.wait_for_timeout(400)
    pitch = pg.evaluate("__gs.st._pitch")
    expect = 2 * 2.2 / math.sqrt(3)
    print(f"connect pitch: {pitch[0]:.3f} (cube face-to-face = {expect:.3f})")
    assert abs(pitch[0] - expect) < 0.03, "connected cubes do not share faces"
    pg.screenshot(path=f"{BASE}/shot_connect.png")
    pg.evaluate("__gs.setShape('rect')")
    pg.wait_for_timeout(300)
    pitch = pg.evaluate("__gs.st._pitch")
    assert abs(pitch[0] - 3.4) < 0.03 and abs(pitch[1] - 2.0) < 0.03, f"rect brick pitch wrong: {pitch}"
    print("rect tiles brick-exact: OK")
    pg.evaluate("__gs.setShape('triangle'); __gs.K.roty.setVary(true)")

    # --- MEMORY presets: auto-name, save, mutate, restore ---
    pg.evaluate("__gs.setShape('triangle'); __gs.K.p0.set(2.5); __gs.K.p1.set(3.2); __gs.K.p2.set(4.0)")
    name = pg.evaluate("__gs.mem.save('')")
    print(f"preset saved as: {name}")
    assert name.startswith("TRIANGLE_A25_B32_C40"), f"bad auto-name: {name}"
    name2 = pg.evaluate("__gs.mem.save('my fave')")
    assert name2 == "TRIANGLE_A25_B32_C40_MY_FAVE", f"bad suffixed name: {name2}"
    pg.evaluate("__gs.setShape('cube'); __gs.K.p0.set(1.0); __gs.K.rows.set(3)")
    pg.evaluate("__gs.mem.load(0)")
    pg.wait_for_timeout(300)
    assert pg.evaluate("__gs.st.shape") == "triangle", "preset did not restore shape"
    a = pg.evaluate("__gs.P.triangle.a")
    rows = pg.evaluate("__gs.st.rows")
    assert abs(a - 2.5) < 1e-6 and rows != 3, f"preset did not restore values: a={a} rows={rows}"
    print("preset load restores shape, params, array: OK")

    # --- NEGATIVE: the lit space, carved by the moving shapes ---
    pg.evaluate("""
      __gs.T.neg.set(true); __gs.K.spin.set(45); __gs.K.phos0.set(0.85);
      __gs.K.rows.set(1); __gs.K.zoom.set(0.12); __gs.T.orbit.set(true);
    """)
    pg.wait_for_timeout(2000)
    pg.screenshot(path=f"{BASE}/shot_negative.png")
    pg.evaluate("__gs.T.neg.set(false)")
    print("negative mode: OK")

    # fps sanity: count frames over 2s
    fps = pg.evaluate("""new Promise(res => {
      let n = 0; const t0 = performance.now();
      function tick(){ n++; if (performance.now() - t0 < 2000) requestAnimationFrame(tick); else res(n/2); }
      requestAnimationFrame(tick);
    })""")
    print(f"fps with 3-row triangle lattice: {fps:.0f}")
    b.close()

if errors:
    print("ERRORS:"); [print(" ", e) for e in errors]; sys.exit(1)
print("ALL OK")
