"""Eras, sides, and the enemy/friendly forces that belong to each.

Every player aircraft has an era and a side. The mission's era is the most
common one among the player slots (ties go to the newer era), and the enemy is
the opposite side, so a flight of F-86s meets MiG-15s and a flight of MiG-29s
meets F-15s.

For WWII, "west" means the Allies and "east" means the Axis.
"""
from collections import Counter

from dcs import planes, ships, vehicles

AD = vehicles.AirDefence
ARMOR = vehicles.Armor
UNARMED = vehicles.Unarmed

ERAS = ["ww2", "korea", "vietnam", "coldwar", "modern"]
ERA_LABELS = {
    "ww2": "World War II",
    "korea": "Korea (1950s)",
    "vietnam": "Vietnam era (1960s-70s)",
    "coldwar": "Late Cold War (1975-91)",
    "modern": "Modern (1991+)",
}
SIDE_LABELS = {
    "ww2": {"west": "Allies", "east": "Axis"},
    "default": {"west": "NATO / Western", "east": "Soviet / Eastern"},
}


def side_label(era, side):
    return SIDE_LABELS.get(era, SIDE_LABELS["default"])[side]


# (era, side) for each player-flyable type. Trainers/aerobatic types not listed
# here don't vote on the era.
AIRCRAFT_ERA = {
    # WWII
    **dict.fromkeys([
        "P-51D", "P-51D-30-NA", "TF-51D", "P-47D-30", "P-47D-30bl1", "P-47D-40", "SpitfireLFMkIX",
        "SpitfireLFMkIXCW", "MosquitoFBMkVI", "F4U-1D", "I-16", "La-7"
    ], ("ww2", "west")),
    **dict.fromkeys(["FW-190D9", "FW-190A8", "Bf-109K-4"], ("ww2", "east")),
    # Korea
    "F-86F Sabre": ("korea", "west"), "F-86F_FC": ("korea", "west"),
    "MiG-15bis": ("korea", "east"), "MiG-15bis_FC": ("korea", "east"),
    # Vietnam era
    **dict.fromkeys([
        "F-4E-45MC", "F-5E-3", "F-5E-3_FC", "F-100D", "UH-1H", "MB-339A", "MB-339APAN", "C-101EB", "C-101CC"
    ], ("vietnam", "west")),
    **dict.fromkeys(["MiG-21Bis", "MiG-19P", "Mi-8MT", "L-39C", "L-39ZA"], ("vietnam", "east")),
    # Late Cold War
    **dict.fromkeys([
        "F-14A-95-GR", "F-14A-135-GR", "F-14A-135-GR-Early", "F-14B", "AJS37", "Mirage-F1CE", "Mirage-F1EE",
        "Mirage-F1BE", "F-15C", "A-10A", "M-2000C", "AV8BNA", "Hawk", "SA342M", "SA342L", "SA342Mistral",
        "SA342Minigun"
    ], ("coldwar", "west")),
    **dict.fromkeys([
        "Su-27", "Su-33", "Su-25", "MiG-29A", "MiG-29G", "MiG-29S", "MiG-29 Fulcrum", "Mi-24P"
    ], ("coldwar", "east")),
    # Modern
    **dict.fromkeys([
        "F-16C_50", "FA-18C_hornet", "F-15ESE", "A-10C", "A-10C_2", "AH-64D_BLK_II", "OH58D", "CH-47Fbl1",
        "C-130J-30", "F-14BU"
    ], ("modern", "west")),
    **dict.fromkeys(["JF-17", "J-11A", "Su-25T", "Ka-50", "Ka-50_3"], ("modern", "east")),
}


def _mod_eras():
    from .mods import MODS
    for mod in MODS.values():
        for type_id, (_name, _cls, era_side) in mod.get("aircraft", {}).items():
            AIRCRAFT_ERA[type_id] = era_side


_mod_eras()


def detect(flights):
    """flights: iterable of (aircraft_id, slots). Returns (era, player_side)."""
    eras, sides = Counter(), Counter()
    for ac, slots in flights:
        if ac in AIRCRAFT_ERA:
            era, side = AIRCRAFT_ERA[ac]
            eras[era] += slots
            sides[side] += slots
    if not eras:
        return "modern", "west"
    top = max(eras.values())
    era = max((e for e, n in eras.items() if n == top), key=ERAS.index)
    side = "west" if sides["west"] >= sides["east"] else "east"
    return era, side


