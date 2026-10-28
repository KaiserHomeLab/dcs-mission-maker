# DCS Mission Maker

A small web app that generates `.miz` mission files for DCS World. It runs
straight on Windows (e.g. on the PC that hosts your DCS server) or in Docker.
Pick the map, the mission and the aircraft you and your friends want to fly,
and it writes a ready-to-fly multiplayer mission. Enemies, support aircraft
and loadouts all adapt to what you picked.

It's built on [pydcs](https://github.com/pydcs/dcs), the same library used by
DCS Liberation and Retribution.

## Run it

### The Windows app (no Python, no Docker)

Download `DCS-Mission-Maker-Setup-<version>.exe` from the
[Releases](https://github.com/KaiserHomeLab/dcs-mission-maker/releases) page and run it. It installs to Program Files, adds a Start menu
entry and an uninstaller, and offers to:

- **let other PCs reach it** (a Windows Firewall rule for the app, whatever port it uses), and
- **start it when you log on**.

The app opens the builder in your browser and sits in the tray (next to the clock):
*Open*, *Settings*, *Open data folder*, *Start with Windows* and *Quit*. Running it again
while it's running just opens the browser.

- **Your data** (missions, settings, logs) lives in `C:\ProgramData\DCS Mission Maker`,
  readable only by your account and administrators, since the settings hold your Discord
  webhook and passwords. Upgrades keep it; uninstalling asks before deleting it.
- **Settings** (⚙ in the builder): public address, the server's Missions folder (suggested
  from your Saved Games), SRS, Discord, password and so on. They can be changed from the PC
  running the app, or from anywhere once a password is set.
- **Port:** 8080. If another program has it, the app moves to the next free port, tells
  you, and remembers it (change it on the Settings page).
- **Installed maps:** on the DCS server's PC the app finds the DCS install (`Program Files\Eagle
  Dynamics\DCS World Server` and the other usual places, or the folder set on the Settings page)
  and offers only the maps installed there, by the folders in `Mods\terrains`. Turn the check
  off on the Settings page to build missions for maps this PC doesn't have.
- **Updates:** once a day the app asks GitHub for the latest release and the builder shows
  a note when there's a newer one; download and run its installer over the old one. The
  request carries only the app's version. Turn it off on the Settings page.
- **SmartScreen:** the installer isn't code-signed yet, so Windows may say "Windows protected
  your PC": choose *More info*, then *Run anyway*.
- No installer? The release (and every CI run) also has a zip of the app: unzip it anywhere
  and run `DCS Mission Maker.exe`.

### On Windows from source, without Docker (e.g. on your DCS server PC)

This is the lighter option next to a DCS server: no Docker, no virtual machine taking RAM.

1. Install [Python 3.12](https://www.python.org/downloads/) (keep *py launcher* ticked).
2. Get this project: `git clone https://github.com/KaiserHomeLab/dcs-mission-maker.git dcs-mission-maker`, or download it as a ZIP
   and unpack it, e.g. to `C:\dcs-mission-maker`.
3. Double-click `windows\setup.bat`. It creates a Python environment in `.venv`, installs
   the packages, downloads the pinned mission scripts, airfield data and fonts, and creates
   `.env` from `.env.example`.
4. Double-click `windows\start.bat` and open <http://localhost:8080>. Close the window to stop it.

Optional:

- `windows\open-firewall.bat` (right-click, *Run as administrator*) lets other PCs reach port 8080.
- `windows\autostart-on.bat` starts the app whenever you log on (`autostart-off.bat` undoes it).
- In `.env`, set `SERVER_MISSIONS_DIR` to the server's Missions folder, e.g.
  `C:\Users\dcs\Saved Games\DCS.server\Missions`, to publish missions straight to it, and
  `PUBLIC_URL` to the address your friends use.

Missions are stored in the `missions` folder. To update, `git pull` (or unpack the new ZIP
over the old folder) and run `setup.bat` again. `python -m app` runs the same server on Linux too.

### With Docker

You need Docker with the Compose plugin (Docker Desktop on Windows/macOS, or Docker Engine on Linux).

