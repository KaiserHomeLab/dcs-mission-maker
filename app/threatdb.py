"""Threat recognition data for the Briefing Room's blueprint cards.

Figures are approximate public numbers, rounded for briefing use, and roughly
what DCS models; they are not authoritative. `art` picks the blueprint
silhouette class drawn by the page. `rwr` is only given where the symbol is
well established.
"""
import json
import os

from . import eras, mods, paths

# ---------------------------------------------------------------- fighters
_F = "fighter"
FIGHTERS = {
    "Bf-109K-4": dict(title="Bf 109 K-4", role="Axis fighter", art="prop", speed="710 km/h",
                      arms="1x 30 mm MK 108, 2x 13 mm MG 131",
                      notes="Climbs and accelerates very well. Fight it in the horizontal, not vertical."),
    "FW-190A8": dict(title="Fw 190 A-8", role="Axis fighter / attack", art="prop", speed="650 km/h",
                     arms="4x 20 mm MG 151, 2x 13 mm MG 131",
                     notes="Excellent roll rate and heavy guns. Avoid head-on passes."),
    "FW-190D9": dict(title="Fw 190 D-9 \"Dora\"", role="Axis fighter", art="prop", speed="685 km/h",
                     arms="2x 20 mm MG 151, 2x 13 mm MG 131",
                     notes="Fast energy fighter. Keep your speed up and don't get dragged into a dive race."),
    "P-47D-30": dict(title="P-47D Thunderbolt", role="Allied fighter-bomber", art="prop",
                     speed="690 km/h", arms="8x .50 cal M2",
                     notes="Dives faster than anything; heavy. Out-climb it at low altitude."),
    "P-51D": dict(title="P-51D Mustang", role="Allied fighter", art="prop", speed="700 km/h",
                  arms="6x .50 cal M2", notes="Fast, long-legged and good at altitude."),
    "P-51D-30-NA": dict(title="P-51D Mustang", role="Allied fighter", art="prop", speed="700 km/h",
                        arms="6x .50 cal M2", notes="Fast, long-legged and good at altitude."),
    "SpitfireLFMkIX": dict(title="Spitfire LF Mk IX", role="Allied fighter", art="prop",
                           speed="650 km/h", arms="2x 20 mm Hispano, 4x .303",
                           notes="Out-turns almost everything. Never turn with it; use speed and vertical."),
    "MiG-15bis": dict(title="MiG-15bis \"Fagot\"", role="Jet fighter", art="early_jet",
                      speed="Mach 0.9", arms="1x 37 mm N-37, 2x 23 mm NR-23",
                      notes="Climbs well; its 37 mm hits hard but fires slowly. Poor handling near Mach."),
    "F-86F Sabre": dict(title="F-86F Sabre", role="Jet fighter", art="early_jet", speed="Mach 0.9",
                        arms="6x .50 cal M3", notes="Good high-speed handling and gunsight."),
    "MiG-19P": dict(title="MiG-19P \"Farmer\"", role="Interceptor", art="jet", speed="Mach 1.35",
                    arms="2x 30 mm NR-30, IR missiles",
                    notes="Fast and powerful but short-legged; short-range IR missiles only."),
    "MiG-21Bis": dict(title="MiG-21bis \"Fishbed-L\"", role="Fighter", art="delta", speed="Mach 2.0",
                      arms="23 mm GSh-23, R-60 / R-3 missiles", range="~8 km (IR)",
                      notes="Small and fast; bleeds energy in sustained turns. Mostly a short-range threat."),
    "MiG-23MLD": dict(title="MiG-23MLD \"Flogger-K\"", role="Fighter", art="jet", speed="Mach 2.3",
                      arms="R-24R/T radar and IR missiles, R-60, 23 mm", range="~35 km (R-24R)",
                      notes="Fast with a real BVR shot. Poor in a turning fight."),
    "F-5E-3": dict(title="F-5E Tiger II", role="Light fighter", art="jet", speed="Mach 1.6",
                   arms="2x 20 mm M39, AIM-9", range="~8 km (IR)",
                   notes="Tiny and hard to spot; no BVR missiles. Stay out of its gun and AIM-9 range."),
    "F-4E-45MC": dict(title="F-4E Phantom II", role="Fighter-bomber", art="jet", speed="Mach 2.2",
                      arms="AIM-7 Sparrow, AIM-9, 20 mm M61", range="~25 km (AIM-7)",
                      notes="Semi-active Sparrows: it must keep pointing at you. Doesn't turn well."),
    "F-14A-135-GR": dict(title="F-14A Tomcat", role="Fleet interceptor", art="swing", speed="Mach 2.3",
                         arms="AIM-54 Phoenix, AIM-7, AIM-9, 20 mm", range="~100 km (AIM-54)",
                         notes="Very long-range Phoenix shots. Notch and go low early."),
    "F-14B": dict(title="F-14B Tomcat", role="Fleet interceptor", art="swing", speed="Mach 2.3",
                  arms="AIM-54 Phoenix, AIM-7, AIM-9, 20 mm", range="~100 km (AIM-54)",
                  notes="Very long-range Phoenix shots. Notch and go low early."),
    "MiG-29A": dict(title="MiG-29A \"Fulcrum-A\"", role="Air superiority", art="twin", speed="Mach 2.25",
                    arms="R-27R, R-73 (helmet-cued), 30 mm", range="~40 km (R-27R)",
                    notes="Superb up close with the R-73; can find you silently with its IRST. Don't merge."),
    "MiG-29S": dict(title="MiG-29S \"Fulcrum-C\"", role="Air superiority", art="twin", speed="Mach 2.25",
                    arms="R-77 active radar, R-27, R-73, 30 mm", range="~50 km (R-77)",
                    notes="Fire-and-forget R-77s. Respect its BVR shot and its R-73 up close."),
    "Su-27": dict(title="Su-27 \"Flanker-B\"", role="Air superiority", art="twin", speed="Mach 2.35",
                  arms="R-27ER/ET, R-73, 30 mm", range="~60 km (R-27ER)",
                  notes="Long-range R-27ERs and lots of fuel and missiles. Its IR R-27ET gives no RWR warning."),
    "Su-30": dict(title="Su-30 \"Flanker-C\"", role="Multirole air superiority", art="twin",
                  speed="Mach 2.0", arms="R-77, R-27ER, R-73, 30 mm", range="~60 km",
                  notes="The most dangerous fighter here: active R-77s plus long-range R-27ERs."),
    "F-15C": dict(title="F-15C Eagle", role="Air superiority", art="twin", speed="Mach 2.5",
                  arms="AIM-120 / AIM-7, AIM-9, 20 mm", range="~50 km (AIM-120)",
                  notes="Excellent radar and long-range AMRAAMs. Use terrain and notch."),
    "F-16A": dict(title="F-16A Fighting Falcon", role="Multirole fighter", art="jet", speed="Mach 2.0",
                  arms="AIM-9, 20 mm M61", range="~10 km (IR)",
                  notes="Very agile. The early F-16A is mainly a within-visual-range threat."),
    "F-16C_50": dict(title="F-16C Viper", role="Multirole fighter", art="jet", speed="Mach 2.0",
                     arms="AIM-120C, AIM-9X, 20 mm M61", range="~50 km (AIM-120C)",
                     notes="Active AMRAAMs and a helmet-cued AIM-9X. Very agile."),
    "FA-18C_hornet": dict(title="F/A-18C Hornet", role="Multirole fighter", art="twin", speed="Mach 1.8",
                          arms="AIM-120C, AIM-9X, 20 mm M61", range="~50 km (AIM-120C)",
                          notes="Great nose authority at slow speed; don't get into a slow knife fight."),
}

