"""Livery choices per aircraft type, for the builder's livery dropdown.

Two sources, merged:
  * data/liveries.json: liveries DCS Retribution's squadrons use (stock DCS liveries,
    labelled with the squadron), built by tools/build_liveries.py.
  * OUTPUT_DIR/installed_liveries.json: what the DCS server hook found in the server's
    DCS install and Saved Games\\Liveries, with each livery's in-game name.
Livery folder names are case-insensitive in DCS, so matching is on the lower-cased id.
"""
import json
import re
from pathlib import Path

from . import paths

BUNDLED = Path(__file__).resolve().parent / "data" / "liveries.json"
INSTALLED = paths.output_dir() / "installed_liveries.json"
VALID_ID = re.compile(r"[^\x00-\x1f\"\\\\]{1,80}")


def _load(path, key):
    try:
        return json.loads(path.read_text(encoding="utf-8")).get(key, {})
    except (OSError, ValueError):
        return {}


def installed_info():
    """When the server last reported, and how many types/liveries; None if never."""
    try:
        data = json.loads(INSTALLED.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    types = data.get("types", {})
    return {"at": data.get("at"), "types": len(types), "liveries": sum(len(v) for v in types.values())}


def options(type_id):
    """[{"id", "label", "installed"}] for one aircraft type: server-reported liveries first
    (by in-game name), then squadron liveries the server didn't report."""
    key = type_id.lower()
    installed = {k.lower(): v for k, v in _load(INSTALLED, "types").items()}.get(key, [])
    bundled = {k.lower(): v for k, v in _load(BUNDLED, "liveries").items()}.get(key, [])
    squads = {e["id"].lower(): e for e in bundled}
    out, seen = [], set()
    for e in sorted(installed, key=lambda e: (e.get("name") or e["id"]).lower()):
        lid = e["id"]
        sq = squads.get(lid.lower())
        label = e.get("name") or lid
        if sq and sq["squadrons"]:
            label += f" · {sq['squadrons'][0]}"
        out.append({"id": lid, "label": label, "installed": True,
                    "squadron": sq["squadrons"][0] if sq and sq["squadrons"] else ""})
        seen.add(lid.lower())
    for e in bundled:
        if e["id"].lower() in seen:
            continue
        name = e["squadrons"][0] if e["squadrons"] else e["id"]
        country = f" ({', '.join(e['countries'])})" if e["countries"] else ""
        out.append({"id": e["id"], "label": f"{name}{country}", "installed": False,
                    "squadron": e["squadrons"][0] if e["squadrons"] else ""})
    return out


def known(type_id, livery_id):
    return any(o["id"].lower() == livery_id.lower() for o in options(type_id))


def save_installed(body, now):
    """Stores the hook's scan: {"types": {type_id: [{"id", "name"}]}}; returns counts."""
    types = {}
    for type_id, items in (body.get("types") or {}).items():
        if not isinstance(items, list) or not VALID_ID.fullmatch(str(type_id)):
            continue
        clean = []
        for e in items[:400]:
            lid = str((e or {}).get("id", "")) if isinstance(e, dict) else ""
            if VALID_ID.fullmatch(lid):
                clean.append({"id": lid, "name": str(e.get("name") or "")[:80]})
        if clean:
            types[str(type_id)] = clean
    INSTALLED.write_text(json.dumps({"at": now, "types": types}), encoding="utf-8")
    return {"types": len(types), "liveries": sum(len(v) for v in types.values())}