def ring(utype, count, radius, start=0):
    return [(utype, start + i * 360 / count, radius) for i in range(count)]


# --- SAM / AAA site layouts: (label, [(type, bearing, distance_m)]) ---------
SA2 = ("SA-2 Guideline", [(AD.SNR_75V, 0, 0), (AD.P_19_s_125_sr, 180, 250)]
       + ring(AD.S_75M_Volhov, 6, 200))
SA3 = ("SA-3 Goa", [(AD.Snr_s_125_tr, 0, 0), (AD.P_19_s_125_sr, 180, 200)]
       + ring(AD.X_5p73_s_125_ln, 4, 150, 45))
SA6 = ("SA-6 Gainful", [(AD.Kub_1S91_str, 0, 0)] + ring(AD.Kub_2P25_ln, 4, 220))
SA11 = ("SA-11 Gadfly", [(AD.SA_11_Buk_SR_9S18M1, 0, 0), (AD.SA_11_Buk_CC_9S470M1, 180, 150)]
        + ring(AD.SA_11_Buk_LN_9A310M1, 4, 250, 45))
SA10 = ("SA-10 Grumble", [(AD.S_300PS_40B6M_tr, 0, 0), (AD.S_300PS_64H6E_sr, 180, 300),
                          (AD.S_300PS_40B6MD_sr, 90, 300), (AD.S_300PS_54K6_cp, 270, 250)]
        + ring(AD.S_300PS_5P85C_ln, 6, 450, 30))
HAWK = ("MIM-23 Hawk", [(AD.Hawk_sr, 0, 0), (AD.Hawk_tr, 90, 120), (AD.Hawk_pcp, 180, 100),
                        (AD.Hawk_cwar, 270, 150)] + ring(AD.Hawk_ln, 3, 250, 30))
PATRIOT = ("MIM-104 Patriot", [(AD.Patriot_str, 0, 0), (AD.Patriot_cp, 180, 120),
                               (AD.Patriot_ECS, 200, 140), (AD.Patriot_EPP, 160, 140),
                               (AD.Patriot_AMG, 270, 120)] + ring(AD.Patriot_ln, 4, 300, 45))
NASAMS = ("NASAMS", [(AD.NASAMS_Radar_MPQ64F1, 0, 0), (AD.NASAMS_Command_Post, 180, 120)]
          + ring(AD.NASAMS_LN_C, 3, 250, 30))
FLAK88 = ("88mm Flak battery", [(AD.FuMG_401, 0, 0), (AD.KDO_Mod40, 180, 60),
                                (AD.Maschinensatz_33, 200, 90), (AD.Flakscheinwerfer_37, 90, 150)]
          + ring(AD.Flak36, 4, 120, 45))
FLAK88_HEAVY = ("Heavy Flak battery", FLAK88[1] + ring(AD.Flak41, 2, 180) + ring(AD.Flak38, 3, 250))
ALLIED_AA = ("3.7-inch AA battery", [(AD.Allies_Director, 0, 0)] + ring(AD.QF_37_AA, 4, 120, 45))
ALLIED_AA_HEAVY = ("Heavy AA battery", ALLIED_AA[1] + ring(AD.Bofors40, 3, 220) + ring(AD.M45_Quadmount, 2, 260))
RADAR_AAA = ("Radar-directed AAA", [(AD.SON_9, 0, 0)] + ring(AD.KS_19, 4, 120, 45))
RADAR_AAA_HEAVY = ("Radar-directed AAA", RADAR_AAA[1] + ring(AD.S_60_Type59_Artillery, 4, 250))


