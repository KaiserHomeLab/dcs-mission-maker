"""Builds a .miz file from a mission request using pydcs.

Public API: MissionRequest, generate_full, preview and the choice lists."""
import datetime
import os
import re
import tempfile
import zipfile

from .builder import Builder
from .common import default_callsign
from .preview import map_points, preview
from .request import DIFFICULTIES, MISSION_TYPES, TIMES, WEATHER, WINDS, MissionError, MissionRequest

__all__ = ["DIFFICULTIES", "MISSION_TYPES", "TIMES", "WEATHER", "WINDS", "MissionError", "MissionRequest",
           "default_callsign", "generate_full", "map_points", "preview"]


def generate_full(req: MissionRequest) -> dict:
    """Build a mission: the .miz bytes, filename, briefing text, warnings and the Briefing Room data."""
    with tempfile.TemporaryDirectory() as tmp:
        b = Builder(req, tmp)
        m = b.build()
        safe = re.sub(r"[^\w\-]+", "_", b.title).strip("_")[:60]
        filename = f"{safe}_{datetime.datetime.now():%Y%m%d_%H%M%S}.miz"
        path = os.path.join(tmp, filename)
        m.save(path)
        with zipfile.ZipFile(path, "a", zipfile.ZIP_DEFLATED) as z:
            # The Mission Editor stores the map name in its own "theatre" file too; pydcs
            # doesn't, and some loaders (dedicated servers, mission tools) look for it.
            z.writestr("theatre", m.terrain.miz_theatre_name)
            for name, text in b.dtc_files.items():
                z.writestr(f"DTC/{name}.dtc", text)
        with open(path, "rb") as fh:
            data = fh.read()
    return {"data": data, "filename": filename, "briefing": b.briefing_text,
            "warnings": b.warnings, "brief": b.export_brief(filename)}