# --------------------------------------------------------------- SAM systems
SAM_SYSTEMS = {
    "SA-2 Guideline": dict(title="SA-2 \"Guideline\"", nato="S-75 Dvina", role="Medium/high-altitude SAM",
                           art="sam_big", range="~45 km", alt="~25,000 m", guidance="Radio command (Fan Song radar)",
                           rwr="2", notes="Huge, smoky missile you can often see. Beam it, chaff, and break hard late. "
                                          "Kill the Fan Song radar and the site is blind."),
    "SA-3 Goa": dict(title="SA-3 \"Goa\"", nato="S-125 Neva", role="Low/medium-altitude SAM", art="sam",
                     range="~25 km", alt="~18,000 m (low as 20 m)", guidance="Radio command (Low Blow radar)",
                     rwr="3", notes="Designed to catch low flyers. Kill the Low Blow tracking radar."),
    "SA-6 Gainful": dict(title="SA-6 \"Gainful\"", nato="2K12 Kub", role="Mobile medium-range SAM",
                         art="sam", range="~25 km", alt="~14,000 m", guidance="Semi-active radar",
                         rwr="6", notes="One Straight Flush radar guides the whole battery: kill it and the "
                                        "launchers can't shoot. Missile is fast and agile; beam and chaff."),
    "SA-11 Gadfly": dict(title="SA-11 \"Gadfly\"", nato="9K37 Buk", role="Mobile medium-range SAM",
                         art="sam", range="~35 km", alt="~22,000 m", guidance="Semi-active radar",
                         rwr="11", notes="Every launcher has its own radar, so killing the search radar "
                                         "doesn't silence it. Hunt the launchers with stand-off weapons."),
    "SA-10 Grumble": dict(title="SA-10 \"Grumble\"", nato="S-300PS", role="Long-range strategic SAM",
                          art="sam_big", range="~75 km", alt="~27,000 m", guidance="Track-via-missile",
                          rwr="10", notes="Deadly at long range. Stay low and behind terrain; attack with "
                                          "HARMs or stand-off weapons from outside its envelope."),
    "SA-20 Gargoyle": dict(title="SA-20 \"Gargoyle\"", nato="S-300PMU1 (mod)", role="Long-range SAM",
                           art="sam_big", range="~150 km", alt="~27,000 m", guidance="Track-via-missile",
                           notes="Huge envelope. Treat its area as no-go above the terrain."),
    "SA-20B Gargoyle": dict(title="SA-20B \"Gargoyle\"", nato="S-300PMU2 (mod)", role="Long-range SAM",
                            art="sam_big", range="~200 km", alt="~27,000 m", guidance="Track-via-missile",
                            notes="Huge envelope. Treat its area as no-go above the terrain."),
    "MIM-23 Hawk": dict(title="MIM-23 Hawk", nato="Hawk", role="Medium-range SAM", art="sam",
                        range="~40 km", alt="~14,000 m", guidance="Semi-active radar (CW)", rwr="HA",
                        notes="Kill the tracking radar and the launchers are useless. Beam and chaff."),
    "MIM-104 Patriot": dict(title="MIM-104 Patriot", nato="Patriot", role="Long-range SAM", art="sam_big",
                            range="~70 km+", alt="~24,000 m", guidance="Track-via-missile", rwr="P",
                            notes="Long range and very capable. Fly low behind terrain; use stand-off weapons."),
    "NASAMS": dict(title="NASAMS", nato="NASAMS", role="Medium-range SAM", art="sam",
                   range="~25 km", alt="~15,000 m", guidance="Active radar (AIM-120)",
                   notes="Fires AMRAAMs from the ground: missiles go active, so notch and defend early."),
    "88mm Flak battery": dict(title="8.8 cm Flak battery", nato="Flak 36 + Freya radar", role="Heavy AAA",
                              art="flak", range="~10 km", alt="~8,000 m", guidance="Radar/optical director",
                              notes="Bursts at your altitude. Change height and heading often and don't fly "
                                    "straight and level near it."),
    "Heavy Flak battery": dict(title="Heavy Flak battery", nato="Flak 36/41 + 20 mm", role="Heavy and light AAA",
                               art="flak", range="~10 km", alt="~10,000 m", guidance="Radar/optical director",
                               notes="88s up high, quad 20 mm down low. Jink, and come in fast and low."),
    "3.7-inch AA battery": dict(title="QF 3.7-inch AA battery", nato="3.7-inch AA", role="Heavy AAA",
                                art="flak", range="~9 km", alt="~9,000 m", guidance="Predictor director",
                                notes="Accurate at altitude. Change height and heading often."),
    "Heavy AA battery": dict(title="Heavy AA battery", nato="3.7-inch + Bofors", role="Heavy and light AAA",
                             art="flak", range="~9 km", alt="~9,000 m", guidance="Predictor director",
                             notes="Heavy guns up high, Bofors and .50s down low."),
    "Radar-directed AAA": dict(title="Radar-directed AAA", nato="KS-19 + Fire Can", role="Heavy AAA",
                               art="flak", range="~12 km", alt="~12,000 m", guidance="Fire Can radar",
                               notes="Kill the Fire Can radar and the guns lose accuracy."),
}

