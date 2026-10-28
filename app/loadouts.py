"""Aircraft loadouts.

pydcs normally reads default payloads from a local DCS install, which the
container doesn't have, so loadouts are defined here: hand-written ones for
popular modules, plus a generic pylon filler for everything else.
"""
import functools

ROLE_FOR_MISSION = {"cap": "aa", "cas": "cas", "sead": "sead",
                    "strike": "strike", "antiship": "antiship", "csar": "cas", "free": "aa"}
ROLE_FALLBACK = {"cas": ["strike"], "sead": ["cas", "strike"],
                 "strike": ["cas"], "antiship": ["cas", "strike"], "aa": []}


def _sym(left: dict, mirror: dict) -> dict:
    """Mirror a left-side pylon map onto its right-side pylon numbers."""
    out = dict(left)
    for lhs, rhs in mirror.items():
        if lhs in left:
            out[rhs] = left[lhs]
    return out


F16 = {1: 9, 2: 8, 3: 7, 4: 6}
F16_AAM = {1: "AIM_120C_AMRAAM___Active_Radar_AAM", 2: "AIM_9X_Sidewinder_IR_AAM"}
HORNET = {1: 9, 2: 8, 3: 7}
A10 = {2: 10, 3: 9, 4: 8, 5: 7}

CURATED = {
    "F-16C_50": {
        "aa": _sym({**F16_AAM, 3: "AIM_120C_AMRAAM___Active_Radar_AAM",
                    4: "Fuel_tank_370_gal"}, F16) | {5: "ALQ_184"},
        "cas": _sym({**F16_AAM, 3: "LAU_117___AGM_65D___Maverick_D__IIR_ASM_",
                     4: "GBU_12___500lb_Laser_Guided_Bomb"}, F16)
               | {5: "Fuel_tank_300_gal", 11: "AN_AAQ_28_LITENING___Targeting_Pod_"},
        "sead": _sym({**F16_AAM, 3: "AGM_88C_HARM___High_Speed_Anti_Radiation_Missile_",
                      4: "Fuel_tank_370_gal"}, F16)
                | {5: "ALQ_184", 10: "AN_ASQ_213_HTS___HARM_Targeting_System"},
        "strike": _sym({**F16_AAM, 3: "GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb",
                        4: "Fuel_tank_370_gal"}, F16)
                  | {5: "ALQ_184", 11: "AN_AAQ_28_LITENING___Targeting_Pod_"},
        "antiship": _sym({**F16_AAM, 3: "LAU_117___AGM_65K___Maverick_K__CCD_Imp_ASM_",
                          4: "Fuel_tank_370_gal"}, F16)
                    | {5: "ALQ_184", 11: "AN_AAQ_28_LITENING___Targeting_Pod_"},
    },
    "FA-18C_hornet": {
        "aa": _sym({1: "AIM_9X_Sidewinder_IR_AAM", 2: "LAU_115_2_LAU_127_AIM_120C",
                    3: "LAU_115_2_LAU_127_AIM_120C"}, HORNET)
              | {4: "AIM_120C_AMRAAM___Active_Radar_AAM", 5: "FPU_8A_Fuel_Tank_330_gallons",
                 6: "AIM_120C_AMRAAM___Active_Radar_AAM"},
        "cas": _sym({1: "AIM_9X_Sidewinder_IR_AAM",
                     2: "BRU_33_with_2_x_GBU_12___500lb_Laser_Guided_Bomb",
                     3: "LAU_117_AGM_65F"}, HORNET)
               | {4: "AN_ASQ_228_ATFLIR___Targeting_Pod", 5: "FPU_8A_Fuel_Tank_330_gallons",
                  6: "AIM_120C_AMRAAM___Active_Radar_AAM"},
        "sead": _sym({1: "AIM_9X_Sidewinder_IR_AAM",
                      2: "AGM_88C_HARM___High_Speed_Anti_Radiation_Missile_",
                      3: "AGM_88C_HARM___High_Speed_Anti_Radiation_Missile_"}, HORNET)
                | {4: "AIM_120C_AMRAAM___Active_Radar_AAM", 5: "FPU_8A_Fuel_Tank_330_gallons",
                   6: "AIM_120C_AMRAAM___Active_Radar_AAM"},
        "strike": _sym({1: "AIM_9X_Sidewinder_IR_AAM",
                        2: "GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb",
                        3: "AGM_154C___JSOW_Unitary_BROACH"}, HORNET)
                  | {4: "AN_ASQ_228_ATFLIR___Targeting_Pod", 5: "FPU_8A_Fuel_Tank_330_gallons",
                     6: "AIM_120C_AMRAAM___Active_Radar_AAM"},
        "antiship": _sym({1: "AIM_9X_Sidewinder_IR_AAM", 2: "LAU_115_2_LAU_127_AIM_120C",
                          3: "AGM_84D_Harpoon_AShM"}, HORNET)
                    | {4: "AIM_120C_AMRAAM___Active_Radar_AAM",
                       5: "FPU_8A_Fuel_Tank_330_gallons",
                       6: "AIM_120C_AMRAAM___Active_Radar_AAM"},
    },
    "A-10C_2": {
        "aa": {1: "LAU_105___2_x_AIM_9M_Sidewinder_IR_AAM", 11: "ALQ_131___ECM_Pod",
               10: "AN_AAQ_28_LITENING___Targeting_Pod_"},
        "cas": _sym({2: "LAU_131___7_x_Laser_Guided_Rkts__70_mm_Hydra_70_M151_HE_APKWS",
                     3: "LAU_117___AGM_65D___Maverick_D__IIR_ASM_",
                     4: "GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb",
                     5: "GBU_12___500lb_Laser_Guided_Bomb"}, A10)
               | {1: "LAU_105___2_x_AIM_9M_Sidewinder_IR_AAM", 11: "ALQ_131___ECM_Pod",
                  10: "AN_AAQ_28_LITENING___Targeting_Pod_"},
        "strike": _sym({2: "LAU_131___7_x_Laser_Guided_Rkts__70_mm_Hydra_70_M151_HE_APKWS",
                        3: "GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb",
                        4: "GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb",
                        5: "GBU_12___500lb_Laser_Guided_Bomb"}, A10)
                  | {1: "LAU_105___2_x_AIM_9M_Sidewinder_IR_AAM", 11: "ALQ_131___ECM_Pod",
                     10: "AN_AAQ_28_LITENING___Targeting_Pod_"},
        "antiship": _sym({2: "LAU_131___7_x_Laser_Guided_Rkts__70_mm_Hydra_70_M151_HE_APKWS",
                          3: "LAU_117___AGM_65K___Maverick_K__CCD_Imp_ASM_",
                          4: "GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb",
                          5: "GBU_12___500lb_Laser_Guided_Bomb"}, A10)
                    | {1: "LAU_105___2_x_AIM_9M_Sidewinder_IR_AAM", 11: "ALQ_131___ECM_Pod",
                       10: "AN_AAQ_28_LITENING___Targeting_Pod_"},
    },
    "F-15ESE": {
        "aa": {1: "AIM_120C_AMRAAM___Active_Radar_AAM", 3: "AIM_120C_AMRAAM___Active_Radar_AAM",
               5: "AIM_120C_AMRAAM___Active_Radar_AAM", 6: "AIM_120C_AMRAAM___Active_Radar_AAM",
               10: "AIM_120C_AMRAAM___Active_Radar_AAM", 11: "AIM_120C_AMRAAM___Active_Radar_AAM",
               2: "Fuel_tank_610_gal_", 8: "Fuel_tank_610_gal_"},
        "cas": {1: "AIM_120C_AMRAAM___Active_Radar_AAM", 11: "AIM_120C_AMRAAM___Active_Radar_AAM",
                2: "Fuel_tank_610_gal_", 8: "Fuel_tank_610_gal_",
                4: "GBU_12___4", 12: "GBU_12___4_", 7: "AN_AAQ_14_LANTIRN_TGT_Pod",
                9: "AN_AAQ_13_LANTIRN_NAV_POD"},
        "strike": {1: "AIM_120C_AMRAAM___Active_Radar_AAM", 11: "AIM_120C_AMRAAM___Active_Radar_AAM",
                   2: "GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb",
                   8: "GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb",
                   4: "GBU_38___3", 12: "GBU_38___3_", 7: "AN_AAQ_14_LANTIRN_TGT_Pod",
                   9: "AN_AAQ_13_LANTIRN_NAV_POD"},
    },
    "AH-64D_BLK_II": {
        "cas": {1: "M261___19_x_UnGd_Rkts__70_mm_Hydra_70_M151_HE__M433_RC_Fuze",
                2: "M299___4_x_AGM_114K_Hellfire", 3: "M299___4_x_AGM_114K_Hellfire",
                4: "M261___19_x_UnGd_Rkts__70_mm_Hydra_70_M151_HE__M433_RC_Fuze"},
        "antiship": {1: "M299___4_x_AGM_114K_Hellfire", 2: "M299___4_x_AGM_114K_Hellfire",
                     3: "M299___4_x_AGM_114K_Hellfire", 4: "M299___4_x_AGM_114K_Hellfire"},
    },
    "Ka-50_3": {
        "cas": {1: "APU_6___6_x_9M127_Vikhr___ATGM__LOSBR__Tandem_HEAT_Frag",
                2: "B_8V20A___20_x_UnGd_Rkts__80_mm_S_8KOM_HEAT_Frag",
                3: "B_8V20A___20_x_UnGd_Rkts__80_mm_S_8KOM_HEAT_Frag",
                4: "APU_6___6_x_9M127_Vikhr___ATGM__LOSBR__Tandem_HEAT_Frag"},
    },
    "AV8BNA": {
        "aa": {1: "AIM_9M_Sidewinder_IR_AAM", 8: "AIM_9M_Sidewinder_IR_AAM",
               2: "LAU_7___AIM_9M_Sidewinder_IR_AAM", 7: "LAU_7___AIM_9M_Sidewinder_IR_AAM",
               3: "AERO_1D_300_Gallons_Fuel_Tank__", 6: "AERO_1D_300_Gallons_Fuel_Tank__"},
        "cas": {1: "AIM_9M_Sidewinder_IR_AAM", 8: "AIM_9M_Sidewinder_IR_AAM",
                2: "LAU_117___AGM_65E___Maverick_E__Laser_ASM___Lg_Whd_",
                7: "LAU_117___AGM_65E___Maverick_E__Laser_ASM___Lg_Whd_",
                3: "GBU_12___500lb_Laser_Guided_Bomb", 6: "GBU_12___500lb_Laser_Guided_Bomb",
                5: "AN_AAQ_28_LITENING___Targeting_Pod_"},
        "strike": {1: "AIM_9M_Sidewinder_IR_AAM", 8: "AIM_9M_Sidewinder_IR_AAM",
                   2: "GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb",
                   3: "GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb",
                   6: "GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb",
                   7: "GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb",
                   5: "AN_AAQ_28_LITENING___Targeting_Pod_"},
    },
    "F-14B": {
        "aa": {1: "LAU_138_AIM_9M", 10: "LAU_138_AIM_9M", 2: "LAU_7_AIM_9M", 9: "LAU_7_AIM_9M",
               3: "Fuel_tank_300_gal_", 8: "Fuel_tank_300_gal_",
               4: "AIM_54C_Mk47", 7: "AIM_54C_Mk47", 5: "AIM_7M_", 6: "AIM_7M_"},
        "cas": {1: "LAU_138_AIM_9M", 10: "LAU_138_AIM_9M", 2: "AIM_7M",
                9: "LANTIRN_Targeting_Pod", 3: "Fuel_tank_300_gal_", 8: "Fuel_tank_300_gal_",
                4: "GBU_12", 5: "GBU_12", 6: "GBU_12", 7: "GBU_12"},
    },
    "M-2000C": {
        "aa": {1: "Matra_Magic_II", 9: "Matra_Magic_II", 2: "Matra_Super_530D",
               8: "Matra_Super_530D", 5: "RPL_522_1300_liters_Fuel_Tank"},
        "cas": {1: "Matra_Magic_II", 9: "Matra_Magic_II", 2: "RPL_541_2000_liters_Fuel_Tank_",
                8: "RPL_541_2000_liters_Fuel_Tank__", 3: "Mk_82_Snakeye___500lb_GP_Bomb_HD",
                4: "Mk_82_Snakeye___500lb_GP_Bomb_HD", 6: "Mk_82_Snakeye___500lb_GP_Bomb_HD",
                7: "Mk_82_Snakeye___500lb_GP_Bomb_HD", 5: "RPL_522_1300_liters_Fuel_Tank"},
    },
    "JF-17": {
        "aa": {1: "DIS_PL_5EII", 7: "DIS_PL_5EII", 2: "DIS_SD_10_DUAL_L", 6: "DIS_SD_10_DUAL_R"},
        "cas": {1: "DIS_PL_5EII", 7: "DIS_PL_5EII", 2: "DIS_GBU_12_DUAL_GDJ_II19_L",
                6: "DIS_GBU_12_DUAL_GDJ_II19_R", 3: "DIS_LS_6_500", 5: "DIS_LS_6_500",
                4: "DIS_WMD7"},
        "sead": {1: "DIS_PL_5EII", 7: "DIS_PL_5EII", 2: "DIS_LD_10_DUAL_L",
                 6: "DIS_LD_10_DUAL_R", 4: "DIS_WMD7"},
        "antiship": {1: "DIS_PL_5EII", 7: "DIS_PL_5EII", 2: "DIS_SD_10",
                     6: "DIS_SD_10", 3: "DIS_C_802AK", 5: "DIS_C_802AK"},
    },
    # Enemy AI fighters.
    "Su-27": {"aa": {1: "R_73__AA_11_Archer____Infra_Red", 2: "R_73__AA_11_Archer____Infra_Red",
                     4: "R_27ER__AA_10_Alamo_C____Semi_Act_Extended_Range",
                     5: "R_27R__AA_10_Alamo_A____Semi_Act_Rdr",
                     6: "R_27R__AA_10_Alamo_A____Semi_Act_Rdr",
                     7: "R_27ER__AA_10_Alamo_C____Semi_Act_Extended_Range",
                     9: "R_73__AA_11_Archer____Infra_Red", 10: "R_73__AA_11_Archer____Infra_Red"}},
    "Su-30": {"aa": {1: "R_73__AA_11_Archer____Infra_Red", 10: "R_73__AA_11_Archer____Infra_Red",
                     2: "R_77__AA_12_Adder____Active_Rdr", 9: "R_77__AA_12_Adder____Active_Rdr",
                     4: "R_27ER__AA_10_Alamo_C____Semi_Act_Extended_Range",
                     7: "R_27ER__AA_10_Alamo_C____Semi_Act_Extended_Range",
                     5: "R_77__AA_12_Adder____Active_Rdr", 6: "R_77__AA_12_Adder____Active_Rdr"}},
    "MiG-29S": {"aa": {1: "R_73__AA_11_Archer____Infra_Red", 7: "R_73__AA_11_Archer____Infra_Red",
                       2: "R_77__AA_12_Adder____Active_Rdr", 6: "R_77__AA_12_Adder____Active_Rdr",
                       3: "R_27R__AA_10_Alamo_A____Semi_Act_Rdr",
                       5: "R_27R__AA_10_Alamo_A____Semi_Act_Rdr", 4: "Fuel_tank_1400L"}},
    "MiG-21Bis": {"aa": {1: "APU_60_2M_with_2_x_R_60M__AA_8_Aphid_B____IR_AAM",
                         5: "APU_60_2M_with_2_x_R_60M__AA_8_Aphid_B____IR_AAM_",
                         2: "APU_13U_2_with_R_3R__AA_2_Atoll_C____Semi_Active_AAM",
                         4: "APU_13U_2_with_R_3R__AA_2_Atoll_C____Semi_Active_AAM",
                         3: "Fuel_Tank_800_L__21_"}},
}

