import collections
import contextlib
import datetime
import functools
import hashlib
import io
import json
import os
import re
import secrets
import threading
import time
import zipfile
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows: one process (waitress), so the thread locks below are enough
    fcntl = None

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

from . import __version__, ai, debrief, eras, integrations, liveries, mission_store, mods, paths, scripts, settings
from .aircraft import AIRCRAFT, catalog
from .generator import (
    DIFFICULTIES,
    MISSION_TYPES,
    TIMES,
    WEATHER,
    WINDS,
    MissionError,
    MissionRequest,
    default_callsign,
    generate_full,
    preview,
)
from .loadouts import presets
from .theaters import THEATERS

OUTPUT_DIR = paths.output_dir()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SETUPS_DIR = OUTPUT_DIR / "setups"
SETUPS_DIR.mkdir(exist_ok=True)
EVENTS_DIR = OUTPUT_DIR / "events"
EVENTS_DIR.mkdir(exist_ok=True)
settings.refresh()  # settings.json -> os.environ before anything reads PORT etc.

app = Flask(__name__)
# Mission building keeps module-level state. Gunicorn runs one request per process, but
# waitress (python -m app, used on Windows) runs threads, so builds take turns.
_build_lock = threading.Lock()
# Largest request body: the DCS hook's livery scan is the biggest legitimate one.
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024


@functools.cache
def _static_hash(filename):
    return hashlib.sha256((Path(app.static_folder) / filename).read_bytes()).hexdigest()[:10]


@app.template_global()
def static_url(filename):
    """/static/<file>?v=<content hash>: a new URL whenever the file changes."""
    return f"/static/{filename}?v={_static_hash(filename)}"


# ---------------------------------------------------------------- access
# With APP_PASSWORD set, the builder and everything that generates, publishes or
# deletes needs it (HTTP Basic auth, any user name). What pilots use stays open:
# sign-up pages, the Briefing Room, downloads, and the DCS server hook's reports.
PUBLIC_ENDPOINTS = {
    "static", "healthz", "options", "event_page", "get_event", "claim_seat",
    "briefing_room", "mission_brief", "comm_card", "mission_debrief", "get_roster", "claim_roster_seat",
    "kneeboard_page", "print_pack", "drawing", "download",
    "add_report", "add_debrief", "installed_liveries", "dcs_hook",
}


@app.before_request
def _require_password():
    settings.refresh()  # first, so a password set on the Settings page applies at once
    password = os.environ.get("APP_PASSWORD", "")
    if not password or request.endpoint in PUBLIC_ENDPOINTS:
        return None
    auth = request.authorization
    if auth and secrets.compare_digest((auth.password or "").encode(), password.encode()):
        return None
    return ("Password required", 401, {"WWW-Authenticate": 'Basic realm="DCS Mission Maker", charset="UTF-8"'})


@app.after_request
def _headers(resp):
    # Versioned static files never change under the same URL: cache them for a year.
    if request.path.startswith("/static/") and request.args.get("v") and resp.status_code == 200:
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    # Map tile servers (OpenStreetMap) require a referrer: send just the origin, never the path.
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    return resp


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/healthz")
def healthz():
    """Health check (Docker, and the Windows app checking it's already running): the app
    is up and the output folder is writable."""
    ok = os.access(OUTPUT_DIR, os.W_OK)
    return jsonify({"ok": ok, "app": "dcs-mission-maker", "version": __version__}), 200 if ok else 503


# ------------------------------------------------------------------ settings
LOCAL_HOSTS = re.compile(r"(localhost|127\.0\.0\.1|\[::1\])(:\d+)?")


def _on_this_pc():
    """The browser is on the PC running the app. Checks the Host header too, so a web page
    can't reach the settings by pointing its own domain name at 127.0.0.1."""
    return request.remote_addr in ("127.0.0.1", "::1") and bool(LOCAL_HOSTS.fullmatch(request.host or ""))


@app.get("/settings")
def settings_page():
    return render_template("settings.html", version=__version__)


@app.get("/api/settings")
def get_settings():
    return jsonify({**settings.view(), "can_edit": bool(os.environ.get("APP_PASSWORD")) or _on_this_pc()})


