"""Builds app/data/liveries.json: the DCS livery ids squadrons use, per aircraft type.

Source: DCS Retribution (LGPL-3.0), resources/squadrons/*/*.yaml (each squadron names
its stock DCS livery) and resources/units/aircraft/<type id>.yaml (display names, to map
a squadron's aircraft to its DCS type id). Pinned to the same commit as the beacon data.

    curl -fsSL -o r.tar.gz https://codeload.github.com/dcs-retribution/dcs-retribution/tar.gz/$COMMIT
    sha256sum r.tar.gz   # must match SHA256 below
    tar xzf r.tar.gz
    python tools/build_liveries.py dcs-retribution-$COMMIT/resources app/data/liveries.json
"""
import json
import pathlib
import sys

COMMIT = "49e8067f691301eb796bcc9d70c26c92ea190a97"
SHA256 = "3432667250319f76b7b4c7a4a2473114d416597169c3231d272252ea739a3aba"


def _value(raw):
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v.strip()


def top_level(path):
    """The flat `key: value` lines of a YAML file (enough for squadron files)."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line[0].isspace() and ":" in line and not line.startswith(("#", "-")):
            key, _, val = line.partition(":")
            out[key.strip()] = _value(val)
    return out


def variant_names(path):
    """Display names under `variants:` in a Retribution aircraft file."""
    names, inside = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("variants:"):
            inside = True
        elif inside and line.startswith("  ") and not line.startswith("    "):
            names.append(_value(line.strip().split(":", 1)[0] if not line.strip().startswith(("'", '"'))
                                else line.strip().rsplit(":", 1)[0]))
        elif inside and line and not line[0].isspace():
            break
    return names


def main(resources, out_path):
    resources = pathlib.Path(resources)
    type_of = {}
    for f in sorted((resources / "units" / "aircraft").glob("*.yaml")):
        for name in variant_names(f):
            type_of.setdefault(name, f.stem)
    liveries = {}
    for f in sorted((resources / "squadrons").rglob("*.yaml")):
        sq = top_level(f)
        type_id, livery = type_of.get(sq.get("aircraft", "")), sq.get("livery", "")
        if not type_id or not livery:
            continue
        label = " ".join(x for x in (sq.get("name"), sq.get("nickname")) if x)
        entry = liveries.setdefault(type_id, {}).setdefault(livery, {"id": livery, "squadrons": [], "countries": []})
        if label and label not in entry["squadrons"]:
            entry["squadrons"].append(label)
        if sq.get("country") and sq["country"] not in entry["countries"]:
            entry["countries"].append(sq["country"])
    data = {t: sorted(v.values(), key=lambda e: (e["squadrons"][0] if e["squadrons"] else e["id"]).lower())
            for t, v in sorted(liveries.items())}
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(out_path).write_text(json.dumps({"source": f"DCS Retribution {COMMIT} (LGPL-3.0)",
                                                  "liveries": data}, indent=1) + "\n", encoding="utf-8")
    print(f"{sum(len(v) for v in data.values())} liveries for {len(data)} aircraft -> {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