# Variants that share a curated loadout (unresolvable pylons are dropped).
for _alias, _base in {"F-14A-135-GR": "F-14B", "F-14A-135-GR-Early": "F-14B",
                      "F-14A-95-GR": "F-14B", "F-14BU": "F-14B", "A-10C": "A-10C_2",
                      "Ka-50": "Ka-50_3"}.items():
    CURATED.setdefault(_alias, CURATED[_base])

# Generic filler preferences, best first (substring match on pylon option names).
BVR = ["AIM_120C", "AIM_120B", "R_77", "SD_10", "AIM_54C", "R_27ER", "Super_530D",
       "AIM_7M", "R_27R", "Super_530F", "AIM_7F", "AIM_7E", "R_3R"]
WVR = ["AIM_9X", "AIM_9M", "R_73", "Magic_II", "PL_5", "AIM_9L", "R_60M", "R_550",
       "AIM_9P5", "AIM_9P", "R_13M", "R_3S", "AIM_9B"]
UNGUIDED = ["Mk_82___500lb_GP_Bomb_LD", "Mk_82_Snakeye", "FAB_250M_62", "FAB_250",
            "LAU_68___7_x_UnGd_Rkts__70_mm_Hydra_70_M151_HE", "B_8M1___20_x_UnGd_Rkts__80_mm_S_8KOM",
            "B_8V20A___20_x_UnGd_Rkts__80_mm_S_8KOM", "UB_32", "UB_16", "HVAR", "AN_M64",
            "SC_250", "SC_500", "500_lb", "250_lb", "Mk_81", "BR_250", "BR_500", "FAB_100",
            # helicopter rockets and door guns
            "M261_MK151", "XM158_M151", "B_8V20A_OFP2", "M134", "M60_SIDE", "KORD", "PKT"]