@app.put("/api/settings")
def put_settings():
    # With a password set, the before_request check already asked for it. Without one,
    # anyone who can reach the app could otherwise point publishing at another folder.
    if not os.environ.get("APP_PASSWORD") and not _on_this_pc():
        return jsonify({"errors": {"": "Set a builder password first, or change settings on the PC "
                                       "running the app (http://localhost)."}}), 403
    errors = settings.save(request.get_json(silent=True))
    if errors:
        return jsonify({"errors": errors}), 400
    return jsonify(settings.view())


@app.get("/api/options")
def options():
    return jsonify({
        "theaters": [{
            "key": t.key, "label": t.label, "notes": t.notes,
            "blue_bases": t.blue_bases, "red_bases": [b.name for b in t.red_bases],
            "default_blue": t.default_blue, "default_red": t.default_red,
            "has_sea": t.red_sea is not None, "has_carrier": t.blue_carrier is not None,
        } for t in THEATERS.values()],
        "aircraft": catalog(),
        "mission_types": list(MISSION_TYPES.items()),
        "difficulties": DIFFICULTIES,
        "eras": [[e, eras.ERA_LABELS[e]] for e in eras.ERAS],
        "times": list(TIMES),
        "weather": WEATHER,
        "winds": list(WINDS),
        "scripts": scripts.available(),
        "ai_tasks": [[k, v[0]] for k, v in ai.AI_TASKS.items()],
        "integrations": integrations.status(),
        "mission_ttl_hours": mission_store.ttl_seconds() / 3600,
        "mods": mods.catalog(),
    })


@app.get("/api/ai_aircraft")
def ai_aircraft():
    t = request.args.get("task", "cap")
    if t not in ai.AI_TASKS:
        return jsonify({"error": "unknown task"}), 400
    return jsonify(ai.catalog(t, request.args.get("era"), request.args.get("side")))


def _setup_path(name):
    safe = re.sub(r"[^\w \-]", "", name or "").strip()[:60]
    if not safe:
        abort(400)
    return SETUPS_DIR / f"{safe}.json", safe


@app.get("/api/setups")
def list_setups():
    return jsonify(sorted(p.stem for p in SETUPS_DIR.glob("*.json")))


@app.get("/api/setups/<name>")
def get_setup(name):
    path, _ = _setup_path(name)
    if not path.exists():
        abort(404)
    return jsonify(json.loads(path.read_text(encoding="utf-8")))


@app.put("/api/setups/<name>")
def save_setup(name):
    path, safe = _setup_path(name)
    path.write_text(json.dumps(request.get_json(force=True) or {}, indent=2), encoding="utf-8")
    return jsonify({"saved": safe})


@app.delete("/api/setups/<name>")
def delete_setup(name):
    path, _ = _setup_path(name)
    path.unlink(missing_ok=True)
    return jsonify({"deleted": True})


@app.get("/api/loadouts")
def loadouts():
    ac = AIRCRAFT.get(request.args.get("aircraft", ""))
    mission = request.args.get("mission", "cas")
    if not ac or mission not in MISSION_TYPES:
        return jsonify({"error": "unknown aircraft or mission"}), 400
    return jsonify(presets(ac["cls"], mission))


@app.get("/api/liveries")
def livery_options():
    ac = request.args.get("aircraft", "")
    if ac not in AIRCRAFT:
        return jsonify({"error": "unknown aircraft"}), 400
    return jsonify({"liveries": liveries.options(ac), "server": liveries.installed_info()})


@app.post("/api/liveries")
def installed_liveries():
    """The DCS server hook's scan of the liveries installed on the server."""
    body = request.get_json(force=True, silent=True) or {}
    return jsonify({"ok": True, **liveries.save_installed(body, time.time())})


@app.get("/api/callsign")
def callsign():
    ac = request.args.get("aircraft", "")
    if ac not in AIRCRAFT:
        return jsonify({"error": "unknown aircraft"}), 400
    return jsonify({"callsign": default_callsign(ac, int(request.args.get("index", 0)))})


@app.post("/api/preview")
def api_preview():
    with _build_lock:
        return jsonify(preview(request.get_json(force=True) or {}))


