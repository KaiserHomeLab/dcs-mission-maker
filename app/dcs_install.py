"""Which DCS maps are installed on this PC (the Windows app usually runs next to the DCS server),
and whether the app's server hook is installed there.

Every installed map is a folder in <DCS install>\\Mods\\terrains named like the theatre name
missions use. The install is DCS_INSTALL_DIR (Settings page) or the first one found in the
usual places, server installs first. When one is found and MAPS_FILTER isn't "off", the
builder offers only the installed maps and generating a mission on another one is refused.
Docker, or a PC without DCS: nothing is found and every map stays available.
"""
import os
import time
from pathlib import Path

# Theater key (app/theaters.py) -> its folder in Mods\terrains, which is also the mission's
# theatre name (pydcs miz_theatre_name; tests/api.py checks the two agree).
DCS_NAMES = {
    "caucasus": "Caucasus", "persiangulf": "PersianGulf", "syria": "Syria", "nevada": "Nevada",
    "marianas": "MarianaIslands", "sinai": "SinaiMap", "kola": "Kola", "falklands": "Falklands",
    "germany": "GermanyCW", "normandy": "Normandy", "channel": "TheChannel",
}
FOLDERS = ["DCS World Server", "DCS World OpenBeta Server", "DCS World", "DCS World OpenBeta"]
CACHE_S = 60
_cache = {"at": 0.0, "key": None, "value": None}


def candidates():
    """Where DCS usually is: Program Files\\Eagle Dynamics on any drive, Steam, or a drive's root."""
    roots = [os.environ.get("PROGRAMFILES", r"C:\Program Files")]
    roots += [f"{d}:\\" for d in "CDEFG"]
    out = []
    for root in roots:
        for name in FOLDERS:
            out += [Path(root) / "Eagle Dynamics" / name, Path(root) / name]
    steam = Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Steam"
    out.append(steam / "steamapps" / "common" / "DCSWorld")
    return list(dict.fromkeys(out))


def _terrains_dir(install):
    return Path(install) / "Mods" / "terrains"


def found_installs():
    """DCS installs on this PC (folders that have Mods\\terrains), server installs first."""
    if os.name != "nt":
        return []
    found = []
    for p in candidates():
        try:
            if _terrains_dir(p).is_dir():
                found.append(str(p))
        except OSError:
            continue
    return found


def install_dir():
    """The DCS install whose maps count: the setting, or the first one found; None if none."""
    chosen = os.environ.get("DCS_INSTALL_DIR", "").strip()
    if chosen:
        return chosen if _terrains_dir(chosen).is_dir() else None
    found = found_installs()
    return found[0] if found else None


def installed_maps():
    """{"install", "theaters": [keys], "filter": bool}, or None when no DCS install was found.
    Cached for a minute; changes of the setting apply at once."""
    key = (os.environ.get("DCS_INSTALL_DIR", ""), os.environ.get("MAPS_FILTER", ""))
    now = time.time()
    if _cache["key"] == key and now - _cache["at"] < CACHE_S:
        return _cache["value"]
    install, value = install_dir(), None
    if install:
        try:
            folders = {p.name.lower() for p in _terrains_dir(install).iterdir() if p.is_dir()}
        except OSError:
            folders = set()
        theaters = [k for k, name in DCS_NAMES.items() if name.lower() in folders]
        # No known map at all means the wrong folder, not "fly nowhere": don't filter then.
        value = {"install": install, "theaters": theaters,
                 "filter": bool(theaters) and os.environ.get("MAPS_FILTER", "on").lower() != "off"}
    _cache.update(at=now, key=key, value=value)
    return value


def hook_files():
    """The app's hook (dcs-hook/dmm_reporter.lua) in this user's Saved Games\\DCS*\\Scripts\\Hooks
    folders: DCS.server, DCS.openbeta and so on."""
    if os.name != "nt":
        return []
    saved = Path(os.environ.get("USERPROFILE") or Path.home()) / "Saved Games"
    try:
        return [str(p) for p in saved.glob("DCS*/Scripts/Hooks/dmm_reporter.lua")]
    except OSError:
        return []


def allowed(theater_key):
    """False only when the map filter is on and that map isn't installed."""
    info = installed_maps()
    return not (info and info["filter"]) or theater_key in info["theaters"]
