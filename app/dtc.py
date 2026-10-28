"""Native DCS Data Transfer Cartridges (F/A-18C, F-16C).

A cartridge is two pieces inside the .miz:
  * a JSON file at DTC/<name>.dtc  ->  {"data": {...}, "name": ..., "type": ...}
  * a per-unit block in the mission table:
        ["DTC"] = { ["Cartridges"] = { [1] = { name=..., default=true } },
                    ["AutoLoad"] = true }
The jet loads it at spawn when AutoLoad is set. Sections we leave out keep the
module's defaults.

Format notes come from DCS Retribution's DTC work (PR #966), whose author
checked it against the Mission Editor's own DTC manager
(MissionEditor/modules/me_managerDTC.lua and CoreMods/aircraft/<type>/DTC).
"""
import json
import re

HORNET = "FA-18C_hornet"
VIPER = "F-16C_50"
SUPPORTED = {HORNET, VIPER}
CAP_ORBIT_DIAMETER_M = 5 * 1852.0


def cartridge_name(flight_name, unit_type):
    return re.sub(r"[^\w \-]", "", f"{flight_name} {unit_type}").strip()


def _short(label, n=5):
    return re.sub(r"[^A-Z0-9]", "", label.upper())[:n]


def _ascii(label, n=24):
    return " ".join(label.encode("ascii", "ignore").decode().split())[:n]


# ------------------------------------------------------------------- Hornet
def _hornet_comm(unit, labels):
    defaults = [305.0, 264.0, 265.0, 256.0, 254.0, 250.0, 270.0, 257.0, 255.0, 262.0,
                259.0, 268.0, 269.0, 260.0, 263.0, 261.0, 267.0, 251.0, 253.0, 266.0]
    comm = {}
    for radio_id in (1, 2):
        channels = dict(enumerate(defaults, start=1))
        if unit.radio and radio_id in unit.radio:
            channels.update(unit.radio[radio_id]["channels"])
        table = {"Guard": False}
        for n in range(1, 21):
            freq = float(channels[n])
            table[f"Channel_{n}"] = {"frequency": freq, "modulation": 1 if freq < 88 else 0,
                                     "name": labels.get(round(freq, 3), f"CH {n}")}
        table["Channel_G"] = {"frequency": 243.0, "modulation": 0, "name": "GUARD"}
        table["Channel_M"] = {"frequency": 305.0, "modulation": 0, "name": "MAN"}
        table["Channel_C"] = {"frequency": 30.0, "modulation": 1, "name": "CUE"}
        table["Channel_S"] = {"frequency": 156.05, "modulation": 1, "name": "MAR"}
        comm[f"COMM{radio_id}"] = table
        comm[f"mirror_COMM{radio_id}"] = False
    return comm


def _oa(i):
    return {"isOA": False, "idOA": f"OA{i}", "idOA_Line": f"OA{i}Line", "OA_X": 0, "OA_Y": 0,
            "OA_Alt": 0, "OA_Bearing": 0, "OA_Bearing_Units": 1, "OA_Range": 0,
            "OA_Range_Units": 1, "OA_DeltaX": 0, "OA_DeltaY": 0, "OA_Elevation_Units": 1}


def _hornet_wypt(route, terrain, carrier):
    nav_pts, seq = [], {}
    home, target_done = 1, False
    for n, wp in enumerate(route, start=1):
        alt = min(max(wp["alt"], -609.6), 7620.0)
        entry = {"wypt_num": n, "id": f"STPT{n}", "text_note": _ascii(wp["name"]), "note": "",
                 "x": wp["pos"].x, "y": wp["pos"].y, "alt": alt,
                 "altitudeType": 2 if wp.get("agl") else 1, "velocityType": 3,
                 "R1": True, "R2": False, "R3": False, "R1_order": n, **_oa(n)}
        is_tgt = wp["kind"] == "TGT" and not target_done
        target_done = target_done or is_tgt
        seq[f"STPT{n}"] = {"route_num": 1, "wypt_num": n, "alt": wp["alt"],
                           "altitudeType": entry["altitudeType"], "speed": wp["speed"],
                           "ETA": 0, "FIX_Time": False, "TGT": is_tgt}
        nav_pts.append(entry)
        if wp["kind"] == "HOME":
            home = n
    tacan = {"Mode": 1, "Channel": 1, "ChannelMode": 1, "OnOff": False}
    icls = {"Channel": 1, "OnOff": False}
    acls = {"Frequency": 225.0, "OnOff": False}
    if carrier:
        tacan = {"Mode": 1, "Channel": carrier["tacan"], "ChannelMode": 1, "OnOff": True}
        icls = {"Channel": carrier["icls"], "OnOff": True}
        acls = {"Frequency": carrier["link4"], "OnOff": True}
    return {
        "NAV_PTS": nav_pts, "NAV_ROUTE": [seq, [], []], "terrain": terrain,
        "mirror_NAV_PTS": False,
        "NAV_SETTINGS": {"TACAN": tacan, "ICLS": icls, "ACLS": acls,
                         "AA_Waypoint": {"AA_WP_Number": 59, "AA_WP_Enabled": False},
                         "Home_Waypoint": {"FPAS_HOME_WP": home},
                         "Altitude_Warning": {"Warn_Alt_Rdr": 500, "Warn_Alt_Baro": 2000}},
    }


