"""Which generated missions stay on disk.

A new mission is temporary: its download and Briefing Room work straight away, and
it's deleted MISSION_TTL_HOURS later (default 24) unless someone keeps it. Missions
generated for a sign-up event, posted to Discord or published to a server are kept
automatically, since other people get links to them.

State lives in <stem>.meta.json: {"created", "expires"} with expires = null once
kept. Missions from before this existed have no meta file and count as kept.
"""
import json
import os
import time

from . import paths

OUTPUT_DIR = paths.output_dir()
CLEANUP_EVERY_S = 300
_last_cleanup = [0.0]


def ttl_seconds():
    try:
        return max(0.25, float(os.environ.get("MISSION_TTL_HOURS", "24"))) * 3600
    except ValueError:
        return 24 * 3600


def _meta_path(stem):
    return OUTPUT_DIR / f"{stem}.meta.json"


def status(stem):
    """{"kept": bool, "expires": unix time or None}."""
    try:
        meta = json.loads(_meta_path(stem).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"kept": True, "expires": None}          # older missions: kept
    return {"kept": meta.get("expires") is None, "expires": meta.get("expires")}


def mark_temporary(stem):
    now = time.time()
    _meta_path(stem).write_text(json.dumps({"created": now, "expires": now + ttl_seconds()}), encoding="utf-8")
    return status(stem)


def keep(stem, kept=True):
    """Keep a mission for good, or make it temporary again (expires a full TTL from now)."""
    now = time.time()
    try:
        meta = json.loads(_meta_path(stem).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        meta = {"created": now}
    meta["expires"] = None if kept else now + ttl_seconds()
    _meta_path(stem).write_text(json.dumps(meta), encoding="utf-8")
    return status(stem)


def delete(stem):
    """Removes the mission and everything stored with it (briefing, roster, debrief...).
    On Windows a file that's being downloaded can't be deleted; the meta file goes last,
    so a mission that couldn't be fully removed is tried again at the next cleanup."""
    meta = _meta_path(stem)
    for path in [*OUTPUT_DIR.glob(f"{stem}.*"), OUTPUT_DIR / f".{stem}.lock"]:
        if path != meta:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                return False
    meta.unlink(missing_ok=True)
    return True


def cleanup(force=False):
    """Deletes temporary missions past their time. Cheap; runs at most every few minutes."""
    now = time.time()
    if not force and now - _last_cleanup[0] < CLEANUP_EVERY_S:
        return []
    _last_cleanup[0] = now
    gone = []
    for meta_path in OUTPUT_DIR.glob("*.meta.json"):
        stem = meta_path.name[: -len(".meta.json")]
        expires = status(stem)["expires"]
        if expires is not None and expires < now and delete(stem):
            gone.append(stem)
    return gone