```bash
git clone https://github.com/KaiserHomeLab/dcs-mission-maker.git dcs-mission-maker
cd dcs-mission-maker
docker compose up -d --build
```

The first build takes a few minutes: it downloads the pinned mission scripts,
airfield data and fonts.

Open <http://localhost:8080> (or `http://<host-ip>:8080` from another PC).
Generated missions download from the page and are stored in `./missions` (with their
settings as `.json`; saved setups go to `./missions/setups`). New missions are
**temporary**: their download and Briefing Room work straight away, and they're deleted
24 hours later (`MISSION_TTL_HOURS`) unless you press **Keep** on the result or in
*Recent missions*. Missions posted to Discord, published to your server or generated
from a sign-up page are kept automatically, because other people have links to them.
Kept missions have a **Delete** button.

### Optional: Discord and publishing to your server

Copy `.env.example` to `.env` (Windows setup does this for you), fill in what you use, and
restart the app (`windows\start.bat`, or `docker compose up -d`):

- `DISCORD_WEBHOOK_URL`: posts each mission (briefing, kneeboard preview and
  the `.miz`) and sign-up links to a channel.
- `PUBLIC_URL`: how your friends reach this app, used in sign-up links.
- `SERVER_MISSIONS_DIR` (Windows) or `SERVER_MISSIONS_HOST_DIR` (Docker): your DCS
  server's `Missions` folder on this machine (or a share). Missions get copied straight in.
- `SFTP_*`: upload to a remote server (e.g. a rented Windows box running
  OpenSSH) instead. Set `SFTP_KNOWN_HOSTS` to verify the server's key.