# Forces keyed by (era, side) of the *enemy*.
FORCES = {
    ("ww2", "east"): {
        "fighters": {"easy": planes.Bf_109K_4, "medium": planes.FW_190A8,
                     "hard": planes.FW_190D9, "extreme": planes.FW_190D9},
        "tanks": {"easy": ARMOR.Pz_IV_H, "medium": ARMOR.Pz_V_Panther_G,
                  "hard": ARMOR.Tiger_I, "extreme": ARMOR.Tiger_II_H},
        "ifv": ARMOR.Sd_Kfz_251, "truck": UNARMED.Blitz_36_6700A,
        "shorad": {"easy": ring(AD.Flak38, 2, 300), "medium": ring(AD.Flak38, 3, 300),
                   "hard": ring(AD.Flak38, 3, 300) + [(AD.Flak36, 90, 450)],
                   "extreme": ring(AD.Flak38, 4, 300) + ring(AD.Flak41, 2, 500)},
        "sam": {"easy": FLAK88, "medium": FLAK88, "hard": FLAK88_HEAVY, "extreme": FLAK88_HEAVY},
        "ewr": AD.FuMG_401,
        "ships": {"easy": [ships.Schnellboot_type_S130] * 2,
                  "medium": [ships.Schnellboot_type_S130] * 3,
                  "hard": [ships.Uboat_VIIC, ships.Schnellboot_type_S130, ships.Schnellboot_type_S130],
                  "extreme": [ships.Uboat_VIIC, ships.Uboat_VIIC] + [ships.Schnellboot_type_S130] * 3},
    },
    ("ww2", "west"): {
        "fighters": {"easy": planes.P_47D_30, "medium": planes.P_51D,
                     "hard": planes.SpitfireLFMkIX, "extreme": planes.P_51D_30_NA},
        "tanks": {"easy": ARMOR.M4_Sherman, "medium": ARMOR.Cromwell_IV,
                  "hard": ARMOR.M4A4_Sherman_FF, "extreme": ARMOR.Churchill_VII},
        "ifv": ARMOR.M2A1_halftrack, "truck": UNARMED.CCKW_353,
        "shorad": {"easy": ring(AD.M45_Quadmount, 2, 300), "medium": ring(AD.Bofors40, 2, 300),
                   "hard": ring(AD.Bofors40, 2, 300) + ring(AD.M45_Quadmount, 2, 450),
                   "extreme": ring(AD.Bofors40, 3, 300) + ring(AD.QF_37_AA, 2, 500)},
        "sam": {"easy": ALLIED_AA, "medium": ALLIED_AA, "hard": ALLIED_AA_HEAVY,
                "extreme": ALLIED_AA_HEAVY},
        "ewr": None,
        "ships": {"easy": [ships.LST_Mk2] * 2, "medium": [ships.LST_Mk2, ships.USS_Samuel_Chase],
                  "hard": [ships.USS_Samuel_Chase, ships.LST_Mk2, ships.LST_Mk2],
                  "extreme": [ships.USS_Samuel_Chase] * 2 + [ships.LST_Mk2] * 2},
    },
    ("korea", "east"): {
        "fighters": dict.fromkeys(("easy", "medium", "hard", "extreme"), planes.MiG_15bis),
        "tanks": dict.fromkeys(("easy", "medium", "hard", "extreme"), ARMOR.T_34_85),
        "ifv": ARMOR.T_34_85, "truck": UNARMED.Ural_375,
        "shorad": {"easy": ring(AD.ZU_23_Emplacement, 2, 300),
                   "medium": ring(AD.S_60_Type59_Artillery, 2, 300),
                   "hard": ring(AD.S_60_Type59_Artillery, 3, 300),
                   "extreme": ring(AD.S_60_Type59_Artillery, 3, 300) + ring(AD.KS_19, 2, 500)},
        "sam": {"easy": RADAR_AAA, "medium": RADAR_AAA, "hard": RADAR_AAA_HEAVY,
                "extreme": RADAR_AAA_HEAVY},
        "ewr": AD.P_19_s_125_sr,
        "ships": {d: [ships.Dry_cargo_ship_1, ships.Dry_cargo_ship_2] for d in
                  ("easy", "medium", "hard", "extreme")},
    },
    ("korea", "west"): {
        "fighters": dict.fromkeys(("easy", "medium", "hard", "extreme"), planes.F_86F_Sabre),
        "tanks": dict.fromkeys(("easy", "medium", "hard", "extreme"), ARMOR.M4_Sherman),
        "ifv": ARMOR.M2A1_halftrack, "truck": UNARMED.CCKW_353,
        "shorad": {"easy": ring(AD.M45_Quadmount, 2, 300), "medium": ring(AD.Bofors40, 2, 300),
                   "hard": ring(AD.Bofors40, 2, 300) + ring(AD.M45_Quadmount, 2, 450),
                   "extreme": ring(AD.Bofors40, 3, 300) + ring(AD.QF_37_AA, 2, 500)},
        "sam": {"easy": ALLIED_AA, "medium": ALLIED_AA, "hard": ALLIED_AA_HEAVY,
                "extreme": ALLIED_AA_HEAVY},
        "ewr": None,
        "ships": {d: [ships.LST_Mk2, ships.USS_Samuel_Chase] for d in
                  ("easy", "medium", "hard", "extreme")},
    },
    ("vietnam", "east"): {
        "fighters": {"easy": planes.MiG_19P, "medium": planes.MiG_21Bis,
                     "hard": planes.MiG_21Bis, "extreme": planes.MiG_23MLD},
        "tanks": {"easy": ARMOR.PT_76, "medium": ARMOR.T_55, "hard": ARMOR.T_55,
                  "extreme": ARMOR.T62M},
        "ifv": ARMOR.BTR_60, "truck": UNARMED.Ural_375,
        "shorad": {"easy": ring(AD.ZU_23_Emplacement, 2, 300),
                   "medium": ring(AD.ZSU_23_4_Shilka, 2, 400) + [(AD.S_60_Type59_Artillery, 90, 500)],
                   "hard": ring(AD.ZSU_23_4_Shilka, 2, 400) + [(AD.Strela_1_9P31, 90, 500)],
                   "extreme": ring(AD.ZSU_23_4_Shilka, 2, 400) + ring(AD.ZSU_57_2, 2, 600)
                   + [(AD.Strela_1_9P31, 90, 500)]},
        "sam": {"easy": SA2, "medium": SA2, "hard": SA3, "extreme": SA6},
        "ewr": AD.P_19_s_125_sr,
        "ships": {"easy": [ships.Dry_cargo_ship_1, ships.Dry_cargo_ship_2],
                  "medium": [ships.Dry_cargo_ship_1, ships.ALBATROS],
                  "hard": [ships.ALBATROS, ships.ALBATROS, ships.Dry_cargo_ship_2],
                  "extreme": [ships.REZKY, ships.ALBATROS, ships.ALBATROS]},
    },
    ("vietnam", "west"): {
        "fighters": {"easy": planes.F_5E_3, "medium": planes.F_4E_45MC,
                     "hard": planes.F_4E_45MC, "extreme": planes.F_14A_135_GR},
        "tanks": dict.fromkeys(("easy", "medium", "hard", "extreme"), ARMOR.M_60),
        "ifv": ARMOR.M_113, "truck": UNARMED.M_818,
        "shorad": {"easy": ring(AD.Vulcan, 2, 300), "medium": ring(AD.Vulcan, 2, 300),
                   "hard": ring(AD.Vulcan, 2, 300) + [(AD.M48_Chaparral, 90, 500)],
                   "extreme": ring(AD.Vulcan, 3, 300) + ring(AD.M48_Chaparral, 2, 500)},
        "sam": {"easy": HAWK, "medium": HAWK, "hard": HAWK, "extreme": HAWK},
        "ewr": None,
        "ships": {"easy": [ships.Leander_gun_achilles], "medium": [ships.Leander_gun_achilles] * 2,
                  "hard": [ships.Leander_gun_achilles, ships.Leander_gun_andromeda, ships.LST_Mk2],
                  "extreme": [ships.Leander_gun_achilles, ships.Leander_gun_andromeda,
                              ships.Leander_gun_ariadne]},
    },
    ("coldwar", "east"): {
        "fighters": {"easy": planes.MiG_21Bis, "medium": planes.MiG_23MLD,
                     "hard": planes.MiG_29A, "extreme": planes.Su_27},
        "tanks": {"easy": ARMOR.T_55, "medium": ARMOR.T_72B, "hard": ARMOR.T_80B,
                  "extreme": ARMOR.T_80UD},
        "ifv": ARMOR.BMP_2, "truck": UNARMED.Ural_375,
        "shorad": {"easy": ring(AD.ZU_23_Emplacement, 2, 350),
                   "medium": ring(AD.ZSU_23_4_Shilka, 2, 400) + [(AD.Strela_1_9P31, 90, 500)],
                   "hard": ring(AD.ZSU_23_4_Shilka, 2, 400)
                   + [(AD.Strela_10M3, 90, 500), (AD.Osa_9A33_ln, 270, 700)],
                   "extreme": ring(AD.X_2S6_Tunguska, 2, 450)
                   + [(AD.Strela_10M3, 90, 500), (AD.Osa_9A33_ln, 270, 700)]},
        "sam": {"easy": SA3, "medium": SA6, "hard": SA11, "extreme": SA10},
        "ewr": AD.X_1L13_EWR,
        "ships": {"easy": [ships.Dry_cargo_ship_1, ships.Dry_cargo_ship_2, ships.MOLNIYA],
                  "medium": [ships.Dry_cargo_ship_1, ships.MOLNIYA, ships.ALBATROS],
                  "hard": [ships.REZKY, ships.ALBATROS, ships.MOLNIYA],
                  "extreme": [ships.MOSCOW, ships.REZKY, ships.ALBATROS]},
    },
    ("coldwar", "west"): {
        "fighters": {"easy": planes.F_5E_3, "medium": planes.F_4E_45MC,
                     "hard": planes.F_15C, "extreme": planes.F_14B},
        "tanks": {"easy": ARMOR.M_60, "medium": ARMOR.Leopard1A3, "hard": ARMOR.M_1_Abrams,
                  "extreme": ARMOR.M_1_Abrams},
        "ifv": ARMOR.M_2_Bradley, "truck": UNARMED.M_818,
        "shorad": {"easy": ring(AD.Vulcan, 2, 300),
                   "medium": ring(AD.Vulcan, 2, 300) + [(AD.M48_Chaparral, 90, 500)],
                   "hard": ring(AD.Gepard, 2, 400) + [(AD.Roland_ADS, 90, 600)],
                   "extreme": ring(AD.Gepard, 2, 400) + [(AD.Roland_ADS, 90, 600),
                                                         (AD.M48_Chaparral, 270, 500)]},
        "sam": {"easy": HAWK, "medium": HAWK, "hard": PATRIOT, "extreme": PATRIOT},
        "ewr": AD.FPS_117,
        "ships": {"easy": [ships.PERRY], "medium": [ships.PERRY, ships.PERRY],
                  "hard": [ships.TICONDEROG, ships.PERRY],
                  "extreme": [ships.TICONDEROG, ships.PERRY, ships.PERRY]},
    },
    ("modern", "east"): {
        "fighters": {"easy": planes.MiG_29A, "medium": planes.MiG_29S,
                     "hard": planes.Su_27, "extreme": planes.Su_30},
        "tanks": {"easy": ARMOR.T_72B, "medium": ARMOR.T_72B3, "hard": ARMOR.T_90,
                  "extreme": ARMOR.T_90},
        "ifv": ARMOR.BMP_3, "truck": UNARMED.KAMAZ_Truck,
        "shorad": {"easy": ring(AD.ZU_23_Emplacement, 2, 350),
                   "medium": ring(AD.ZSU_23_4_Shilka, 2, 400) + [(AD.Strela_1_9P31, 90, 500)],
                   "hard": ring(AD.ZSU_23_4_Shilka, 2, 400)
                   + [(AD.Strela_10M3, 90, 500), (AD.Osa_9A33_ln, 270, 700)],
                   "extreme": ring(AD.X_2S6_Tunguska, 2, 450)
                   + [(AD.Strela_10M3, 90, 500), (AD.Tor_9A331, 270, 700)]},
        "sam": {"easy": SA6, "medium": SA11, "hard": SA10, "extreme": SA10},
        "ewr": AD.X_55G6_EWR,
        "ships": {"easy": [ships.Dry_cargo_ship_1, ships.Dry_cargo_ship_2, ships.MOLNIYA],
                  "medium": [ships.Dry_cargo_ship_1, ships.MOLNIYA, ships.ALBATROS],
                  "hard": [ships.REZKY, ships.ALBATROS, ships.MOLNIYA],
                  "extreme": [ships.MOSCOW, ships.NEUSTRASH, ships.REZKY]},
    },
    ("modern", "west"): {
        "fighters": {"easy": planes.F_16A, "medium": planes.F_16C_50,
                     "hard": planes.FA_18C_hornet, "extreme": planes.F_15C},
        "tanks": {"easy": ARMOR.Leopard_2A4, "medium": ARMOR.M_1_Abrams,
                  "hard": ARMOR.Leopard_2A5, "extreme": ARMOR.M1A2C_SEP_V3},
        "ifv": ARMOR.M_2_Bradley, "truck": UNARMED.M978_HEMTT_Tanker,
        "shorad": {"easy": ring(AD.Vulcan, 2, 300),
                   "medium": ring(AD.M1097_Avenger, 2, 400) + [(AD.Vulcan, 90, 300)],
                   "hard": ring(AD.Gepard, 2, 400) + [(AD.M6_Linebacker, 90, 500),
                                                      (AD.M1097_Avenger, 270, 500)],
                   "extreme": ring(AD.Gepard, 2, 400) + [(AD.M6_Linebacker, 90, 500),
                                                         (AD.Roland_ADS, 270, 700)]},
        "sam": {"easy": HAWK, "medium": NASAMS, "hard": PATRIOT, "extreme": PATRIOT},
        "ewr": AD.FPS_117,
        "ships": {"easy": [ships.PERRY], "medium": [ships.PERRY, ships.PERRY],
                  "hard": [ships.USS_Arleigh_Burke_IIa, ships.PERRY],
                  "extreme": [ships.TICONDEROG, ships.USS_Arleigh_Burke_IIa,
                              ships.USS_Arleigh_Burke_IIa]},
    },
}

