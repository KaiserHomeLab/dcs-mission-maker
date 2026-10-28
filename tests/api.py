"""API checks: sign-ups, publishing, Discord (against a fake webhook), reports."""
import base64
import datetime
import http.server
import io
import json
import os
import pathlib
import sys
import tempfile
import threading
import zipfile

tmp = tempfile.mkdtemp()
os.environ.update(OUTPUT_DIR=f"{tmp}/out", SERVER_MISSIONS_HOST_DIR="/x",
                  SERVER_MISSIONS_DIR=f"{tmp}/server", PUBLIC_URL="http://missions.local")
os.makedirs(f"{tmp}/server")
got = []


class Hook(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        got.append(self.rfile.read(int(self.headers["Content-Length"])))
        self.send_response(204)
        self.end_headers()

    def log_message(self, *a):
        pass


srv = http.server.HTTPServer(("127.0.0.1", 0), Hook)
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["DISCORD_WEBHOOK_URL"] = f"http://127.0.0.1:{srv.server_port}/hook"

from app.server import app  # noqa: E402

OUTPUT_DIR_PATH = pathlib.Path(os.environ["OUTPUT_DIR"])

c = app.test_client()
fails = []


def ok(cond, msg):
    if not cond:
        fails.append(msg)
        print("FAIL", msg)


cfg = {"theater": "caucasus", "mission_type": "cas",
       "flights": [{"aircraft": "F-16C_50", "slots": 2, "callsign": "Viper", "number": 1}]}
r = c.post("/api/events", json={"title": "Friday", "when": "Fri 20:00",
                                    "when_iso": "2026-10-24T18:00:00.000Z", "config": cfg, "discord": True})
ok(r.status_code == 200, f"create event {r.status_code} {r.json}")
eid = r.json["id"]
ok(r.json.get("discord") == "ok", f"event discord post: {r.json}")
ok(c.get(f"/e/{eid}").status_code == 200, "event page")
ok(b"<t:1792864800:F>" in got[0], "discord gets a local-time timestamp")
ok(c.get(f"/api/events/{eid}").json["when_iso"].startswith("2026-10-24T18:00"), "when_iso stored")
r = c.post(f"/api/events/{eid}/claim", json={"seat": "Viper 1-2", "name": "Mitsu"})
ok(r.status_code == 200 and r.json["seats"][1]["pilot"] == "Mitsu", "claim seat")
r = c.post(f"/api/events/{eid}/claim", json={"seat": "Viper 1-2", "name": "Bob"})
ok(r.status_code == 409, "seat already taken")
r = c.post(f"/api/events/{eid}/generate", json={"publish": ["folder", "discord"]})
ok(r.status_code == 200, f"event generate {r.status_code} {r.json}")
ok(r.json.get("published") == {"folder": "ok", "discord": "ok"}, f"publish: {r.json.get('published')}")
name = r.json["filename"]
ok(os.path.exists(f"{tmp}/server/{name}"), "copied to server folder")
with zipfile.ZipFile(f"{tmp}/out/{name}") as z:
    ok("Viper 1-2 (Mitsu)" in z.read("mission").decode(), "pilot name on the slot")
ok(len(got) == 2 and name.encode() in got[1] and b"kneeboard.png" in got[1], "discord multipart")
stem = name[:-4]
ok(c.get(f"/briefing/{stem}").status_code == 200, "briefing room page")
b = c.get(f"/api/missions/{stem}/brief").json
ok(b["flights"][0]["route"][0]["name"] == "Join" and b["bullseye"]["pos"], "briefing data")
ok(c.get(f"/missions/{stem}/kneeboard/1.png").data[:4] == b"\x89PNG", "kneeboard image")
ok(c.get(f"/missions/{stem}/kneeboard/1_route.png").data[:4] == b"\x89PNG", "route kneeboard image")
ok(c.get(f"/missions/{stem}/kneeboard/1_x.png").status_code == 404, "bad kneeboard page name")

# Debrief from the DCS hook: events + objective flags; resending a batch doesn't duplicate it.
ok(c.get(f"/api/missions/{stem}/debrief").json["debrief"] is None, "no debrief before the hook reports")
evs = [{"type": "takeoff", "t": 60, "player": "Mitsu", "place": "Senaki"},
       {"type": "kill", "t": 900, "player": "Mitsu", "victim_type": "T-72B3", "weapon": "GBU-12"},
       {"type": "bogus", "t": 901},
       {"type": "landing", "t": 2400, "player": "Mitsu", "place": "Senaki"}]
for _ in range(2):
    r = c.post("/api/debrief", json={"mission": f"{stem}.miz", "from": 0, "events": evs, "time": 2500,
                                     "flags": {"9000": 1, "9001": 1}})
ok(r.status_code == 200 and r.json["events"] == 3, f"debrief post {r.status_code} {r.json}")
c.post("/api/debrief", json={"mission": f"{stem}.miz", "from": 3, "final": True,
                             "events": [{"type": "mission_end", "t": 2600}]})
d = c.get(f"/api/missions/{stem}/debrief").json["debrief"]
ok(d["final"] and d["all_done"] and d["objectives"][0]["done"], f"debrief objectives {d}")
ok(d["pilots"][0]["name"] == "Mitsu" and d["pilots"][0]["kills"] == 1 and d["pilots"][0]["sorties"] == 1,
   f"debrief pilots {d['pilots']}")
ok(len(d["timeline"]) == 4 and "killed T-72B3 with GBU-12" in d["timeline"][1]["text"], f"timeline {d['timeline']}")
ok(c.post("/api/debrief", json={"mission": "nope.miz"}).status_code == 404, "debrief unknown mission")

r = c.get(f"/missions/{stem}/pack.pdf")
pdf_pages = r.data.count(b"/Type /Page\n") + r.data.count(b"/Type /Page ")
ok(r.status_code == 200 and r.data[:5] == b"%PDF-" and pdf_pages >= 3, f"print pack {r.status_code} {pdf_pages} pages")

# SRS default from the settings, stored with each mission + comm card
ok(c.get(f"/api/missions/{stem}/brief").json["srs"] is None, "no SRS when none was set")
os.environ.update(SRS_ADDRESS="srs.example.com:5002", SRS_NOTE="password in #dcs")
sstem = c.post("/api/generate", json=cfg).json["filename"][:-4]
ok(c.get(f"/api/missions/{sstem}/brief").json["srs"]["address"] == "srs.example.com:5002", "default srs in brief")
card = c.get(f"/missions/{sstem}/comms.txt").get_data(as_text=True)
ok("SRS server: srs.example.com:5002" in card and "Viper 1" in card and "Guard" in card, f"comm card:\n{card}")
ok(c.get("/briefing/nope").status_code == 404, "unknown briefing 404")
ro = c.get(f"/api/missions/{stem}/roster").json
ok([st["pilot"] for st in ro["seats"]] == ["", "Mitsu"], f"roster seeded from sign-up: {ro}")
r = c.post(f"/api/missions/{stem}/roster", json={"seat": "Viper 1-1", "name": "Bob"})
ok(r.status_code == 200 and r.json["seats"][0]["pilot"] == "Bob", "take seat in briefing room")
ok(c.post(f"/api/missions/{stem}/roster", json={"seat": "Viper 1-1", "name": "Eve"}).status_code == 409,
   "taken seat refused")
r = c.post(f"/api/missions/{stem}/roster", json={"seat": "Viper 1-2", "name": "", "me": "Mitsu"})
ok(r.status_code == 200 and r.json["seats"][1]["pilot"] == "", "leave seat")
with zipfile.ZipFile(f"{tmp}/out/{name}") as z:
    mission = z.read("mission").decode()
    ok('"Viper 1-1 (Bob)"' in mission and '"Viper 1-2"' in mission and "(Mitsu)" not in mission,
       "slot names rewritten in the .miz")
    ok(any(n.startswith("KNEEBOARD/") for n in z.namelist()), "rest of the .miz intact")
r = c.post("/api/reports", json={"mission": name, "errors": ["SCRIPTING (Main): boom"]})
ok(r.status_code == 200, "report")
missions = c.get("/api/missions").json
ok(missions[0]["report"]["errors"] == ["SCRIPTING (Main): boom"], "report listed")
hook = c.get("/dcs-hook.lua").data.decode()
ok('local APP_URL = "http://missions.local"' in hook, "hook has app url")
ok(c.put("/api/setups/My Night", json=cfg).status_code == 200, "save setup")
ok(c.get("/api/setups").json == ["My Night"], "list setups")
# Liveries: squadron liveries built in; the hook's scan of the server adds installed ones first.
lv = c.get("/api/liveries?aircraft=F-16C_50").json
ok(any(x["id"] == "IAF_101st_squadron" and not x["installed"] for x in lv["liveries"]), "squadron liveries")
r = c.post("/api/liveries", json={"types": {"F-16C_50": [{"id": "iaf_101st_squadron", "name": "IAF 101 Sqn"},
                                                      {"id": "my custom", "name": "Our skin"},
                                                      {"id": 'bad"id', "name": "x"}]}})
ok(r.status_code == 200 and r.json["liveries"] == 2, f"installed liveries {r.json}")
lv = c.get("/api/liveries?aircraft=F-16C_50").json
ok(lv["liveries"][0]["installed"] and lv["liveries"][0]["label"].startswith("IAF 101 Sqn")
   and sum(x["id"].lower() == "iaf_101st_squadron" for x in lv["liveries"]) == 1, f"merged {lv['liveries'][:3]}")
gen = {"theater": "caucasus", "mission_type": "cas", "srs": "srs.other.com:5010", "srs_note": "pw in #ops",
       "flights": [{"aircraft": "F-16C_50", "slots": 2, "livery": "my custom"},
                   {"aircraft": "FA-18C_hornet", "slots": 1, "livery": "no such skin"}]}
r = c.post("/api/generate", json=gen)
ok(r.status_code == 200, f"generate with livery {r.status_code} {r.json}")
gstem = r.json["filename"][:-4]
with zipfile.ZipFile(f"{tmp}/out/{r.json['filename']}") as z:
    mission = z.read("mission").decode()
ok(mission.count('["livery_id"]="my custom"') == 2, "livery on both F-16s")
ok(any("no such skin" in w for w in r.json["warnings"]), f"unknown livery warns {r.json['warnings']}")
ok(c.get(f"/api/missions/{gstem}/brief").json["srs"] == {"address": "srs.other.com:5010", "note": "pw in #ops"},
   "per-mission SRS in brief")
ok("srs.other.com:5010" in c.get(f"/missions/{gstem}/comms.txt").get_data(as_text=True), "per-mission SRS on comm card")
ok(c.post("/api/generate", json={**gen, "srs": "bad server!"}).status_code == 400, "bad SRS rejected")

# Temporary vs kept missions
from app import mission_store  # noqa: E402

r = c.post("/api/generate", json=cfg).json
tstem = r["filename"][:-4]
left = r["expires"] - datetime.datetime.now().timestamp()
ok(r["kept"] is False and left > 23 * 3600, f"new mission is temporary {r}")
ok(c.get(f"/api/events/{eid}").json["mission"] and mission_store.status(name[:-4])["kept"], "event mission kept")
ok(mission_store.status(stem)["kept"], "published mission kept")
ok(c.post(f"/api/missions/{tstem}/keep", json={"keep": True}).json["kept"], "keep")
ok(not c.post(f"/api/missions/{tstem}/keep", json={"keep": False}).json["kept"], "un-keep")
meta = OUTPUT_DIR_PATH / f"{tstem}.meta.json"
meta.write_text(json.dumps({"created": 0, "expires": 1}), encoding="utf-8")
c.post(f"/api/missions/{tstem}/roster", json={"seat": "Viper 1-1", "name": "Mitsu"})
ok(tstem in mission_store.cleanup(force=True), "expired mission cleaned up")
ok(not list(OUTPUT_DIR_PATH.glob(f"{tstem}.*")), f"all its files gone {list(OUTPUT_DIR_PATH.glob(f'{tstem}.*'))}")
ok(c.get(f"/briefing/{tstem}").status_code == 404, "briefing gone with it")
ok(any(m["stem"] == stem and m["kept"] for m in c.get("/api/missions").json), "list shows kept")
legacy = c.post("/api/generate", json=cfg).json["filename"][:-4]
(OUTPUT_DIR_PATH / f"{legacy}.meta.json").unlink()
ok(mission_store.status(legacy)["kept"], "missions from before count as kept")
ok(c.delete(f"/api/missions/{legacy}").status_code == 200 and not list(OUTPUT_DIR_PATH.glob(f"{legacy}.*")),
   "delete removes everything")
# Windows can't delete a file that's being downloaded: keep the meta file so cleanup tries again.
busy = c.post("/api/generate", json=cfg).json["filename"][:-4]
(OUTPUT_DIR_PATH / f"{busy}.meta.json").write_text(json.dumps({"created": 0, "expires": 1}), encoding="utf-8")
real_unlink = pathlib.Path.unlink


def in_use(self, missing_ok=False):
    if self.suffix == ".miz":
        raise PermissionError("in use")
    real_unlink(self, missing_ok=missing_ok)


pathlib.Path.unlink = in_use
ok(busy not in mission_store.cleanup(force=True) and (OUTPUT_DIR_PATH / f"{busy}.meta.json").exists(),
   "file in use: mission stays queued for cleanup")
ok(c.delete(f"/api/missions/{busy}").status_code == 409, "file in use: delete says so")
pathlib.Path.unlink = real_unlink
ok(busy in mission_store.cleanup(force=True) and not list(OUTPUT_DIR_PATH.glob(f"{busy}.*")),
   "file free again: cleaned up")

# Weekly events: once the date has passed, the next occurrence exists, on the same weekday and time.
r = c.post("/api/events", json={"title": "Weekly", "config": cfg, "repeat": "weekly"})
ok(r.status_code == 400, "repeating event needs a date")
posts = len(got)
r = c.post("/api/events", json={"title": "Weekly", "config": cfg, "repeat": "weekly", "discord": True,
                                "when_iso": "2020-01-03T19:00:00Z"})
wid = r.json["id"]
c.post(f"/api/events/{wid}/claim", json={"seat": "Viper 1-1", "name": "Mitsu"})
ev = c.get(f"/api/events/{wid}").json
nxt = c.get(f"/api/events/{ev.get('next_id')}").json if ev.get("next_id") else {}
when = datetime.datetime.fromisoformat(nxt.get("when_iso", "2000-01-01T00:00:00+00:00"))
ok(when > datetime.datetime.now(datetime.UTC) and when.weekday() == 4 and when.hour == 19,
   f"next occurrence {nxt.get('when_iso')}")
ok(nxt.get("prev_id") == wid and not nxt.get("claims") and nxt.get("repeat") == "weekly", "next occurrence is fresh")
ok(c.get(f"/api/events/{wid}").json["next_id"] == nxt["id"], "rolled over once")
ok(len(got) == posts + 2, f"both occurrences announced on Discord ({len(got) - posts})")
for e in (wid, nxt["id"]):
    c.delete(f"/api/events/{e}")

# Optional password: the builder and admin actions need it, what pilots use doesn't.
os.environ["APP_PASSWORD"] = "hunter2"
basic = {"Authorization": "Basic " + base64.b64encode(b"x:hunter2").decode()}
wrong = {"Authorization": "Basic " + base64.b64encode(b"x:nope").decode()}
r = c.get("/")
ok(r.status_code == 401 and "Basic" in r.headers.get("WWW-Authenticate", ""), "builder needs password")
ok(c.get("/", headers=wrong).status_code == 401, "wrong password refused")
ok(c.get("/", headers=basic).status_code == 200, "right password works")
ok(c.post("/api/generate", json=cfg).status_code == 401, "generate needs password")
ok(c.delete(f"/api/events/{eid}").status_code == 401, "delete event needs password")
for url in [f"/briefing/{stem}", f"/api/missions/{stem}/brief", f"/e/{eid}", f"/api/events/{eid}", "/healthz",
            f"/missions/{stem}/kneeboard/1.png", f"/missions/{name}", "/api/options"]:
    ok(c.get(url).status_code == 200, f"public without password: {url}")
ok(c.post("/api/debrief", json={"mission": f"{stem}.miz", "events": []}).status_code == 200, "hook stays open")
del os.environ["APP_PASSWORD"]
ok(c.get("/").headers.get("X-Content-Type-Options") == "nosniff", "security headers")

# .env for python -m app (Windows): Notepad's BOM, comments, quotes, Windows paths; the environment wins.
from app.__main__ import load_env  # noqa: E402

env_file = pathlib.Path(tmp) / ".env"
env_file.write_text('\ufeffDMM_T1=C:\\Users\\dcs\\Saved Games\\DCS.server\\Missions\n# DMM_T2=no\n'
                    'DMM_T3="quoted value"\nDMM_T4=from file\n\n', encoding="utf-8")
os.environ["DMM_T4"] = "from env"
load_env(env_file)
ok(os.environ.get("DMM_T1") == "C:\\Users\\dcs\\Saved Games\\DCS.server\\Missions", ".env: Windows path")
ok("DMM_T2" not in os.environ and os.environ.get("DMM_T3") == "quoted value", ".env: comments, quotes")
ok(os.environ["DMM_T4"] == "from env", ".env: environment wins")
load_env(pathlib.Path(tmp) / "missing.env")

# Settings page: secrets never sent back; changes only from this PC (or with the password);
# settings from the environment are locked; saved values apply at once.
from app import settings  # noqa: E402

view = c.get("/api/settings").json
by_key = {f["key"]: f for f in view["fields"]}
ok(view["can_edit"] and by_key["DISCORD_WEBHOOK_URL"] == {**by_key["DISCORD_WEBHOOK_URL"], "set": True, "locked": True}
   and "value" not in by_key["DISCORD_WEBHOOK_URL"], "settings: secrets only say they're set")
ok(c.put("/api/settings", json={"SRS_NOTE": "x"}, environ_base={"REMOTE_ADDR": "10.0.0.5"}).status_code == 403,
   "settings: other PCs can't change them without a password")
ok(c.put("/api/settings", json={"SRS_NOTE": "x"}, headers={"Host": "evil.example:8080"}).status_code == 403,
   "settings: a page rebinding its domain to 127.0.0.1 can't change them")
r = c.put("/api/settings", json={"DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/1/x", "PORT": "99999",
                                 "PUBLIC_URL": "ftp://x", "NOPE": "1", "SRS_NOTE": "a\nb"})
ok(r.status_code == 400 and set(r.json["errors"]) == {"DISCORD_WEBHOOK_URL", "PORT", "PUBLIC_URL", "NOPE", "SRS_NOTE"},
   f"settings: validation and locked keys {r.json}")
ok(not settings.path().exists(), "settings: nothing saved when anything is wrong")
r = c.put("/api/settings", json={"SRS_ADDRESS": "srs.saved.net:5002", "SFTP_PASSWORD": "s3cret",
                                 "SFTP_KEY_FILE": str(env_file)})
ok(r.status_code == 200 and os.environ["SRS_ADDRESS"] == "srs.saved.net:5002", "settings: saved and applied")
ok("s3cret" not in r.get_data(as_text=True) and os.environ["SFTP_PASSWORD"] == "s3cret", "settings: secret kept")
ok(c.get("/api/options").json["integrations"]["srs"]["address"] == "srs.saved.net:5002", "settings: used by the app")
c.put("/api/settings", json={"SFTP_PASSWORD": "", "SRS_ADDRESS": ""})
saved = json.loads(settings.path().read_text(encoding="utf-8"))
ok("SFTP_PASSWORD" not in os.environ and "SRS_ADDRESS" not in saved, "settings: cleared")
ok(c.get("/healthz").json["app"] == "dcs-mission-maker", "healthz names the app (single-instance check)")
os.environ["APP_PASSWORD"] = "pw2"
ok(c.put("/api/settings", json={"SRS_NOTE": "x"}).status_code == 401, "settings: password asked when set")
ok(c.put("/api/settings", json={"SRS_NOTE": "remote ok"}, environ_base={"REMOTE_ADDR": "10.0.0.5"},
         headers={"Authorization": "Basic " + base64.b64encode(b"x:pw2").decode()}).status_code == 200,
   "settings: other PCs can with the password")
os.environ.pop("APP_PASSWORD", None)  # saving re-applied settings.json, which has none

# Update check: off without a release repository; shows only a newer, well-formed release.
from app import updates  # noqa: E402

ok(c.get("/api/update").json == {"enabled": False, "current": updates.__version__, "available": None},
   "update check off in source/Docker builds")
ok(updates.version_tuple("v1.10.0") > updates.version_tuple("1.9.3") and updates.version_tuple("1.2") is None,
   "version compare")
updates.REPO = "squadron/dcs-mission-maker"
release = {"tag_name": "v99.0.0", "html_url": "https://github.com/squadron/dcs-mission-maker/releases/tag/v99.0.0"}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


real_urlopen = updates.urllib.request.urlopen
updates.urllib.request.urlopen = lambda req, timeout=0: FakeResponse(json.dumps(release).encode())
c.get("/api/update")  # starts the background check
for t in [t for t in threading.enumerate() if t.name == "update-check"]:
    t.join(5)
u = c.get("/api/update").json
ok(u["available"] == {"version": "99.0.0", "url": release["html_url"]}, f"newer release shown {u}")
os.environ["UPDATE_CHECK"] = "off"
ok(c.get("/api/update").json["available"] is None, "update check can be turned off")
del os.environ["UPDATE_CHECK"]
release.update(tag_name="v0.0.1", html_url="https://github.com/squadron/dcs-mission-maker/releases/tag/v0.0.1")
updates._state["checked"] = 0
updates._check()
ok(c.get("/api/update").json["available"] is None, "older release not shown")
release.update(tag_name="v99.0.0", html_url="https://evil.example/download")
updates._check()
ok(updates._state["latest"]["version"] == "0.0.1", "release pointing elsewhere ignored")
updates.urllib.request.urlopen = real_urlopen
updates.REPO = ""
r = c.put("/api/settings", json={"UPDATE_CHECK": "maybe"})
ok(r.status_code == 400 and "UPDATE_CHECK" in r.json["errors"], "update switch validated")

# Kneeboards edited in the Briefing Room: only pilots with a seat in that aircraft type; pages
# hidden, moved, added (notes, PNG/JPG/PDF uploads), deleted and reset; the squadron library.
from PIL import Image  # noqa: E402

from app import kneeboard_store  # noqa: E402

kb_cfg = {"theater": "caucasus", "mission_type": "cas", "time_of_day": "night",
          "flights": [{"aircraft": "F-16C_50", "slots": 2, "callsign": "Viper", "number": 1},
                      {"aircraft": "FA-18C_hornet", "slots": 1, "callsign": "Hornet", "number": 2}]}
kb_stem = c.post("/api/generate", json=kb_cfg).json["filename"][:-4]
kb_api = f"/api/missions/{kb_stem}/kneeboards"


def miz_pages(stem, type_id):
    with zipfile.ZipFile(OUTPUT_DIR_PATH / f"{stem}.miz") as z:
        return sorted(n.rsplit("/", 1)[1] for n in z.namelist() if n.startswith(f"KNEEBOARD/{type_id}/IMAGES/"))


def png(color, size=(600, 800), fmt="PNG"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, fmt)
    return buf.getvalue()


view = c.get(kb_api).json
viper = next(t for t in view["types"] if t["type"] == "F-16C_50")
ok([p["label"] for p in viper["pages"]] == ["Viper 1 · Flight", "Viper 1 · Route"] and viper["flights"] == ["Viper 1"],
   f"kneeboard view {viper}")
ok(not kneeboard_store.state_path(kb_stem).exists(), "viewing writes nothing")
ok(c.get(f"/missions/{kb_stem}/kb/g:kneeboard_1_route.png").status_code == 200, "page image before any edit")
arr = {"action": "arrange", "name": "Mitsu",
       "order": [{"id": "g:kneeboard_1_route"}, {"id": "g:kneeboard_1", "hidden": True}]}
ok(c.post(f"{kb_api}/F-16C_50", json=arr).status_code == 403, "kneeboard: not on the roster, no edits")
seat = next(st for st in c.get(f"/api/missions/{kb_stem}/roster").json["seats"] if st["flight"] == "Viper 1")
c.post(f"/api/missions/{kb_stem}/roster", json={"seat": seat["seat"], "name": "Mitsu", "me": "Mitsu"})
ok(c.post(f"{kb_api}/FA-18C_hornet", json={**arr, "order": []}).status_code == 403,
   "kneeboard: a seat in another aircraft doesn't count")
# Published to the server folder earlier: edits update that copy.
server_copy = pathlib.Path(os.environ["SERVER_MISSIONS_DIR"]) / f"{kb_stem}.miz"
server_copy.write_bytes((OUTPUT_DIR_PATH / f"{kb_stem}.miz").read_bytes())
r = c.post(f"{kb_api}/F-16C_50", json=arr)
ok(r.status_code == 200 and miz_pages(kb_stem, "F-16C_50") == ["01_kneeboard_1_route.png"],
   f"kneeboard: reordered and hidden in the .miz {r.json} {miz_pages(kb_stem, 'F-16C_50')}")
ok(miz_pages(kb_stem, "FA-18C_hornet") == ["01_kneeboard_2.png", "02_kneeboard_2_route.png"],
   "other aircraft untouched")
ok(server_copy.read_bytes() == (OUTPUT_DIR_PATH / f"{kb_stem}.miz").read_bytes(), "kneeboard: server copy updated")
ok(c.get(f"/missions/{kb_stem}/kneeboard/1.png").status_code == 200, "hidden page still viewable (My flight tab)")
bad = c.post(f"{kb_api}/F-16C_50", json={**arr, "order": arr["order"][:1]})
ok(bad.status_code == 400, "arrange must list every page")
r = c.post(f"{kb_api}/F-16C_50", json={"action": "notes", "name": "mitsu", "title": "Game plan",
                                        "text": "PUSH\nPush at 0130 on 251.000.\nRTB if winchester."})
notes = next(p for t in r.json["types"] if t["type"] == "F-16C_50" for p in t["pages"] if p["kind"] == "notes")
ok(r.status_code == 200 and notes["by"] == "Mitsu" and notes["label"] == "Game plan", f"notes page {r.json}")
night_px = Image.open(io.BytesIO(c.get(f"/missions/{kb_stem}/kb/{notes['id']}.png").data)).getpixel((5, 5))
ok(sum(night_px[:3]) < 120, f"notes page is dark at night {night_px}")
pdf = io.BytesIO()
Image.new("RGB", (612, 792), "white").save(pdf, "PDF", save_all=True,
                                           append_images=[Image.new("RGB", (612, 792), "gray")])
r = c.post(f"{kb_api}/F-16C_50/upload", content_type="multipart/form-data", data={
    "name": "Mitsu", "library": "1",
    "files": [(io.BytesIO(png("red")), "Startup checklist.png"), (io.BytesIO(png("blue", fmt="JPEG")), "chart.jpg"),
              (io.BytesIO(pdf.getvalue()), "Ramp start.pdf")]})
pages = next(t for t in r.json["types"] if t["type"] == "F-16C_50")["pages"] if r.status_code == 200 else []
ok([p["label"] for p in pages if p["kind"] == "upload"]
   == ["Startup checklist", "chart", "Ramp start (1/2)", "Ramp start (2/2)"], f"uploads {r.status_code} {r.json}")
ok(len(miz_pages(kb_stem, "F-16C_50")) == 6, f"uploads in the .miz {miz_pages(kb_stem, 'F-16C_50')}")
ok(len(kneeboard_store.library("F-16C_50")) == 4, "uploads saved to the squadron library")
up = next(p for p in pages if p["label"] == "chart")
img = Image.open(io.BytesIO(c.get(f"/missions/{kb_stem}/kb/{up['id']}.png").data))
ok(img.format == "PNG" and img.size == (600, 800), f"uploads re-encoded as PNG {img.format} {img.size}")
for junk, why in [(b"<html><script>alert(1)</script>", "not an image"), (b"%PDF-1.7 broken", "broken PDF")]:
    r = c.post(f"{kb_api}/F-16C_50/upload", content_type="multipart/form-data",
               data={"name": "Mitsu", "files": [(io.BytesIO(junk), "evil.png")]})
    ok(r.status_code == 400 and "evil.png" in r.json["error"], f"upload refused: {why} {r.json}")
ok(c.post(f"{kb_api}/F-16C_50", json={"action": "delete", "name": "Mitsu", "id": "g:kneeboard_1"}).status_code == 400,
   "generated pages can only be hidden")
r = c.post(f"{kb_api}/F-16C_50", json={"action": "delete", "name": "Mitsu", "id": up["id"]})
ok(r.status_code == 200 and len(miz_pages(kb_stem, "F-16C_50")) == 5, "uploaded page deleted")
r = c.post(f"{kb_api}/F-16C_50", json={"action": "reset", "name": "Mitsu"})
ok(miz_pages(kb_stem, "F-16C_50") == ["01_kneeboard_1.png", "02_kneeboard_1_route.png"]
   and len(list(kneeboard_store.pages_dir(kb_stem).glob("u_*"))) == 0, "reset to the original pages")
ok(any("reset" in entry["what"] for entry in r.json["log"]) and r.json["log"][0]["by"] == "Mitsu", "changes logged")
# A new mission with that aircraft gets the library pages; they can be hidden there.
new = c.post("/api/generate", json=kb_cfg).json["filename"][:-4]
ok(len(miz_pages(new, "F-16C_50")) == 6 and len(miz_pages(new, "FA-18C_hornet")) == 2,
   f"library pages in new missions {miz_pages(new, 'F-16C_50')}")
lib_id = kneeboard_store.library("F-16C_50")[0]["id"]
r = c.post(f"{kb_api}/F-16C_50", json={"action": "unlibrary", "name": "Mitsu", "id": lib_id})
ok(r.status_code == 200 and len(kneeboard_store.library("F-16C_50")) == 3 and len(miz_pages(new, "F-16C_50")) == 6,
   "removed from the library; missions keep their copy")
ok(mission_store.delete(kb_stem) and not kneeboard_store.pages_dir(kb_stem).exists(),
   "deleting a mission removes its pages")

# Maps installed on the DCS server's PC: only those are offered and generated.
from app import dcs_install  # noqa: E402
from app.theaters import THEATERS  # noqa: E402

ok({k: t.terrain_cls().miz_theatre_name for k, t in THEATERS.items()} == dcs_install.DCS_NAMES,
   "DCS map folder names match pydcs")
ok(all(t["allowed"] for t in c.get("/api/options").json["theaters"]), "no DCS install: every map offered")
dcs = pathlib.Path(tmp) / "DCS World Server"
for folder in ("Caucasus", "SinaiMap", "SomeModMap"):
    (dcs / "Mods" / "terrains" / folder).mkdir(parents=True)
os.environ["DCS_INSTALL_DIR"] = str(dcs)
opts = c.get("/api/options").json
ok(sorted(t["key"] for t in opts["theaters"] if t["allowed"]) == ["caucasus", "sinai"]
   and opts["installed_maps"]["filter"], f"only installed maps offered {opts['installed_maps']}")
r = c.post("/api/generate", json={**cfg, "theater": "syria"})
ok(r.status_code == 400 and "isn't installed" in r.json["error"], f"map not installed refused {r.json}")
ok(c.post("/api/generate", json=cfg).status_code == 200, "installed map still builds")
os.environ["MAPS_FILTER"] = "off"
ok(all(t["allowed"] for t in c.get("/api/options").json["theaters"]), "map check can be turned off")
del os.environ["MAPS_FILTER"]
r = c.put("/api/settings", json={"DCS_INSTALL_DIR": tmp})
ok(r.status_code == 400 and "Mods" in r.json["errors"]["DCS_INSTALL_DIR"], "DCS install folder checked")
os.environ.pop("DCS_INSTALL_DIR", None)

print(f"api checks done, {len(fails)} failures")
sys.exit(1 if fails else 0)
