"""Debrief: what happened in a flown mission, from the DCS server hook's reports.

The hook (dcs-hook/dmm_reporter.lua) posts game events (kills, losses, take-offs,
landings) and the mission's objective flags. merge() folds a post into the stored
record; summary() turns the record plus the mission's brief into what the
Briefing Room's Debrief tab shows.
"""
import time

MAX_EVENTS = 500
EVENT_TYPES = {"kill", "crash", "eject", "pilot_death", "takeoff", "landing", "friendly_fire", "mission_end"}
LOSSES = {"crash": "crashed", "eject": "ejected", "pilot_death": "killed"}
TEXT_FIELDS = ("player", "unit", "killer_type", "killer_side", "victim_player", "victim_unit", "victim_type",
               "victim_side", "weapon", "place", "winner", "text")


def _clean_event(e):
    if not isinstance(e, dict) or e.get("type") not in EVENT_TYPES:
        return None
    out = {"type": e["type"], "t": max(0, int(e.get("t") or 0))}
    for k in TEXT_FIELDS:
        if e.get(k) not in (None, ""):
            out[k] = str(e[k])[:80]
    return out


def merge(record, body):
    """Fold one hook post into the stored record. Posts carry the events from index
    `from` onward, so a retried post replaces rather than duplicates."""
    record = dict(record or {})
    events = list(record.get("events", []))
    start = max(0, min(int(body.get("from") or 0), len(events)))
    fresh = [e for e in map(_clean_event, body.get("events") or []) if e]
    events = (events[:start] + fresh)[:MAX_EVENTS]
    flags = dict(record.get("flags", {}))
    for k, v in (body.get("flags") or {}).items():
        if str(k).isdigit():
            try:
                flags[str(k)] = int(v)
            except (TypeError, ValueError):
                continue
    record.update(events=events, flags=flags, updated=time.time(),
                  model_time=int(body.get("time") or 0),
                  final=bool(record.get("final") or body.get("final")))
    return record


def _clock(start, seconds):
    """'HH:MM' local time, seconds after a 'HH:MM' mission start."""
    try:
        hh, mm = map(int, start.split(":"))
    except (AttributeError, ValueError):
        return f"+{seconds // 60:d} min"
    t = (hh * 3600 + mm * 60 + seconds) % 86400
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}"


def _who(e, prefix=""):
    return e.get(f"{prefix}player") or e.get(f"{prefix}unit") or ""


def _line(e):
    who = _who(e) or "AI"
    if e["type"] == "kill":
        victim = _who(e, "victim_") or e.get("victim_type", "a target")
        if e.get("victim_player"):
            victim = f"{victim} ({e.get('victim_type', '')})".replace(" ()", "")
        weapon = f" with {e['weapon']}" if e.get("weapon") else ""
        return f"{_who(e) or e.get('killer_type', 'AI')} killed {victim}{weapon}"
    if e["type"] in LOSSES:
        return f"{who} {LOSSES[e['type']]}"
    if e["type"] == "takeoff":
        return f"{who} took off" + (f" from {e['place']}" if e.get("place") else "")
    if e["type"] == "landing":
        return f"{who} landed" + (f" at {e['place']}" if e.get("place") else "")
    if e["type"] == "friendly_fire":
        weapon = f" with {e['weapon']}" if e.get("weapon") else ""
        return f"{who} hit friendly {_who(e, 'victim_') or 'unit'}{weapon}"
    return "Mission ended" + (f": {e['text']}" if e.get("text") else "")


def summary(brief, record):
    """Objectives met, a row per pilot, and the timeline."""
    if not record:
        return None
    flags = record.get("flags", {})
    objectives = [{"name": o["name"], "what": o["what"],
                   "done": None if o.get("flag") is None or str(o["flag"]) not in flags
                   else flags[str(o["flag"])] > 0}
                  for o in brief.get("objectives", [])]
    all_flag = brief.get("debrief_flag")
    all_done = (flags.get(str(all_flag), 0) > 0) if all_flag is not None and str(all_flag) in flags else None

    pilots = {}

    def row(name):
        return pilots.setdefault(name, {"name": name, "kills": 0, "victims": [], "losses": [],
                                        "sorties": 0, "landings": [], "friendly_fire": 0})

    for e in record.get("events", []):
        name = _who(e)
        if not name:
            continue
        r = row(name)
        if e["type"] == "kill":
            r["kills"] += 1
            r["victims"].append(e.get("victim_type") or "target")
        elif e["type"] in LOSSES:
            r["losses"].append(LOSSES[e["type"]])
        elif e["type"] == "takeoff":
            r["sorties"] += 1
        elif e["type"] == "landing":
            r["landings"].append(e.get("place") or "landed")
        elif e["type"] == "friendly_fire":
            r["friendly_fire"] += 1
    start = brief.get("meta", {}).get("start")
    return {
        "final": record.get("final", False), "updated": record.get("updated"),
        "flown_minutes": record.get("model_time", 0) // 60,
        "all_done": all_done, "objectives": objectives,
        "pilots": sorted(pilots.values(), key=lambda p: (-p["kills"], p["name"])),
        "timeline": [{"time": _clock(start, e["t"]), "type": e["type"], "text": _line(e)}
                     for e in record.get("events", [])],
    }
