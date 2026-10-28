"""Curated map data.

pydcs has no land/sea mask, so every place we spawn something is expressed as
an anchor airport plus a bearing/distance that is known to land on the right
kind of terrain (inland for ground targets, open water for ships/carriers).
"""
from dataclasses import dataclass, field

from dcs import terrain


@dataclass(frozen=True)
class Offset:
    anchor: str          # airport name
    bearing: float       # degrees true
    distance_km: float


@dataclass(frozen=True)
class RedBase:
    name: str
    # Direction/distance from the airfield where ground targets are placed.
    inland: Offset
    # How far beyond the airfield secondary objectives may go (islands: keep small).
    spread_km: float = 15
    fan_deg: float = 40          # secondaries go inland bearing +/- this


@dataclass
class Theater:
    key: str
    label: str
    terrain_cls: type
    blue_bases: list[str]
    red_bases: list[RedBase]
    red_sea: Offset | None = None      # enemy shipping
    blue_carrier: Offset | None = None  # friendly carrier group
    summer_temp: int = 25
    winter_temp: int = 5
    notes: str = ""
    default_blue: str = field(default="")
    default_red: str = field(default="")
    beacons: str = ""        # beacon database file (navdata), "" = none

    def __post_init__(self):
        self.default_blue = self.default_blue or self.blue_bases[0]
        self.default_red = self.default_red or self.red_bases[0].name

    def red_base(self, name: str) -> RedBase:
        for rb in self.red_bases:
            if rb.name == name:
                return rb
        raise KeyError(name)


def _inland(name, bearing=0, km=6, spread=15, fan=40):
    return RedBase(name, Offset(name, bearing, km), spread, fan)