# Extra kit per (era, side): artillery for secondary objectives, hidden pop-up
# air defenses, and infantry for CSAR search parties.
ART = vehicles.Artillery
INF = vehicles.Infantry
EXTRA = {
    ("ww2", "east"): {"artillery": ART.LeFH_18_40_105, "popup": AD.Flak38, "infantry": INF.Soldier_mauser98},
    ("ww2", "west"): {"artillery": ART.M2A1_105, "popup": AD.Bofors40, "infantry": INF.Soldier_wwii_us},
    ("korea", "east"): {"artillery": ART.X_2B11_mortar, "popup": AD.ZU_23_Emplacement, "infantry": INF.Infantry_AK},
    ("korea", "west"): {"artillery": ART.M2A1_105, "popup": AD.M45_Quadmount, "infantry": INF.Soldier_wwii_us},
    ("vietnam", "east"): {"artillery": ART.Grad_URAL, "popup": AD.Strela_1_9P31, "infantry": INF.Infantry_AK},
    ("vietnam", "west"): {"artillery": ART.M_109, "popup": AD.M48_Chaparral, "infantry": INF.Soldier_M4},
    ("coldwar", "east"): {"artillery": ART.SAU_Gvozdika, "popup": AD.SA_18_Igla_manpad, "infantry": INF.Infantry_AK},
    ("coldwar", "west"): {"artillery": ART.M_109, "popup": AD.Soldier_stinger, "infantry": INF.Soldier_M4},
    ("modern", "east"): {"artillery": ART.SAU_Msta, "popup": AD.SA_18_Igla_S_manpad, "infantry": INF.Infantry_AK_ver3},
    ("modern", "west"): {"artillery": ART.MLRS, "popup": AD.Soldier_stinger, "infantry": INF.Soldier_M4},
}
for _k, _v in EXTRA.items():
    FORCES[_k].update(_v)


