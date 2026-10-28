"""Optional community mods. Only used when you say your group has them, and
listed in the mission's requiredModules so DCS tells anyone who's missing one.

Unit type names come from BriefingRoom's mod database.
"""
from dcs import helicopters, planes, unittype

# Attributes copied from a similar stock type; weapon pylons are deliberately
# not copied, so mod aircraft spawn clean (rearm on the ground).
_COPY = ["category", "chaff", "chaff_charge_size", "charge_total", "eplrs", "flare",
         "flare_charge_size", "fuel_max", "height", "length", "width", "max_speed",
         "tacan", "property_defaults", "properties", "tasks", "task_default", "large_parking_slot",
         "radio_frequency"]


def _flyable(type_id, base, helicopter, panel_radio=None, callnames=None, group_size=4):
    attrs = {k: getattr(base, k) for k in _COPY if hasattr(base, k)}
    attrs.update(id=type_id, flyable=True, helicopter=helicopter, group_size_max=group_size,
                 pylons=set(), panel_radio=panel_radio, callnames=callnames or {},
                 livery_name=type_id, payloads=None, Liveries=getattr(base, "Liveries", None))
    parent = helicopters.HelicopterType if helicopter else planes.PlaneType
    return type(type_id.replace("-", "_"), (parent,), attrs)


def _uhf_radio(freqs):
    return {1: {"channels": {i + 1: f for i, f in enumerate(freqs)}}}


A4E = _flyable("A-4E-C", planes.F_5E_3, False,
               panel_radio=_uhf_radio([264, 265, 256, 254, 250, 270, 257, 258, 262, 259,
                                       268, 269, 260, 263, 261, 267, 251, 253, 266, 252]))
UH60L = _flyable("UH-60L", helicopters.UH_1H, True,
                 callnames={"USA": ["Jolly", "Pedro"]})


def _vehicle(type_id, name, base=unittype.VehicleType):
    return type("HDS_" + "".join(c if c.isalnum() else "_" for c in type_id), (base,),
                {"id": type_id, "name": name, "eplrs": False, "detection_range": 0,
                 "threat_range": 0, "air_weapon_dist": 0})


def _ring(utype, count, radius, start=0):
    return [(utype, start + i * 360 / count, radius) for i in range(count)]


# High Digit SAMs: SA-20 (S-300PMU1) and SA-20B (S-300PMU2) batteries.
_PMU1 = {k: _vehicle(k, k) for k in ["S-300PMU1 64N6E sr", "S-300PMU1 40B6M tr",
                                      "S-300PMU1 54K6 cp", "S-300PMU1 5P85CE ln"]}
_PMU2 = {k: _vehicle(k, k) for k in ["S-300PMU2 64H6E2 sr", "S-300PMU2 92H6E tr",
                                      "S-300PMU2 54K6E2 cp", "S-300PMU2 5P85SE2 ln"]}
SA20 = ("SA-20 Gargoyle", [(_PMU1["S-300PMU1 40B6M tr"], 0, 0),
                           (_PMU1["S-300PMU1 64N6E sr"], 180, 300),
                           (_PMU1["S-300PMU1 54K6 cp"], 270, 250)]
        + _ring(_PMU1["S-300PMU1 5P85CE ln"], 6, 450, 30))
SA20B = ("SA-20B Gargoyle", [(_PMU2["S-300PMU2 92H6E tr"], 0, 0),
                             (_PMU2["S-300PMU2 64H6E2 sr"], 180, 300),
                             (_PMU2["S-300PMU2 54K6E2 cp"], 270, 250)]
         + _ring(_PMU2["S-300PMU2 5P85SE2 ln"], 6, 450, 30))

MODS = {
    "a4e": {"name": "Community A-4E-C", "module": "A-4E-C",
            "desc": "Adds the A-4E Skyhawk as a flyable aircraft (Vietnam era).",
            "aircraft": {"A-4E-C": ("A-4E-C Skyhawk (mod)", A4E, ("vietnam", "west"))}},
    "uh60l": {"name": "UH-60L Black Hawk", "module": "UH-60L",
              "desc": "Adds the UH-60L as a flyable helicopter (modern).",
              "aircraft": {"UH-60L": ("UH-60L Black Hawk (mod)", UH60L, ("modern", "west"))}},
    "hds": {"name": "High Digit SAMs", "module": "HighDigitSAMs",
            "desc": "Modern Soviet-side enemies field SA-20/SA-20B batteries on hard/extreme SEAD.",
            "sam": {("modern", "east"): {"hard": SA20, "extreme": SA20B}}},
}


def catalog():
    return [{"id": k, "name": v["name"], "desc": v["desc"]} for k, v in MODS.items()]


def sam_override(mods, era, side, difficulty):
    for mid in mods:
        site = MODS[mid].get("sam", {}).get((era, side), {}).get(difficulty)
        if site:
            return site, MODS[mid]["module"]
    return None, None
