"""Mission depth: secondary objectives (optionally chained), the CAS front
line, pop-up air defenses and zone triggers."""
import itertools

from dcs import task
from dcs.action import ActivateGroup, Coalition, MessageToCoalition, SetFlag
from dcs.condition import GroupDead, PartOfCoalitionInZone
from dcs.drawing import Rgba
from dcs.drawing.drawings import StandardLayer
from dcs.triggers import TriggerOnce

SECONDARY_KINDS = ["sam", "artillery", "convoy", "radar"]

_flag = [100]


def next_flag():
    _flag[0] += 1
    return _flag[0]


def reset_flags():
    _flag[0] = 100


def zone_entry_flag(b, name, pos, radius_m):
    """A trigger zone that sets a flag the first time any blue unit enters it."""
    z = b.m.triggers.add_triggerzone(pos, radius_m, True, name)
    flag = next_flag()
    t = TriggerOnce(comment=f"Blue enters {name}")
    t.add_condition(PartOfCoalitionInZone("blue", z.id))
    t.add_action(SetFlag(flag))
    b.m.triggerrules.triggers.append(t)
    return flag


def secondary_positions(b, count):
    """Inland points spread around the enemy airfield, clear of the primary."""
    rb = b.red_base
    base = b.red_airport.position
    dist = max(rb.spread_km, rb.inland.distance_km + 4) * 1000
    offsets = [-rb.fan_deg, rb.fan_deg, 0]
    return [base.point_from_heading(rb.inland.bearing + offsets[i], dist) for i in range(count)]


def build_secondary(b, kind, pos, index):
    f = b.forces
    name = f"Objective {index + 2}"
    h = pos.heading_between_point(b.home.position)
    if kind == "sam":
        label, layout = f["sam"]["easy"]
        groups = [b.sam_site(label, layout, pos, f"Obj{index + 2}")]
        what = label
    elif kind == "artillery":
        layout = [(f["artillery"], h + 90, 80 * i) for i in range(-2, 2)] + [(f["truck"], h + 180, 200)]
        groups = [b.ground_group(f"{name} Artillery", layout, pos, heading=h)]
        what = f"{b.type_name(f['artillery'])} artillery battery"
    elif kind == "convoy":
        layout = [(f["truck"], h + 180, 40 * i) for i in range(6)] + [(f["ifv"], h, 60)]
        g = b.ground_group(f"{name} Convoy", layout, pos, heading=h)
        far = pos.point_from_heading(b.red_base.inland.bearing, 3000)
        g.add_waypoint(far, speed=30)
        g.add_waypoint(pos, speed=30)
        groups = [g]
        what = "supply convoy shuttling between depots"
    else:  # radar
        ewr = f.get("ewr")
        if not ewr:
            return build_secondary(b, "artillery", pos, index)
        groups = [b.ground_group(f"EW {name} Radar", [(ewr, 0, 0)], pos)]
        groups.append(b.ground_group(f"{name} Radar Guard",
                                     [(t, brg, dist) for t, brg, dist in f["shorad"]["easy"]], pos))
        what = f"{b.type_name(ewr)} early-warning radar"
    return {"name": name, "kind": kind, "pos": pos, "what": what,
            "units": [("group", g.id) for g in groups], "groups": groups}


def add_secondaries(b):
    r = b.req
    if not r.secondaries or r.mission_type in ("cap", "free"):
        return []
    kinds = list(r.secondary_kinds or [])
    pool = [k for k in SECONDARY_KINDS if k not in kinds]
    b.rng.shuffle(pool)
    kinds = (kinds + pool)[:r.secondaries]
    out = []
    for i, (kind, pos) in enumerate(zip(kinds, secondary_positions(b, len(kinds)), strict=True)):
        out.append(build_secondary(b, kind, pos, i))
    return out


