"""Generate a wide spread of missions and sanity-check each .miz.

Run inside the image:  python -m tests.smoke [--quick] [--jobs N] [--lua-dir DIR]
Missions build in parallel, one process per CPU unless --jobs says otherwise.
--quick builds a sample (~1 minute instead of ~10): every map, mission type, era
and aircraft at least once, rotating through the combinations.
With --lua-dir, the mission table and our config scripts are extracted there
for a `luac -p` syntax check (see README).
"""
import io
import itertools
import json
import os
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor

from app import eras
from app.aircraft import AIRCRAFT
from app.generator import MISSION_TYPES, MissionRequest, generate_full
from app.theaters import THEATERS

lua_dir = sys.argv[sys.argv.index("--lua-dir") + 1] if "--lua-dir" in sys.argv else None
QUICK = "--quick" in sys.argv
MT = list(MISSION_TYPES)
DIFFS = ["easy", "medium", "hard", "extreme"]


def sample(outer, inner, n):
    """In --quick mode keep one inner combination per outer item, rotating."""
    return not QUICK or inner == outer % n
JOBS = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else os.cpu_count() or 1
queue = []


def check(label, req_json, expect_dtc=0, expect_scripts=()):
    queue.append((label, req_json, expect_dtc, tuple(expect_scripts)))


def run(job):
    """Builds and checks one mission; returns (label, error text or None)."""
    label, req_json, expect_dtc, expect_scripts = job
    try:
        data = generate_full(MissionRequest.from_json(req_json))["data"]
        z = zipfile.ZipFile(io.BytesIO(data))
        names = z.namelist()
        assert "mission" in names, names
        theatre = z.read("theatre").decode()
        assert f'["theatre"]="{theatre}"' in z.read("mission").decode(), ("theatre file matches the mission", theatre)
        pages = [n for n in names if n.startswith("KNEEBOARD/")]
        routes = [n for n in pages if n.endswith("_route.png")]
        assert routes and len(routes) * 2 == len(pages), ("every flight gets a route page", pages)
        dtcs = [n for n in names if n.startswith("DTC/")]
        assert len(dtcs) == expect_dtc, (dtcs, expect_dtc)
        mission = z.read("mission").decode()
        for n in dtcs:
            doc = json.loads(z.read(n))
            assert doc["type"] in ("FA-18C_hornet", "F-16C_50") and doc["data"], n
            assert f'["name"]="{doc["name"]}"' in mission, f"cartridge {n} not bound"
        for s in expect_scripts:
            assert any(s in n for n in names), (s, names)
        if lua_dir:
            safe = label.replace(" ", "_").replace("/", "_")
            with open(os.path.join(lua_dir, f"{safe}.mission.lua"), "w") as fh:
                fh.write(mission)
            for n in names:
                if n.startswith("l10n/DEFAULT/dmm_"):
                    with open(os.path.join(lua_dir, f"{safe}.{n.rsplit('/', 1)[1]}"), "wb") as fh:
                        fh.write(z.read(n))
    except Exception as e:  # noqa: BLE001 - report everything
        return label, f"{type(e).__name__} {e}"
    return label, None


# 1. Every map x mission x difficulty, mixed flights incl. carrier + DTC jets.
for (ti, tk), (mi, mt), (di, diff) in itertools.product(enumerate(THEATERS), enumerate(MT), enumerate(DIFFS)):
    t = THEATERS[tk]
    if mt == "antiship" and not t.red_sea:
        continue
    # quick: every mission type on Caucasus, one rotating type and difficulty on the other maps
    if QUICK and not ((tk == "caucasus" and diff == "medium") or (sample(ti, mi, len(MT)) and sample(ti, di, 4))):
        continue
    flights = [{"aircraft": "F-16C_50", "slots": 2, "start": "cold", "squadron": "VFA-13"},
               {"aircraft": "A-10C_2", "slots": 2, "start": "hot"},
               {"aircraft": "AH-64D_BLK_II", "slots": 2, "start": "air"}]
    n_dtc = 1
    if t.blue_carrier:
        flights.append({"aircraft": "FA-18C_hornet", "slots": 4, "base": "carrier"})
        n_dtc += 1
    check(f"{tk} {mt} {diff}", {"theater": tk, "mission_type": mt, "difficulty": diff,
                                "flights": flights, "enemy_air": "heavy", "weather": "rain",
                                "wind": "strong"}, expect_dtc=n_dtc)

# 2. Every era and both sides, for every mission type.
reps = {("ww2", "west"): "P-51D", ("ww2", "east"): "Bf-109K-4",
        ("korea", "west"): "F-86F Sabre", ("korea", "east"): "MiG-15bis",
        ("vietnam", "west"): "F-4E-45MC", ("vietnam", "east"): "MiG-21Bis",
        ("coldwar", "west"): "F-14B", ("coldwar", "east"): "MiG-29S",
        ("modern", "west"): "FA-18C_hornet", ("modern", "east"): "JF-17"}
