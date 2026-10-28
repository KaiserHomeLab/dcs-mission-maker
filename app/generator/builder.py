"""The mission builder: shared state, build order and environment."""
import datetime
import random

import dcs
from dcs import cloud_presets, countries
from dcs.weather import Wind

from .. import eras, mods, objectives
from ..aircraft import AIRCRAFT
from ..comms import CommPlan
from ..theaters import THEATERS
from .briefing import BriefingMixin
from .common import (
    JTAC_FREQ,
    Briefing,
    fmt_latlon,
    resolve_offset,
    type_name,
)
from .enemy import EnemyMixin
from .friendly import FriendlyMixin
from .players import PlayersMixin
from .request import (
    TIMES,
    WINDS,
    MissionRequest,
    validate,
)
from .scripting import ScriptingMixin


class Builder(EnemyMixin, FriendlyMixin, PlayersMixin, ScriptingMixin, BriefingMixin):
    """Builds one mission. The mixins hold each part of the build; this class holds the
    shared state and the order the parts run in."""

    def __init__(self, req: MissionRequest, workdir: str):
        self.req = req
        self.workdir = workdir
        validate(req)
        self.theater = THEATERS[req.theater]
        self.m = dcs.Mission(self.theater.terrain_cls())
        self.terrain = self.m.terrain
        self.brief = Briefing()
        self.rng = random.Random()

        self.m.coalition["blue"].add_country(countries.CombinedJointTaskForcesBlue())
        self.m.coalition["red"].add_country(countries.CombinedJointTaskForcesRed())
        self.blue = self.m.country(countries.CombinedJointTaskForcesBlue.name)
        self.red = self.m.country(countries.CombinedJointTaskForcesRed.name)

        self.home = self.terrain.airports[req.blue_base or self.theater.default_blue]
        self.red_base = self.theater.red_base(req.red_base or self.theater.default_red)
        self.red_airport = self.terrain.airports[self.red_base.name]
        self.home.set_blue()
        self.red_airport.set_red()

        if req.mission_type == "antiship":
            self.target = resolve_offset(self.terrain, self.theater.red_sea)
        else:
            self.target = resolve_offset(self.terrain, self.red_base.inland)

        detected_era, self.player_side = eras.detect(
            (f.aircraft, f.slots) for f in req.flights)
        self.era = detected_era if req.era == "auto" else req.era
        self.enemy_side = eras.enemy_side(self.player_side)
        self.forces = eras.FORCES[(self.era, self.enemy_side)]
        self.support = eras.SUPPORT[(self.era, self.player_side)]

        self.carrier = None
        self.carrier_info = None
        self.carrier_heading = 0
        self.objective_units = []   # (kind, id) for the completion trigger
        self.warnings = []
        self.threats = []           # for cartridges: {"name","pos","range"}
        self.orbits = []            # for cartridges: {"name","center","course","length","alt"}
        self.awacs_unit = None
        self.heli_groups = []
        self.dtc_files = {}         # cartridge name -> JSON text
        self.cap_station = None
        self.player_groups = {}     # "Viper 1" -> group
        self.cards = []             # kneeboard data per player flight
        self.jtac_line = None
        self.jtac_pos = None
        self.flot = None
        self.friendly_armor = None
        self.ai_cards = []
        self.used_callsigns = {(f.callsign, f.number) for f in req.flights}
        self.forces_player = eras.FORCES[(self.era, self.player_side)]
        self.modules_used = {mods.MODS[AIRCRAFT[f.aircraft]["mod"]]["module"]
                             for f in req.flights if AIRCRAFT[f.aircraft].get("mod")}
        self.objectives = []        # [{"name","what","pos","units","groups"}], primary first
        self.secondaries = []
        self.fmt = fmt_latlon
        self.type_name = type_name
        self.cap_flag = None
        objectives.reset_flags()


    # --------------------------------------------------------------- building
    def build(self):
        self.setup_environment()
        if any(f.base == "carrier" for f in self.req.flights):
            self.add_carrier()
        getattr(self, f"objective_{self.req.mission_type}")()
        if self.objective_units:
            self.objectives.append({"name": "Primary objective", "what": "primary target",
                                    "pos": self.target, "units": list(self.objective_units),
                                    "groups": []})
        self.secondaries = objectives.add_secondaries(self)
        self.objectives += self.secondaries
        if self.secondaries and self.req.chain:
            self.brief.tasking.append(
                f"{len(self.secondaries)} follow-on target(s) will be passed by radio once the "
                "primary is destroyed. Keep some weapons and fuel in reserve.")
        for o in ([] if self.req.chain else self.secondaries):
            self.brief.tasking.append(
                f"{o['name']}: {o['what']} at {fmt_latlon(o['pos'])} (bulls {self.bulls(o['pos'])}).")
        if self.req.chain and len(self.objectives) > 1:
            objectives.chain(self, self.objectives)
        objectives.add_popups(self)
        self.add_ewr()
        self.add_enemy_air()
        self.add_support()
        self.comm_plan = CommPlan(self.home, self.has_awacs, self.has_boom, self.has_drogue,
                                  jtac_freq=JTAC_FREQ if self.wants_jtac() else None)
        self.add_jtac()
        self.add_players()
        self.add_ai_flights()
        self.add_scripts()
        self.apply_options()
        self.add_completion_trigger()
        self.write_briefing()
        self.add_kneeboards()
        if self.modules_used:
            self.m.required_modules = {mod: mod for mod in sorted(self.modules_used)}
        return self.m

    def setup_environment(self):
        r, m = self.req, self.m
        hh, mm = TIMES[r.time_of_day]
        month, day = (6, 21) if r.season == "summer" else (1, 15)
        year = {"ww2": 1944, "korea": 1952, "vietnam": 1968, "coldwar": 1985}.get(self.era, 2024)
        m.start_time = datetime.datetime(year, month, day, hh, mm, tzinfo=datetime.UTC)
        w = m.weather
        w.season_temperature = (self.theater.summer_temp if r.season == "summer"
                                else self.theater.winter_temp)
        preset = {"scattered": cloud_presets.Clouds.Scattered3,
                  "broken": cloud_presets.Clouds.Broken3,
                  "overcast": cloud_presets.Clouds.Overcast3,
                  "rain": cloud_presets.Clouds.OvercastAndRain1}.get(r.weather)
        if preset:
            w.clouds_preset = preset.value
            w.clouds_base = max(preset.value.min_base, 1200 if r.weather != "rain" else 900)
            w.clouds_thickness = 1500
        w.visibility_distance = 80000 if r.weather != "rain" else 15000

        g, a2k, a8k = WINDS[r.wind]
        # DCS stores the direction the wind blows *towards*.
        to_dir = self.rng.randint(0, 359)
        self.wind_from = (to_dir + 180) % 360
        w.wind_at_ground = Wind(to_dir, g)
        w.wind_at_2000 = Wind(to_dir, a2k)
        w.wind_at_8000 = Wind((to_dir + 20) % 360, a8k)
        self.wind_strength = g
        self.bullseye = self.home.position.lerp(self.target, 0.5)
        m.coalition["blue"].set_bullseye({"x": self.bullseye.x, "y": self.bullseye.y})
        rb = self.red_airport.position
        m.coalition["red"].set_bullseye({"x": rb.x, "y": rb.y})
