/* Per-unit specs for the generated 3-view line drawings, and the renderer.
 * Draw3V.render(entry) -> { body, views } laid out in the blueprint's drawing
 * area, or null when the unit has no spec. Sizes are metres from published
 * figures; detail is representative, not a factory drawing.
 */
(function (global) {
  "use strict";
  const D = global.Draw3VParts, F = global.Draw3VFamilies;
  const { poly, line, seg, circ, rect, path, rot, range } = D;
  const COS = (d) => Math.cos(d * Math.PI / 180), SIN = (d) => Math.sin(d * Math.PI / 180);

  // Merge extra parts (drawn on top, so they occlude what's behind) into a view set.
  function add(v, m) {
    return {
      ...v, side: v.side + (m.side || ""), top: v.top + (m.top || ""), front: v.front + (m.front || ""),
      H: Math.max(v.H, m.H || 0), W: Math.max(v.W, m.W || 0),
      xmin: Math.min(v.xmin, m.xmin ?? Infinity), xmax: Math.max(v.xmax, m.xmax ?? -Infinity),
    };
  }

  /* Missiles or canisters on a launcher. Tail (pivot) at (tx, ty), pointing forward
   * (-x) and up at elev degrees. cols = lateral positions, rows stacked above. */
  function rack(o) {
    const { L, d, tx, ty, elev = 0, cols = [0], rows = 1, kind = "missile", gap = 1.15 } = o;
    const c = COS(elev), s = SIN(elev), nx = tx - L * c, ny = ty + L * s;
    const item = (len) => (kind === "canister" ? D.canister(len, d, o.ribs ?? 4) : D.missile(len, d, o.fin || 1, o.canards !== false));
    let side = "", top = "", front = "";
    for (let j = rows - 1; j >= 0; j--) {
      const oy = j * d * gap;
      side += rot(item(L), nx - oy * s, ny + oy * c, -elev);
    }
    for (const y of cols) top += rot(item(L * c || 0.01), nx, y, 0);
    for (const y of cols) for (let j = 0; j < rows; j++) {
      const oy = j * d * gap * c;
      if (kind === "canister") front += rect(y - d / 2, ty + oy, d, Math.max(d, L * s), "k1") + circ(y, ny + oy - d / 2, d * 0.32, "k3", false);
      else front += rect(y - d / 4, ty + oy, d / 2, Math.max(d / 2, L * s), "k1") + circ(y, ny + oy, d / 2) + seg(y - d * 1.4, ty + oy + 0.05, y + d * 1.4, ty + oy + 0.05, "k2") + seg(y, ty + oy - d, y, ty + oy + d * 1.2, "k2");
    }
    return { side, top, front, H: ny + rows * d * gap + 0.1, xmin: nx - 0.1 };
  }

  // A rotating radar: mast + dish or array, side / top / front.
  function radar(o) {
    const { x, y, w, h = w * 0.3, kind = "array", mast = 0.3, tilt = 0 } = o;
    let side = "", top = "", front = "";
    if (mast > 0) side += rect(x - 0.08, y, 0.16, mast, "k2");
    const yy = y + mast;
    if (kind === "dish") {
      side += D.dish(x, yy + w * 0.12, w, 90 + tilt);
      top += rot(path(`M ${-w / 2} 0 Q 0 ${w * 0.3} ${w / 2} 0 Z`, "k1"), x, 0, 90);
      front += circ(0, yy + w / 2, w / 2) + circ(0, yy + w / 2, w * 0.38, "k3", false) + circ(0, yy + w / 2, w * 0.06, "k2", false);
    } else {
      side += rot(rect(-0.12, 0, 0.24, h, "k1") + seg(0, 0, 0, h, "k3"), x, yy, -tilt);
      top += rect(x - 0.12, -w / 2, 0.24, w, "k1") + seg(x, -w / 2, x, w / 2, "k3");
      front += D.arrayPanel(-w / 2, yy, w, h, Math.max(4, Math.round(w * 2)), 3);
    }
    if (mast > 0) front += rect(-0.08, y, 0.16, mast, "k2");
    return { side, top, front, H: yy + (kind === "dish" ? w : h) };
  }

  // Gun cluster of n barrels in a side-by-side row, front view only.
  function muzzles(xs, y, d) { return xs.map((x) => D.muzzle(x, y, d)).join(""); }

  /* Box turret on a hull (for SPAAG / SAM vehicles). */
  function boxTurret(x0, len, y0, h, w) {
    return {
      side: poly([[x0, y0], [x0 - 0.1, y0 + h * 0.55], [x0 + 0.15, y0 + h], [x0 + len - 0.1, y0 + h], [x0 + len, y0 + h * 0.6], [x0 + len, y0]]) + seg(x0 + 0.05, y0 + 0.06, x0 + len, y0 + 0.06, "k3"),
      top: poly([[x0, -w * 0.4], [x0 + 0.25, -w / 2], [x0 + len, -w / 2], [x0 + len, w / 2], [x0 + 0.25, w / 2], [x0, w * 0.4]]) + D.hatchTop(x0 + len * 0.6, -w * 0.2, 0.25) + D.hatchTop(x0 + len * 0.6, w * 0.2, 0.25),
      front: poly([[-w / 2, y0], [-w / 2 + 0.1, y0 + h], [w / 2 - 0.1, y0 + h], [w / 2, y0]]) + seg(-w / 2 + 0.05, y0 + 0.06, w / 2 - 0.05, y0 + 0.06, "k3"),
      H: y0 + h,
    };
  }

  // ===================================================================== tanks
  const TANK = {
    // WWII
    Pz_IV_H: () => F.armour({ hullL: 5.9, W: 2.88, hullH: 1.8, glacis: 0.6, track: { n: 8, r: 0.235, returns: 4, sprocket: "front", style: "rubber", skirt: "plate", skirtTop: 1.75 }, trackW: 0.4,
      turret: { x: 2.7, len: 2.3, w: 2.2, h: 0.78, shape: "box", cupolaX: 3.4, cupolaR: 0.3, cupolaH: 0.2, mg: false }, gun: { len: 3.65, d: 0.11, brake: true } }),
    Pz_V_Panther_G: () => F.armour({ hullL: 6.87, W: 3.27, hullH: 1.85, glacis: 2.0, track: { n: 8, r: 0.43, interleave: true, sprocket: "front", style: "steel", skirt: "plate", skirtTop: 1.8 }, trackW: 0.66,
      turret: { x: 3.1, len: 2.7, w: 2.4, h: 0.95, shape: "box", cupolaX: 3.9, mg: true }, gun: { len: 5.25, d: 0.12, brake: true } }),
    Tiger_I: () => F.armour({ hullL: 6.3, W: 3.56, hullH: 1.95, glacis: 0.5, track: { n: 8, r: 0.4, interleave: true, sprocket: "front", style: "steel" }, trackW: 0.72,
      hullPts: [[0, 0.55], [-0.1, 0.9], [0.05, 1.35], [0.2, 1.95], [6.1, 1.95], [6.3, 1.5], [6.3, 0.6]],
      turret: { x: 3.1, len: 3.0, w: 2.6, h: 0.95, shape: "box", cupolaX: 3.9 }, gun: { len: 4.9, d: 0.14, brake: true }, fenderBoxes: [[4.6, 1.2]] }),
    Tiger_II_H: () => F.armour({ hullL: 7.38, W: 3.75, hullH: 1.9, glacis: 2.1, track: { n: 9, r: 0.4, interleave: true, sprocket: "front", style: "steel" }, trackW: 0.8,
      turret: { x: 3.7, len: 3.4, w: 2.6, h: 1.05, shape: "slab", bustle: 0.6, cupolaX: 4.5 }, gun: { len: 6.3, d: 0.14, brake: true } }),
    M4_Sherman: () => F.armour({ hullL: 5.84, W: 2.62, hullH: 1.95, glacis: 1.5, track: { n: 6, r: 0.255, returns: 3, sprocket: "front", style: "spoked" }, trackW: 0.42,
      turret: { x: 2.6, len: 2.35, w: 2.0, h: 0.85, shape: "cast", cupolaR: 0.28, cupolaH: 0.18 }, gun: { len: 2.8, d: 0.1 } }),
    M4A4_Sherman_FF: () => F.armour({ hullL: 6.06, W: 2.62, hullH: 1.95, glacis: 1.5, track: { n: 6, r: 0.255, returns: 3, sprocket: "front", style: "spoked" }, trackW: 0.42,
      turret: { x: 2.7, len: 2.35, w: 2.0, h: 0.85, shape: "cast", bustle: 0.65, cupolaR: 0.28, cupolaH: 0.18 }, gun: { len: 4.4, d: 0.11, brake: true } }),
    Cromwell_IV: () => F.armour({ hullL: 6.35, W: 3.0, hullH: 1.75, glacis: 0.45, track: { n: 5, r: 0.4, sprocket: "rear", style: "spoked" }, trackW: 0.5,
      hullPts: [[0, 0.5], [-0.05, 0.9], [0.05, 1.75], [6.2, 1.75], [6.35, 1.5], [6.35, 0.55]],
      turret: { x: 2.5, len: 2.0, w: 1.95, h: 0.8, shape: "box", cupolaR: 0.28 }, gun: { len: 2.8, d: 0.1, brake: true } }),
    Churchill_VII: () => F.armour({ hullL: 7.44, W: 3.25, hullH: 1.9, glacis: 0.4, track: { n: 11, r: 0.17, sprocket: "rear", style: "steel", skirt: "panel", skirtTop: 1.35 }, trackW: 0.56,
      hullPts: [[0, 0.3], [-0.2, 1.3], [0.15, 1.9], [7.3, 1.9], [7.44, 1.4], [7.44, 0.35]],
      turret: { x: 3.0, len: 2.1, w: 2.0, h: 0.75, shape: "cast", cupolaR: 0.28 }, gun: { len: 2.8, d: 0.1 } }),
    "T-34-85": () => F.armour({ hullL: 6.1, W: 3.0, hullH: 1.55, glacis: 1.7, track: { n: 5, r: 0.42, sprocket: "rear", style: "spoked" }, trackW: 0.5, drums: true,
      turret: { x: 2.4, len: 3.0, w: 2.3, h: 0.95, shape: "cast", cupolaX: 3.0 }, gun: { len: 4.7, d: 0.11, sleeve: [0.4] } }),
    // Cold War / modern
    "T-55": () => F.armour({ hullL: 6.45, W: 3.27, hullH: 1.5, glacis: 1.3, track: { n: 5, r: 0.41, sprocket: "rear", style: "spoked" }, trackW: 0.58, drums: true,
      turret: { x: 2.3, len: 2.4, w: 2.2, h: 0.85, shape: "dome", ir: true, cupolaX: 2.6 }, gun: { len: 5.3, d: 0.15, evac: 0.78 } }),
    T62M: () => F.armour({ hullL: 6.63, W: 3.3, hullH: 1.5, glacis: 1.3, track: { n: 5, r: 0.41, sprocket: "rear", style: "spoked", skirt: "rubber", skirtTop: 1.0 }, trackW: 0.58, drums: true,
      turret: { x: 2.5, len: 2.6, w: 2.3, h: 0.85, shape: "dome", ir: true, cupolaX: 2.9, era: true }, gun: { len: 5.7, d: 0.16, evac: 0.55, sleeve: [0.3] } }),
    "M-60": () => F.armour({ hullL: 6.95, W: 3.63, hullH: 1.85, glacis: 1.6, track: { n: 6, r: 0.33, returns: 3, sprocket: "rear", style: "rubber" }, trackW: 0.7,
      turret: { x: 3.2, len: 3.2, w: 2.9, h: 1.0, shape: "cast", bustle: 0.65, cupolaR: 0.45, cupolaH: 0.38, cupolaX: 3.6, smoke: true }, gun: { len: 5.5, d: 0.16, evac: 0.55 } }),
    "M-1 Abrams": () => F.armour({ hullL: 7.92, W: 3.66, hullH: 1.45, glacis: 1.4, track: { n: 7, r: 0.32, returns: 2, sprocket: "rear", style: "rubber", skirt: "panel", skirtTop: 1.25 }, trackW: 0.64, exhaust: true,
      turret: { x: 3.25, len: 4.0, w: 3.5, h: 0.85, shape: "slab", bustle: 0.9, cupolaR: 0.35, cupolaH: 0.25, cupolaX: 4.0, smoke: true, antenna: true }, gun: { len: 5.3, d: 0.19, evac: 0.45, mrs: true } }),
    // Fallbacks for units that normally use a real drawing (fetched at build, may be missing)
    "T-72B": () => t72({}), "T-72B3": () => t72({ era: true }), "T-90": () => t72({ era: true, shtora: true, W: 3.78 }),
    "T-80B": () => t80({}), "T-80UD": () => t80({ era: true }),
    PT_76: () => F.armour({ hullL: 7.63, W: 3.14, hullH: 1.65, glacis: 1.6, track: { n: 6, r: 0.35, sprocket: "rear", style: "spoked" }, trackW: 0.36,
      hullPts: [[0, 0.7], [-0.15, 1.1], [1.6, 1.65], [7.5, 1.65], [7.63, 1.3], [7.63, 0.6]],
      turret: { x: 2.6, len: 2.2, w: 2.1, h: 0.6, shape: "cast", cupolaR: 0.25, cupolaH: 0.15 }, gun: { len: 3.6, d: 0.1, brake: true, evac: 0.6 } }),
    Leopard1A3: () => F.armour({ hullL: 7.09, W: 3.37, hullH: 1.6, glacis: 1.1, track: { n: 7, r: 0.35, returns: 4, sprocket: "rear", style: "rubber", skirt: "rubber", skirtTop: 1.15 }, trackW: 0.55, exhaust: true,
      turret: { x: 3.0, len: 3.2, w: 2.8, h: 0.95, shape: "slab", bustle: 0.6, cupolaR: 0.35, cupolaX: 3.5, smoke: true }, gun: { len: 5.5, d: 0.16, evac: 0.45, sleeve: [0.2, 0.6] } }),
    "leopard-2A4": () => leo2(false), "Leopard-2A5": () => leo2(true),
    "BMP-3": () => F.armour({ hullL: 7.14, W: 3.3, hullH: 1.65, glacis: 1.6, ribbedGlacis: true, track: { n: 6, r: 0.33, returns: 3, sprocket: "rear", style: "steel" }, trackW: 0.45,
      turret: { x: 3.4, len: 2.1, w: 2.1, h: 0.6, shape: "ifv", cupola: false }, gun: { len: 3.4, d: 0.17, elev: 2, sleeve: [0.5] } }),
    M1A2C_SEP_V3: () => add(F.armour({ hullL: 7.92, W: 3.66, hullH: 1.45, glacis: 1.4, track: { n: 7, r: 0.32, returns: 2, sprocket: "rear", style: "rubber", skirt: "panel", skirtTop: 1.25 }, trackW: 0.64, exhaust: true,
      turret: { x: 3.25, len: 4.0, w: 3.5, h: 0.85, shape: "slab", bustle: 0.9, cupolaR: 0.35, cupolaH: 0.25, cupolaX: 4.0, smoke: true, antenna: true }, gun: { len: 5.3, d: 0.19, evac: 0.45, mrs: true } }),
      { side: D.box(3.9, 2.55, 0.7, 0.42) + D.box(2.0, 2.3, 0.5, 0.45), front: rect(0.4, 2.55, 0.7, 0.42, "k2") + rect(-1.3, 2.3, 0.5, 0.45, "k2"), H: 3.0 }),
  };

  function t72(o) {
    return F.armour({ hullL: 6.95, W: o.W || 3.59, hullH: 1.45, glacis: 1.5, eraHull: o.era, track: { n: 6, r: 0.375, returns: 3, sprocket: "rear", style: "steel", skirt: "rubber", skirtTop: 1.05 }, trackW: 0.58, drums: true,
      turret: { x: 2.7, len: 2.9, w: 2.9, h: 0.8, shape: "dome", era: o.era, shtora: o.shtora, cupolaX: 3.4, cupolaR: 0.3, smoke: true }, gun: { len: 6.0, d: 0.18, evac: 0.5, sleeve: [0.25, 0.55] } });
  }
  function t80(o) {
    return F.armour({ hullL: 7.0, W: 3.6, hullH: 1.45, glacis: 1.5, eraHull: o.era, track: { n: 6, r: 0.335, returns: 5, sprocket: "rear", style: "rubber", skirt: "rubber", skirtTop: 1.0 }, trackW: 0.58, exhaust: true,
      turret: { x: 2.8, len: 2.9, w: 2.9, h: 0.8, shape: "dome", era: o.era, cupolaX: 3.4, cupolaR: 0.3, smoke: true }, gun: { len: 6.0, d: 0.18, evac: 0.5, sleeve: [0.25, 0.55] } });
  }
  function leo2(a5) {
    const v = F.armour({ hullL: 7.72, W: 3.7, hullH: 1.55, glacis: 1.2, track: { n: 7, r: 0.35, returns: 4, sprocket: "rear", style: "rubber", skirt: "panel", skirtTop: 1.2 }, trackW: 0.63, exhaust: true,
      turret: { x: 3.4, len: 3.9, w: 3.5, h: 0.9, shape: "slab", bustle: 0.9, cupolaR: 0.35, cupolaX: 4.1, smoke: true }, gun: { len: 5.3, d: 0.19, evac: 0.42, mrs: true } });
    // 2A5: spaced wedge armour on the turret front
    return a5 ? add(v, { side: poly([[1.45, 1.55], [0.5, 1.75], [1.45, 2.45]]), top: poly([[1.45, -1.75], [0.3, 0], [1.45, 1.75]], "k2") + rot(D.barrel(0, 0, { len: 5.3, d: 0.19, evac: 0.42 }), 1.55, 0, 180), xmin: v.xmin }) : v;
  }

  // ============================================================ IFV / APC
  function bmp2() {
    const v = F.armour({ hullL: 6.72, W: 3.15, hullH: 1.6, glacis: 1.8, ribbedGlacis: true, track: { n: 6, r: 0.35, returns: 3, sprocket: "front", style: "steel" }, trackW: 0.42, rearDoor: true,
      hullPts: [[0, 0.55], [-0.1, 0.85], [1.8, 1.6], [6.6, 1.6], [6.72, 1.4], [6.72, 0.55]],
      turret: { x: 2.9, len: 1.9, w: 1.9, h: 0.55, shape: "ifv", cupola: false, atgm: true }, gun: { len: 3.0, d: 0.07, elev: 4, sleeve: [0.5] }, extraH: 2.45 });
    return v;
  }
  function bradley(pod) {
    const v = F.armour({ hullL: 6.55, W: 3.6, hullH: 2.0, glacis: 1.0, track: { n: 6, r: 0.3, returns: 3, sprocket: "front", style: "rubber", skirt: "panel", skirtTop: 1.15 }, trackW: 0.55, rearDoor: true,
      hullPts: [[0, 0.55], [-0.05, 1.1], [1.0, 2.0], [6.4, 2.0], [6.55, 1.8], [6.55, 0.55]],
      turret: { x: 3.0, len: 2.5, w: 2.4, h: 0.8, shape: "slab", cupola: false, tow: !pod, smoke: true }, gun: { len: 2.6, d: 0.085, elev: 3, sleeve: [0.6] } });
    if (!pod) return v;
    return add(v, { side: D.box(2.7, 2.35, 1.4, 0.55) + rack({ L: 1.5, d: 0.22, tx: 4.2, ty: 2.95, elev: 5, kind: "canister", rows: 2, ribs: 2 }).side,
      front: rect(-1.6, 2.35, 0.55, 0.55, "k1") + range(-1.55, -1.1, 2).map((x) => circ(x + 0.12, 2.48, 0.09, "k3", false) + circ(x + 0.12, 2.75, 0.09, "k3", false)).join(""), H: 3.4 });
  }
  function m113(extra) {
    const v = F.armour({ hullL: 4.86, W: 2.69, hullH: 1.85, glacis: 0.9, track: { n: 5, r: 0.31, sprocket: "front", style: "steel" }, trackW: 0.38, rearDoor: true,
      hullPts: [[0, 0.5], [-0.05, 0.9], [0.9, 1.85], [4.75, 1.85], [4.86, 1.7], [4.86, 0.5]], extraH: 2.5 });
    return extra ? add(v, extra) : add(v, { side: D.cupola(2.0, 1.85, 0.4, 0.3, true) + rect(1.4, 1.85, 0.06, 0.6, "k3"), front: rect(-0.6, 1.85, 0.8, 0.3, "k2") + rect(-0.45, 2.2, 0.5, 0.08, "k2"), H: 2.5 });
  }
  function halftrack(us) {
    const L = us ? 6.18 : 5.8, W = us ? 2.2 : 2.1, H = us ? 2.3 : 1.75;
    const tr = D.trackSide({ x0: us ? 3.0 : 2.4, x1: L - 0.15, n: us ? 4 : 6, r: us ? 0.26 : 0.3, sprocket: "front", interleave: !us, returns: us ? 1 : 0, style: us ? "rubber" : "steel" });
    const hb = us ? 1.65 : 1.55;
    let side = "", top = "", front = "";
    if (us) {
      side += poly([[0, 0.65], [0, 1.3], [1.6, 1.4], [1.9, hb], [L, hb], [L, 0.6], [3.0, 0.6], [2.1, 0.75], [1.6, 0.75]]);
      side += D.grille(0.05, 0.4, 0.75, 0.5, 6) + rect(-0.2, 0.55, 0.25, 0.25, "k2");                      // winch roller
      side += poly([[1.95, hb], [2.05, 2.15], [2.15, 2.15], [2.15, hb]], "k2");                               // windscreen
      side += rect(3.2, hb, 0.06, 0.55, "k3") + D.cupola(3.0, hb + 0.4, 0.3, 0.12, true);
    } else {
      side += poly([[0, 0.7], [0.1, 1.05], [1.3, 1.35], [1.9, hb], [L - 0.35, hb], [L, 0.75], [L - 0.3, 0.55], [2.0, 0.55], [0.8, 0.55]]);
      side += line([[0.15, 1.05], [1.2, 1.3]], "k3") + D.grille(0.6, 1.2, 1.12, 0.12, 6);
      side += poly([[2.6, hb], [2.6, hb + 0.4], [3.0, hb + 0.42], [3.0, hb]], "k2") + rect(2.85, hb + 0.3, 0.05, 0.12, "k3");    // MG shield
      side += rot(D.barrel(0, 0, { len: 1.1, d: 0.05 }), 2.7, hb + 0.25, 180);
    }
    side += tr.s;
    side += path(`M 0.25 0.45 A 0.55 0.55 0 0 0 1.45 0.45`, "k2", false) + D.wheel(0.85, us ? 0.45 : 0.45, 0.45, "tyre");
    top += D.trackTop(us ? 3.0 : 2.4, L - 0.15, -W / 2, 0.3) + D.trackTop(us ? 3.0 : 2.4, L - 0.15, W / 2 - 0.3, 0.3);
    top += poly(us ? [[0, -0.7], [1.7, -0.75], [1.9, -W / 2 + 0.05], [L, -W / 2 + 0.05], [L, W / 2 - 0.05], [1.9, W / 2 - 0.05], [1.7, 0.75], [0, 0.7]]
      : [[0, -0.45], [1.3, -0.7], [1.9, -W / 2 + 0.1], [L - 0.35, -W / 2 + 0.1], [L, -0.6], [L, 0.6], [L - 0.35, W / 2 - 0.1], [1.9, W / 2 - 0.1], [1.3, 0.7], [0, 0.45]]);
    top += rect(2.1, -W / 2 + 0.25, L - 2.4, W - 0.5, "k2") + rect(0.7, -W / 2, 0.3, 0.25, "k2") + rect(0.7, W / 2 - 0.25, 0.3, 0.25, "k2");
    front += D.trackFront(-W / 2, 0.3, 0.9) + D.trackFront(W / 2 - 0.3, 0.3, 0.9);
    front += poly([[-W / 2 + 0.15, 0.6], [-W / 2 + 0.05, hb], [W / 2 - 0.05, hb], [W / 2 - 0.15, 0.6]]);
    front += poly([[-0.55, 0.7], [-0.6, 1.3], [0.6, 1.3], [0.55, 0.7]], "k1") + D.grille(-0.4, 0.4, 0.8, 0.4, 8);
    front += rect(-0.95, 0, 0.22, 0.9, "k1") + rect(0.73, 0, 0.22, 0.9, "k1") + D.light(-0.85, 1.0) + D.light(0.6, 1.0);
    if (us) front += rect(-W / 2 + 0.05, hb, W - 0.1, 0.5, "k2") + rect(-0.15, hb + 0.4, 0.3, 0.14, "k2");
    else front += rect(-0.25, hb, 0.5, 0.42, "k2");
    return { side, top, front, xmin: -0.25, xmax: L, W, H };
  }
  function btr60() {
    const v = F.wheeled({ hullL: 7.56, W: 2.83, hullH: 2.05, r: 0.53, axles: [1.3, 2.75, 4.8, 6.25], boat: true, ports: 4 });
    return add(v, {
      side: poly([[1.9, 2.05], [2.0, 2.4], [2.9, 2.4], [3.0, 2.05]]) + rot(D.barrel(0, 0, { len: 1.8, d: 0.07 }), 2.0, 2.25, 180) + D.antenna(5.8, 2.05, 1.4),
      top: circ(2.45, 0, 0.55) + rot(D.barrel(0, 0, { len: 1.8, d: 0.07 }), 2.0, 0, 180) + D.hatchTop(4.3, -0.6, 0.3) + D.hatchTop(4.3, 0.6, 0.3),
      front: poly([[-0.55, 2.05], [-0.45, 2.4], [0.45, 2.4], [0.55, 2.05]]) + D.muzzle(0, 2.25, 0.07) + rect(-1.0, 1.55, 0.7, 0.3, "k2") + rect(0.3, 1.55, 0.7, 0.3, "k2"), H: 2.4, xmin: 0.15,
    });
  }

  // ================================================================= SPAAG
  function shilka() {
    const v = F.armour({ hullL: 6.5, W: 3.1, hullH: 1.35, glacis: 1.3, track: { n: 6, r: 0.33, sprocket: "rear", style: "steel" }, trackW: 0.42 });
    const t = boxTurret(1.7, 3.0, 1.35, 0.75, 2.95);
    let side = t.side, top = t.top, front = t.front;
    for (const yo of [0, 0.22]) side += rot(D.barrel(0, 0, { len: 2.1, d: 0.05, sleeve: [0.3] }), 1.9, 1.75 + yo, 180 - 18);
    for (const y of [-0.55, -0.35, 0.35, 0.55]) top += rot(D.barrel(0, 0, { len: 2.0, d: 0.05 }), 1.9, y, 180);
    front += muzzles([-0.55, -0.35, 0.35, 0.55], 2.25, 0.05) + muzzles([-0.55, -0.35, 0.35, 0.55], 2.05, 0.05);
    const r = radar({ x: 4.3, y: 2.1, w: 1.5, kind: "dish", mast: 0.5 });
    return add(v, { side: side + r.side, top: top + r.top, front: front + r.front, H: r.H, xmin: -0.3 });
  }
  function zsu57() {
    const v = F.armour({ hullL: 6.22, W: 3.27, hullH: 1.45, glacis: 1.3, track: { n: 4, r: 0.41, sprocket: "rear", style: "spoked" }, trackW: 0.58 });
    const t = boxTurret(2.0, 3.0, 1.45, 1.0, 2.8);
    let side = t.side + rot(D.barrel(0, 0, { len: 4.3, d: 0.09, brake: true, sleeve: [0.2] }), 2.3, 2.05, 180 - 12);
    const top = t.top + rot(D.barrel(0, 0, { len: 4.2, d: 0.09, brake: true }), 2.3, -0.35, 180) + rot(D.barrel(0, 0, { len: 4.2, d: 0.09, brake: true }), 2.3, 0.35, 180);
    const front = t.front + muzzles([-0.35, 0.35], 2.95, 0.09);
    side += rect(2.2, 2.45, 2.7, 0.04, "k3");                                                                  // open-top rim
    return add(v, { side, top, front, H: 3.0, xmin: 2.3 - 4.7 * COS(12) });
  }
  function tunguska() {
    const v = F.armour({ hullL: 7.93, W: 3.24, hullH: 1.75, glacis: 1.3, track: { n: 6, r: 0.35, returns: 3, sprocket: "rear", style: "steel" }, trackW: 0.5, exhaust: true });
    const t = boxTurret(2.4, 3.0, 1.75, 1.05, 2.6);
    let side = t.side, top = t.top, front = t.front;
    const m = rack({ L: 2.6, d: 0.24, tx: 4.8, ty: 2.45, elev: 8, kind: "canister", rows: 2, cols: [-1.55, 1.55], ribs: 3 });
    side += m.side + rot(D.barrel(0, 0, { len: 2.4, d: 0.07, sleeve: [0.4] }), 2.6, 2.2, 180 - 6);
    top += m.top + rot(D.barrel(0, 0, { len: 2.4, d: 0.07 }), 2.6, -1.4, 180) + rot(D.barrel(0, 0, { len: 2.4, d: 0.07 }), 2.6, 1.4, 180);
    front += m.front + muzzles([-1.4, 1.4], 2.45, 0.07);
    const s = radar({ x: 4.6, y: 2.8, w: 1.9, h: 0.55, kind: "array", mast: 0.25, tilt: 15 }), dsh = radar({ x: 2.6, y: 2.6, w: 1.0, kind: "dish", mast: 0.15 });
    return add(v, { side: side + s.side + dsh.side, top: top + s.top + dsh.top, front: front + dsh.front + s.front, H: Math.max(s.H, dsh.H), W: 3.4, xmin: m.xmin });
  }
  function gepard() {
    const v = F.armour({ hullL: 7.0, W: 3.37, hullH: 1.6, glacis: 1.1, track: { n: 7, r: 0.35, returns: 4, sprocket: "rear", style: "rubber", skirt: "rubber", skirtTop: 1.15 }, trackW: 0.55, exhaust: true });
    const t = boxTurret(2.2, 2.9, 1.6, 1.05, 2.4);
    const side = t.side + D.box(2.4, 1.85, 2.4, 0.55) + rot(D.barrel(0, 0, { len: 3.2, d: 0.1, sleeve: [0.2, 0.55] }), 2.5, 2.15, 180 - 5);
    const top = t.top + rect(2.3, -1.65, 2.4, 0.42, "k1") + rect(2.3, 1.23, 2.4, 0.42, "k1") + rot(D.barrel(0, 0, { len: 3.2, d: 0.1 }), 2.4, -1.45, 180) + rot(D.barrel(0, 0, { len: 3.2, d: 0.1 }), 2.4, 1.45, 180);
    const front = t.front + rect(-1.65, 1.85, 0.42, 0.55, "k1") + rect(1.23, 1.85, 0.42, 0.55, "k1") + muzzles([-1.45, 1.45], 2.15, 0.1);
    const s = radar({ x: 4.8, y: 2.65, w: 2.2, h: 0.55, mast: 0.3, tilt: 10 }), dsh = radar({ x: 2.4, y: 2.65, w: 1.0, kind: "dish", mast: 0.05 });
    return add(v, { side: side + s.side + dsh.side, top: top + s.top + dsh.top, front: front + s.front + dsh.front, H: s.H, xmin: 2.5 - 3.5 });
  }
  function vulcan() {
    return m113({
      side: poly([[1.6, 1.85], [1.5, 2.3], [2.6, 2.4], [2.7, 1.85]], "k1") + rot(D.barrel(0, 0, { len: 1.8, d: 0.26, sleeve: [0.15, 0.85] }), 1.6, 2.15, 180 - 10) + circ(2.2, 2.55, 0.18, "k2"),
      top: circ(2.15, 0, 0.75) + rot(D.barrel(0, 0, { len: 1.75, d: 0.26 }), 1.6, 0, 180),
      front: poly([[-0.75, 1.85], [-0.7, 2.4], [0.7, 2.4], [0.75, 1.85]], "k1") + circ(0, 2.45, 0.15) + range(0, 5, 6).map((i) => circ(COS(i * 60) * 0.08, 2.45 + SIN(i * 60) * 0.08, 0.025, "k3", false)).join(""), H: 2.75,
    });
  }
  function strela10() {
    const v = F.armour({ hullL: 6.6, W: 2.85, hullH: 1.55, glacis: 0.9, track: { n: 6, r: 0.3, sprocket: "front", style: "steel" }, trackW: 0.36, rearDoor: true,
      hullPts: [[0, 0.45], [-0.1, 0.9], [0.9, 1.55], [6.5, 1.55], [6.6, 1.35], [6.6, 0.45]] });
    const t = boxTurret(3.2, 1.4, 1.55, 0.7, 1.6);
    const m = rack({ L: 2.2, d: 0.2, tx: 4.6, ty: 2.55, elev: 15, kind: "canister", rows: 2, cols: [-1.0, -0.75, 0.75, 1.0], ribs: 2 });
    return add(v, { side: t.side + m.side + D.antenna(4.3, 2.25, 1.0), top: t.top + m.top, front: t.front + m.front + rect(-0.85, 2.25, 0.2, 0.6, "k2") + rect(0.65, 2.25, 0.2, 0.6, "k2"), H: 3.5, W: 2.85, xmin: m.xmin });
  }
  function chaparral() {
    const v = F.armour({ hullL: 6.1, W: 2.69, hullH: 1.2, glacis: 0.5, track: { n: 5, r: 0.31, sprocket: "front", style: "steel" }, trackW: 0.38,
      hullPts: [[0, 0.5], [-0.05, 1.2], [6.0, 1.2], [6.1, 1.0], [6.1, 0.5]] });
    const cab = poly([[0.15, 1.2], [0.1, 2.2], [1.9, 2.25], [1.95, 1.2]]) + poly([[0.18, 2.15], [0.2, 1.7], [1.0, 1.7], [1.0, 2.15]], "k2");
    const t = boxTurret(3.4, 1.7, 1.2, 0.9, 1.5);
    const m = rack({ L: 2.9, d: 0.13, tx: 5.3, ty: 2.25, elev: 10, rows: 2, cols: [-0.95, -0.7, 0.7, 0.95], fin: 1.3, gap: 2.4 });
    return add(v, { side: cab + t.side + m.side + rect(4.9, 2.1, 0.6, 0.25, "k2"), top: rect(0.15, -1.2, 1.8, 2.4, "k1") + t.top + m.top,
      front: rect(-1.25, 1.2, 2.5, 1.05, "k1") + rect(-1.1, 1.7, 0.95, 0.45, "k2") + rect(0.15, 1.7, 0.95, 0.45, "k2") + t.front + m.front, H: 2.9, xmin: m.xmin });
  }
  function roland() {
    const v = F.armour({ hullL: 6.9, W: 3.24, hullH: 1.9, glacis: 1.4, track: { n: 6, r: 0.35, returns: 3, sprocket: "front", style: "rubber" }, trackW: 0.5,
      hullPts: [[0, 0.55], [-0.05, 1.1], [1.4, 1.9], [6.8, 1.9], [6.9, 1.6], [6.9, 0.55]] });
    const t = boxTurret(3.2, 2.2, 1.9, 0.8, 1.9);
    const m = rack({ L: 2.6, d: 0.3, tx: 5.3, ty: 2.25, elev: 8, kind: "canister", rows: 1, cols: [-1.3, 1.3], ribs: 3 });
    const r = radar({ x: 4.6, y: 2.7, w: 1.4, h: 0.45, mast: 0.15, tilt: 10 });
    return add(v, { side: t.side + m.side + r.side + D.dish(3.5, 2.85, 0.6, 90), top: t.top + m.top + r.top, front: t.front + m.front + r.front, H: r.H, xmin: m.xmin });
  }
  function tor() {
    const v = F.armour({ hullL: 7.5, W: 3.3, hullH: 1.6, glacis: 1.2, track: { n: 6, r: 0.35, returns: 3, sprocket: "rear", style: "steel" }, trackW: 0.5 });
    let side = poly([[2.2, 1.6], [2.0, 2.4], [2.3, 3.75], [5.3, 3.75], [5.4, 1.6]]) + D.arrayPanel(2.0, 2.45, 1.3, 0.35, 5, 3, 76) + D.dish(2.2, 3.1, 0.5, 90);
    side += D.eraRows(3.0, 4.9, 2.0, 3.6, 4, 2) + seg(2.2, 1.7, 5.4, 1.7, "k3");
    const r = radar({ x: 4.3, y: 3.75, w: 2.4, h: 0.55, mast: 0.35, tilt: 25 });
    const top = rect(2.2, -1.3, 3.2, 2.6, "k1") + D.eraRows(2.9, 4.9, -1.2, 1.2, 4, 4) + r.top;
    const front = rect(-1.3, 1.6, 2.6, 2.15, "k1") + D.arrayPanel(-0.65, 2.3, 1.3, 1.0, 6, 5) + D.dish(-0.9, 3.2, 0.45, 0) + r.front;
    return add(v, { side: side + r.side, top, front, H: r.H });
  }
  function osa() {
    const v = F.wheeled({ hullL: 9.14, W: 2.75, hullH: 1.9, r: 0.6, axles: [1.6, 4.5, 7.4], boat: true, ports: 0 });
    const t = boxTurret(3.4, 2.4, 1.9, 0.75, 2.0);
    const m = rack({ L: 3.2, d: 0.21, tx: 6.0, ty: 2.75, elev: 12, rows: 3, cols: [-1.25, -0.95, -0.65, 0.65, 0.95, 1.25], fin: 1.1, gap: 1.6 });
    const s = radar({ x: 5.0, y: 2.65, w: 1.6, h: 0.6, mast: 0.6, tilt: 15 }), d = radar({ x: 3.6, y: 2.65, w: 0.8, kind: "dish", mast: 0.2 });
    return add(v, { side: t.side + d.side + m.side + s.side, top: t.top + m.top + s.top, front: t.front + m.front + d.front + s.front, H: Math.max(s.H, m.H), xmin: m.xmin });
  }
  function strela1() {
    const v = F.wheeled({ hullL: 5.75, W: 2.35, hullH: 1.9, r: 0.55, axles: [1.3, 4.05], boat: true, ports: 0 });
    const t = boxTurret(2.6, 1.2, 1.9, 0.4, 1.4);
    const m = rack({ L: 1.8, d: 0.22, tx: 4.2, ty: 2.4, elev: 18, kind: "canister", rows: 2, cols: [-0.95, -0.7, 0.7, 0.95], ribs: 2 });
    return add(v, { side: t.side + m.side, top: t.top + m.top, front: t.front + m.front + rect(-0.9, 1.4, 0.6, 0.28, "k2") + rect(0.3, 1.4, 0.6, 0.28, "k2"), H: m.H, xmin: m.xmin });
  }
  function hmmwv() {
    const L = 4.95, W = 2.18, r = 0.47;
    let side = poly([[0, 0.65], [0, 1.15], [1.5, 1.3], [1.65, 1.85], [3.6, 1.9], [L, 1.75], [L, 0.65]]) + D.grille(0.02, 0.4, 0.75, 0.35, 6);
    side += path(`M 0.3 0.6 A 0.6 0.6 0 0 0 1.5 0.6`, "k2", false) + path(`M 3.25 0.6 A 0.6 0.6 0 0 0 4.45 0.6`, "k2", false);
    side += poly([[1.7, 1.82], [1.75, 1.4], [2.4, 1.4], [2.4, 1.82]], "k2") + rect(2.5, 1.0, 0.85, 0.75, "k3") + D.wheelsSide([0.9, 3.85], r);
    const top = rect(0, -W / 2, L, W, "k1") + seg(1.55, -W / 2, 1.55, W / 2, "k2") + rect(0.5, -W / 2, 0.8, 0.25, "k3") + rect(0.5, W / 2 - 0.25, 0.8, 0.25, "k3") + D.grille(0.05, 1.3, -0.6, 1.2, 12);
    const front = poly([[-W / 2, 0.55], [-W / 2, 1.15], [-0.85, 1.85], [0.85, 1.85], [W / 2, 1.15], [W / 2, 0.55]]) + D.grille(-0.45, 0.45, 0.75, 0.35, 9)
      + rect(-W / 2, 0, 0.32, 0.94, "k1") + rect(W / 2 - 0.32, 0, 0.32, 0.94, "k1") + D.light(-0.95, 0.85) + D.light(0.7, 0.85) + rect(-0.8, 1.35, 0.75, 0.45, "k2") + rect(0.05, 1.35, 0.75, 0.45, "k2");
    return { side, top, front, xmin: -0.05, xmax: L, W, H: 1.9 };
  }
  function avenger() {
    const v = hmmwv();
    const t = { side: rect(2.7, 1.9, 1.2, 0.55, "k1") + circ(3.3, 2.35, 0.3, "k2"), top: circ(3.3, 0, 0.55) , front: rect(-0.55, 1.9, 1.1, 0.75, "k1") + rect(-0.25, 2.1, 0.5, 0.4, "k2") };
    const m = rack({ L: 1.6, d: 0.28, tx: 4.1, ty: 2.15, elev: 8, kind: "canister", rows: 2, cols: [-0.85, 0.85], ribs: 2 });
    return add(v, { side: t.side + m.side, top: t.top + m.top, front: t.front + m.front + range(0, 1, 2).map((j) => circ(-0.92 + j * 0.15, 2.3, 0.05, "k3", false) + circ(0.78 + j * 0.15, 2.3, 0.05, "k3", false)).join(""), H: 2.65 });
  }

  // ======================================================== SAM launchers
  function sa6() {
    const v = F.armour({ hullL: 7.39, W: 3.18, hullH: 1.45, glacis: 1.4, track: { n: 6, r: 0.33, returns: 0, sprocket: "rear", style: "steel" }, trackW: 0.45 });
    const base = poly([[2.8, 1.45], [2.9, 1.75], [5.2, 1.75], [5.3, 1.45]]);
    const m = rack({ L: 5.8, d: 0.33, tx: 5.6, ty: 2.1, elev: 12, cols: [-0.95, 0, 0.95], fin: 1.4, canards: true });
    return add(v, { side: base + rect(4.9, 1.75, 0.3, 0.45, "k2") + m.side, top: rect(2.8, -1.4, 2.5, 2.8, "k1") + m.top, front: rect(-1.4, 1.45, 2.8, 0.3, "k1") + rect(-1.1, 1.75, 2.2, 0.35, "k2") + m.front, H: m.H, xmin: m.xmin });
  }
  function sa11() {
    const v = F.armour({ hullL: 9.3, W: 3.25, hullH: 1.7, glacis: 1.4, track: { n: 6, r: 0.37, returns: 3, sprocket: "front", style: "steel" }, trackW: 0.5, exhaust: true });
    const base = poly([[3.1, 1.7], [3.2, 2.05], [7.5, 2.05], [7.6, 1.7]]);
    const m = rack({ L: 5.55, d: 0.4, tx: 7.6, ty: 2.45, elev: 10, cols: [-1.0, -0.4, 0.4, 1.0], fin: 1.0, canards: false });
    const r = { side: poly([[2.4, 2.05], [2.3, 3.2], [3.0, 3.6], [3.4, 3.6], [3.4, 2.05]]) + D.dish(2.35, 2.85, 1.3, 98), top: rect(2.3, -0.75, 1.1, 1.5, "k1"), front: path(`M -0.7 2.05 L -0.75 3.0 Q 0 3.8 0.75 3.0 L 0.7 2.05 Z`) + circ(0, 2.95, 0.55, "k3", false) };
    return add(v, { side: base + m.side + r.side, top: rect(3.1, -1.4, 4.5, 2.8, "k1") + m.top + r.top, front: rect(-1.4, 1.7, 2.8, 0.35, "k1") + m.front + r.front, H: Math.max(m.H, 3.8), xmin: m.xmin });
  }
  function maz543(canisters, n) {
    // 8x8 MAZ-543 with split cabs, launcher body behind.
    const L = 13.0, W = 3.05, r = 0.78;
    const axles = [1.6, 3.9, 7.4, 9.6];
    let side = rect(0.2, 1.1, L - 0.4, 0.4, "k2");
    side += path(`M 0.4 1.1 A 1.2 1.2 0 0 0 2.8 1.1`, "k2", false) + path(`M 2.7 1.1 A 1.2 1.2 0 0 0 5.1 1.1`, "k2", false) + path(`M 6.2 1.1 A 1.2 1.2 0 0 0 8.6 1.1`, "k2", false) + path(`M 8.4 1.1 A 1.2 1.2 0 0 0 10.8 1.1`, "k2", false);
    side += D.wheelsSide(axles, r);
    side += poly([[0, 1.2], [0, 2.6], [0.4, 2.95], [2.0, 2.95], [2.1, 1.2]]) + poly([[0.12, 2.8], [0.1, 2.15], [1.0, 2.15], [1.0, 2.8]], "k2") + rect(1.15, 2.15, 0.75, 0.6, "k3");
    side += poly([[2.2, 1.5], [2.2, 2.7], [3.5, 2.7], [3.5, 1.5]], "k1") + D.grille(2.3, 3.4, 1.7, 0.6, 10);
    let top = rect(0.1, -W / 2, 2.0, 1.25, "k1") + rect(0.1, W / 2 - 1.25, 2.0, 1.25, "k1") + rect(2.2, -0.6, 1.3, 1.2, "k2") + rect(3.6, -W / 2, L - 3.7, W, "k1");
    for (const x of axles) top += rect(x - r, -W / 2 - 0.05, 2 * r, 0.45, "k2") + rect(x - r, W / 2 - 0.4, 2 * r, 0.45, "k2");
    let front = rect(-W / 2, 1.2, 1.25, 1.75, "k1") + rect(W / 2 - 1.25, 1.2, 1.25, 1.75, "k1") + rect(-W / 2 + 0.1, 2.15, 1.05, 0.6, "k2") + rect(W / 2 - 1.15, 2.15, 1.05, 0.6, "k2")
      + rect(-0.25, 1.4, 0.5, 1.3, "k2") + rect(-W / 2, 0, 0.45, 2 * r, "k1") + rect(W / 2 - 0.45, 0, 0.45, 2 * r, "k1") + D.light(-1.4, 1.35) + D.light(1.15, 1.35);
    // canisters in travel position (pivot at the rear)
    const m = rack({ L: canisters, d: 0.75, tx: L - 0.1, ty: 2.15, elev: 0, kind: "canister", rows: 2, cols: n === 4 ? [-0.4, 0.4] : [0], ribs: 6, gap: 1.05 });
    side += rect(3.6, 1.5, L - 3.7, 0.6, "k1") + m.side + rect(L - 0.5, 0.3, 0.25, 1.2, "k2");
    top += m.top;
    front += m.front;
    return { side, top, front, xmin: -0.05, xmax: L, W, H: 3.8 };
  }
  function patriot() {
    // M901 launching station on the M860 semi-trailer (tractor omitted).
    const L = 10.4, W = 2.5, r = 0.5;
    let side = poly([[0, 1.35], [0, 1.65], [L, 1.65], [L, 1.15], [8.0, 1.15], [7.6, 0.95], [1.4, 0.95], [1.4, 1.35]]);
    side += rect(0.3, 1.65, 0.2, 0.35, "k3") + D.wheelsSide([8.0, 9.2], r) + rect(1.0, 0, 0.15, 1.0, "k2") + rect(0.8, 0, 0.55, 0.08, "k2");
    side += D.box(2.0, 1.65, 1.6, 1.0);
    const m = rack({ L: 5.8, d: 0.9, tx: 9.6, ty: 1.85, elev: 38, kind: "canister", rows: 2, cols: [-0.48, 0.48], ribs: 5, gap: 1.02 });
    side += poly([[9.2, 1.65], [9.6, 1.85], [6.6, 1.65]], "k2") + m.side;
    const top = rect(0, -W / 2, L, W, "k1") + rect(2.0, -0.8, 1.6, 1.6, "k2") + rect(7.5, -W / 2 - 0.05, 2.2, 0.4, "k2") + rect(7.5, W / 2 - 0.35, 2.2, 0.4, "k2") + m.top;
    const front = rect(-W / 2, 0.95, W, 0.7, "k1") + rect(-W / 2, 0, 0.4, 1.0, "k1") + rect(W / 2 - 0.4, 0, 0.4, 1.0, "k1") + m.front;
    return { side, top, front, xmin: Math.min(0, m.xmin), xmax: L, W, H: m.H };
  }
  function nasams() {
    const v = F.truck({ L: 7.0, W: 2.5, r: 0.55, axles: [1.3, 4.6, 5.9], cabL: 2.0, cabH: 2.75 });
    const m = rack({ L: 4.0, d: 0.5, tx: 6.9, ty: 1.55, elev: 30, kind: "canister", rows: 2, cols: [-0.8, 0, 0.8], ribs: 4, gap: 1.02 });
    return add(v, { side: rect(2.4, 1.25, 4.5, 0.3, "k1") + m.side, top: rect(2.3, -1.2, 4.6, 2.4, "k1") + m.top, front: m.front, H: m.H, xmin: Math.min(-0.05, m.xmin) });
  }
  function staticRail(o) {
    // Static rail launcher on a turntable (SA-2 SM-90, SA-3 5P73, Hawk M192).
    const { L, d, n, elev, booster } = o, h = o.h || 1.4, W = o.W || 3.2, c = COS(elev), sn = SIN(elev);
    let side = poly([[-1.3, 0], [-1.1, 0.3], [1.1, 0.3], [1.3, 0]]) + rect(-0.9, 0.3, 1.8, 0.35, "k1") + poly([[-0.7, 0.65], [-0.5, h - 0.2], [0.5, h - 0.2], [0.7, 0.65]]) + D.grille(-0.8, 0.8, 0.35, 0.25, 8);
    let top = rect(-W / 2, -0.22, W, 0.44, "k2") + rect(-0.22, -W / 2, 0.44, W, "k2") + circ(0, 0, 1.1, "k1") + circ(0, 0, 0.9, "k3", false);
    for (const [x, y] of [[-W / 2 + 0.15, 0], [W / 2 - 0.15, 0], [0, -W / 2 + 0.15], [0, W / 2 - 0.15]]) top += circ(x, y, 0.18, "k2");
    let front = poly([[-W / 2, 0], [-W / 2, 0.15], [W / 2, 0.15], [W / 2, 0]]) + rect(-0.9, 0.15, 1.8, 0.5, "k1") + poly([[-0.7, 0.65], [-0.5, h - 0.2], [0.5, h - 0.2], [0.7, 0.65]]);
    const cols = n === 4 ? [-0.55, 0.55] : n === 3 ? [-0.75, 0, 0.75] : n === 2 ? [-0.55, 0.55] : [0];
    const rows = n === 4 ? 2 : 1;
    // trunnion at (0, h); missile tail sits a quarter-length behind it, along the rail
    const back = L * 0.25, tx = back * c, ty = h - back * sn + d;
    const m = rack({ L, d, tx, ty, elev, cols, rows, fin: booster ? 1.6 : 1.1, canards: !!o.canards, gap: 2.2 });
    // cradle + rail beam(s) under the missiles, and elevating ram
    const rail = (j) => rot(rect(-0.2, d * 0.55 + j * d * 2.2, L * 0.82, 0.16, "k1") + seg(0, d * 0.55 + j * d * 2.2 + 0.08, L * 0.8, d * 0.55 + j * d * 2.2 + 0.08, "k3"), tx, ty, 180 - elev);
    side += poly([[-0.6, h - 0.2], [-0.2, h + 0.25], [0.3, h + 0.25], [0.7, h - 0.2]]) + circ(0, h, 0.1, "k2");
    side += line([[-0.4, h - 0.2], [-L * 0.3 * c, h + L * 0.3 * sn - 0.1]], "k1");
    for (let j = 0; j < rows; j++) side += rail(j);
    side += m.side;
    if (booster) side += rot(rect(0, -d * 0.7, L * 0.28, d * 1.4, "k1") + poly([[L * 0.12, d * 0.7], [L * 0.24, d * 2.6], [L * 0.28, d * 2.6], [L * 0.28, d * 0.7]], "k2") + poly([[L * 0.12, -d * 0.7], [L * 0.24, -d * 2.6], [L * 0.28, -d * 2.6], [L * 0.28, -d * 0.7]], "k2") + seg(L * 0.04, -d * 0.7, L * 0.04, d * 0.7, "k3"), tx - L * 0.28 * c, ty + L * 0.28 * sn, -elev);
    top += m.top + cols.map((y) => rect(tx - L * 0.82 * c, y - 0.08, L * 0.82 * c, 0.16, "k3")).join("");
    front += rect(-(Math.max(...cols.map(Math.abs)) + 0.3), h - 0.2, 2 * (Math.max(...cols.map(Math.abs)) + 0.3), 0.45, "k1") + m.front;
    return { side, top, front, xmin: Math.min(-1.4, m.xmin), xmax: Math.max(1.4, tx + 0.5), W: Math.max(W, 2 * Math.max(...cols.map(Math.abs)) + 1), H: m.H };
  }

  // ============================================================ towed guns
  const TOWED = {
    flak38: () => F.towedGun({ L: 4.1, W: 2.4, r: 0.35, mountH: 1.0, cruciform: true, gunLen: 2.0, d: 0.06, elev: 25, barrels: 4, shield: true, seat: true }),
    flak36: () => F.towedGun({ L: 7.6, W: 2.3, r: 0.45, mountH: 1.6, cruciform: true, gunLen: 4.9, d: 0.14, elev: 30, shield: true, seat: true }),
    flak41: () => F.towedGun({ L: 9.6, W: 2.4, r: 0.45, mountH: 1.7, cruciform: true, gunLen: 6.5, d: 0.15, elev: 30, shield: true, seat: true }),
    "M45_Quadmount": () => F.towedGun({ L: 3.0, W: 2.1, r: 0.4, mountH: 1.2, cruciform: true, wheels: true, gunLen: 1.65, d: 0.05, elev: 20, barrels: 4, shieldW: 1.6, shield: true, seat: true }),
    bofors40: () => F.towedGun({ L: 6.4, W: 2.0, r: 0.42, mountH: 1.35, cruciform: true, gunLen: 3.0, d: 0.09, elev: 25, seat: true, brake: true }),
    QF_37_AA: () => F.towedGun({ L: 8.6, W: 2.4, r: 0.5, mountH: 1.7, cruciform: true, gunLen: 5.0, d: 0.15, elev: 30, seat: true }),
    "ZU-23 Emplacement": () => F.towedGun({ L: 4.6, W: 1.8, r: 0.35, mountH: 0.95, cruciform: true, gunLen: 2.6, d: 0.05, elev: 20, barrels: 2, seat: true }),
    "S-60_Type59_Artillery": () => F.towedGun({ L: 8.5, W: 2.1, r: 0.5, mountH: 1.5, cruciform: true, gunLen: 4.4, d: 0.09, elev: 25, shield: true, seat: true, brake: true }),
    "KS-19": () => F.towedGun({ L: 9.5, W: 2.3, r: 0.55, mountH: 1.75, cruciform: true, gunLen: 5.6, d: 0.16, elev: 30, shield: true, seat: true, brake: true }),
    "LeFH_18-40-105": () => F.towedGun({ L: 6.0, W: 1.98, r: 0.62, mountH: 1.15, gunLen: 3.1, d: 0.14, elev: 12, shield: true, brake: true }),
    "M2A1-105": () => F.towedGun({ L: 5.9, W: 2.2, r: 0.55, mountH: 1.15, gunLen: 2.6, d: 0.15, elev: 12, shield: true }),
  };
  function mortar() {
    // 2B11 120 mm mortar on its wheeled transport mount.
    let side = poly([[0.9, 0], [0.7, 0.12], [1.4, 0.12], [1.5, 0]]) + D.wheel(1.45, 0.35, 0.35, "tyre");
    side += rot(D.barrel(0, 0, { len: 1.85, d: 0.16, sleeve: [0.1] }), 1.1, 0.15, 180 - 60);
    side += line([[0.55, 0], [0.35, 1.1]], "k2") + line([[0.6, 0], [0.4, 1.1]], "k2") + rect(0.25, 1.05, 0.25, 0.12, "k2");
    const top = circ(1.1, 0, 0.35) + rot(D.barrel(0, 0, { len: 0.93, d: 0.16 }), 1.1, 0, 180) + seg(0.35, -0.5, 0.45, 0.5, "k2") + rect(1.3, -0.6, 0.3, 0.2, "k2") + rect(1.3, 0.4, 0.3, 0.2, "k2");
    const front = rect(-0.35, 0, 0.7, 0.12, "k1") + rect(-0.08, 0.15, 0.16, 1.6, "k1") + D.muzzle(0, 1.75, 0.16) + line([[-0.5, 0], [-0.05, 1.1]], "k2") + line([[0.5, 0], [0.05, 1.1]], "k2");
    return { side, top, front, xmin: 0.0, xmax: 1.9, W: 1.2, H: 1.85 };
  }

  // ============================================================== artillery
  function m109() {
    return F.armour({ hullL: 6.11, W: 3.15, hullH: 1.4, glacis: 1.2, track: { n: 7, r: 0.3, sprocket: "front", style: "steel" }, trackW: 0.38,
      turret: { x: 3.8, len: 3.9, w: 3.1, h: 1.45, shape: "box", cupolaX: 4.2, cupolaR: 0.35, gunY: 0.35, gunX: 0.05 }, gun: { len: 6.0, d: 0.2, evac: 0.6, brake: true, sleeve: [0.2] } });
  }
  function gvozdika() {
    return F.armour({ hullL: 7.26, W: 2.85, hullH: 1.5, glacis: 1.4, track: { n: 7, r: 0.3, sprocket: "front", style: "steel" }, trackW: 0.4, rearDoor: true,
      turret: { x: 3.9, len: 2.6, w: 2.4, h: 0.8, shape: "cast", cupolaX: 4.3 }, gun: { len: 3.45, d: 0.17, evac: 0.55, brake: true } });
  }
  function msta() {
    return F.armour({ hullL: 7.15, W: 3.58, hullH: 1.55, glacis: 1.4, track: { n: 6, r: 0.37, returns: 5, sprocket: "rear", style: "steel", skirt: "rubber", skirtTop: 1.05 }, trackW: 0.58, exhaust: true,
      turret: { x: 3.5, len: 4.2, w: 3.4, h: 1.3, shape: "box", cupolaX: 4.6, cupolaR: 0.38, smoke: true, gunY: 0.35 }, gun: { len: 7.1, d: 0.2, evac: 0.65, brake: true, sleeve: [0.15] } });
  }
  function mlrs() {
    const v = F.armour({ hullL: 6.85, W: 2.97, hullH: 1.25, glacis: 0.5, track: { n: 6, r: 0.3, returns: 3, sprocket: "front", style: "rubber" }, trackW: 0.53,
      hullPts: [[0, 0.5], [-0.05, 1.25], [6.75, 1.25], [6.85, 1.05], [6.85, 0.5]] });
    const cab = poly([[0.05, 1.25], [0.0, 2.3], [0.3, 2.6], [2.3, 2.6], [2.3, 1.25]]) + D.grille(0.6, 1.8, 2.0, 0.35, 8) + rect(0.25, 1.5, 1.6, 0.25, "k3");
    const pods = poly([[2.7, 1.45], [2.7, 2.55], [6.85, 2.55], [6.85, 1.45]]) + seg(2.7, 2.0, 6.85, 2.0, "k2") + D.eraRows(2.75, 6.8, 1.5, 2.5, 6, 2);
    return add(v, { side: cab + pods, top: rect(0.0, -1.45, 2.3, 2.9, "k1") + rect(2.7, -1.05, 4.15, 2.1, "k1") + seg(2.7, 0, 6.85, 0, "k2"),
      front: rect(-1.45, 1.25, 2.9, 1.35, "k1") + rect(-1.3, 1.85, 1.2, 0.55, "k2") + rect(0.1, 1.85, 1.2, 0.55, "k2"), H: 2.6 });
  }
  function grad() {
    const v = F.truck({ L: 7.35, W: 2.4, r: 0.55, axles: [1.0, 4.75, 6.15], bonnet: true, cabL: 1.6, cabH: 2.4 });
    const tubes = rack({ L: 3.0, d: 0.122, tx: 6.9, ty: 1.85, elev: 0, kind: "canister", rows: 4, cols: range(-0.6, 0.6, 10), ribs: 1, gap: 1.0 });
    return add(v, { side: rect(3.8, 1.25, 3.5, 0.45, "k1") + tubes.side + rect(3.8, 1.7, 3.2, 0.15, "k2"), top: tubes.top, front: rect(-0.75, 1.85, 1.5, 0.55, "k1") + range(-0.6, 0.6, 10).map((x) => range(1.9, 2.3, 4).map((y) => circ(x, y, 0.05, "k3", false)).join("")).join(""), H: 2.5 });
  }

  // ===================================================================== EWR
  function truckRadar(o) {
    const v = F.truck({ L: o.L || 7.0, W: 2.5, r: 0.55, axles: o.axles || [1.3, 4.6, 5.9], cabL: 2.0, cabH: 2.7, bonnet: o.bonnet });
    const box = { side: D.box(2.8, 1.35, (o.L || 7) - 2.9, 1.6), top: rect(2.8, -1.2, (o.L || 7) - 2.9, 2.4, "k1"), front: rect(-1.2, 1.35, 2.4, 1.6, "k1") };
    const r = radar({ x: o.ax || 4.8, y: 2.95, w: o.aw, h: o.ah, mast: o.mast, tilt: 0 });
    return add(v, { side: box.side + r.side, top: box.top + r.top, front: box.front + r.front, H: r.H, W: o.aw });
  }
  function yagiArray(w, h, y0, mast) {
    // VHF array of yagi elements on a mast, seen from the front.
    let s = rect(-0.15, 0, 0.3, y0, "k2");
    s += rect(-w / 2, y0, w, h, "k2", false);
    for (const x of range(-w / 2 + 0.3, w / 2 - 0.3, Math.round(w / 1.2))) for (const y of range(y0 + 0.3, y0 + h - 0.3, Math.max(2, Math.round(h / 1.2)))) s += seg(x - 0.45, y, x + 0.45, y, "k3") + circ(x, y, 0.04, "k3", false);
    if (mast) s += seg(-w / 2, y0, 0, 0, "k3") + seg(w / 2, y0, 0, 0, "k3");
    return s;
  }
  function boxSpring(w, h, y0, baseL) {
    // 1L13 / 55G6: large VHF array on a turning mast, on a trailer.
    let side = rect(0, 0.6, baseL, 0.6, "k1") + D.wheelsSide([1.0, baseL - 1.0], 0.5) + rect(baseL / 2 - 0.15, 1.2, 0.3, y0 - 1.2, "k1");
    side += rect(baseL / 2 - 0.6, y0, 1.2, h, "k1") + range(y0 + 0.3, y0 + h - 0.3, Math.round(h / 1.2)).map((y) => seg(baseL / 2 - 1.6, y, baseL / 2 + 1.6, y, "k3")).join("");
    side += seg(baseL / 2 - 0.15, 1.2, baseL / 2 - 0.6, y0, "k3") + seg(baseL / 2 + 0.15, 1.2, baseL / 2 + 0.6, y0, "k3");
    const top = rect(0, -1.25, baseL, 2.5, "k1") + rect(baseL / 2 - 0.6, -w / 2, 1.2, w, "k1") + range(-w / 2 + 0.3, w / 2 - 0.3, Math.round(w / 1.2)).map((y) => seg(baseL / 2 - 1.6, y, baseL / 2 + 1.6, y, "k3")).join("");
    const front = rect(-1.25, 0.6, 2.5, 0.6, "k1") + rect(-1.25, 0, 0.4, 1.0, "k1") + rect(0.85, 0, 0.4, 1.0, "k1") + rect(-0.15, 1.2, 0.3, y0 - 1.2, "k1") + yagiArray(w, h, y0, false).replace(/^<rect[^>]*>/, "");
    return { side, top, front, xmin: baseL / 2 - 1.7, xmax: baseL, W: w, H: y0 + h };
  }
  function freya() {
    // FuMG 401 Freya: turning cabin with the antenna array on top.
    const w = 6.2, h = 4.2, y0 = 2.6;
    let side = rect(0, 0, 4.0, 0.3, "k1") + rect(0.5, 0.3, 3.0, 2.0, "k1") + rect(1.0, 0.9, 0.7, 1.0, "k2") + rect(1.2, 2.3, 1.6, 0.3, "k2");
    side += rect(1.8, y0, 0.5, h, "k1") + range(y0 + 0.3, y0 + h - 0.3, 4).map((y) => seg(1.3, y, 2.8, y, "k3")).join("");
    const top = rect(0, -2.0, 4.0, 4.0, "k1") + rect(0.5, -1.5, 3.0, 3.0, "k1") + rect(1.8, -w / 2, 0.5, w, "k1");
    const front = rect(-2.0, 0, 4.0, 0.3, "k1") + rect(-1.5, 0.3, 3.0, 2.0, "k1") + rect(-0.8, 2.3, 1.6, 0.3, "k2") + yagiArray(w, h, y0, false).replace(/^<rect[^>]*>/, "");
    return { side, top, front, xmin: 0, xmax: 4.0, W: w, H: y0 + h };
  }
  function fps117() {
    // AN/FPS-117 radome on a raised equipment building.
    const R = 6.5, bh = 9.0, L = 14;
    const dome = (cx) => path(`M ${cx - R} ${bh + 1.2} A ${R} ${R * 1.05} 0 1 0 ${cx + R} ${bh + 1.2} Z`) + range(-R + 1.5, R - 1.5, 6).map((x) => `<path class="k3" d="M ${cx + x} ${bh + 1.2} Q ${cx + x * 1.15} ${bh + 1.2 + R * 0.9} ${cx} ${bh + 1.2 + R * 1.25}" fill="none"/>`).join("");
    const side = rect(0, 0, L, bh, "k1") + range(1, L - 1, 6).map((x) => rect(x - 0.4, bh * 0.55, 0.8, 1.2, "k3")).join("") + rect(2.0, 0, 1.2, 2.4, "k2") + rect(L / 2 - 3, bh, 6, 1.2, "k1") + dome(L / 2);
    const top = rect(0, -L / 2, L, L, "k1") + circ(L / 2, 0, R) + circ(L / 2, 0, R * 0.6, "k3", false);
    const front = rect(-L / 2, 0, L, bh, "k1") + rect(-3, bh, 6, 1.2, "k1") + dome(0);
    return { side, top, front, xmin: 0, xmax: L, W: L, H: bh + 1.2 + R * 1.25 };
  }

  // ======================================================== infantry MANPADS
  function soldier() {
    const side = path("M 0.15 0 L 0.25 0.85 L 0.2 1.35 Q 0.18 1.5 0.25 1.55 L 0.35 1.55 L 0.45 1.35 L 0.45 0.85 L 0.5 0 L 0.38 0 L 0.33 0.8 L 0.28 0 Z")
      + circ(0.33, 1.68, 0.12) + path("M 0.2 1.7 Q 0.33 1.86 0.46 1.72 L 0.46 1.66 L 0.2 1.66 Z", "k2") + rect(0.38, 0.95, 0.22, 0.35, "k2")
      + rot(rect(0, -0.05, 1.55, 0.1, "k1") + rect(0.25, -0.12, 0.25, 0.07, "k3") + circ(1.0, -0.12, 0.05, "k3"), -0.4, 1.62, -8);
    const top = `<ellipse class="k1 occ" cx="0.33" cy="0" rx="0.17" ry="0.25"/>` + circ(0.33, 0, 0.12, "k2") + rect(-0.4, 0.12, 1.55, 0.1, "k1") + rect(0.38, -0.2, 0.22, 0.4, "k2");
    const front = path("M -0.22 0 L -0.18 0.85 L -0.25 1.45 L -0.12 1.55 L 0.12 1.55 L 0.25 1.45 L 0.18 0.85 L 0.22 0 L 0.08 0 L 0.02 0.8 L -0.02 0.8 L -0.08 0 Z")
      + circ(0, 1.68, 0.12) + circ(0.17, 1.58, 0.07) + circ(0.17, 1.58, 0.04, "k3", false);
    return { side, top, front, xmin: -0.45, xmax: 1.2, W: 0.6, H: 1.85 };
  }

  // ================================================================== ships
  // Ships from bow (x = 0) aft. blocks: superstructure; masts; funnels; guns; launchers.
  const SHIP = {
    Schnellboot_type_S130: () => F.ship({ L: 35, B: 5.1, freeboard: 1.8, draft: 1.6, blocks: [{ x: 11, len: 5, h: 2.4, w: 3.2 }], masts: [{ x: 14, base: 2.4, h: 4.5 }],
      guns: [{ x: 7, size: 0.7 }, { x: 25, size: 0.8, aft: true }], launchers: [{ x: 2.5, len: 7, d: 0.55, kind: "tubes", n: 1, ang: 3, w: 1.6 }] }),
    Uboat_VIIC: () => F.ship({ L: 67, B: 6.2, freeboard: 1.2, draft: 4.8, blocks: [{ x: 26, len: 9, h: 3.6, w: 2.4 }], masts: [{ x: 31, base: 3.6, h: 2.5 }],
      guns: [{ x: 22, size: 0.9 }, { x: 34, size: 0.5, base: 3.6, aft: true }] }),
    LST_Mk2: () => F.ship({ L: 100, B: 15, freeboard: 6.5, draft: 3.0, boats: [78], hatches: [{ x: 30, len: 12 }], blocks: [{ x: 74, len: 18, h: 8, w: 12 }], masts: [{ x: 80, base: 8, h: 9 }], funnels: [{ x: 86, w: 3, h: 4, base: 8 }],
      guns: [{ x: 6, size: 1.2 }, { x: 95, size: 1.2, aft: true }] }),
    USS_Samuel_Chase: () => F.ship({ L: 150, B: 21, freeboard: 9, draft: 7.5, boats: [63, 71], derricks: true,
      hatches: [{ x: 18, len: 10 }, { x: 36, len: 12 }, { x: 100, len: 12 }, { x: 118, len: 10 }], blocks: [{ x: 55, len: 40, h: 9, w: 16 }, { x: 62, len: 18, h: 15, w: 10 }], masts: [{ x: 30, base: 0, h: 26 }, { x: 105, base: 0, h: 24 }],
      funnels: [{ x: 76, w: 7, h: 9, base: 15 }], guns: [{ x: 10, size: 2 }, { x: 140, size: 2, aft: true }] }),
    "Dry-cargo ship-1": () => F.ship({ L: 130, B: 20, freeboard: 8, draft: 7, boats: [104], derricks: true,
      hatches: [{ x: 14, len: 14 }, { x: 34, len: 16 }, { x: 60, len: 16 }, { x: 82, len: 14 }], blocks: [{ x: 100, len: 22, h: 13, w: 17 }], masts: [{ x: 25, base: 0, h: 18 }, { x: 55, base: 0, h: 18 }, { x: 80, base: 0, h: 18 }, { x: 108, base: 13, h: 9 }],
      funnels: [{ x: 115, w: 6, h: 7, base: 13 }] }),
    "Dry-cargo ship-2": () => F.ship({ L: 110, B: 18, freeboard: 7, draft: 6.5, boats: [48], derricks: true,
      hatches: [{ x: 12, len: 14 }, { x: 28, len: 12 }, { x: 70, len: 14 }, { x: 88, len: 12 }], blocks: [{ x: 45, len: 20, h: 12, w: 15 }], masts: [{ x: 20, base: 0, h: 16 }, { x: 80, base: 0, h: 16 }, { x: 53, base: 12, h: 8 }],
      funnels: [{ x: 58, w: 5, h: 6, base: 12 }] }),
    ALBATROS: () => F.ship({ L: 71, B: 10, freeboard: 4.5, draft: 3.5, blocks: [{ x: 18, len: 22, h: 6, w: 8 }, { x: 22, len: 9, h: 9, w: 6 }], masts: [{ x: 28, base: 9, h: 9, array: 3 }],
      funnels: [{ x: 34, w: 4, h: 4, base: 6 }], guns: [{ x: 60, size: 1.6, aft: true }], launchers: [{ x: 9, len: 4, d: 1, kind: "rail", w: 1.4 }] }),
    MOLNIYA: () => F.ship({ L: 56, B: 10, freeboard: 4, draft: 2.5, blocks: [{ x: 16, len: 24, h: 5, w: 8 }, { x: 18, len: 10, h: 8, w: 6 }], masts: [{ x: 25, base: 8, h: 8, array: 2.5 }],
      guns: [{ x: 8, size: 1.5 }, { x: 44, size: 0.8, aft: true }], launchers: [{ x: 32, len: 9, d: 0.9, kind: "tubes", n: 2, ang: 12, w: 4 }] }),
    REZKY: () => F.ship({ L: 123, B: 14, boats: [40], freeboard: 6.5, draft: 4.6, blocks: [{ x: 28, len: 50, h: 6, w: 11 }, { x: 34, len: 14, h: 11, w: 8 }], masts: [{ x: 44, base: 11, h: 14, array: 5 }],
      funnels: [{ x: 66, w: 8, h: 4, base: 6 }], guns: [{ x: 100, size: 2, aft: true }, { x: 110, size: 2, aft: true }], launchers: [{ x: 6, len: 10, d: 1.2, kind: "tubes", n: 2, ang: 5, w: 3 }, { x: 19, len: 4, d: 1, kind: "rail", w: 1.4 }] }),
    NEUSTRASH: () => F.ship({ L: 129, B: 15.6, boats: [40], freeboard: 7, draft: 5.6, blocks: [{ x: 26, len: 70, h: 7, w: 13 }, { x: 32, len: 18, h: 12, w: 9 }], masts: [{ x: 42, base: 12, h: 14, array: 6 }, { x: 70, base: 7, h: 10, dish: 3 }],
      funnels: [{ x: 58, w: 8, h: 5, base: 7 }], guns: [{ x: 12, size: 2.4 }], launchers: [{ x: 18, len: 6, d: 0.3, kind: "vls", w: 3 }], heloDeck: true }),
    MOSCOW: () => F.ship({ L: 186, B: 20.8, boats: [58], freeboard: 9, draft: 7.6, blocks: [{ x: 40, len: 100, h: 7, w: 15 }, { x: 50, len: 22, h: 15, w: 11 }, { x: 105, len: 18, h: 10, w: 9 }], masts: [{ x: 60, base: 15, h: 18, array: 7 }, { x: 112, base: 10, h: 14, array: 6, dish: 4 }],
      funnels: [{ x: 90, w: 10, h: 6, base: 7 }], guns: [{ x: 16, size: 3.2 }], launchers: [{ x: 38, len: 52, d: 1.6, kind: "tubes", n: 2, ang: 8, base: 0, w: 7 }, { x: 155, len: 8, d: 0.3, kind: "vls", w: 4 }] }),
    PERRY: () => F.ship({ L: 136, B: 13.7, boats: [36], freeboard: 6.5, draft: 4.5, blocks: [{ x: 20, len: 90, h: 7, w: 12 }, { x: 28, len: 20, h: 11, w: 9 }], masts: [{ x: 38, base: 11, h: 15, array: 4, dish: 3 }, { x: 60, base: 7, h: 12 }],
      funnels: [{ x: 66, w: 7, h: 5, base: 7 }], guns: [{ x: 58, size: 1.5, base: 7 }], launchers: [{ x: 8, len: 5, d: 1, kind: "rail", w: 1.4 }], heloDeck: true }),
    TICONDEROG: () => F.ship({ L: 173, B: 16.8, boats: [52], freeboard: 7.5, draft: 6.0, blocks: [{ x: 38, len: 95, h: 8, w: 15 }, { x: 44, len: 28, h: 15, w: 13 }, { x: 98, len: 26, h: 13, w: 12 }], masts: [{ x: 58, base: 15, h: 16 }, { x: 108, base: 13, h: 12 }],
      funnels: [{ x: 78, w: 8, h: 6, base: 8 }, { x: 92, w: 7, h: 5, base: 8 }], guns: [{ x: 14, size: 2.2 }, { x: 160, size: 2.2, aft: true }], launchers: [{ x: 22, len: 14, d: 0.3, kind: "vls", w: 5 }, { x: 135, len: 14, d: 0.3, kind: "vls", w: 5 }] }),
    "leander-gun-achilles": () => leander(), "leander-gun-andromeda": () => leander(), "leander-gun-ariadne": () => leander(),
    USS_Arleigh_Burke_IIa: () => F.ship({ L: 155, B: 20, boats: [48], freeboard: 8, draft: 6.3, blocks: [{ x: 36, len: 80, h: 8, w: 17 }, { x: 40, len: 22, h: 16, w: 14 }], masts: [{ x: 56, base: 16, h: 16 }],
      funnels: [{ x: 70, w: 8, h: 6, base: 8 }, { x: 94, w: 7, h: 5, base: 8 }], guns: [{ x: 14, size: 2.2 }], launchers: [{ x: 24, len: 10, d: 0.3, kind: "vls", w: 5 }, { x: 118, len: 12, d: 0.3, kind: "vls", w: 5 }], heloDeck: true }),
  };
  function leander() {
    return F.ship({ L: 113, B: 12.5, freeboard: 6.5, draft: 4.5, blocks: [{ x: 26, len: 50, h: 6, w: 10 }, { x: 30, len: 14, h: 10, w: 8 }], masts: [{ x: 40, base: 10, h: 12, array: 4 }, { x: 64, base: 6, h: 10 }],
      funnels: [{ x: 54, w: 7, h: 5, base: 6 }], guns: [{ x: 14, size: 2.2 }], launchers: [{ x: 82, len: 4, d: 1, kind: "rail", w: 1.4 }], heloDeck: true });
  }

  // =========================================================== spec lookup
  const SPECS = {
    ...TANK, ...TOWED, ...SHIP,
    "BMP-2": bmp2, "M-2 Bradley": () => bradley(false), "M6 Linebacker": () => bradley(true), "M-113": () => m113(),
    Sd_Kfz_251: () => halftrack(false), M2A1_halftrack: () => halftrack(true), "BTR-60": btr60,
    "ZSU-23-4 Shilka": shilka, ZSU_57_2: zsu57, "2S6 Tunguska": tunguska, Gepard: gepard, Vulcan: vulcan,
    "Strela-10M3": strela10, "M48 Chaparral": chaparral, "Roland ADS": roland, "Tor 9A331": tor, "Osa 9A33 ln": osa,
    "Strela-1 9P31": strela1, "M1097 Avenger": avenger,
    "SA-18 Igla manpad": soldier, "SA-18 Igla-S manpad": soldier, "Soldier stinger": soldier,
    "SA-2 Guideline": () => staticRail({ L: 10.6, d: 0.5, n: 1, elev: 30, booster: true, h: 2.0, W: 6.0 }),
    "SA-3 Goa": () => staticRail({ L: 6.1, d: 0.38, n: 4, elev: 25, booster: true, h: 1.5, W: 4.0 }),
    "MIM-23 Hawk": () => staticRail({ L: 5.0, d: 0.36, n: 3, elev: 25, h: 1.3, W: 4.0 }),
    "SA-6 Gainful": sa6, "SA-11 Gadfly": sa11,
    "SA-10 Grumble": () => maz543(7.25, 4), "SA-20 Gargoyle": () => maz543(7.5, 4), "SA-20B Gargoyle": () => maz543(7.5, 4),
    "MIM-104 Patriot": patriot, NASAMS: nasams,
    "88mm Flak battery": TOWED.flak36, "Heavy Flak battery": TOWED.flak41, "3.7-inch AA battery": TOWED.QF_37_AA,
    "Heavy AA battery": TOWED.QF_37_AA, "Radar-directed AAA": TOWED["KS-19"],
    "p-19 s-125 sr": () => truckRadar({ L: 7.0, aw: 6.0, ah: 1.4, mast: 1.4, ax: 4.8 }),
    "1L13 EWR": () => boxSpring(17, 6, 9, 10), "55G6 EWR": () => boxSpring(28, 8, 10, 12),
    "FuMG-401": freya, "FPS-117": fps117,
    "2B11 mortar": mortar, "Grad-URAL": grad, "M-109": m109, "SAU Gvozdika": gvozdika, "SAU Msta": msta, MLRS: mlrs,
  };
  // What the drawing shows when a battery or site is represented by one unit.
  const SHOWS = {
    "88mm Flak battery": "8.8 cm Flak 36", "Heavy Flak battery": "8.8 cm Flak 41", "3.7-inch AA battery": "QF 3.7-inch gun",
    "Heavy AA battery": "QF 3.7-inch gun", "Radar-directed AAA": "KS-19 gun", "SA-2 Guideline": "SM-90 launcher",
    "SA-3 Goa": "5P73 launcher", "MIM-23 Hawk": "M192 launcher", "SA-6 Gainful": "2P25 launcher", "SA-11 Gadfly": "9A310 TELAR",
    "SA-10 Grumble": "5P85 launcher", "SA-20 Gargoyle": "5P85 launcher", "SA-20B Gargoyle": "5P85 launcher",
    "MIM-104 Patriot": "M901 launcher", NASAMS: "NASAMS launcher", "M6 Linebacker": "M6 Linebacker",
    "SA-18 Igla manpad": "Igla gunner", "SA-18 Igla-S manpad": "Igla-S gunner", "Soldier stinger": "Stinger gunner",
  };

  /* Lay out side (top-left), plan (below) and front (right) at one scale inside
   * box {x, y, w, h} (sheet px). Returns the SVG body and each view's extents in
   * sheet px for dimension lines. */
  function render(e, box = { x: 18, y: 34, w: 406, h: 292 }) {
    const fn = SPECS[e.key];
    if (!fn) return null;
    let v;
    try { v = fn(); } catch (err) { console.warn("draw3v", e.key, err); return null; }
    const L = v.xmax - v.xmin, W = v.W, ymin = v.ymin || 0, Hh = v.H - ymin;
    const gap = 30;                                 // px between views (room for dimensions)
    const s = Math.min((box.w - gap * 2.2) / (L + W), (box.h - gap * 2.4) / (Hh + W));
    const cw = (L + W) * s + gap, ch = (Hh + W) * s + gap;
    const x0 = box.x + (box.w - cw - gap * 0.6) / 2 + 4, y0 = box.y + (box.h - ch - gap * 0.8) / 2 + 4;
    const ground = y0 + v.H * s;
    const sideX = x0 - v.xmin * s, topY = y0 + Hh * s + gap, frontX = x0 + L * s + gap + W / 2 * s;
    const sv = (body, tx, ty, sy) => `<g transform="translate(${tx.toFixed(2)} ${ty.toFixed(2)}) scale(${s.toFixed(4)} ${(sy * s).toFixed(4)})">${body}</g>`;
    let body = `<g class="v3">`;
    body += `<line class="x" x1="${x0 - 6}" y1="${ground}" x2="${x0 + L * s + 6}" y2="${ground}"/>`
      + `<line class="x" x1="${frontX - W / 2 * s - 6}" y1="${ground}" x2="${frontX + W / 2 * s + 6}" y2="${ground}"/>`;
    body += sv(v.side, sideX, ground, -1) + sv(v.top, sideX, topY + W / 2 * s, 1) + sv(v.front, frontX, ground, -1);
    // projection lines between views
    body += `<line class="pj" x1="${x0 + L * s + 4}" y1="${y0}" x2="${frontX - W / 2 * s - 4}" y2="${y0}"/>`
      + `<line class="pj" x1="${x0}" y1="${ground + 4}" x2="${x0}" y2="${topY - 4}"/>`;
    body += "</g>";
    return {
      body, scale: s, shows: SHOWS[e.key],
      views: {
        side: { x1: x0, x2: x0 + L * s, top: y0, bottom: y0 + Hh * s, ground },
        top: { x1: x0, x2: x0 + L * s, top: topY, bottom: topY + W * s },
        front: { x1: frontX - W / 2 * s, x2: frontX + W / 2 * s, top: y0, bottom: y0 + Hh * s },
      },
      size: { length: L, width: W, height: v.H },
    };
  }

  global.Draw3V = { render, has: (key) => key in SPECS, keys: () => Object.keys(SPECS) };
})(window);