for ei, ((era, side), ac) in enumerate(reps.items()):
    assert eras.detect([(ac, 2)]) == (era, side), (ac, eras.detect([(ac, 2)]))
    types = [m for m in MT if m != "csar"]  # csar needs a helicopter; covered below
    for mi, mt in enumerate(types):
        if not sample(ei, mi, len(types)):
            continue
        check(f"era {era}/{side} {mt}", {"theater": "caucasus", "mission_type": mt,
                                         "difficulty": "hard", "enemy_air": "heavy",
                                         "flights": [{"aircraft": ac, "slots": 2}]},
              expect_dtc=1 if ac == "FA-18C_hornet" else 0)

# 3. Every flyable aircraft (air start) builds for every mission type.
for ai_, ac in enumerate(AIRCRAFT):
    if AIRCRAFT[ac].get("mod"):
        continue  # covered with their mods below
    types = [m for m in MT if m != "csar" or AIRCRAFT[ac]["helicopter"]]
    for mi, mt in enumerate(types):
        if not sample(ai_, mi, len(types)):
            continue
        check(f"aircraft {ac} {mt}", {"theater": "caucasus", "mission_type": mt,
                                      "awacs": False, "tankers": False, "enemy_air": "none",
                                      "flights": [{"aircraft": ac, "slots": 1, "start": "air"}]},
              expect_dtc=1 if ac in ("FA-18C_hornet", "F-16C_50") else 0)

# 4. All scripts together, with helicopters for CTLD/CSAR.
check("scripts all", {"theater": "syria", "mission_type": "sead", "difficulty": "hard",
                      "scripts": ["skynet", "hound", "ewrs", "ctld", "csar"],
                      "flights": [{"aircraft": "F-16C_50", "slots": 2},
                                  {"aircraft": "UH-1H", "slots": 2},
                                  {"aircraft": "CH-47Fbl1", "slots": 1}]},
      expect_dtc=1, expect_scripts=["mist.lua", "Moose_.lua", "skynet-iads-compiled.lua",
                                    "HoundElint.lua", "EWRS.lua", "dmm_skynet_config.lua",
                                    "dmm_hound_config.lua", "dmm_ctld_config.lua",
                                    "dmm_csar_config.lua"])

# 5. Friendly AI: wingmen, every AI task, JTAC, options, kneeboards.
from app import ai as ai_mod  # noqa: E402

for mi, mt in enumerate(["cas", "strike", "sead", "cap", "antiship"]):
    for ei, era_ac in enumerate(["F-16C_50", "F-4E-45MC", "P-51D", "MiG-29S"]):
        if not sample(mi, ei, 4):
            continue
        era, side = eras.detect([(era_ac, 2)])
        ai_flights = []
        for t in ai_mod.AI_TASKS:
            opts = ai_mod.catalog(t, era, side)
            if opts:
                ai_flights.append({"task": t, "aircraft": opts[0]["id"], "count": 2,
                                   "delay": 10 if t == "sead" else 0})
        check(f"ai {mt} {era_ac}", {
            "theater": "persiangulf", "mission_type": mt, "difficulty": "medium",
            "flights": [{"aircraft": era_ac, "slots": 1, "ai_wingmen": 1}],
            "ai_flights": ai_flights[:8], "jtac": True,
            "options": {"labels": "dots", "f10": "allies", "unlimited_fuel": True, "birds": True}},
            expect_dtc=1 if era_ac == "F-16C_50" else 0, expect_scripts=["KNEEBOARD/"])

# 6. Depth, planning and mods.
for ti, tk in enumerate(THEATERS):
    for mi, mt in enumerate(["cas", "sead", "strike", "csar"]):
        if not sample(ti, mi, 4):
            continue
        check(f"depth {tk} {mt}", {
            "theater": tk, "mission_type": mt, "difficulty": "extreme", "secondaries": 2,
            "chain": mt == "strike", "tot": "09:30", "popups": True, "dynamic_air": True,
            "flights": [{"aircraft": "UH-1H", "slots": 2},
                        {"aircraft": "A-10C_2", "slots": 2, "route": {"ip": None, "transit": [1, 1]}}],
            "ai_flights": [{"aircraft": "F-16C bl.52d", "task": "sead", "count": 2, "delay": "tot"}],
            "scripts": ["ctld"]})
check("mods", {"theater": "syria", "mission_type": "sead", "difficulty": "extreme",
               "mods": ["a4e", "uh60l", "hds"], "era": "modern",
               "flights": [{"aircraft": "A-4E-C", "slots": 2}, {"aircraft": "UH-60L", "slots": 2}]})
check("route override", {"theater": "caucasus", "mission_type": "strike", "flights": [
    {"aircraft": "F-16C_50", "slots": 2, "route": {"ip": [42.8, 41.6], "transit": [42.4, 41.9]}}]},
    expect_dtc=1)

fails = 0
with ProcessPoolExecutor(max_workers=JOBS) as pool:
    for label, err in pool.map(run, queue, chunksize=4):
        if err:
            fails += 1
            print("FAIL", label, err)
print(f"done: {len(queue)} missions, {fails} failures")
sys.exit(1 if fails else 0)