def chain(b, objectives):
    """Objective n+1 spawns when objective n is destroyed."""
    for prev, nxt in itertools.pairwise(objectives):
        for g in nxt["groups"]:
            g.late_activation = True
        t = TriggerOnce(comment=f"Unlock {nxt['name']}")
        for kind, uid in prev["units"]:
            if kind == "group":
                t.add_condition(GroupDead(uid))
        for g in nxt["groups"]:
            t.add_action(ActivateGroup(g.id))
        t.add_action(MessageToCoalition(Coalition.Blue, b.m.string(
            f"NEW TASKING - {nxt['name']}: {nxt['what']} at {b.fmt(nxt['pos'])}, "
            f"bullseye {b.bulls(nxt['pos'])}. Proceed when able."), 45))
        b.m.triggerrules.triggers.append(t)


# ------------------------------------------------------------------ CAS FLOT
def add_front_line(b, armor):
    """Friendly armor holds 6 km short of the target; the enemy column pushes
    2 km toward it. The line between them is drawn on the F10 map."""
    home_dir = b.heading_to_home()
    blue = b.forces_player
    blue_pos = b.target.point_from_heading(home_dir, 6000)
    layout = [(blue["tanks"]["medium"], home_dir + 90, 120 * i) for i in range(-1, 2)] \
        + [(blue["ifv"], home_dir + 90, 120 * i + 60) for i in range(-1, 1)]
    g = b.ground_group("Friendly Armor", layout, blue_pos, heading=(home_dir + 180) % 360,
                       country=b.blue)
    g.points[0].tasks.append(task.OptROE(task.OptROE.Values.ReturnFire))
    armor.add_waypoint(b.target.point_from_heading(home_dir, 2000), speed=10)
    mid = b.target.point_from_heading(home_dir, 4000)
    a = mid.point_from_heading(home_dir + 90, 12000)
    c = mid.point_from_heading(home_dir - 90, 12000)
    b.flot = (a, c)
    b.friendly_armor = blue_pos
    layer = b.m.drawings.get_layer(StandardLayer.Common)
    layer.add_line_segment(a, c, color=Rgba(220, 40, 40, 255), line_thickness=6)
    layer.add_text_box(a.point_from_heading(home_dir + 180, 1500), "FLOT",
                       color=Rgba(220, 40, 40, 255), fill=Rgba(255, 255, 255, 120), font_size=18)
    b.brief.situation.append(
        f"Friendly armor holds 6 km short of the target ({b.fmt(blue_pos)}); the front line is "
        "drawn on the F10 map. The enemy column is pushing toward them. Don't shoot south of "
        "the friendlies.")


# ------------------------------------------------------------------- pop-ups
POPUPS_BY_DIFFICULTY = {"easy": 0, "medium": 1, "hard": 2, "extreme": 3}


def add_popups(b):
    n = POPUPS_BY_DIFFICULTY[b.req.difficulty]
    if not b.req.popups or not n or b.req.mission_type in ("cap", "free", "antiship"):
        return
    ptype = b.forces["popup"]
    flag = zone_entry_flag(b, "Popup Zone", b.target, 25000)
    home_dir = b.heading_to_home()
    spots = [b.target.point_from_heading(home_dir + 25, 4000),
             b.target.point_from_heading(home_dir - 25, 6000),
             b.target.point_from_heading(home_dir + 60, 3000)]
    t = TriggerOnce(comment="Pop-up threats")
    from dcs.condition import FlagIsTrue
    t.add_condition(FlagIsTrue(flag))
    for i, pos in enumerate(spots[:n]):
        g = b.ground_group(f"Popup {i + 1}", [(ptype, 0, 0), (ptype, 90, 30)], pos)
        g.late_activation = True
        g.hidden = True
        t.add_action(ActivateGroup(g.id))
    b.m.triggerrules.triggers.append(t)
    b.brief.situation.append("Intel suggests mobile air defenses may be operating near the "
                             "target that aren't on any map.")