# Weapons that guide themselves (no targeting pod needed), by role.
GROUND_PREFS = {
    "cas": ["AGM_114K", "AGM_65D", "AGM_65K", "AGM_65E", "RB_75", "Kh_25ML", "Kh_29T", "Vikhr",
            "9M114", "HOT3", "HOT", "LAU_131", "M260___7_x_Laser", "CBU_97", "CBU_87", "RBK_500", "Mk_20",
            "BL_755", "ARAK", "BK_90"] + UNGUIDED,
    "sead": ["AGM_88C", "AGM_88", "Kh_58", "Kh_25MPU", "Kh_25MP", "LD_10", "AGM_45",
             "AGM_122", "ALARM", "AGM_65D", "RB_75", "Kh_25ML"] + UNGUIDED,
    "strike": ["GBU_31_V_1_B", "GBU_38", "AGM_154C", "AGM_154A", "KAB_500S", "Mk_84", "FAB_500",
               "Mk_83", "BetAB_500", "SC_500", "1000_lb", "Mk_82", "FAB_250"] + UNGUIDED,
    "antiship": ["AGM_84D", "AGM_84", "Kh_31A", "Kh_35", "C_802", "RB_15", "RB_04", "Kormoran",
                 "AM39", "Kh_59", "AGM_65K", "AGM_65F", "AGM_65D", "Kh_29T", "AGM_114"] + UNGUIDED,
}
ROLE_LABELS = {"aa": "Air-to-air", "cas": "CAS", "sead": "SEAD", "strike": "Strike",
               "antiship": "Anti-ship"}


