/* Vehicle families and per-unit specs for Draw3V (see draw3v.js).
 * Every family returns { side, top, front, xmin, xmax, W, H } in metres:
 *   side  : x along the vehicle (front = 0, rear = +), y = height above ground
 *   top   : x along the vehicle, y = lateral (centre 0)
 *   front : x = lateral (centre 0), y = height above ground
 * Proportions follow published dimensions; detail is representative.
 */
(function (global) {
  "use strict";
  const D = global.Draw3VParts;
  const { poly, line, seg, circ, rect, path, grp, rot, range } = D;
  const flipX = (s, x, y) => grp(s, `translate(${x} ${y}) scale(-1 1)`);

  // ================================================================ armour
  /* p: hullL W hullH H, track{n r returns sprocket skirt style interleave},
   *    turret{x len w h shape cupola}, gun{len d evac brake sleeve elev}, extras  */
  function armour(p) {
    const tW = p.trackW || Math.min(0.6, p.W * 0.18), hL = p.hullL, W = p.W, hH = p.hullH;
    const tr = D.trackSide({ x0: 0.15, x1: hL - 0.1, ...p.track });
    const topY = tr.topY, T = p.turret, G = p.gun;
    let side = "", top = "", front = "";
    // ---- side: hull, then running gear, fenders, turret, gun
    const g = p.glacis || 1.4;
    const hullPts = p.hullPts || [[0, topY * 0.5], [-0.05, topY * 0.75], [g, hH], [hL - 0.25, hH], [hL, hH - 0.3], [hL, topY * 0.55]];
    side += poly(hullPts);
    if (p.ribbedGlacis) for (const x of range(0.2, g - 0.1, 5)) side += seg(x, topY * 0.75 + (x / g) * (hH - topY * 0.75) - 0.04, x + 0.08, topY * 0.75 + ((x + 0.08) / g) * (hH - topY * 0.75) - 0.12, "k3");
    side += tr.s;
    side += rect(0.1, topY + 0.05, hL - 0.2, 0.06, "k2");                                       // fender
    for (const b of p.fenderBoxes || []) side += D.box(b[0], topY + 0.11, b[1], 0.3);
    if (p.drums) side += circ(hL - 0.25, hH + 0.28, 0.28, "k2") + circ(hL - 0.25, hH + 0.28, 0.22, "k3", false);
    if (p.exhaust) side += D.grille(hL - 1.6, hL - 0.9, hH - 0.35, 0.18, 8);
    if (p.eraHull) side += D.eraRows(0.3, g - 0.05, topY * 0.85, hH - 0.05, 5, 1);
    if (p.rearDoor) side += rect(hL - 0.05, topY * 0.7, 0.05, hH - topY * 0.8, "k2");
    let tx0 = 0, tx1 = 0, ty1 = hH, gx = 0, gy = hH;
    if (T) {
      tx0 = T.x - T.len / 2; tx1 = T.x + T.len / 2; ty1 = hH + T.h;
      const L = T.len, h = T.h;
      let shape;
      if (T.shape === "dome") shape = [[tx0, hH], [tx0 + 0.1 * L, hH + h * 0.72], [tx0 + 0.38 * L, hH + h], [tx1 - 0.2 * L, hH + h * 0.96], [tx1, hH + h * 0.45], [tx1 - 0.04, hH]];
      else if (T.shape === "welded") shape = [[tx0, hH], [tx0 + 0.04, hH + h * 0.8], [tx0 + 0.3 * L, hH + h], [tx1 - 0.1 * L, hH + h], [tx1, hH + h * 0.55], [tx1 - 0.05, hH]];
      else if (T.shape === "slab") shape = [[tx0, hH + h * 0.1], [tx0 + 0.06, hH + h * 0.75], [tx0 + 0.32 * L, hH + h], [tx1, hH + h], [tx1 + 0.05, hH + h * 0.3], [tx1 - 0.2, hH]];
      else if (T.shape === "cast") shape = [[tx0, hH + h * 0.2], [tx0 + 0.08 * L, hH + h * 0.8], [tx0 + 0.35 * L, hH + h], [tx1 - 0.15 * L, hH + h * 0.98], [tx1, hH + h * 0.6], [tx1 - 0.08, hH]];
      else if (T.shape === "box") shape = [[tx0 + 0.08, hH], [tx0, hH + h * 0.35], [tx0 + 0.05, hH + h * 0.95], [tx0 + 0.15, hH + h], [tx1 - 0.1, hH + h], [tx1, hH + h * 0.9], [tx1, hH]];
      else shape = [[tx0, hH], [tx0 + 0.1, hH + h], [tx1 - 0.1, hH + h], [tx1, hH]];   // small / ifv
      if (T.bustle) side += D.box(tx1 - 0.05, hH + h * 0.25, T.bustle, h * 0.6);
      side += poly(shape);
      side += seg(tx0 + 0.1, hH + 0.06, tx1 - 0.1, hH + 0.06, "k3");
      if (T.era) side += D.eraRows(tx0 + 0.08, tx0 + L * 0.42, hH + h * 0.12, hH + h * 0.82, 4, 2);
      if (T.shtora) side += D.box(tx0 + 0.15, hH + h * 0.3, 0.45, 0.32);
      if (T.smoke) side += D.smokeLaunchers(tx0 + L * 0.35, hH + h * 0.55, 4);
      if (T.ir) side += D.box(tx0 - 0.05, hH + h * 0.6, 0.38, 0.3) + D.circ(tx0 - 0.08, hH + h * 0.75, 0.13, "k2");
      if (T.cupola !== false) side += D.cupola(T.cupolaX || T.x + L * 0.15, hH + h * 0.95, T.cupolaR || 0.32, T.cupolaH || 0.22, T.mg !== false);
      if (T.antenna) side += D.antenna(tx1 - 0.25, hH + h, 1.6);
      if (T.atgm) side += D.grp(D.canister(1.2, 0.14, 2), `translate(${T.x - 0.2} ${hH + h + 0.18})`);
      if (T.tow) side += D.box(T.x - 0.1, hH + h * 0.35, 1.0, 0.45);
      gx = tx0 + (T.gunX || 0.12); gy = hH + h * (T.gunY || 0.48);
    }
    if (G) {
      side += rect(gx - 0.05, gy - 0.18, 0.35, 0.36, "k2");                                        // mantlet
      side += rot(D.barrel(0, 0, G), gx, gy, 180 - (G.elev || 0));
    }
    // ---- top
    const hw = W / 2;
    top += D.trackTop(0.1, hL - 0.05, -hw, tW) + D.trackTop(0.1, hL - 0.05, hw - tW, tW);
    top += poly([[0, -hw + tW * 0.9], [g * 0.4, -hw + 0.05], [hL - 0.15, -hw + 0.05], [hL, -hw + 0.2], [hL, hw - 0.2], [hL - 0.15, hw - 0.05], [g * 0.4, hw - 0.05], [0, hw - tW * 0.9]]);
    top += seg(g, -hw + tW, g, hw - tW, "k2") + seg(0.4, -hw + tW, 0.4, hw - tW, "k3");
    top += seg(0, -hw + tW, hL, -hw + tW, "k3") + seg(0, hw - tW, hL, hw - tW, "k3");
    for (const x of range(hL - 1.9, hL - 0.3, 10)) top += seg(x, -hw + tW + 0.2, x, hw - tW - 0.2, "k3");             // engine deck
    top += D.hatchTop(g * 0.6, p.driverY || 0, 0.25);
    if (p.drums) top += D.drum(hL - 0.5, -hw + tW + 0.05, 0.55, 0.28) + D.drum(hL - 0.5, hw - tW - 0.6, 0.55, 0.28);
    if (T) {
      if (T.shape === "dome" || T.shape === "cast") top += `<ellipse class="k1 occ" cx="${T.x}" cy="0" rx="${T.len / 2}" ry="${T.w / 2}"/>`;
      else top += poly([[tx0, -T.w * 0.3], [tx0 + T.len * 0.25, -T.w / 2], [tx1 + (T.bustle || 0), -T.w / 2], [tx1 + (T.bustle || 0), T.w / 2], [tx0 + T.len * 0.25, T.w / 2], [tx0, T.w * 0.3]]);
      if (T.bustle) top += seg(tx1, -T.w / 2, tx1, T.w / 2, "k3");
      top += D.hatchTop(T.x + T.len * 0.12, -T.w * 0.22, 0.28) + D.hatchTop(T.x + T.len * 0.12, T.w * 0.22, 0.24);
      if (T.era) top += D.eraRows(tx0 + 0.05, tx0 + T.len * 0.35, -T.w * 0.42, -T.w * 0.08, 2, 4) + D.eraRows(tx0 + 0.05, tx0 + T.len * 0.35, T.w * 0.08, T.w * 0.42, 2, 4);
    }
    if (G) top += rot(D.barrel(0, 0, G), gx + 0.1, 0, 180);
    // ---- front
    front += D.trackFront(-hw, tW, topY + 0.05) + D.trackFront(hw - tW, tW, topY + 0.05);
    front += poly([[-hw + tW * 0.85, topY * 0.25], [-hw + tW * 0.7, hH * 0.92], [-hw + tW * 0.9, hH], [hw - tW * 0.9, hH], [hw - tW * 0.7, hH * 0.92], [hw - tW * 0.85, topY * 0.25]]);
    front += rect(-hw, topY + 0.05, W, 0.06, "k2") + D.light(-hw + tW + 0.1, hH * 0.8) + D.light(hw - tW - 0.35, hH * 0.8);
    front += seg(-hw + tW, topY * 0.55, hw - tW, topY * 0.55, "k3");
    if (p.blade) front += rect(-hw + tW * 0.9, topY * 0.2, W - tW * 1.8, 0.12, "k2");
    if (p.track.skirt) front += rect(-hw - 0.04, topY * 0.55, 0.06, topY * 0.55, "k2") + rect(hw - 0.02, topY * 0.55, 0.06, topY * 0.55, "k2");
    if (T) {
      const tw = T.w / 2, h = T.h;
      if (T.shape === "dome" || T.shape === "cast") front += path(`M ${-tw} ${hH} Q ${-tw} ${hH + h * 0.9} ${-tw * 0.4} ${hH + h} L ${tw * 0.4} ${hH + h} Q ${tw} ${hH + h * 0.9} ${tw} ${hH} Z`);
      else front += poly([[-tw, hH], [-tw * 0.95, hH + h * 0.85], [-tw * 0.75, hH + h], [tw * 0.75, hH + h], [tw * 0.95, hH + h * 0.85], [tw, hH]]);
      if (T.era) front += D.eraRows(-tw * 0.95, -tw * 0.3, hH + 0.08, hH + h * 0.8, 2, 2) + D.eraRows(tw * 0.3, tw * 0.95, hH + 0.08, hH + h * 0.8, 2, 2);
      if (T.shtora) front += rect(-tw * 0.75, hH + h * 0.3, 0.3, 0.25, "k2") + rect(tw * 0.75 - 0.3, hH + h * 0.3, 0.3, 0.25, "k2");
      if (T.cupola !== false) front += rect(-0.3 + tw * 0.35, hH + h * 0.95, 0.6, T.cupolaH || 0.22, "k2");
      if (T.ir) front += D.circ(tw * 0.35, hH + h * 0.75, 0.16, "k2");
      if (G) front += rect(-0.2, gy - 0.18, 0.4, 0.36, "k2") + D.muzzle(0, gy, G.d);
    }
    const xmin = G ? Math.min(-0.1, gx - (G.len + (G.brake ? 0.4 : 0)) * Math.cos((G.elev || 0) * Math.PI / 180)) : -0.1;
    const H = Math.max(ty1 + (T && T.cupola !== false ? (T.cupolaH || 0.22) + 0.1 : 0), hH + 0.4, p.extraH || 0);
    return { side, top, front, xmin, xmax: hL + (T && T.bustle ? 0 : 0.05), W, H, topY, hH, T, gx, gy };
  }

  // ============================================================ wheeled hull
  function wheeled(p) {
    const hL = p.hullL, W = p.W, hH = p.hullH, r = p.r;
    let side = "", top = "", front = "";
    const pts = p.boat
      ? [[0.1, r * 1.1], [0, r * 1.5], [0.9, hH], [hL - 0.4, hH], [hL, hH - 0.35], [hL, r * 1.2], [hL - 0.5, r * 0.75], [0.6, r * 0.75]]
      : [[0, r * 0.9], [0, hH - 0.4], [0.5, hH], [hL - 0.2, hH], [hL, hH - 0.2], [hL, r * 0.9]];
    side += poly(pts);
    for (const x of p.axles) side += path(`M ${x - r * 1.15} ${r * 0.9} A ${r * 1.15} ${r * 1.15} 0 0 0 ${x + r * 1.15} ${r * 0.9}`, "k3", false);
    side += D.wheelsSide(p.axles, r);
    side += seg(0.4, hH * 0.72, hL - 0.4, hH * 0.72, "k3");
    for (const x of range(1.2, hL - 1.2, p.ports || 3)) side += circ(x, hH * 0.85, 0.06, "k3", false);
    if (p.hatches) for (const x of p.hatches) side += rect(x, hH, 0.5, 0.06, "k2");
    const hw = W / 2;
    top += poly(p.boat ? [[0, -hw * 0.45], [0.9, -hw], [hL - 0.3, -hw], [hL, -hw * 0.8], [hL, hw * 0.8], [hL - 0.3, hw], [0.9, hw], [0, hw * 0.45]]
      : [[0, -hw * 0.85], [0.3, -hw], [hL, -hw], [hL, hw], [0.3, hw], [0, hw * 0.85]]);
    for (const x of p.axles) top += rect(x - r * 0.95, -hw - 0.02, r * 1.9, 0.38, "k2") + rect(x - r * 0.95, hw - 0.36, r * 1.9, 0.38, "k2");
    top += seg(0.9, -hw * 0.7, 0.9, hw * 0.7, "k3") + D.grille(hL - 1.6, hL - 0.4, -hw * 0.5, hw, 9);
    front += poly([[-hw * 0.9, r * 0.9], [-hw, hH * 0.8], [-hw * 0.7, hH], [hw * 0.7, hH], [hw, hH * 0.8], [hw * 0.9, r * 0.9]]);
    front += rect(-hw - 0.02, 0, 0.36, r * 2, "k1") + rect(hw - 0.34, 0, 0.36, r * 2, "k1");
    for (const y of range(0.1, r * 1.9, 7)) front += seg(-hw - 0.02, y, -hw + 0.34, y, "k3") + seg(hw - 0.34, y, hw + 0.02, y, "k3");
    front += rect(-hw * 0.5, hH * 0.75, hw * 0.35, 0.14, "k3") + rect(hw * 0.15, hH * 0.75, hw * 0.35, 0.14, "k3");
    return { side, top, front, xmin: -0.05, xmax: hL + 0.05, W, H: hH, hH };
  }

  // ================================================================= truck
  function truck(p) {
    const L = p.L, W = p.W, r = p.r, cab = p.cabL || 2.2, cabH = p.cabH || 2.8, frame = r * 1.25;
    let side = "", top = "", front = "";
    // chassis + bed / mount
    side += rect(0.3, frame, L - 0.4, 0.28, "k2");
    for (const x of p.axles) side += path(`M ${x - r * 1.2} ${frame + 0.1} A ${r * 1.2} ${r * 1.2} 0 0 0 ${x + r * 1.2} ${frame + 0.1}`, "k2", false);
    side += D.wheelsSide(p.axles, r);
    // cab (forward control or bonneted)
    if (p.bonnet) {
      side += poly([[0, frame + 0.2], [0, frame + 1.0], [1.4, frame + 1.15], [1.6, cabH], [cab + 1.2, cabH], [cab + 1.3, frame + 0.2]]);
      side += poly([[1.65, cabH - 0.1], [1.75, cabH - 0.75], [2.4, cabH - 0.75], [2.4, cabH - 0.1]], "k2");
      side += D.grille(0.05, 0.45, frame + 0.35, 0.55, 5);
    } else {
      side += poly([[0, frame + 0.2], [0, cabH - 0.25], [0.25, cabH], [cab, cabH], [cab, frame + 0.2]]);
      side += poly([[0.12, cabH - 0.12], [0.08, cabH - 0.9], [cab * 0.48, cabH - 0.9], [cab * 0.48, cabH - 0.12]], "k2");
      side += rect(cab * 0.55, cabH - 0.85, cab * 0.35, 0.65, "k3") + seg(cab * 0.52, frame + 0.3, cab * 0.52, cabH - 0.1, "k3");
      side += rect(cab * 0.6, frame + 0.75, 0.25, 0.05, "k3", false);
    }
    side += rect(p.bonnet ? cab + 1.45 : cab + 0.3, frame + 0.25, 1.0, 0.35, "k3");                    // fuel tank
    const hw = W / 2;
    top += rect(0.25, -hw * 0.55, L - 0.35, W * 0.55, "k2");
    for (const x of p.axles) top += rect(x - r * 0.9, -hw, r * 1.8, 0.4, "k2") + rect(x - r * 0.9, hw - 0.4, r * 1.8, 0.4, "k2");
    top += rect(0, -hw * 0.95, p.bonnet ? cab + 1.3 : cab, W * 0.95, "k1") + seg(p.bonnet ? 1.6 : 0.15, -hw * 0.85, p.bonnet ? 1.6 : 0.15, hw * 0.85, "k2");
    front += rect(-hw * 0.95, frame + 0.2, W * 0.95, cabH - frame - 0.2, "k1");
    front += rect(-hw * 0.85, cabH - 0.85, hw * 0.8, 0.65, "k2") + rect(hw * 0.05, cabH - 0.85, hw * 0.8, 0.65, "k2");
    front += D.grille(-hw * 0.5, hw * 0.5, frame + 0.35, 0.45, 9) + rect(-hw, frame + 0.05, W, 0.16, "k2");
    front += D.light(-hw * 0.85, frame + 0.4) + D.light(hw * 0.85 - 0.25, frame + 0.4);
    front += rect(-hw, 0, 0.36, r * 2, "k1") + rect(hw - 0.36, 0, 0.36, r * 2, "k1");
    for (const y of range(0.1, r * 1.9, 7)) front += seg(-hw, y, -hw + 0.36, y, "k3") + seg(hw - 0.36, y, hw, y, "k3");
    return { side, top, front, xmin: -0.05, xmax: L, W, H: cabH, hH: frame + 0.3, deck: frame + 0.3 };
  }

  // ============================================================ towed gun
  /* p: L (overall), W, r (wheel), mountH (trunnion height), elev, gunLen, d, brake,
   *    cruciform (AA platform) or split trail, barrels + cols, shield, seat, wheels */
  function towedGun(p) {
    const W = p.W || 2.2, r = p.r || 0.42, e = p.elev, c = Math.cos(e * Math.PI / 180), sn = Math.sin(e * Math.PI / 180);
    const nb = p.barrels || 1, cols = p.cols || (nb >= 2 ? 2 : 1), rows = Math.ceil(nb / cols);
    const tH = p.mountH || 1.2, d = p.d;
    const fwd = p.gunLen * 0.82, aft = p.gunLen * 0.18;          // barrel ahead of / breech behind the trunnion
    const tX = p.cruciform ? p.L * 0.5 : fwd * c + 0.3;
    const bsp = Math.max(d * 2.6, 0.17), shW = p.shieldW || Math.min(W * 0.85, 2.0);
    const colY = (i) => (i - (cols - 1) / 2) * bsp;
    let side = "", top = "", front = "";
    // ---- side
    if (p.cruciform) {
      side += rect(p.L * 0.06, 0.28, p.L * 0.88, 0.14, "k1") + seg(p.L * 0.08, 0.35, p.L * 0.92, 0.35, "k3");
      for (const x of [p.L * 0.08, p.L * 0.92]) side += poly([[x - 0.2, 0], [x + 0.2, 0], [x + 0.08, 0.28], [x - 0.08, 0.28]], "k2") + seg(x, 0.42, x, 0.62, "k2") + seg(x - 0.12, 0.62, x + 0.12, 0.62, "k3");
      if (p.wheels) for (const x of [p.L * 0.2, p.L * 0.8]) side += D.wheel(x, r, r, "tyre");
      side += poly([[tX - 0.55, 0.42], [tX - 0.32, tH - 0.45], [tX + 0.32, tH - 0.45], [tX + 0.55, 0.42]]) + seg(tX - 0.45, 0.6, tX + 0.45, 0.6, "k3");
    } else {
      side += poly([[tX - 0.05, r + 0.05], [p.L - 0.35, 0.16], [p.L, 0.02], [p.L, 0.2], [p.L - 0.3, 0.3], [tX + 0.25, r + 0.28]]) + poly([[p.L - 0.3, 0.3], [p.L - 0.22, -0.12], [p.L - 0.05, -0.12], [p.L, 0.2]], "k2");
      side += seg(tX + 0.3, r + 0.2, p.L - 0.4, 0.24, "k3") + rect(p.L - 0.75, 0.24, 0.3, 0.08, "k3");
      side += poly([[tX - 0.3, r - 0.1], [tX - 0.22, tH - 0.25], [tX + 0.35, tH - 0.25], [tX + 0.45, r - 0.1]]);
    }
    if (p.shield) side += poly([[tX - 0.42, tH - 0.62], [tX - 0.58, tH + 0.52], [tX - 0.46, tH + 0.78], [tX - 0.36, tH + 0.78], [tX - 0.32, tH - 0.62]]);
    side += poly([[tX - 0.5, tH - 0.45], [tX - 0.42, tH - 0.28], [tX + 0.6, tH - 0.28], [tX + 0.68, tH - 0.45]]);
    side += poly([[tX - 0.32, tH - 0.28], [tX - 0.08, tH + 0.14], [tX + 0.12, tH + 0.14], [tX + 0.36, tH - 0.28]]) + circ(tX, tH, 0.07, "k2");
    // cradle, breech and barrel(s), rotated about the trunnion (local +x = muzzle, +y = below the bore)
    let g = rect(-aft * 0.8, d * 0.7, aft * 0.8 + fwd * 0.42, Math.max(0.12, d * 1.5), "k1") + seg(-aft * 0.7, d * 0.7 + Math.max(0.12, d * 1.5) / 2, fwd * 0.4, d * 0.7 + Math.max(0.12, d * 1.5) / 2, "k3");
    for (let j = rows - 1; j >= 0; j--) {
      const y = -j * bsp;
      g += rect(-aft, y - d * 1.3, aft, d * 2.6, "k1") + seg(-aft * 0.5, y - d * 1.3, -aft * 0.5, y + d * 1.3, "k3")
        + D.barrel(0, y, { len: fwd, d, brake: p.brake, sleeve: [0.08, 0.35] });
    }
    side += rot(g, tX, tH, 180 - e);
    if (p.seat) {
      side += rect(tX + 0.5, tH - 0.2, 0.28, 0.06, "k2") + seg(tX + 0.64, tH - 0.2, tX + 0.6, tH - 0.45, "k3") + rect(tX + 0.72, tH - 0.14, 0.05, 0.3, "k3");
      side += circ(tX + 0.3, tH - 0.1, 0.14, "k2") + circ(tX + 0.3, tH - 0.1, 0.03, "k3", false) + seg(tX + 0.18, tH - 0.1, tX + 0.42, tH - 0.1, "k3") + seg(tX + 0.3, tH - 0.22, tX + 0.3, tH + 0.02, "k3");
    }
    if (!p.cruciform) side += D.wheel(tX, r, r, "tyre");
    // ---- plan
    if (p.cruciform) {
      top += rect(p.L * 0.06, -0.09, p.L * 0.88, 0.18, "k1") + rect(tX - 0.09, -W / 2, 0.18, W, "k1");
      for (const [x, y] of [[p.L * 0.08, 0], [p.L * 0.92, 0], [tX, -W / 2 + 0.1], [tX, W / 2 - 0.1]]) top += circ(x, y, 0.2, "k2") + circ(x, y, 0.07, "k3", false);
      top += circ(tX, 0, 0.6) + circ(tX, 0, 0.5, "k3", false);
    } else {
      for (const sg of [-1, 1]) top += poly([[tX + 0.2, sg * 0.08], [p.L, sg * W * 0.38], [p.L, sg * (W * 0.38 + 0.18)], [tX + 0.2, sg * 0.28]], "k1") + rect(p.L - 0.25, sg > 0 ? W * 0.38 - 0.1 : -W * 0.38 - 0.28, 0.25, 0.38, "k2");
      top += rect(tX - r, -W / 2, 2 * r, 0.26, "k1") + rect(tX - r, W / 2 - 0.26, 2 * r, 0.26, "k1") + seg(tX, -W / 2 + 0.26, tX, W / 2 - 0.26, "k2");
      top += rect(tX - 0.3, -0.45, 0.75, 0.9, "k1");
    }
    if (p.seat) top += rect(tX + 0.45, -0.75, 0.3, 0.25, "k2") + rect(tX + 0.45, 0.5, 0.3, 0.25, "k2") + seg(tX + 0.3, -0.62, tX + 0.3, -0.42, "k2") + seg(tX + 0.3, 0.42, tX + 0.3, 0.62, "k2");
    if (p.shield) top += path(`M ${tX - 0.42} ${-shW / 2} Q ${tX - 0.62} 0 ${tX - 0.42} ${shW / 2} L ${tX - 0.34} ${shW / 2} Q ${tX - 0.54} 0 ${tX - 0.34} ${-shW / 2} Z`);
    top += rect(tX - fwd * 0.42 * c, colY(0) - d * 1.4, (fwd * 0.42 + aft) * c, (cols - 1) * bsp + d * 2.8, "k1");
    for (let i = 0; i < cols; i++) top += rect(tX, colY(i) - d * 1.3, aft * c, d * 2.6, "k1") + rot(D.barrel(0, 0, { len: fwd * c, d, brake: p.brake, sleeve: [0.08] }), tX, colY(i), 180);
    // ---- front
    if (p.cruciform) {
      front += rect(-W / 2, 0.28, W, 0.14, "k1");
      for (const x of [-W / 2 + 0.1, W / 2 - 0.1]) front += poly([[x - 0.2, 0], [x + 0.2, 0], [x + 0.08, 0.28], [x - 0.08, 0.28]], "k2") + seg(x, 0.42, x, 0.62, "k2") + seg(x - 0.12, 0.62, x + 0.12, 0.62, "k3");
      if (p.wheels) front += rect(-W / 2 + 0.25, 0, 0.25, 2 * r, "k1") + rect(W / 2 - 0.5, 0, 0.25, 2 * r, "k1");
      front += poly([[-0.55, 0.42], [-0.32, tH - 0.45], [0.32, tH - 0.45], [0.55, 0.42]]) + rect(-0.09, 0.28, 0.18, 0.14, "k2");
    } else {
      for (const sg of [-1, 1]) front += line([[sg * 0.25, r], [sg * W * 0.42, 0.05]], "k2");
      front += rect(-W / 2 + 0.26, r - 0.06, W - 0.52, 0.12, "k1");
      for (const x of [-W / 2, W / 2 - 0.26]) { front += rect(x, 0, 0.26, 2 * r, "k1"); for (const y of range(0.08, 2 * r - 0.08, 8)) front += seg(x, y, x + 0.26, y, "k3"); }
      front += rect(-0.3, r - 0.1, 0.6, tH - r - 0.15, "k1");
    }
    front += rect(-0.5, tH - 0.45, 1.0, 0.17, "k1") + rect(-0.42, tH - 0.28, 0.13, 0.42, "k1") + rect(0.29, tH - 0.28, 0.13, 0.42, "k1");
    if (p.seat) front += circ(-0.68, tH - 0.1, 0.14, "k2") + circ(0.68, tH - 0.1, 0.14, "k2") + rect(-0.98, tH - 0.2, 0.25, 0.06, "k2") + rect(0.73, tH - 0.2, 0.25, 0.06, "k2");
    if (p.shield) front += poly([[-shW / 2, tH - 0.62], [-shW / 2, tH + 0.52], [-shW / 2 + 0.15, tH + 0.78], [shW / 2 - 0.15, tH + 0.78], [shW / 2, tH + 0.52], [shW / 2, tH - 0.62]])
      + seg(-shW / 2 + 0.05, tH + 0.52, shW / 2 - 0.05, tH + 0.52, "k3") + rect(-(cols * bsp) / 2 - 0.08, tH - 0.25, cols * bsp + 0.16, 0.6, "k2");
    front += rect(colY(0) - d * 1.5, tH - 0.15, (cols - 1) * bsp + d * 3, Math.max(0.3, fwd * 0.42 * sn), "k1");
    for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) {
      const bx = colY(i), by = tH + j * bsp * c;
      front += rect(bx - d / 2, by, d, Math.max(d, fwd * sn), "k1") + D.muzzle(bx, by + fwd * sn, p.brake ? d * 1.6 : d);
    }
    const H = Math.max(tH + fwd * sn + d * 2 + (rows - 1) * bsp, p.shield ? tH + 0.8 : 0);
    return { side, top, front, xmin: Math.min(0, tX - fwd * c - (p.brake ? 0.45 : 0.1)), xmax: Math.max(p.L, tX + aft * c + 0.8), W: Math.max(W, shW), H };
  }

  // ================================================================= ships
  /* p: L, B, freeboard, draft; blocks [{x, len, h, w}] (superstructure), masts [{x, base, h, array, dish}],
   *    funnels [{x, w, h, base}], guns [{x, size, base, aft}], launchers [{x, len, d, kind, n, ang, w}],
   *    hatches [{x, len}] and derricks (cargo), boats [x...] (lifeboats on the tallest block), heloDeck */
  function ship(p) {
    const L = p.L, B = p.B, fb = p.freeboard || L * 0.07, dr = p.draft || L * 0.035, hb = B / 2;
    const deckY = (x) => (x < L * 0.25 ? fb * (1.15 - 0.17 * x / (L * 0.25)) : fb * (0.98 - 0.18 * (x - L * 0.25) / (L * 0.75)));
    const rail = Math.max(0.9, L * 0.006);
    const blocks = p.blocks || [];
    const bridge = [...blocks].sort((a, b) => b.h - a.h || a.x - b.x)[0];
    let side = "", top = "", front = "";

    // ---------------------------------------------------------------- side
    // underwater gear first, so the hull hides what it should
    side += poly([[L * 0.955, -dr * 0.15], [L * 0.99, -dr * 0.2], [L * 0.99, -dr * 0.9], [L * 0.955, -dr * 0.85]], "k2");
    side += `<ellipse class="k2 occ" cx="${L * 0.94}" cy="${-dr * 0.6}" rx="${L * 0.004}" ry="${dr * 0.32}"/>`;
    side += path(`M 0 ${fb * 1.25} Q ${L * 0.04} ${fb * 0.6} ${L * 0.06} ${-dr} L ${L * 0.93} ${-dr} Q ${L * 0.97} ${-dr * 0.6} ${L * 0.985} ${fb * 0.2} L ${L} ${fb * 0.85} Q ${L * 0.5} ${fb * 0.95} ${L * 0.25} ${fb * 1.05} Z`);
    side += seg(L * 0.03, 0, L * 0.99, 0, "kc") + line([[L * 0.035, fb * 0.12], [L * 0.985, fb * 0.12]], "k3");   // waterline, boot-topping
    side += line([[L * 0.02, fb * 1.15], [L * 0.25, fb * 0.98], [L * 0.99, fb * 0.8]], "k3");                          // deck edge
    for (const x of range(L * 0.15, L * 0.85, Math.round(L / 6))) side += circ(x, fb * 0.55, L * 0.0025, "k3", false);
    side += circ(L * 0.035, fb * 0.85, L * 0.004, "k2", false) + path(`M ${L * 0.035} ${fb * 0.8} l 0 ${-fb * 0.22} m ${-L * 0.006} ${fb * 0.06} q ${L * 0.006} ${-fb * 0.08} ${L * 0.012} 0`, "k2", false);  // hawse + anchor
    // railings along the open deck
    const railPts = range(L * 0.04, L * 0.98, Math.max(12, Math.round(L / 2.5)));
    side += line(railPts.map((x) => [x, deckY(x) + rail]), "k3");
    for (const x of railPts) side += seg(x, deckY(x), x, deckY(x) + rail, "k3");
    for (const h of p.hatches || []) side += rect(h.x, deckY(h.x), h.len, rail * 1.2, "k2");
    for (const fn of p.funnels || []) {
      const y0 = fn.base + fb, y1 = y0 + fn.h;
      side += poly([[fn.x, y0], [fn.x + fn.w * 0.15, y1], [fn.x + fn.w, y1], [fn.x + fn.w * 1.05, y0]]);
      side += rect(fn.x + fn.w * 0.1, y1, fn.w * 0.95, fn.h * 0.08, "k2") + seg(fn.x + fn.w * 0.12, y1 - fn.h * 0.25, fn.x + fn.w, y1 - fn.h * 0.25, "k3");
      for (const x of range(fn.x + fn.w * 0.3, fn.x + fn.w * 0.8, 3)) side += rect(x, y0 + fn.h * 0.3, fn.w * 0.08, fn.h * 0.25, "k3", false);
    }
    for (const s of blocks) {
      const y0 = fb, y1 = fb + s.h;
      side += poly([[s.x, y0], [s.x + 0.04 * s.len, y1], [s.x + s.len, y1], [s.x + s.len, y0]]);
      for (let d = 1; d * 2.7 < s.h - 0.8; d++) side += seg(s.x + 0.04 * s.len * (d * 2.7 / s.h), y0 + d * 2.7, s.x + s.len, y0 + d * 2.7, "k3");   // deck levels
      for (const x of range(s.x + s.len * 0.1, s.x + s.len * 0.9, Math.max(2, Math.round(s.len / 3)))) side += rect(x, y0 + s.h * 0.6, s.len * 0.03, s.h * 0.12, "k3", false);
      side += rect(s.x + s.len * 0.82, y0, Math.min(1.0, s.len * 0.06), Math.min(2.0, s.h * 0.4), "k3", false);  // door
      if (s === bridge) {
        const wy = y1 - Math.min(1.6, s.h * 0.18);
        side += line([[s.x + 0.04 * s.len * ((wy - y0) / s.h), wy], [s.x + s.len * 0.35, wy]], "k2");
        for (const x of range(s.x + s.len * 0.05, s.x + s.len * 0.33, 6)) side += rect(x, wy + 0.2, s.len * 0.035, Math.min(1.1, s.h * 0.12), "k3", false);
        for (const bx of p.boats || []) {
          const by = y0 + s.h * 0.45;
          side += path(`M ${bx} ${by} q 0 ${-1.4} 1.2 ${-1.4} l ${4.6} 0 q 1.2 0 1.2 1.4 z`, "k1") + seg(bx + 0.4, by, bx + 0.4, by + 1.4, "k3") + seg(bx + 6.6, by, bx + 6.6, by + 1.4, "k3");
        }
      }
    }
    for (const m of p.masts || []) {
      const y0 = m.base + fb, y1 = y0 + m.h, w = m.h * 0.05;
      side += line([[m.x - w, y0], [m.x, y1], [m.x + w, y0]], "k2");
      if (m.h > 8) for (let i = 0; i < 4; i++) {                                                   // lattice bracing
        const ya = y0 + m.h * i / 5, yb = y0 + m.h * (i + 1) / 5, wa = w * (1 - i / 5), wb = w * (1 - (i + 1) / 5);
        side += seg(m.x - wa, ya, m.x + wb, yb, "k3") + seg(m.x + wa, ya, m.x - wb, yb, "k3");
      }
      side += seg(m.x - m.h * 0.12, y0 + m.h * 0.75, m.x + m.h * 0.12, y0 + m.h * 0.75, "k3") + seg(m.x - m.h * 0.08, y0 + m.h * 0.9, m.x + m.h * 0.08, y0 + m.h * 0.9, "k3");
      side += circ(m.x, y1, Math.max(0.15, m.h * 0.012), "k2");
      if (m.array) side += D.arrayPanel(m.x - m.array / 2, y0 + m.h * 0.82, m.array, m.array * 0.3, 6, 2);
      if (m.dish) side += D.dish(m.x, y0 + m.h * 0.6, m.dish, 0);
      if (p.derricks && m.base === 0) side += seg(m.x, y0 + m.h * 0.1, m.x - m.h * 0.75, y0 + m.h * 0.35, "k2") + seg(m.x, y0 + m.h * 0.85, m.x - m.h * 0.75, y0 + m.h * 0.35, "k3");
    }
    for (const g of p.guns || []) {
      const gy = (g.base || 0) + fb;
      side += path(`M ${g.x - g.size} ${gy} L ${g.x - g.size * 0.8} ${gy + g.size * 0.7} L ${g.x + g.size} ${gy + g.size * 0.7} L ${g.x + g.size} ${gy} Z`)
        + seg(g.x - g.size * 0.6, gy + g.size * 0.35, g.x + g.size * 0.8, gy + g.size * 0.35, "k3")
        + rot(D.barrel(0, 0, { len: g.size * 2.6, d: g.size * 0.14 }), g.x - g.size * 0.8, gy + g.size * 0.35, g.aft ? 0 : 180 - 8);
    }
    for (const lc of p.launchers || []) {
      const ly = (lc.base || 0) + fb;
      if (lc.kind === "tubes") for (let i = 0; i < (lc.n || 4); i++) side += rot(D.canister(lc.len, lc.d, 3), lc.x, ly + i * lc.d * 1.05, lc.ang || 15);
      else if (lc.kind === "vls") side += rect(lc.x, ly, lc.len, 0.3, "k2") + D.eraRows(lc.x, lc.x + lc.len, ly, ly + 0.28, 6, 1);
      else side += rect(lc.x, ly, lc.len, lc.d, "k2") + rot(D.missile(lc.len * 0.9, lc.d * 0.4, 0.8), lc.x, ly + lc.d * 1.3, 25);
    }
    if (p.heloDeck) side += seg(L * 0.82, fb + 0.05, L * 0.99, fb + 0.05, "k2");

    // ---------------------------------------------------------------- plan
    const outline = (k) => `M 0 0 Q ${L * 0.2} ${-hb * 0.95 * k} ${L * 0.45} ${-hb * k} L ${L * 0.95} ${-hb * 0.92 * k} Q ${L} ${-hb * 0.8 * k} ${L} 0 Q ${L} ${hb * 0.8 * k} ${L * 0.95} ${hb * 0.92 * k} L ${L * 0.45} ${hb * k} Q ${L * 0.2} ${hb * 0.95 * k} 0 0 Z`;
    top += path(outline(1)) + `<path class="k3" d="${outline(0.9)}"/>` + seg(0, 0, L, 0, "kc");
    for (const sg of [-1, 1]) top += line([[L * 0.03, sg * hb * 0.18], [L * 0.08, sg * hb * 0.12]], "k3") + circ(L * 0.085, sg * hb * 0.12, hb * 0.07, "k2");   // chain to capstan
    for (const h of p.hatches || []) top += rect(h.x, -hb * 0.6, h.len, hb * 1.2, "k1") + range(h.x, h.x + h.len, 6).slice(1, -1).map((x) => seg(x, -hb * 0.6, x, hb * 0.6, "k3")).join("");
    for (const s of blocks) {
      top += rect(s.x, -s.w / 2, s.len, s.w, "k1") + rect(s.x + s.len * 0.08, -s.w * 0.4, s.len * 0.84, s.w * 0.8, "k3", false);
      if (s === bridge && s.w < B * 0.9) top += rect(s.x + s.len * 0.05, -hb * 0.95, s.len * 0.12, B * 0.95, "k2");   // bridge wings
    }
    for (const bx of p.boats || []) if (bridge) for (const sg of [-1, 1]) top += rect(bx, sg > 0 ? bridge.w / 2 : -bridge.w / 2 - 2.2, 7, 2.2, "k2");
    for (const fn of p.funnels || []) top += rect(fn.x, -fn.w * 0.4, fn.w, fn.w * 0.8, "k1") + rect(fn.x + fn.w * 0.2, -fn.w * 0.25, fn.w * 0.6, fn.w * 0.5, "k3", false);
    for (const m of p.masts || []) {
      top += circ(m.x, 0, Math.max(0.3, m.h * 0.04), "k2") + seg(m.x, -m.h * 0.12, m.x, m.h * 0.12, "k3");
      if (m.array) top += rect(m.x - 0.3, -m.array / 2, 0.6, m.array, "k1");
    }
    for (const g of p.guns || []) top += circ(g.x, 0, g.size * 0.8, "k1") + circ(g.x, 0, g.size * 0.5, "k3", false) + rot(D.barrel(0, 0, { len: g.size * 2.6, d: g.size * 0.14 }), g.x - g.size * 0.5, 0, g.aft ? 0 : 180);
    for (const lc of p.launchers || []) {
      const w = lc.w || 2;
      top += rect(lc.x, -w, lc.len, w * 2, "k2");
      top += lc.kind === "vls" ? D.eraRows(lc.x, lc.x + lc.len, -w, w, Math.max(2, Math.round(lc.len / 1.3)), Math.max(2, Math.round(w * 2 / 1.3))) : seg(lc.x, 0, lc.x + lc.len, 0, "k3");
    }
    if (p.heloDeck) top += circ(L * 0.9, 0, hb * 0.55, "k3", false) + seg(L * 0.88, -hb * 0.25, L * 0.88, hb * 0.25, "k3") + seg(L * 0.92, -hb * 0.25, L * 0.92, hb * 0.25, "k3") + seg(L * 0.88, 0, L * 0.92, 0, "k3");

    // ------------------------------------------------------------- bow-on
    front += path(`M ${-hb} ${fb * 1.1} L ${hb} ${fb * 1.1} Q ${hb * 0.9} ${0} ${hb * 0.3} ${-dr} L ${-hb * 0.3} ${-dr} Q ${-hb * 0.9} 0 ${-hb} ${fb * 1.1} Z`);
    front += seg(-hb * 1.1, 0, hb * 1.1, 0, "kc") + seg(-hb * 0.95, fb * 0.12, hb * 0.95, fb * 0.12, "k3");
    front += line([[-hb, fb * 1.1 + rail], [hb, fb * 1.1 + rail]], "k3");
    for (const sg of [-1, 1]) front += circ(sg * hb * 0.3, fb * 0.85, Math.max(0.2, B * 0.02), "k2", false);
    for (const m of p.masts || []) {
      const y0 = m.base + fb;
      front += line([[-m.h * 0.08, y0], [0, y0 + m.h], [m.h * 0.08, y0]], "k2") + seg(-m.h * 0.2, y0 + m.h * 0.75, m.h * 0.2, y0 + m.h * 0.75, "k3") + seg(-m.h * 0.14, y0 + m.h * 0.9, m.h * 0.14, y0 + m.h * 0.9, "k3");
      if (m.array) front += rect(-m.array / 2, y0 + m.h * 0.82, m.array, m.array * 0.3, "k1");
      if (m.dish) front += circ(0, y0 + m.h * 0.6, m.dish * 0.4, "k2");
    }
    for (const fn of p.funnels || []) front += rect(-fn.w * 0.4, fn.base + fb, fn.w * 0.8, fn.h, "k1") + rect(-fn.w * 0.45, fn.base + fb + fn.h, fn.w * 0.9, fn.h * 0.08, "k2");
    // nearest the bow is drawn last so it hides what is behind it
    for (const s of [...blocks].sort((a, b) => b.x - a.x)) {
      front += rect(-s.w / 2, fb, s.w, s.h, "k1");
      for (let d = 1; d * 2.7 < s.h - 0.8; d++) front += seg(-s.w / 2, fb + d * 2.7, s.w / 2, fb + d * 2.7, "k3");
      if (s === bridge) {
        const wy = fb + s.h - Math.min(1.6, s.h * 0.18);
        if (s.w < B * 0.9) front += rect(-hb * 0.95, wy - 0.4, B * 0.95, 0.4, "k2");                     // bridge wings
        for (const x of range(-s.w * 0.4, s.w * 0.4 - s.w * 0.07, 8)) front += rect(x, wy + 0.2, s.w * 0.07, Math.min(1.1, s.h * 0.12), "k3", false);
      }
    }
    for (const g of (p.guns || []).filter((g) => !g.aft)) {
      const gy = (g.base || 0) + fb;
      front += path(`M ${-g.size} ${gy} L ${-g.size * 0.8} ${gy + g.size * 0.7} L ${g.size * 0.8} ${gy + g.size * 0.7} L ${g.size} ${gy} Z`) + D.muzzle(0, gy + g.size * 0.35 + 0.2, g.size * 0.14);
    }
    const H = Math.max(...(p.masts || [{ base: 0, h: 10 }]).map((m) => m.base + m.h)) + fb;
    return { side, top, front, xmin: -0.5, xmax: L, W: B, H, ymin: -dr };
  }

  global.Draw3VFamilies = { armour, wheeled, truck, towedGun, ship, flipX };
})(window);