THEATERS: dict[str, Theater] = {t.key: t for t in [
    Theater(
        key="caucasus", label="Caucasus", terrain_cls=terrain.Caucasus, beacons="caucasus",
        blue_bases=["Senaki-Kolkhi", "Kutaisi", "Kobuleti", "Batumi",
                    "Tbilisi-Lochini", "Vaziani"],
        red_bases=[_inland("Sukhumi-Babushara", 45, 8), _inland("Gudauta", 45, 6),
                   _inland("Nalchik"), _inland("Mozdok"),
                   _inland("Mineralnye Vody"), _inland("Maykop-Khanskaya")],
        red_sea=Offset("Gudauta", 225, 35),
        blue_carrier=Offset("Batumi", 270, 70),
        summer_temp=24, winter_temp=2,
    ),
    Theater(
        key="persiangulf", label="Persian Gulf", terrain_cls=terrain.PersianGulf,
        beacons="persiangulf",
        blue_bases=["Al Dhafra AFB", "Al Minhad AFB", "Al Maktoum Intl",
                    "Sharjah Intl", "Fujairah Intl", "Khasab"],
        red_bases=[_inland("Bandar Abbas Intl", 0, 8), _inland("Havadarya", 0, 8),
                   _inland("Bandar Lengeh", 0, 8), _inland("Lar"),
                   _inland("Jiroft"), _inland("Kerman"), _inland("Shiraz Intl")],
        red_sea=Offset("Bandar Lengeh", 180, 30),
        blue_carrier=Offset("Fujairah Intl", 90, 60),
        summer_temp=38, winter_temp=20,
    ),
    Theater(
        key="syria", label="Syria", terrain_cls=terrain.Syria, beacons="syria",
        blue_bases=["Incirlik", "Ramat David", "Akrotiri",
                    "King Hussein Air College", "Muwaffaq Salti"],
        red_bases=[_inland("Bassel Al-Assad", 90, 8), _inland("Hama"),
                   _inland("Shayrat"), _inland("Tiyas"), _inland("Palmyra"),
                   _inland("Al-Dumayr"), _inland("Aleppo")],
        red_sea=Offset("Bassel Al-Assad", 270, 35),
        blue_carrier=Offset("Akrotiri", 135, 60),
        default_blue="Incirlik", default_red="Hama",
        summer_temp=32, winter_temp=8,
    ),
    Theater(
        key="nevada", label="Nevada (NTTR)", terrain_cls=terrain.Nevada, beacons="nevada",
        blue_bases=["Nellis", "Creech", "Groom Lake"],
        red_bases=[_inland("Tonopah Test Range"), _inland("Pahute Mesa"),
                   _inland("Tonopah"), _inland("Beatty"), _inland("Mina")],
        notes="Landlocked: no anti-ship missions or carrier ops.",
        summer_temp=35, winter_temp=8,
    ),
    Theater(
        key="marianas", label="Marianas", terrain_cls=terrain.MarianaIslands,
        beacons="marianaislands",
        blue_bases=["Andersen AFB", "Antonio B. Won Pat Intl"],
        red_bases=[_inland("Saipan Intl", 0, 4, spread=7, fan=15),
                   _inland("Tinian Intl", 20, 3, spread=6, fan=12)],
        red_sea=Offset("Saipan Intl", 270, 30),
        blue_carrier=Offset("Andersen AFB", 270, 50),
        summer_temp=30, winter_temp=27,
    ),
    Theater(
        key="sinai", label="Sinai", terrain_cls=terrain.Sinai, beacons="sinai",
        blue_bases=["Ramon Airbase", "Nevatim", "Hatzerim", "Ovda", "Tel Nof"],
        red_bases=[_inland("Bir Hasanah"), _inland("Melez"),
                   _inland("El Arish", 180, 6), _inland("Gebel El Basur Air Base"),
                   _inland("Cairo West"), _inland("Bilbeis Air Base")],
        red_sea=Offset("El Arish", 0, 30),
        blue_carrier=Offset("Palmachim", 270, 50),
        summer_temp=33, winter_temp=14,
    ),
    Theater(
        key="kola", label="Kola", terrain_cls=terrain.Kola, beacons="kola",
        blue_bases=["Bardufoss", "Banak", "Evenes", "Andoya", "Bodo", "Kirkenes"],
        red_bases=[_inland("Kilpyavr", 270, 5), _inland("Severomorsk-1", 90, 5),
                   _inland("Severomorsk-3", 90, 5), _inland("Murmansk International", 270, 5),
                   _inland("Olenya", 90, 5), _inland("Luostari Pechenga", 90, 5)],
        red_sea=Offset("Severomorsk-1", 20, 60),
        blue_carrier=Offset("Andoya", 300, 60),
        default_blue="Bardufoss", default_red="Kilpyavr",
        notes="Kola is dotted with lakes; check ground targets in the Mission Editor if one "
              "lands in water.",
        summer_temp=14, winter_temp=-12,
    ),
    Theater(
        key="falklands", label="South Atlantic (1982)", terrain_cls=terrain.Falklands,
        beacons="falklands",
        blue_bases=["Rio Gallegos", "Rio Grande", "San Julian", "Comandante Luis Piedrabuena"],
        red_bases=[_inland("Port Stanley", 255, 11), _inland("Mount Pleasant", 0, 6),
                   _inland("San Carlos FOB", 90, 4, spread=8, fan=20)],
        red_sea=Offset("Port Stanley", 90, 30),
        notes="You fly from the Argentine mainland against British-held East Falkland, "
              "about 400 nm away: bring tankers.",
        summer_temp=12, winter_temp=2,
    ),
    Theater(
        key="germany", label="Germany (Cold War)", terrain_cls=terrain.Germany,
        beacons="germanycoldwar",
        blue_bases=["Fassberg", "Gutersloh", "Celle", "Fritzlar", "Hahn", "Ramstein",
                    "Spangdahlem", "Bitburg"],
        red_bases=[_inland("Stendal"), _inland("Mahlwinkel"), _inland("Zerbst"),
                   _inland("Allstedt"), _inland("Merseburg"), _inland("Brand")],
        default_blue="Fassberg", default_red="Stendal",
        notes="Landlocked (as far as the action goes): no anti-ship missions or carrier ops.",
        summer_temp=22, winter_temp=0,
    ),
    Theater(
        key="normandy", label="Normandy (1944)", terrain_cls=terrain.Normandy,
        blue_bases=["Ford", "Tangmere", "Funtington", "Chailey", "Holmsley South",
                    "Saint Pierre du Mont", "Cardonville"],
        red_bases=[_inland("Carpiquet", 180), _inland("Evreux"), _inland("Bernay Saint Martin"),
                   _inland("Conches"), _inland("Argentan"), _inland("Abbeville Drucat", 90)],
        red_sea=Offset("Fecamp-Benouville", 0, 25),
        default_blue="Ford", default_red="Carpiquet",
        summer_temp=20, winter_temp=5,
    ),
    Theater(
        key="channel", label="The Channel", terrain_cls=terrain.TheChannel,
        blue_bases=["Manston", "Hawkinge", "Lympne", "Detling", "Biggin Hill", "High Halden"],
        red_bases=[_inland("Saint Omer Longuenesse"), _inland("Merville Calonne"),
                   _inland("Abbeville Drucat", 90), _inland("Dunkirk Mardyck", 180)],
        red_sea=Offset("Dunkirk Mardyck", 330, 25),
        default_blue="Manston", default_red="Saint Omer Longuenesse",
        summer_temp=20, winter_temp=4,
    ),
]}
