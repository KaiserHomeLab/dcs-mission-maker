"""Third-party scripts and their glue, forced mission options and the completion trigger."""
import os

from dcs import vehicles
from dcs.action import Coalition, DoScriptFile, MessageToAll, MessageToCoalition, SetFlag
from dcs.condition import GroupDead, TimeAfter, UnitDead
from dcs.forcedoptions import ForcedOptions
from dcs.triggers import TriggerOnce, TriggerStart

from .. import scripts
from .request import F10_VIEWS, LABELS, MISSION_TYPES

# Debrief flags: DEBRIEF_FLAG = all objectives done, DEBRIEF_FLAG + 1 + i = objective i done.
DEBRIEF_FLAG = 9000


class ScriptingMixin:
    """Third-party scripts and their glue, forced mission options and the completion trigger."""

    # ---------------------------------------------------------------- scripts
    def add_scripts(self):
        r = self.req
        if not r.scripts:
            return
        start = TriggerStart(comment="Load scripts")
        loaded = []
        for sid in r.scripts:
            if sid in ("ctld", "csar"):
                if not self.heli_groups:
                    self.warnings.append(
                        f"{scripts.CATALOG[sid]['name']} needs a helicopter flight; skipped.")
                    continue
                path = self.write_glue(sid, self.glue_for(sid))
            elif sid == "skynet":
                if not any(t["name"] != "SHORAD" and t["range"] > 12000 for t in self.threats) \
                        and not self.forces.get("ewr"):
                    self.warnings.append("Skynet loaded, but this mission has no enemy SAMs "
                                         "or radars for it to run.")
                path = scripts.path_for(sid)
            elif sid == "hound":
                if not self.awacs_unit:
                    self.warnings.append("Hound ELINT needs the AWACS as its sensor; enable "
                                         "AWACS (Vietnam era or later). Skipped.")
                    continue
                path = scripts.path_for(sid)
            else:
                path = scripts.path_for(sid)
            start.add_action(DoScriptFile(self.m.map_resource.add_resource_file(path)))
            loaded.append(scripts.CATALOG.get(sid, {}).get("name", sid.split(":", 1)[-1]))
            # Config glue right after its library.
            if sid == "skynet":
                start.add_action(DoScriptFile(self.m.map_resource.add_resource_file(
                    self.write_glue("skynet", scripts.skynet_glue()))))
            elif sid == "hound":
                start.add_action(DoScriptFile(self.m.map_resource.add_resource_file(
                    self.write_glue("hound", scripts.hound_glue([self.awacs_unit])))))
        if loaded:
            self.m.triggerrules.triggers.append(start)
            self.brief.situation.append("Scripts: " + ", ".join(loaded) + ".")

    def glue_for(self, sid):
        home = self.home.position
        templ_pos = home.point_from_heading(90, 400)
        if sid == "ctld":
            self.m.triggers.add_triggerzone(home, 800, False, "CTLD Pickup")
            for name, utype, n in (("CTLD Infantry", vehicles.Infantry.Soldier_M4, 6),
                                   ("CTLD Humvee", vehicles.Unarmed.Hummer, 1)):
                g = self.ground_group(name, [(utype, 0, i * 5) for i in range(n)], templ_pos,
                                      country=self.blue)
                g.late_activation = True
            return scripts.ctld_glue(self.heli_groups, "CTLD Pickup", "CTLD Infantry",
                                     "CTLD Humvee")
        if sid == "csar":
            self.m.triggers.add_triggerzone(home, 600, False, "MASH Home")
            g = self.ground_group("CSAR Pilot", [(vehicles.Infantry.Soldier_M4, 0, 0)],
                                  templ_pos.point_from_heading(0, 50), country=self.blue)
            g.late_activation = True
            return scripts.csar_glue(self.heli_groups, "CSAR Pilot", "MASH",
                                     "CSAR Survivor" if self.req.mission_type == "csar" else None)
        raise KeyError(sid)

    def write_glue(self, sid, text):
        path = os.path.join(self.workdir, f"dmm_{sid}_config.lua")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    # ---------------------------------------------------- options & kneeboard
    def apply_options(self):
        o, fo = self.req.options, self.m.forced_options
        fo.labels = LABELS[o["labels"]]
        fo.options_view = F10_VIEWS[o["f10"]]
        fo.external_views = bool(o["external_views"])
        fo.fuel = bool(o["unlimited_fuel"])
        fo.weapons = bool(o["unlimited_weapons"])
        fo.easy_communication = bool(o["easy_comms"])
        fo.civil_traffic = (ForcedOptions.CivilTraffic.Medium if o["civil_traffic"]
                            else ForcedOptions.CivilTraffic.Off)
        fo.birds = 1000 if o["birds"] else 0
        extras = [k.replace("_", " ") for k in ("unlimited_fuel", "unlimited_weapons") if o[k]]
        if extras:
            self.brief.situation.append("Training aids: " + ", ".join(extras) + ".")

    # ------------------------------------------------------------ completion
    def add_completion_trigger(self):
        m = self.m
        hello = TriggerOnce(comment="Mission start message")
        hello.add_condition(TimeAfter(5))
        hello.add_action(MessageToCoalition(
            Coalition.Blue, m.string(f"{MISSION_TYPES[self.req.mission_type]}: check your "
                                     "briefing (kneeboard / F10 map) for tasking."), 20))
        m.triggerrules.triggers.append(hello)
        if not self.objectives:
            return

        def dead(t, units):
            for kind, uid in units:
                t.add_condition(GroupDead(uid) if kind == "group" else UnitDead(uid))

        # Each objective sets a user flag the DCS server hook reads for the debrief.
        for i, o in enumerate(self.objectives):
            o["flag"] = DEBRIEF_FLAG + 1 + i
            t = TriggerOnce(comment=f"{o['name']} complete")
            dead(t, o["units"])
            t.add_action(SetFlag(o["flag"]))
            if len(self.objectives) > 1:
                t.add_action(MessageToCoalition(Coalition.Blue, m.string(
                    f"{o['name']} destroyed."), 15))
            m.triggerrules.triggers.append(t)
        done = TriggerOnce(comment="Mission complete")
        dead(done, [u for o in self.objectives for u in o["units"]])
        done.add_action(SetFlag(DEBRIEF_FLAG))
        done.add_action(MessageToAll(m.string(
            "All objectives destroyed. Mission accomplished - RTB!"), 30))
        m.triggerrules.triggers.append(done)
