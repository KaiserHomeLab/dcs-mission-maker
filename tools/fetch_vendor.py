"""Downloads the pinned third-party files the app needs into one folder (default: vendor/).

Used by the Docker build and by windows/setup.bat, so both get the same files.
Every download is checked against its SHA-256; a mismatch stops with an error.

  * Mission scripts: MOOSE (GPL-3.0), MIST (GPL-3.0), Skynet IADS (Apache-2.0),
    Hound ELINT (GPL-3.0), EWRS (MIT).
  * beacons/: airfield TACAN/ILS frequencies from DCS Retribution (LGPL-3.0).
  * fonts/: DejaVu Sans and Sans Mono 2.37 for the kneeboards (Bitstream Vera licence).

    python tools/fetch_vendor.py [out_dir]
"""
import hashlib
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

RETRIBUTION = "https://raw.githubusercontent.com/dcs-retribution/dcs-retribution/49e8067f691301eb796bcc9d70c26c92ea190a97"

SCRIPTS = {
    "Moose_.lua": (
        "https://raw.githubusercontent.com/FlightControl-Master/MOOSE_INCLUDE/"
        "37c2001e63f715d2e6be14b49ddc3b84656a3f4e/Moose_Include_Static/Moose_.lua",
        "5d307f804d656ace0566123383b43cc70e156df783ab339a17858a391d30ace7"),
    "mist.lua": (
        "https://raw.githubusercontent.com/mrSkortch/MissionScriptingTools/"
        "da53d53087677745443d5df9a7225eaff98438dc/mist_4_5_126.lua",
        "85e78e6cb5d2191b4148241e1a77c4884049b51295508d3d38b20793a0968c39"),
    "skynet-iads-compiled.lua": (
        "https://raw.githubusercontent.com/walder/Skynet-IADS/"
        "62aab46901eed16dbfe17fb482ba05f74d056355/demo-missions/skynet-iads-compiled.lua",
        "6b95b407f99ddf3933addcf3cfda2288d53519af652ffb90b779c26ba7608ba7"),
    "HoundElint.lua": (
        "https://github.com/uriba107/DCS-Hound/releases/download/v0.5.2/HoundElint.lua",
        "b7a863374bbc83368a1c02bfc618a8acdf6157331df51e704173efbe7ae3f0ca"),
    "EWRS.lua": (
        "https://raw.githubusercontent.com/Bob7heBuilder/EWRS/6e67a8844e40e9ce8d4b30a0f989a769a6b2be61/EWRS.lua",
        "48380672cb916b6d5e747b398324d4131de9fd06933060f370a3c0df6c266ccb"),
}

BEACONS = {
    "caucasus": "b69ba4138d4acf41867e950af4c83c947d350c54a469c03abc8b00d04afbec49",
    "persiangulf": "6378c724a3497a67f6b889a3aa617d62d3eeb82da6267d413cc311cdb7ee7987",
    "syria": "97bbccf127429d761e49c98209d55ab11259f72cde4646d9888c16cc8969e71e",
    "nevada": "7beab9fa92ff358890c5c1e04133e9a838b661a59841aa30bf3dbc8b05d2abba",
    "marianaislands": "2e11b1558c0d9d608f6c89d7e8d5b154ff7c647e9c6245941c1e6a7a183a29be",
    "sinai": "f03fb2a2f7fdbfe621c8c05e5c0041c7220814048e14f05353935047e56282b9",
    "kola": "b639b1cb90f3473158b1044a39cc085c4ce150efced7c95ba7b7f59a582d746f",
    "falklands": "f009e9e6ce6d043281a266d873d662932941efd4b8b8fd60857278d365883d42",
    "germanycoldwar": "0de8320aab24db4ec6ff7b10f1e28866dfe9500aa57efb9715fa11cff430b4ad",
}

FONTS_ZIP = (
    "https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.zip",
    "7576310b219e04159d35ff61dd4a4ec4cdba4f35c00e002a136f00e96a908b0a")
FONTS = ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSansMono.ttf", "DejaVuSansMono-Bold.ttf"]


def fetch(url, sha256):
    with urllib.request.urlopen(url, timeout=120) as r:
        data = r.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise SystemExit(f"Checksum mismatch for {url}\n  expected {sha256}\n  got      {got}")
    return data


def main(out_dir):
    out = Path(out_dir)
    (out / "beacons").mkdir(parents=True, exist_ok=True)
    (out / "fonts").mkdir(exist_ok=True)
    for name, (url, sha) in SCRIPTS.items():
        print("script ", name)
        (out / name).write_bytes(fetch(url, sha))
    for name, sha in BEACONS.items():
        print("beacons", name)
        (out / "beacons" / f"{name}.json").write_bytes(fetch(f"{RETRIBUTION}/resources/dcs/beacons/{name}.json", sha))
    print("fonts   DejaVu 2.37")
    with zipfile.ZipFile(io.BytesIO(fetch(*FONTS_ZIP))) as z:
        root = "dejavu-fonts-ttf-2.37/"
        for name in FONTS:
            (out / "fonts" / name).write_bytes(z.read(root + "ttf/" + name))
        (out / "fonts" / "LICENSE").write_bytes(z.read(root + "LICENSE"))
    print(f"done -> {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "vendor")