# ------------------------------------------------------- short-range / guns
SHORT = {
    "flak38": dict(title="Flakvierling 38", role="Quad 20 mm AAA", art="aaa", range="~2 km", alt="~2,000 m",
                   guidance="Optical", notes="Deadly down low. Stay above 2,000 m or out of range."),
    "flak36": dict(title="8.8 cm Flak 36", role="Heavy AAA", art="flak", range="~10 km", alt="~8,000 m",
                   guidance="Optical/director", notes="Don't fly straight and level near it."),
    "flak41": dict(title="8.8 cm Flak 41", role="Heavy AAA", art="flak", range="~12 km", alt="~10,000 m",
                   guidance="Optical/director", notes="Higher-reaching 88. Jink."),
    "M45_Quadmount": dict(title="M45 Quadmount", role="Quad .50 cal AAA", art="aaa", range="~1.5 km",
                          alt="~1,500 m", guidance="Optical", notes="Low-level only. Stay above it."),
    "bofors40": dict(title="Bofors 40 mm", role="Light AAA", art="aaa", range="~3 km", alt="~3,000 m",
                     guidance="Optical", notes="Dangerous on low strafing runs."),
    "QF_37_AA": dict(title="QF 3.7-inch", role="Heavy AAA", art="flak", range="~9 km", alt="~9,000 m",
                     guidance="Director", notes="Change height and heading often."),
    "ZU-23 Emplacement": dict(title="ZU-23-2", role="Twin 23 mm AAA", art="aaa", range="~2.5 km",
                              alt="~1,500 m", guidance="Optical", notes="Stay above 2,000 m or out of range."),
    "S-60_Type59_Artillery": dict(title="S-60 57 mm", role="AAA", art="aaa", range="~4 km", alt="~4,000 m",
                                  guidance="Optical / radar", notes="Reaches higher than light AAA."),
    "KS-19": dict(title="KS-19 100 mm", role="Heavy AAA", art="flak", range="~12 km", alt="~12,000 m",
                  guidance="Fire Can radar", notes="Kill the Fire Can radar."),
    "ZSU-23-4 Shilka": dict(title="ZSU-23-4 Shilka", role="Radar-guided SPAAG", art="spaag",
                            range="~2.5 km", alt="~1,500 m", guidance="Gun Dish radar", rwr="A",
                            notes="Very accurate quad 23 mm. Stay above 3,000 m or beyond 3 km."),
    "ZSU_57_2": dict(title="ZSU-57-2", role="SPAAG", art="spaag", range="~4 km", alt="~4,000 m",
                     guidance="Optical", notes="Optical only; don't loiter low."),
    "Strela-1 9P31": dict(title="SA-9 \"Gaskin\"", role="IR SAM vehicle", art="ir_sam", range="~4 km",
                          alt="~3,500 m", guidance="Infrared", notes="No radar warning. Flares, and stay high."),
    "Strela-10M3": dict(title="SA-13 \"Gopher\"", role="IR SAM vehicle", art="ir_sam", range="~5 km",
                        alt="~3,500 m", guidance="Infrared", notes="No radar warning. Flares, and stay high."),
    "Osa 9A33 ln": dict(title="SA-8 \"Gecko\"", role="Mobile radar SAM", art="ir_sam", range="~10 km",
                        alt="~5,000 m", guidance="Radio command, own radar", rwr="8",
                        notes="Self-contained, so every vehicle can shoot. Chaff and beam it."),
    "2S6 Tunguska": dict(title="SA-19 \"Grison\" (2S6 Tunguska)", role="Gun/missile SPAAG", art="spaag",
                         range="~8 km", alt="~3,500 m", guidance="Radar + optical", rwr="19",
                         notes="Guns and missiles. Stay above 4,000 m or use stand-off weapons."),
    "Tor 9A331": dict(title="SA-15 \"Gauntlet\" (Tor)", role="Short-range SAM", art="ir_sam",
                      range="~12 km", alt="~6,000 m", guidance="Radio command, own radar", rwr="15",
                      notes="Can shoot down incoming bombs and HARMs. Saturate it or use guided weapons "
                            "from outside 12 km."),
    "Vulcan": dict(title="M163 Vulcan", role="20 mm SPAAG", art="spaag", range="~1.5 km", alt="~1,200 m",
                   guidance="Range-only radar", notes="Low-level threat only."),
    "M48 Chaparral": dict(title="M48 Chaparral", role="IR SAM vehicle", art="ir_sam", range="~5 km",
                          alt="~3,000 m", guidance="Infrared (Sidewinder)", notes="No radar warning. Flares."),
    "Gepard": dict(title="Gepard", role="35 mm radar SPAAG", art="spaag", range="~4 km", alt="~3,000 m",
                   guidance="Search + track radar", notes="Very accurate. Stay above 4,000 m."),
    "Roland ADS": dict(title="Roland", role="Short-range SAM", art="ir_sam", range="~8 km", alt="~5,500 m",
                       guidance="Radar / optical command", notes="Chaff, beam, or stay above 6,000 m."),
    "M1097 Avenger": dict(title="Avenger", role="Stinger SAM vehicle", art="ir_sam", range="~4.5 km",
                          alt="~3,800 m", guidance="Infrared", notes="No radar warning. Flares, stay high."),
    "M6 Linebacker": dict(title="M6 Linebacker", role="Stinger + 25 mm", art="ir_sam", range="~4.5 km",
                          alt="~3,800 m", guidance="Infrared", notes="No radar warning. Flares, stay high."),
    "SA-18 Igla manpad": dict(title="SA-18 \"Grouse\" (Igla)", role="MANPADS", art="manpads",
                              range="~5 km", alt="~3,500 m", guidance="Infrared",
                              notes="Invisible until launch. Pre-emptive flares on low passes; stay high."),
    "SA-18 Igla-S manpad": dict(title="SA-24 \"Grinch\" (Igla-S)", role="MANPADS", art="manpads",
                                range="~6 km", alt="~3,500 m", guidance="Infrared",
                                notes="Invisible until launch. Pre-emptive flares on low passes; stay high."),
    "Soldier stinger": dict(title="FIM-92 Stinger", role="MANPADS", art="manpads", range="~4.5 km",
                            alt="~3,800 m", guidance="Infrared",
                            notes="Invisible until launch. Pre-emptive flares on low passes; stay high."),
}