def _pylon_options(cls, n):
    P = getattr(cls, f"Pylon{n}", None)
    if P is None:
        return {}
    return {a: getattr(P, a) for a in dir(P) if not a.startswith("_")}


def _resolve(cls, n, name):
    opts = _pylon_options(cls, n)
    if name in opts:
        return opts[name]
    key = name.strip("_").lower()
    for a, w in opts.items():
        if a.strip("_").lower() == key:
            return w
    for a, w in opts.items():
        if key in a.lower():
            return w
    return None


# Never picked by the automatic filler.
EXCLUDE = ("smoke", "practice", "inert", "bdu", "illum", "sab_", "_tp", "empty", "dummy",
           "captive", "training", "for_a_i")


def _first_match(opts, prefs):
    usable = sorted(a for a in opts if not any(x in a.lower() for x in EXCLUDE))
    for p in prefs:
        for a in usable:
            if p.lower() in a.lower():
                return opts[a]
    return None


@functools.cache
def _generic(cls, role):
    """Automatic {pylon: weapon} for a role. Cached per type: callers must not mutate it."""
    pylons = sorted(int(a[5:]) for a in dir(cls) if a.startswith("Pylon") and a[5:].isdigit())
    out = {}
    opts = {n: _pylon_options(cls, n) for n in pylons}
    aam_pylons = [] if cls.helicopter else [n for n in pylons if _first_match(opts[n], BVR + WVR)]
    outer = {aam_pylons[0], aam_pylons[-1]} if aam_pylons else set()
    for n in pylons:
        if role == "aa" or n in outer:
            w = _first_match(opts[n], WVR if n in outer else BVR) or _first_match(opts[n], BVR + WVR)
        else:
            w = _first_match(opts[n], GROUND_PREFS[role])
        if w:
            out[n] = w
    return out


