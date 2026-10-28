"""Where the app keeps its files.

The Docker image sets each of these through the environment. Run without Docker
(e.g. on the Windows PC that hosts the DCS server) they default to folders in the
project: missions/, vendor/ (tools/fetch_vendor.py), drawings/ and scripts/.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def folder(env_name, default):
    return Path(os.environ.get(env_name) or ROOT / default)


def output_dir():
    return folder("OUTPUT_DIR", "missions")


def vendor_dir():
    return folder("VENDOR_DIR", "vendor")
