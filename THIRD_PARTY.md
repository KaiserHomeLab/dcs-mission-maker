# Third-party components

DCS Mission Maker builds on the work below. Nothing in this list is copied into
this repository except where noted; setup (`tools/fetch_vendor.py`, used by both the Docker
build and `windows\setup.bat`) downloads each item from a pinned commit or release and checks its hash.

## Python packages (installed at setup, `requirements.txt`)

| Package | Licence | Use |
|---|---|---|
| [pydcs](https://github.com/pydcs/dcs) | LGPL-3.0 | Reading and writing `.miz` missions |
| [Flask](https://flask.palletsprojects.com/) | BSD-3-Clause | Web app |
| [Gunicorn](https://gunicorn.org/) | MIT | Web server (Docker) |
| [Waitress](https://github.com/Pylons/waitress) | ZPL-2.1 | Web server (Windows, `python -m app`) |
| [Pillow](https://python-pillow.org/) | MIT-CMU | Kneeboard pages, print pack PDF |
| [Paramiko](https://www.paramiko.org/) | LGPL-2.1 | SFTP publishing |
| [pystray](https://github.com/moses-palmer/pystray) | LGPL-3.0 | Tray icon of the Windows app |
| [Inno Setup](https://jrsoftware.org/isinfo.php) | Inno Setup licence | Builds the installer (not part of the app) |
| [PyInstaller](https://pyinstaller.org/) | GPL-2.0 with bootloader exception | Builds the Windows app (not part of it, apart from its bootloader, which the exception allows) |

The Windows app bundles these packages unmodified. This repository's source and
`windows\build.bat` let anyone rebuild it with modified versions of the LGPL libraries
(pydcs, Paramiko, pystray).

## Mission scripts (downloaded at setup, embedded in missions you tick them for)

| Script | Licence |
|---|---|
| [MOOSE](https://github.com/FlightControl-Master/MOOSE) | GPL-3.0 |
| [MIST](https://github.com/mrSkortch/MissionScriptingTools) | GPL-3.0 |
| [Skynet IADS](https://github.com/walder/Skynet-IADS) | Apache-2.0 |
| [Hound ELINT](https://github.com/uriba107/DCS-Hound) | GPL-3.0 |
| [EWRS](https://github.com/Bob7heBuilder/EWRS) | MIT |

Missions that include these scripts carry them under their own licences.

## Data

- **Airfield beacons** (TACAN/ILS) from [DCS Retribution](https://github.com/dcs-retribution/dcs-retribution),
  LGPL-3.0, downloaded at setup.
- **Squadron liveries** (`app/data/liveries.json`, included in this repository) are derived from DCS
  Retribution's squadron files, LGPL-3.0. `tools/build_liveries.py` rebuilds it from the pinned commit.
- **3-view drawings** for the Threat ID sheets come from Wikimedia Commons under public domain, CC0,
  CC BY or CC BY-SA licences (`drawings.json` lists each file, author and licence). They're downloaded
  at setup and credited on every sheet that shows one.

## In the browser

- [Leaflet](https://leafletjs.com/) (BSD-2-Clause), loaded from unpkg.
- Map tiles from OpenStreetMap, OpenTopoMap and Esri, credited on the map.

## Fonts

- [DejaVu fonts](https://dejavu-fonts.github.io/) 2.37 (Bitstream Vera / DejaVu licence), downloaded at setup
  with their licence file (`vendor/fonts/LICENSE`), for the kneeboards.

DCS World, its modules and their 3D models are © Eagle Dynamics and their developers. This project
isn't affiliated with Eagle Dynamics.
