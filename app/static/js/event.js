/* Page script for event.html. */
"use strict";
const EID = document.body.dataset.eid;
let EV = null, INTEG = {};
const NAMES = {};
try { $("me").value = localStorage.getItem("dcs-mm:name") || ""; } catch (e) {}
$("me").oninput = () => { try { localStorage.setItem("dcs-mm:name", $("me").value); } catch (e) {} render(); };

function render() {
  const me = $("me").value.trim().toLowerCase();
  $("title").textContent = EV.title;
  $("when").textContent = EV.when_iso
    ? new Date(EV.when_iso).toLocaleString([], { weekday: "long", day: "numeric", month: "long",
        hour: "2-digit", minute: "2-digit", timeZoneName: "short" }) + " (your time)"
    : EV.when;
  const series = [EV.repeat ? "Repeats every week." : "",
    EV.prev_id ? `<a href="/e/${encodeURIComponent(EV.prev_id)}">Previous week</a>` : "",
    EV.next_id ? `<a href="/e/${encodeURIComponent(EV.next_id)}"><b>Next week's sign-up →</b></a>` : ""].filter(Boolean);
  $("series").innerHTML = series.join(" · ");
  $("series").classList.toggle("hidden", !series.length);
  const c = EV.config;
  $("meta").textContent = [NAMES[c.theater] || c.theater, NAMES[c.mission_type] || c.mission_type,
                            c.difficulty, c.tot ? "TOT " + c.tot : c.time_of_day].filter(Boolean).join(" · ")
    + ` · ${EV.seats.filter(s => s.pilot).length}/${EV.seats.length} seats taken`;
  const byFlight = {};
  for (const s of EV.seats) (byFlight[s.seat.replace(/-\d+$/, "")] = byFlight[s.seat.replace(/-\d+$/, "")] || []).push(s);
  $("seats").innerHTML = Object.entries(byFlight).map(([flight, seats]) => `
    <div class="flight"><h3>${esc(flight)} <small>${esc(NAMES[seats[0].aircraft] || seats[0].aircraft)}${seats[0].squadron ? " · " + esc(seats[0].squadron) : ""}</small></h3>
    ${seats.map(s => {
      const mine = s.pilot && s.pilot.toLowerCase() === me;
      return `<div class="seat ${mine ? "mine" : ""}"><span>${esc(s.seat)}</span>
        <span class="who ${s.pilot ? "taken" : ""}">${s.pilot ? esc(s.pilot) : "open"}</span>
        ${mine ? `<button data-seat="${esc(s.seat)}" data-act="release">Leave</button>`
          : `<button data-seat="${esc(s.seat)}" data-act="claim" ${s.pilot || !me ? "disabled" : ""}>Take seat</button>`}
      </div>`; }).join("")}</div>`).join("");
  document.querySelectorAll("#seats button").forEach(b => b.onclick = () => claim(b.dataset.seat, b.dataset.act));
  if (EV.mission) $("mission_status").innerHTML = `Latest: <a href="${esc(EV.mission.url)}">${esc(EV.mission.filename)}</a>`
    + (EV.mission.briefing_url ? ` · <a href="${esc(EV.mission.briefing_url)}"><b>Open the briefing room</b></a>` : "");
}

async function claim(seat, act) {
  $("error").textContent = "";
  const me = $("me").value.trim();
  const res = await fetch(`/api/events/${EID}/claim`, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seat, name: act === "claim" ? me : "", me }) });
  const data = await res.json();
  if (!res.ok) { $("error").textContent = data.error; return load(); }
  EV = data; render();
}

async function load() {
  EV = await (await fetch(`/api/events/${EID}`)).json();
  render();
}

$("generate").onclick = async () => {
  $("generate").disabled = true; $("gen_result").textContent = "Generating…";
  const publish = [...document.querySelectorAll("input[name=publish]:checked")].map(i => i.value);
  const res = await fetch(`/api/events/${EID}/generate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ publish }) });
  const data = await res.json();
  $("generate").disabled = false;
  if (!res.ok) { $("gen_result").innerHTML = `<span class="err">${esc(data.error)}</span>`; return; }
  const pubs = Object.entries(data.published || {}).map(([k, v]) => `${k}: ${v === "ok" ? "done" : v}`).join(" · ");
  $("gen_result").innerHTML = `<span class="ok">Ready:</span> <a href="${esc(data.url)}">${esc(data.filename)}</a>`
    + ` · <a href="${esc(data.briefing_url)}"><b>Briefing room</b></a>${pubs ? " · " + esc(pubs) : ""}`;
  load();
};

(async function init() {
  const opt = await (await fetch("/api/options")).json();
  INTEG = opt.integrations;
  opt.aircraft.forEach(a => NAMES[a.id] = a.name);
  opt.theaters.forEach(t => NAMES[t.key] = t.label);
  opt.mission_types.forEach(([k, v]) => NAMES[k] = v);
  const opts = [["folder", "Copy to DCS server folder"], ["sftp", "Upload to server (SFTP)"], ["discord", "Post to Discord"]]
    .filter(([k]) => INTEG[k]);
  $("publish_opts").innerHTML = opts.map(([k, v]) => `<label><input type="checkbox" name="publish" value="${k}" checked> ${v}</label>`).join("");
  await load();
  setInterval(load, 15000);
})();
