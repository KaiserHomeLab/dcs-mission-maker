/* Blueprint drawing sheets for the Briefing Room's Threat ID cards.
 *
 * Each card becomes a 640x360 "engineering drawing": two orthographic views
 * (side + plan for aircraft and ships, side + front for vehicles and guns),
 * dimension lines from real (aircraft) or approximate (ground/naval) sizes,
 * numbered callouts, an engagement-envelope diagram and a title block.
 * Units with a real drawing (Wikimedia Commons) or a generated 3-view
 * (draw3v*.js) use those instead; the stylized family drawings here are the
 * last resort for anything else.
 *
 * Usage: Blueprint.sheet(entry) -> SVG string. Styles: static/css/blueprint.css.
 */
(function (global) {
  "use strict";
  let uid = 0;
  const r1 = (n) => Math.round(n * 10) / 10;
  const P = (a) => a.map(([x, y]) => `${r1(x)},${r1(y)}`).join(" ");
  const poly = (a, c = "o") => `<polygon class="${c}" points="${P(a)}"/>`;
  const pl = (a, c = "d") => `<polyline class="${c}" points="${P(a)}"/>`;
  const ln = (x1, y1, x2, y2, c = "d") => `<line class="${c}" x1="${r1(x1)}" y1="${r1(y1)}" x2="${r1(x2)}" y2="${r1(y2)}"/>`;
  const ci = (x, y, r, c = "o") => `<circle class="${c}" cx="${r1(x)}" cy="${r1(y)}" r="${r1(r)}"/>`;
  const el = (x, y, rx, ry, c = "o") => `<ellipse class="${c}" cx="${r1(x)}" cy="${r1(y)}" rx="${r1(rx)}" ry="${r1(ry)}"/>`;
  const rc = (x, y, w, h, c = "o", rx = 0) => `<rect class="${c}" x="${r1(x)}" y="${r1(y)}" width="${r1(w)}" height="${r1(h)}" rx="${rx}"/>`;
  const pa = (d, c = "o") => `<path class="${c}" d="${d}"/>`;
  const g = (inner, tf = "") => `<g${tf ? ` transform="${tf}"` : ""}>${inner}</g>`;
  const mir = (a, cy) => a.map(([x, y]) => [x, 2 * cy - y]);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const T = (x, y, s, size = 8, anchor = "start", cls = "t") =>
    `<text class="${cls}" x="${r1(x)}" y="${r1(y)}" font-size="${size}" text-anchor="${anchor}">${esc(s)}</text>`;

  // A missile drawn along +x from (0,0), then placed/rotated.
  function missile(x, y, len, dia, deg = 0, finScale = 1) {
    const h = dia / 2, n = len * 0.14, f = dia * 1.4 * finScale;
    const body = `${poly([[n, -h], [len - 2, -h], [len, -h * 0.7], [len, h * 0.7], [len - 2, h], [n, h]])}`
      + pa(`M ${n} ${-h} Q ${n * 0.25} ${-h * 0.7} 0 0 Q ${n * 0.25} ${h * 0.7} ${n} ${h}`)
      + poly([[len - len * 0.12, -h], [len - 2, -h - f], [len, -h - f], [len, -h]])
      + poly([[len - len * 0.12, h], [len - 2, h + f], [len, h + f], [len, h]])
      + poly([[len * 0.42, -h], [len * 0.5, -h - f * 0.6], [len * 0.58, -h - f * 0.6], [len * 0.6, -h]], "d")
      + ln(n, 0, len - 3, 0, "c");
    return g(body, `translate(${r1(x)} ${r1(y)}) rotate(${-deg})`);
  }

  // ------------------------------------------------------------- dimensions
  function dimH(x1, x2, y, yObj, label) {
    const a = 4;
    return ln(x1, yObj, x1, y + 4, "x") + ln(x2, yObj, x2, y + 4, "x") + ln(x1, y, x2, y, "x")
      + pa(`M ${x1} ${y} l ${a * 1.6} ${-a / 2} l 0 ${a} z M ${x2} ${y} l ${-a * 1.6} ${-a / 2} l 0 ${a} z`, "ar")
      + `<rect class="tb" x="${r1((x1 + x2) / 2 - label.length * 2.6 - 4)}" y="${r1(y - 6)}" width="${r1(label.length * 5.2 + 8)}" height="11"/>`
      + T((x1 + x2) / 2, y + 3, label, 8, "middle", "dt");
  }
  function dimV(y1, y2, x, xObj, label) {
    const a = 4;
    return ln(xObj, y1, x + 4, y1, "x") + ln(xObj, y2, x + 4, y2, "x") + ln(x, y1, x, y2, "x")
      + pa(`M ${x} ${y1} l ${-a / 2} ${a * 1.6} l ${a} 0 z M ${x} ${y2} l ${-a / 2} ${-a * 1.6} l ${a} 0 z`, "ar")
      + g(`<rect class="tb" x="${r1(-label.length * 2.6 - 4)}" y="-6" width="${r1(label.length * 5.2 + 8)}" height="11"/>`
        + T(0, 3, label, 8, "middle", "dt"), `translate(${r1(x)} ${r1((y1 + y2) / 2)}) rotate(-90)`);
  }
  const m = (v, approx) => `${approx ? "≈ " : ""}${(+v).toFixed(v >= 100 ? 0 : 2)} m`;

  // --------------------------------------------------------------- aircraft
  const AIR = {
    flanker: { r: 58, h: 11, cs: 92, cl: 58, ch: 13, tails: 2, finX: 286, intake: "ventral", lerx: 1, irst: 1, stinger: 1, nz: 2, wing: "trap", ws: 168, wc: 120 },
    eagle:   { r: 50, h: 12, cs: 80, cl: 62, ch: 14, tails: 2, finX: 292, intake: "side", lerx: 0, nz: 2, wing: "trap", ws: 170, wc: 122 },
    hornet:  { r: 52, h: 11, cs: 78, cl: 60, ch: 13, tails: 2, finX: 270, intake: "side", lerx: 1, nz: 2, wing: "trap", ws: 176, wc: 104, cant: 1 },
    viper:   { r: 50, h: 11, cs: 66, cl: 66, ch: 15, tails: 1, finX: 288, intake: "chin", lerx: 1, nz: 1, wing: "trap", ws: 190, wc: 96 },
    light:   { r: 60, h: 9, cs: 96, cl: 52, ch: 12, tails: 1, finX: 282, intake: "side", lerx: 1, nz: 2, wing: "trap", ws: 182, wc: 92 },
    phantom: { r: 52, h: 13, cs: 84, cl: 80, ch: 13, tails: 1, finX: 282, intake: "side", lerx: 0, nz: 2, wing: "swept", ws: 168, wc: 112, anhedral: 1 },
    delta:   { r: 30, h: 10, cs: 110, cl: 48, ch: 11, tails: 1, finX: 270, intake: "nose", lerx: 0, nz: 1, wing: "delta", ws: 160, wc: 160 },
    swing:   { r: 56, h: 11, cs: 92, cl: 54, ch: 12, tails: 1, finX: 280, intake: "side", lerx: 0, nz: 1, wing: "swing", ws: 176, wc: 100 },
    tomcat:  { r: 56, h: 12, cs: 80, cl: 62, ch: 14, tails: 2, finX: 290, intake: "side", lerx: 0, nz: 2, wing: "swing", ws: 160, wc: 110 },
    early_jet: { r: 26, h: 15, cs: 104, cl: 46, ch: 12, tails: 1, finX: 268, intake: "nose", lerx: 0, nz: 1, wing: "swept", ws: 150, wc: 110, high: 1 },
  };

  function jet(e, style) {
    let o = AIR[style] || AIR.viper;
    const d = e.dims || { length: 17, span: 11, height: 4.8 };
    const x0 = 24, x1 = 372, L = x1 - x0, cy = 98;
    const u = L / d.length;                      // drawing units per metre
    // Fuselage depth around 12-14% of length, like the real aircraft.
    const h = o.h * 1.55, cs = x0 + o.cs, ce = cs + o.cl;
    o = { ...o, ch: o.ch * 1.25 };
    const fh = Math.min(70, Math.max(30, d.height * u - 2 * h - 6));
    let s = "";
    // Fuselage side profile
    const top = [...(o.intake === "nose" ? [[x0, cy - h * 0.75]] : [[x0, cy], [x0 + o.r * 0.45, cy - h * 0.55]]),
      [x0 + o.r, cy - h * 0.85], [cs, cy - h], [x1 - 70, cy - h - 1], [x1 - 10, cy - h * 0.72], [x1, cy - h * 0.55]];
    const bot = [[x1, cy + h * 0.55], [x1 - 10, cy + h * 0.8], [x1 - 90, cy + h], [cs + 10, cy + h],
      [x0 + o.r, cy + h * 0.8], ...(o.intake === "nose" ? [[x0, cy + h * 0.75]] : [[x0 + o.r * 0.45, cy + h * 0.55]])];
    s += poly([...top, ...bot]);
    // canopy
    s += pa(`M ${cs} ${cy - h} Q ${cs + o.cl * 0.3} ${cy - h - o.ch * 1.15} ${cs + o.cl * 0.55} ${cy - h - o.ch} T ${ce} ${cy - h - 1} Z`, "g");
    s += ln(cs + o.cl * 0.28, cy - h - o.ch * 0.92, cs + o.cl * 0.2, cy - h, "d") + ln(cs + o.cl * 0.7, cy - h - o.ch * 0.85, cs + o.cl * 0.72, cy - h, "d");
    s += ln(x0 + o.r, cy - h * 0.85, x0 + o.r, cy + h * 0.8, "d");                       // radome joint
    for (const px of [ce + 22, x1 - 120, x1 - 64]) s += ln(px, cy - h, px, cy + h, "d");     // panel lines
    s += ln(ce, cy - h * 0.35, x1 - 20, cy - h * 0.35, "d");
    s += ln(x0 - 6, cy, x1 + 18, cy, "c");                                                    // centreline
    if (o.intake !== "nose") s += ln(x0 - 12, cy, x0, cy, "d");                               // pitot
    else s += poly([[x0 - 13, cy], [x0, cy - h * 0.45], [x0, cy + h * 0.45]]) + el(x0, cy, 2.5, h * 0.75, "d");
    // intake
    if (o.intake === "side") s += poly([[cs + o.cl * 0.6, cy - h * 0.5], [cs + o.cl + 30, cy - h * 0.5], [cs + o.cl + 40, cy + h * 0.75], [cs + o.cl * 0.45, cy + h * 0.75]], "o2")
      + ln(cs + o.cl * 0.6, cy - h * 0.5, cs + o.cl * 0.45, cy + h * 0.75, "d");
    if (o.intake === "chin") s += poly([[cs + 6, cy + h - 1], [cs + 4, cy + h + 11], [cs + 58, cy + h + 9], [cs + 92, cy + h]], "o2");
    if (o.intake === "ventral") s += poly([[cs + 50, cy + h - 1], [cs + 48, cy + h + 13], [x1 - 40, cy + h + 11], [x1 - 14, cy + h * 0.8]], "o2")
      + ln(cs + 70, cy + h + 3, x1 - 50, cy + h + 3, "d");
    // wing (seen edge-on) and LERX
    s += poly([[x0 + o.ws, cy + 2], [x0 + o.ws + o.wc, cy], [x0 + o.ws + o.wc + 8, cy + 3], [x0 + o.ws + 10, cy + 5]], "o2");
    if (o.lerx) s += pl([[x0 + o.r + 20, cy + 1], [x0 + o.ws + 4, cy + 2]], "d");
    // fins
    const fin = (dx, cls) => poly([[o.finX + dx, cy - h - 1], [o.finX + 34 + dx, cy - h - fh], [o.finX + 58 + dx, cy - h - fh],
      [x1 - 6 + dx, cy - h * 0.75]], cls);
    if (o.tails === 2) s += fin(10, "h");
    s += fin(0, "o") + ln(o.finX + 44, cy - h - fh + 4, x1 - 14, cy - h * 0.9, "d");
    // stabilator
    const sy = o.high ? cy - h - fh * 0.55 : cy + (o.anhedral ? 6 : 1);
    s += poly([[x1 - 58, sy], [x1 + 6, sy + (o.anhedral ? 6 : -2)], [x1 + 10, sy + (o.anhedral ? 9 : 2)], [x1 - 52, sy + 4]], "o2");
    // nozzle(s)
    s += rc(x1 - 2, cy - h * 0.55, 10, h * 1.1, "o2") + ln(x1 + 3, cy - h * 0.55, x1 + 3, cy + h * 0.55, "d");
    if (o.stinger) s += poly([[x1 + 8, cy - 2], [x1 + 26, cy], [x1 + 8, cy + 2]], "o2");
    if (o.irst) s += pa(`M ${cs - 12} ${cy - h} a 4 4 0 0 1 8 0`, "o2");
    // stores
    const my = cy + 14;
    s += missile(x0 + o.ws + 10, my, 46, 3.2) + missile(x0 + o.ws + o.wc * 0.55, my + 2, 34, 2.6);
    // gear (retracted) doors as hidden lines
    s += ln(x0 + o.ws + 20, cy + h, x0 + o.ws + 60, cy + h, "h");

    // plan view
    const pcy = 57;
    const halfSpan = Math.min(52, (d.span || 10) * u / 2), w = h * 0.95;
    const wingLE = x0 + o.ws, wingTE = wingLE + o.wc;
    let p = ln(x0 - 6, pcy, x1 + 22, pcy, "c");
    const fus = [[x0, pcy], [x0 + o.r * 0.5, pcy - w * 0.5], [x0 + o.r, pcy - w * 0.75], [cs + 10, pcy - w],
      [cs + o.cl + 10, pcy - w * (o.intake === "side" || o.intake === "ventral" ? 1.45 : 1.05)], [x1 - 40, pcy - w * 1.2], [x1, pcy - w * 0.85]];
    const fusAll = [...fus, ...mir(fus.slice(1).reverse(), pcy)];
    // wings
    let wing;
    if (o.wing === "delta") wing = [[wingLE - 10, pcy - w], [wingTE + 4, pcy - halfSpan], [wingTE + 14, pcy - halfSpan], [wingTE + 16, pcy - w]];
    else if (o.wing === "swing") wing = [[wingLE, pcy - w * 1.2], [wingLE + 72, pcy - halfSpan], [wingLE + 92, pcy - halfSpan], [wingLE + 86, pcy - w * 1.2]];
    else if (o.wing === "swept") wing = [[wingLE, pcy - w], [wingLE + 92, pcy - halfSpan], [wingLE + 114, pcy - halfSpan], [wingTE + 8, pcy - w]];
    else wing = [[wingLE, pcy - w * 1.1], [wingLE + 86, pcy - halfSpan], [wingLE + 104, pcy - halfSpan], [wingTE, pcy - w * 1.1]];
    p += poly(wing, "o2") + poly(mir(wing, pcy), "o2");
    if (o.wing === "swing") {
      const sw = [[wingLE, pcy - w * 1.2], [wingLE + 130, pcy - halfSpan * 0.55], [wingLE + 146, pcy - halfSpan * 0.55], [wingLE + 96, pcy - w * 1.2]];
      p += poly(sw, "h") + poly(mir(sw, pcy), "h");
    }
    if (o.lerx) { const lx = [[x0 + o.r + 18, pcy - w * 0.8], [wingLE, pcy - w * 1.15 - 6], [wingLE + 6, pcy - w * 1.1]]; p += pl(lx) + pl(mir(lx, pcy)); }
    // stabs
    const st = [[x1 - 54, pcy - w * 1.1], [x1 - 6, pcy - w * 1.1 - halfSpan * 0.42], [x1 + 8, pcy - w * 1.1 - halfSpan * 0.42], [x1 + 10, pcy - w]];
    p += poly(st, "o2") + poly(mir(st, pcy), "o2");
    p += poly(fusAll, "o");
    p += pa(`M ${cs} ${pcy - w * 0.6} Q ${cs + o.cl / 2} ${pcy - w * 1.05} ${ce} ${pcy - w * 0.6} L ${ce} ${pcy + w * 0.6} Q ${cs + o.cl / 2} ${pcy + w * 1.05} ${cs} ${pcy + w * 0.6} Z`, "g");
    if (o.tails === 2) for (const dy of [-1, 1]) p += rc(o.finX + 20, pcy + dy * w * 0.95 - 1.5, x1 - o.finX - 20, 3, "o2");
    else p += rc(o.finX + 20, pcy - 1.5, x1 - o.finX - 22, 3, "o2");
    for (let i = 0; i < o.nz; i++) p += rc(x1, pcy - (o.nz === 2 ? (i ? -w * 0.35 - 4 : w * 0.35) : 3), 8, o.nz === 2 ? 4 : 6, "o2");
    // dims
    const dims = dimH(x0, x1 + (o.stinger ? 26 : 10), 170, cy + h + 16, m(d.length, d.approx))
      + dimV(cy - h - fh, cy + h + (o.intake === "ventral" ? 13 : 2), 392, x1 + 10, m(d.height, d.approx));
    const pdims = d.span ? dimV(pcy - halfSpan, pcy + halfSpan, wingLE + 132, wingLE + 104, m(d.span, d.approx)) : "";
    const callouts = [
      [x0 + 18, cy, "Radar / nose"], [cs + o.cl * 0.5, cy - h - o.ch * 0.8, "Cockpit"],
      [o.intake === "nose" ? x0 + 4 : cs + o.cl + 10, cy + h * 0.6, "Engine intake"],
      [x0 + o.ws + 30, my, "Air-to-air missiles"], [x1 + 4, cy, `Engine nozzle${o.nz > 1 ? "s" : ""}`],
    ];
    if (o.irst) callouts.push([cs - 8, cy - h - 3, "IRST sensor"]);
    return { side: s + dims, plan: p + pdims, planLabel: "PLAN VIEW", callouts };
  }

  function prop(e) {
    const d = e.dims || { length: 9.5, span: 11, height: 3.9 };
    const x0 = 40, x1 = 360, cy = 92, h = 13;
    let s = ln(x0 - 20, cy, x1 + 10, cy, "c");
    s += poly([[x0, cy - h * 0.8], [x0 + 60, cy - h], [x0 + 110, cy - h - 2], [x0 + 170, cy - h + 2], [x1 - 20, cy - 5], [x1, cy - 3],
      [x1, cy + 3], [x1 - 40, cy + 6], [x0 + 150, cy + h], [x0 + 60, cy + h + 2], [x0, cy + h * 0.8]]);
    s += pa(`M ${x0} ${cy - 8} Q ${x0 - 16} ${cy} ${x0} ${cy + 8} Z`, "o2");                               // spinner
    s += ln(x0 - 6, cy - 58, x0 - 6, cy + 58, "h") + el(x0 - 6, cy - 32, 3, 24, "o2") + el(x0 - 6, cy + 32, 3, 24, "o2");
    s += ln(x0 + 50, cy - h, x0 + 50, cy + h + 2, "d") + ln(x0 + 6, cy - h * 0.6, x0 + 6, cy + h * 0.6, "d");  // cowl
    for (const px of [x0 + 18, x0 + 32]) s += ln(px, cy + 6, px, cy + 10, "d");                             // exhausts
    s += pa(`M ${x0 + 108} ${cy - h - 2} Q ${x0 + 128} ${cy - h - 22} ${x0 + 158} ${cy - h - 6} L ${x0 + 168} ${cy - h + 1} Z`, "g");
    s += ln(x0 + 120, cy - h - 12, x0 + 117, cy - h - 2, "d");
    s += pa(`M ${x1 - 46} ${cy - 5} Q ${x1 - 34} ${cy - 46} ${x1 - 8} ${cy - 44} Q ${x1 + 2} ${cy - 30} ${x1} ${cy - 4} Z`);  // fin
    s += ln(x1 - 14, cy - 40, x1 - 10, cy - 5, "d");
    s += poly([[x1 - 50, cy + 1], [x1 + 4, cy - 1], [x1 + 6, cy + 3], [x1 - 46, cy + 4]], "o2");
    s += poly([[x0 + 70, cy + 7], [x0 + 150, cy + 6], [x0 + 154, cy + 10], [x0 + 74, cy + 11]], "o2");     // wing edge
    // gear down
    for (const gx of [x0 + 84, x0 + 92]) s += ln(gx, cy + 10, gx - 4, cy + 46, "o2");
    s += ci(x0 + 86, cy + 50, 9, "o2") + ci(x0 + 86, cy + 50, 3, "d") + ln(x1 - 30, cy + 5, x1 - 26, cy + 18, "o2") + ci(x1 - 26, cy + 21, 4, "o2");
    s += ln(x0 + 100, cy - 2, x0 + 128, cy - 2, "x") ;
    // plan
    const pcy = 57, u = (x1 - x0) / d.length, hs = Math.min(52, d.span * u / 2);
    let p = ln(x0 - 20, pcy, x1 + 10, pcy, "c");
    const wing = `M ${x0 + 70} ${pcy - 8} C ${x0 + 80} ${pcy - hs} ${x0 + 120} ${pcy - hs - 2} ${x0 + 138} ${pcy - hs + 6} C ${x0 + 150} ${pcy - hs * 0.6} ${x0 + 152} ${pcy - 14} ${x0 + 150} ${pcy - 8} Z`;
    p += pa(wing, "o2") + g(pa(wing, "o2"), `translate(0 ${2 * pcy}) scale(1 -1)`);
    p += pa(`M ${x1 - 44} ${pcy - 4} Q ${x1 - 34} ${pcy - 26} ${x1 - 8} ${pcy - 22} L ${x1 - 4} ${pcy - 3} Z`, "o2")
      + g(pa(`M ${x1 - 44} ${pcy - 4} Q ${x1 - 34} ${pcy - 26} ${x1 - 8} ${pcy - 22} L ${x1 - 4} ${pcy - 3} Z`, "o2"), `translate(0 ${2 * pcy}) scale(1 -1)`);
    p += poly([[x0, pcy - 9], [x0 + 70, pcy - 11], [x0 + 160, pcy - 9], [x1, pcy - 3], [x1, pcy + 3], [x0 + 160, pcy + 9], [x0 + 70, pcy + 11], [x0, pcy + 9]]);
    p += ln(x0 - 6, pcy - 46, x0 - 6, pcy + 46, "h") + pa(`M ${x0} ${pcy - 6} Q ${x0 - 14} ${pcy} ${x0} ${pcy + 6} Z`, "o2");
    p += el(x0 + 132, pcy, 22, 6, "g");
    for (const dy of [-1, 1]) p += ln(x0 + 95, pcy + dy * hs * 0.65, x0 + 100, pcy + dy * hs * 0.65, "d");     // guns
    const dims = dimH(x0 - 6, x1 + 6, 168, cy + 60, m(d.length, d.approx)) + dimV(cy - 46, cy + 59, 392, x1 + 6, m(d.height, d.approx));
    const pdims = dimV(pcy - hs, pcy + hs, x0 + 190, x0 + 140, m(d.span, d.approx));
    return {
      side: s + dims, plan: p + pdims, planLabel: "PLAN VIEW",
      callouts: [[x0 - 6, cy - 40, "Propeller"], [x0 + 30, cy, "Engine"], [x0 + 130, cy - h - 10, "Cockpit"],
                 [x0 + 100, cy + 8, "Wing guns"], [x1 - 22, cy - 26, "Tail"]],
    };
  }

  // ------------------------------------------------------------- envelope
  const num = (s) => { const mm = String(s || "").replace(/,/g, "").match(/(\d+(\.\d+)?)/); return mm ? parseFloat(mm[1]) : null; };
  function envelope(e) {
    const X = 448, Y = 40, W = 168, H = 118;
    let s = rc(X - 8, Y - 18, W + 16, H + 44, "fr") + T(X - 2, Y - 6, e.category === "fighter" ? "WEAPON RANGE" : "ENGAGEMENT ENVELOPE", 8, "start", "th");
    const shipSam = (e.arms || "").match(/~\s*(\d+)\s*km/);
    const R = num(e.range) || (shipSam ? +shipSam[1] : null), A = num(e.alt);
    if (e.category === "ewr" && R) {
      const cx = X + 20, cyy = Y + H - 4, rr = Math.min(W - 30, H - 20);
      s = rc(X - 8, Y - 18, W + 16, H + 44, "fr") + T(X - 2, Y - 6, "DETECTION COVERAGE", 8, "start", "th");
      for (const f of [0.33, 0.66, 1]) s += pa(`M ${cx} ${cyy} L ${cx + rr * f} ${cyy} A ${rr * f} ${rr * f} 0 0 0 ${cx} ${cyy - rr * f}`, f === 1 ? "en" : "h");
      s += ci(cx, cyy, 3, "dot") + T(cx + rr, cyy + 10, `≈ ${R} km`, 7, "end", "dt") + T(X + W, Y + 10, "SENSOR ONLY · CUES SAMs & FIGHTERS", 6.5, "end", "dt");
      return s;
    }
    if (e.category === "fighter") {
      const max = R ? (R > 60 ? 120 : R > 25 ? 60 : 25) : 25;
      s += ln(X, Y + 60, X + W, Y + 60, "x");
      for (let i = 0; i <= 4; i++) s += ln(X + i * W / 4, Y + 56, X + i * W / 4, Y + 64, "x") + T(X + i * W / 4, Y + 76, `${max * i / 4}`, 7, "middle", "dt");
      s += T(X + W, Y + 88, "km", 7, "end", "dt");
      if (R) s += rc(X, Y + 40, Math.min(W, R / max * W), 12, "en") + T(X + 4, Y + 49, `≈ ${R} km  ${e.range.replace(/^[^(]*/, "")}`, 7.5, "start", "dt");
      else s += T(X, Y + 30, "GUNS / SHORT-RANGE IR ONLY", 7.5, "start", "dt");
      if (e.speed) s += T(X, Y + 106, `MAX SPEED ${e.speed.toUpperCase()}`, 7.5, "start", "dt");
      return s;
    }
    if (!R) return s + T(X + W / 2, Y + H / 2, e.category === "ewr" ? "NO WEAPONS — SENSOR ONLY" : "NO AIR-DEFENSE WEAPONS", 7.5, "middle", "dt");
    const Rkm = R, Akm = A ? A / 1000 : Rkm * 0.4;
    const gx = X + 10, gy = Y + H - 8, gw = W - 18, gh = H - 22;
    const scaleR = gw / (Rkm * 1.15), scaleA = gh / (Akm * 1.2);
    s += ln(gx, gy, gx + gw, gy, "x") + ln(gx, gy, gx, gy - gh, "x");
    let dpath = `M ${gx} ${gy}`;
    for (let t = 0; t <= 90; t += 6) {
      const a = t * Math.PI / 180;
      dpath += ` L ${r1(gx + Rkm * Math.cos(a) * scaleR)} ${r1(gy - Akm * Math.sin(a) * scaleA)}`;
    }
    s += pa(dpath + " Z", "en");
    s += T(gx + Rkm * scaleR, gy + 10, `${Rkm} km`, 7, "middle", "dt") + T(gx - 3, gy - Akm * scaleA + 3, `${(Akm * 1000).toLocaleString()} m`, 7, "end", "dt");
    s += T(gx + gw, gy - gh + 6, "ALT", 7, "end", "dt") + T(gx + gw, gy - 3, "RANGE", 7, "end", "dt");
    // a reference jet at 20,000 ft
    const jy = gy - 6.1 * scaleA;
    if (jy > gy - gh) s += ln(gx, jy, gx + gw, jy, "h") + T(gx + gw - 2, jy - 2, "FL200", 6.5, "end", "dt");
    return s;
  }

  // ------------------------------------------------------------------ sheet
  // Generated two-view drawing for aircraft without a real drawing; null if not an aircraft.
  function aircraftViews(e) {
    const st = e.style || e.art;
    if (AIR[st]) return jet(e, st);
    if (st === "jet" || st === "twin") return jet(e, st === "twin" ? "eagle" : "viper");
    if (st === "prop") return prop(e);
    return null;
  }

  // A real 3-view drawing (black ink on white or transparent) recoloured to white
  // lines on the blueprint: composite over white, then alpha = darkness.
  function realDrawing(e, id) {
    const d = e.dims;
    // Small raster drawings get a touch of blur so enlarged pixels don't look jagged.
    const soften = e.drawing.lowres ? `<feGaussianBlur in="c0" stdDeviation="0.45" result="c"/>` : "";
    let s = `<filter id="${id}ink" x="0" y="0" width="1" height="1" color-interpolation-filters="sRGB">
        <feFlood flood-color="#fff" result="w"/><feComposite in="SourceGraphic" in2="w" operator="over" result="${soften ? "c0" : "c"}"/>${soften}
        <feColorMatrix in="c" type="matrix" values="0 0 0 0 0.94  0 0 0 0 0.97  0 0 0 0 1  -0.30 -1.0 -0.10 0 1.35"/></filter>`;
    s += `<image href="${esc(e.drawing.url)}" x="18" y="34" width="406" height="292" preserveAspectRatio="xMidYMid meet" filter="url(#${id}ink)"/>`;
    if (d) {
      const parts = [["LENGTH", d.length], ["SPAN", d.span], ["HEIGHT", d.height]].filter(([, v]) => v)
        .map(([k, v]) => `${k} ${m(v, d.approx)}`);
      s += rc(18, 330, 406, 14, "tb") + T(221, 340, parts.join("   ·   "), 8, "middle", "dt");
    }
    return s;
  }

  function sheet(e) {
    const id = `bp${++uid}`;
    if (e.drawing) return drawingSheet(e, id);
    const gen = e.category !== "fighter" && global.Draw3V ? global.Draw3V.render(e) : null;
    if (gen) return generatedSheet(e, id, gen);
    const v = aircraftViews(e);
    return v ? aircraftSheet(e, id, v) : frame(e, id) + titleBlock(e, "DMM BRIEFING ROOM") + "</svg>";
  }

  // Side elevation over plan view, with numbered callouts keyed on the right.
  function aircraftSheet(e, id, v) {
    let s = frame(e, id);
    s += `<clipPath id="${id}cs"><rect x="12" y="32" width="418" height="181"/></clipPath>`
      + `<clipPath id="${id}cp"><rect x="12" y="215" width="418" height="133"/></clipPath>`;
    s += `<g clip-path="url(#${id}cs)">${g(v.side, "translate(18 12)")}</g>`;
    s += ln(16, 214, 432, 214, "x") + T(22, 226, "SIDE ELEVATION", 7.5, "start", "th") + T(22, 342, v.planLabel, 7.5, "start", "th");
    s += `<g clip-path="url(#${id}cp)">${g(v.plan, "translate(18 228)")}</g>`;
    const cos = (v.callouts || []).slice(0, 6);
    const lx = 448, ly = 190;
    s += T(lx - 2, ly - 6, "KEY", 8, "start", "th");
    // balloons spread along the top in left-to-right order of the parts they point at
    const order = cos.map((c, i) => i).sort((a, b) => cos[a][0] - cos[b][0]);
    const step = cos.length > 1 ? 360 / (cos.length - 1) : 0;
    cos.forEach(([cx, cy, label], i) => {
      const n = i + 1, px = cx + 18, py = cy + 12, k = order.indexOf(i);
      const bx = Math.min(414, cos.length === 1 ? px : 46 + k * step), by = 44 + (k % 2) * 14;
      s += ln(px, py, bx, by + 6, "ldr") + ci(px, py, 1.8, "dot") + ci(bx, by, 7, "bal") + T(bx, by + 3, n, 8, "middle", "bn");
      s += ci(lx + 5, ly + 8 + i * 13, 5.5, "bal") + T(lx + 5, ly + 10.5 + i * 13, n, 7, "middle", "bn") + T(lx + 15, ly + 11 + i * 13, label, 7.5, "start", "dt");
    });
    return s + titleBlock(e, "DMM BRIEFING ROOM") + "</svg>";
  }

  function frame(e, id) {
    let s = `<svg viewBox="0 0 640 360" class="bp" role="img" aria-label="${esc(e.title)} blueprint">
      <defs>
        <pattern id="${id}m" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M8 0 L0 0 0 8" class="gm"/></pattern>
        <pattern id="${id}M" width="40" height="40" patternUnits="userSpaceOnUse"><rect width="40" height="40" fill="url(#${id}m)"/><path d="M40 0 L0 0 0 40" class="gM"/></pattern>
        <radialGradient id="${id}v" cx="50%" cy="45%" r="75%"><stop offset="0" stop-color="#174a7c"/><stop offset="1" stop-color="#0a2b4f"/></radialGradient>
      </defs>
      <rect width="640" height="360" fill="url(#${id}v)"/><rect width="640" height="360" fill="url(#${id}M)"/>
      <rect class="fr2" x="6" y="6" width="628" height="348"/><rect class="fr" x="10" y="10" width="620" height="340"/>`;
    for (let i = 1; i < 8; i++) s += ln(10 + i * 77.5, 10, 10 + i * 77.5, 14, "x") + ln(10 + i * 77.5, 346, 10 + i * 77.5, 350, "x");
    s += T(20, 25, (e.title || "").toUpperCase(), 10, "start", "th");
    s += g(rc(-64, -9, 128, 15, "stamp") + T(0, 2.5, "RESTRICTED · MISSION USE", 7, "middle", "st"), "translate(352 21)");
    return s + ln(432, 10, 432, 350, "x") + envelope(e);
  }

  function titleBlock(e, source) {
    const drg = `DMM-${(e.key || "X").replace(/[^A-Za-z0-9]/g, "").slice(0, 8).toUpperCase()}-01`;
    const tx = 440, ty = 274, tw = 184;
    let s = rc(tx, ty, tw, 72, "fr") + ln(tx, ty + 18, tx + tw, ty + 18, "x") + ln(tx, ty + 36, tx + tw, ty + 36, "x")
      + ln(tx, ty + 54, tx + tw, ty + 54, "x") + ln(tx + 92, ty + 36, tx + 92, ty + 72, "x");
    s += T(tx + 4, ty + 7, "TITLE", 5.5, "start", "tk") + T(tx + 4, ty + 15, (e.title || "").toUpperCase().slice(0, 34), 7.5, "start", "dt");
    s += T(tx + 4, ty + 25, "DESIGNATION / ROLE", 5.5, "start", "tk") + T(tx + 4, ty + 33, `${e.nato && e.nato !== e.title ? e.nato + " · " : ""}${e.role || ""}`.toUpperCase().slice(0, 40), 6.5, "start", "dt");
    s += T(tx + 4, ty + 43, "DRG NO", 5.5, "start", "tk") + T(tx + 4, ty + 51, drg, 7, "start", "dt");
    s += T(tx + 96, ty + 43, "SCALE", 5.5, "start", "tk") + T(tx + 96, ty + 51, "NTS", 7, "start", "dt");
    s += T(tx + 4, ty + 61, "SHEET", 5.5, "start", "tk") + T(tx + 4, ty + 69, "1 OF 1", 7, "start", "dt");
    s += T(tx + 96, ty + 61, "SOURCE", 5.5, "start", "tk") + T(tx + 96, ty + 69, source, 6.5, "start", "dt");
    return s;
  }

  function drawingSheet(e, id) {
    const dr = e.drawing;
    let s = frame(e, id) + realDrawing(e, id);
    // credits (the drawing's licence requires attribution)
    s += T(446, 196, "DRAWING", 8, "start", "th");
    const credit = [`${dr.artist || "Unknown author"}`, `${dr.license}`, "via Wikimedia Commons", "Link: credit under the card"];
    credit.forEach((c, i) => { s += T(448, 210 + i * 12, c.slice(0, 36), 7, "start", "dt"); });
    s += T(448, 262, dr.shows ? `Drawing shows a ${dr.shows}.` : "Recoloured to blueprint style.", 6.5, "start", "tk");
    s += titleBlock(e, "WIKIMEDIA COMMONS");
    return s + "</svg>";
  }

  // A generated true-scale 3-view (draw3v*.js) in the same layout as a real drawing.
  function generatedSheet(e, id, gen) {
    const v = gen.views, z = gen.size;
    let s = frame(e, id) + gen.body;
    s += T(v.side.x1, v.side.top - 5, "SIDE", 6.5, "start", "tk") + T(v.front.x1, v.front.top - 5, "FRONT", 6.5, "start", "tk")
      + T(v.top.x1, v.top.top - 5, "PLAN", 6.5, "start", "tk");
    s += dimH(v.top.x1, v.top.x2, v.top.bottom + 13, v.top.bottom + 2, m(z.length, true));
    s += dimV(v.front.top, v.side.ground, v.front.x2 + 15, v.front.x2 + 2, m(z.height, true));
    s += dimH(v.front.x1, v.front.x2, v.side.ground + 14, v.side.ground + 2, m(z.width, true));
    s += T(446, 196, "DRAWING", 8, "start", "th");
    const notes = ["Generated line drawing,", "true scale from published", "dimensions. Detail is", "representative."];
    notes.forEach((c, i) => { s += T(448, 210 + i * 12, c, 7, "start", "dt"); });
    s += T(448, 262, gen.shows ? `Drawing shows the ${gen.shows}.` : "All views to one scale.", 6.5, "start", "tk");
    s += titleBlock(e, "DMM BRIEFING ROOM");
    return s + "</svg>";
  }

  global.Blueprint = { sheet };
})(window);
