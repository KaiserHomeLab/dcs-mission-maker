"""Airfield navigation data: TACAN, ILS, tower frequencies, runway in use.

pydcs only knows beacon ids, so frequencies come from DCS Retribution's beacon
database (LGPL-3.0, extracted from DCS), downloaded at image build time.
"""
import functools
import json

from . import paths

BEACON_DIR = paths.vendor_dir() / "beacons"
TACAN_TYPES = {4, 5}           # TACAN, VORTAC
ILS_LOCALIZER = 16640


@functools.cache
def _beacons(file_key):
    path = BEACON_DIR / f"{file_key}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _tacan(beacons, airport):
    for b in airport.beacons or []:
        d = beacons.get(b.id)
        if d and d["beacon_type"] in TACAN_TYPES and d.get("channel"):
            return f"{d['channel']}X {d['callsign']}"
    return None


def runway_in_use(airport, wind_from, calm):
    """(approach name, heading, approach) landing into the wind."""
    best = None
    for rw in airport.runways or []:
        for appr in (rw.main, rw.opposite):
            if calm:
                return appr
            diff = abs((appr.heading - wind_from + 180) % 360 - 180)
            if best is None or diff < best[0]:
                best = (diff, appr)
    return best[1] if best else None


def _ils(beacons, approach):
    for b in approach.beacons or []:
        d = beacons.get(b.id)
        if d and d["beacon_type"] == ILS_LOCALIZER:
            return f"{d['hertz'] / 1e6:.2f} {d['callsign']}"
    return None


def airfield_card(file_key, airport, wind_from, calm):
    """Short human description for briefings and kneeboards."""
    beacons = _beacons(file_key) if file_key else {}
    parts = [airport.name]
    tacan = _tacan(beacons, airport)
    if tacan:
        parts.append(f"TACAN {tacan}")
    atc = airport.atc_radio
    if atc:
        freqs = [f"{hz / 1e6:.3f}" for hz in (atc.uhf_hz, atc.vhf_high_hz) if hz]
        if freqs:
            parts.append("Tower " + " / ".join(freqs))
    appr = runway_in_use(airport, wind_from, calm)
    if appr:
        ils = _ils(beacons, appr)
        parts.append(f"RWY {appr.name}" + (f" ILS {ils}" if ils else ""))
    return " · ".join(parts)
