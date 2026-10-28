"""Third-party mission scripts.

Bundled scripts are downloaded at image build time (see Dockerfile) into
VENDOR_DIR. Anything you drop into CUSTOM_DIR (the ./scripts volume) shows up
in the UI as a custom script.
"""
from . import paths

VENDOR_DIR = paths.vendor_dir()
CUSTOM_DIR = paths.scripts_dir()

# id -> metadata. "file" is relative to VENDOR_DIR; "needs" are loaded first.
CATALOG = {
    "mist": {"name": "MIST", "file": "mist.lua", "needs": [],
             "desc": "Mission Scripting Tools library. Required by Skynet and EWRS; "
                     "tick it if a custom script needs MIST."},
    "moose": {"name": "MOOSE", "file": "Moose_.lua", "needs": [],
              "desc": "MOOSE framework. Required by CTLD and CSAR; tick it if a custom "
                      "script needs MOOSE."},
    "skynet": {"name": "Skynet IADS", "file": "skynet-iads-compiled.lua", "needs": ["mist"],
               "desc": "Networks enemy SAM sites and early-warning radars into an IADS: "
                       "radars go dark, react to HARMs and hand off targets."},
    "ctld": {"name": "CTLD (MOOSE)", "file": None, "needs": ["moose"],
             "desc": "Troop and vehicle-crate transport for helicopter flights. Load at "
                     "the blue smoke at your home base via the F10 menu.",
             "helicopters": True},
    "csar": {"name": "CSAR (MOOSE)", "file": None, "needs": ["moose"],
             "desc": "Downed pilots eject and wait for rescue; helicopter flights pick "
                     "them up and bring them to the MASH at home base.",
             "helicopters": True},
    "hound": {"name": "Hound ELINT", "file": "HoundElint.lua", "needs": [],
              "desc": "A friendly ELINT aircraft triangulates enemy radars and marks "
                      "them on the F10 map."},
    "ewrs": {"name": "EWRS", "file": "EWRS.lua", "needs": ["mist"],
             "desc": "Early Warning Radar Script: BRA calls on enemy aircraft from "
                     "friendly radars and AWACS (F10 menu)."},
}
ORDER = ["mist", "moose", "skynet", "hound", "ewrs", "ctld", "csar"]


def available():
    out = []
    for sid in ORDER:
        meta = CATALOG[sid]
        ok = meta["file"] is None or (VENDOR_DIR / meta["file"]).exists()
        out.append({"id": sid, "name": meta["name"], "desc": meta["desc"],
                    "needs": meta["needs"], "available": ok,
                    "helicopters": meta.get("helicopters", False)})
    if CUSTOM_DIR.is_dir():
        for p in sorted(CUSTOM_DIR.glob("*.lua")):
            out.append({"id": f"custom:{p.name}", "name": p.name, "custom": True,
                        "desc": "Your script from the scripts folder. Loaded after the "
                                "built-in ones.", "needs": [], "available": True})
    return out


def resolve(selected):
    """Expand dependencies; returns ordered ids. Raises ValueError on bad ids."""
    chosen = set()
    for sid in selected:
        if sid.startswith("custom:"):
            name = sid.split(":", 1)[1]
            if "/" in name or "\\" in name or not (CUSTOM_DIR / name).is_file():
                raise ValueError(f"Custom script '{name}' not found")
            chosen.add(sid)
            continue
        if sid not in CATALOG:
            raise ValueError(f"Unknown script '{sid}'")
        meta = CATALOG[sid]
        if meta["file"] and not (VENDOR_DIR / meta["file"]).exists():
            raise ValueError(f"{meta['name']} isn't installed in this image")
        chosen.add(sid)
        chosen.update(meta["needs"])
    ordered = [s for s in ORDER if s in chosen]
    ordered += sorted(s for s in chosen if s.startswith("custom:"))
    return ordered


def path_for(sid):
    if sid.startswith("custom:"):
        return CUSTOM_DIR / sid.split(":", 1)[1]
    f = CATALOG[sid]["file"]
    return VENDOR_DIR / f if f else None


# ------------------------------------------------------------- config glue
def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lua_list(items):
    return "{" + ", ".join(lua_str(i) for i in items) + "}"


def skynet_glue():
    return """-- Skynet IADS: enemy SAM sites (group names starting "SAM") and EW radars ("EW")
enemyIADS = SkynetIADS:create('ENEMY IADS')
enemyIADS:addSAMSitesByPrefix('SAM')
enemyIADS:addEarlyWarningRadarsByPrefix('EW')
enemyIADS:activate()
"""


def ctld_glue(heli_groups, pickup_zone, troops_template, crate_template):
    return f"""-- MOOSE CTLD for the helicopter flights
local ctld = CTLD:New(coalition.side.BLUE, {lua_list(heli_groups)}, "Logistics")
ctld.useprefix = true
ctld.enableLoadSave = false
ctld:AddTroopsCargo("Infantry squad", {lua_list([troops_template])}, CTLD_CARGO.Enum.TROOPS, 6)
ctld:AddCratesCargo("Humvee", {lua_list([crate_template])}, CTLD_CARGO.Enum.VEHICLE, 1)
ctld:AddCTLDZone({lua_str(pickup_zone)}, CTLD.CargoZoneType.LOAD, SMOKECOLOR.Blue, true, true)
ctld:__Start(5)
"""


def csar_glue(heli_groups, pilot_template, mash_prefix, survivor_zone=None):
    return f"""-- MOOSE CSAR for the helicopter flights
local csar = CSAR:New(coalition.side.BLUE, {lua_str(pilot_template)}, "Rescue")
csar.csarPrefix = {lua_list(heli_groups)}
csar.mashprefix = {lua_list([mash_prefix])}
csar.enableForAI = false
csar.allowFARPRescue = true
csar:__Start(5)
""" + (f"""-- The mission's downed pilot
timer.scheduleFunction(function()
  csar:SpawnCSARAtZone({lua_str(survivor_zone)}, coalition.side.BLUE, "Downed pilot", false)
end, nil, timer.getTime() + 15)
""" if survivor_zone else "")


def hound_glue(platform_units):
    adds = "\n".join(f"hound:addPlatform({lua_str(u)})" for u in platform_units)
    return f"""-- Hound ELINT: friendly ELINT platforms locate enemy radars
hound = HoundElint:create(coalition.side.BLUE)
{adds}
hound:enableMarkers()
hound:systemOn()
"""
