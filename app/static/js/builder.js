/* Page script for index.html. */
"use strict";
let OPT = null;
const AC = {};
const STORE = "dcs-mission-maker:v2";
const MISSION_HINTS = {
  cap: "Hold a CAP and kill waves of enemy fighters",
  cas: "Destroy an armored column under air defense cover",
  sead: "Take down an air defense site",
  strike: "Destroy a defended supply depot",
  antiship: "Sink an enemy naval group",
  csar: "Rescue a downed pilot before the enemy finds them (needs a helicopter)",
  free: "No threats: practice, sightseeing",
};
const ERA_SHORT = { ww2: "WWII", korea: "Korea", vietnam: "Vietnam", coldwar: "Cold War", modern: "Modern" };

function seg(container, name, values, checked) {
  container.innerHTML = values.map(v =>
    `<label><input type="radio" name="${name}" value="${v}" ${v === checked ? "checked" : ""}>${v}</label>`).join("");
}
const radio = (name) => document.querySelector(`input[name=${name}]:checked`)?.value;
const setRadio = (name, v) => { const el = document.querySelector(`input[name=${name}][value="${v}"]`); if (el) el.checked = true; };
function fillSelect(sel, items, value) {
  sel.innerHTML = items.map(i => Array.isArray(i)
    ? `<option value="${esc(i[0])}">${esc(i[1])}</option>` : `<option>${esc(i)}</option>`).join("");
  if (value != null && [...sel.options].some(o => o.value === value)) sel.value = value;
}
const theater = () => OPT.theaters.find(t => t.key === $("theater").value);
const flights = () => [...document.querySelectorAll(".flight")];

function clearRoutes() { flights().forEach(d => d.dataset.route = ""); }

function onTheater(e) {
  if (e) clearRoutes();  // only on a real user change, not when restoring
  const t = theater();
  fillSelect($("blue_base"), t.blue_bases, t.default_blue);
  fillSelect($("red_base"), t.red_bases, t.default_red);
  $("theater_note").textContent = t.notes;
  const anti = document.querySelector("input[name=mission_type][value=antiship]");
  anti.disabled = !t.has_sea;
  if (anti.checked && !t.has_sea) { setRadio("mission_type", "cas"); onMissionType(); }
  flights().forEach(refreshFlight);
  refresh();
}

function onMissionType(e) {
  if (e) clearRoutes();
  const mt = radio("mission_type");
  $("enemy_air_box").classList.toggle("hidden", mt === "cap" || mt === "free");
  $("secondaries_box").classList.toggle("hidden", mt === "cap" || mt === "free");
  $("chain_box").classList.toggle("hidden", mt === "cap" || mt === "free");
  $("front_line_box").classList.toggle("hidden", mt !== "cas");
  flights().forEach(loadLoadouts);
  refresh();
}

function aircraftOptions() {
  const groups = {};
  for (const a of OPT.aircraft) {
    const key = a.mod ? "Mods" : a.helicopter ? "Helicopters" : (a.era ? `${ERA_SHORT[a.era]} era` : "Trainers & aerobatic");
    (groups[key] = groups[key] || []).push(a);
  }
  const order = ["Modern", "Cold War", "Vietnam", "Korea", "WWII"].map(e => `${e} era`)
    .concat(["Trainers & aerobatic", "Helicopters", "Mods"]);
  return order.filter(k => groups[k]).map(k =>
    `<optgroup label="${k}">${groups[k].map(a => `<option value="${esc(a.id)}">${esc(a.name)}</option>`).join("")}</optgroup>`).join("");
}

function nextFreeNumber(callsign, self) {
  const used = flights().filter(d => d !== self && d.querySelector(".callsign").value === callsign)
    .map(d => +d.querySelector(".number").value);
  for (let n = 1; n <= 9; n++) if (!used.includes(n)) return n;
  return 1;
}

