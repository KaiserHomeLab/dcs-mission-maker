"""Friendly AI flights: catalog of usable types and the per-task behavior."""
from dcs import helicopters, planes, task

from .eras import AIRCRAFT_ERA

AI_TASKS = {
    "cap": ("Combat air patrol", [task.CAP, task.FighterSweep, task.Intercept]),
    "escort": ("Escort a player flight", [task.Escort, task.CAP]),
    "sead": ("SEAD / suppress air defenses", [task.SEAD]),
    "cas": ("Close air support", [task.CAS, task.GroundAttack]),
    "strike": ("Strike the objective", [task.PinpointStrike, task.GroundAttack, task.CAS]),
    "antiship": ("Anti-ship strike", [task.AntishipStrike]),
}
LOADOUT_ROLE = {"cap": "aa", "escort": "aa", "sead": "sead", "cas": "cas",
                "strike": "strike", "antiship": "antiship"}

# Era/side for AI-only types (player-flyable types come from eras.AIRCRAFT_ERA).
AI_ERA = {
    "F-14A": ("coldwar", "west"), "F-4E": ("vietnam", "west"), "F-5E": ("vietnam", "west"),
    "F-15E": ("modern", "west"), "F-16A": ("coldwar", "west"), "F-16A MLU": ("modern", "west"),
    "F-16C bl.50": ("modern", "west"), "F-16C bl.52d": ("modern", "west"),
    "F/A-18A": ("coldwar", "west"), "F/A-18C": ("modern", "west"),
    "Tornado IDS": ("coldwar", "west"), "Tornado GR4": ("modern", "west"),
    "Mirage 2000-5": ("modern", "west"), "F-117A": ("coldwar", "west"),
    "A6E": ("vietnam", "west"), "S-3B": ("coldwar", "west"), "B-52H": ("vietnam", "west"),
    "B-1B": ("coldwar", "west"), "MQ-9 Reaper": ("modern", "west"),
    "RQ-1A Predator": ("modern", "west"), "F4U-1D_CW": ("ww2", "west"),
    "A-20G": ("ww2", "west"), "B-17G": ("ww2", "west"), "Ju-88A4": ("ww2", "east"),
    "MiG-23MLD": ("coldwar", "east"), "MiG-25PD": ("coldwar", "east"),
    "MiG-27K": ("coldwar", "east"), "MiG-31": ("coldwar", "east"),
    "Su-17M4": ("coldwar", "east"), "Su-24M": ("coldwar", "east"), "Su-30": ("modern", "east"),
    "Su-34": ("modern", "east"), "Su-25TM": ("modern", "east"), "Tu-22M3": ("coldwar", "east"),
    "Tu-95MS": ("vietnam", "east"), "Tu-160": ("coldwar", "east"), "H-6J": ("modern", "east"),
    "WingLoong-I": ("modern", "east"), "Mirage-F1C": ("coldwar", "west"),
    "AH-64A": ("coldwar", "west"), "AH-1W": ("coldwar", "west"), "Mi-28N": ("modern", "east"),
    "Ka-52": ("modern", "east"), "Mi-24V": ("coldwar", "east"),
}
ERA_ORDER = ["ww2", "korea", "vietnam", "coldwar", "modern"]

# Best-suited types first for each job; anything else follows.
_FIGHTERS = ["F-15C", "F-16C bl.52d", "F/A-18C", "Su-27", "MiG-29S", "Su-30", "J-11A", "MiG-31",
             "F-14A", "F-16A", "MiG-23MLD", "F-4E", "MiG-21Bis", "F-5E", "MiG-19P",
             "F-86F Sabre", "MiG-15bis", "P-51D", "SpitfireLFMkIX", "FW-190D9", "Bf-109K-4"]
PREFERRED = {
    "cap": _FIGHTERS, "escort": _FIGHTERS,
    "sead": ["F-16C bl.52d", "F/A-18C", "Tornado GR4", "Tornado IDS", "Su-34", "Su-24M",
             "Su-30", "F-4E", "Su-25T", "A6E"],
    "cas": ["A-10C", "A-10A", "Su-25", "Su-25T", "AV8BNA", "F-16C bl.52d", "Su-17M4",
            "MiG-27K", "F-4E", "F-5E", "P-47D-30", "P-51D", "FW-190A8", "AH-64D_BLK_II", "Ka-50"],
    "strike": ["F-15E", "Tornado IDS", "Su-34", "Su-24M", "F-117A", "B-1B", "B-52H", "Tu-22M3",
               "F-4E", "A6E", "A-20G", "B-17G", "Ju-88A4", "F-16C bl.52d"],
    "antiship": ["F/A-18C", "Tu-22M3", "Su-24M", "S-3B", "Tornado IDS", "Su-30", "A6E",
                 "F-16C bl.52d"],
}


def _all_types():
    out = {}
    for m in (planes.plane_map, helicopters.helicopter_map):
        out.update(m)
    return out


TYPES = _all_types()


def era_of(type_id):
    return AIRCRAFT_ERA.get(type_id) or AI_ERA.get(type_id)


def catalog(ai_task, era=None, side=None):
    """Types that can fly `ai_task`, suggested (same era & side) first."""
    wanted = AI_TASKS[ai_task][1]
    items = []
    for tid, cls in TYPES.items():
        if not any(t in cls.tasks for t in wanted):
            continue
        es = era_of(tid)
        if es is None:
            continue  # skip civil/odd types with no era
        suggested = es == (era, side)
        items.append({"id": tid, "name": getattr(cls, "name", None) or tid,
                      "era": es[0], "side": es[1], "helicopter": bool(cls.helicopter),
                      "suggested": suggested})
    pref = PREFERRED.get(ai_task, [])
    items.sort(key=lambda a: (not a["suggested"],
                              pref.index(a["id"]) if a["id"] in pref else len(pref),
                              a["helicopter"], -ERA_ORDER.index(a["era"]), a["name"].lower()))
    return items


def pick_task(cls, ai_task):
    for t in AI_TASKS[ai_task][1]:
        if t in cls.tasks:
            return t
    return cls.task_default
