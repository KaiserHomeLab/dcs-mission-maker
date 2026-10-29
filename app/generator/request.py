"""What the builder asks for: mission/flight requests, their choices, and validation."""
import re
from dataclasses import dataclass, field

from dcs.forcedoptions import ForcedOptions

from .. import ai, eras, liveries, mods, objectives, scripts
from ..aircraft import AIRCRAFT
from ..comms import callsign_options
from ..theaters import THEATERS
from .common import default_callsign

MISSION_TYPES = {
    "cap": "Combat Air Patrol",
    "cas": "Close Air Support",
    "sead": "SEAD / DEAD",
    "strike": "Precision Strike",
    "antiship": "Anti-Ship Strike",
    "csar": "Combat Search & Rescue",
    "free": "Free Flight / Training",
}
DIFFICULTIES = ["easy", "medium", "hard", "extreme"]
TIMES = {"dawn": (6, 0), "morning": (8, 30), "noon": (12, 0),
         "afternoon": (15, 30), "dusk": (18, 45), "night": (22, 0)}
WEATHER = ["clear", "scattered", "broken", "overcast", "rain"]
WINDS = {"calm": (0, 0, 0), "light": (2, 5, 8), "strong": (7, 13, 20)}


class MissionError(ValueError):
    """User-facing error (bad request or impossible layout)."""


@dataclass
class FlightRequest:
    aircraft: str
    slots: int = 2             # player seats
    ai_wingmen: int = 0        # AI aircraft added after the player seats
    callsign: str = ""
    number: int = 1
    squadron: str = ""
    start: str = "cold"        # cold | hot | runway | air
    base: str = "airfield"     # airfield | carrier
    loadout: str = ""          # preset id from /api/loadouts, "" = recommended
    livery: str = ""           # livery id from /api/liveries, "" = DCS default
    dtc: bool = True           # write a data cartridge when the jet supports one
    pilots: list[str] = field(default_factory=list)  # names per player seat (sign-ups)
    route: dict = field(default_factory=dict)        # {"transit": [lat, lng], "ip": [lat, lng]}


@dataclass
class AIFlightRequest:
    aircraft: str
    task: str = "cap"          # see ai.AI_TASKS
    count: int = 2
    escort: str = ""           # player flight to escort, e.g. "Viper 1"
    delay: int | str = 0       # minutes after mission start, or "tot" to time it off the TOT


OPTION_DEFAULTS = {"labels": "none", "f10": "all", "external_views": True,
                   "unlimited_fuel": False, "unlimited_weapons": False,
                   "easy_comms": False, "civil_traffic": False, "birds": False}
LABELS = {"none": ForcedOptions.Labels.None_, "full": ForcedOptions.Labels.Full,
          "abbreviated": ForcedOptions.Labels.Abbreviate, "dots": ForcedOptions.Labels.DotOnly}
F10_VIEWS = {"all": ForcedOptions.Views.All, "allies": ForcedOptions.Views.Allies,
             "own": ForcedOptions.Views.MyAircraft, "map": ForcedOptions.Views.OnlyMap}


