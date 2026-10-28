"""Shared generator constants and helpers: positions, bearings, threat ranges."""
import math
from dataclasses import dataclass, field

from dcs import task
from dcs.mapping import Point
from dcs.unit import Skill

from .. import eras
from ..aircraft import AIRCRAFT
from ..comms import callsign_options
from ..theaters import Offset

TASK_PREFERENCE = {
    "cap": [task.CAP, task.FighterSweep, task.Intercept, task.Escort],
    "cas": [task.CAS, task.GroundAttack],
    "sead": [task.SEAD, task.GroundAttack, task.CAS],
    "strike": [task.PinpointStrike, task.GroundAttack, task.CAS],
    "antiship": [task.AntishipStrike, task.GroundAttack, task.CAS],
    "csar": [task.CAS, task.Escort, task.GroundAttack, task.Transport],
    "free": [],
}

AAA_SITES = {eras.FLAK88[0], eras.FLAK88_HEAVY[0], eras.ALLIED_AA[0],
             eras.ALLIED_AA_HEAVY[0], eras.RADAR_AAA[0]}
THREAT_RANGE_M = {"SA-20": 150000, "SA-2": 45000, "SA-3": 25000, "SA-6": 25000, "SA-11": 35000,
                  "SA-10": 75000, "MIM-23": 40000, "MIM-104": 70000, "NASAMS": 25000,
                  "Flak": 10000, "AA battery": 9000, "AAA": 12000}
ERAS_WITH_JTAC = {"vietnam": True, "coldwar": True, "modern": True}
SKILLS = {"easy": Skill.Average, "medium": Skill.Good, "hard": Skill.High,
          "extreme": Skill.Excellent}
JTAC_FREQ, JTAC_LASER = 266, 1688


@dataclass
class Briefing:
    situation: list[str] = field(default_factory=list)
    tasking: list[str] = field(default_factory=list)
    comms: list[str] = field(default_factory=list)
    flights: list[str] = field(default_factory=list)


def fmt_latlon(p: Point) -> str:
    ll = p.latlng()

    def ddm(v, pos, neg):
        hemi = pos if v >= 0 else neg
        v = abs(v)
        deg = int(v)
        return f"{hemi}{deg:02d}°{(v - deg) * 60:06.3f}'"

    return f"{ddm(ll.lat, 'N', 'S')} {ddm(ll.lng, 'E', 'W')}"


def latlng_pair(p: Point) -> list[float]:
    """[lat, lng] rounded for JSON (maps, Briefing Room)."""
    ll = p.latlng()
    return [round(ll.lat, 5), round(ll.lng, 5)]


def bearing_nm(origin: Point, pos: Point) -> tuple[float, float]:
    """True bearing (degrees) and great-circle distance (nm) from origin to pos."""
    a, b = origin.latlng(), pos.latlng()
    la1, lo1, la2, lo2 = map(math.radians, (a.lat, a.lng, b.lat, b.lng))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    brg = (math.degrees(math.atan2(y, x)) + 360) % 360
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return brg, 2 * 6371000 * math.asin(math.sqrt(h)) / 1852


def bra(origin: Point, pos: Point) -> str:
    """'BBB/RR': true bearing and range in nm, on the sphere."""
    brg, nm = bearing_nm(origin, pos)
    return f"{round(brg) % 360:03d}/{nm:.0f}"


def resolve_offset(terrain, off: Offset) -> Point:
    ap = terrain.airports[off.anchor]
    return ap.position.point_from_heading(off.bearing, off.distance_km * 1000)


def pick_task(cls, mission_type):
    for t in TASK_PREFERENCE[mission_type]:
        if t in cls.tasks:
            return t
    return cls.task_default or task.Nothing


def type_name(t):
    return getattr(t, "name", None) or t.id


def default_callsign(aircraft_id, index):
    """First aircraft-specific callsign if the type has them, else a generic one."""
    opts = callsign_options(AIRCRAFT[aircraft_id]["cls"])
    own = opts[8:]
    return own[0] if own else opts[index % 8]


def threat_range(label):
    for key, rng in THREAT_RANGE_M.items():
        if key in label:
            return rng
    return 5000