def _hornet_sa(orbits, threats):
    caps = [{"id": f"CAP_PTS_{i}", "num": i, "x": o["center"].x, "y": o["center"].y,
             "course": o["course"], "length": o["length"], "diameter": CAP_ORBIT_DIAMETER_M,
             "turn_direction": "Left", "note": _short(o["name"])}
            for i, o in enumerate(orbits[:9], start=1)]
    mez = [{"id": f"MEZ_THRTS_{i}", "num": i, "x": t["pos"].x, "y": t["pos"].y,
            "text": _short(t["name"], 8), "threat_type": "Custom",
            "threat_ring_radius": round(t["range"] / 1852.0, 1), "threat_level": 1}
           for i, t in enumerate(threats[:40], start=1)]
    dcltr = dict.fromkeys((
        "Bullseye_TDC_Info", "Waypoint_Info", "Compase_Rose", "Ground_Speed", "Countermeasure_Inventory", "SEQ",
        "CAP", "CORR", "FAOR", "FLOT", "MEZ_Names", "MEZ_Rings"
    ), True)
    return {
        "CAP_PTS": caps, "CORRIDORS": [], "FAOR_FLOT": {"FAOR": [], "FLOT": []},
        "MEZ_THRTS": mez,
        "SETTINGS": {"SENSORS_SETTINGS": {"RWR_Symbols": 1, "FRIEND_Symbols": 3,
                                          "PPLI_tracks": True, "FF_tracks": True,
                                          "SURV_tracks": True, "UNK_tracks": True},
                     "DCLTR_SETTINGS": {"MREJ1": dict(dcltr), "MREJ2": dict(dcltr)}},
        "Default_CAP_Point": 1, "Default_CORRIDORS_Point": 1, "Default_FAOR_Line": 1,
        "Default_FLOT_Line": 1, "Default_MEZ_THRTS_Level": 1, "mirror_MEZ_THRTS": False,
    }


def _hornet_tcn(carrier):
    if not carrier:
        return []
    return [{"callsign": carrier["callsign"], "channel": carrier["tacan"], "modeChannel": "X",
             "display_name": f"{carrier['unit_name']}_P1", "elevation": 0,
             "unitId": carrier["unit_id"], "unitPointNum": 1,
             "x": carrier["pos"].x, "y": carrier["pos"].y}]


# -------------------------------------------------------------------- Viper
def _viper_stpt(n, name, pos, alt, speed, kind, agl=False):
    d = {"number": n, "id": f"STPT{n}", "type": kind, "note": _ascii(name), "x": pos.x, "y": pos.y,
         "alt": alt, "altitudeType": 2 if agl else 1, "R1": kind != "ANCHOR", "R2": False,
         "R3": False, "speed": speed, "velocityType": 3, "TOS": 0, "isTOSEnabled": False,
         "FIX_Time": False, "routeAltitude": alt}
    if d["type"] == "ANCHOR":
        d["type"] = "STPT"
    for k in (1, 2):
        d.update({f"isOAP_{k}": False, f"idOA{k}": f"OA{k}{n}", f"idOA{k}_Line": f"OA{k}{n}Line",
                  f"OAP_{k}_X": 0, f"OAP_{k}_Y": 0, f"OAP_{k}_Alt": 0, f"OAP_{k}_Bearing": 0,
                  f"OAP_{k}_Range": 0, f"OAP_{k}_DeltaX": 0, f"OAP_{k}_DeltaY": 0})
    return d


def _viper_mpd(route, orbits, threats, dests, terrain):
    pts = []
    for wp in route[:20]:
        kind = {"TGT": "TGT", "IP": "IP"}.get(wp["kind"], "STPT")
        pts.append(_viper_stpt(len(pts) + 1, wp["name"], wp["pos"], wp["alt"], wp["speed"],
                               kind, wp.get("agl")))
    for o in orbits:
        if len(pts) >= 24:
            break
        pts.append(_viper_stpt(len(pts) + 1, o["name"], o["center"], o["alt"], 463.0, "ANCHOR"))
    thr = [{"number": i, "id": f"THREAT_PTS{55 + i}", "x": t["pos"].x, "y": t["pos"].y,
            "threatName": "Custom", "radius": t["range"], "alt": 9144, "elev": 0,
            "text": _short(t["name"], 8), "ring": True, "def_num": 1}
           for i, t in enumerate(threats[:15], start=1)]
    dest = [{"number": i, "id": f"DEST{80 + i}", "x": d["pos"].x, "y": d["pos"].y, "alt": 0,
             "text": _short(d["name"], 3) or "DST", "note": d["name"]}
            for i, d in enumerate(dests[:19], start=1)]
    return {"terrain": terrain, "mirror_NAV_PTS": False, "NAV_PTS": pts,
            "mirror_GEO_LINES": False, "GEO_LINES": [],
            "mirror_THREAT_PTS": False, "THREAT_PTS": thr,
            "mirror_DEST": False, "DEST": dest}


# --------------------------------------------------------------------- API
def build(unit_type, name, terrain, *, unit, route, labels, orbits, threats, dests, carrier):
    """Returns the .dtc JSON text for one flight, or None if unsupported."""
    data = {"type": unit_type, "name": name, "terrain": terrain}
    if unit_type == HORNET:
        data["COMM"] = _hornet_comm(unit, labels)
        data["WYPT"] = _hornet_wypt(route, terrain, carrier)
        data["SA"] = _hornet_sa(orbits, threats)
        data["TCN"] = _hornet_tcn(carrier)
    elif unit_type == VIPER:
        data["MPD"] = _viper_mpd(route, orbits, threats, dests, terrain)
    else:
        return None
    return json.dumps({"data": data, "name": name, "type": unit_type}, indent=4)


def bind(unit, name, autoload=True):
    """Adds the per-unit DTC block by wrapping the unit's dict()."""
    original = unit.dict

    def dict_with_dtc():
        d = original()
        d["DTC"] = {"Cartridges": {1: {"default": True, "name": name}}, "AutoLoad": autoload}
        return d

    unit.dict = dict_with_dtc