function addFlight(f = {}) {
  if (flights().length >= 8) return;
  const div = document.createElement("div");
  div.className = "flight";
  div.innerHTML = `
    <div class="flight-head"><strong class="title"></strong>
      <div class="tags"><span class="tag era-tag"></span><span class="tag dtc hidden" title="Data Transfer Cartridge">DTC</span>
      <button type="button" class="link remove" title="Remove this flight">Remove</button></div></div>
    <div class="fgrid">
      <div class="ac"><label>Aircraft</label><select class="aircraft">${aircraftOptions()}</select></div>
      <div><label>Callsign</label><select class="callsign"></select></div>
      <div><label>Flight #</label><select class="number">${[1,2,3,4,5,6,7,8,9].map(n => `<option>${n}</option>`).join("")}</select></div>
      <div><label>Players</label><input type="number" class="slots" min="1" max="4" value="${f.slots || 2}"></div>
      <div><label>AI wingmen</label><select class="ai_wingmen"></select></div>
    </div>
    <div class="fgrid2">
      <div><label>Starts from</label><select class="base"><option value="airfield">Airfield</option><option value="carrier">Carrier</option></select></div>
      <div><label>Start</label><select class="start">
        <option value="cold">Cold &amp; dark</option><option value="hot">Hot on ramp</option>
        <option value="runway">On runway</option><option value="air">In the air</option></select></div>
      <div class="lo"><label>Loadout</label><select class="loadout"></select></div>
    </div>
    <p class="weapons"></p>
    <div class="row">
      <div style="flex:1;min-width:180px"><label>Livery</label><select class="livery"><option value="">DCS default</option></select></div>
      <div style="flex:1;min-width:180px"><label>Squadron (optional)</label><input type="text" class="squadron" maxlength="40" placeholder="e.g. VFA-103 Jolly Rogers"></div>
      <label class="switch dtc-box hidden" title="Loads the route, radio channel names, threat rings and tanker orbits into the jet at spawn">
        <input type="checkbox" class="dtc-on" checked> Data cartridge</label>
    </div>`;
  const q = (s) => div.querySelector(s);
  q(".aircraft").value = f.aircraft && AC[f.aircraft] ? f.aircraft : "F-16C_50";
  q(".base").value = f.base || "airfield";
  q(".start").value = f.start || "cold";
  q(".squadron").value = f.squadron || "";
  q(".dtc-on").checked = f.dtc !== false;
  div.dataset.loadout = f.loadout || "";
  div.dataset.livery = f.livery || "";
  $("flights").appendChild(div);
  div.dataset.route = f.route ? JSON.stringify(f.route) : "";
  q(".aircraft").onchange = () => {
    const mod = AC[q(".aircraft").value].mod;
    if (mod) { const box = document.querySelector(`input[name=mod][value="${mod}"]`); if (box) box.checked = true; }
    div.dataset.loadout = ""; div.dataset.livery = "";
    setCallsigns(div); refreshFlight(div); loadLoadouts(div); loadLiveries(div); refresh(); };
  q(".callsign").onchange = () => { q(".number").value = nextFreeNumber(q(".callsign").value, div); refreshEscorts(); refresh(); };
  for (const s of [".number", ".base", ".start", ".dtc-on", ".ai_wingmen"]) q(s).onchange = refresh;
  div.dataset.ai = f.ai_wingmen || 0;
  q(".slots").oninput = () => { refreshFlight(div); refresh(); };
  q(".squadron").oninput = refresh;
  q(".loadout").onchange = () => { div.dataset.loadout = q(".loadout").value; showWeapons(div); refresh(); };
  q(".livery").onchange = () => {
    div.dataset.livery = q(".livery").value;
    // a squadron livery fills in the squadron name if you haven't typed one
    const pick = (div._liveries || []).find(l => l.id === q(".livery").value);
    if (pick && pick.squadron && !q(".squadron").value.trim()) q(".squadron").value = pick.squadron;
    refresh();
  };
  q(".remove").onclick = () => { div.remove(); if (!flights().length) addFlight(); refreshEscorts(); refresh(); };
  setCallsigns(div, f.callsign, f.number);
  refreshFlight(div);
  loadLiveries(div);
  loadLoadouts(div);
}

function setCallsigns(div, value, number) {
  const a = AC[div.querySelector(".aircraft").value];
  const own = a.callsigns.slice(8), generic = a.callsigns.slice(0, 8);
  const sel = div.querySelector(".callsign");
  sel.innerHTML = (own.length ? `<optgroup label="${esc(a.name)}">${own.map(c => `<option>${esc(c)}</option>`).join("")}</optgroup>` : "")
    + `<optgroup label="Generic">${generic.map(c => `<option>${esc(c)}</option>`).join("")}</optgroup>`;
  sel.value = value && a.callsigns.includes(value) ? value : (own[0] || generic[Math.max(0, flights().indexOf(div)) % 8]);
  div.querySelector(".number").value = number || nextFreeNumber(sel.value, div);
}

function refreshFlight(div) {
  const q = (s) => div.querySelector(s);
  const a = AC[q(".aircraft").value];
  const slots = q(".slots");
  slots.max = a.max_group;
  if (+slots.value > a.max_group) slots.value = a.max_group;
  if (+slots.value < 1) slots.value = 1;
  const aiSel = q(".ai_wingmen"), wanted = aiSel.options.length ? +aiSel.value : +(div.dataset.ai || 0);
  const room = a.max_group - +slots.value;
  aiSel.innerHTML = Array.from({ length: room + 1 }, (_, n) => `<option>${n}</option>`).join("");
  aiSel.value = Math.min(wanted, room);
  const carrierOk = a.carrier && theater().has_carrier;
  q(".base option[value=carrier]").disabled = !carrierOk;
  if (!carrierOk) q(".base").value = "airfield";
  q(".era-tag").textContent = a.era ? ERA_SHORT[a.era] : "Any era";
  q(".dtc").classList.toggle("hidden", !a.dtc);
  q(".dtc-box").classList.toggle("hidden", !a.dtc);
}

const loadoutCache = {};
async function loadLoadouts(div) {
  const ac = div.querySelector(".aircraft").value, mt = radio("mission_type");
  const key = `${ac}|${mt}`;
  loadoutCache[key] = loadoutCache[key] || fetch(`/api/loadouts?aircraft=${encodeURIComponent(ac)}&mission=${mt}`).then(r => r.json());
  const list = await loadoutCache[key];
  if (div.querySelector(".aircraft").value !== ac || radio("mission_type") !== mt) return;
  div._loadouts = list;
  const sel = div.querySelector(".loadout");
  sel.innerHTML = list.map(p => `<option value="${esc(p.id)}">${esc(p.label)}${p.recommended ? " (recommended)" : ""}</option>`).join("");
  const keep = div.dataset.loadout;
  sel.value = keep && list.some(p => p.id === keep) ? keep : list[0].id;
  div.dataset.loadout = sel.value === list[0].id ? "" : sel.value;
  showWeapons(div);
}

