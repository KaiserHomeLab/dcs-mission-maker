"""Friendly support: carrier group, AWACS and tankers, JTAC and AI flights."""

from dcs import ships, task, vehicles
from dcs.action import ActivateGroup
from dcs.condition import TimeAfter
from dcs.triggers import TriggerOnce

from .. import ai, eras
from ..comms import apply_callsign, apply_support_callsign, callsign_options
from ..loadouts import apply_role
from .common import ERAS_WITH_JTAC, JTAC_FREQ, JTAC_LASER, SKILLS, fmt_latlon, latlng_pair, resolve_offset, type_name
from .request import MissionError


class FriendlyMixin:
    """Friendly support: carrier group, AWACS and tankers, JTAC and AI flights."""

    # ---------------------------------------------------------------- support
    def add_carrier(self):
        pos = resolve_offset(self.terrain, self.theater.blue_carrier)
        h = self.terrain.airports[self.theater.blue_carrier.anchor].position.heading_between_point(pos)
        self.carrier_heading = h
        ctype = eras.CARRIER.get(self.era, ships.Stennis)
        name = "CV-9 Essex" if ctype is ships.Essex else "CVN-74 Stennis"
        g = self.m.ship_group(self.blue, name, ctype, pos, heading=h)
        if ctype is ships.Stennis:
            esc = self.m.ship("CG Escort", ships.TICONDEROG)
            esc.position = pos.point_from_heading(h + 180, 2500)
            esc.heading = h
            g.add_unit(esc)
        g.add_waypoint(pos.point_from_heading(h, 150000), 46)  # ~25 kts
        cvn = g.units[0]
        if ctype is ships.Stennis:
            g.points[0].tasks.append(task.ActivateBeaconCommand(
                channel=74, modechannel="X", callsign="STN", aa=False, unit_id=cvn.id))
            g.points[0].tasks.append(task.ActivateICLSCommand(channel=4, unit_id=cvn.id))
            g.points[0].tasks.append(task.ActivateLink4Command(frequency=336, unit_id=cvn.id))
            self.carrier_info = {"tacan": 74, "icls": 4, "link4": 336.0, "callsign": "STN",
                                 "unit_name": cvn.name, "unit_id": cvn.id, "pos": pos}
            self.brief.comms.append(
                f"{name}: TACAN 74X STN, ICLS 4, Link 4 336 MHz, steaming {h:03.0f}° at "
                f"25 kts from {fmt_latlon(pos)}.")
        else:
            self.brief.comms.append(
                f"{name}: steaming {h:03.0f}° at 25 kts from {fmt_latlon(pos)} (no TACAN).")
        self.carrier = g
        # Wind over the deck: put the surface wind on the bow.
        for wind in (self.m.weather.wind_at_ground, self.m.weather.wind_at_2000):
            wind.direction = (h + 180) % 360
        self.wind_from = round(h) % 360

    def add_support(self):
        r = self.req
        home = self.home.position
        threat = home.heading_between_point(self.target)
        self.has_awacs = self.has_boom = self.has_drogue = False
        if r.awacs and "awacs" in self.support:
            pos = home.point_from_heading(threat + 180, 30000)
            g = self.m.awacs_flight(self.blue, "Overlord", self.support["awacs"], None, pos,
                                    race_distance=40000, heading=threat + 90,
                                    altitude=9000, speed=600, frequency=251)
            apply_support_callsign(g, "awacs", "Overlord")
            self.awacs_unit = g.units[0].name
            self.has_awacs = True
            self.orbits.append({"name": "AWACS", "center": pos, "course": threat + 90,
                                "length": 40000, "alt": 9000})
            self.brief.comms.append(
                f"AWACS Overlord ({type_name(self.support['awacs'])}): 251.000 MHz AM.")

        tankers = [("boom", "Texaco", 252, "51X", 6100, threat),
                   ("drogue", "Arco", 253, "52X", 4900, threat + 30)]
        if r.tankers:
            any_tanker = False
            for kind, name, freq, tacan, alt, brg in tankers:
                if kind not in self.support:
                    continue
                pos = home.point_from_heading(brg, 25000 if kind == "boom" else 30000)
                g = self.m.refuel_flight(self.blue, name, self.support[kind], None, pos,
                                         race_distance=40000, heading=threat + 90,
                                         altitude=alt, speed=500, frequency=freq,
                                         tacanchannel=tacan)
                apply_support_callsign(g, "tanker", name)
                setattr(self, f"has_{kind}", True)
                any_tanker = True
                self.orbits.append({"name": name.upper(), "center": pos, "course": threat + 90,
                                    "length": 40000, "alt": alt})
                self.brief.comms.append(
                    f"Tanker {name} ({type_name(self.support[kind])}, {kind}): {freq}.000 MHz, "
                    f"TACAN {tacan}, FL{round(alt * 3.281 / 1000) * 10:03d}.")
            if not any_tanker:
                self.brief.situation.append(f"No tankers in the {eras.ERA_LABELS[self.era]} era.")

    # ------------------------------------------------------------- friendly AI
    def wants_jtac(self):
        return (self.req.jtac and self.req.mission_type in ("cas", "strike", "sead")
                and ERAS_WITH_JTAC.get(self.era, False))

    def add_jtac(self):
        """An invisible, immortal JTAC that lases the objective (code 1688)."""
        if not self.wants_jtac():
            return
        fac = task.FAC(callsign=1, designation=task.Designation.Auto, frequency=JTAC_FREQ,
                       modulation=task.Modulation.AM)
        if self.era == "modern":
            orbit = self.target.point_from_heading(self.heading_to_home(), 6000)
            g = self.m.flight_group_inflight(self.blue, "JTAC Axeman", self.ai_type("MQ-9 Reaper"),
                                             orbit, 4500, 250, maintask=task.AFAC, group_size=1)
            # Its aircraft callsign must not clash with a player flight's.
            apply_callsign(g, *self.next_ai_callsign(g.units[0].unit_type))
            g.units[0].name = "JTAC Axeman"
            g.points[0].tasks += [task.SetInvisibleCommand(True), task.SetImmortalCommand(True),
                                  fac]
            wp = g.add_waypoint(self.target, 4500, 250)
            wp.tasks.append(task.OrbitAction(4500, 250, task.OrbitAction.OrbitPattern.Circle))
            what = "MQ-9 Reaper orbiting the target"
            self.jtac_pos = orbit
        else:
            pos = self.target.point_from_heading(self.heading_to_home(), 3000)
            g = self.ground_group("JTAC Axeman", [(vehicles.Unarmed.Hummer, 0, 0)], pos,
                                  country=self.blue)
            g.points[0].tasks += [task.SetInvisibleCommand(True), task.SetImmortalCommand(True),
                                  fac]
            what = "ground team 3 km short of the target"
            self.jtac_pos = pos
        self.jtac_line = (f"JTAC Axeman ({what}): {JTAC_FREQ}.000 MHz AM, laser code "
                          f"{JTAC_LASER}. Check in on the radio and ask for a target.")
        self.brief.comms.append(self.jtac_line)

    @staticmethod
    def ai_type(type_id):
        return ai.TYPES[type_id]

    def next_ai_callsign(self, cls):
        for name in callsign_options(cls)[:8][::-1]:   # Pontiac, Chevy, ... first
            for n in range(1, 10):
                if (name, n) not in self.used_callsigns:
                    self.used_callsigns.add((name, n))
                    return name, n
        raise MissionError("Ran out of callsigns for AI flights")

    def add_ai_flights(self):
        home = self.home.position
        axis = home.heading_between_point(self.target)
        for i, af in enumerate(self.req.ai_flights):
            cls = ai.TYPES[af.aircraft]
            name, number = self.next_ai_callsign(cls)
            label = f"{name} {number}"
            maintask = ai.pick_task(cls, af.task)
            heli = bool(cls.helicopter)
            slow = heli or (cls.max_speed and cls.max_speed < 800)
            alt, spd = (300, 200) if heli else ((3000, 450) if slow else (6500, 750))
            if af.task == "escort":
                lead = self.player_groups[af.escort]
                spawn = lead.points[0].position.point_from_heading(axis + 180, 3000)
            else:
                spawn = home.point_from_heading(axis + 90 * (1 if i % 2 else -1), 6000)
            g = self.m.flight_group_inflight(self.blue, f"AI {label}", cls, spawn, alt, spd,
                                             maintask=maintask, group_size=af.count)
            apply_callsign(g, name, number)
            apply_role(g, ai.LOADOUT_ROLE[af.task])
            for u in g.units:
                u.skill = SKILLS["hard"]
            if heli:
                g.points[0].alt_type = "RADIO"
            first = g.points[0]
            desc = ai.AI_TASKS[af.task][0].lower()
            if af.task == "cap":
                station = home.lerp(self.target, 0.4)
                first.tasks.append(task.EngageTargets(max_distance=60000,
                                                      targets=[task.Targets.All.Air]))
                wp = g.add_waypoint(station, alt, spd)
                wp.tasks.append(task.OrbitAction(alt, spd - 100,
                                                 task.OrbitAction.OrbitPattern.RaceTrack))
                g.add_waypoint(station.point_from_heading(axis + 90, 30000), alt, spd)
                where = f"CAP station {fmt_latlon(station)}"
            elif af.task == "escort":
                lead = self.player_groups[af.escort]
                first.tasks.append(task.EscortTaskAction(group_id=lead.id, engagement_max_dist=60000,
                                                         lastwpt=len(lead.points)))
                where = f"escorting {af.escort}"
            else:
                targets = {"sead": [task.Targets.All.GroundUnits.AirDefence],
                           "cas": [task.Targets.All.GroundUnits],
                           "strike": [task.Targets.All.GroundUnits],
                           "antiship": [task.Targets.All.Naval]}[af.task]
                ip = self.target.point_from_heading(self.heading_to_home(), 20000)
                g.add_waypoint(ip, alt, spd)
                wp = g.add_waypoint(self.target, alt, spd)
                wp.tasks.append(task.EngageTargetsInZone(self.target, 5000, targets))
                if af.task == "strike" and self.req.mission_type == "strike":
                    wp.tasks.append(task.Bombing(self.target))
                g.add_waypoint(home, alt, spd)
                where = f"attacking near {self.red_airport.name}"
            if af.delay == "tot":
                tot = self.tot_seconds()
                arrive = tot - 180 if af.task == "sead" else tot + 120
                path = spawn.distance_to_point(self.target.point_from_heading(
                    self.heading_to_home(), 20000)) + 20000
                af.delay = max(0, round((arrive - path / (spd / 3.6)) / 60))
                af.timed = True
            if af.delay:
                g.late_activation = True
                trig = TriggerOnce(comment=f"Launch {label}")
                trig.add_condition(TimeAfter(af.delay * 60))
                trig.add_action(ActivateGroup(g.id))
                self.m.triggerrules.triggers.append(trig)
            when = f", launches at T+{af.delay} min" if af.delay else ""
            if getattr(af, "timed", False):
                when += (" to hit the target 3 min before your TOT" if af.task == "sead"
                         else " to arrive just after your TOT")
            self.brief.flights.append(
                f"{label} (AI): {af.count}x {type_name(cls)}, {desc}, {where}{when}.")
            self.ai_cards.append({"name": label, "aircraft": type_name(cls), "count": af.count,
                                  "job": desc, "where": where + when,
                                  "station": latlng_pair(station) if af.task == "cap" else None})