@dataclass
class MissionRequest:
    theater: str
    mission_type: str
    flights: list[FlightRequest]
    blue_base: str = ""
    red_base: str = ""
    difficulty: str = "medium"
    era: str = "auto"
    time_of_day: str = "morning"
    season: str = "summer"
    weather: str = "clear"
    wind: str = "light"
    enemy_air: str = "light"   # none | light | heavy (ground missions)
    awacs: bool = True
    tankers: bool = True
    singleplayer: bool = False
    title: str = ""
    scripts: list[str] = field(default_factory=list)
    ai_flights: list[AIFlightRequest] = field(default_factory=list)
    jtac: bool = True
    options: dict = field(default_factory=dict)
    secondaries: int = 0            # extra objectives (0-2)
    secondary_kinds: list[str] = field(default_factory=list)
    chain: bool = False             # each objective unlocks the next
    popups: bool = True             # hidden air defenses that switch on near the target
    front_line: bool = True         # CAS: friendly troops + advancing column
    dynamic_air: bool = True        # enemy fighters launch when you arrive
    tot: str = ""                   # time on target "HH:MM" (local), "" = none
    mods: list[str] = field(default_factory=list)   # community mods your group has
    srs: str = ""                   # SRS voice server for this mission, "" = SRS_ADDRESS default
    srs_note: str = ""              # e.g. where the password is (never the password itself)

    @classmethod
    def from_json(cls, d: dict) -> "MissionRequest":
        def build(klass, items):
            return [klass(**{k: v for k, v in f.items() if k in klass.__dataclass_fields__})
                    for f in items or []]
        fields = {k: v for k, v in d.items()
                  if k in cls.__dataclass_fields__ and k not in ("flights", "ai_flights")}
        return cls(flights=build(FlightRequest, d.get("flights")),
                   ai_flights=build(AIFlightRequest, d.get("ai_flights")), **fields)


def validate(r: MissionRequest) -> None:
    """Check and normalise a request in place; raises MissionError."""
    if r.theater not in THEATERS:
        raise MissionError(f"Unknown map '{r.theater}'")
    t = THEATERS[r.theater]
    if r.mission_type not in MISSION_TYPES:
        raise MissionError(f"Unknown mission type '{r.mission_type}'")
    if r.blue_base and r.blue_base not in t.blue_bases:
        raise MissionError(f"'{r.blue_base}' is not a friendly base on {t.label}")
    if r.red_base and r.red_base not in [b.name for b in t.red_bases]:
        raise MissionError(f"'{r.red_base}' is not a target area on {t.label}")
    if r.difficulty not in DIFFICULTIES:
        raise MissionError("Bad difficulty")
    if r.era != "auto" and r.era not in eras.ERAS:
        raise MissionError("Bad era")
    if r.time_of_day not in TIMES or r.weather not in WEATHER or r.wind not in WINDS:
        raise MissionError("Bad time/weather/wind")
    if not r.flights:
        raise MissionError("Add at least one flight")
    if len(r.flights) > 8:
        raise MissionError("Maximum 8 flights")
    if r.mission_type == "antiship" and not t.red_sea:
        raise MissionError(f"{t.label} has no sea: pick another mission type")
    try:
        r.scripts = scripts.resolve(r.scripts or [])
    except ValueError as e:
        raise MissionError(str(e)) from e
    used = set()
    for i, f in enumerate(r.flights):
        _check_flight(f, i, t, used)
    if len(r.ai_flights) > 8:
        raise MissionError("Maximum 8 AI flights")
    player_names = {f"{f.callsign} {f.number}" for f in r.flights}
    for af in r.ai_flights:
        _check_ai_flight(af, r, player_names)
    bad = [x for x in r.mods or [] if x not in mods.MODS]
    bad = [x for x in r.mods or [] if x not in mods.MODS]
    if bad:
        raise MissionError(f"Unknown mod '{bad[0]}'")
    for f in r.flights:
        need = AIRCRAFT[f.aircraft].get("mod")
        if need and need not in r.mods:
            raise MissionError(f"{AIRCRAFT[f.aircraft]['name']} needs the "
                               f"{mods.MODS[need]['name']} mod: tick it under Mods.")
    if r.tot:
        m = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", r.tot.strip())
        if not m:
            raise MissionError("TOT must look like 09:30")
        r.tot = f"{int(m.group(1)):02d}:{m.group(2)}"
    r.secondaries = int(r.secondaries or 0)
    if not 0 <= r.secondaries <= 2:
        raise MissionError("Extra objectives: 0 to 2")
    if any(k not in objectives.SECONDARY_KINDS for k in r.secondary_kinds or []):
        raise MissionError("Unknown objective kind")
    if r.mission_type == "csar":
        r.scripts = scripts.resolve(list(r.scripts) + ["csar"])
        if not any(AIRCRAFT[f.aircraft]["helicopter"] for f in r.flights):
            raise MissionError("Combat Search & Rescue needs at least one helicopter flight "
                               "to pick up the survivor.")
    opts = dict(OPTION_DEFAULTS)
    opts.update({k: v for k, v in (r.options or {}).items() if k in OPTION_DEFAULTS})
    if opts["labels"] not in LABELS or opts["f10"] not in F10_VIEWS:
        raise MissionError("Bad mission options")
    r.options = opts
    r.srs = str(r.srs or "").strip()
    if r.srs and not re.fullmatch(r"[\w.\-:\[\]]{1,100}", r.srs):
        raise MissionError("SRS server should look like srs.example.com:5002")
    r.srs_note = re.sub(r"[^\w #@.,:;!?()'/\-]", "", str(r.srs_note or ""))[:80].strip()


