# PyInstaller recipe for the Windows app. Run windows\build.bat, or after setup:
#     pyinstaller --noconfirm windows\dcs-mission-maker.spec
# Output: dist\DCS Mission Maker\ (the .exe plus an _internal folder with everything it needs).
# vendor\ and drawings\ must be downloaded first (tools\fetch_vendor.py, tools\fetch_drawings.py).
import pathlib
import sys

from PyInstaller.utils.hooks import collect_all

ROOT = pathlib.Path(SPECPATH).parent  # noqa: F821 - SPECPATH is set by PyInstaller
sys.path.insert(0, str(ROOT))
from app.icon import save_ico  # noqa: E402

if not (ROOT / "vendor" / "beacons").is_dir():
    raise SystemExit("vendor\\ is missing: run python tools\\fetch_vendor.py first.")

# pydcs loads terrain and unit data files and imports some modules by name; pypdfium2 ships
# the PDFium library as a data file.
datas, binaries, hiddenimports = collect_all("dcs")
for package in ("pypdfium2", "pypdfium2_raw"):
    d, b, h = collect_all(package)
    datas, binaries, hiddenimports = datas + d, binaries + b, hiddenimports + h
datas += [
    (str(ROOT / "app" / "templates"), "app/templates"),
    (str(ROOT / "app" / "static"), "app/static"),
    (str(ROOT / "app" / "data"), "app/data"),
    (str(ROOT / "dcs-hook"), "dcs-hook"),
    (str(ROOT / "vendor"), "vendor"),
    (str(ROOT / "THIRD_PARTY.md"), "."),
]
if (ROOT / "drawings").is_dir():  # optional: sheets fall back to generated drawings
    datas.append((str(ROOT / "drawings"), "drawings"))
hiddenimports += ["waitress"]
if sys.platform == "win32":
    hiddenimports += ["pystray._win32"]

a = Analysis(  # noqa: F821
    [str(ROOT / "windows" / "launcher.py")],
    pathex=[str(ROOT)],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "gunicorn", "tests", "pytest"],
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DCS Mission Maker",
    console=False,  # a tray app: no console window (logs go to the data folder)
    icon=save_ico(ROOT / "build" / "icon.ico"),
)
coll = COLLECT(exe, a.binaries, a.datas, name="DCS Mission Maker")  # noqa: F821
