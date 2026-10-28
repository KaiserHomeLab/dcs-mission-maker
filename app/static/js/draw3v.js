/* Detailed 3-view line drawings for ground and naval units that have no real
 * drawing. Everything is drawn in metres and scaled, so side, top and front
 * views share one true scale built from the unit's real length/width/height.
 *
 * Draw3V.render(entry, box) -> SVG fragment (white line art for the blueprint
 * sheet), or null when the unit has no spec. Views are drawn back-to-front with
 * opaque "occ" fills so hidden lines disappear, like a real line drawing.
 *
 * Styles (static/css/blueprint.css, all vector-effect: non-scaling-stroke):
 *   k1 outline · k2 detail · k3 fine detail · kh hidden · kc centreline · occ occluding fill
 */
(function (global) {
  "use strict";
  const f = (n) => Math.round(n * 1000) / 1000;
  const pts = (a) => a.map(([x, y]) => `${f(x)},${f(y)}`).join(" ");

  // ------------------------------------------------------------ primitives
  // Side and front views use y = height above ground (flipped at render time).
  const poly = (a, k = "k1", occ = true) => `<polygon class="${k}${occ ? " occ" : ""}" points="${pts(a)}"/>`;
  const line = (a, k = "k2") => `<polyline class="${k}" points="${pts(a)}"/>`;
  const seg = (x1, y1, x2, y2, k = "k2") => `<line class="${k}" x1="${f(x1)}" y1="${f(y1)}" x2="${f(x2)}" y2="${f(y2)}"/>`;
  const circ = (x, y, r, k = "k1", occ = true) => `<circle class="${k}${occ ? " occ" : ""}" cx="${f(x)}" cy="${f(y)}" r="${f(r)}"/>`;
  const rect = (x, y, w, h, k = "k1", occ = true) => `<rect class="${k}${occ ? " occ" : ""}" x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}"/>`;
  const path = (d, k = "k1", occ = true) => `<path class="${k}${occ ? " occ" : ""}" d="${d}"/>`;
  const grp = (s, tf) => `<g transform="${tf}">${s}</g>`;
  const rot = (s, x, y, deg) => grp(s, `translate(${f(x)} ${f(y)}) rotate(${f(deg)})`);
  const range = (a, b, n) => Array.from({ length: n }, (_, i) => (n === 1 ? (a + b) / 2 : a + (b - a) * i / (n - 1)));

  // A road wheel / idler as seen from the side.
  function wheel(x, y, r, style = "steel") {
    let s = circ(x, y, r) + circ(x, y, r * 0.84, "k3", false);
    if (style === "steel" || style === "rubber") {
      s += circ(x, y, r * 0.55, "k3", false) + circ(x, y, r * 0.24, "k2", false);
      for (let i = 0; i < 8; i++) {
        const a = i * Math.PI / 4;
        s += circ(x + Math.cos(a) * r * 0.4, y + Math.sin(a) * r * 0.4, r * 0.06, "k3", false);
      }
    } else if (style === "spoked") {
      s += circ(x, y, r * 0.2, "k2", false);
      for (let i = 0; i < 6; i++) { const a = i * Math.PI / 3; s += seg(x + Math.cos(a) * r * 0.2, y + Math.sin(a) * r * 0.2, x + Math.cos(a) * r * 0.8, y + Math.sin(a) * r * 0.8, "k3"); }
    } else if (style === "tyre") {
      s += circ(x, y, r * 0.62, "k2", false) + circ(x, y, r * 0.2, "k2", false);
      for (let i = 0; i < 10; i++) { const a = i * Math.PI / 5; s += circ(x + Math.cos(a) * r * 0.42, y + Math.sin(a) * r * 0.42, r * 0.04, "k3", false); }
      for (let i = 0; i < 24; i++) { const a = i * Math.PI / 12; s += seg(x + Math.cos(a) * r * 0.86, y + Math.sin(a) * r * 0.86, x + Math.cos(a) * r, y + Math.sin(a) * r, "k3"); }
    }
    return s;
  }
  function sprocket(x, y, r) {
    const teeth = [];
    for (let i = 0; i < 26; i++) { const a = i * Math.PI / 13, rr = i % 2 ? r : r * 0.88; teeth.push([x + Math.cos(a) * rr, y + Math.sin(a) * rr]); }
    return poly(teeth) + circ(x, y, r * 0.62, "k3", false) + circ(x, y, r * 0.26, "k2", false);
  }

  /* Tracked running gear, side view.
   *  o = { x0, x1: track ends, n: road wheels, r: wheel radius, sprocket: "rear"|"front",
   *        returns: return rollers, style: wheel style, interleave, skirt: "rubber"|"panel"|"plate"|null,
   *        skirtTop, pitch }                                                       */
  function trackSide(o) {
    const r = o.r, pitch = o.pitch || 0.16, th = 0.09;
    const idR = r * 0.82, spR = r * 0.78;
    const front = o.sprocket === "front";
    const ix = o.x0 + idR, iy = r * 1.35 + th, sx = o.x1 - spR, sy = r * 1.4 + th;
    const topY = Math.max(iy, sy) + idR * 0.95;
    const xa = o.x0 + idR * 2.0 + r * 0.9, xb = o.x1 - spR * 2.0 - r * 0.9;
    const wheels = range(xa, xb, o.n);
    let s = "";
    // track outer band
    s += path(`M ${f(xa - r * 0.6)} 0 L ${f(xb + r * 0.6)} 0 Q ${f(o.x1 + 0.02)} 0 ${f(o.x1 + 0.03)} ${f(sy)} Q ${f(o.x1 + 0.03)} ${f(topY)} ${f(sx - spR * 0.4)} ${f(topY)}`
      + ` L ${f(ix + idR * 0.4)} ${f(topY)} Q ${f(o.x0 - 0.03)} ${f(topY)} ${f(o.x0 - 0.03)} ${f(iy)} Q ${f(o.x0 - 0.02)} 0 ${f(xa - r * 0.6)} 0 Z`, "k1");
    s += line([[xa - r * 0.5, th], [xb + r * 0.5, th]], "k3") + line([[ix + idR * 0.4, topY - th], [sx - spR * 0.4, topY - th]], "k3");
    for (let x = xa - r * 0.5; x < xb + r * 0.5; x += pitch) s += seg(x, 0, x, th, "k3");
    for (let x = ix + idR * 0.5; x < sx - spR * 0.4; x += pitch) s += seg(x, topY - th, x, topY, "k3");
    // return rollers (upper run sits on them)
    for (const x of range(xa + r * 0.6, xb - r * 0.6, o.returns || 0)) s += circ(x, topY - th - 0.08, 0.08, "k2");
    // wheels: interleaved sets draw the inner row first
    // road wheels ride on the lower run, so it shows beneath them
    const wy = r + th * 0.9;
    if (o.interleave) for (const x of range(xa + r * 0.55, xb - r * 0.55, o.n - 1)) s += wheel(x, wy, r, o.style);
    for (const x of wheels) s += wheel(x, wy, r, o.style);
    s += front ? sprocket(ix, iy, spR) + wheel(sx, sy, idR, "spoked") : wheel(ix, iy, idR, "spoked") + sprocket(sx, sy, spR);
    // side skirts
    if (o.skirt) {
      const top = o.skirtTop || topY + 0.12, bot = o.skirt === "rubber" ? topY - r * 0.7 : r * 0.95;
      const x0 = o.x0 + idR * 0.6, x1 = o.x1 - spR * 0.4;
      if (o.skirt === "rubber") {
        const pts2 = [[x0, top]];
        for (const x of range(x0, x1, 10)) pts2.push([x, bot], [x + (x1 - x0) / 20, bot + 0.05]);
        s += poly([...pts2, [x1, top]], "k2");
        for (const x of range(x0, x1, 10).slice(1)) s += seg(x, top, x, bot, "k3");
      } else {
        s += poly([[x0 + 0.1, top], [x1, top], [x1, bot + 0.05], [x0 + 0.25, bot], [x0, bot + 0.2]], "k1");
        const panels = o.skirt === "panel" ? 7 : 4;
        for (const x of range(x0, x1, panels + 1).slice(1, -1)) s += seg(x, top, x, bot, "k3");
        for (const x of range(x0 + 0.2, x1 - 0.2, panels * 3)) s += circ(x, top - 0.08, 0.025, "k3", false);
      }
    }
    return { s, topY, wheels };
  }

  // Wheeled running gear, side view.
  function wheelsSide(xs, r) { return xs.map((x) => wheel(x, r, r, "tyre")).join(""); }

  // Track as seen from above (one side) and from the front.
  function trackTop(x0, x1, y0, w, pitch = 0.16) {
    let s = rect(x0, y0, x1 - x0, w, "k1");
    for (let x = x0 + pitch; x < x1; x += pitch) s += seg(x, y0, x, y0 + w, "k3");
    return s + seg(x0, y0 + w * 0.5, x1, y0 + w * 0.5, "k3");
  }
  function trackFront(x, w, h) {
    let s = rect(x, 0, w, h, "k1");
    for (let y = 0.08; y < h; y += 0.12) s += seg(x, y, x + w, y, "k3");
    return s + seg(x + w * 0.5, 0, x + w * 0.5, h, "k3");
  }

  // ------------------------------------------------------------- gun parts
  /* Gun barrel along +x from (x, y), seen from the side or above.
   *  o = { len, d: outer dia, evac: [pos 0..1], sleeve: bands, brake, mrs }  */
  function barrel(x, y, o) {
    const r = o.d / 2;
    let s = poly([[x, y - r * 1.25], [x + o.len * 0.05, y - r], [x + o.len, y - r * 0.85], [x + o.len, y + r * 0.85], [x + o.len * 0.05, y + r], [x, y + r * 1.25]]);
    if (o.evac != null) { const ex = x + o.len * o.evac; s += poly([[ex, y - r], [ex + 0.1, y - r * 1.55], [ex + 0.62, y - r * 1.5], [ex + 0.72, y - r * 0.95], [ex + 0.72, y + r * 0.95], [ex + 0.62, y + r * 1.5], [ex + 0.1, y + r * 1.55], [ex, y + r]], "k2"); }
    for (const p of o.sleeve || []) s += seg(x + o.len * p, y - r * 1.05, x + o.len * p, y + r * 1.05, "k3");
    if (o.brake) s += rect(x + o.len - 0.04, y - r * 1.6, 0.42, r * 3.2, "k2") + seg(x + o.len + 0.12, y - r * 1.6, x + o.len + 0.12, y + r * 1.6, "k3") + seg(x + o.len + 0.26, y - r * 1.6, x + o.len + 0.26, y + r * 1.6, "k3");
    if (o.mrs) s += rect(x + o.len - 0.1, y + r * 0.85, 0.12, 0.05, "k3", false);
    s += seg(x, y, x + o.len + (o.brake ? 0.4 : 0), y, "kc");
    return s;
  }
  function muzzle(x, y, d) { return circ(x, y, d * 0.75) + circ(x, y, d * 0.4, "k2", false) + circ(x, y, d * 0.2, "k3", false); }

  // ------------------------------------------------------- vehicle details
  function cupola(x, y, r, h, mg = true) {
    let s = poly([[x - r, y], [x - r * 0.9, y + h], [x + r * 0.9, y + h], [x + r, y]], "k2") + seg(x - r * 0.95, y + h * 0.55, x + r * 0.95, y + h * 0.55, "k3");
    for (const px of [x - r * 0.5, x, x + r * 0.5]) s += rect(px - 0.04, y + h * 0.6, 0.08, h * 0.25, "k3", false);
    if (mg) s += rect(x - r * 0.3, y + h, r * 0.6, 0.08, "k2") + seg(x - r * 0.3, y + h + 0.04, x - r * 0.3 - 0.9, y + h + 0.08, "k2");
    return s;
  }
  function eraRows(x0, x1, y0, y1, cols, rows) {
    let s = "";
    const w = (x1 - x0) / cols, h = (y1 - y0) / rows;
    for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) s += rect(x0 + i * w + 0.01, y0 + j * h + 0.01, w - 0.02, h - 0.02, "k3");
    return s;
  }
  function smokeLaunchers(x, y, n, dx = 0.12) { let s = ""; for (let i = 0; i < n; i++) s += rot(rect(0, -0.04, 0.24, 0.08, "k3"), x + i * dx, y + i * 0.03, 30); return s; }
  function antenna(x, y, h) { return rect(x - 0.03, y, 0.06, 0.08, "k3") + seg(x, y + 0.08, x - h * 0.12, y + h, "k3"); }
  function grille(x0, x1, y, h, n = 10) { let s = rect(x0, y, x1 - x0, h, "k2"); for (const x of range(x0, x1, n).slice(1, -1)) s += seg(x, y, x, y + h, "k3"); return s; }
  function box(x, y, w, h) { return rect(x, y, w, h, "k2") + seg(x, y + h * 0.75, x + w, y + h * 0.75, "k3") + rect(x + w * 0.4, y + h * 0.4, w * 0.2, h * 0.15, "k3", false); }
  function drum(x, y, l, r) { return rect(x, y, l, r * 2, "k2") + seg(x + l * 0.33, y, x + l * 0.33, y + r * 2, "k3") + seg(x + l * 0.66, y, x + l * 0.66, y + r * 2, "k3"); }
  function hatchTop(x, y, r) { return circ(x, y, r, "k2") + circ(x, y, r * 0.75, "k3", false) + seg(x - r * 0.5, y, x + r * 0.5, y, "k3"); }
  function light(x, y) { return rect(x, y, 0.12, 0.1, "k3") + circ(x + 0.13, y + 0.05, 0.05, "k3", false); }

  /* Missile drawn along +x from (0,0): body diameter d, length L. */
  function missile(L, d, finScale = 1, canards = true) {
    const r = d / 2, nose = L * 0.16, fin = d * 1.6 * finScale;
    let s = path(`M 0 0 Q ${f(nose * 0.3)} ${f(r * 0.95)} ${f(nose)} ${f(r)} L ${f(L - 0.04)} ${f(r)} L ${f(L)} ${f(r * 0.8)} L ${f(L)} ${f(-r * 0.8)} L ${f(L - 0.04)} ${f(-r)} L ${f(nose)} ${f(-r)} Q ${f(nose * 0.3)} ${f(-r * 0.95)} 0 0 Z`);
    s += poly([[L * 0.86, r], [L - 0.03, r + fin], [L, r + fin], [L, r]], "k2") + poly([[L * 0.86, -r], [L - 0.03, -r - fin], [L, -r - fin], [L, -r]], "k2");
    if (canards) s += poly([[nose * 1.1, r], [nose * 1.25, r + fin * 0.45], [nose * 1.45, r + fin * 0.45], [nose * 1.5, r]], "k3") + poly([[nose * 1.1, -r], [nose * 1.25, -r - fin * 0.45], [nose * 1.45, -r - fin * 0.45], [nose * 1.5, -r]], "k3");
    s += seg(nose, -r, nose, r, "k3") + seg(L * 0.55, -r, L * 0.55, r, "k3") + seg(0, 0, L, 0, "kc");
    return s;
  }
  /* Launch canister along +x: length L, diameter d, ribbed. */
  function canister(L, d, ribs = 6) {
    const r = d / 2;
    let s = rect(0, -r, L, d, "k1") + rect(-0.06, -r * 1.05, 0.06, d * 1.05, "k2") + rect(L, -r * 1.05, 0.06, d * 1.05, "k2");
    for (const x of range(0, L, ribs + 2).slice(1, -1)) s += rect(x - 0.03, -r * 1.06, 0.06, d * 1.06, "k3");
    return s + seg(0, 0, L, 0, "kc");
  }
  function dish(x, y, w, deg = 0) {
    const s = path(`M ${f(-w / 2)} 0 Q 0 ${f(-w * 0.32)} ${f(w / 2)} 0 Z`, "k1") + seg(0, 0, 0, -w * 0.22, "k3") + circ(0, -w * 0.24, w * 0.04, "k3", false)
      + seg(-w * 0.35, -0.02, 0, -w * 0.22, "k3") + seg(w * 0.35, -0.02, 0, -w * 0.22, "k3");
    return rot(s, x, y, deg);
  }
  function arrayPanel(x, y, w, h, cols = 8, rows = 4, deg = 0) {
    let s = rect(0, 0, w, h, "k1");
    for (const c of range(0, w, cols + 1).slice(1, -1)) s += seg(c, 0, c, h, "k3");
    for (const rr of range(0, h, rows + 1).slice(1, -1)) s += seg(0, rr, w, rr, "k3");
    return rot(s, x, y, deg);
  }

  global.Draw3VParts = {
    poly, line, seg, circ, rect, path, grp, rot, range, wheel, sprocket, trackSide, wheelsSide, trackTop, trackFront,
    barrel, muzzle, cupola, eraRows, smokeLaunchers, antenna, grille, box, drum, hatchTop, light, missile, canister, dish, arrayPanel,
  };
})(window);
