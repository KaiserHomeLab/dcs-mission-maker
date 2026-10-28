"""Map preview and era summary for the builder UI, without building a mission."""
import functools

from dcs.mapping import LatLng, Point

from .. import eras, routes
from ..aircraft import AIRCRAFT
from ..theaters import THEATERS
from .common import latlng_pair, resolve_offset
from .request import DIFFICULTIES, MISSION_TYPES


@functools.cache
def _terrain(key):
    return THEATERS[key].terrain_cls()


def map_points(req_json):
    """Rough mission geometry for the UI map (no mission is built)."""
    t = THEATERS.get(req_json.get("theater"))
    if not t:
        return []
    terrain = _terrain(t.key)
    blue = req_json.get("blue_base") if req_json.get("blue_base") in t.blue_bases else t.default_blue
    red_names = [b.name for b in t.red_bases]
    red = t.red_base(req_json.get("red_base") if req_json.get("red_base") in red_names
                     else t.default_red)
    home = terrain.airports[blue].position
    red_ap = terrain.airports[red.name].position
    mt = req_json.get("mission_type")
    target = (resolve_offset(terrain, t.red_sea) if mt == "antiship" and t.red_sea
              else resolve_offset(terrain, red.inland))
    pts = [{"kind": "home", "label": f"Home: {blue}", "pos": latlng_pair(home)},
           {"kind": "enemy", "label": f"Enemy airfield: {red.name}", "pos": latlng_pair(red_ap)},
           {"kind": "bulls", "label": "Bullseye", "pos": latlng_pair(home.lerp(target, 0.5))}]
    if mt == "cap":
        pts.append({"kind": "target", "label": "CAP station", "pos": latlng_pair(home.lerp(red_ap, 0.45))})
    elif mt != "free":
        pts.append({"kind": "target", "label": "Target area", "pos": latlng_pair(target)})
    else:
        pts.append({"kind": "target", "label": "Range area", "pos": latlng_pair(target)})
    if t.blue_carrier and any(f.get("base") == "carrier" for f in req_json.get("flights", [])):
        pts.append({"kind": "carrier", "label": "Carrier", "pos": latlng_pair(resolve_offset(terrain, t.blue_carrier))})
    nm = home.distance_to_point(target) / 1852
    flight_routes = []
    carrier = resolve_offset(terrain, t.blue_carrier) if t.blue_carrier else None
    carrier_hdg = (terrain.airports[t.blue_carrier.anchor].position.heading_between_point(carrier)
                   if carrier else None)
    for f in req_json.get("flights", []):
        on_carrier = f.get("base") == "carrier" and carrier
        origin = carrier if on_carrier else home
        heli = AIRCRAFT.get(f.get("aircraft"), {}).get("helicopter", False)
        tgt = home.lerp(red_ap, 0.45) if mt == "cap" else target
        overrides = {}
        for key, val in (f.get("route") or {}).items():
            key = "ingress" if key == "transit" else key
            if key in routes.EDITABLE:
                try:
                    pt = Point.from_latlng(LatLng(float(val[0]), float(val[1])), terrain)
                except (TypeError, ValueError, IndexError):
                    continue
                if pt.distance_to_point(tgt) < 400000:
                    overrides[key] = pt
        steps = routes.plan(origin, origin, tgt, mt if mt in MISSION_TYPES else "cas", heli,
                            overrides, recovery_heading=carrier_hdg if on_carrier else None)
        flight_routes.append({"origin": latlng_pair(origin), "steps": [
            {"key": s_["key"], "name": s_["name"], "pos": latlng_pair(s_["pos"]),
             "editable": s_["key"] in routes.EDITABLE} for s_ in steps]})
    return {"points": pts, "distance_nm": round(nm), "routes": flight_routes}


def preview(req_json: dict) -> dict:
    """Era/enemy summary for the UI, without building a mission."""
    flights = [(f.get("aircraft"), int(f.get("slots") or 1)) for f in req_json.get("flights", [])
               if f.get("aircraft") in AIRCRAFT]
    era, side = eras.detect(flights)
    if req_json.get("era") in eras.ERAS:
        era = req_json["era"]
    diff = req_json.get("difficulty") if req_json.get("difficulty") in DIFFICULTIES else "medium"
    out = eras.summary(era, side, diff)
    out["detected_era"] = eras.detect(flights)[0]
    out["side"] = side
    out.update(map_points(req_json) or {})
    return out