# ------------------------------------------------------------- EW radars
EWR = {
    "p-19 s-125 sr": dict(title="P-19 \"Flat Face\"", role="Search radar", art="radar", range="~150 km",
                          notes="No weapons, but it cues SAMs and fighters onto you."),
    "1L13 EWR": dict(title="1L13 \"Box Spring\"", role="Early-warning radar", art="radar", range="~300 km",
                     notes="No weapons, but it cues SAMs and fighters onto you."),
    "55G6 EWR": dict(title="55G6 \"Tall Rack\"", role="Early-warning radar", art="radar", range="~400 km",
                     notes="No weapons, but it cues SAMs and fighters onto you."),
    "FuMG-401": dict(title="FuMG 401 \"Freya\"", role="Early-warning radar", art="radar",
                     range="~150 km", notes="No weapons, but it warns flak and fighters you're coming."),
    "FPS-117": dict(title="AN/FPS-117", role="Early-warning radar", art="radar", range="~400 km",
                    notes="No weapons, but it cues SAMs and fighters onto you."),
}

# ------------------------------------------------------------ armor/ships
def _tank(title, gun, atgm=None, era=""):
    notes = "Main gun and a heavy MG for low aircraft."
    if atgm:
        notes += f" Can fire {atgm} through the gun: a real threat to hovering helicopters."
    return dict(title=title, role=f"Main battle tank{era}", art="tank", arms=gun, notes=notes)


