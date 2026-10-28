"""Callsigns and radio presets.

DCS numbers a western callsign by its position in the country's generic list
(Enfield, Springfield, ...) followed by the aircraft's own list (Viper, Venom,
...), counting from 1. Under Combined Joint Task Forces every country's
aircraft-specific names are allowed.
"""
from dcs import countries

GENERIC = list(countries.CombinedJointTaskForcesBlue.callsign["Air"])
AWACS = list(countries.CombinedJointTaskForcesBlue.callsign["AWACS"])
TANKERS = list(countries.CombinedJointTaskForcesBlue.callsign["Tankers"])


def callsign_options(cls) -> list[str]:
    own = []
    for names in (getattr(cls, "callnames", None) or {}).values():
        own += [n for n in names if n not in own and n not in GENERIC]
    return GENERIC + own


def apply_callsign(group, name: str, number: int):
    """Name every unit "<Name> <n>-<i>" and set the DCS callsign to match."""
    options = callsign_options(group.units[0].unit_type)
    index = options.index(name) + 1
    for i, u in enumerate(group.units, start=1):
        u.name = f"{name} {number}-{i}"
        u.callsign_dict = {1: index, 2: number, 3: i, "name": f"{name}{number}{i}"}
        props = u.addpropaircraft or {}
        # Link 16 jets (F-16C, F/A-18C, ...) show these on the datalink pages.
        if "VoiceCallsignLabel" in props:
            u.set_property("VoiceCallsignLabel", (name[0] + name[-1]).upper())
            u.set_property("VoiceCallsignNumber", f"{number}{i}")
        for key in ("STN_L16", "SADL_TN"):
            if key in props:
                _stn[0] += 1
                u.set_property(key, f"{_stn[0]:05o}")


_stn = [0o100]  # unique Link 16 track numbers within a process run


def reset_stn():
    _stn[0] = 0o100


def apply_support_callsign(group, kind: str, name: str, number: int = 1):
    table = AWACS if kind == "awacs" else TANKERS
    index = table.index(name) + 1
    for i, u in enumerate(group.units, start=1):
        u.name = f"{name} {number}-{i}"
        u.callsign_dict = {1: index, 2: number, 3: i, "name": f"{name}{number}{i}"}


# --------------------------------------------------------------------- radios
UHF = (225.0, 400.0)
VHF_AM = (116.0, 156.0)


def radio_band(cls, radio_id):
    """'uhf', 'vhf' or None, judged from the module's default presets."""
    radios = getattr(cls, "panel_radio", None) or {}
    chans = list(radios.get(radio_id, {}).get("channels", {}).values())
    if not chans:
        return None
    for band, (lo, hi) in (("uhf", UHF), ("vhf", VHF_AM)):
        if all(lo <= float(c) <= hi for c in chans):
            return band
    return None


class CommPlan:
    """One shared plan; each flight gets its own intra-flight frequency."""

    PACKAGE = {"uhf": 255.0, "vhf": 134.0}

    def __init__(self, home_airport, has_awacs, has_boom, has_drogue, carrier_freq=None,
                 jtac_freq=None):
        atc = home_airport.atc_radio
        self.atc = {"uhf": atc.uhf_hz / 1e6 if atc else None,
                    "vhf": atc.vhf_high_hz / 1e6 if atc else None}
        self.awacs = 251.0 if has_awacs else None
        self.boom = 252.0 if has_boom else None
        self.drogue = 253.0 if has_drogue else None
        self.carrier = carrier_freq
        self.jtac = jtac_freq

    @staticmethod
    def flight_freq(index, band):
        return (310.0 + index) if band == "uhf" else (140.0 + index * 0.5)

    def channels(self, index, band):
        """[(channel, MHz, label)] for one radio."""
        plan = [(self.flight_freq(index, band), "FLIGHT"), (self.PACKAGE[band], "PKG")]
        if band == "uhf":
            plan += [(self.awacs, "AWACS"), (self.boom, "TEXACO"), (self.drogue, "ARCO"),
                     (self.carrier, "CVN"), (self.jtac, "JTAC")]
        plan.append((self.atc[band], "TOWER"))
        return [(n, f, label) for n, (f, label) in enumerate(
            [p for p in plan if p[0]], start=1)]

    def apply(self, group, index):
        """Sets presets on every client unit. Returns {radio_id: channels}."""
        cls = group.units[0].unit_type
        applied = {}
        for radio_id in (1, 2):
            band = radio_band(cls, radio_id)
            if band is None:
                continue
            chans = self.channels(index, band)
            for u in group.units:
                if u.radio is None:
                    continue
                for n, freq, _ in chans:
                    if n <= u.num_radio_channels(radio_id):
                        u.set_radio_channel_preset(radio_id, n, freq)
            applied[radio_id] = chans
        primary = applied.get(1) or applied.get(2)
        if primary:
            # DCS copies the group frequency into channel 1 of the first
            # compatible radio, which the plan already uses for FLIGHT.
            group.frequency = primary[0][1]
            group.radio_set = True
        return applied

    @staticmethod
    def describe(applied):
        parts = []
        for radio_id, chans in applied.items():
            parts.append(f"R{radio_id}: " + ", ".join(
                f"Ch{n} {label} {freq:.3f}" for n, freq, label in chans))
        return "; ".join(parts)