const liveryCache = {};
async function loadLiveries(div) {
  const ac = div.querySelector(".aircraft").value;
  liveryCache[ac] = liveryCache[ac] || fetch(`/api/liveries?aircraft=${encodeURIComponent(ac)}`).then(r => r.json());
  const data = await liveryCache[ac];
  if (div.querySelector(".aircraft").value !== ac) return;
  const list = data.liveries || [];
  div._liveries = list;
  const opt = (l) => `<option value="${esc(l.id)}">${esc(l.label)}</option>`;
  const onServer = list.filter(l => l.installed), squads = list.filter(l => !l.installed);
  const sel = div.querySelector(".livery");
  sel.innerHTML = `<option value="">DCS default</option>`
    + (onServer.length ? `<optgroup label="Installed on your DCS server">${onServer.map(opt).join("")}</optgroup>` : "")
    + (squads.length ? `<optgroup label="${onServer.length ? "Other squadron liveries" : "Squadron liveries (stock DCS)"}">${squads.map(opt).join("")}</optgroup>` : "");
  const keep = div.dataset.livery;
  sel.value = keep && list.some(l => l.id === keep) ? keep : "";
  div.dataset.livery = sel.value;
  sel.title = list.length ? "" : "No liveries known for this aircraft yet. The DCS server hook can report the ones installed on your server.";
}

function showWeapons(div) {
  const p = (div._loadouts || []).find(x => x.id === div.querySelector(".loadout").value);
  div.querySelector(".weapons").textContent = p && p.weapons.length ? p.weapons.join(" · ") : "No stores. Rearm with the ground crew.";
}

function collect() {
  return {
    theater: $("theater").value, blue_base: $("blue_base").value, red_base: $("red_base").value,
    mission_type: radio("mission_type"), difficulty: radio("difficulty"), enemy_air: radio("enemy_air"),
    era: $("era").value, time_of_day: $("time_of_day").value, season: radio("season"),
    weather: $("weather").value, wind: radio("wind"), awacs: $("awacs").checked,
    tankers: $("tankers").checked, singleplayer: $("singleplayer").checked, title: $("title").value,
    scripts: [...document.querySelectorAll("input[name=script]:checked")].map(i => i.value),
    flights: flights().map(d => ({
      aircraft: d.querySelector(".aircraft").value, slots: +d.querySelector(".slots").value,
      callsign: d.querySelector(".callsign").value, number: +d.querySelector(".number").value,
      squadron: d.querySelector(".squadron").value, base: d.querySelector(".base").value,
      start: d.querySelector(".start").value, loadout: d.dataset.loadout || "", livery: d.dataset.livery || "",
      dtc: d.querySelector(".dtc-on").checked, ai_wingmen: +d.querySelector(".ai_wingmen").value,
      route: d.dataset.route ? JSON.parse(d.dataset.route) : {},
    })),
    secondaries: +$("secondaries").value, chain: $("chain").checked, popups: $("popups").checked,
    dynamic_air: $("dynamic_air").checked, front_line: $("front_line").checked,
    tot: $("tot").value.trim(),
    srs: $("srs").value.trim(), srs_note: $("srs_note").value.trim(),
    mods: [...document.querySelectorAll("input[name=mod]:checked")].map(i => i.value),
    publish: [...document.querySelectorAll("input[name=publish]:checked")].map(i => i.value),
    ai_flights: aiFlights().map(d => ({
      task: d.querySelector(".ai_task").value, aircraft: d.querySelector(".ai_aircraft").value,
      count: +d.querySelector(".ai_count").value, escort: d.querySelector(".ai_escort").value,
      delay: d.querySelector(".ai_delay").value === "tot" ? "tot" : +d.querySelector(".ai_delay").value,
    })),
    jtac: $("jtac").checked,
    options: {
      labels: $("opt_labels").value, f10: $("opt_f10").value,
      ...Object.fromEntries(["external_views", "unlimited_fuel", "unlimited_weapons", "easy_comms",
        "civil_traffic", "birds"].map(k => [k, $("opt_" + k).checked])),
    },
  };
}

