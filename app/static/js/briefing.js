/* Page script for briefing.html. */
"use strict";
const STEM = document.body.dataset.stem;
const COLORS = { blue: "#4a90e2", red: "#e5675c", gold: "#e0a526", purple: "#8e44ad", green: "#27ae60" };
const FLIGHT_COLORS = ["#4a90e2", "#2ecc71", "#00b8d4", "#9b59b6", "#f39c12", "#1abc9c", "#3498db", "#e84393"];
let B = null, map = null, selected = "all", ROSTER = null;
const layers = {};

// ------------------------------------------------------------------ geometry
const R = 6371000, NM = 1852;
const rad = (d) => d * Math.PI / 180, deg = (r) => r * 180 / Math.PI;
function bearing(a, b) {
  const [la1, lo1, la2, lo2] = [rad(a[0]), rad(a[1]), rad(b[0]), rad(b[1])];
  const y = Math.sin(lo2 - lo1) * Math.cos(la2);
  const x = Math.cos(la1) * Math.sin(la2) - Math.sin(la1) * Math.cos(la2) * Math.cos(lo2 - lo1);
  return (deg(Math.atan2(y, x)) + 360) % 360;
}
function dist(a, b) {
  const dla = rad(b[0] - a[0]), dlo = rad(b[1] - a[1]);
  const h = Math.sin(dla / 2) ** 2 + Math.cos(rad(a[0])) * Math.cos(rad(b[0])) * Math.sin(dlo / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
function ddm(v, pos, neg) {
  const h = v >= 0 ? pos : neg, a = Math.abs(v), d = Math.floor(a);
  return `${h}${String(d).padStart(2, "0")}°${((a - d) * 60).toFixed(3).padStart(6, "0")}'`;
}
const fmtPos = (p) => `${ddm(p[0], "N", "S")} ${ddm(p[1], "E", "W")}`;
const bulls = (p) => `${String(Math.round(bearing(B.bullseye.pos, p)) % 360).padStart(3, "0")}/${Math.round(dist(B.bullseye.pos, p) / NM)}`;

// ----------------------------------------------------------------------- map
function dot(pos, color, label, r = 7) {
  return L.circleMarker(pos, { radius: r, color: "#fff", weight: 2, fillColor: color, fillOpacity: 1 })
    .bindTooltip(label);
}

function buildMap() {
  map = L.map("map", { zoomControl: false });
  L.control.zoom({ position: "bottomright" }).addTo(map);
  const base = {
    // OpenStreetMap's tile policy: no a/b/c subdomains, a referrer, and this attribution.
    "Map": L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      { maxZoom: 14, referrerPolicy: "strict-origin-when-cross-origin", attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors" }),
    "Terrain": L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", { maxZoom: 14, attribution: "© OpenTopoMap (CC-BY-SA)" }),
    "Satellite": L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 14, attribution: "Imagery © Esri" }),
  };
  base["Terrain"].addTo(map);
  for (const k of ["routes", "threats", "objectives", "support", "battlefield", "bases"]) layers[k] = L.layerGroup().addTo(map);
  L.control.layers(base, {
    "Flight routes": layers.routes, "Threat rings": layers.threats, "Objectives": layers.objectives,
    "Tankers & AWACS": layers.support, "Front line & JTAC": layers.battlefield, "Bases & bullseye": layers.bases,
  }, { position: "topright" }).addTo(map);
  map.on("click", (e) => {
    const p = [e.latlng.lat, e.latlng.lng];
    L.popup().setLatLng(e.latlng).setContent(
      `<div class="mono">${fmtPos(p)}<br>Bullseye ${bulls(p)}<br>From home ${Math.round(bearing(B.home.pos, p))}° / ${Math.round(dist(B.home.pos, p) / NM)} nm</div>`
    ).openOn(map);
  });
}

function drawStatic() {
  // Bases, bullseye, carrier
  dot(B.home.pos, COLORS.blue, `Home: ${B.home.name}`, 8).addTo(layers.bases);
  dot(B.enemy_base.pos, COLORS.red, `Enemy airfield: ${B.enemy_base.name}`, 7).addTo(layers.bases);
  if (B.carrier) dot(B.carrier.pos, COLORS.blue, B.carrier.name, 8).addTo(layers.bases);
  const bp = B.bullseye.pos;
  L.circleMarker(bp, { radius: 10, color: COLORS.purple, weight: 2, fill: false }).bindTooltip(`Bullseye ${B.bullseye.text}`).addTo(layers.bases);
  L.circleMarker(bp, { radius: 3, color: COLORS.purple, fillColor: COLORS.purple, fillOpacity: 1 }).addTo(layers.bases);
  // Objectives
  for (const o of B.objectives) {
    if (o.hidden) continue;
    L.marker(o.pos, { icon: L.divIcon({ className: "", html: `<div style="width:18px;height:18px;border:3px solid ${COLORS.gold};transform:rotate(45deg);background:rgba(224,165,38,.25)"></div>`, iconSize: [18, 18], iconAnchor: [9, 9] }) })
      .bindTooltip(`${o.name}: ${o.what}`).addTo(layers.objectives);
  }
  // Threats
  for (const t of B.threats) {
    const big = t.range_m > 6000;
    L.circle(t.pos, { radius: t.range_m, color: COLORS.red, weight: big ? 2 : 1, dashArray: big ? null : "4 4",
                      fillColor: COLORS.red, fillOpacity: big ? .08 : .04 })
      .bindTooltip(`${t.name}: ~${Math.round(t.range_m / NM)} nm ring`).addTo(layers.threats);
    dot(t.pos, COLORS.red, t.name, big ? 5 : 3).addTo(layers.threats);
  }
  // Support orbits
  for (const o of B.orbits) {
    L.polyline(o.line, { color: COLORS.blue, weight: 4, opacity: .7, dashArray: "8 6" })
      .bindTooltip(`${o.name} orbit, ${o.alt_ft.toLocaleString()} ft`).addTo(layers.support);
  }
  for (const a of B.ai_flights || []) {
    if (a.station) dot(a.station, COLORS.blue, `${a.name} (AI ${a.aircraft}) CAP`, 5).addTo(layers.support);
  }
  // Battlefield
  if (B.flot) {
    L.polyline(B.flot, { color: COLORS.red, weight: 5 }).bindTooltip("Front line (FLOT)").addTo(layers.battlefield);
  }
  if (B.friendly_armor) dot(B.friendly_armor, COLORS.blue, "Friendly armor", 6).addTo(layers.battlefield);
  if (B.jtac) dot(B.jtac.pos, COLORS.green, B.jtac.text, 6).addTo(layers.battlefield);
}

function drawRoutes() {
  layers.routes.clearLayers();
  B.flights.forEach((f, i) => {
    const on = selected === "all" || selected === i;
    const color = FLIGHT_COLORS[i % FLIGHT_COLORS.length];
    const pts = f.route.map(w => w.pos);
    const start = B.carrier && f.base === B.carrier.name ? B.carrier.pos : B.home.pos;
    L.polyline([start, ...pts], { color, weight: on ? 3.5 : 2, opacity: on ? .95 : .25 })
      .bindTooltip(f.name).addTo(layers.routes);
    if (!on) return;
    f.route.forEach((w, n) => {
      const m = L.circleMarker(w.pos, { radius: w.kind === "TGT" ? 6 : 4, color, weight: 2, fillColor: "#fff", fillOpacity: 1 })
        .bindTooltip(`${n + 1} ${w.name}`, { permanent: selected !== "all", direction: "right", className: "wp-label", offset: [6, 0] })
        .addTo(layers.routes);
      m.on("click", () => openFlight(i));
    });
  });
}

function fit() {
  const pts = [B.home.pos, B.enemy_base.pos, ...B.objectives.filter(o => !o.hidden).map(o => o.pos)];
  if (B.carrier) pts.push(B.carrier.pos);
  B.flights.forEach(f => f.route.forEach(w => pts.push(w.pos)));
  map.fitBounds(L.latLngBounds(pts).pad(0.12));
}

function mapbar() {
  const btns = [["all", "All flights"], ...B.flights.map((f, i) => [i, f.name])];
  $("mapbar").innerHTML = btns.map(([k, v]) => `<button type="button" data-k="${k}" class="${selected === k ? "on" : ""}">${esc(v)}</button>`).join("")
    + `<button type="button" data-fit="1">Fit</button>`;
  $("mapbar").querySelectorAll("button").forEach(b => b.onclick = () => {
    if (b.dataset.fit) return fit();
    selected = b.dataset.k === "all" ? "all" : +b.dataset.k;
    mapbar(); drawRoutes();
    if (selected !== "all") map.fitBounds(L.latLngBounds(B.flights[selected].route.map(w => w.pos)).pad(0.2));
  });
}

// --------------------------------------------------------------------- panels
const TABS = [["overview", "Overview"], ["mine", "My flight"], ["flights", "Flights"], ["threats", "Threat ID"],
              ["comms", "Comms"], ["weather", "Weather & field"], ["kneeboards", "Kneeboards"],
              ["debrief", "Debrief"]];
function fitMine() {
  // A map created in a hidden tab has no size yet; fit it once it's visible.
  setTimeout(() => { if (myMap && myBounds) { myMap.invalidateSize(); myMap.fitBounds(myBounds); } }, 60);
}
function tab(name) {
  if (name === "mine") fitMine();
  if (name === "debrief") loadDebrief();
  document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("on", b.dataset.t === name));
  document.querySelectorAll(".panel").forEach(p => p.classList.toggle("on", p.dataset.tab === name));
  try { history.replaceState(null, "", "#" + name); } catch (e) {}
}
function openFlight(i) {
  tab("flights");
  document.getElementById(`flight_${i}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

const list = (items) => items.length ? `<ul class="plain">${items.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : `<p class="muted">None.</p>`;

function renderPanels() {
  const m = B.meta;
  $("p_overview").innerHTML = `
    <h2>Who's flying</h2><div class="card" id="roster"></div>
    <h2>Tasking</h2>${B.tasking.map(t => `<div class="card">${esc(t)}</div>`).join("")}
    <h2>Situation</h2><div class="card">${esc(m.era)}. ${esc(m.you)} vs ${esc(m.enemy)}. You fly from ${esc(B.home.name)}; the
      enemy is concentrated around ${esc(B.enemy_base.name)}.${B.situation.length ? list(B.situation) : ""}</div>
    <h2>Objectives</h2><div class="card"><table><tr><th>Objective</th><th>Position</th><th>Bulls</th></tr>
      ${B.objectives.map(o => o.hidden ? `<tr><td>${esc(o.name)}</td><td colspan="2" class="muted">Passed by radio when the previous target is destroyed</td></tr>`
        : `<tr><td>${esc(o.name)}<br><span class="muted">${esc(o.what)}</span></td><td class="mono">${fmtPos(o.pos)}</td><td class="mono">${bulls(o.pos)}</td></tr>`).join("")}
    </table></div>
    <h2>Package</h2><div class="card"><table><tr><th>Flight</th><th>Aircraft</th><th>Job</th></tr>
      ${B.flights.map((f, i) => `<tr><td><a href="#" onclick="openFlight(${i});return false">${esc(f.name)}</a>${f.squadron ? `<br><span class="muted">${esc(f.squadron)}</span>` : ""}</td>
        <td>${f.seats}${f.ai ? ` + ${f.ai} AI` : ""} × ${esc(f.aircraft)}</td><td>${esc(m.mission)}${f.timing ? `<br><span class="muted">${esc(f.timing)}</span>` : ""}</td></tr>`).join("")}
      ${(B.ai_flights || []).map(a => `<tr><td>${esc(a.name)} <span class="muted">(AI)</span></td><td>${a.count} × ${esc(a.aircraft)}</td><td>${esc(a.job)}<br><span class="muted">${esc(a.where)}</span></td></tr>`).join("")}
    </table></div>
    ${B.notes.length ? `<h2>Notes</h2><div class="card warn">${list(B.notes)}</div>` : ""}
    ${B.report ? `<h2>Server check</h2><div class="card">${B.report.errors.length
      ? `<span class="badge bad">${B.report.errors.length} script error(s)</span>${list(B.report.errors)}`
      : `<span class="badge ok">Loaded clean on the server</span>`}</div>` : ""}`;

  $("p_flights").innerHTML = `<div class="flightpick">${B.flights.map((f, i) =>
      `<button type="button" onclick="openFlight(${i})">${esc(f.name)}</button>`).join("")}</div>`
    + B.flights.map((f, i) => `
    <div class="card" id="flight_${i}">
      <h3>${esc(f.name)} <small>${esc(f.aircraft)}${f.squadron ? " · " + esc(f.squadron) : ""}</small></h3>
      <p class="muted" style="margin:0 0 8px">${f.seats} player seat(s)${f.ai ? ` + ${f.ai} AI` : ""} · ${esc(f.base)} · ${esc(f.start)} start
        <span class="flight-pilots" data-flight="${esc(f.name)}"></span>${f.timing ? `<br><b>${esc(f.timing)}</b>` : ""}</p>
      <table><tr><th>#</th><th>Waypoint</th><th>Alt</th><th>Bulls</th><th>Position</th></tr>
        ${f.route.map((w, n) => `<tr class="${w.kind === "TGT" ? "tgt" : ""}"><td>${n + 1}</td><td>${esc(w.name)}</td>
          <td class="mono">${w.alt_ft ? w.alt_ft.toLocaleString() + (w.agl ? " AGL" : "") : "-"}</td>
          <td class="mono">${esc(w.bulls)}</td><td class="mono">${fmtPos(w.pos)}</td></tr>`).join("")}
      </table>
      <h2>Loadout</h2><p style="margin:0">${esc(f.loadout)}</p>
      ${f.presets.length ? `<h2>Radio presets</h2>${f.presets.map(p => `<div class="mono">${esc(p)}</div>`).join("")}` : ""}
      <p style="margin:10px 0 0"><a href="#" onclick="selected=${i};mapbar();drawRoutes();map.fitBounds(L.latLngBounds(B.flights[${i}].route.map(w=>w.pos)).pad(.2));return false">Show on map</a></p>
    </div>`).join("");

  $("p_comms").innerHTML = `
    ${B.srs ? `<h2>Voice (SRS)</h2><div class="card">SRS server <b class="mono">${esc(B.srs.address)}</b>${B.srs.note
      ? ` <span class="muted">· ${esc(B.srs.note)}</span>` : ""}<br><span class="muted">Connect the SRS client, then
      tune the frequencies below. Your cockpit radios set your SRS frequency.</span></div>` : ""}
    <p><a class="btn" href="/missions/${encodeURIComponent(STEM)}/comms.txt" target="_blank">Comm card (text)</a>
      <span class="muted">every frequency on one page, for a second screen or your phone.</span></p>
    <h2>Support &amp; agencies</h2>${B.support.length ? B.support.map(s => `<div class="card">${esc(s)}</div>`).join("") : `<p class="muted">No support aircraft in this era.</p>`}
    <h2>Flight frequencies</h2><div class="card"><table><tr><th>Flight</th><th>Presets</th></tr>
      ${B.flights.map(f => `<tr><td>${esc(f.name)}</td><td class="mono">${f.presets.map(esc).join("<br>") || "<span class='muted'>No preset radios</span>"}</td></tr>`).join("")}
    </table></div>
    <p class="muted">Guard is 243.000 UHF / 121.500 VHF.</p>`;

  const oob = B.oob || [];
  $("p_threats").innerHTML = `<p class="muted" style="margin-top:0">Recognition cards for the enemy systems in this
    mission. Drawings are real 3-view drawings where one exists, otherwise true-scale line drawings
    generated from published dimensions; figures are approximate.</p>
    ${oob.length ? `<div class="tcards">${oob.map(threatCard).join("")}</div>` : `<p class="muted">No enemy forces.</p>`}`
    + (B.threats.length ? `
    <h2>Known threat positions</h2><div class="card"><table><tr><th>Threat</th><th>Ring</th><th>Bulls</th><th>Position</th></tr>
      ${B.threats.map(t => `<tr><td>${esc(t.name)}</td><td class="mono">${Math.round(t.range_m / NM)} nm</td><td class="mono">${esc(t.bulls)}</td><td class="mono">${esc(t.text)}</td></tr>`).join("")}
    </table></div><p class="muted">Pop-up threats aren't shown: they're not on any intel map.</p>` : "");

  $("p_weather").innerHTML = `
    <h2>Time</h2><div class="card">${esc(m.date)}, mission starts ${esc(m.start)} local${m.tot ? `<br><b>TOT ${esc(m.tot)}</b>` : ""}</div>
    <h2>Weather</h2><div class="card">${esc(cap(m.weather))}, wind ${esc(m.wind)}${m.wind_from != null ? ` from ${String(m.wind_from).padStart(3, "0")}°` : ""}, ${m.temp_c} °C</div>
    <h2>Home field</h2><div class="card">${esc(B.home.card)}</div>
    <h2>Bullseye</h2><div class="card mono">${esc(B.bullseye.text)}</div>`;

  $("p_kneeboards").innerHTML = `<p class="muted" style="margin-top:0">These pages are in the cockpit kneeboard too. Click one to open it full size.</p>
    <div class="kb">${B.flights.flatMap(f => (f.kneeboards || [{ page: f.kneeboard, label: "Flight" }]).map(k => {
      const src = `/missions/${encodeURIComponent(STEM)}/kneeboard/${encodeURIComponent(k.page)}.png`;
      return `<div><a href="${src}" target="_blank"><img loading="lazy" src="${src}" alt="${esc(k.label)} kneeboard for ${esc(f.name)}"></a>
      <p>${esc(f.name)} · ${esc(k.label)}</p></div>`;
    })).join("")}</div>`;
}
// ------------------------------------------------------------------- debrief
const EVENT_ICON = { kill: "✕", crash: "▼", eject: "⇡", pilot_death: "✝", takeoff: "↗", landing: "↘",
                     friendly_fire: "!", mission_end: "■" };
async function loadDebrief() {
  let d = null;
  try { d = (await (await fetch(`/api/missions/${encodeURIComponent(STEM)}/debrief`)).json()).debrief; } catch (e) {}
  $("p_debrief").innerHTML = d ? debriefHtml(d) : `<p class="muted" style="margin-top:0">No debrief yet.</p>
    <div class="card">The debrief fills in by itself when this mission is flown on a DCS server running the
    <a href="/dcs-hook.lua">DCS Mission Maker hook</a>: kills, losses, ejections, take-offs and landings, and which
    objectives were destroyed. Put the file in <span class="mono">Saved Games\DCS.server\Scripts\Hooks\</span>
    (or <span class="mono">Saved Games\DCS\Scripts\Hooks\</span> if you host from your own PC) and restart DCS.
    It reports every minute while the mission runs and once more when it ends.</div>`;
}
function debriefHtml(d) {
  const status = d.final ? `<span class="badge ok">Mission over</span>` : `<span class="badge">In progress</span>`;
  const objs = d.objectives.map(o => `<tr><td>${esc(o.name)}</td><td>${esc(o.what)}</td><td>${
    o.done === null ? `<span class="muted">not reported</span>` : o.done ? `<span class="badge ok">Destroyed</span>`
      : `<span class="badge bad">Still standing</span>`}</td></tr>`).join("");
  const pilots = d.pilots.map(p => `<tr><td>${esc(p.name)}</td><td>${p.kills}</td>
    <td>${esc(p.victims.slice(0, 6).join(", "))}${p.victims.length > 6 ? "…" : ""}</td>
    <td>${p.losses.length ? `<span class="warn">${esc(p.losses.join(", "))}</span>` : "-"}</td>
    <td>${esc(p.landings.join(", ") || "-")}${p.friendly_fire ? ` <span class="badge bad">${p.friendly_fire} friendly fire</span>` : ""}</td></tr>`).join("");
  return `<p class="muted" style="margin-top:0">${status} ${d.flown_minutes} min flown${d.all_done === true
      ? ` · <b>all objectives destroyed</b>` : ""}. Reported by the DCS server; refreshes while this tab is open.</p>
    ${d.objectives.length ? `<h2>Objectives</h2><div class="card"><table><tr><th>Objective</th><th>What</th><th>Result</th></tr>${objs}</table></div>` : ""}
    <h2>Pilots</h2><div class="card">${d.pilots.length ? `<table><tr><th>Pilot</th><th>Kills</th><th>Destroyed</th><th>Losses</th><th>Landed</th></tr>${pilots}</table>`
      : `<span class="muted">No player events yet.</span>`}</div>
    <h2>Timeline</h2><div class="card">${d.timeline.length ? `<table>${d.timeline.map(e => `<tr><td class="mono">${esc(e.time)}</td>
      <td>${EVENT_ICON[e.type] || ""}</td><td>${esc(e.text)}</td></tr>`).join("")}</table>` : `<span class="muted">Nothing yet.</span>`}</div>`;
}

function threatCard(e) {
  const stats = [["Range", e.range], ["Altitude", e.alt], ["Guidance", e.guidance], ["Speed", e.speed],
                 ["Weapons", e.arms], ["RWR", e.rwr]].filter(([, v]) => v);
  const i = CARD_REG.push(e) - 1;
  return `<div class="tcard">
    <button type="button" class="bpbtn" onclick="openSheet(${i})" title="Open the full blueprint">${Blueprint.sheet(e)}</button>
    <div class="tbody">
      <h3>${esc(e.title)} <small>${e.possible ? "possible" : `×${e.count}${e.sites && e.sites.length ? ` · ${e.sites.length} site${e.sites.length > 1 ? "s" : ""}` : ""}`}</small></h3>
      <p class="muted" style="margin:0 0 6px">${esc(e.nato && e.nato !== e.title ? e.nato + " · " : "")}${esc(e.role)}</p>
      ${stats.length ? `<dl class="stats">${stats.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}</dl>` : ""}
      <p class="beat"><b>How to beat it:</b> ${esc(e.notes)}</p>
      ${e.drawing ? `<p class="credit">Drawing: <a href="${esc(e.drawing.page)}" target="_blank" rel="noopener">${esc(e.drawing.artist || "Wikimedia Commons")}</a>, ${esc(e.drawing.license)}${e.drawing.shows ? ` (shows a ${esc(e.drawing.shows)})` : ""}</p>` : ""}
    </div></div>`;
}
const CARD_REG = [];
function openSheet(i) {
  const e = CARD_REG[i];
  $("sheet_body").innerHTML = Blueprint.sheet(e);
  $("sheet_title").textContent = e.title;
  $("sheet").showModal();
}

// ------------------------------------------------------------------ my flight
let myMap = null, myBounds = null;
function mySeat() {
  const me = myName.trim().toLowerCase();
  if (!me || !ROSTER) return null;
  return ROSTER.seats.find(st => !st.ai && st.pilot && st.pilot.toLowerCase() === me) || null;
}
function legTable(f) {
  const start = B.carrier && f.base === B.carrier.name ? B.carrier.pos : B.home.pos;
  let prev = start, total = 0;
  return `<table><tr><th>#</th><th>Waypoint</th><th>Hdg</th><th>Dist</th><th>Alt</th><th>Bulls</th></tr>${f.route.map((w, n) => {
    const hdg = String(Math.round(bearing(prev, w.pos)) % 360).padStart(3, "0"), d = dist(prev, w.pos) / NM;
    total += d; prev = w.pos;
    return `<tr class="${w.kind === "TGT" ? "tgt" : ""}"><td>${n + 1}</td><td>${esc(w.name)}</td><td class="mono">${hdg}°</td>
      <td class="mono">${d.toFixed(0)} nm</td><td class="mono">${w.alt_ft ? w.alt_ft.toLocaleString() + (w.agl ? " AGL" : "") : "-"}</td>
      <td class="mono">${esc(w.bulls)}</td></tr>`;
  }).join("")}<tr><td></td><td class="muted">Total</td><td></td><td class="mono">${total.toFixed(0)} nm</td><td></td><td></td></tr></table>`;
}
function nearRoute(pos, f, km) {
  return f.route.some(w => dist(w.pos, pos) < km * 1000);
}
function renderMine() {
  const box = $("p_mine");
  const seat = mySeat();
  if (myMap) { myMap.remove(); myMap = null; }
  if (!seat) {
    box.innerHTML = `<div class="card"><h3>Claim a seat to get your flight</h3>
      <p class="muted" style="margin:0">Type your name and take a seat under <a href="#" onclick="tab('overview');return false">Overview → Who's flying</a>.
      This tab then shows your own route map, legs, threats along your route, radios and kneeboard.</p></div>`;
    return;
  }
  const fi = B.flights.findIndex(f => f.name === seat.flight), f = B.flights[fi];
  const mates = ROSTER.seats.filter(st => st.flight === seat.flight && st.seat !== seat.seat)
    .map(st => `${st.seat.split(" ").pop()} ${st.ai ? "AI" : st.pilot || "open"}`);
  const nearThreats = B.threats.filter(t => nearRoute(t.pos, f, t.range_m / 1000 + 25));
  const cards = (B.oob || []).filter(e => e.possible || e.category === "fighter" || (e.sites || []).some(p => nearRoute(p, f, 60)));
  box.innerHTML = `
    <div class="you"><h3>${esc(seat.seat)} · ${esc(f.aircraft)}</h3>
      <div class="muted">${esc(f.squadron || "")}${f.squadron ? " · " : ""}${esc(f.base)}, ${esc(f.start)} start${mates.length ? ` · with ${esc(mates.join(", "))}` : ""}</div>
      ${f.timing ? `<div style="margin-top:4px"><b>${esc(f.timing)}</b></div>` : ""}</div>
    <div id="mymap"></div>
    <h2>Your legs</h2><div class="card">${legTable(f)}</div>
    <h2>Loadout</h2><div class="card">${esc(f.loadout)}</div>
    ${f.presets.length ? `<h2>Your radios</h2><div class="card mono">${f.presets.map(esc).join("<br>")}</div>` : ""}
    <h2>Threats on your route</h2>
    ${cards.length ? `<div class="tcards">${cards.map(threatCard).join("")}</div>` : `<p class="muted">Nothing known near your route.</p>`}
    <h2>Your kneeboard</h2><div class="kb" style="grid-template-columns:minmax(0,360px)"><a href="/missions/${encodeURIComponent(STEM)}/kneeboard/${f.kneeboard}.png" target="_blank">
      <img src="/missions/${encodeURIComponent(STEM)}/kneeboard/${f.kneeboard}.png" alt="Your kneeboard"></a></div>`;
  if (!window.L) return;
  myMap = L.map("mymap", { zoomControl: false, attributionControl: true });
  L.control.zoom({ position: "bottomright" }).addTo(myMap);
  L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", { maxZoom: 14, attribution: "© OpenTopoMap (CC-BY-SA)" }).addTo(myMap);
  const start = B.carrier && f.base === B.carrier.name ? B.carrier.pos : B.home.pos;
  for (const t of nearThreats) {
    L.circle(t.pos, { radius: t.range_m, color: COLORS.red, weight: 1.5, fillColor: COLORS.red, fillOpacity: .07 })
      .bindTooltip(`${t.name} ~${Math.round(t.range_m / NM)} nm`).addTo(myMap);
  }
  for (const o of B.objectives) if (!o.hidden) dot(o.pos, COLORS.gold, `${o.name}: ${o.what}`, 6).addTo(myMap);
  dot(B.bullseye.pos, COLORS.purple, "Bullseye", 5).addTo(myMap);
  dot(start, COLORS.blue, f.base, 7).addTo(myMap);
  L.polyline([start, ...f.route.map(w => w.pos)], { color: COLORS.gold, weight: 4 }).addTo(myMap);
  f.route.forEach((w, n) => L.circleMarker(w.pos, { radius: w.kind === "TGT" ? 6 : 4, color: COLORS.gold, weight: 2, fillColor: "#fff", fillOpacity: 1 })
    .bindTooltip(`${n + 1} ${w.name}`, { permanent: true, direction: "right", className: "wp-label", offset: [6, 0] }).addTo(myMap));
  myBounds = L.latLngBounds([start, ...f.route.map(w => w.pos)]).pad(0.15);
  fitMine();
  // Highlight it on the big map too, once.
  if (selected === "all" && map && !renderMine.done) { renderMine.done = true; selected = fi; mapbar(); drawRoutes(); }
}

// -------------------------------------------------------------------- roster
let myName = "";
try { myName = localStorage.getItem("dcs-mm:name") || ""; } catch (e) {}

function renderRoster() {
  const box = $("roster");
  if (!box || !ROSTER) return;
  const byFlight = {};
  for (const st of ROSTER.seats) (byFlight[st.flight] = byFlight[st.flight] || []).push(st);
  const focused = document.activeElement && document.activeElement.id === "rname";
  if (!focused) {
    box.innerHTML = `<label for="rname" class="muted" style="font-size:12.5px">Your name, as you want it on your slot</label>
      <input class="name" id="rname" maxlength="24" placeholder="e.g. Mitsu" value="${esc(myName)}">
      <div id="rseats"></div>
      <p class="muted" id="rerr" style="margin:6px 0 0"></p>
      <p class="muted" style="margin:6px 0 0;font-size:12.5px">Taking a seat also puts your name on that slot in the .miz.
        Re-download (or re-publish) the mission after everyone has picked.</p>`;
    $("rname").oninput = () => { myName = $("rname").value; try { localStorage.setItem("dcs-mm:name", myName); } catch (e) {} drawSeats(); refreshMine(); };
  }
  drawSeats();
  function drawSeats() {
    const me = myName.trim().toLowerCase();
    $("rseats").innerHTML = Object.entries(byFlight).map(([flight, seats]) => `
      <div class="roster-flight"><h4>${esc(flight)} <small>${esc(seats[0].aircraft)}</small></h4>
      ${seats.map(st => {
        if (st.ai) return `<div class="seat"><span>${esc(st.seat)}</span><span class="who">AI wingman</span><span></span></div>`;
        const mine = st.pilot && st.pilot.toLowerCase() === me;
        return `<div class="seat ${mine ? "mine" : ""}"><span>${esc(st.seat)}</span>
          <span class="who ${st.pilot ? "taken" : ""}">${st.pilot ? esc(st.pilot) : "open"}</span>
          ${mine ? `<button type="button" data-seat="${esc(st.seat)}" data-act="leave">Leave</button>`
                 : `<button type="button" data-seat="${esc(st.seat)}" data-act="take" ${st.pilot || !me ? "disabled" : ""}
                     title="${!me ? "Type your name first" : ""}">Take seat</button>`}</div>`;
      }).join("")}</div>`).join("");
    $("rseats").querySelectorAll("button").forEach(b => b.onclick = () => claim(b.dataset.seat, b.dataset.act));
  }
  // Pilot names on the flight cards too.
  document.querySelectorAll(".flight-pilots").forEach(el => {
    const names = ROSTER.seats.filter(st => st.flight === el.dataset.flight && st.pilot).map(st => `${st.seat.split(" ").pop()} ${st.pilot}`);
    el.innerHTML = names.length ? `<br>Pilots: ${esc(names.join(", "))}` : "";
  });
}

let lastMine = null;  // null so the first roster load always renders the tab
async function loadRoster() {
  const res = await fetch(`/api/missions/${encodeURIComponent(STEM)}/roster`);
  if (res.ok) { ROSTER = await res.json(); renderRoster(); refreshMine(); }
}
function refreshMine() {
  const s = mySeat(), key = s ? s.seat : "";
  if (key !== lastMine) { lastMine = key; renderMine(); }
}

async function claim(seat, act) {
  const res = await fetch(`/api/missions/${encodeURIComponent(STEM)}/roster`, { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seat, name: act === "take" ? myName.trim() : "", me: myName.trim() }) });
  const data = await res.json();
  if (!res.ok) { await loadRoster(); $("rerr").textContent = data.error; $("rerr").className = "warn"; return; }
  ROSTER = data; renderRoster(); refreshMine();
}

const cap = (s) => String(s).charAt(0).toUpperCase() + String(s).slice(1);

(async function init() {
  const res = await fetch(`/api/missions/${encodeURIComponent(STEM)}/brief`);
  if (!res.ok) { $("title").textContent = "Briefing not found"; return; }
  B = await res.json();
  document.title = `${B.title} · Briefing Room`;
  $("title").textContent = B.title;
  $("download").href = B.download;
  const m = B.meta;
  $("chips").innerHTML = [m.map, m.mission, m.era, `${m.difficulty} difficulty`, `${m.date} ${m.start}`,
    `${cap(m.weather)}, wind ${m.wind}`].map(c => `<span class="chip">${esc(c)}</span>`).join("")
    + (m.tot ? `<span class="chip tot">TOT ${esc(m.tot)}</span>` : "");
  $("tabs").innerHTML = TABS.map(([k, v]) => `<button type="button" data-t="${k}">${v}</button>`).join("");
  $("tabs").querySelectorAll("button").forEach(b => b.onclick = () => tab(b.dataset.t));
  $("pack").href = `/missions/${encodeURIComponent(STEM)}/pack.pdf`;
  $("copy").onclick = async () => {
    try { await navigator.clipboard.writeText(location.href.split("#")[0]); $("copy").textContent = "Copied!"; }
    catch (e) { prompt("Copy this link:", location.href.split("#")[0]); }
    setTimeout(() => $("copy").textContent = "Copy link", 1500);
  };
  renderPanels();
  await loadRoster();
  setInterval(loadRoster, 15000);
  // the hook reports every minute while the mission runs
  setInterval(() => { if ($("p_debrief").classList.contains("on")) loadDebrief(); }, 30000);
  const want = location.hash.slice(1);
  tab(TABS.some(t => t[0] === want) ? want : "overview");
  if (window.L) { buildMap(); drawStatic(); drawRoutes(); mapbar(); fit(); }
  else $("mapwrap").innerHTML = `<p class="muted" style="padding:16px">The map needs internet access to load.</p>`;
})();
