"""Briefing text, kneeboards and the Briefing Room export."""
import os
from pathlib import Path

from .. import eras, integrations, kneeboard, navdata, threatdb
from .common import JTAC_FREQ, bearing_nm, bra, fmt_latlon, latlng_pair
from .request import MISSION_TYPES, TIMES
from .scripting import DEBRIEF_FLAG


class BriefingMixin:
    """Briefing text, kneeboards and the Briefing Room export."""

    def srs(self):
        """The SRS server for this mission: the one set in the builder, else SRS_ADDRESS."""
        if self.req.srs:
            return {"address": self.req.srs, "note": self.req.srs_note}
        return integrations.srs()

    def bulls(self, pos):
        """True bearing / range in nm from the bullseye (great circle, so it matches
        what the Briefing Room computes from lat/long)."""
        return bra(self.bullseye, pos)

    def dark_cockpit(self):
        """Dark kneeboard pages when the cockpit will be dark: night, or a winter dawn/dusk."""
        r = self.req
        return r.time_of_day == "night" or (r.season == "winter" and r.time_of_day in ("dawn", "dusk"))

    def add_kneeboards(self):
        r = self.req
        hh, mm = TIMES[r.time_of_day]
        mission = {
            "title": self.title, "start": f"{hh:02d}{mm:02d} local",
            "tasking": self.brief.tasking,
            "support": ([f"SRS voice server: {srs['address']}" + (f" ({srs['note']})" if srs["note"] else "")]
                        if (srs := self.srs()) else []) + list(self.brief.comms),
            "threats": [f"{t['name']}: {fmt_latlon(t['pos'])}, ~{t['range'] / 1852:.0f} nm ring, "
                        f"bulls {self.bulls(t['pos'])}" for t in self.threats][:8],
            "weather": f"{r.weather.capitalize()}, wind {r.wind}"
                       + (f" from {self.wind_from:03d}" if self.wind_strength else "")
                       + f", {self.m.weather.season_temperature:.0f} C.",
            "bullseye": fmt_latlon(self.bullseye),
            "home": self.home_card,
            "night": self.dark_cockpit(),
        }
        for i, card in enumerate(self.cards):
            card["steerpoints"] = [{
                "name": wp["name"], "latlon": fmt_latlon(wp["pos"]),
                "alt_ft": (f"{round(wp['alt'] * 3.281, -2):,.0f}" + (" AGL" if wp.get("agl") else "")
                           if wp["alt"] else "-"),
                "bulls": self.bulls(wp["pos"])} for wp in card["route"]]
            # DCS shows a type's pages in filename order: flight page, then its route page
            for suffix, render in (("", kneeboard.flight_page), ("_route", kneeboard.route_page)):
                path = os.path.join(self.workdir, f"kneeboard_{i + 1}{suffix}.png")
                render(card if suffix == "" else self.nav_log(card), mission, path)
                self.m.add_aircraft_kneeboard(card["type"], Path(path))

    # ----------------------------------------------------------------- route page
    def nav_log(self, card):
        """Route page data for one flight: legs with course, distance, ETA, what to do at
        each waypoint, and local x/y (km, north up) for the sketch."""
        start = self.STARTUP_S[card["start"]]
        route, origin = card["route"], card["origin"]
        mps = (route[0]["speed"] if route else 800) / 3.6
        legs, prev, total = [], origin, 0.0
        for w in route:
            crs, nm = bearing_nm(prev, w["pos"])
            total += nm
            legs.append({"crs": crs, "nm": nm, "total": total})
            prev = w["pos"]
        tot, tgt_i = self.tot_seconds(), next((i for i, w in enumerate(route) if w["kind"] == "TGT"), None)
        timed = tot is not None and tgt_i is not None
        zero = tot - legs[tgt_i]["total"] * 1852 / mps if timed else start   # time at the origin

        def eta(i):
            return zero + legs[i]["total"] * 1852 / mps

        if timed:
            eta_note = f"ETAs are worked back from TOT {self.req.tot}."
        else:
            eta_note = (f"ETAs assume a {card['start']} start (about {start // 60} min to taxi and "
                        "take off) and no holding." if start else "ETAs from mission start.")
        rows, notes = [], []
        for i, (w, leg) in enumerate(zip(route, legs, strict=True), start=1):
            rows.append({
                "n": i, "name": w["name"], "crs": f"{round(leg['crs']) % 360:03d}",
                "leg": f"{leg['nm']:.0f}", "total": f"{leg['total']:.0f}",
                "alt": ("-" if not w["alt"]
                        else f"{round(w['alt'] * 3.281, -2):,.0f}" + (" AGL" if w.get("agl") else "")),
                "kt": f"{w['speed'] / 1.852:.0f}" if w["alt"] else "-", "eta": self.clock(eta(i - 1))})
            notes.append((i, w["name"], self.waypoint_note(w, card)))

        def local(p):
            """km east, km north of the origin (pydcs x is north, y is east)."""
            return (p.y - origin.y) / 1000, (p.x - origin.x) / 1000

        threats = [{"name": t["name"], "xy": local(t["pos"]), "r": t["range"] / 1000}
                   for t in self.threats]
        return {**card, "rows": rows, "notes": notes, "eta_note": eta_note,
                "sketch": {"origin": (0.0, 0.0), "points": [local(w["pos"]) for w in route],
                           "kinds": [w["kind"] for w in route], "threats": threats,
                           "bulls": local(self.bullseye)}}

    def waypoint_note(self, w, card):
        """One line on what the flight does at a waypoint, for this mission type."""
        mt, key = self.req.mission_type, w.get("key", "")
        heli = card["type"].helicopter
        tgt_what = {
            "cas": "Target area: friendly troops in contact. "
                   + (f"Check in with JTAC Axeman on {JTAC_FREQ}.000 AM for targets and the laser code."
                      if self.jtac_line else "Find the enemy column and confirm friendlies before you shoot."),
            "sead": "Air defense site. Shooters fire HARMs or stand-off weapons from outside the rings; "
                    "the rest of the package waits until the radars are down.",
            "strike": "Supply depot. One pass if you can: drop and egress, don't loiter over the defenses.",
            "antiship": "Enemy ships. Launch from outside their SAM range and turn away.",
            "csar": ("Survivor: land next to the smoke once the escorts call the area clear, pick up, "
                     "and leave low and fast." if heli else
                     "Survivor: sanitise the area and cover the helicopter while it lands and picks up."),
        }
        if key == "join":
            return "Join up. Lead holds the briefed speed so wingmen can catch up; check in on the flight frequency."
        if key == "ingress" and mt == "cap":
            return "Fence in (master arm, countermeasures, lights) and head for the CAP station."
        if key == "ingress":
            timing = f" {card['timing']}." if card.get("timing") else ""
            return f"Fence in (master arm, countermeasures, lights) and leave on time.{timing}"
        if key == "ip" and mt == "csar" and heli:
            return "Start of the run-in to the survivor: drop to low level, escorts ahead of you."
        if key == "ip":
            return "Start of the attack run. From here it's a straight run to the target; set up weapons."
        if key == "target":
            return tgt_what.get(mt, "Target.")
        if key.startswith("obj"):
            o = next((o for o in self.secondaries if o["name"].endswith(key[3:])), None)
            return f"Follow-on objective: {o['what']}." if o else "Follow-on objective."
        if key == "cap":
            return "CAP station: fly a race-track between CAP and CAP 2. Commit on bandits heading for friendlies."
        if key == "cap2":
            return "Far end of the CAP race-track. Turn back toward CAP."
        if key == "range":
            return "Training range: no threats. Practise whatever you briefed."
        if key == "egress" and mt == "cap":
            return "Leave the station on a different line than you came in on. Fence out when clear."
        if key == "egress":
            return ("Turns off the attack axis, so you don't fly home over the defenses you came in "
                    "through. Fence out when clear.")
        if key == "return" and card.get("carrier"):
            return "Marshal 20 km astern of the carrier, then recover. Check in on the carrier frequency."
        if key == "return":
            return "Recovery fix: get the ATIS, check in with tower and set up for the runway in use."
        if key == "land":
            return f"Land at {w['name']}."
        return ""

    # ---------------------------------------------------------- briefing room
    def export_brief(self, filename):
        """Everything the Briefing Room page shows, with lat/lng positions."""
        r = self.req
        hh, mm = TIMES[r.time_of_day]
        s = eras.summary(self.era, self.player_side, r.difficulty)

        def orbit(o):
            half = o["length"] / 2
            return {"name": o["name"], "alt_ft": round(o["alt"] * 3.281, -2),
                    "line": [latlng_pair(o["center"].point_from_heading(o["course"] + 180, half)),
                             latlng_pair(o["center"].point_from_heading(o["course"], half))]}

        primary = next((o for o in self.objectives if o["name"] == "Primary objective"), {})
        objectives_out = [{"name": "Primary", "what": MISSION_TYPES[r.mission_type],
                           "pos": latlng_pair(self.target), "hidden": False, "flag": primary.get("flag")}]
        objectives_out += [{"name": o["name"], "what": o["what"], "pos": latlng_pair(o["pos"]),
                            "hidden": bool(r.chain), "flag": o.get("flag")} for o in self.secondaries]
        flights = []
        for i, c in enumerate(self.cards):
            flights.append({
                "name": c["name"], "aircraft": c["aircraft"], "type": c["type"].id, "squadron": c["squadron"],
                "seats": c["seats"], "ai": c["ai"], "base": c["base"], "start": c["start"],
                "loadout": c["loadout"], "presets": c["presets"], "pilots": c["pilots"],
                "timing": c["timing"], "kneeboard": i + 1,
                "kneeboards": [{"page": f"{i + 1}", "label": "Flight"}, {"page": f"{i + 1}_route", "label": "Route"}],
                "route": [{"name": w["name"], "kind": w["kind"], "pos": latlng_pair(w["pos"]),
                           "alt_ft": round(w["alt"] * 3.281, -2) if w["alt"] else 0,
                           "agl": bool(w.get("agl")), "bulls": self.bulls(w["pos"])}
                          for w in c["route"]]})
        return {
            "file": filename, "title": self.title,
            "meta": {"map": self.theater.label, "mission": MISSION_TYPES[r.mission_type],
                     "mission_type": r.mission_type, "era": s["era_label"],
                     "you": s["player_side"], "enemy": s["enemy_side"],
                     "difficulty": r.difficulty, "date": f"{self.m.start_time:%d %b %Y}",
                     "start": f"{hh:02d}:{mm:02d}", "tot": r.tot or None,
                     "weather": r.weather, "wind": r.wind,
                     "wind_from": self.wind_from if self.wind_strength else None,
                     "temp_c": round(self.m.weather.season_temperature), "night": self.dark_cockpit()},
            "situation": self.brief.situation, "tasking": self.brief.tasking,
            "support": self.brief.comms, "notes": self.warnings,
            "home": {"name": self.home.name, "pos": latlng_pair(self.home.position),
                     "card": self.home_card},
            "enemy_base": {"name": self.red_airport.name, "pos": latlng_pair(self.red_airport.position)},
            "bullseye": {"pos": latlng_pair(self.bullseye), "text": fmt_latlon(self.bullseye)},
            "carrier": ({"name": self.carrier.name, "pos": latlng_pair(self.carrier.position)}
                        if self.carrier else None),
            "objectives": objectives_out,
            "debrief_flag": DEBRIEF_FLAG if self.objectives else None,
            "srs": self.srs(),
            "threats": [{"name": t["name"], "pos": latlng_pair(t["pos"]), "range_m": t["range"],
                         "text": fmt_latlon(t["pos"]), "bulls": self.bulls(t["pos"])}
                        for t in self.threats],
            "orbits": [orbit(o) for o in self.orbits],
            "flot": [latlng_pair(p) for p in self.flot] if self.flot else None,
            "friendly_armor": latlng_pair(self.friendly_armor) if self.friendly_armor else None,
            "jtac": ({"pos": latlng_pair(self.jtac_pos), "text": self.jtac_line}
                     if self.jtac_pos else None),
            "flights": flights, "ai_flights": self.ai_cards,
            "oob": self.order_of_battle(),
        }

    def order_of_battle(self):
        """Enemy systems for the Threat ID cards: one entry per system, with counts
        and site positions (none for pop-ups, fighters and not-yet-revealed targets)."""
        found = {}
        surface = list(self.red.vehicle_group) + list(self.red.ship_group)
        air = list(self.red.plane_group) + list(self.red.helicopter_group)
        for g in surface + air:
            flying = g in air
            # Pop-ups and not-yet-unlocked targets are "possible", with no position.
            secret = g.name.startswith("Popup") or (g.late_activation and not flying)
            for u in g.units:
                key = threatdb.key_for(u.type, g.name)
                if not key:
                    continue
                e = found.setdefault(key, {**threatdb.card(key), "count": 0, "sites": [],
                                           "possible": True})
                e["count"] += 1
                e["possible"] = e["possible"] and secret
                if not secret and not flying:
                    pos = latlng_pair(g.units[0].position)
                    if pos not in e["sites"]:
                        e["sites"].append(pos)
        order = {"sam": 0, "fighter": 1, "short": 2, "ship": 3, "ewr": 4, "armor": 5, "artillery": 6}
        return sorted(found.values(), key=lambda e: (order[e["category"]], e["title"]))

    def write_briefing(self):
        r, m = self.req, self.m
        self.home_card = navdata.airfield_card(self.theater.beacons, self.home, self.wind_from,
                                               calm=not self.wind_strength)
        title = r.title.strip() or f"{MISSION_TYPES[r.mission_type]} - {self.theater.label}"
        m.set_sortie_text(title)
        s = eras.summary(self.era, self.player_side, r.difficulty)
        m.set_description_text(
            f"{s['era_label']}. {s['player_side']} forces operate from {self.home.name}; "
            f"{s['enemy_side']} forces are concentrated around {self.red_airport.name}.\n\n"
            + "\n".join(self.brief.situation)
            + f"\n\nDifficulty: {r.difficulty}. Weather: {r.weather}. Wind: {r.wind}"
            + (f" from {self.wind_from:03d}°" if self.wind_strength else "")
            + ".\nGenerated by DCS Mission Maker.")
        self.briefing_text = (
            "TASKING\n" + "\n".join(self.brief.tasking)
            + "\n\nFLIGHTS\n" + "\n".join(self.brief.flights)
            + ("\n\nSUPPORT\n" + "\n".join(self.brief.comms) if self.brief.comms else "")
            + f"\n\nBullseye: {fmt_latlon(self.bullseye)} (target is {self.bulls(self.target)} "
            "from bulls, true).\n"
            + f"Home plate: {self.home_card}.\n"
            "Loadouts are a starting point: rearm with the ground crew if you want something "
            "different."
            + ("\n\nNOTES\n" + "\n".join(self.warnings) if self.warnings else ""))
        m.set_description_bluetask_text(self.briefing_text)
        m.set_description_redtask_text("Defend.")
        self.title = title
