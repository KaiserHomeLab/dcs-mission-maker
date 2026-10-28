/* Settings page: shows /api/settings grouped, saves only what changed. Secrets are never
   sent to the page: a secret field is left empty to keep it, typed in to replace it, or cleared. */
"use strict";

let fields = [];
const cleared = new Set();

const INPUT_TYPES = { url: "url", number: "number", secret: "password" };

function fieldHtml(f, canEdit) {
  const id = `f_${f.key}`;
  const off = f.locked || !canEdit ? " disabled" : "";
  const lock = f.locked ? `<span class="locked">set in .env</span>` : "";
  let input;
  if (f.kind === "secret") {
    input = `<div class="secret">
        <input type="password" id="${id}" autocomplete="new-password"${off}
          placeholder="${f.set ? "Saved. Type a new one to replace it" : "Not set"}">
        ${f.set && !off ? `<button type="button" class="clear" data-key="${f.key}">Clear</button>` : ""}
        <span class="state" id="state_${f.key}"></span>
      </div>`;
  } else {
    const list = f.kind === "folder" ? ` list="mission_folders"` : "";
    const step = f.kind === "number" ? ` step="any" min="0"` : "";
    input = `<input type="${INPUT_TYPES[f.kind] || "text"}" id="${id}" value="${esc(f.value)}"${list}${step}${off}
      placeholder="${esc(f.placeholder)}"
      spellcheck="false" autocomplete="off">`;
  }
  return `<div class="field">
      <label for="${id}">${esc(f.label)}${lock}</label>
      ${input}
      ${f.help ? `<p class="help">${esc(f.help)}</p>` : ""}
      <p class="err hidden" id="err_${f.key}"></p>
    </div>`;
}

function render(data) {
  fields = data.fields;
  cleared.clear();
  $("data_dir").textContent = data.data_dir;
  const ro = $("readonly");
  ro.classList.toggle("hidden", data.can_edit);
  ro.textContent = "To change settings, open this page on the PC running the app (http://localhost:…), "
    + "or set a builder password there first.";
  const groups = [...new Set(fields.map(f => f.group))];
  $("groups").innerHTML = groups.map(g => `<section><h2>${esc(g)}</h2>
      ${fields.filter(f => f.group === g).map(f => fieldHtml(f, data.can_edit)).join("")}</section>`).join("");
  $("mission_folders").innerHTML = (data.suggestions.SERVER_MISSIONS_DIR || [])
    .map(p => `<option value="${esc(p)}">`).join("");
  $("save").disabled = !data.can_edit;
  document.querySelectorAll("button.clear").forEach(b => b.onclick = () => {
    cleared.add(b.dataset.key);
    $(`f_${b.dataset.key}`).value = "";
    $(`state_${b.dataset.key}`).textContent = "Will be cleared when you save.";
  });
}

function changes() {
  const out = {};
  for (const f of fields) {
    const el = $(`f_${f.key}`);
    if (!el || el.disabled) continue;
    if (f.kind === "secret") {
      if (el.value) out[f.key] = el.value;
      else if (cleared.has(f.key)) out[f.key] = "";
    } else if (el.value.trim() !== (f.value || "")) {
      out[f.key] = el.value.trim();
    }
  }
  return out;
}

function showErrors(errors) {
  for (const f of fields) {
    const msg = errors[f.key];
    const p = $(`err_${f.key}`);
    p.textContent = msg || "";
    p.classList.toggle("hidden", !msg);
    $(`f_${f.key}`).setAttribute("aria-invalid", msg ? "true" : "false");
  }
}

async function save() {
  const body = changes();
  const status = $("status");
  if (!Object.keys(body).length) { status.className = ""; status.textContent = "Nothing changed."; return; }
  $("save").disabled = true;
  try {
    const r = await fetch("/api/settings", {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const data = await r.json();
    if (!r.ok) {
      showErrors(data.errors || {});
      status.className = "err";
      status.textContent = (data.errors || {})[""] || "Not saved: check the highlighted settings.";
      return;
    }
    render({ ...data, can_edit: true });
    status.className = "ok";
    status.textContent = "PORT" in body ? "Saved. Restart the app to use the new port." : "Saved.";
  } catch {
    status.className = "err";
    status.textContent = "Couldn't reach the app.";
  } finally {
    $("save").disabled = false;
  }
}

async function init() {
  const r = await fetch("/api/settings");
  render(await r.json());
  $("form").onsubmit = (e) => { e.preventDefault(); save(); };
}

init();