ARMOR = {
    "Pz_IV_H": _tank("Panzer IV H", "75 mm KwK 40"),
    "Pz_V_Panther_G": _tank("Panther G", "75 mm KwK 42"),
    "Tiger_I": _tank("Tiger I", "88 mm KwK 36"),
    "Tiger_II_H": _tank("Tiger II", "88 mm KwK 43"),
    "M4_Sherman": _tank("M4 Sherman", "75 mm M3"),
    "Cromwell_IV": _tank("Cromwell IV", "75 mm OQF"),
    "M4A4_Sherman_FF": _tank("Sherman Firefly", "17-pounder"),
    "Churchill_VII": _tank("Churchill VII", "75 mm OQF"),
    "T-34-85": _tank("T-34-85", "85 mm ZiS-S-53"),
    "PT_76": dict(title="PT-76", role="Light amphibious tank", art="tank", arms="76 mm D-56T",
                  notes="Light armor; easy kill."),
    "T-55": _tank("T-55", "100 mm D-10T"),
    "T62M": _tank("T-62M", "115 mm U-5TS", atgm="9M117 Bastion (~4 km)"),
    "M-60": _tank("M60A3 Patton", "105 mm M68"),
    "T-72B": _tank("T-72B", "125 mm 2A46", atgm="9M119 Svir (~4 km)"),
    "T-80B": _tank("T-80B", "125 mm 2A46", atgm="9M112 Kobra (~4 km)"),
    "T-80UD": _tank("T-80U", "125 mm 2A46", atgm="9M119 Refleks (~5 km)"),
    "Leopard1A3": _tank("Leopard 1A3", "105 mm L7"),
    "M-1 Abrams": _tank("M1A2 Abrams", "120 mm M256"),
    "T-72B3": _tank("T-72B3", "125 mm 2A46M", atgm="9M119 Svir (~4 km)"),
    "T-90": _tank("T-90A", "125 mm 2A46M", atgm="9M119 Refleks (~5 km)"),
    "leopard-2A4": _tank("Leopard 2A4", "120 mm Rh-120"),
    "Leopard-2A5": _tank("Leopard 2A5", "120 mm Rh-120"),
    "M1A2C_SEP_V3": _tank("M1A2C SEP v3 Abrams", "120 mm M256"),
    "Sd_Kfz_251": dict(title="Sd.Kfz. 251", role="Halftrack APC", art="apc", arms="MG 42",
                       notes="Light armor and an MG; dangerous only to low strafing passes."),
    "M2A1_halftrack": dict(title="M2A1 Halftrack", role="Halftrack APC", art="apc", arms=".50 cal",
                           notes="The .50 cal can hurt low aircraft."),
    "BTR-60": dict(title="BTR-60", role="APC", art="apc", arms="14.5 mm KPVT",
                   notes="Its 14.5 mm can hit low helicopters."),
    "M-113": dict(title="M113", role="APC", art="apc", arms=".50 cal", notes="Light threat to helicopters."),
    "BMP-2": dict(title="BMP-2", role="Infantry fighting vehicle", art="apc", arms="30 mm 2A42, 9M113 ATGM",
                  notes="The 30 mm cannon elevates high: a real threat to helicopters below 2 km."),
    "M-2 Bradley": dict(title="M2 Bradley", role="Infantry fighting vehicle", art="apc",
                        arms="25 mm M242, TOW", notes="The 25 mm is a threat to low helicopters."),
    "BMP-3": dict(title="BMP-3", role="Infantry fighting vehicle", art="apc", arms="100 mm + 30 mm, ATGM",
                  notes="The 30 mm cannon is a threat to helicopters."),
}


def _ship(title, role, sam=None, guns="", art="ship"):
    return dict(title=title, role=role, art=art, arms=", ".join(x for x in (sam, guns) if x),
                notes=("Ship-launched SAMs: " + sam + ". Attack from outside that range."
                       if sam else "Guns only. Watch the AAA on low passes."))