@app.post("/api/generate")
def api_generate():
    body = request.get_json(force=True) or {}
    try:
        result = build_and_store(body)
    except (MissionError, TypeError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    result["published"] = publish(result["filename"], body.get("publish") or [])
    result.update(mission_store.status(result["filename"][:-4]))
    return jsonify(result)


def build_and_store(body):
    mission_store.cleanup()
    req = MissionRequest.from_json(body)
    with _build_lock:
        out = generate_full(req)
    data, filename, briefing, warnings = out["data"], out["filename"], out["briefing"], out["warnings"]
    (OUTPUT_DIR / filename).write_bytes(data)
    (OUTPUT_DIR / (filename[:-4] + ".brief.json")).write_text(json.dumps(out["brief"]), encoding="utf-8")
    # Keep the settings so the mission can be regenerated or tweaked later.
    (OUTPUT_DIR / (filename[:-4] + ".json")).write_text(json.dumps(body, indent=2), encoding="utf-8")
    (OUTPUT_DIR / (filename[:-4] + ".txt")).write_text(briefing, encoding="utf-8")
    return {"filename": filename, "url": f"/missions/{filename}", "size": len(data),
            "briefing": briefing, "warnings": warnings,
            "briefing_url": f"/briefing/{filename[:-4]}", **mission_store.mark_temporary(filename[:-4])}


def publish(filename, targets, extra_text=""):
    """targets: any of folder, sftp, discord. Returns {target: "ok" | error}."""
    path = OUTPUT_DIR / filename
    out = {}
    if "folder" in targets:
        out["folder"] = integrations.publish_folder(path) or "ok"
    if "sftp" in targets:
        out["sftp"] = integrations.publish_sftp(path) or "ok"
    if "discord" in targets:
        out["discord"] = discord_mission(filename, extra_text) or "ok"
    if "ok" in out.values():     # other people now have links to it
        mission_store.keep(filename[:-4])
    return out


def discord_mission(filename, extra_text=""):
    path = OUTPUT_DIR / filename
    settings = OUTPUT_DIR / (filename[:-4] + ".json")
    data = path.read_bytes()
    brief_path = OUTPUT_DIR / (filename[:-4] + ".txt")
    brief = brief_path.read_text(encoding="utf-8") if brief_path.exists() else ""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        pages = [n for n in z.namelist() if n.startswith("KNEEBOARD/") and n.endswith(".png")]
        page = z.read(min(pages)) if pages else None   # first flight's main page
    cfg = json.loads(settings.read_text(encoding="utf-8")) if settings.exists() else {}
    room = OUTPUT_DIR / (filename[:-4] + ".brief.json")
    saved = json.loads(room.read_text(encoding="utf-8")) if room.exists() else {}
    srs = saved["srs"] if "srs" in saved else integrations.srs()
    flights = ", ".join(f"{f.get('callsign')} {f.get('number')} ({f.get('aircraft')})"
                        for f in cfg.get("flights", []))
    text = (extra_text + "\n\n" if extra_text else "") + _tasking(brief)
    files = [(filename, data, "application/octet-stream")]
    if page:
        files.append(("kneeboard.png", page, "image/png"))
    pub = integrations.status()["public_url"]
    has_room = (OUTPUT_DIR / (filename[:-4] + ".brief.json")).exists()
    if pub and has_room:
        text += f"\n\nBriefing room: {pub}/briefing/{filename[:-4]}"
    return integrations.post_discord(
        cfg.get("title") or filename[:-4].replace("_", " "), text,
        url=f"{pub}/briefing/{filename[:-4]}" if pub and has_room else None,
        fields=[("Map", str(cfg.get("theater", "")), True),
                ("Mission", str(cfg.get("mission_type", "")), True),
                ("Difficulty", str(cfg.get("difficulty", "")), True),
                ("Flights", flights, False),
                *([("SRS", srs["address"], True)] if srs else [])],
        files=files, image_name="kneeboard.png" if page else None)


def _tasking(text):
    """The TASKING section of a stored briefing."""
    m = re.search(r"TASKING\n(.*?)\n\n", text, re.S)
    return m.group(1) if m else "New mission ready."


@app.post("/api/publish")
def api_publish():
    body = request.get_json(force=True) or {}
    name = body.get("filename", "")
    if not re.fullmatch(r"[\w\-.]+\.miz", name) or not (OUTPUT_DIR / name).exists():
        abort(404)
    return jsonify(publish(name, body.get("targets") or []))


# -------------------------------------------------------------------- events
def _event_path(eid):
    if not re.fullmatch(r"[\w\-]{6,32}", eid or ""):
        abort(404)
    return EVENTS_DIR / f"{eid}.json"


def _load_event(eid):
    path = _event_path(eid)
    if not path.exists():
        abort(404)
    return json.loads(path.read_text(encoding="utf-8"))


def _save_event(ev):
    _event_path(ev["id"]).write_text(json.dumps(ev, indent=2), encoding="utf-8")


def _seats(cfg):
    out = []
    for f in cfg.get("flights", []):
        for i in range(1, int(f.get("slots") or 1) + 1):
            out.append({"seat": f"{f.get('callsign')} {f.get('number')}-{i}",
                        "aircraft": f.get("aircraft"), "squadron": f.get("squadron", "")})
    return out


def _event_view(ev):
    seats = _seats(ev["config"])
    for s in seats:
        s["pilot"] = ev["claims"].get(s["seat"], "")
    return {**ev, "seats": seats}


@app.get("/api/events")
def list_events():
    evs = []
    for p in sorted(EVENTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        ev = _roll_over(json.loads(p.read_text(encoding="utf-8")))
        evs.append({"id": ev["id"], "title": ev["title"], "when": ev.get("when", ""),
                    "when_iso": ev.get("when_iso", ""), "repeat": ev.get("repeat", ""),
                    "claimed": len(ev["claims"]), "seats": len(_seats(ev["config"]))})
    return jsonify(evs)


@app.post("/api/events")
def create_event():
    body = request.get_json(force=True) or {}
    cfg = body.get("config") or {}
    try:
        MissionRequest.from_json(cfg)
    except (TypeError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    if not cfg.get("flights"):
        return jsonify({"error": "Add at least one flight first"}), 400
    repeat = body.get("repeat") if body.get("repeat") in REPEATS else ""
    when_iso = _iso(body.get("when_iso"))
    if repeat and not when_iso:
        return jsonify({"error": "Pick a date and time for a repeating event"}), 400
    ev = {"id": secrets.token_urlsafe(8), "title": (body.get("title") or "Mission night")[:80],
          "when": (body.get("when") or "")[:60], "when_iso": when_iso,
          "config": cfg, "claims": {}, "repeat": repeat, "post_discord": bool(body.get("discord")),
          "created": time.time(), "mission": None}
    _save_event(ev)
    if ev["post_discord"]:
        ev["discord"] = _announce_event(ev)
    return jsonify({"id": ev["id"], "url": f"/e/{ev['id']}", "discord": ev.get("discord")})


def _announce_event(ev):
    """Posts the sign-up link to Discord. Returns "ok", an error, or None without PUBLIC_URL."""
    pub = integrations.status()["public_url"]
    if not pub:
        return None
    link = f"{pub}/e/{ev['id']}"
    err = integrations.post_discord(
        f"Sign up: {ev['title']}", f"{_discord_time(ev)}\nPick your seat: {link}",
        fields=[("Seats", "\n".join(s["seat"] + f" ({s['aircraft']})"
                                    for s in _seats(ev["config"]))[:1000], False)],
        url=link)
    return err or "ok"


# Repeating events: the next occurrence is created once this one is generated or over.
REPEATS = {"weekly": datetime.timedelta(days=7)}
EVENT_OVER = datetime.timedelta(hours=3)


def _roll_over(ev):
    """Creates the next occurrence of a repeating event when it's due; returns the event."""
    if not ev.get("repeat") or ev.get("next_id") or not ev.get("when_iso"):
        return ev
    when = datetime.datetime.fromisoformat(ev["when_iso"])
    now = datetime.datetime.now(datetime.UTC)
    if not ev.get("mission") and now < when + EVENT_OVER:
        return ev
    with _locked(f"event-{ev['id']}"):
        ev = _load_event(ev["id"])          # another worker may have rolled it already
        if ev.get("next_id"):
            return ev
        step = REPEATS[ev["repeat"]]
        nxt_when = when + step
        while nxt_when + EVENT_OVER < now:  # skip weeks nobody opened the page
            nxt_when += step
        nxt = {"id": secrets.token_urlsafe(8), "title": ev["title"], "when": "",
               "when_iso": nxt_when.isoformat(), "config": ev["config"], "claims": {},
               "repeat": ev["repeat"], "post_discord": ev.get("post_discord", False),
               "prev_id": ev["id"], "created": time.time(), "mission": None}
        _save_event(nxt)
        ev["next_id"] = nxt["id"]
        _save_event(ev)
    if nxt["post_discord"]:
        nxt["discord"] = _announce_event(nxt)
        _save_event(nxt)
    return ev


def _iso(value):
    """A validated UTC ISO timestamp, or ""."""
    try:
        dt = datetime.datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.UTC)
    return dt.astimezone(datetime.UTC).isoformat()


def _discord_time(ev):
    """Discord renders <t:...> in every reader's own time zone."""
    if ev.get("when_iso"):
        unix = int(datetime.datetime.fromisoformat(ev["when_iso"]).timestamp())
        return f"<t:{unix}:F> (<t:{unix}:R>)"
    return ev.get("when", "")


@app.get("/api/events/<eid>")
def get_event(eid):
    return jsonify(_event_view(_roll_over(_load_event(eid))))


@app.post("/api/events/<eid>/claim")
def claim_seat(eid):
    ev = _load_event(eid)
    body = request.get_json(force=True) or {}
    seat, name = body.get("seat", ""), re.sub(r"[^\w \-.']", "", body.get("name", ""))[:24].strip()
    if seat not in [s["seat"] for s in _seats(ev["config"])]:
        return jsonify({"error": "No such seat"}), 400
    holder = ev["claims"].get(seat)
    if not name:  # release
        if holder and holder.lower() != (body.get("me") or "").lower():
            return jsonify({"error": f"{holder} has that seat"}), 409
        ev["claims"].pop(seat, None)
    else:
        if holder and holder.lower() != name.lower():
            return jsonify({"error": f"{holder} already took {seat}"}), 409
        ev["claims"] = {k: v for k, v in ev["claims"].items() if v.lower() != name.lower()}
        ev["claims"][seat] = name
    _save_event(ev)
    return jsonify(_event_view(ev))


@app.post("/api/events/<eid>/generate")
def event_generate(eid):
    ev = _load_event(eid)
    cfg = json.loads(json.dumps(ev["config"]))
    for f in cfg.get("flights", []):
        f["pilots"] = [ev["claims"].get(f"{f.get('callsign')} {f.get('number')}-{i}", "")
                       for i in range(1, int(f.get("slots") or 1) + 1)]
    cfg["title"] = cfg.get("title") or ev["title"]
    try:
        result = build_and_store(cfg)
    except (MissionError, TypeError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    ev["mission"] = {"filename": result["filename"], "url": result["url"],
                     "briefing_url": result["briefing_url"]}
    _save_event(ev)
    result.update(mission_store.keep(result["filename"][:-4]))   # the sign-up page links to it
    ev = _roll_over(ev)
    targets = (request.get_json(silent=True) or {}).get("publish") or []
    result["published"] = publish(result["filename"], targets,
                                  extra_text=f"{ev['title']} {_discord_time(ev)}".strip())
    return jsonify(result)


@app.delete("/api/events/<eid>")
def delete_event(eid):
    _event_path(eid).unlink(missing_ok=True)
    return jsonify({"deleted": True})


# -------------------------------------------------------- DCS server reports
REPORTS = OUTPUT_DIR / "reports.json"
HOOK = paths.ROOT / "dcs-hook" / "dmm_reporter.lua"


def _reports():
    try:
        return json.loads(REPORTS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


@app.post("/api/reports")
def add_report():
    body = request.get_json(force=True, silent=True) or {}
    mission = str(body.get("mission", ""))[:200]
    if not mission.endswith(".miz"):
        return jsonify({"error": "expected a .miz name"}), 400
    errors = [str(e)[:400] for e in (body.get("errors") or [])][:25]
    reports = _reports()
    reports[mission] = {"errors": errors, "at": time.time()}
    REPORTS.write_text(json.dumps(dict(list(reports.items())[-200:]), indent=1), encoding="utf-8")
    return jsonify({"ok": True})


@app.get("/dcs-hook.lua")
def dcs_hook():
    url = integrations.status()["public_url"] or request.host_url.rstrip("/")
    text = HOOK.read_text(encoding="utf-8").replace("__APP_URL__", url)
    return text, 200, {"Content-Type": "text/plain; charset=utf-8",
                       "Content-Disposition": "attachment; filename=dmm_reporter.lua"}


# ------------------------------------------------------------- briefing room
def _stem(stem):
    if not re.fullmatch(r"[\w\-.]+", stem or "") or not (OUTPUT_DIR / f"{stem}.miz").exists():
        abort(404)
    return stem


@app.get("/briefing/<stem>")
def briefing_room(stem):
    _stem(stem)
    if not (OUTPUT_DIR / f"{stem}.brief.json").exists():
        abort(404)
    return render_template("briefing.html", stem=stem)


@app.get("/api/missions/<stem>/brief")
def mission_brief(stem):
    path = OUTPUT_DIR / f"{_stem(stem)}.brief.json"
    if not path.exists():
        abort(404)
    brief = json.loads(path.read_text(encoding="utf-8"))
    brief["report"] = _reports().get(f"{stem}.miz")
    brief["download"] = f"/missions/{stem}.miz"
    if "srs" not in brief:              # missions generated before SRS was per mission
        brief["srs"] = integrations.srs()
    return jsonify(brief)


@app.get("/missions/<stem>/comms.txt")
def comm_card(stem):
    """Every frequency for the mission on one plain-text card (second screen, SRS users)."""
    path = OUTPUT_DIR / f"{_stem(stem)}.brief.json"
    if not path.exists():
        abort(404)
    brief = json.loads(path.read_text(encoding="utf-8"))
    srs = brief["srs"] if "srs" in brief else integrations.srs()
    lines = [f"COMM CARD - {brief.get('title') or stem.replace('_', ' ')}", ""]
    if srs:
        lines += [f"SRS server: {srs['address']}" + (f"  ({srs['note']})" if srs["note"] else ""), ""]
    lines += ["SUPPORT", *[f"  {s}" for s in brief.get("support") or ["None."]], ""]
    lines += ["FLIGHTS"]
    for f in brief.get("flights", []):
        lines.append(f"  {f['name']} ({f['aircraft']})")
        lines += [f"    {p}" for p in f.get("presets") or ["No preset radios"]]
    lines += ["", "HOME FIELD", f"  {brief['home']['card']}", "", "Guard: 243.000 UHF / 121.500 VHF"]
    return "\n".join(lines) + "\n", 200, {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": f'inline; filename="{stem}_comms.txt"'}


# ------------------------------------------------------------------- debrief
def _debrief_path(stem):
    return OUTPUT_DIR / f"{stem}.debrief.json"


@app.post("/api/debrief")
def add_debrief():
    """Game events and objective flags from the DCS server hook."""
    body = request.get_json(force=True, silent=True) or {}
    mission = str(body.get("mission", ""))[:200]
    stem = mission[:-4] if mission.endswith(".miz") else ""
    if not re.fullmatch(r"[\w\-.]+", stem) or not (OUTPUT_DIR / mission).exists():
        return jsonify({"error": "unknown mission"}), 404
    with _locked(stem):
        path = _debrief_path(stem)
        record = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        record = debrief.merge(record, body)
        path.write_text(json.dumps(record, indent=1), encoding="utf-8")
    return jsonify({"ok": True, "events": len(record["events"])})


@app.get("/api/missions/<stem>/debrief")
def mission_debrief(stem):
    path = _debrief_path(_stem(stem))
    brief_path = OUTPUT_DIR / f"{stem}.brief.json"
    if not path.exists() or not brief_path.exists():
        return jsonify({"debrief": None})
    brief, record = (json.loads(p.read_text(encoding="utf-8")) for p in (brief_path, path))
    return jsonify({"debrief": debrief.summary(brief, record)})


# -------------------------------------------------------------------- roster
_stem_locks = collections.defaultdict(threading.Lock)


@contextlib.contextmanager
def _locked(stem):
    """Serialises roster and debrief edits: across threads, and across gunicorn's worker
    processes with a lock file (not needed on Windows, where waitress runs one process)."""
    with _stem_locks[stem]:
        if fcntl is None:
            yield
            return
        with open(OUTPUT_DIR / f".{stem}.lock", "w") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)


def _roster_seats(brief):
    seats = []
    for f in brief["flights"]:
        for i in range(1, f["seats"] + f["ai"] + 1):
            seats.append({"seat": f"{f['name']}-{i}", "flight": f["name"],
                          "aircraft": f["aircraft"], "ai": i > f["seats"]})
    return seats


def _load_roster(stem, brief):
    path = OUTPUT_DIR / f"{stem}.roster.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    claims = {}  # seed from pilot names baked in at generation (sign-up pages)
    for f in brief["flights"]:
        for entry in f.get("pilots", []):
            num, _, name = entry.partition(" ")
            if name:
                claims[f"{f['name'].rsplit(' ', 1)[0]} {num}"] = name
    return claims


def _roster_view(stem, brief, claims):
    seats = _roster_seats(brief)
    for st in seats:
        st["pilot"] = "" if st["ai"] else claims.get(st["seat"], "")
    return {"seats": seats}


def _apply_names_to_miz(stem, claims, seats):
    """Rewrites slot names in the .miz in place: "Viper 1-2" -> "Viper 1-2 (Mitsu)"."""
    path = OUTPUT_DIR / f"{stem}.miz"
    with zipfile.ZipFile(path) as z:
        entries = [(i, z.read(i.filename)) for i in z.infolist()]
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for info, data in entries:
            if info.filename == "mission":
                text = data.decode("utf-8")
                for st in seats:
                    if st["ai"]:
                        continue
                    pattern = r'\["name"\]="' + re.escape(st["seat"]) + r'(?: \([^"()]*\))?"'
                    pilot = claims.get(st["seat"])
                    new = f'["name"]="{st["seat"]}' + (f" ({pilot})" if pilot else "") + '"'
                    text = re.sub(pattern, lambda _m, new=new: new, text)
                data = text.encode("utf-8")
            z.writestr(info, data)
    tmp = path.with_suffix(".miz.tmp")
    tmp.write_bytes(out.getvalue())
    os.replace(tmp, path)


@app.get("/api/missions/<stem>/roster")
def get_roster(stem):
    path = OUTPUT_DIR / f"{_stem(stem)}.brief.json"
    if not path.exists():
        abort(404)
    brief = json.loads(path.read_text(encoding="utf-8"))
    return jsonify(_roster_view(stem, brief, _load_roster(stem, brief)))


@app.post("/api/missions/<stem>/roster")
def claim_roster_seat(stem):
    path = OUTPUT_DIR / f"{_stem(stem)}.brief.json"
    if not path.exists():
        abort(404)
    brief = json.loads(path.read_text(encoding="utf-8"))
    body = request.get_json(force=True) or {}
    seat = body.get("seat", "")
    name = re.sub(r"[^\w \-.']", "", body.get("name", ""))[:24].strip()
    me = (body.get("me") or "").strip().lower()
    seats = _roster_seats(brief)
    if seat not in [st["seat"] for st in seats if not st["ai"]]:
        return jsonify({"error": "No such player seat"}), 400
    with _locked(stem):
        claims = _load_roster(stem, brief)
        holder = claims.get(seat)
        if not name:  # leaving the seat
            if holder and holder.lower() != me:
                return jsonify({"error": f"{holder} has that seat"}), 409
            claims.pop(seat, None)
        else:
            if holder and holder.lower() != name.lower():
                return jsonify({"error": f"{holder} already took {seat}"}), 409
            claims = {k: v for k, v in claims.items() if v.lower() != name.lower()}
            claims[seat] = name
        (OUTPUT_DIR / f"{stem}.roster.json").write_text(json.dumps(claims, indent=1), encoding="utf-8")
        _apply_names_to_miz(stem, claims, seats)
    return jsonify(_roster_view(stem, brief, claims))


@app.get("/missions/<stem>/kneeboard/<page>.png")
def kneeboard_page(stem, page):
    """page is the flight number, optionally with a page suffix: "2" or "2_route"."""
    if not re.fullmatch(r"\d{1,2}(_route)?", page):
        abort(404)
    with zipfile.ZipFile(OUTPUT_DIR / f"{_stem(stem)}.miz") as z:
        names = [x for x in z.namelist() if x.startswith("KNEEBOARD/")
                 and x.endswith(f"/kneeboard_{page}.png")]
        if not names:
            abort(404)
        data = z.read(names[0])
    return data, 200, {"Content-Type": "image/png", "Cache-Control": "max-age=86400"}


@app.get("/missions/<stem>/pack.pdf")
def print_pack(stem):
    """The briefing plus every kneeboard page as one PDF, to print or put on a tablet."""
    from PIL import Image

    from . import kneeboard
    _stem(stem)
    brief_path, text_path = OUTPUT_DIR / f"{stem}.brief.json", OUTPUT_DIR / f"{stem}.txt"
    title = json.loads(brief_path.read_text(encoding="utf-8")).get("title", stem) if brief_path.exists() else stem
    text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
    pages = kneeboard.text_pages(title, "Mission briefing", text) if text else []
    with zipfile.ZipFile(OUTPUT_DIR / f"{stem}.miz") as z:
        names = sorted(n for n in z.namelist() if n.startswith("KNEEBOARD/") and n.endswith(".png"))
        pages += [Image.open(io.BytesIO(z.read(n))).convert("RGB") for n in names]
    if not pages:
        abort(404)
    out = io.BytesIO()
    pages[0].save(out, "PDF", save_all=True, append_images=pages[1:], resolution=96)
    return out.getvalue(), 200, {"Content-Type": "application/pdf",
                                 "Content-Disposition": f'inline; filename="{stem}.pdf"'}


@app.get("/drawings/<path:name>")
def drawing(name):
    from .threatdb import DRAWINGS_DIR
    if not re.fullmatch(r"[\w\-.]+\.(svg|png|jpg|jpeg|gif)", name):
        abort(404)
    resp = send_from_directory(DRAWINGS_DIR, name, max_age=86400)
    # Third-party SVGs: never let them run script if opened directly.
    resp.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.get("/e/<eid>")
def event_page(eid):
    _load_event(eid)
    return render_template("event.html", eid=eid)


@app.get("/api/missions")
def list_missions():
    mission_store.cleanup()
    files = sorted(OUTPUT_DIR.glob("*.miz"), key=lambda p: p.stat().st_mtime, reverse=True)
    reports = _reports()
    return jsonify([{"filename": p.name, "url": f"/missions/{p.name}",
                     "size": p.stat().st_size, "stem": p.stem, **mission_store.status(p.stem),
                     "settings": (f"/api/missions/{p.stem}/settings"
                                  if p.with_suffix(".json").exists() else None),
                     "report": reports.get(p.name),
                     "briefing": (f"/briefing/{p.stem}"
                                  if (OUTPUT_DIR / f"{p.stem}.brief.json").exists() else None)}
                    for p in files[:25]])


@app.post("/api/missions/<stem>/keep")
def keep_mission(stem):
    """{"keep": true} keeps a mission for good; false makes it temporary again."""
    keep = (request.get_json(silent=True) or {}).get("keep", True)
    return jsonify(mission_store.keep(_stem(stem), bool(keep)))


@app.delete("/api/missions/<stem>")
def delete_mission(stem):
    if not mission_store.delete(_stem(stem)):
        return jsonify({"error": "A file is still in use (being downloaded?). Try again in a moment."}), 409
    return jsonify({"deleted": True})


@app.get("/api/missions/<stem>/settings")
def mission_settings(stem):
    if not re.fullmatch(r"[\w\-.]+", stem):
        abort(404)
    path = OUTPUT_DIR / f"{stem}.json"
    if not path.exists():
        abort(404)
    return jsonify(json.loads(path.read_text(encoding="utf-8")))


@app.get("/missions/<name>")
def download(name):
    if not re.fullmatch(r"[\w\-.]+\.miz", name):
        abort(404)
    return send_from_directory(OUTPUT_DIR, name, as_attachment=True)
