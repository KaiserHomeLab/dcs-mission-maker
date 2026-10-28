"""Threat ID drawings made with an image generator (Gemini or similar), and the prompts for them.

    python tools/art_drawings.py

1. Cleans every image in art/drawings/ into app/data/drawings/: greyscale, pure white
   background, trimmed to the drawing, 1600 px wide, a small PNG (~30 KB). Name each image
   after its unit, as art/PROMPTS.md says (e.g. MiG_29A.png); JPEG data is fine.
2. Rewrites art/PROMPTS.md: a ready-to-paste prompt for every Threat ID unit that has no
   drawing in app/data/drawings/ yet.

art/drawings/ (the originals) isn't committed; app/data/drawings/ and art/PROMPTS.md are.
Units without a drawing there use the generated line drawing.
"""
import difflib
import os
import sys

from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app import threatdb  # noqa: E402

SRC = os.path.join(ROOT, "art", "drawings")
OUT = threatdb.DRAWINGS_DIR
PROMPTS = os.path.join(ROOT, "art", "PROMPTS.md")
WIDTH = 1600

# Units that look the same as another one: no prompt of their own, they use its drawing.
SAME = threatdb.DRAWING_SAME


# ------------------------------------------------------------------ cleaning
def clean(src, dst):
    im = Image.open(src).convert("L")
    im = im.point(lambda v: 255 if v > 215 else v)  # paper tint and JPEG speckle -> white
    box = ImageOps.invert(im).getbbox()
    if not box:
        raise ValueError("the image is blank")
    pad = round(max(im.size) * 0.015)
    im = im.crop((max(box[0] - pad, 0), max(box[1] - pad, 0),
                  min(box[2] + pad, im.width), min(box[3] + pad, im.height)))
    if im.width > WIDTH:
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
    im = im.point(lambda v: 255 if v > 215 else (0 if v < 60 else v))
    im.quantize(4).save(dst, "PNG", optimize=True)


def clean_all():
    if not os.path.isdir(SRC):
        return
    os.makedirs(OUT, exist_ok=True)
    names = {threatdb.drawing_name(k): k for k in threatdb.ENTRIES}
    for f in sorted(os.listdir(SRC)):
        stem, ext = os.path.splitext(f)
        if ext.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        name = stem + ".png"
        if name not in names:
            near = difflib.get_close_matches(name, list(names), n=1)
            print(f"skip {f}: no unit is called that" + (f" (did you mean {near[0]}?)" if near else ""))
            continue
        src, dst = os.path.join(SRC, f), os.path.join(OUT, name)
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            continue  # already cleaned
        try:
            clean(src, dst)
        except (OSError, ValueError) as e:
            print(f"skip {f}: {e}")
            continue
        print(f"ok   {f} -> {os.path.getsize(os.path.join(OUT, name)) // 1024} KB")


# ------------------------------------------------------------------ prompts
STYLE = """Style: a technical line drawing like a published scale-modelling plan. Black lines only on a
pure white background (#FFFFFF). Uniform thin lines for detail, slightly heavier outlines.
ABSOLUTELY NO grid, NO text of any kind, NO labels, NO arrows, NO callouts, NO title block,
NO scale bar, NO dimensions, NO border, NO paper texture, NO colour, NO shading, NO shadows.
Draw each view ONCE. Views must not overlap and must have plenty of white margin.
Landscape image, about 1.4:1."""

VIEWS = """Three orthographic views of the {name} at exactly the same scale, no perspective:
- side view ({side}) across the top
- top-down plan view directly below it, {front} pointing left, lined up so the front and
  rear sit at the same horizontal positions as in the side view
- front view (looking straight at the {front}) to the right of the plan view"""

SHIP_VIEWS = """Two orthographic views of the {name} at exactly the same scale, no perspective:
- side view (port side, bow pointing left) across the top half, waterline as a straight line
- top-down plan view directly below it, bow pointing left, lined up so bow and stern sit
  at the same horizontal positions as in the side view
No front view."""

POSE = {
    "air": "Clean configuration: no external fuel tanks, bombs or missiles{stores}. Landing gear down.",
    "ground": "{pose}",
    "towed": "In firing position{pose}.",
    "radar": "Antennas in their working position, facing forward.",
    "manpads": "Only the weapon itself, NO soldier, NO hands.",
    "ship": "",
}