// ---------------------------------------------------------------- AI flights
const aiFlights = () => [...document.querySelectorAll(".aiflight")];
let lastPreview = { era: "modern", side: "west" };
const aiCache = {};
function playerFlightNames() {
  return flights().map(d => `${d.querySelector(".callsign").value} ${d.querySelector(".number").value}`);
}
function refreshEscorts() {
  for (const d of aiFlights()) {
    const sel = d.querySelector(".ai_escort"), keep = sel.value || d.dataset.escort;
    const names = playerFlightNames();
    sel.innerHTML = names.map(n => `<option>${esc(n)}</option>`).join("");
    if (names.includes(keep)) sel.value = keep;
    d.querySelector(".escort-box").classList.toggle("hidden", d.querySelector(".ai_task").value !== "escort");
  }
}
async function loadAIAircraft(d) {
  const t = d.querySelector(".ai_task").value;
  const key = `${t}|${lastPreview.era}|${lastPreview.side}`;
  aiCache[key] = aiCache[key] || fetch(`/api/ai_aircraft?task=${t}&era=${lastPreview.era}&side=${lastPreview.side}`).then(r => r.json());
  const list = await aiCache[key];
  if (d.querySelector(".ai_task").value !== t) return;
  const sel = d.querySelector(".ai_aircraft"), keep = sel.value || d.dataset.aircraft;
  const sug = list.filter(a => a.suggested), rest = list.filter(a => !a.suggested);
  const opt = a => `<option value="${esc(a.id)}">${esc(a.name)} (${ERA_SHORT[a.era]})</option>`;
  sel.innerHTML = (sug.length ? `<optgroup label="Matches your era">${sug.map(opt).join("")}</optgroup>` : "")
    + `<optgroup label="Other eras">${rest.map(opt).join("")}</optgroup>`;
  if (keep && list.some(a => a.id === keep)) sel.value = keep;
  d.dataset.aircraft = sel.value;
  refresh();
}
function addAIFlight(f = {}) {
  if (aiFlights().length >= 8) return;
  const d = document.createElement("div");
  d.className = "aiflight";
  d.dataset.aircraft = f.aircraft || "";
  d.dataset.escort = f.escort || "";
  d.innerHTML = `
    <div><label>Job</label><select class="ai_task">${OPT.ai_tasks.map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("")}</select></div>
    <div><label>Aircraft</label><select class="ai_aircraft"></select></div>
    <div><label>Count</label><select class="ai_count">${[1, 2, 3, 4].map(n => `<option>${n}</option>`).join("")}</select></div>
    <div class="escort-box"><label>Escort</label><select class="ai_escort"></select></div>
    <div><label>Launch</label><select class="ai_delay"><option value="tot">Time it off the TOT</option>${[0, 5, 10, 15, 20, 30, 45, 60].map(n => `<option value="${n}">${n ? "T+" + n + " min" : "At start"}</option>`).join("")}</select></div>
    <button type="button" class="link" title="Remove AI flight">Remove</button>`;
  $("ai_flights").appendChild(d);
  const q = (s) => d.querySelector(s);
  q(".ai_task").value = f.task || "cap";
  q(".ai_count").value = f.count || 2;
  q(".ai_delay").value = f.delay === "tot" ? "tot" : (f.delay || 0);
  q(".ai_task").onchange = () => { refreshEscorts(); loadAIAircraft(d); };
  q(".ai_aircraft").onchange = () => { d.dataset.aircraft = q(".ai_aircraft").value; refresh(); };
  for (const s of [".ai_count", ".ai_delay", ".ai_escort"]) q(s).onchange = refresh;
  q("button").onclick = () => { d.remove(); refresh(); };
  refreshEscorts();
  loadAIAircraft(d);
}