- `APP_PASSWORD`: protects the builder and everything that generates, publishes or
  deletes (see [Security](#security)).
- `SRS_ADDRESS` / `SRS_NOTE`: your usual SRS voice server, the default for the
  per-mission SRS field.
- `MISSION_TTL_HOURS`: how long unkept missions stay (default 24).
- `WEB_CONCURRENCY` (Docker): worker processes (default 3; each builds one mission at a time).
- `PORT` (Windows): the port to serve on (default 8080).

Then tick *Copy to server*, *Upload (SFTP)* or *Post to Discord* next to the
Generate button.

## Using the missions

1. Copy the `.miz` into `Saved Games\DCS\Missions\`.
2. **Multiplayer:** host it from the Multiplayer menu. Every seat is a *Client*
   slot named after its flight, for example `VFA-103 - Hornet 1` / `Hornet 1-2`.
3. **Single-player:** tick *Single-player* so the first seat becomes *Player*.

## Features

| | |
|---|---|
| **Maps** | Caucasus, Persian Gulf, Syria, Nevada, Marianas, Sinai, Kola, South Atlantic (Falklands, 1982), Germany (Cold War), Normandy (1944), The Channel |
| **Missions** | CAP, CAS, SEAD/DEAD, Precision Strike, Anti-Ship, Combat Search & Rescue, Free Flight |
| **Extra objectives** | Up to two more targets (air defense site, artillery battery, supply convoy, early-warning radar), either all briefed up front or unlocked one at a time with a radio call and coordinates when the previous one dies. |
| **Living battlefield** | CAS columns push toward friendly armor holding a front line drawn on the F10 map. Hidden pop-up air defenses switch on when you get close (more on higher difficulty). Enemy fighters scramble when you approach instead of on a timer. |
| **CSAR** | A downed pilot past the enemy airfield and a search party closing in. Helicopters find the survivor through MOOSE CSAR (beacon, smoke, flares) and bring them to the MASH; everyone else escorts and kills the search party. |
| **Sign-up page** | Turn a mission into a shareable page where friends claim seats ("Viper 1-2"). Tick *Repeat weekly* for a regular night: once an occurrence is generated (or 3 hours after it starts), next week's sign-up opens with the same setup and empty seats, is posted to Discord if the first one was, and is linked from the old page. Generating from it puts their names on the slots ("Viper 1-2 (Mitsu)"), the briefing and the kneeboards. Optionally posts the link to Discord. |
| **Discord & server** | Post missions to Discord, copy them straight into your server's Missions folder, or upload them over SFTP (see above). |
| **Briefing Room** | Every mission gets its own page (`/briefing/<mission>`), linked from the Generate result, recent missions, sign-up pages and Discord posts. A full-screen tactical map with map, terrain and satellite views shows each flight's route and waypoints, SAM threat rings, objectives, tanker/AWACS orbits, bullseye, front line and JTAC (click anywhere for coordinates and bullseye bearing/range). Tabs beside it cover the tasking and situation, each flight's route table, loadout and radios, a comms card, threats, weather and home field, and the kneeboard pages. Printable, and shareable with your group. A **Who's flying** roster lets each player type their name and take a seat ("Viper 1-2"); everyone sees who's on which aircraft, AI wingmen are marked, names from a sign-up page carry over, and the slot names in the `.miz` update to "Viper 1-2 (Mitsu)" (re-download or re-publish after everyone has picked). |
| **My flight** | Once you've taken a seat, the Briefing Room's *My flight* tab shows your own route map with numbered waypoints and the threat rings near it, a leg table (true heading, distance, altitude, bullseye), your TOT, loadout, radios and wingmen, recognition cards for the threats along your route, and your kneeboard. The main map highlights your flight too. |
| **Threat ID** | Blueprint drawing sheets for every enemy system in the mission. The fighters, the main tanks and IFVs, the main SAM launchers, and the Ticonderoga and Arleigh Burke use **3-view recognition drawings** made for the app (`app/data/drawings/`), recoloured to blueprint style; variants such as the T-72B3 borrow the closest one until they have their own. Every other ground and naval unit (tanks, APCs, SPAAGs, SAM launchers, towed guns, radars, artillery, MANPADS, ships) gets a **generated 3-view line drawing** in the same style: side, plan and front views at one true scale built from published dimensions, with running gear, turrets, guns, missiles, radars and hidden lines removed, plus length/width/height dimensions. Each sheet also has an engagement-envelope or weapon-range diagram and a title block; click one to open it full screen. Each card also lists (fighters, SAM sites, short-range air defenses, radars, armor, ships): role, range, altitude, guidance, weapons, RWR symbol where well known, and how to beat it. Pop-up threats and not-yet-revealed targets show as "possible" without a location. Generated drawings are representative in detail, and figures are approximate. |
| **Waypoints** | Every flight gets a full route: Join, Push, Ingress, Target (plus extra objectives), Egress (turned off the attack axis, away from your ingress) and Return, then home. CAP flights get a two-point CAP racetrack. The same waypoints go into the mission, the data cartridges and the kneeboards. |
| **Route editing & TOT** | Drag each flight's Push, Ingress and Egress on the map. Set a time on target: the target waypoint is locked to it, the time to leave Ingress is briefed, warnings show if a flight can't make it, and AI flights can be timed off it (SEAD goes in 3 min before you, strikers just after). |
| **Airfield data** | Home field TACAN, tower frequencies, runway in use (into the wind) and its ILS, in the briefing and on the kneeboards. |
| **Mods** | Tick the mods your group has: Community A-4E-C and UH-60L Black Hawk as flyable aircraft, High Digit SAMs (SA-20/SA-20B for modern Soviet-side enemies). The mission lists them as required modules. |
| **Server load check** | An optional DCS server hook reports whether each mission loaded without script errors; the result shows next to the mission in the app. |
| **Debrief** | With the same hook installed, the Briefing Room's *Debrief* tab fills in while the mission is flown and after it ends: which objectives were destroyed, a row per pilot (kills and what they destroyed, losses, landings, friendly fire) and a timeline. The hook reports every minute and once more at mission end. |
| **SRS password rotation** | Optional (Settings > *SRS password rotation*, Windows app on the PC running SRS). Each time a mission is copied to the server, the app makes random blue and red **External AWACS Mode** passwords, stops SRS through its Task Scheduler task, writes them into SRS's `server.cfg` (only `EXTERNAL_AWACS_MODE_BLUE_PASSWORD` and `EXTERNAL_AWACS_MODE_RED_PASSWORD` in `[External AWACS Mode Settings]` change; the old file is kept as `server.cfg.dmm-backup`) and starts SRS again. If SRS can't be stopped, nothing changes; if writing fails, SRS is still started again. That mission's Briefing Room (Comms tab) shows the passwords until another mission is published. Restarting SRS drops everyone on it for a few seconds, so it only happens on publish. The task should start `SR-Server.exe` directly, and the app's user must be allowed to stop and start it. |
| **Print pack** | One PDF with the briefing and every kneeboard page (Briefing Room > *Print pack*), for printing or a tablet. |
| **Liveries** | Each flight has a livery dropdown. Built in: the stock DCS liveries that DCS Retribution's squadrons use (e.g. "VFA-37 Ragin' Bulls (USA)"), for about 30 of the flyable aircraft; picking one fills in the squadron name if it's empty. With the DCS server hook installed, the server also reports every livery it has (stock and custom, by in-game name) and those are listed first. Everyone flying needs the livery installed; DCS shows its default otherwise. |
| **SRS** | Set the SRS voice server per mission in the builder (step 5, plus an optional note such as where the password is), or a default with `SRS_ADDRESS` / `SRS_NOTE` in `.env`. It appears on the Comms tab, the kneeboards and Discord posts. The Comms tab also has a plain-text **comm card** with every frequency for a second screen or phone. The password is never stored. |
| **Era-matched enemies** | Your aircraft decide the era (WWII, Korea, Vietnam, Late Cold War, Modern) and your side. The enemy is the opposite side of the same era: P-51s meet Fw 190s and 88 mm Flak, F-86s meet MiG-15s, F-4Es meet MiG-21s and SA-2s, MiG-29s meet F-15s and Patriots. You can override the era. |
| **Friendly AI** | AI wingmen inside your own flights (players take the first seats, AI fills the rest), plus separate AI flights: CAP, escort (sticks to a player flight you pick), SEAD, CAS, strike and anti-ship, with an optional launch delay (T+5 to T+60 min). AI types suitable for the job and era are listed first. |
| **JTAC** | For CAS, strike and SEAD (Vietnam era onward): JTAC "Axeman" on 266.0 AM, laser code 1688. In the modern era it's an MQ-9 orbiting the target, otherwise a ground team. Invisible and immortal so it stays on station. |
| **Kneeboards** | Two pages per flight, dark pages for night (and winter dawn/dusk) missions so they don't blind you. **Flight:** tasking, steerpoints with lat/long and bullseye bearing/range, radio presets, support frequencies, threats and weather. **Route:** a north-up sketch of the route (numbered waypoints, threat rings, bullseye, scale), a nav log (true course, leg and total distance, altitude, speed and ETA, worked back from the TOT when one is set), and what to do at each waypoint for your mission type and aircraft. Both are in the Briefing Room's Kneeboards tab too. DCS shows kneeboard pages per aircraft type, so flights flying the same type see each other's pages. |
| **Kneeboard editing** | In the Briefing Room's *Kneeboards* tab, pilots with a seat in an aircraft (on the roster) can change that aircraft's kneeboard: hide, show and reorder pages, add a **notes page** (typed text, drawn like the other pages and dark at night), and **upload pages** as PNG, JPG or PDF (up to 20 PDF pages, 16 MB per upload, 30 pages per aircraft). Uploads are re-drawn as plain PNG images, so nothing but pixels goes into the `.miz`. Ticking *Also save to the squadron library* adds the pages to every new mission with that aircraft (stored in `missions/kneeboards/`; hide them per mission, or remove them from the library). *Reset* restores the pages the mission was built with, and a change list shows who did what. Every change rewrites the `.miz`; when the mission was copied to the server folder, that copy is updated too (for the next time the mission loads). |
| **Bullseye** | Set halfway between your airfield and the target; shown in the briefing, kneeboards and cartridges. |
| **Mission options** | Unit labels, F10 map visibility, external views, unlimited fuel/weapons, easy comms, civilian traffic, bird strikes. |
| **Saved setups** | Save your group's usual setup by name and load it next time. Every generated mission also keeps its settings, so you can "Reuse settings" from the recent list and tweak them. |
| **Map preview & Surprise me** | A live map of home, target, bullseye and carrier. Surprise me randomizes map, mission, time and weather but keeps your flights. The map tiles come from OpenStreetMap, so they need internet access; everything else works offline. |
| **Squads** | Each flight gets a real DCS callsign, including aircraft-specific ones (Viper, Hornet, Hawg, Apache...), a flight number and an optional squadron name. Units are named `Viper 1-1`, `Viper 1-2`, and the callsign, datalink voice callsign and Link 16 STN all match. |
| **Comm plan** | Radio presets on every seat: flight, package, AWACS, tankers, tower. Listed in the briefing. |
| **Loadouts** | Matched to the mission: HARMs for SEAD, Harpoons/C-802s for anti-ship, Mavericks and GBUs for CAS, and so on. Each flight can pick another preset, and the UI shows exactly what's on the jet. |
| **Data cartridge (DTC)** | F/A-18C and F-16C flights get a native DCS Data Transfer Cartridge that loads at spawn: steerpoints, threat rings, tanker/AWACS orbits, home field, and on the Hornet named COMM channels plus carrier TACAN/ICLS/ACLS. |
| **Scripts** | MOOSE, MIST, Skynet IADS, Hound ELINT, EWRS, plus CTLD and CSAR (via MOOSE) for helicopter flights. Dependencies are added automatically. |
| **Your own scripts** | Drop any `.lua` into `./scripts` (e.g. Splash Damage 3.x from the DCS user files) and it appears in the UI. It's loaded after the built-in ones. |
| **Support** | AWACS and boom/drogue tankers appropriate to the era and side (none in WWII/Korea). Carrier ops from CVN-74 Stennis, or CV-9 Essex for WWII. |

## How the scripts are wired

All scripts load from a *Mission Start* trigger (`DO SCRIPT FILE`) in this
order: MIST, MOOSE, Skynet, Hound, EWRS, CTLD, CSAR, then your custom scripts.

- **Skynet IADS:** enemy SAM sites are named `SAM ...` and early-warning radars
  `EW ...`. The config calls `addSAMSitesByPrefix('SAM')` and
  `addEarlyWarningRadarsByPrefix('EW')`.
- **Hound ELINT:** uses the AWACS as its sensor platform, so it needs AWACS on.
- **CTLD:** pickup zone `CTLD Pickup` at your airfield, with an infantry squad
  and a Humvee crate. Uses your helicopter flights' group names.
- **CSAR:** downed pilots use the `CSAR Pilot` template; the MASH is zone
  `MASH Home` at your airfield.

Bundled scripts are downloaded at build time from their upstream repos, pinned
to exact commits and checked with SHA-256 (see `tools/fetch_vendor.py`):
MOOSE (GPL-3.0), MIST 4.5.126 (GPL-3.0), Skynet IADS 3.3.0 (Apache-2.0),
Hound ELINT 0.5.2 (GPL-3.0), EWRS (MIT).

## DCS server hook (experimental)

Download `http://<this app>/dcs-hook.lua` and save it as
`Saved Games\DCS.server\Scripts\Hooks\dmm_reporter.lua` (or `Saved Games\DCS\...`
if you host from your own PC). When a mission starts, it waits a minute, scans
`dcs.log` for script errors logged since the mission loaded, and reports back. While
the mission runs it also records kills, losses, ejections, crashes, take-offs and
landings and reads the objective flags (9000 = all done, 9001+ = each objective),
and sends them every minute and at mission end for the Debrief tab. Once per DCS
session it also lists the liveries installed on the server (DCS install and
`Saved Games\Liveries`) for the builder's livery dropdowns.
The app needs to be reachable from the DCS machine (`PUBLIC_URL`; on the same PC, `http://localhost:8080` works). It uses the
LuaSocket library that ships with DCS. **It hasn't been run inside DCS yet.**

## Notes and limits

- **Blueprint drawings:** the recognition drawings are made with an image generator from the prompts in [art/PROMPTS.md](art/PROMPTS.md), checked against photos for the features that tell a unit apart, and cleaned by `tools/art_drawings.py`. Detail and proportions are approximate. Units without one yet use generated line drawings. DCS's own 3D models are proprietary and aren't used.

- **Not flown yet:** missions are checked for structure and Lua syntax, but not
  loaded in DCS by the generator. Fly a test mission before a big night.
- **DTC** follows the format used by DCS Retribution's DTC work, which was
  checked against the Mission Editor's own DTC manager. The F-14B(U) also
  supports cartridges in DCS, but its format isn't documented, so it doesn't
  get one yet.
- **Loadouts:** the F-16C, F/A-18C, A-10C/A-10C II, F-15E, AH-64D, Ka-50,
  AV-8B, F-14 family, M-2000C and JF-17 have hand-written loadouts per role.
  Other aircraft get an automatic loadout from the weapons each pylon allows.
- **Placement:** target areas and sea positions are hand-picked per map in
  `app/theaters.py`, because pydcs has no land/sea data.
- **Kola** is full of small lakes; check ground targets in the Mission Editor if
  one ends up in water. Normandy and the Channel have no TACAN/ILS data (1944).
- **Mod aircraft** spawn clean (no loadout data for them); rearm on the ground.
- **Afghanistan and Iraq** aren't in pydcs yet, so they're not offered.
- In Docker the app runs as an unprivileged user (uid 1000); on start it makes
  `./missions` and the server-missions folder writable for that user. On Windows it runs as
  whoever starts it, so use a normal (not administrator) account.

## Security

- With **`APP_PASSWORD`** set, your browser asks for a password (any user name) on the
  mission builder and on everything that generates, publishes, deletes or posts to
  Discord. Sign-up pages, the Briefing Room (including the seat roster), mission
  downloads and the DCS server hook stay open, so pilots and the server need no password.
- Without it the app is open to anyone who can reach it. That's fine on a home LAN or
  VPN; if it's reachable from the internet, set `APP_PASSWORD` and put it behind a
  reverse proxy with HTTPS (Caddy or nginx), since Basic auth sends the password with
  every request.
- Sign-up and Briefing Room links are hard to guess but not secret: anyone with a link
  can claim a seat.
- With SRS password rotation on, the EAM passwords are shown in the published mission's
  Briefing Room, which anyone with its link can open (including through a Cloudflare bypass).
  Anyone who has the link can join SRS as an external AWACS for either side.
- Secrets (Discord webhook, SFTP password, `APP_PASSWORD`) live only in `.env`, which is
  ignored by git. Never put the SRS password in the SRS note.

### Reaching it from outside your network (Cloudflare Tunnel)

A Cloudflare Tunnel publishes the app over HTTPS without opening a port on your router:

1. Zero Trust > Networks > Tunnels: create a tunnel, run its Windows install command on the
   PC running the app (it becomes a service), and add a public hostname, e.g.
   `missions.example.com`, pointing to `http://localhost:8080`.
2. Zero Trust > Access > Applications: one app for the whole hostname that allows only you,
   and a second app on the same hostname for what pilots use, with a **Bypass** (Everyone)
   policy on these paths: `briefing/*`, `e/*`, `missions/*`, `api/missions/*`, `api/events/*`,
   `static/*`, `drawings/*` and `api/options`.
3. In the app's Settings, set a builder password too: a few builder actions (deleting a
   mission, generating from a sign-up) live under those paths, and the app asks for the
   password there. Set the public address to `https://missions.example.com`.

Download the DCS server hook on the server's PC itself (`http://localhost:8080/dcs-hook.lua`)
so it reports straight to the app instead of through Cloudflare.

## Development

Templates hold markup only; scripts and styles live in `app/static`, and server values reach the
page scripts through `data-` attributes on `<body>` (e.g. `data-stem` in the Briefing Room).
Static files are linked with a content hash (`static_url()` in the templates), so browsers cache
them for a year and pick up changes immediately. GitHub Actions (`.github/workflows/ci.yml`) runs
the linters, builds the image and runs the API tests, the quick smoke test and a Lua syntax check
on every push and pull request.

```bash
ruff check app tools tests        # Python lint (settings in pyproject.toml)
npx eslint app/static             # browser-script lint (settings in eslint.config.mjs)
docker compose build
# Quick sample (~35 s): every map, mission type, era and aircraft at least once:
docker run --rm -v $PWD:/src:ro -w /src dcsmission-dcs-mission-maker python -m tests.smoke --quick
# Full run (~900 missions across maps, mission types, eras, every aircraft, scripts and mods),
# built in parallel on every CPU (--jobs N to limit):
docker run --rm -v $PWD:/src:ro -w /src dcsmission-dcs-mission-maker python -m tests.smoke
# API: sign-ups, publishing, Discord (against a fake webhook), server reports:
docker run --rm -v $PWD:/src:ro -w /src dcsmission-dcs-mission-maker python -m tests.api
# Also dump the mission tables and script configs for a Lua syntax check:
mkdir -p /tmp/lua && docker run --rm -v $PWD:/src:ro -v /tmp/lua:/lua -w /src \
  dcsmission-dcs-mission-maker python -m tests.smoke --lua-dir /lua
docker run --rm -v /tmp/lua:/lua:ro debian:stable-slim sh -c \
  'apt-get update -qq && apt-get install -y -qq lua5.1 >/dev/null && for f in /lua/*; do luac5.1 -p "$f"; done'
```

| File | Purpose |
|---|---|
| `app/generator/` | Mission building. `__init__.py` is the public API (`generate_full`, `preview`) |
| `app/generator/request.py` | Mission and flight requests, their choices, and validation |
| `app/generator/builder.py` | `Builder`: shared state, build order, time and weather; combines the mixins below |
| `app/generator/enemy.py` | Enemy ground groups and SAM sites, the objective for each mission type, EWRs, enemy fighters |
| `app/generator/friendly.py` | Carrier group, AWACS and tankers, JTAC, friendly AI flights |
| `app/generator/players.py` | Player flights: spawning, callsigns, loadouts, routes, TOT, data cartridges |
| `app/generator/scripting.py` | Third-party scripts and glue, forced options, completion trigger |
| `app/generator/briefing.py` | Briefing text, kneeboards, Briefing Room export and order of battle |
| `app/generator/common.py`, `preview.py` | Shared constants and position helpers; map preview for the builder |
| `app/ai.py` | Friendly AI flight catalog and job definitions |
| `app/kneeboard.py` | Kneeboard page rendering |
| `app/eras.py` | Era/side detection and the enemy and support forces for each |
| `app/comms.py` | DCS callsigns, datalink callsigns and radio presets |
| `app/loadouts.py` | Curated and automatic loadouts, presets per mission |
| `app/dtc.py` | Data Transfer Cartridges for the F/A-18C and F-16C |
| `app/scripts.py` | Script catalog, dependency ordering and config glue |
| `app/theaters.py` | Per-map bases, target areas, sea and carrier positions |
| `app/aircraft.py` | Flyable aircraft catalog and display names |
| `app/objectives.py` | Extra/chained objectives, front line, pop-up threats, zone triggers |
| `app/navdata.py` | Airfield TACAN/ILS/tower data and runway in use |
| `app/mods.py` | Community mod aircraft and units |
| `app/integrations.py` | Discord webhook, server folder and SFTP publishing |
| `app/server.py` | Flask API, sign-ups, downloads |
| `app/templates/index.html` | The mission builder (page markup) |
| `app/templates/event.html` | The sign-up page (page markup) |
| `app/templates/briefing.html` | The Briefing Room (page markup) |
| `app/static/css/` | `base.css` (shared theme), one stylesheet per page, `blueprint.css` (drawing sheets) |
| `app/static/js/common.js` | Helpers shared by the page scripts |
| `app/static/js/builder.js`, `event.js`, `briefing.js` | Page scripts for the builder, sign-up page and Briefing Room |
| `app/threatdb.py` | Threat recognition data and dimensions for the Threat ID cards |
| `app/static/js/blueprint.js` | Blueprint sheets: layout, envelopes, recognition drawings, aircraft two-views |
| `app/static/js/draw3v.js`, `draw3v_units.js`, `draw3v_specs.js` | Generated 3-view line drawings: parts (tracks, wheels, barrels, missiles, radars), vehicle/gun/ship families, and per-unit specs in metres |
| `app/data/drawings/`, `tools/art_drawings.py`, `art/PROMPTS.md` | Recognition drawings made for the app: the tool cleans images dropped in `art/drawings/` into `app/data/drawings/` and rewrites the prompt list for the units still without one |
| `tools/fetch_vendor.py` | Downloads the pinned, SHA-256-checked mission scripts, beacon data and fonts into `vendor/` |
| `app/paths.py` | Where data lives: from the environment (Docker) or folders in the project (Windows) |
| `app/__main__.py`, `windows/*.bat` | `python -m app` (waitress server, reads `.env`); Windows setup, start, autostart, firewall and build scripts |
| `app/desktop.py`, `app/icon.py`, `windows/launcher.py`, `windows/dcs-mission-maker.spec` | The Windows app: tray icon, single instance, start with Windows, logs; its icon; the PyInstaller recipe |
| `app/settings.py`, `app/templates/settings.html`, `app/static/js/settings.js` | The Settings page: settings.json, validation, locked `.env` values, secrets never sent back |
| `dcs-hook/dmm_reporter.lua` | DCS server hook: script-error check and debrief events |
| `app/debrief.py` | Turns the hook's events and flags into the Debrief tab |
| `app/mission_store.py` | Temporary vs kept missions, expiry and deletion |
| `app/liveries.py`, `app/data/liveries.json`, `tools/build_liveries.py` | Livery choices: squadron liveries from DCS Retribution (LGPL-3.0, pinned commit; the tool documents how to rebuild the JSON) merged with what the server hook reports |
| `pyproject.toml`, `eslint.config.mjs` | Lint settings (Ruff for Python, ESLint for the browser scripts) |
| `Dockerfile`, `docker-entrypoint.sh`, `gunicorn.conf.py`, `docker-compose.yml` | Two-stage image (downloads in the build stage), volume ownership and privilege drop, web server settings |
| `.github/workflows/ci.yml`, `windows.yml` | CI: lint, image build and tests; on Windows the tests without Docker, the app build, its installer (installed, run and uninstalled) |
| `.github/workflows/release.yml` | Publishes a release with the installer and zip when a `v*.*.*` tag is pushed |
| `windows/installer.iss`, `windows/smoke-test.ps1` | The installer (Inno Setup): Program Files, firewall rule, start at logon, uninstaller; the CI check that starts the app and builds a mission |
| `app/kneeboard_store.py` | Kneeboard editing in the Briefing Room: page state per mission, uploads (re-encoded), notes pages, the squadron library, rewriting the `.miz` |
| `app/dcs_install.py` | Finds the DCS install on this PC and which maps it has (`Mods\terrains`) |
| `app/updates.py`, `tools/write_build_info.py` | The daily update check against GitHub Releases (release builds only) |
| `THIRD_PARTY.md` | Third-party components and their licences |

### Releasing the Windows app

1. Set the new version in `app/__init__.py` (`__version__`) and `pyproject.toml`, and commit.
2. `git tag v1.2.0 && git push origin v1.2.0` (the tag must match the version).
3. `.github/workflows/release.yml` builds and tests the app and installer on Windows and
   publishes a GitHub release with both. Release builds know the repository they came from
   (`tools/write_build_info.py`), which turns on their update check.

Locally, `windows\build.bat` builds the same app, zip and (with Inno Setup 6 installed) installer.

## Credits and licences

Built on pydcs, MOOSE, MIST, Skynet IADS, Hound ELINT, EWRS, DCS Retribution's data
and Leaflet. See [THIRD_PARTY.md](THIRD_PARTY.md) for each
component and its licence. DCS World is © Eagle Dynamics; this project isn't affiliated with it.

DCS Mission Maker is free software under the [GNU General Public License v3.0](LICENSE) or later.
