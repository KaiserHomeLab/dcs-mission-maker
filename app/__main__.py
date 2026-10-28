"""Runs the app without Docker, e.g. on the Windows PC that hosts the DCS server:

    python -m app

Reads settings from .env in the project folder (the same file Docker Compose uses;
variables already set in the environment win), then serves on HOST:PORT
(default 0.0.0.0:8080) with waitress, which works on Windows and Linux.
"""
import os
import sys

from . import paths


def load_env(path):
    """KEY=VALUE lines; # comments and blank lines are skipped, surrounding quotes removed."""
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


def main():
    load_env(paths.ROOT / ".env")
    if not (paths.vendor_dir() / "beacons").is_dir():
        sys.exit("The mission scripts and data aren't downloaded yet. Run windows\\setup.bat "
                 "(or: python tools/fetch_vendor.py) first.")
    from waitress import serve

    from .server import app  # after load_env: modules read their settings on import

    host, port = os.environ.get("HOST", "0.0.0.0"), int(os.environ.get("PORT", "8080"))
    print(f"DCS Mission Maker on http://localhost:{port}  (missions in {paths.output_dir()})", flush=True)
    serve(app, host=host, port=port, threads=int(os.environ.get("THREADS", "6")))


if __name__ == "__main__":
    main()