// ----------------------------------------------------------------------- map
let map = null, layer = null;
const MARK = { home: "#2f80ed", enemy: "#e5675c", target: "#e0a526", bulls: "#8e44ad", carrier: "#27ae60" };
function drawMap(p) {
  if (!window.L || !p.points) return;
  $("map").classList.remove("hidden");
  if (!map) {
    map = L.map("map", { zoomControl: false, attributionControl: true });
    // OpenStreetMap's tile policy: no a/b/c subdomains, a referrer, and this attribution.
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      { maxZoom: 12, referrerPolicy: "strict-origin-when-cross-origin", attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors" }).addTo(map);
    layer = L.layerGroup().addTo(map);
  }
  layer.clearLayers();
  drawRoute(p);
  const byKind = {};
  for (const pt of p.points) {
    byKind[pt.kind] = pt.pos;
    L.circleMarker(pt.pos, { radius: 7, color: "#fff", weight: 2, fillColor: MARK[pt.kind], fillOpacity: 1 })
      .bindTooltip(pt.label).addTo(layer);
  }
  if (byKind.home && byKind.target) L.polyline([byKind.carrier || byKind.home, byKind.target], { color: MARK.target, dashArray: "6 6", weight: 2 }).addTo(layer);
  const key = JSON.stringify(p.points.map(x => x.pos));
  if (key !== map._dmmKey) { map._dmmKey = key; map.fitBounds(L.latLngBounds(p.points.map(x => x.pos)).pad(0.25)); }
}

function drawRoute(p) {
  const names = playerFlightNames();
  const sel = $("route_flight"), keep = sel.value;
  sel.innerHTML = names.map((n, i) => `<option value="${i}">${esc(n)}</option>`).join("");
  if (keep && +keep < names.length) sel.value = keep;
  $("route_tools").classList.toggle("hidden", !names.length || !p.routes);
  const i = +sel.value || 0, d = flights()[i], r = (p.routes || [])[i];
  $("route_list").textContent = r ? "Waypoints: " + r.steps.map(x => x.name).join(" → ") + " → home. Drag the gold handles to move Push, Ingress and Egress." : "";
  if (!d || !r) return;
  L.polyline([r.origin, ...r.steps.map(x => x.pos)], { color: "#2f80ed", weight: 3 }).addTo(layer);
  for (const st of r.steps) {
    if (!st.editable) {
      L.circleMarker(st.pos, { radius: 4, color: "#2f80ed", weight: 2, fillColor: "#fff", fillOpacity: 1 })
        .bindTooltip(st.name).addTo(layer);
      continue;
    }
    const m = L.marker(st.pos, { draggable: true, icon: L.divIcon({ className: "route-handle" }) })
      .bindTooltip(`${st.name} (drag me)`).addTo(layer);
    m.on("dragend", () => {
      const ll = m.getLatLng(), cur = d.dataset.route ? JSON.parse(d.dataset.route) : {};
      cur[st.key] = [+ll.lat.toFixed(5), +ll.lng.toFixed(5)];
      d.dataset.route = JSON.stringify(cur);
      refresh();
    });
  }
}

function renderScripts() {
  $("scripts").innerHTML = OPT.scripts.map(s => `
    <label class="card script">
      <input type="checkbox" name="script" value="${esc(s.id)}" ${s.available ? "" : "disabled"}>
      <b>${esc(s.name)}</b><small>${esc(s.desc)}</small>
      ${s.needs.length ? `<small class="req">Also adds ${s.needs.map(n => esc(OPT.scripts.find(x => x.id === n)?.name || n)).join(", ")}</small>` : ""}
      ${s.helicopters ? `<small class="req heli-req">Needs a helicopter flight</small>` : ""}
      ${s.available ? "" : `<small class="req">Not installed in this image</small>`}
    </label>`).join("");
  $("scripts").onchange = (e) => {
    const s = OPT.scripts.find(x => x.id === e.target.value);
    if (e.target.checked && s) s.needs.forEach(n => { const el = document.querySelector(`input[name=script][value="${n}"]`); if (el) el.checked = true; });
    refresh();
  };
}

let previewTimer = null;
function refresh() {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(updateSummary, 150);
}

async function updateSummary() {
  const body = collect();
  try { localStorage.setItem(STORE, JSON.stringify(body)); } catch (e) {}
  const p = await (await fetch("/api/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })).json();
  const eraChanged = p.era !== lastPreview.era || p.side !== lastPreview.side;
  lastPreview = p;
  if (eraChanged) aiFlights().forEach(loadAIAircraft);
  refreshEscorts();
  drawMap(p);
  const autoLabel = OPT.eras.find(e => e[0] === p.detected_era)[1];
  $("era").options[0].textContent = `Auto (${autoLabel})`;
  const seats = body.flights.reduce((n, f) => n + f.slots, 0);
  const aiWing = body.flights.reduce((n, f) => n + f.ai_wingmen, 0);
  const mt = body.mission_type;
  const rows = [
    ["Era", p.era_label], ["You", `${p.player_side} · ${seats} player${seats === 1 ? "" : "s"}${aiWing ? ` + ${aiWing} AI` : ""}`],
    ["Enemy", p.enemy_side],
  ];
  if (mt === "cap" || (mt !== "free" && body.enemy_air !== "none")) rows.push(["Fighters", p.fighters]);
  if (mt === "cas") rows.push(["Armor", p.tanks]);
  if (mt === "sead" || mt === "strike") rows.push(["Air defense", p.sam]);
  if (mt === "antiship") rows.push(["Ships", p.ships.join(", ")]);
  rows.push(["Flights", body.flights.map(f => `${f.callsign} ${f.number}`).join(", ")]);
  if (body.ai_flights.length) rows.push(["AI flights", body.ai_flights.map(f => `${f.count}× ${f.aircraft} (${f.task})`).join(", ")]);
  if (p.distance_nm) rows.push(["Distance", `${p.distance_nm} nm home → target`]);
  $("summary").innerHTML = rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("");

  const sup = p.support;
  const tankers = ["boom", "drogue"].filter(k => sup.includes(k));
  $("support_note").textContent = sup.length
    ? `${p.era_label}: AWACS ${sup.includes("awacs") ? "available" : "not available"}; tankers: ${tankers.join(" + ") || "none"}.`
    : `No AWACS or tankers in the ${p.era_label} era.`;
  if (["cas", "strike", "sead"].includes(mt) && $("jtac").checked)
    $("support_note").textContent += ["ww2", "korea"].includes(p.era) ? " No JTAC in this era." : " JTAC on 266.0 AM, laser 1688.";

  const warns = [];
  const hasHeli = body.flights.some(f => AC[f.aircraft].helicopter);
  document.querySelectorAll(".heli-req").forEach(el => el.classList.toggle("hidden", hasHeli));
  for (const id of ["ctld", "csar"]) {
    if (body.scripts.includes(id) && !hasHeli) warns.push(`${OPT.scripts.find(s => s.id === id).name} needs a helicopter flight.`);
  }
  if (body.scripts.includes("hound") && !(body.awacs && sup.includes("awacs"))) warns.push("Hound ELINT uses the AWACS as its sensor. Turn AWACS on (Vietnam era or later).");
  const seen = {};
  body.flights.forEach(f => { const k = `${f.callsign} ${f.number}`; if (seen[k]) warns.push(`Two flights are called ${k}; the second will be renumbered.`); seen[k] = 1; });
  flights().forEach((d, i) => {
    const f = body.flights[i];
    d.querySelector(".title").textContent = `${f.callsign} ${f.number}` + (f.squadron ? ` · ${f.squadron}` : "");
  });
  $("live_warnings").innerHTML = warns.map(w => `<p class="warn">${esc(w)}</p>`).join("");
}

function restore(s) {
  $("flights").innerHTML = ""; $("ai_flights").innerHTML = "";
  if (!s) return addFlight();
  if (OPT.theaters.some(t => t.key === s.theater)) { $("theater").value = s.theater; onTheater(); }
  $("blue_base").value = s.blue_base; $("red_base").value = s.red_base;
  ["mission_type", "difficulty", "enemy_air", "season", "wind"].forEach(k => setRadio(k, s[k]));
  $("time_of_day").value = s.time_of_day; $("weather").value = s.weather; $("era").value = s.era || "auto";
  $("awacs").checked = s.awacs; $("tankers").checked = s.tankers;
  $("singleplayer").checked = s.singleplayer; $("title").value = s.title || "";
  (s.scripts || []).forEach(id => { const el = document.querySelector(`input[name=script][value="${id}"]`); if (el && !el.disabled) el.checked = true; });
  (s.flights?.length ? s.flights : [{}]).forEach(addFlight);
  (s.ai_flights || []).forEach(addAIFlight);
  if (s.jtac !== undefined) $("jtac").checked = s.jtac;
  $("secondaries").value = s.secondaries || 0; $("tot").value = s.tot || "";
  $("srs").value = s.srs || ""; $("srs_note").value = s.srs_note || "";
  for (const k of ["chain", "popups", "dynamic_air", "front_line"]) if (k in s) $(k).checked = !!s[k];
  document.querySelectorAll("input[name=mod]").forEach(i => i.checked = (s.mods || []).includes(i.value));
  const o = s.options || {};
  if (o.labels) $("opt_labels").value = o.labels;
  if (o.f10) $("opt_f10").value = o.f10;
  for (const k of ["external_views", "unlimited_fuel", "unlimited_weapons", "easy_comms", "civil_traffic", "birds"]) {
    if (k in o) $("opt_" + k).checked = !!o[k];
  }
}
function applyConfig(s) {
  document.querySelectorAll("input[name=script]").forEach(i => i.checked = false);
  restore(s);
  onMissionType();
  $("result").classList.add("hidden");
}

// -------------------------------------------------------------------- setups
async function loadSetupList(select) {
  const names = await (await fetch("/api/setups")).json();
  $("setups").innerHTML = `<option value="">Saved setups…</option>` + names.map(n => `<option>${esc(n)}</option>`).join("");
  if (select) $("setups").value = select;
}
async function setupLoad() {
  const n = $("setups").value; if (!n) return;
  applyConfig(await (await fetch(`/api/setups/${encodeURIComponent(n)}`)).json());
}
async function setupSave() {
  const n = prompt("Name this setup (e.g. 'Friday night Hornets'):", $("setups").value || $("title").value || "");
  if (!n) return;
  const r = await (await fetch(`/api/setups/${encodeURIComponent(n)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(collect()) })).json();
  loadSetupList(r.saved);
}
async function setupDelete() {
  const n = $("setups").value; if (!n || !confirm(`Delete saved setup "${n}"?`)) return;
  await fetch(`/api/setups/${encodeURIComponent(n)}`, { method: "DELETE" });
  loadSetupList();
}
function pick(a) { return a[Math.floor(Math.random() * a.length)]; }
function surprise() {
  clearRoutes();
  const t = pick(OPT.theaters);
  $("theater").value = t.key; onTheater();
  $("blue_base").value = pick(t.blue_bases); $("red_base").value = pick(t.red_bases);
  const types = OPT.mission_types.map(m => m[0]).filter(k => k !== "free" && (k !== "antiship" || t.has_sea));
  setRadio("mission_type", pick(types));
  setRadio("difficulty", pick(["easy", "medium", "hard"]));
  setRadio("enemy_air", pick(["none", "light", "heavy"]));
  $("time_of_day").value = pick(OPT.times.filter(x => x !== "night"));
  $("weather").value = pick(OPT.weather);
  setRadio("season", pick(["summer", "winter"])); setRadio("wind", pick(OPT.winds));
  onMissionType();
}

function fmtWhen(iso) {
  return new Date(iso).toLocaleString([], { weekday: "short", day: "numeric", month: "short",
    hour: "2-digit", minute: "2-digit", timeZoneName: "short" });
}

async function loadEvents() {
  const list = await (await fetch("/api/events")).json();
  $("events_box").classList.toggle("hidden", !list.length);
  $("events").innerHTML = list.map(e => `<li><a href="/e/${esc(e.id)}" target="_blank">${esc(e.title)}</a>
    ${e.when_iso ? "· " + esc(fmtWhen(e.when_iso)) : e.when ? "· " + esc(e.when) : ""} · ${e.claimed}/${e.seats} seats${e.repeat ? " · weekly" : ""}</li>`).join("");
}

function makeEvent() {
  $("ev_result").classList.add("hidden");
  $("ev_error").textContent = "";
  $("ev_create").disabled = false;
  if (!$("ev_title").value) $("ev_title").value = $("title").value || "";
  if (!$("ev_when").value) {  // default: tomorrow at 20:00 local
    const d = new Date(); d.setDate(d.getDate() + 1); d.setHours(20, 0, 0, 0);
    $("ev_when").value = new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  }
  $("ev_discord_box").classList.toggle("hidden", !(OPT.integrations.discord && OPT.integrations.public_url));
  $("event_panel").showModal();
}

async function createEvent() {
  $("ev_error").textContent = "";
  const res = await fetch("/api/events", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: $("ev_title").value || "Mission night",
      when_iso: $("ev_when").value ? new Date($("ev_when").value).toISOString() : "",
      when: $("ev_when").value ? new Date($("ev_when").value).toLocaleString([], { weekday: "short", day: "numeric",
        month: "short", hour: "2-digit", minute: "2-digit", timeZoneName: "short" }) : "",
      repeat: $("ev_repeat").checked ? "weekly" : "",
      discord: !$("ev_discord_box").classList.contains("hidden") && $("ev_discord").checked, config: collect() }) });
  const data = await res.json();
  if (!res.ok) { $("ev_error").textContent = data.error; return; }
  const link = (OPT.integrations.public_url || location.origin) + data.url;
  $("ev_link").value = link;
  $("ev_open").href = data.url;
  $("ev_discord_result").textContent = data.discord ? (data.discord === "ok" ? "Posted to Discord." : data.discord) : "";
  if (!OPT.integrations.public_url && /^(localhost|127\.)/.test(location.hostname))
    $("ev_discord_result").textContent += " Note: 'localhost' only works on this computer. Send friends this computer's "
      + "network address instead (e.g. http://192.168.x.x:8080/...), or set PUBLIC_URL in .env.";
  $("ev_result").classList.remove("hidden");
  $("ev_create").disabled = true;
  $("ev_link").select();
  loadEvents();
}

// Temporary missions disappear after a while unless kept.
function expiresIn(ts) {
  const h = Math.max(0, (ts * 1000 - Date.now()) / 3600000);
  return h >= 1 ? `${Math.round(h)} h` : `${Math.max(1, Math.round(h * 60))} min`;
}
function keepText(m) {
  return m.kept ? "Kept: this mission stays until you delete it."
    : `Temporary: deleted in ${expiresIn(m.expires)} unless you keep it.`;
}
async function setKept(stem, keep) {
  const res = await fetch(`/api/missions/${encodeURIComponent(stem)}/keep`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ keep }) });
  return res.ok ? res.json() : null;
}
let lastResult = null;
function showKeep() {
  if (!lastResult) return;
  $("keep_text").textContent = keepText(lastResult);
  $("keep_btn").textContent = lastResult.kept ? "Don't keep" : "Keep this mission";
}

async function loadRecent() {
  const list = await (await fetch("/api/missions")).json();
  $("recent").innerHTML = list.length
    ? list.map(m => `<li><a href="${esc(m.url)}">${esc(m.filename)}</a>${m.kept
        ? `<span class="badge ok" title="Stays until you delete it">kept</span>`
        : `<span class="badge" title="Deleted automatically unless you keep it">${esc(expiresIn(m.expires))} left</span>`}${m.briefing
        ? ` · <a href="${esc(m.briefing)}" target="_blank">Briefing</a>` : ""}${m.report
        ? (m.report.errors.length ? `<span class="badge bad" title="${esc(m.report.errors.join("\n"))}">${m.report.errors.length} script error(s) on server</span>`
          : `<span class="badge ok">loaded clean on server</span>`) : ""}${m.settings
        ? ` · <button type="button" class="link reuse" data-url="${esc(m.settings)}" title="Load this mission's settings into the form">Reuse settings</button>` : ""}
        · ${m.kept ? `<button type="button" class="link del" data-stem="${esc(m.stem)}">Delete</button>`
          : `<button type="button" class="link keep" data-stem="${esc(m.stem)}">Keep</button>`}</li>`).join("")
    : "<li>None yet.</li>";
  document.querySelectorAll("#recent .keep").forEach(b => b.onclick = async () => {
    const st = await setKept(b.dataset.stem, true);
    if (st && lastResult && lastResult.stem === b.dataset.stem) { Object.assign(lastResult, st); showKeep(); }
    loadRecent();
  });
  document.querySelectorAll("#recent .del").forEach(b => b.onclick = async () => {
    if (!confirm(`Delete ${b.dataset.stem}? Its download, Briefing Room and debrief go too.`)) return;
    const r = await fetch(`/api/missions/${encodeURIComponent(b.dataset.stem)}`, { method: "DELETE" });
    if (!r.ok) { alert((await r.json().catch(() => ({}))).error || "Couldn't delete it."); return; }
    if (lastResult && lastResult.stem === b.dataset.stem) $("result").classList.add("hidden");
    loadRecent();
  });
  document.querySelectorAll(".reuse").forEach(b => b.onclick = async () => {
    applyConfig(await (await fetch(b.dataset.url)).json());
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

async function onGenerate() {
  const body = collect();
  $("error").textContent = "";
  $("generate").disabled = true; $("generate").textContent = "Generating…";
  try {
    const res = await fetch("/api/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Generation failed");
    $("download").href = data.url;
    $("room").href = data.briefing_url;
    $("download").textContent = `Download ${data.filename}`;
    $("briefing").textContent = data.briefing;
    $("warnings").textContent = (data.warnings || []).join(" ");
    const PUB = { folder: "Server folder", sftp: "SFTP", discord: "Discord" };
    $("published").textContent = Object.entries(data.published || {})
      .map(([k, v]) => `${PUB[k]}: ${v === "ok" ? "done" : v}`).join(" · ");
    lastResult = { stem: data.filename.replace(/\.miz$/, ""), kept: data.kept, expires: data.expires };
    showKeep();
    $("result").classList.remove("hidden");
    $("result").scrollIntoView({ behavior: "smooth", block: "nearest" });
    loadRecent();
  } catch (e) {
    $("error").textContent = e.message;
  } finally {
    $("generate").disabled = false; $("generate").textContent = "Generate mission";
  }
}

// ---- update note: the Windows app checks GitHub once a day (see app/updates.py)
async function showUpdate() {
  try {
    const u = await (await fetch("/api/update")).json();
    if (!u.available) return;
    const a = $("update_link");
    a.href = u.available.url;
    a.textContent = `Version ${u.available.version} is available (you have ${u.current}). Download it`;
    $("update").classList.remove("hidden");
  } catch (e) { /* no update info: nothing to show */ }
}

(async function init() {
  $("keep_btn").onclick = async () => {
    const st = await setKept(lastResult.stem, !lastResult.kept);
    if (st) { Object.assign(lastResult, st); showKeep(); loadRecent(); }
  };
  OPT = await (await fetch("/api/options")).json();
  const srsDefault = OPT.integrations.srs;
  $("srs").placeholder = srsDefault ? `${srsDefault.address} (default)` : "e.g. srs.myserver.com:5002";
  $("srs_note").placeholder = srsDefault?.note ? `${srsDefault.note} (default)` : "e.g. password in #dcs-info";
  OPT.aircraft.forEach(a => AC[a.id] = a);
  fillSelect($("theater"), OPT.theaters.map(t => [t.key, t.label]), "caucasus");
  $("mission_types").innerHTML = OPT.mission_types.map(([k, v]) =>
    `<label class="card"><input type="radio" name="mission_type" value="${k}" ${k === "cas" ? "checked" : ""}>
     <b>${esc(v)}</b><small>${MISSION_HINTS[k] || ""}</small></label>`).join("");
  seg($("difficulty"), "difficulty", OPT.difficulties, "medium");
  seg($("enemy_air"), "enemy_air", ["none", "light", "heavy"], "light");
  seg($("season"), "season", ["summer", "winter"], "summer");
  seg($("wind"), "wind", OPT.winds, "light");
  fillSelect($("time_of_day"), OPT.times, "morning");
  fillSelect($("weather"), OPT.weather, "clear");
  fillSelect($("era"), [["auto", "Auto"], ...OPT.eras], "auto");
  renderScripts();
  $("theater").onchange = onTheater;
  $("mission_types").onchange = onMissionType;
  for (const id of ["blue_base", "red_base", "era", "time_of_day", "weather", "awacs", "tankers", "singleplayer",
                    "difficulty", "enemy_air", "season", "wind", "jtac", "opt_labels", "opt_f10",
                    "opt_external_views", "opt_unlimited_fuel", "opt_unlimited_weapons", "opt_easy_comms",
                    "opt_civil_traffic", "opt_birds"]) $(id).addEventListener("change", refresh);
  $("add_ai").onclick = () => addAIFlight();
  for (const id of ["blue_base", "red_base"]) $(id).addEventListener("change", clearRoutes);
  $("mods").innerHTML = OPT.mods.map(m => `<label class="card"><input type="checkbox" name="mod" value="${esc(m.id)}">
    <b>${esc(m.name)}</b><small>${esc(m.desc)}</small></label>`).join("");
  $("mods").onchange = refresh;
  const integ = OPT.integrations;
  $("publish_opts").innerHTML = [["folder", "Copy to server"], ["sftp", "Upload (SFTP)"], ["discord", "Post to Discord"]]
    .filter(([k]) => integ[k]).map(([k, v]) => `<label class="switch"><input type="checkbox" name="publish" value="${k}"> ${v}</label>`).join("");
  for (const id of ["secondaries", "chain", "popups", "dynamic_air", "front_line", "route_flight"]) $(id).addEventListener("change", refresh);
  $("tot").addEventListener("change", refresh);
  $("route_reset").onclick = () => { const d = flights()[+$("route_flight").value || 0]; if (d) { d.dataset.route = ""; refresh(); } };
  $("make_event").onclick = makeEvent;
  $("ev_create").onclick = createEvent;
  $("ev_cancel").onclick = () => $("event_panel").close();
  $("ev_copy").onclick = async () => {
    try { await navigator.clipboard.writeText($("ev_link").value); $("ev_copy").textContent = "Copied!"; }
    catch (e) { $("ev_link").select(); document.execCommand("copy"); $("ev_copy").textContent = "Copied!"; }
    setTimeout(() => $("ev_copy").textContent = "Copy", 1500);
  };
  loadEvents();
  $("setup_load").onclick = setupLoad; $("setup_save").onclick = setupSave; $("setup_delete").onclick = setupDelete;
  $("setups").onchange = setupLoad;
  $("surprise").onclick = surprise;
  loadSetupList();
  $("title").addEventListener("input", refresh);
  $("add_flight").onclick = () => { addFlight(); refresh(); };
  $("generate").onclick = onGenerate;
  onTheater();
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem(STORE)); } catch (e) {}
  try { restore(saved); } catch (e) { $("flights").innerHTML = ""; addFlight(); }
  onMissionType();
  loadRecent();
  showUpdate();
})();