@functools.cache
def _curated_spec(cls, role):
    curated = CURATED.get(cls.id, {}).get(role)
    if not curated:
        return None
    spec = {n: _resolve(cls, n, w) for n, w in curated.items()}
    return {n: w for n, w in spec.items() if w}


def summarize(spec):
    """'2x AIM-120C ..., 4x GBU-12 ...' from a {pylon: weapon} spec."""
    counts = {}
    for _, (_, w) in sorted(spec.items()):
        name = w["name"]
        counts[name] = counts.get(name, 0) + 1
    return [f"{n}x {name}" for name, n in counts.items()]


def presets(cls, mission_type):
    """Loadout choices for one aircraft, recommended first.

    Each is {"id", "label", "weapons", "recommended"}; the id is what the
    mission request passes back in FlightRequest.loadout.
    """
    return [dict(p) for p in _presets(cls, mission_type)]


@functools.cache
def _presets(cls, mission_type):
    role = ROLE_FOR_MISSION[mission_type]
    order = [role] + ROLE_FALLBACK.get(role, []) + [r for r in ROLE_LABELS if r != role]
    out, seen = [], set()
    for r in order:
        for kind in ("curated", "auto"):
            spec = _curated_spec(cls, r) if kind == "curated" else _generic(cls, r)
            if not spec:
                continue
            key = tuple(sorted((n, w[1]["clsid"]) for n, w in spec.items()))
            if key in seen:
                continue
            seen.add(key)
            label = ROLE_LABELS[r] + (" (auto)" if kind == "auto" else "")
            out.append({"id": f"{kind}:{r}", "label": label, "weapons": summarize(spec),
                        "role": r})
    empty = {"id": "empty", "label": "Clean (guns only)", "weapons": [], "role": None}
    # An air-to-air mission with no missiles to carry flies clean, not with bombs.
    if role == "aa" and not (out and out[0]["role"] == "aa"):
        out.insert(0, empty)
    else:
        out.append(empty)
    out[0]["recommended"] = True
    return out


def spec_for(cls, mission_type, preset_id=None):
    if preset_id == "empty":
        return {}, "empty"
    if preset_id and ":" in preset_id:
        kind, role = preset_id.split(":", 1)
        if role in ROLE_LABELS:
            spec = _curated_spec(cls, role) if kind == "curated" else _generic(cls, role)
            if spec:
                return spec, preset_id
    best = _presets(cls, mission_type)[0]
    return spec_for(cls, mission_type, best["id"])


def apply_loadout(group, mission_type, preset_id=None):
    """Loads every unit in `group`. Returns (label, weapons summary)."""
    cls = group.units[0].unit_type
    spec, chosen = spec_for(cls, mission_type, preset_id)
    for u in group.units:
        for n, w in spec.items():
            u.load_pylon(w, n)
    if not spec:
        return "clean, guns only", []
    kind, role = chosen.split(":")
    return ROLE_LABELS[role] + (" (auto)" if kind == "auto" else ""), summarize(spec)


def apply_role(group, role):
    """For AI groups: curated spec for the role if there is one, else auto."""
    cls = group.units[0].unit_type
    spec = _curated_spec(cls, role) or _generic(cls, role)
    for u in group.units:
        for n, w in spec.items():
            u.load_pylon(w, n)
