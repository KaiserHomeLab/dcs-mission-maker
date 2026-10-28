"""Player-flyable aircraft catalog."""
from dcs import helicopters, planes

# Friendlier names for the DCS type ids that aren't self-explanatory.
DISPLAY_NAMES = {
    "FA-18C_hornet": "F/A-18C Hornet",
    "F-16C_50": "F-16C Viper",
    "F-15ESE": "F-15E Strike Eagle",
    "F-15C": "F-15C Eagle (FC)",
    "F-14B": "F-14B Tomcat",
    "F-14A-135-GR": "F-14A Tomcat",
    "F-14A-135-GR-Early": "F-14A Tomcat (early)",
    "F-14A-95-GR": "F-14A Tomcat (-95)",
    "F-14BU": "F-14B(U) Tomcat",
    "F-4E-45MC": "F-4E Phantom II",
    "F-5E-3": "F-5E Tiger II",
    "F-5E-3_FC": "F-5E Tiger II (FC)",
    "F-86F Sabre": "F-86F Sabre",
    "F-86F_FC": "F-86F Sabre (FC)",
    "F-100D": "F-100D Super Sabre",
    "A-10A": "A-10A Warthog (FC)",
    "A-10C": "A-10C Warthog",
    "A-10C_2": "A-10C II Tank Killer",
    "AV8BNA": "AV-8B Harrier N/A",
    "AJS37": "AJS-37 Viggen",
    "M-2000C": "Mirage 2000C",
    "Mirage-F1CE": "Mirage F1CE",
    "Mirage-F1EE": "Mirage F1EE",
    "Mirage-F1BE": "Mirage F1BE",
    "JF-17": "JF-17 Thunder",
    "J-11A": "J-11A (FC)",
    "MiG-29 Fulcrum": "MiG-29A Fulcrum (full fidelity)",
    "MiG-29A": "MiG-29A (FC)",
    "MiG-29S": "MiG-29S (FC)",
    "MiG-29G": "MiG-29G (FC)",
    "Su-27": "Su-27 Flanker (FC)",
    "Su-33": "Su-33 Flanker-D (FC)",
    "Su-25": "Su-25 Frogfoot (FC)",
    "Su-25T": "Su-25T Frogfoot",
    "MiG-21Bis": "MiG-21bis Fishbed",
    "MiG-19P": "MiG-19P Farmer",
    "MiG-15bis": "MiG-15bis",
    "MiG-15bis_FC": "MiG-15bis (FC)",
    "C-101EB": "C-101EB Aviojet",
    "C-101CC": "C-101CC Aviojet",
    "C-130J-30": "C-130J Hercules",
    "L-39C": "L-39C Albatros",
    "L-39ZA": "L-39ZA Albatros",
    "MB-339A": "MB-339A",
    "MB-339APAN": "MB-339A PAN",
    "Christen Eagle II": "Christen Eagle II",
    "Yak-52": "Yak-52",
    "Hawk": "Hawk T.1A",
    "P-51D": "P-51D Mustang",
    "P-51D-30-NA": "P-51D-30-NA Mustang",
    "TF-51D": "TF-51D Mustang",
    "P-47D-30": "P-47D-30 Thunderbolt",
    "P-47D-30bl1": "P-47D-30 Thunderbolt (early)",
    "P-47D-40": "P-47D-40 Thunderbolt",
    "SpitfireLFMkIX": "Spitfire LF Mk IX",
    "SpitfireLFMkIXCW": "Spitfire LF Mk IX (clipped)",
    "FW-190D9": "Fw 190 D-9",
    "FW-190A8": "Fw 190 A-8",
    "Bf-109K-4": "Bf 109 K-4",
    "MosquitoFBMkVI": "Mosquito FB Mk VI",
    "F4U-1D": "F4U-1D Corsair",
    "I-16": "I-16",
    "La-7": "La-7",
    "AH-64D_BLK_II": "AH-64D Apache",
    "Ka-50": "Ka-50 Black Shark",
    "Ka-50_3": "Ka-50 Black Shark III",
    "Mi-8MT": "Mi-8MTV2 Hip",
    "Mi-24P": "Mi-24P Hind",
    "UH-1H": "UH-1H Huey",
    "SA342M": "SA342M Gazelle",
    "SA342L": "SA342L Gazelle",
    "SA342Mistral": "SA342 Gazelle (Mistral)",
    "SA342Minigun": "SA342 Gazelle (Minigun)",
    "OH58D": "OH-58D Kiowa Warrior",
    "CH-47Fbl1": "CH-47F Chinook",
}

CARRIER_CAPABLE = {
    "FA-18C_hornet", "F-14B", "F-14A-135-GR", "F-14A-135-GR-Early",
    "F-14A-95-GR", "F-14BU", "AV8BNA", "Su-33", "F4U-1D",
}


def _collect():
    out = {}
    for type_map, is_heli in ((planes.plane_map, False),
                              (helicopters.helicopter_map, True)):
        for type_id, cls in type_map.items():
            if not getattr(cls, "flyable", False):
                continue
            out[type_id] = {
                "id": type_id,
                "name": DISPLAY_NAMES.get(type_id, type_id),
                "helicopter": is_heli,
                "carrier": is_heli or type_id in CARRIER_CAPABLE,
                "max_group": int(getattr(cls, "group_size_max", 4) or 4),
                "cls": cls,
            }
    return out


AIRCRAFT = _collect()


def _add_mods():
    from .mods import MODS
    for mod_id, mod in MODS.items():
        for type_id, (name, cls, _era) in mod.get("aircraft", {}).items():
            AIRCRAFT[type_id] = {"id": type_id, "name": name, "helicopter": cls.helicopter,
                                 "carrier": cls.helicopter, "max_group": cls.group_size_max,
                                 "cls": cls, "mod": mod_id}


_add_mods()


def catalog():
    """JSON-safe list for the UI, sorted planes first then helicopters."""
    from .comms import callsign_options
    from .dtc import SUPPORTED
    from .eras import AIRCRAFT_ERA
    items = []
    for a in AIRCRAFT.values():
        item = {k: v for k, v in a.items() if k != "cls"}
        item["callsigns"] = callsign_options(a["cls"])
        item["era"], item["side"] = AIRCRAFT_ERA.get(a["id"], (None, None))
        item["dtc"] = a["id"] in SUPPORTED
        items.append(item)
    return sorted(items, key=lambda a: (a["helicopter"], a["name"].lower()))