def fmt(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")


def proportions(kind, u, dims):
    L, W, H = (u.get(k) for k in ("length", "width", "height"))
    if dims:
        L, W, H = (L or dims[0]), (W or dims[1]), (H or dims[2])
    if not L:
        return ""
    if kind == "air":
        r = W / L
        span = "about the same as" if abs(r - 1) < 0.04 else f"{fmt(r)}x"
        return (f"Real proportions (approximate): length {fmt(L)} m, wingspan {fmt(W)} m, height {fmt(H)} m.\n"
                f"In the plan view the wingspan must be {span} the length. In the side view the length\n"
                f"must be {fmt(L / H)}x the height.")
    if kind == "ship":
        return (f"Real proportions (approximate): length {fmt(L)} m, beam {fmt(W)} m. In the plan view the ship\n"
                f"must be {fmt(L / W)}x as long as it is wide; it should look long and slender.")
    hull = u.get("hull") or L
    size = f"length {fmt(hull)} m" + (f" ({fmt(L)} m including the gun)" if hull + 0.2 < L else "")
    size += (f", width {fmt(W)} m" if W else "") + (f", height {fmt(H)} m" if H else "")
    out = f"Real proportions (approximate): {size}."
    rules = []
    if W:
        rules.append(f"In the plan view it must be {fmt(hull / W)}x as long as it is wide"
                     + (" (not counting the gun)." if hull + 0.2 < L else "."))
    if H:
        rules.append(f"In the side view it must be {fmt(hull / H)}x as long as it is tall.")
    return out + ("\n" + "\n".join(rules) if rules else "")


def prompt(key):
    u = UNITS[key]
    kind = u["kind"]
    if kind == "ship":
        views = SHIP_VIEWS.format(name=u["name"])
    elif kind == "air":
        views = VIEWS.format(name=u["name"], side="left profile, nose pointing left", front="nose")
    else:
        views = VIEWS.format(name=u["name"], side="left side, front pointing left", front="front")
    pose = POSE[kind].format(stores=u.get("stores", ""), pose=u.get("pose", "Facing forward, any turret or "
                             "launcher pointing forward in its travel position."))
    parts = [views, pose, proportions(kind, u, threatdb.DIMS.get(key)),
             "Distinctive features that must be correct:\n"
             + "\n".join(f if f.startswith("  ") else f"- {f}" for f in u["features"]), STYLE]
    return "\n\n".join(p for p in parts if p)


def status(key):
    alias = threatdb.DRAWING_ALIAS.get(key)
    if alias in threatdb.DRAWINGS:
        return f"borrows the {threatdb.ENTRIES[alias]['title']} drawing"
    return "generated line drawing"


ORDER = ("fighter", "sam", "short", "ewr", "armor", "artillery", "ship")
HEADINGS = {"fighter": "Aircraft", "sam": "SAM systems", "short": "Short-range air defence and AAA",
            "ewr": "Radars", "armor": "Armour", "artillery": "Artillery", "ship": "Ships"}


def write_prompts():
    have = set(os.listdir(OUT)) if os.path.isdir(OUT) else set()
    missing = [k for k in threatdb.ENTRIES if k not in SAME and threatdb.drawing_name(k) not in have]
    unknown = [k for k in missing if k not in UNITS]
    if unknown:
        raise SystemExit(f"no prompt data for: {', '.join(unknown)} (add them to UNITS in {__file__})")
    done = len([k for k in threatdb.ENTRIES if k not in SAME]) - len(missing)
    out = ["# Threat ID drawing prompts", "",
           "Written by `python tools/art_drawings.py`; don't edit by hand.", "",
           f"{done} units have a drawing, {len(missing)} still need one.", "",
           "1. Paste one block into a new Gemini chat. If it adds text, a grid or a second copy of a view,",
           "   reply \"same drawing, remove all text and the grid\" in the same chat.",
           "2. Check it against a photo: right shape, right number of wheels, engines or fins.",
           "   The plan view's proportions are the part most often wrong.",
           "3. Save it in `art/drawings/` with the name shown, then run `python tools/art_drawings.py`.",
           "   That cleans it into `app/data/drawings/` and takes it off this list.", ""]
    for cat in ORDER:
        keys = [k for k in missing if threatdb.ENTRIES[k]["category"] == cat]
        if not keys:
            continue
        out += [f"## {HEADINGS[cat]}", ""]
        for k in keys:
            title = threatdb.ENTRIES[k]["title"]
            also = [a for a in dict.fromkeys(threatdb.ENTRIES[s]["title"] for s, t in SAME.items() if t == k)
                    if a != title]
            used = f" Also used for: {', '.join(also)}." if also else ""
            out += [f"### {title}  ->  `{threatdb.drawing_name(k)}`", "",
                    f"Now: {status(k)}.{used}", "", "```", prompt(k), "```", ""]
    with open(PROMPTS, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out))
    print(f"{PROMPTS}: {len(missing)} prompts")


# ------------------------------------------------------------------ unit data
def air(name, features, stores=""):
    return {"kind": "air", "name": name, "features": features, "stores": stores}


def gnd(name, features, kind="ground", **kw):
    return {"kind": kind, "name": name, "features": features, **kw}


def ship(name, features):
    return {"kind": "ship", "name": name, "features": features}