SHIPS = {
    "Schnellboot_type_S130": _ship("S-boat (S-130)", "Fast attack craft", guns="20/37 mm flak", art="boat"),
    "Uboat_VIIC": _ship("U-boat Type VIIC", "Submarine (surfaced)", guns="20 mm flak", art="boat"),
    "LST_Mk2": _ship("LST Mk.II", "Landing ship", guns="40 mm / 20 mm AA"),
    "USS_Samuel_Chase": _ship("USS Samuel Chase", "Attack transport", guns="5-inch, 40 mm, 20 mm AA"),
    "Dry-cargo ship-1": _ship("Cargo ship", "Merchant", guns=""),
    "Dry-cargo ship-2": _ship("Cargo ship", "Merchant", guns=""),
    "ALBATROS": _ship("Grisha corvette", "ASW corvette", sam="SA-N-4 Gecko (~10 km)", guns="57 mm, 30 mm"),
    "MOLNIYA": _ship("Molniya corvette", "Missile corvette", sam="SA-N-5 MANPADS (~5 km)",
                     guns="76 mm, 30 mm CIWS", art="boat"),
    "REZKY": _ship("Krivak frigate", "ASW frigate", sam="SA-N-4 Gecko (~10 km)", guns="76 mm"),
    "NEUSTRASH": _ship("Neustrashimy frigate", "Frigate", sam="SA-N-9 Gauntlet (~12 km)",
                       guns="100 mm, CIWS"),
    "MOSCOW": _ship("Slava-class cruiser \"Moskva\"", "Missile cruiser",
                    sam="SA-N-6 Grumble (~75 km) and SA-N-4", guns="130 mm, CIWS"),
    "leander-gun-achilles": _ship("Leander frigate", "Frigate", sam="Sea Cat (~5 km)", guns="4.5-inch"),
    "leander-gun-andromeda": _ship("Leander frigate", "Frigate", sam="Sea Cat (~5 km)", guns="4.5-inch"),
    "leander-gun-ariadne": _ship("Leander frigate", "Frigate", sam="Sea Cat (~5 km)", guns="4.5-inch"),
    "PERRY": _ship("Oliver Hazard Perry frigate", "Frigate", sam="SM-1 (~40 km)", guns="76 mm, Phalanx"),
    "TICONDEROG": _ship("Ticonderoga cruiser", "AEGIS cruiser", sam="SM-2 (~100 km+)",
                        guns="5-inch, Phalanx"),
    "USS_Arleigh_Burke_IIa": _ship("Arleigh Burke destroyer", "AEGIS destroyer", sam="SM-2 (~100 km+)",
                                   guns="5-inch, Phalanx"),
}

ARTILLERY = {t.id: dict(title=getattr(t, "name", t.id), role="Artillery", art="artillery",
                        notes="No threat to aircraft; a ground target.")
             for t in {f["artillery"] for f in eras.FORCES.values()}}

ENTRIES = {}
for _cat, _table in (("fighter", FIGHTERS), ("sam", SAM_SYSTEMS), ("short", SHORT), ("ewr", EWR),
                     ("armor", ARMOR), ("ship", SHIPS), ("artillery", ARTILLERY)):
    for _k, _v in _table.items():
        ENTRIES[_k] = {**_v, "category": _cat}


def _components():
    """Type id -> SAM system label, so a site's radar and launchers share one card."""
    out = {}
    layouts = [site for f in eras.FORCES.values() for site in f["sam"].values()]
    layouts += [mods.SA20, mods.SA20B]
    for label, layout in layouts:
        for t, _b, _d in layout:
            out.setdefault(t.id, label)
    return out


COMPONENT = _components()
# Shared towed guns inside flak batteries still get their own card.
for _gun in ("flak36", "flak41", "flak38", "QF_37_AA", "bofors40", "M45_Quadmount", "KS-19",
             "S-60_Type59_Artillery"):
    COMPONENT.pop(_gun, None)


def key_for(type_id, group_name=""):
    if group_name.startswith("EW ") and type_id in EWR:
        return type_id
    if type_id in COMPONENT:
        return COMPONENT[type_id]
    return type_id if type_id in ENTRIES else None


