"""Tells you when a newer release is out (the Windows app built by CI).

The release build writes app/build_info.py with the GitHub repository it was built from;
without it (Docker, running from source) there's nothing to check. At most once a day it
asks GitHub for the latest release, in the background: the request carries nothing but the
app's version in the User-Agent. Off with UPDATE_CHECK=off (a switch on the Settings page).
"""
import json
import logging
import os
import re
import threading
import time
import urllib.request

from . import __version__

try:
    from .build_info import REPO
except ImportError:
    REPO = ""

CHECK_EVERY = 24 * 3600
log = logging.getLogger(__name__)
_state = {"checked": 0.0, "latest": None}
_lock = threading.Lock()


def enabled():
    return bool(REPO) and os.environ.get("UPDATE_CHECK", "on").lower() != "off"


def version_tuple(text):
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(text or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def _fetch():
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": f"DCSMissionMaker/{__version__}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)
    version, url = version_tuple(data.get("tag_name")), str(data.get("html_url") or "")
    if not version or not url.startswith(f"https://github.com/{REPO}/releases/"):
        raise ValueError(f"unexpected release data: {data.get('tag_name')!r} {url!r}")
    return {"version": ".".join(map(str, version)), "url": url}


def _check():
    try:
        _state["latest"] = _fetch()
    except (OSError, ValueError) as e:
        log.info("update check failed: %s", e)


def status():
    """{"enabled", "current", "available": {"version", "url"} or None}; starts a check if due."""
    with _lock:
        due = enabled() and time.time() - _state["checked"] >= CHECK_EVERY
        if due:
            _state["checked"] = time.time()
    if due:
        threading.Thread(target=_check, name="update-check", daemon=True).start()
    latest = _state["latest"]
    newer = latest and version_tuple(latest["version"]) > version_tuple(__version__)
    return {"enabled": enabled(), "current": __version__, "available": latest if enabled() and newer else None}