TIP = ", but with a Sidewinder on each wingtip rail"
UNITS = {
    # ------------------------------------------------------------ aircraft
    "Bf-109K-4": air("Messerschmitt Bf 109 K-4 (German WWII fighter, 1944-45)", [
        "single inline engine (DB 605) with a three-blade propeller and a large spinner",
        "narrow-track main gear that folds outwards, retractable tail wheel",
        "small straight-tapered wing with rounded tips and a radiator under each wing",
        "tall wooden tail fin, frameless \"Erla\" clear-view canopy hood",
        "supercharger air intake on the left side of the cowling, small bulges over the guns"]),
    "FW-190A8": air("Focke-Wulf Fw 190 A-8 (German WWII fighter, 1944)", [
        "big round BMW 801 radial engine cowling with a cooling fan behind a three-blade propeller",
        "wide-track main gear that folds inwards toward the fuselage",
        "straight-tapered wing with a squared-off tip, cannon in the wing roots",
        "low, slightly bulged sliding canopy, short fuselage, small fin"]),
    "FW-190D9": air("Focke-Wulf Fw 190 D-9 \"Dora\" (German WWII fighter, 1945)", [
        "long nose with an inline Jumo 213 engine behind a round annular radiator at the front, so the",
        "  nose looks like a radial cowling but much longer than the Fw 190 A's",
        "extra fuselage section in front of the tail, taller fin, three-blade wide paddle propeller",
        "bulged blown canopy, wide-track main gear that folds inwards",
        "straight-tapered wing with squared-off tips"]),
    "P-47D-30": air("Republic P-47D-30 Thunderbolt (US WWII fighter-bomber, bubble-canopy version)", [
        "very large, deep fuselage with a huge radial engine in an oval cowling (intake below the hub)",
        "four-blade propeller, bubble canopy, small dorsal fin fillet in front of the tail",
        "elliptical wings, four .50 cal guns per wing",
        "turbo-supercharger exhaust and intake ducting under the rear fuselage",
        "the fuselage is very wide in the plan view too, not slim"]),
    "P-51D": air("North American P-51D Mustang (US WWII fighter)", [
        "slim fuselage with an inline Merlin engine and a four-blade propeller",
        "large radiator air scoop under the fuselage behind the wing",
        "bubble canopy, small dorsal fin fillet",
        "straight-tapered laminar-flow wing with squared tips, three guns per wing"]),
    "SpitfireLFMkIX": air("Supermarine Spitfire LF Mk IX (British WWII fighter)", [
        "elliptical wing, the most important feature, smooth curved leading and trailing edges",
        "two rectangular radiators, one under each wing, the same size on both sides",
        "four-blade propeller, long slim nose with Merlin engine exhaust stubs",
        "narrow-track main gear folding outwards, teardrop canopy with a rear-view fairing behind it",
        "20 mm cannon barrels sticking forward out of each wing"]),
    "MiG-15bis": air("Mikoyan-Gurevich MiG-15bis (Soviet jet fighter, 1950s)", [
        "round nose air intake split by one straight vertical splitter, short fat fuselage",
        "35 degree swept wing with two tall wing fences on each wing, slight anhedral",
        "tall swept fin with the swept tailplane mounted high up on the fin (cross-shaped tail)",
        "bubble canopy, guns under the nose"]),
    "F-86F Sabre": air("North American F-86F Sabre (US jet fighter, 1950s)", [
        "oval nose air intake, slim fuselage",
        "35 degree swept wing, no wing fences",
        "swept tailplane mounted low on the rear fuselage (NOT on the fin)",
        "bubble canopy set well forward, three gun ports on each side of the nose"]),
    "MiG-19P": air("Mikoyan-Gurevich MiG-19P (Soviet jet fighter, 1950s, radar version)", [
        "nose air intake with a small radar fairing on the upper intake lip",
        "very sharply swept wing (55 degrees) with ONE large wing fence on each wing",
        "twin engines side by side, two round exhausts next to each other at the tail",
        "swept fin, swept low-set all-moving tailplane, small ventral fin"]),
    "MiG-21Bis": air("Mikoyan-Gurevich MiG-21bis (Soviet jet fighter, 1970s)", [
        "delta wing (57 degree sweep) with a small conventional swept tailplane at the very back",
        "round nose air intake with a pointed shock cone in the middle",
        "thick dorsal spine running from the canopy to the fin",
        "tall swept fin, a SMALL ventral fin under the tail, pitot boom on the top right of the nose"]),
    "MiG-23MLD": air("Mikoyan-Gurevich MiG-23MLD (Soviet swing-wing fighter, 1980s)", [
        "variable-sweep wings drawn fully spread forward (16 degrees)",
        "MLD-specific sharp \"dogtooth\" notch in the leading edge of the fixed wing glove",
        "rectangular side air intakes with splitter plates, pointed radar nose",
        "large dorsal fin, large ventral fin under the tail (folded to one side when gear is down)",
        "all-moving swept tailplanes, single engine exhaust"]),
    "F-5E-3": air("Northrop F-5E Tiger II (US light fighter, 1970s)", [
        "slim area-ruled fuselage, long pointed \"shark\" nose",
        "small, thin trapezoidal wing with small leading-edge extensions (LERX) at the root",
        "small side air intakes behind the cockpit, twin engines with two exhausts side by side",
        "single tall fin, all-moving tailplane, two 20 mm guns in the nose"], TIP),
    "F-4E-45MC": air("McDonnell Douglas F-4E Phantom II (US fighter, 1970s)", [
        "outer wing panels bent up 12 degrees (dihedral), dogtooth notch in the outer wing leading edge",
        "all-moving tailplanes bent sharply down (23 degree anhedral)",
        "two large rectangular side air intakes with splitter plates",
        "long nose with the M61 gun fairing underneath, two-seat tandem canopy",
        "two engines with two exhausts under the tail, slightly drooping rear fuselage"]),
    "F-14B": air("Grumman F-14B Tomcat (US Navy fighter)", [
        "variable-sweep wings drawn fully spread forward (20 degrees)",
        "two engines in widely separated nacelles with a broad flat \"pancake\" fuselage between them",
        "twin vertical fins, canted slightly outward, on top of the nacelles",
        "large rectangular air intakes with sloped tops, long pointed nose",
        "two-seat tandem canopy, two small ventral fins under the nacelles"]),
    "MiG-29A": air("Mikoyan MiG-29A Fulcrum-A (Soviet fighter, 1980s)", [
        "two widely spaced engines in separate nacelles with a flat lifting fuselage between them",
        "twin vertical fins on top of the engine nacelles, slightly canted outward",
        "large curved leading-edge root extensions (LERX) with auxiliary intake louvres on top",
        "two wedge-shaped air intakes under the LERX, below the wing",
        "bubble canopy, pointed radar nose, short tail stinger between the nozzles"]),
    "Su-27": air("Sukhoi Su-27 Flanker-B (Soviet single-seat fighter, 1980s)", [
        "SINGLE seat, NO canards: nothing sticks out from the fuselage in front of the wing",
        "long, slender fuselage with a drooped nose and a big bubble canopy",
        "large ogival leading-edge root extensions blending into the wing",
        "two box-shaped air intakes under the fuselage, engines widely spaced",
        "twin vertical fins outboard of the engines, long tail \"stinger\" between the two nozzles",
        "missile rails on the wingtips"]),
    "Su-30": air("Sukhoi Su-30 Flanker-C (Russian two-seat fighter, 1990s, without canards)", [
        "like the Su-27 but with a two-seat tandem canopy under one long bubble",
        "retractable in-flight refuelling probe on the left side of the nose, in front of the canopy",
        "NO canards: nothing sticks out from the fuselage in front of the wing",
        "two box-shaped air intakes under the fuselage, twin fins outboard of the engines",
        "long tail \"stinger\" between the two nozzles, missile rails on the wingtips"]),
    "F-15C": air("McDonnell Douglas F-15C Eagle (US air superiority fighter)", [
        "large, nearly straight-edged swept wing with raked (cut-off) tips",
        "twin vertical fins, straight up (NOT canted), with square tops",
        "big rectangular air intakes on both sides of the fuselage, tilting down at the front",
        "high bubble canopy, single seat, tailplanes with a notch (dogtooth) in the leading edge",
        "two engine nozzles side by side"]),
    "F-16C_50": air("General Dynamics F-16C Block 50 Fighting Falcon (US fighter)", [
        "single chin air intake under the cockpit (the larger \"big mouth\" Block 50 intake)",
        "blended wing-body, cropped delta wing with leading-edge root extensions",
        "frameless bubble canopy with \"bird slicer\" IFF antennas in front of the canopy",
        "single tall fin, two small ventral fins under the rear fuselage, one engine nozzle"], TIP),
    "F-16A": air("General Dynamics F-16A Fighting Falcon (US fighter, early version)", [
        "single chin air intake under the cockpit (the original, smaller intake)",
        "blended wing-body, cropped delta wing with leading-edge root extensions",
        "frameless bubble canopy, no antennas in front of the canopy",
        "single tall fin, two small ventral fins under the rear fuselage, one engine nozzle"], TIP),
    "FA-18C_hornet": air("McDonnell Douglas F/A-18C Hornet (US Navy fighter)", [
        "long, narrow leading-edge extensions (LEX) running from the wing root to beside the windscreen",
        "twin vertical fins canted outward about 20 degrees, placed forward of the tailplanes",
        "D-shaped air intakes under the LEX on each side of the fuselage",
        "trapezoidal wing with a small dogtooth, bubble canopy, sturdy naval landing gear"], TIP),

    # ------------------------------------------------------------ SAM systems (main launcher)
    "SA-2 Guideline": gnd("SA-2 Guideline (S-75) SM-63 launcher loaded with one V-750 missile", [
        "a single long launch rail on a turntable, on a low cross-shaped ground platform",
        "the missile: long slender two-stage missile, large cross-shaped fins on the booster at the",
        "  back, smaller wings in the middle and small control fins near the pointed nose",
        "rail and missile raised about 20 degrees, pointing forward"],
        kind="towed", length=10.6, pose=", missile loaded"),
    "SA-3 Goa": gnd("SA-3 Goa (S-125) 5P73 launcher loaded with four V-601 missiles", [
        "it must NOT look like the SA-2: FOUR shorter, fatter missiles, no single long rail",
        "the four missiles sit in two pairs, one pair above the other (2 over 2), on a turntable;",
        "  the front view shows the four missile noses in a 2 x 2 square",
        "each missile: two-stage, a fat booster with four large fins at the back, cross-shaped wings",
        "  in the middle and small fins near the nose",
        "launcher on a low square ground platform, missiles raised about 20 degrees"],
        kind="towed", length=6.1, pose=", four missiles loaded"),
    "SA-6 Gainful": gnd("SA-6 Gainful (2K12 Kub) 2P25 tracked launcher", [
        "low, flat tracked chassis with six road wheels per side and no return rollers",
        "three large missiles side by side on a turntable on the rear deck, pointing forward over the",
        "  driver's cab",
        "each missile has a long body with cross-shaped wings and fins and a pointed nose"]),
    "SA-11 Gadfly": gnd("SA-11 Gadfly (9K37 Buk) 9A310 tracked launcher with its own radar", [
        "tracked chassis with six road wheels per side and return rollers above them",
        "a large turntable on top carrying four missiles on rails side by side",
        "a big round radar dish under a cover at the front of the turntable, below the missiles",
        "driver's cab at the front left of the hull"]),
    "SA-10 Grumble": gnd("SA-10 Grumble (S-300PS) 5P85S launcher on a MAZ-543 8x8 truck", [
        "very long 8x8 truck: eight large wheels in four axles, two pairs at the front, two at the back",
        "two separate small cabs at the front, one each side of the engine",
        "four long cylindrical missile launch tubes in a block lying flat along the back (travel position)",
        "a big support frame at the rear end for raising the tubes"]),
    "SA-20 Gargoyle": gnd("SA-20 Gargoyle (S-300PMU1) 5P85SE launcher on a MAZ-543M 8x8 truck", [
        "very long 8x8 truck: eight large wheels in four axles, two pairs at the front, two at the back",
        "two separate small cabs at the front, one each side of the engine",
        "four long cylindrical missile launch tubes in a block lying flat along the back (travel position)",
        "a big support frame at the rear end for raising the tubes"]),
    "MIM-23 Hawk": gnd("MIM-23 Hawk M192 towed launcher with three missiles", [
        "three missiles side by side on a trainable launcher arm, raised about 30 degrees",
        "each missile: long white body, four long low wings along the rear half, four fins at the tail",
        "launcher on a two-wheeled carriage with four outrigger legs lowered to the ground"],
        kind="towed", length=5.0, width=4.0, pose=", three missiles loaded"),
    "MIM-104 Patriot": gnd("MIM-104 Patriot M901 launching station (semi-trailer)", [
        "a large box of four rectangular missile canisters (2x2), raised to about 38 degrees",
        "the box sits on a two-axle semi-trailer with outrigger jacks lowered",
        "a generator and electronics box at the front of the trailer"],
        kind="towed", pose=", canister box raised"),
    "NASAMS": gnd("NASAMS launcher (AMRAAM canister launcher on a trailer)", [
        "six box-shaped missile canisters in two rows of three, in one block, raised at an angle",
        "the block sits on a small towed trailer with four outrigger legs lowered"],
        kind="towed", pose=", canisters raised"),

    # ------------------------------------------------------------ short-range air defence and AAA
    "flak38": gnd("German 2 cm Flakvierling 38 quadruple anti-aircraft gun", [
        "four 20 mm barrels in a square 2 x 2 arrangement pointing upward about 30 degrees",
        "small curved gun shield, gunner's seat behind the guns",
        "a low cross-shaped ground platform with three or four outrigger legs, wheels removed"],
        kind="towed"),
    "flak36": gnd("German 8.8 cm Flak 36 anti-aircraft gun", [
        "long 88 mm barrel with a recuperator cylinder above it, raised about 30 degrees",
        "flat gun shield in front of the breech",
        "cross-shaped platform with four long outrigger legs on the ground, wheels removed"],
        kind="towed"),
    "flak41": gnd("German 8.8 cm Flak 41 anti-aircraft gun", [
        "very long 88 mm barrel with a muzzle brake, mounted low on a turntable",
        "large angular gun shield",
        "cross-shaped platform with four outrigger legs on the ground, wheels removed"],
        kind="towed"),
    "M45_Quadmount": gnd("US M45 Quadmount (four .50 cal machine guns) on its M17 trailer", [
        "four .50 cal machine guns, two on each side of a central armoured gunner's seat",
        "a curved armour shield in front of the gunner",
        "small two-wheeled trailer with levelling jacks"],
        kind="towed", length=3.0, width=2.1, height=1.9),
    "bofors40": gnd("Bofors 40 mm anti-aircraft gun (WWII)", [
        "single 40 mm barrel with a cone-shaped flash hider, raised about 30 degrees",
        "a clip-loading ammunition guide on top of the breech, gunners' seats on both sides",
        "four-wheeled carriage with outrigger legs lowered"],
        kind="towed"),
    "QF_37_AA": gnd("British QF 3.7-inch heavy anti-aircraft gun", [
        "long barrel with a large breech, raised about 40 degrees",
        "a fuze setter and loading tray beside the breech",
        "four-wheeled carriage with four outrigger legs on the ground"],
        kind="towed"),
    "ZU-23 Emplacement": gnd("ZU-23-2 twin 23 mm anti-aircraft gun", [
        "two long 23 mm barrels side by side on a light mount",
        "a gunner's seat on each side and an optical sight",
        "light two-wheeled carriage with the wheels raised and three levelling feet on the ground"],
        kind="towed"),
    "S-60_Type59_Artillery": gnd("S-60 57 mm anti-aircraft gun", [
        "single long 57 mm barrel with a slotted \"pepperbox\" muzzle brake",
        "small gun shield and an open loading platform",
        "four-wheeled carriage with outrigger legs lowered"],
        kind="towed"),
    "KS-19": gnd("KS-19 100 mm heavy anti-aircraft gun", [
        "very long 100 mm barrel with a muzzle brake",
        "gun shield, large breech and loading platform",
        "four-wheeled carriage with outrigger legs lowered"],
        kind="towed"),
    "ZSU-23-4 Shilka": gnd("ZSU-23-4 Shilka self-propelled anti-aircraft gun", [
        "low tracked hull with six road wheels per side and no return rollers",
        "large, flat, boxy turret with four 23 mm barrels in a square 2 x 2 arrangement at the front",
        "a round \"Gun Dish\" radar dish on a mast at the back of the turret"]),
    "ZSU_57_2": gnd("ZSU-57-2 self-propelled anti-aircraft gun", [
        "tracked hull with four large road wheels per side (a shortened T-54 chassis)",
        "a large open-topped box turret with two long 57 mm barrels side by side"]),
    "Strela-1 9P31": gnd("SA-9 Gaskin (9P31 Strela-1) launcher vehicle", [
        "BRDM-2 4x4 armoured car: boat-shaped hull, four big wheels",
        "a small turret on top with four box-shaped missile canisters, two on each side"]),
    "Strela-10M3": gnd("SA-13 Gopher (9A35 Strela-10M3) launcher vehicle", [
        "MT-LB tracked carrier: low, flat, boxy hull, six road wheels per side, no return rollers",
        "a turret with four box-shaped missile canisters, two on each side",
        "a small range-finding radar antenna between the two pairs of canisters"]),
    "Osa 9A33 ln": gnd("SA-8 Gecko (9K33 Osa) 9A33 launcher vehicle", [
        "6x6 amphibious wheeled vehicle: boat-shaped hull, three evenly spaced axles",
        "a big turret on top with a large search radar folded flat on the roof",
        "a round tracking radar dish at the front of the turret",
        "missiles on rails or in boxes on both sides of the turret"]),
    "2S6 Tunguska": gnd("2S6 Tunguska (SA-19 Grison) gun/missile vehicle", [
        "tracked chassis with six road wheels per side",
        "large turret with two 30 mm cannons on each side",
        "four missile tubes on each side of the turret next to the guns",
        "a search radar dish on the back of the turret roof, tracking radar dish on the front"]),
    "Tor 9A331": gnd("SA-15 Gauntlet (9K331 Tor) launcher vehicle", [
        "tracked chassis with six road wheels per side",
        "a very tall boxy turret holding eight vertical missile launch cells",
        "a large flat rectangular search radar on top of the turret",
        "a flat phased-array tracking radar panel on the front of the turret"]),
    "Vulcan": gnd("M163 Vulcan self-propelled anti-aircraft gun", [
        "M113-type boxy tracked hull with five road wheels per side",
        "a small open turret on top with a six-barrel 20 mm Gatling gun",
        "a small round range-only radar dish on the right side of the turret"]),
    "M48 Chaparral": gnd("M48 Chaparral missile launcher vehicle", [
        "tracked carrier with five road wheels per side, small cab at the front",
        "a launcher turret at the back carrying four Sidewinder-type missiles on rails, two each side"]),
    "Gepard": gnd("Flakpanzer Gepard self-propelled anti-aircraft gun", [
        "Leopard 1 tracked chassis with seven road wheels per side",
        "a large turret with one 35 mm cannon on each side of it",
        "a round search radar dish folded on the back of the turret roof",
        "a round tracking radar dish on the front of the turret"]),
    "Roland ADS": gnd("Roland surface-to-air missile vehicle (Marder chassis)", [
        "tracked chassis with six road wheels per side",
        "a turret with a missile container arm on each side",
        "a search radar dish on top of the turret, tracking radar on the front"]),
    "M1097 Avenger": gnd("M1097 Avenger air defence vehicle (HMMWV)", [
        "HMMWV: wide, low four-wheeled truck with a flat bonnet",
        "a turret in the rear bed with a pod of four Stinger missile tubes on each side",
        "a .50 cal machine gun under the right-hand pod"]),
    "M6 Linebacker": gnd("M6 Linebacker air defence vehicle (Bradley)", [
        "M2 Bradley: high boxy tracked hull with six road wheels per side",
        "turret with a 25 mm cannon",
        "a box of four Stinger missiles on the left side of the turret (where the Bradley has its TOW box)"]),
    "SA-18 Igla manpad": gnd("9K38 Igla (SA-18 Grouse) shoulder-launched missile", [
        "a long thin launch tube with a gripstock and trigger under the front half",
        "a ball-shaped battery unit under the tube in front of the grip",
        "a small optical sight on the left side"],
        kind="manpads", length=1.7, width=0.3, height=0.4),
    "Soldier stinger": gnd("FIM-92 Stinger shoulder-launched missile", [
        "a long thin launch tube with a gripstock and trigger under it",
        "a folded flat IFF antenna (looks like a small grid) on top of the gripstock",
        "an optical sight frame on the left side, battery unit under the grip"],
        kind="manpads", length=1.5, width=0.3, height=0.4),

    # ------------------------------------------------------------ radars
    "p-19 s-125 sr": gnd("P-19 \"Flat Face\" mobile search radar (on a ZiL-131 truck)", [
        "a 6x6 truck with a box-shaped cabin body on the back",
        "two large oval open-mesh dish antennas, one above the other, on a mast above the cabin"],
        kind="radar", length=7.0, width=2.5, height=8.0),
    "1L13 EWR": gnd("1L13 \"Box Spring\" (Nebo-SV) early-warning radar", [
        "a huge flat rectangular array made of many \"fishbone\" Yagi antennas in rows",
        "the array on a rotating support on top of a trailer"],
        kind="radar", length=14.0, width=10.0, height=12.0),
    "55G6 EWR": gnd("55G6 \"Tall Rack\" (Nebo) long-range early-warning radar", [
        "a very large, wide, rectangular array of long Yagi antennas in many rows",
        "mounted on a tall rotating lattice tower over a cabin"],
        kind="radar", length=32.0, width=8.0, height=18.0),
    "FuMG-401": gnd("FuMG 401 \"Freya\" German WWII early-warning radar", [
        "a tall rectangular \"mattress\" antenna made of a grid of dipoles, split into two parts",
        "the antenna on top of a small rotating cabin on a ground platform"],
        kind="radar", length=6.0, width=6.0, height=8.0),
    "FPS-117": gnd("AN/FPS-117 long-range air surveillance radar site", [
        "a large white spherical radome sitting on a square tower",
        "a small equipment building at the foot of the tower"],
        kind="radar", length=15.0, width=15.0, height=20.0),

    # ------------------------------------------------------------ armour
    "Pz_IV_H": gnd("Panzer IV Ausf. H German WWII medium tank", [
        "eight small road wheels per side in pairs (four bogies), four return rollers above",
        "thin armour skirt plates (Schuerzen) along the hull sides and around the turret",
        "boxy turret with a commander's cupola at the back",
        "long 75 mm gun with a double-baffle muzzle brake"], hull=5.9),
    "Pz_V_Panther_G": gnd("Panther Ausf. G German WWII medium tank", [
        "large overlapping (interleaved) road wheels, eight per side in two rows",
        "steeply sloped front plate and sloped hull sides, thin side skirts",
        "rounded gun mantlet, sloped turret sides",
        "long 75 mm gun with a double-baffle muzzle brake"], hull=6.9),
    "Tiger_I": gnd("Tiger I German WWII heavy tank", [
        "boxy hull with flat, vertical front and side plates",
        "large overlapping (interleaved) road wheels",
        "rounded horseshoe-shaped turret",
        "88 mm gun with a double-baffle muzzle brake"], hull=6.3),
    "Tiger_II_H": gnd("Tiger II (Koenigstiger) German WWII heavy tank, production turret", [
        "steeply sloped front plate like a Panther",
        "nine large overlapping road wheels per side",
        "flat-fronted turret with sloped sides and a long overhang at the back",
        "very long 88 mm gun with a double-baffle muzzle brake"], hull=7.4),
    "M4_Sherman": gnd("M4 Sherman US WWII medium tank (75 mm gun)", [
        "tall hull, three bogies per side each with two road wheels and a return roller on top",
        "rounded cast turret, rounded front hull",
        "short 75 mm gun"]),
    "Cromwell_IV": gnd("Cromwell IV British WWII cruiser tank", [
        "five large road wheels per side, NO return rollers",
        "boxy, squared-off turret with flat vertical sides",
        "flat vertical hull sides, short 75 mm gun"], hull=6.35),
    "M4A4_Sherman_FF": gnd("Sherman Firefly (M4A4 hull) British WWII tank with the 17-pounder", [
        "Sherman hull: three bogies per side, each with two road wheels and a return roller",
        "rounded cast turret with an armoured box (for the radio) on the back",
        "very long 17-pounder gun with a muzzle brake"], hull=6.0),
    "Churchill_VII": gnd("Churchill VII British WWII infantry tank", [
        "very long, low hull with the tracks running over the top of the hull sides",
        "many small road wheels hidden behind side panniers",
        "square welded turret, short 75 mm gun, square side escape doors in the hull"]),
    "T-34-85": gnd("T-34-85 Soviet WWII medium tank", [
        "five large road wheels per side, NO return rollers",
        "sloped front plate and sloped hull sides",
        "large cast turret set forward, 85 mm gun"], hull=6.0),
    "PT_76": gnd("PT-76 Soviet amphibious light tank", [
        "long, tall, boxy boat-shaped hull with a pointed bow and a folding trim vane on the front",
        "six road wheels per side, NO return rollers",
        "small, flattened conical turret placed well forward",
        "short 76 mm gun with a muzzle brake",
        "two water-jet outlets in the rear hull plate"], hull=6.9),
    "T-55": gnd("T-55 Soviet main battle tank", [
        "five large road wheels per side with a bigger gap between the first and second, NO return rollers",
        "low dome-shaped turret",
        "100 mm gun with a fume extractor near the muzzle",
        "fuel drums on the rear of the hull"], hull=6.45),
    "T62M": gnd("T-62M Soviet main battle tank", [
        "five large road wheels per side with big gaps between the rear three, NO return rollers",
        "dome-shaped turret with extra \"eyebrow\" armour blocks on the front",
        "115 mm smoothbore gun with a fume extractor about one third along the barrel",
        "rubber side skirts"], hull=6.6),
    "M-60": gnd("M60A3 Patton US main battle tank", [
        "six road wheels per side with three return rollers above",
        "large cast turret with a long pointed \"needle nose\" front",
        "commander's cupola with a machine gun on the turret roof",
        "105 mm gun with a fume extractor"], hull=6.95),
    "T-72B": gnd("T-72B Soviet main battle tank (1985) with Kontakt-1 explosive reactive armour", [
        "six large road wheels per side, three small return rollers mostly hidden by the side skirt",
        "drive sprocket at the rear, idler at the front",
        "low rounded cast turret covered with rows of Kontakt-1 ERA bricks in a V on the front and sides",
        "ERA bricks on the upper front hull; the hull sides are mostly plain rubber side skirts, NOT ERA",
        "125 mm gun with a thermal sleeve and fume extractor",
        "unditching log and two fuel drums across the rear of the hull"], hull=6.95),
    "T-72B3": gnd("T-72B3 Russian main battle tank (2010s)", [
        "six large road wheels per side, side skirts with reactive armour panels at the front",
        "turret covered in flat Kontakt-5 reactive armour panels",
        "a box-shaped Sosna-U gunner's sight on the turret roof right of the gun",
        "125 mm gun with a thermal sleeve and fume extractor"], hull=6.95),
    "T-80B": gnd("T-80B Soviet main battle tank (1980s)", [
        "six rubber-tyred road wheels per side with small return rollers above them",
        "drive sprocket at the rear, rubber side skirts",
        "low rounded cast turret with NO reactive armour",
        "125 mm gun with a thermal sleeve and fume extractor",
        "flat rear engine deck with a large gas-turbine exhaust grille at the very back"], hull=7.0),
    "T-80UD": gnd("T-80U Russian main battle tank (1990s)", [
        "six rubber-tyred road wheels per side with small return rollers above them",
        "turret front covered with big wedge-shaped Kontakt-5 reactive armour blocks",
        "Kontakt-5 panels on the front hull, side skirts with armour panels at the front",
        "125 mm gun with a thermal sleeve and fume extractor"], hull=7.0),
    "T-90": gnd("T-90A Russian main battle tank", [
        "six large road wheels per side, side skirts",
        "welded turret with Kontakt-5 reactive armour wedges on the front",
        "two square Shtora dazzler boxes (\"eyes\") on the turret front, one each side of the gun",
        "125 mm gun with a thermal sleeve and fume extractor"], hull=6.9),
    "Leopard1A3": gnd("Leopard 1A3 German main battle tank", [
        "seven road wheels per side with return rollers above, side skirts",
        "angular welded turret with flat, wedge-shaped spaced-armour faces (the A3 turret)",
        "105 mm L7 gun with a thermal sleeve and fume extractor",
        "crew hatches and periscopes on the turret roof, smoke dischargers on the turret sides"], hull=7.1),
    "leopard-2A4": gnd("Leopard 2A4 German main battle tank", [
        "seven road wheels per side with return rollers above, armoured side skirts",
        "large boxy turret with flat vertical front faces (NOT the 2A5 wedge)",
        "120 mm smoothbore gun with a thermal sleeve and fume extractor",
        "crew hatches and sights on top of the turret, smoke dischargers on the turret sides"], hull=7.7),
    "Leopard-2A5": gnd("Leopard 2A5 German main battle tank", [
        "seven road wheels per side with return rollers above, armoured side skirts",
        "big arrow-head (wedge) shaped add-on armour on the turret front, the main recognition feature",
        "120 mm smoothbore gun with a thermal sleeve and fume extractor"], hull=7.7, length=10.0),
    "M-1 Abrams": gnd("M1A2 Abrams US main battle tank", [
        "very flat, angular turret with flat sloped faces and a big storage bustle at the back",
        "seven road wheels per side behind thick armoured side skirts",
        "a box-shaped commander's thermal viewer on the turret roof",
        "120 mm smoothbore gun"], hull=7.9),
    "M1A2C_SEP_V3": gnd("M1A2C (SEP v3) Abrams US main battle tank", [
        "very flat, angular turret with a big storage bustle at the back",
        "a box-shaped Trophy active-protection unit on each side of the turret",
        "remote weapon station on the turret roof",
        "seven road wheels per side behind thick armoured side skirts, 120 mm gun"], hull=7.9),
    "Sd_Kfz_251": gnd("Sd.Kfz. 251 German WWII half-track", [
        "two wheels at the front, tracks with overlapping road wheels at the back",
        "angular armoured body with sloped sides, open top",
        "an MG 42 machine gun with a small shield above the driver's cab"]),
    "M2A1_halftrack": gnd("M2A1 US WWII half-track", [
        "two wheels at the front with a roller bumper, tracks with four road wheels at the back",
        "open-topped boxy armoured body with vertical sides",
        "a ring mount with a .50 cal machine gun above the cab"]),
    "BTR-60": gnd("BTR-60PB Soviet armoured personnel carrier", [
        "eight big wheels in four evenly spaced axles",
        "boat-shaped hull with a pointed nose",
        "a small cone-shaped turret with a 14.5 mm machine gun"]),
    "M-113": gnd("M113 US armoured personnel carrier", [
        "very boxy hull, five road wheels per side, NO return rollers",
        "sloped front plate with a trim vane, rear ramp",
        "a .50 cal machine gun on the commander's hatch"]),
    "BMP-2": gnd("BMP-2 Soviet infantry fighting vehicle", [
        "low hull with a sharp, ribbed, wedge-shaped front",
        "six road wheels per side with three return rollers",
        "small turret with a long thin 30 mm cannon and an anti-tank missile launcher on its roof",
        "rear troop doors"]),
    "M-2 Bradley": gnd("M2 Bradley US infantry fighting vehicle", [
        "high boxy hull with armoured side skirts, six road wheels per side",
        "turret with a 25 mm cannon",
        "a box-shaped twin TOW missile launcher folded on the left side of the turret"]),
    "BMP-3": gnd("BMP-3 Russian infantry fighting vehicle", [
        "low, wide hull with a sharp wedge-shaped front and a long flat front deck",
        "six road wheels per side with return rollers above them",
        "turret in the middle with a 100 mm gun-launcher and a 30 mm cannon alongside it",
        "a small machine-gun mount on each front corner of the hull",
        "troop doors in the rear hull with roof hatches above them"]),

    # ------------------------------------------------------------ artillery
    "MLRS": gnd("M270 MLRS multiple rocket launcher", [
        "tracked chassis with six road wheels per side, armoured cab at the front",
        "a large box launcher on the back holding two pods of six rocket tubes"],
        length=7.0, width=3.0, height=2.6),
    "Grad-URAL": gnd("BM-21 Grad rocket launcher on a Ural-375 truck", [
        "6x6 Ural truck with a long bonnet and a cab",
        "a block of 40 rocket tubes (four rows of ten) on the back, pointing forward over the cab"],
        length=7.35, width=2.4, height=3.1),
    "SAU Msta": gnd("2S19 Msta-S self-propelled howitzer", [
        "tracked chassis with six road wheels per side",
        "very large, tall boxy turret",
        "long 152 mm gun with a fume extractor and a muzzle brake"],
        hull=6.7, length=11.9, width=3.6, height=3.0),
    "SAU Gvozdika": gnd("2S1 Gvozdika self-propelled howitzer", [
        "low amphibious tracked chassis with seven road wheels per side",
        "turret at the back of the hull",
        "122 mm gun with a double-baffle muzzle brake"],
        hull=7.3, length=7.3, width=2.85, height=2.7),
    "2B11 mortar": gnd("2B11 120 mm mortar", [
        "a mortar tube on a round base plate, held up by a bipod with a sight",
        "no wheels or carriage"],
        kind="towed", length=1.9, width=1.0, height=1.4),
    "M2A1-105": gnd("M2A1 (M101) 105 mm towed howitzer", [
        "two wheels, split trail with two long legs spread on the ground",
        "small gun shield, barrel WITHOUT a muzzle brake"],
        kind="towed", length=6.0, width=2.2, height=1.7),
    "LeFH_18-40-105": gnd("German leFH 18/40 105 mm towed howitzer", [
        "two wheels, split trail with two long legs spread on the ground",
        "gun shield, barrel with a double-baffle muzzle brake"],
        kind="towed", length=6.1, width=2.0, height=1.9),
    "M-109": gnd("M109A6 Paladin self-propelled howitzer", [
        "tracked chassis with seven road wheels per side",
        "large boxy turret set to the back of the hull",
        "long 155 mm gun with a fume extractor and a muzzle brake, a travel lock on the front of the hull"],
        hull=6.2, length=9.7, width=3.9, height=3.2),

    # ------------------------------------------------------------ ships
    "Schnellboot_type_S130": ship("German WWII S-boat (Schnellboot, S-100 class such as S-130)", [
        "long, low, narrow fast attack boat with a raised forecastle",
        "two torpedo tubes built into the forecastle, one each side of the bow",
        "small low armoured bridge amidships, 20 mm and 37 mm guns on the deck"]),
    "Uboat_VIIC": ship("German WWII U-boat Type VIIC, surfaced", [
        "long, low cigar-shaped hull with bulged saddle tanks on the sides",
        "conning tower amidships with an anti-aircraft gun platform behind it",
        "most of the hull is just above the waterline"]),
    "LST_Mk2": ship("LST Mk.II tank landing ship (WWII)", [
        "long box-shaped hull with bow doors at the front",
        "flat open deck along most of the length",
        "the bridge and superstructure at the stern, 40 mm and 20 mm guns"]),
    "USS_Samuel_Chase": ship("USS Samuel Chase, WWII attack transport", [
        "merchant-ship hull with a central superstructure and one funnel",
        "many landing craft hanging on davits along both sides",
        "cargo masts and booms fore and aft"]),
    "Dry-cargo ship-1": ship("general cargo ship (bulk carrier), 130 m", [
        "superstructure and bridge at the stern",
        "several cargo hatches along the deck with cranes between them"]),
    "Dry-cargo ship-2": ship("general cargo ship, 110 m", [
        "superstructure and bridge at the stern",
        "cargo hatches along the deck with derrick masts between them"]),
    "ALBATROS": ship("Grisha-class corvette (Soviet)", [
        "small corvette with a raised forecastle",
        "a twin 57 mm gun turret on the stern",
        "an SA-N-4 missile launcher housed in a round bin on the foredeck",
        "anti-submarine rocket launchers forward of the bridge, radar mast"]),
    "MOLNIYA": ship("Tarantul-class (Molniya) missile corvette (Soviet)", [
        "small, low missile boat",
        "a 76 mm gun on the bow",
        "four large missile launch tubes, two on each side amidships, angled forward",
        "two 30 mm Gatling guns on the stern"]),
    "REZKY": ship("Krivak-class frigate (Soviet)", [
        "a big box-shaped four-tube missile launcher on the bow",
        "two round SA-N-4 launcher bins",
        "two single 100 mm or twin 76 mm gun turrets on the stern, one funnel amidships"]),
    "NEUSTRASH": ship("Neustrashimy-class frigate (Russian)", [
        "a 100 mm gun on the bow, vertical launch cells on the foredeck",
        "large central superstructure with a tall mast and a raked funnel",
        "a helicopter deck and hangar at the stern"]),
    "MOSCOW": ship("Slava-class missile cruiser \"Moskva\" (Russian)", [
        "sixteen huge missile tubes in pairs along both sides of the forward superstructure, angled up:",
        "  the main recognition feature",
        "a twin 130 mm gun turret on the bow",
        "large radar arrays on the masts, vertical missile launchers aft, helicopter pad at the stern"]),
    "leander-gun-achilles": ship("Leander-class frigate, gun version (British)", [
        "a twin 4.5-inch gun turret on the bow",
        "one funnel amidships, a tall lattice mast with a large radar",
        "a Sea Cat missile launcher aft, a small helicopter deck at the stern"]),
    "PERRY": ship("Oliver Hazard Perry-class frigate (US Navy)", [
        "long, low, box-shaped superstructure",
        "a single-arm missile launcher on the foredeck",
        "a 76 mm gun on top of the superstructure amidships, Phalanx gun aft",
        "two hangars and a flight deck at the stern, one funnel"]),
    "TICONDEROG": ship("Ticonderoga-class guided missile cruiser (US Navy)", [
        "two large, flat-sided superstructure blocks, forward and aft, each with octagonal SPY-1 radar faces",
        "one 5-inch gun on the bow and one 5-inch gun on the stern",
        "a vertical missile launch grid on the forward deck and another one aft",
        "two lattice masts and exhaust stacks between the superstructure blocks",
        "a helicopter flight deck and hangar near the stern, Phalanx guns on the superstructure"]),
    "USS_Arleigh_Burke_IIa": ship("Arleigh Burke-class Flight IIA guided missile destroyer (US Navy)", [
        "wide, flared hull with a raked bow",
        "ONE large superstructure block forward with four octagonal SPY-1 radar faces",
        "one 5-inch gun on the bow, a vertical missile launch grid in front of the bridge",
        "one tilted-back mast, two exhaust stacks",
        "a second vertical launch grid aft, then a double helicopter hangar and a flight deck at the stern"]),
}


if __name__ == "__main__":
    clean_all()
    threatdb.DRAWINGS = threatdb.load_drawings()
    write_prompts()