# ---------------------------------------------------------------- dimensions
# (length m, span/width m or None, height m or None, approximate?)
# Aircraft: published figures. Ground systems and ships: approximate main-vehicle
# sizes, shown with "≈" on the drawings.
DIMS = {
    "Bf-109K-4": (9.0, 9.9, 2.6, False), "FW-190A8": (9.0, 10.5, 3.95, False),
    "FW-190D9": (10.2, 10.5, 3.35, False), "P-47D-30": (11.0, 12.4, 4.4, False),
    "P-51D": (9.8, 11.3, 4.1, False), "P-51D-30-NA": (9.8, 11.3, 4.1, False),
    "SpitfireLFMkIX": (9.5, 11.2, 3.9, False), "MiG-15bis": (10.1, 10.1, 3.7, False),
    "F-86F Sabre": (11.4, 11.3, 4.5, False), "MiG-19P": (13.0, 9.0, 3.9, False),
    "MiG-21Bis": (14.5, 7.15, 4.1, False), "MiG-23MLD": (16.7, 14.0, 4.8, False),
    "F-5E-3": (14.5, 8.1, 4.1, False), "F-4E-45MC": (19.2, 11.7, 5.0, False),
    "F-14A-135-GR": (19.1, 19.5, 4.9, False), "F-14B": (19.1, 19.5, 4.9, False),
    "MiG-29A": (17.3, 11.4, 4.7, False), "MiG-29S": (17.3, 11.4, 4.7, False),
    "Su-27": (21.9, 14.7, 5.9, False), "Su-30": (21.9, 14.7, 6.4, False),
    "F-15C": (19.4, 13.05, 5.6, False), "F-16A": (15.1, 9.96, 4.9, False),
    "F-16C_50": (15.1, 9.96, 4.9, False), "FA-18C_hornet": (17.1, 12.3, 4.7, False),
    # SAM systems (main launcher / TEL)
    "SA-2 Guideline": (10.6, None, None, True), "SA-3 Goa": (6.1, None, None, True),
    "SA-6 Gainful": (7.4, 3.2, 3.5, True), "SA-11 Gadfly": (9.3, 3.3, 3.8, True),
    "SA-10 Grumble": (13.0, 3.1, 3.8, True), "SA-20 Gargoyle": (13.0, 3.1, 3.8, True),
    "SA-20B Gargoyle": (13.0, 3.1, 3.8, True), "MIM-23 Hawk": (5.0, None, None, True),
    "MIM-104 Patriot": (10.4, 2.5, 3.9, True), "NASAMS": (7.0, 2.5, 3.0, True),
    "88mm Flak battery": (7.6, 2.3, 2.4, True), "Heavy Flak battery": (7.6, 2.3, 2.4, True),
    "3.7-inch AA battery": (8.6, 2.4, 2.5, True), "Heavy AA battery": (8.6, 2.4, 2.5, True),
    "Radar-directed AAA": (9.5, 2.3, 2.6, True),
    # short-range air defense and guns
    "flak38": (4.1, 2.4, 2.0, True), "flak36": (7.6, 2.3, 2.4, True), "flak41": (9.6, 2.4, 2.4, True),
    "M45_Quadmount": (3.0, 2.1, 1.9, True), "bofors40": (6.4, 2.0, 2.3, True),
    "QF_37_AA": (8.6, 2.4, 2.5, True), "ZU-23 Emplacement": (4.6, 1.8, 1.9, True),
    "S-60_Type59_Artillery": (8.5, 2.1, 2.5, True), "KS-19": (9.5, 2.3, 2.6, True),
    "ZSU-23-4 Shilka": (6.5, 3.1, 2.6, True), "ZSU_57_2": (8.5, 3.3, 2.8, True),
    "Strela-1 9P31": (5.8, 2.4, 2.3, True), "Strela-10M3": (6.6, 2.9, 3.8, True),
    "Osa 9A33 ln": (9.1, 2.8, 4.2, True), "2S6 Tunguska": (7.9, 3.2, 4.0, True),
    "Tor 9A331": (7.5, 3.3, 5.1, True), "Vulcan": (4.9, 2.7, 2.7, True),
    "M48 Chaparral": (6.1, 2.7, 2.9, True), "Gepard": (7.7, 3.3, 3.0, True),
    "Roland ADS": (6.9, 3.2, 2.9, True), "M1097 Avenger": (5.0, 2.2, 2.6, True),
    "M6 Linebacker": (6.6, 3.6, 3.4, True), "SA-18 Igla manpad": (1.7, None, None, True),
    "SA-18 Igla-S manpad": (1.7, None, None, True), "Soldier stinger": (1.5, None, None, True),
    # armor (hull + gun forward)
    "Pz_IV_H": (7.0, 2.9, 2.7, True), "Pz_V_Panther_G": (8.7, 3.3, 3.0, True),
    "Tiger_I": (8.5, 3.6, 3.0, True), "Tiger_II_H": (10.3, 3.8, 3.1, True),
    "M4_Sherman": (5.8, 2.6, 2.7, True), "Cromwell_IV": (6.4, 3.0, 2.5, True),
    "M4A4_Sherman_FF": (7.8, 2.7, 2.7, True), "Churchill_VII": (7.4, 3.3, 2.5, True),
    "T-34-85": (8.2, 3.0, 2.7, True), "PT_76": (7.6, 3.1, 2.3, True), "T-55": (9.0, 3.3, 2.4, True),
    "T62M": (9.3, 3.3, 2.4, True), "M-60": (9.4, 3.6, 3.3, True), "T-72B": (9.5, 3.6, 2.2, True),
    "T-80B": (9.7, 3.6, 2.2, True), "T-80UD": (9.7, 3.6, 2.2, True),
    "Leopard1A3": (9.5, 3.4, 2.6, True), "M-1 Abrams": (9.8, 3.7, 2.4, True),
    "T-72B3": (9.5, 3.6, 2.2, True), "T-90": (9.6, 3.8, 2.2, True),
    "leopard-2A4": (9.7, 3.7, 3.0, True), "Leopard-2A5": (11.0, 3.8, 3.0, True),
    "M1A2C_SEP_V3": (9.8, 3.7, 2.4, True), "Sd_Kfz_251": (5.8, 2.1, 1.8, True),
    "M2A1_halftrack": (6.2, 2.2, 2.3, True), "BTR-60": (7.6, 2.8, 2.3, True),
    "M-113": (4.9, 2.7, 2.5, True), "BMP-2": (6.7, 3.2, 2.5, True),
    "M-2 Bradley": (6.6, 3.6, 3.0, True), "BMP-3": (7.1, 3.3, 2.3, True),
    # ships
    "Schnellboot_type_S130": (35, 5.1, None, True), "Uboat_VIIC": (67, 6.2, None, True),
    "LST_Mk2": (100, 15, None, True), "USS_Samuel_Chase": (150, 21, None, True),
    "Dry-cargo ship-1": (130, 20, None, True), "Dry-cargo ship-2": (110, 18, None, True),
    "ALBATROS": (71, 10, None, True), "MOLNIYA": (56, 10, None, True), "REZKY": (123, 14, None, True),
    "NEUSTRASH": (129, 15.6, None, True), "MOSCOW": (186, 20.8, None, True),
    "leander-gun-achilles": (113, 12.5, None, True), "leander-gun-andromeda": (113, 12.5, None, True),
    "leander-gun-ariadne": (113, 12.5, None, True), "PERRY": (136, 13.7, None, True),
    "TICONDEROG": (173, 16.8, None, True), "USS_Arleigh_Burke_IIa": (155, 20, None, True),
}

