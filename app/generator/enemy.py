"""Enemy forces: ground groups and SAM sites, the objective for each mission type, EWRs and fighters."""

from dcs import statics, task
from dcs.action import ActivateGroup
from dcs.condition import TimeAfter, TimeSinceFlag
from dcs.triggers import TriggerOnce

from .. import mods, objectives
from ..loadouts import apply_role
from .common import AAA_SITES, SKILLS, fmt_latlon, threat_range, type_name


class EnemyMixin:
    """Enemy forces: ground groups and SAM sites, the objective for each mission type, EWRs and fighters."""

    # ---------------------------------------------------------------- helpers
    def ground_group(self, name, layout, center, heading=0, country=None):
        """layout: list of (unit_type, bearing_deg, distance_m)."""
        country = country or self.red
        first, *rest = layout
        pos0 = center.point_from_heading(first[1], first[2])
        g = self.m.vehicle_group(country, name, first[0], pos0, heading=heading)
        for i, (utype, brg, dist) in enumerate(rest, start=2):
            u = self.m.vehicle(f"{name}-{i}", utype)
            u.position = center.point_from_heading(brg, dist)
            u.heading = heading
            g.add_unit(u)
        return g

    def sam_site(self, label, layout, center, role="Site"):
        """A SAM/AAA site. Real SAMs are named "SAM ..." so Skynet picks them up."""
        prefix = "AAA" if label in AAA_SITES else "SAM"
        g = self.ground_group(f"{prefix} {label} {role}", layout, center)
        self.threats.append({"name": label.split()[0], "pos": center,
                             "range": threat_range(label)})
        return g

    def shorad(self, center, name="SHORAD"):
        g = self.ground_group(name, self.forces["shorad"][self.req.difficulty], center)
        self.threats.append({"name": "SHORAD", "pos": center, "range": 5000})
        return g

    def objective(self, group):
        self.objective_units.append(("group", group.id))

    def heading_to_home(self):
        return self.target.heading_between_point(self.home.position)

    # ------------------------------------------------------------- objectives
    def objective_cap(self):
        mid = self.home.position.lerp(self.red_airport.position, 0.55)
        n = {"easy": 2, "medium": 3, "hard": 4, "extreme": 5}[self.req.difficulty]
        self.cap_station = self.home.position.lerp(self.red_airport.position, 0.45)
        flag = (objectives.zone_entry_flag(self, "CAP Station", self.cap_station, 40000)
                if self.req.dynamic_air else None)
        for i in range(n):
            self.objective(self.enemy_fighters(f"Bandit Wave {i + 1}", mid,
                                               activate_after=60 + i * 9 * 60, flag=flag))
        self.orbits.append({"name": "CAP", "center": self.cap_station,
                            "course": self.home.position.heading_between_point(
                                self.red_airport.position) + 90,
                            "length": 20000, "alt": 7000})
        ftype = self.forces["fighters"][self.req.difficulty]
        self.brief.tasking.append(
            f"Establish a CAP at {fmt_latlon(self.cap_station)} between "
            f"{self.home.name} and {self.red_airport.name}. Expect {n} waves of "
            f"{type_name(ftype)} pairs, roughly every 9 minutes"
            + (" once you reach the station" if self.req.dynamic_air else "")
            + ". Destroy all enemy fighters.")

    def objective_cas(self):
        h = self.heading_to_home()
        d = self.req.difficulty
        tanks, ifv, truck = self.forces["tanks"][d], self.forces["ifv"], self.forces["truck"]
        layout = ([(tanks, h + 90, 150 * i) for i in range(-2, 2)]
                  + [(ifv, h + 90, 150 * i + 75) for i in range(-2, 2)])
        armor = self.ground_group("Enemy Armor", layout, self.target, heading=h)
        supply = self.ground_group(
            "Enemy Supply", [(truck, h + 180, 600 + 60 * i) for i in range(4)],
            self.target, heading=h)
        self.shorad(self.target.point_from_heading(h + 180, 400))
        self.objective(armor)
        self.objective(supply)
        if self.req.front_line:
            objectives.add_front_line(self, armor)
        self.brief.tasking.append(
            f"An enemy armored column ({type_name(tanks)} and {type_name(ifv)}) with supply "
            f"trucks is massing at {fmt_latlon(self.target)}, near {self.red_airport.name}. "
            f"Destroy the armor and trucks. Expect short-range air defenses.")

    def objective_sead(self):
        d = self.req.difficulty
        label, layout = self.forces["sam"][d]
        override, module = mods.sam_override(self.req.mods, self.era, self.enemy_side, d)
        if override:
            label, layout = override
            self.modules_used.add(module)
        site = self.sam_site(label, layout, self.target)
        self.objective(site)
        self.shorad(self.target.point_from_heading(self.heading_to_home(), 1200),
                    "Site Point Defense")
        verb = "Suppress and destroy it" if label not in AAA_SITES else "Destroy it"
        self.brief.tasking.append(
            f"An enemy {label} at {fmt_latlon(self.target)} near {self.red_airport.name} "
            f"is denying our access. {verb}: kill the radars and the launchers or guns.")

    def objective_strike(self):
        h = self.heading_to_home()
        layout = [
            (statics.Fortification.Military_staff, 0, 0, "Command Bunker"),
            (statics.Warehouse.Warehouse, 90, 120, "Depot Warehouse A"),
            (statics.Warehouse.Warehouse, 90, 220, "Depot Warehouse B"),
            (statics.Warehouse.Tank, 200, 150, "Fuel Tank A"),
            (statics.Warehouse.Tank, 220, 200, "Fuel Tank B"),
            (statics.Fortification.FARP_Ammo_Dump_Coating, 300, 150, "Ammo Dump"),
        ]
        for stype, brg, dist, name in layout:
            sg = self.m.static_group(self.red, name, stype,
                                     self.target.point_from_heading(h + brg, dist), heading=h)
            self.objective_units.append(("unit", sg.units[0].id))
        self.shorad(self.target, "Depot Air Defense")
        extra = ""
        if self.req.difficulty in ("hard", "extreme"):
            label, layout = self.forces["sam"]["easy"]
            self.sam_site(label, layout, self.target.point_from_heading(h + 180, 3000), "Depot")
            extra = f" and a {label} to the rear"
        self.brief.tasking.append(
            f"Destroy the enemy command and supply depot at {fmt_latlon(self.target)} near "
            f"{self.red_airport.name}: command bunker, two warehouses, two fuel tanks and an "
            f"ammo dump. Defended by short-range air defenses{extra}.")

    def objective_antiship(self):
        fleet = self.forces["ships"][self.req.difficulty]
        h = self.rng.randint(0, 359)
        g = self.m.ship_group(self.red, "Enemy Flotilla", fleet[0], self.target, heading=h)
        for i, stype in enumerate(fleet[1:], start=2):
            s = self.m.ship(f"Enemy Flotilla-{i}", stype)
            s.position = self.target.point_from_heading(h + 180 + (i - 2.5) * 40, 1200 * (i - 1))
            s.heading = h
            g.add_unit(s)
        # Loiter slowly back and forth so the group stays in open water.
        g.add_waypoint(self.target.point_from_heading(h, 8000), 18)
        g.add_waypoint(self.target, 18)
        self.objective(g)
        self.threats.append({"name": "SHIPS", "pos": self.target, "range": 15000})
        names = ", ".join(type_name(s) for s in fleet)
        self.brief.tasking.append(
            f"Enemy naval group ({names}) is operating near {fmt_latlon(self.target)}. "
            f"Sink all vessels. Warships may carry SAMs; plan standoff attacks.")

    def objective_csar(self):
        """A downed pilot deep in enemy territory, with a search party closing in."""
        off = self.red_base.inland
        self.target = self.red_airport.position.point_from_heading(
            off.bearing, (off.distance_km + 3) * 1000)
        self.m.triggers.add_triggerzone(self.target, 300, True, "CSAR Survivor")
        h = self.target.heading_between_point(self.red_airport.position)
        start = self.target.point_from_heading(h, 6000)
        inf = self.forces["infantry"]
        party = self.ground_group(
            "Search Party", [(inf, 90, 10 * i) for i in range(6)] + [(self.forces["ifv"], 180, 30)],
            start, heading=(h + 180) % 360)
        party.add_waypoint(self.target.point_from_heading(h, 400), speed=8)
        self.objective(party)
        self.shorad(self.target.point_from_heading(h, 3000), "Search Party Cover")
        self.brief.tasking.append(
            f"A friendly pilot is down near {fmt_latlon(self.target)} (bulls "
            f"{self.bulls(self.target)}), about 3 km past {self.red_airport.name}. An enemy "
            "search party is closing in from the airfield side. Helicopter flights: find the "
            "survivor with the F10 > CSAR menu (beacon, smoke, flares), land next to them and "
            "bring them home to the MASH at your airfield. Everyone else: escort the helicopters "
            "and destroy the search party before it reaches the pilot.")

    def objective_free(self):
        self.brief.tasking.append(
            "No hostile forces. Free flight / training: practice navigation, formation, "
            f"refueling and landings. Range area is near {self.red_airport.name} "
            f"({fmt_latlon(self.target)}).")

    def add_ewr(self):
        if self.req.mission_type == "free" or not self.forces.get("ewr"):
            return
        off = self.red_base.inland
        pos = self.red_airport.position.point_from_heading(off.bearing, (off.distance_km + 4) * 1000)
        self.ground_group("EW Radar", [(self.forces["ewr"], 0, 0)], pos)

    # -------------------------------------------------------------- enemy air
    def enemy_fighters(self, name, orbit_at, activate_after=None, size=2, flag=None):
        ftype = self.forces["fighters"][self.req.difficulty]
        spawn = self.red_airport.position.point_from_heading(
            self.red_airport.position.heading_between_point(self.home.position) + 180, 15000)
        slow = ftype.max_speed and ftype.max_speed < 800
        alt, spd = (3500, 450) if slow else (7000, 800)
        g = self.m.flight_group_inflight(self.red, name, ftype, spawn, alt, spd,
                                         maintask=task.CAP, group_size=size)
        apply_role(g, "aa")
        for u in g.units:
            u.skill = SKILLS[self.req.difficulty]
        g.points[0].tasks.append(task.EngageTargets(max_distance=80000,
                                                    targets=[task.Targets.All.Air]))
        wp = g.add_waypoint(orbit_at, alt, spd)
        wp.tasks.append(task.OrbitAction(alt, spd - 50, task.OrbitAction.OrbitPattern.Circle))
        if activate_after is not None:
            g.late_activation = True
            trig = TriggerOnce(comment=f"Activate {name}")
            trig.add_condition(TimeSinceFlag(flag, activate_after) if flag
                               else TimeAfter(activate_after))
            trig.add_action(ActivateGroup(g.id))
            self.m.triggerrules.triggers.append(trig)
        return g

    def add_enemy_air(self):
        r = self.req
        if r.mission_type in ("cap", "free") or r.enemy_air == "none":
            return
        flag = (objectives.zone_entry_flag(self, "Enemy CAP Trigger", self.target, 90000)
                if r.dynamic_air else None)
        self.enemy_fighters("Enemy CAP", self.target, activate_after=0 if flag else None,
                            flag=flag)
        if r.enemy_air == "heavy":
            self.enemy_fighters("Enemy Reinforcements", self.target, activate_after=15 * 60,
                                flag=flag)
        ftype = self.forces["fighters"][r.difficulty]
        self.brief.situation.append(
            f"Enemy air: {'one' if r.enemy_air == 'light' else 'two'} {type_name(ftype)} "
            f"pair(s) over the target area"
            + (", scrambling when you come within ~50 nm" if flag else "")
            + (" (a second pair follows ~15 min later)." if r.enemy_air == "heavy" else "."))
