"""Where the app keeps its files.

Three ways to run it:
  * Docker: each folder comes from the environment (see Dockerfile).
  * From source (python -m app, windows\\start.bat): folders in the project.
  * The Windows app (PyInstaller build): the app's own files sit next to the .exe and are
    read-only. Your data (missions, settings, your scripts, logs) goes to the data folder,
    C:\\ProgramData\\DCS Mission Maker by default (DATA_DIR), so it survives upgrades.
"""
import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
# The app's own files: app/templates, app/static, app/data, vendor/, dcs-hook/.
ROOT = Path(getattr(sys, "_MEIPASS", "")) if FROZEN else Path(__file__).resolve().parent.parent


def data_dir():
    if os.environ.get("DATA_DIR"):
        return Path(os.environ["DATA_DIR"])
    if not FROZEN:
        return ROOT
    if sys.platform == "win32":
        return Path(os.environ.get("PROGRAMDATA") or r"C:\ProgramData") / "DCS Mission Maker"
    return Path.home() / ".local" / "share" / "dcs-mission-maker"


def folder(env_name, default):
    return Path(os.environ.get(env_name) or default)


def output_dir():
    """Missions, Briefing Room data, setups, sign-ups and settings.json."""
    return folder("OUTPUT_DIR", data_dir() / "missions")


def scripts_dir():
    """Your own .lua scripts, offered in the builder."""
    return folder("CUSTOM_SCRIPTS_DIR", data_dir() / "scripts")


def logs_dir():
    return data_dir() / "logs"


def vendor_dir():
    return folder("VENDOR_DIR", ROOT / "vendor")