# Finer drawing styles than the card class, so a Su-27 and an F-16 don't look alike.
STYLE = {
    "MiG-21Bis": "delta", "MiG-23MLD": "swing", "F-14A-135-GR": "tomcat", "F-14B": "tomcat",
    "F-5E-3": "light", "F-16A": "viper", "F-16C_50": "viper", "F-4E-45MC": "phantom",
    "MiG-15bis": "early_jet", "F-86F Sabre": "early_jet", "MiG-19P": "early_jet",
    "MiG-29A": "flanker", "MiG-29S": "flanker", "Su-27": "flanker", "Su-30": "flanker",
    "F-15C": "eagle", "FA-18C_hornet": "hornet",
    "SA-2 Guideline": "rail", "SA-3 Goa": "rail", "MIM-23 Hawk": "rail",
    "SA-10 Grumble": "canister", "SA-20 Gargoyle": "canister", "SA-20B Gargoyle": "canister",
    "MIM-104 Patriot": "canister", "NASAMS": "canister",
    "Osa 9A33 ln": "wheeled_sam", "Strela-1 9P31": "wheeled_sam", "M1097 Avenger": "wheeled_sam",
    "BTR-60": "wheeled_apc", "Tor 9A331": "tor",
}


def _base_card(key):
    e = ENTRIES.get(key)
    if not e:
        return None
    out = {**e, "key": key}
    if key in DIMS:
        length, span, height, approx = DIMS[key]
        out["dims"] = {"length": length, "span": span, "height": height, "approx": approx}
    out["style"] = STYLE.get(key, e.get("art"))
    return out


# ------------------------------------------------------------ real drawings
# Wikimedia Commons 3-view drawings fetched at image build (tools/fetch_drawings.py).
DRAWINGS_DIR = str(paths.folder("DRAWINGS_DIR", "drawings"))
# Variants that borrow another drawing; "shows" is printed on the sheet when the
# drawing isn't of the exact variant.
DRAWING_ALIAS = {"P-51D-30-NA": "P-51D", "MiG-29S": "MiG-29A", "F-14A-135-GR": "F-14B",
                 "T-72B3": "T-72B", "T-90": "T-72B", "T-80UD": "T-80B", "Leopard-2A5": "leopard-2A4"}
DRAWING_SHOWS = {"T-72B": "T-72", "T-80B": "T-80", "leopard-2A4": "Leopard 2A4", "MiG-29A": "MiG-29",
                 "P-51D": "P-51D"}


def _drawings():
    try:
        with open(os.path.join(DRAWINGS_DIR, "index.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


DRAWINGS = _drawings()


def card(key):
    """Threat-ID card for a key: data, dimensions, drawing style and real drawing if any."""
    out = _base_card(key)
    if out:
        src = key if key in DRAWINGS else DRAWING_ALIAS.get(key, "")
        d = DRAWINGS.get(src)
        if d:
            out["drawing"] = {**d, "url": f"/drawings/{d['file']}"}
            if src != key and src in DRAWING_SHOWS:
                out["drawing"]["shows"] = DRAWING_SHOWS[src]
    return out
