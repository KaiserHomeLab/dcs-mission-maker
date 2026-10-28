"""Flight route planning shared by the generator and the map preview.

Attack missions:  Join -> Push -> Ingress -> Target -> (objectives) -> Egress -> Return
CAP:              Join -> Push -> CAP -> CAP 2 -> Egress -> Return
Free flight:      Join -> Range -> Return

Egress turns off the attack axis toward the side away from the ingress, so
flights don't go home over the defenses they came in through.
"""
EDITABLE = ("ingress", "ip", "egress")


def _between(a, b, dist_m):
    """Point dist_m from a toward b (never past b)."""
    return a.point_from_heading(a.heading_between_point(b), min(dist_m, a.distance_to_point(b)))


def plan(origin, recovery, target, mission_type, heli, overrides=None, extra_targets=(),
         recovery_heading=None):
    """Returns [{"key", "name", "kind", "pos"}] after the spawn point.

    origin/recovery/target are pydcs Points; overrides maps EDITABLE keys to
    Points the user dragged on the map. recovery_heading (the carrier's course)
    puts the Return fix behind a moving carrier instead of short of an airfield.
    kind is STPT, IP, TGT or HOME (cartridge symbology).
    """
    ov = overrides or {}
    scale = 0.4 if heli else 1.0
    d = origin.distance_to_point(target)
    out = []

    def add(key, name, kind, pos):
        out.append({"key": key, "name": name, "kind": kind, "pos": ov.get(key) or pos})
        return out[-1]["pos"]

    if mission_type == "free":
        add("join", "Join", "STPT", _between(origin, target, min(15000 * scale, d * 0.2)))
        last = add("range", "Range", "TGT", target)
    elif mission_type == "cap":
        axis = origin.heading_between_point(target)
        add("join", "Join", "STPT", _between(origin, target, min(15000 * scale, d * 0.2)))
        add("ingress", "Push", "STPT", _between(target, origin, min(40000, d * 0.4)))
        add("cap", "CAP", "TGT", target)
        last = add("cap2", "CAP 2", "STPT", target.point_from_heading(axis + 90, 30000))
        last = add("egress", "Egress", "STPT", _egress(last, recovery, target, 30000 * scale))
    else:
        ip_default = target.point_from_heading(target.heading_between_point(origin),
                                               min(25000 * scale, d * 0.4))
        ip = ov.get("ip") or ip_default
        d_ip = origin.distance_to_point(ip)
        add("join", "Join", "STPT", _between(origin, ip, min(15000 * scale, d_ip * 0.2)))
        add("ingress", "Push", "STPT", _between(ip, origin, min(40000 * scale, d_ip * 0.35)))
        add("ip", "Ingress", "IP", ip)
        last = add("target", "Survivor" if mission_type == "csar" else "Target", "TGT", target)
        for i, pos in enumerate(extra_targets, start=2):
            last = add(f"obj{i}", f"Obj {i}", "TGT", pos)
        last = add("egress", "Egress", "STPT", _egress(last, recovery, ip, 25000 * scale))

    if recovery_heading is not None:   # carrier: fix 20 km astern
        ret = recovery.point_from_heading(recovery_heading + 180, 20000 * scale)
    else:
        ret = _between(recovery, last, 20000 * scale)
    add("return", "Return", "STPT", ret)
    return out


def _egress(last, recovery, avoid, dist_m):
    """Off the direct line home, on the side away from `avoid` (the ingress)."""
    home = last.heading_between_point(recovery)
    a = last.point_from_heading(home + 50, dist_m)
    b = last.point_from_heading(home - 50, dist_m)
    return a if a.distance_to_point(avoid) > b.distance_to_point(avoid) else b