def _check_flight(f, i, t, used):
    """One player flight; used holds the (callsign, number) pairs taken so far."""
    a = AIRCRAFT.get(f.aircraft)
    if not a:
        raise MissionError(f"Unknown aircraft '{f.aircraft}'")
    f.slots = int(f.slots)
    f.ai_wingmen = int(f.ai_wingmen or 0)
    if f.slots < 1 or f.ai_wingmen < 0 or f.slots + f.ai_wingmen > a["max_group"]:
        raise MissionError(f"{a['name']}: seats + AI wingmen must be 1-{a['max_group']}")
    if f.start not in ("cold", "hot", "runway", "air"):
        raise MissionError("Bad start type")
    if f.base == "carrier":
        if not t.blue_carrier:
            raise MissionError(f"{t.label} has no carrier ops")
        if not a["carrier"]:
            raise MissionError(f"{a['name']} can't operate from a carrier")
    f.callsign = (f.callsign or "").strip() or default_callsign(f.aircraft, i)
    if f.callsign not in callsign_options(a["cls"]):
        raise MissionError(f"'{f.callsign}' isn't a DCS callsign for {a['name']}")
    f.number = int(f.number or 1)
    if not 1 <= f.number <= 9:
        raise MissionError("Flight numbers go from 1 to 9")
    while (f.callsign, f.number) in used:
        f.number += 1
        if f.number > 9:
            raise MissionError(f"Too many {f.callsign} flights")
    used.add((f.callsign, f.number))
    f.squadron = re.sub(r"[^\w \-#.']", "", f.squadron or "")[:40].strip()
    f.livery = str(f.livery or "").strip()
    if f.livery and not liveries.VALID_ID.fullmatch(f.livery):
        raise MissionError(f"{a['name']}: bad livery name")
    f.pilots = [re.sub(r"[^\w \-.']", "", str(p or ""))[:24].strip()
                for p in (f.pilots or [])][:f.slots]


def _check_ai_flight(af, r, player_names):
    """One AI flight; escorts must name a player flight."""
    if af.aircraft not in ai.TYPES:
        raise MissionError(f"Unknown AI aircraft '{af.aircraft}'")
    if af.task not in ai.AI_TASKS:
        raise MissionError(f"Unknown AI task '{af.task}'")
    cls = ai.TYPES[af.aircraft]
    if not any(t in cls.tasks for t in ai.AI_TASKS[af.task][1]):
        raise MissionError(f"{af.aircraft} can't fly {ai.AI_TASKS[af.task][0].lower()}")
    af.count = int(af.count or 1)
    if af.delay == "tot":
        if not r.tot:
            raise MissionError("An AI flight is timed off the TOT, but no TOT is set")
    else:
        af.delay = int(af.delay or 0)
    if not 1 <= af.count <= (cls.group_size_max or 4) or \
            (af.delay != "tot" and not 0 <= af.delay <= 120):
        raise MissionError(f"AI {af.aircraft}: bad size or launch delay")
    if af.task == "escort":
        af.escort = af.escort or next(iter(sorted(player_names)))
        if af.escort not in player_names:
            raise MissionError(f"AI escort: no player flight called '{af.escort}'")
