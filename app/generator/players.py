"""Player flights: spawning, callsigns, loadouts, routes, TOT timing and data cartridges."""

from dcs.mapping import LatLng, Point
from dcs.mission import StartType
from dcs.terrain import NoParkingSlotError

from .. import dtc, liveries, routes
from ..aircraft import AIRCRAFT
from ..comms import CommPlan, apply_callsign, radio_table, reset_stn
from ..loadouts import apply_loadout
from .common import SKILLS, pick_task
from .request import TIMES, MissionError


class PlayersMixin:
    """Player flights: spawning, callsigns, loadouts, routes, TOT timing and data cartridges."""

    # ---------------------------------------------------------------- players
    START_TYPES = {"cold": StartType.Cold, "hot": StartType.Warm, "runway": StartType.Runway}

    def add_players(self):
        r = self.req
        reset_stn()
        for idx, f in enumerate(r.flights):
            a = AIRCRAFT[f.aircraft]
            maintask = pick_task(a["cls"], r.mission_type)
            flight_name = f"{f.callsign} {f.number}"
            group_name = f"{f.squadron} - {flight_name}" if f.squadron else flight_name

            heli = a["helicopter"]
            cruise_alt = 300 if heli else (7000 if r.mission_type == "cap" else 5500)
            cruise_spd = 220 if heli else 750
            if not heli and a["cls"].max_speed and a["cls"].max_speed < 800:  # warbirds/trainers
                cruise_alt, cruise_spd = 3000, 450

            g = self.spawn_player_group(f, a, maintask, group_name, flight_name, cruise_alt, cruise_spd)
            apply_callsign(g, f.callsign, f.number)
            for u, pilot in zip(g.units, f.pilots, strict=False):
                if pilot:
                    u.name = f"{u.name} ({pilot})"
            loadout, weapons = apply_loadout(g, r.mission_type, f.loadout or None)
            if f.livery and liveries.known(f.aircraft, f.livery):
                for u in g.units:
                    u.livery_id = f.livery
            elif f.livery:
                self.warnings.append(f"{flight_name}: livery '{f.livery}' isn't known for the {a['name']}; "
                                     "DCS will use its default.")
            for i, u in enumerate(g.units):
                # set_player/set_client also give the jet its radio channel table, which the
                # comm plan below fills in; setting .skill alone leaves the radios unset.
                if r.singleplayer and idx == 0 and i == 0:
                    u.set_player()
                elif i < f.slots:
                    u.set_client()
                else:
                    u.skill = SKILLS["hard"]
            self.player_groups[flight_name] = g
            applied = self.comm_plan.apply(g, idx)
            route = self.route_player(g, cruise_alt, cruise_spd, heli, f)
            if heli:
                self.heli_groups.append(group_name)

            carrier = f.base == "carrier"
            origin = self.carrier.position if carrier else self.home.position
            nm = origin.distance_to_point(self.target) / 1852
            base = self.carrier.name if carrier else self.home.name
            kit = ", ".join(weapons) or "none"
            pilots = [f"{f.number}-{i} {p}" for i, p in enumerate(f.pilots, start=1) if p]
            crew = (f"{f.slots} seat{'s' if f.slots > 1 else ''}"
                    + (f" + {f.ai_wingmen} AI" if f.ai_wingmen else "") + " ×")
            lines = [f"{group_name}: {crew} {a['name']} from {base} ({f.start} start), "
                     f"{nm:.0f} nm to target. Tasked {maintask.name}."]
            if getattr(f, "timing", None):
                lines.append(f"  {f.timing}.")
            lines.append(f"  Loadout ({loadout}): {kit}")
            if applied:
                lines.append("  Radio presets: " + CommPlan.describe(applied))
            if f.dtc and f.aircraft in dtc.SUPPORTED:
                self.add_cartridge(g, f, flight_name, route, applied)
                lines.append("  Data cartridge loaded at spawn (route, comms, threats).")
            if pilots:
                lines.append("  Pilots: " + ", ".join(pilots))
            self.brief.flights.extend(lines)
            self.cards.append({
                "name": flight_name, "aircraft": a["name"], "type": a["cls"],
                "squadron": f.squadron, "seats": f.slots, "ai": f.ai_wingmen, "base": base,
                "pilots": pilots, "timing": getattr(f, "timing", None),
                "start": f.start, "loadout": f"{loadout}: {kit}",
                "route": route, "origin": origin, "carrier": carrier,
                "radios": radio_table(applied)})
            self.player_warnings(f, a, flight_name, nm, heli, weapons)

    def spawn_player_group(self, f, a, maintask, group_name, flight_name, cruise_alt, cruise_spd):
        """The flight's group: in the air, on the carrier or at the home field."""
        size = f.slots + f.ai_wingmen
        try:
            if f.start == "air":
                origin = self.carrier.position if f.base == "carrier" else self.home.position
                pos = origin.point_from_heading(origin.heading_between_point(self.target), 8000)
                return self.m.flight_group_inflight(self.blue, group_name, a["cls"], pos, cruise_alt,
                                                    cruise_spd, maintask=maintask, group_size=size)
            if f.base == "carrier":
                return self.m.flight_group_from_unit(self.blue, group_name, a["cls"], self.carrier,
                                                     maintask=maintask, start_type=self.START_TYPES[f.start],
                                                     group_size=size)
            return self.m.flight_group_from_airport(self.blue, group_name, a["cls"], self.home,
                                                    maintask=maintask, start_type=self.START_TYPES[f.start],
                                                    group_size=size)
        except NoParkingSlotError as e:
            raise MissionError(
                f"{self.home.name} ran out of parking for {a['name']} ({flight_name}). "
                "Try fewer slots, a bigger base, or an air start.") from e

    def player_warnings(self, f, a, flight_name, nm, heli, weapons):
        if not heli and nm > 300 and not (self.has_boom or self.has_drogue):
            self.warnings.append(
                f"{flight_name}: target is {nm:.0f} nm away and there's no tanker; "
                "check your fuel or start in the air.")
        if heli and nm > 80 and f.start != "air":
            self.warnings.append(
                f"{flight_name}: target is {nm:.0f} nm away, a long haul for a helicopter. "
                "Consider an in-air start or a closer friendly base.")
        if not weapons and f.start == "air":
            self.warnings.append(
                f"{flight_name}: no stores could be loaded for {a['name']}, and an air "
                "start means no chance to rearm.")

    # -------------------------------------------------------------------- timing
    STARTUP_S = {"cold": 20 * 60, "hot": 8 * 60, "runway": 3 * 60, "air": 0}

    def tot_seconds(self):
        """TOT as seconds after mission start, or None."""
        if not self.req.tot:
            return None
        hh, mm = map(int, self.req.tot.split(":"))
        sh, sm = TIMES[self.req.time_of_day]
        return ((hh * 60 + mm) - (sh * 60 + sm)) % (24 * 60) * 60

    def clock(self, seconds):
        sh, sm = TIMES[self.req.time_of_day]
        t = int(sh * 3600 + sm * 60 + seconds) % 86400
        return f"{t // 3600:02d}:{t % 3600 // 60:02d}"

    def latlng_point(self, value, near, max_km=1500):
        try:
            lat, lng = float(value[0]), float(value[1])
            p = Point.from_latlng(LatLng(lat, lng), self.terrain)
        except (TypeError, ValueError, IndexError):
            return None
        return p if p.distance_to_point(near) < max_km * 1000 else None

    def route_player(self, g, alt, spd, heli, f):
        """Adds waypoints and returns them as cartridge steerpoints."""
        r = self.req
        origin = self.carrier.position if f.base == "carrier" else self.home.position
        tgt = self.cap_station if r.mission_type == "cap" else self.target
        route = []

        def wp(pos, name, kind, key):
            g.add_waypoint(pos, alt, spd, name=name)
            route.append({"name": name, "pos": pos, "alt": alt, "speed": spd, "kind": kind,
                          "key": key, "agl": heli, "idx": len(g.points) - 1})

        overrides = {}
        for key, val in (f.route or {}).items():
            key = "ingress" if key == "transit" else key  # older saved setups
            if key in routes.EDITABLE:
                pt = self.latlng_point(val, tgt, 400)
                if pt:
                    overrides[key] = pt
        carrier = f.base == "carrier"
        extra = [] if r.chain else [o["pos"] for o in self.secondaries]
        plan = routes.plan(origin, origin, tgt, r.mission_type, heli, overrides, extra,
                           recovery_heading=self.carrier_heading if carrier else None)
        for step in plan:
            kind = "HOME" if carrier and step["key"] == "return" else step["kind"]
            wp(step["pos"], step["name"], kind, step["key"])
        if heli:
            for p in g.points[1:]:
                p.alt_type = "RADIO"
        if not carrier:
            g.land_at(self.home)
            route.append({"name": self.home.name, "pos": self.home.position, "alt": 0,
                          "speed": spd, "kind": "HOME", "key": "land"})
        self.apply_tot(g, f, origin, route, spd)
        return route

    def apply_tot(self, g, f, origin, route, spd):
        """Locks the first target waypoint's ETA to the TOT and works out the push."""
        tot = self.tot_seconds()
        f.timing = None
        if tot is None:
            return
        tgt = next((w for w in route if w["kind"] == "TGT"), None)
        if not tgt:
            return
        mps = spd / 3.6
        legs, prev = 0.0, origin
        for w in route:
            legs += prev.distance_to_point(w["pos"])
            prev = w["pos"]
            if w is tgt:
                break
        earliest = self.STARTUP_S[f.start] + legs / mps
        point = g.points[tgt["idx"]]
        point.ETA = tot
        point.ETA_locked = True
        ip = next((w for w in route if w["kind"] == "IP"), None)
        push = tot - (ip["pos"].distance_to_point(tgt["pos"]) / mps if ip else 0)
        f.timing = f"TOT {self.req.tot}" + (f", leave Ingress at {self.clock(push)}" if ip else "")
        if earliest > tot:
            self.warnings.append(
                f"{f.callsign} {f.number} can't make TOT {self.req.tot} from a {f.start} start "
                f"(earliest about {self.clock(earliest)}).")

    def add_cartridge(self, g, f, flight_name, route, applied):
        name = dtc.cartridge_name(flight_name, f.aircraft)
        dests = [] if f.base == "carrier" else [{"name": self.home.name,
                                                 "pos": self.home.position}]
        text = dtc.build(f.aircraft, name, self.terrain.name, route=route,
                         radios=applied, orbits=self.orbits, threats=self.threats,
                         dests=dests, carrier=self.carrier_info if f.base == "carrier" else None)
        if text:
            self.dtc_files[name] = text
            for u in g.units:
                dtc.bind(u, name)