# What the *players'* side gets for support, by era. None = not available.
SUPPORT = {
    ("ww2", "west"): {}, ("ww2", "east"): {},
    ("korea", "west"): {}, ("korea", "east"): {},
    ("vietnam", "west"): {"awacs": planes.E_2C, "boom": planes.KC_135, "drogue": planes.KC130},
    ("vietnam", "east"): {},
    ("coldwar", "west"): {"awacs": planes.E_3A, "boom": planes.KC_135, "drogue": planes.KC135MPRS},
    ("coldwar", "east"): {"awacs": planes.A_50, "drogue": planes.IL_78M},
    ("modern", "west"): {"awacs": planes.E_3A, "boom": planes.KC_135, "drogue": planes.KC135MPRS},
    ("modern", "east"): {"awacs": planes.A_50, "drogue": planes.IL_78M},
}

CARRIER = {"ww2": ships.Essex}  # everything else: CVN-74 Stennis


def enemy_side(player_side):
    return "east" if player_side == "west" else "west"


def _name(t):
    return getattr(t, "name", None) or t.id


def summary(era, player_side, difficulty):
    """Short human description of the opposition, for the UI and briefing."""
    f = FORCES[(era, enemy_side(player_side))]
    return {
        "era": era, "era_label": ERA_LABELS[era],
        "player_side": side_label(era, player_side),
        "enemy_side": side_label(era, enemy_side(player_side)),
        "fighters": _name(f["fighters"][difficulty]),
        "tanks": _name(f["tanks"][difficulty]),
        "ships": sorted({_name(s) for s in f["ships"][difficulty]}),
        "sam": f["sam"][difficulty][0],
        "support": sorted(k for k in SUPPORT[(era, player_side)]),
    }
