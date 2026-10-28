"""Settings changed on the Settings page, stored in settings.json in the missions folder.

Every setting is also an environment variable of the same name, and the rest of the app
reads them from os.environ. Values set in the environment when the app starts (Docker's
.env, or .env in the project) win over settings.json and show as locked on the page.
Saved changes apply straight away (other gunicorn workers pick them up on their next
request); PORT needs a restart. Secrets are never sent back to the browser.
"""
import json
import os
import re
from pathlib import Path

from . import paths

# key: (group, label, kind, help). Kinds: text, url, folder, file, number, secret.
FIELDS = {
    "PUBLIC_URL": ("General", "Public address", "url",
                   "How your friends reach this app, e.g. http://203.0.113.5:8080. "
                   "Used in sign-up links, Discord posts and the DCS server hook."),
    "APP_PASSWORD": ("General", "Builder password", "secret",
                     "Asked for on the builder and anything that generates, publishes or deletes. "
                     "Sign-ups, Briefing Rooms and downloads stay open. Set it if the app is reachable "
                     "from the internet."),
    "MISSION_TTL_HOURS": ("General", "Keep unsaved missions for (hours)", "number",
                          "Missions nobody pressed Keep on are deleted after this. Default 24."),
    "PORT": ("General", "Port", "number", "Default 8080. Restart the app to apply."),
    "SERVER_MISSIONS_DIR": ("DCS server", "Server Missions folder", "folder",
                            "Copy to server puts missions here, e.g. "
                            "C:\\Users\\dcs\\Saved Games\\DCS.server\\Missions."),
    "SRS_ADDRESS": ("DCS server", "SRS server", "text",
                    "Your usual SRS voice server, e.g. srs.example.com:5002. The default for each mission."),
    "SRS_NOTE": ("DCS server", "SRS note", "text",
                 "e.g. \"password in #dcs-info\". Never the password itself."),
    "DISCORD_WEBHOOK_URL": ("Discord", "Discord webhook", "secret",
                            "Server Settings > Integrations > Webhooks > New Webhook > Copy URL."),
    "SFTP_HOST": ("Remote server (SFTP)", "Host", "text", "Upload missions to a server elsewhere."),
    "SFTP_PORT": ("Remote server (SFTP)", "Port", "number", "Default 22."),
    "SFTP_USER": ("Remote server (SFTP)", "User", "text", ""),
    "SFTP_PASSWORD": ("Remote server (SFTP)", "Password", "secret", "Or use a key file."),
    "SFTP_KEY_FILE": ("Remote server (SFTP)", "Key file", "file", "Path to a private key on this PC."),
    "SFTP_KNOWN_HOSTS": ("Remote server (SFTP)", "Known hosts file", "file",
                         "Optional: verifies the server's key."),
    "SFTP_PATH": ("Remote server (SFTP)", "Missions folder on the server", "text",
                  "e.g. C:/Users/dcs/Saved Games/DCS.server/Missions"),
}

# Shown in empty fields: what the app uses when a setting isn't set.
DEFAULTS = {"MISSION_TTL_HOURS": "24", "PORT": "8080", "SFTP_PORT": "22", "SRS_ADDRESS": "srs.example.com:5002"}

# Set in the environment when the app started: these win and can't be changed here.
LOCKED = {k for k in FIELDS if os.environ.get(k, "").strip()}
_loaded = [None]  # mtime of the settings.json last applied


def path():
    return paths.output_dir() / "settings.json"


def _read():
    try:
        data = json.loads(path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: str(v) for k, v in data.items() if k in FIELDS} if isinstance(data, dict) else {}


def refresh():
    """Applies settings.json to os.environ if it changed since last time. Cheap: one stat."""
    try:
        mtime = path().stat().st_mtime_ns
    except OSError:
        mtime = 0
    if mtime == _loaded[0]:
        return
    _loaded[0] = mtime
    saved = _read()
    for key in FIELDS.keys() - LOCKED:
        if saved.get(key):
            os.environ[key] = saved[key]
        else:
            os.environ.pop(key, None)


def view():
    """What the Settings page shows: values, except secrets, which only say whether they're set."""
    fields = []
    for key, (group, label, kind, help_text) in FIELDS.items():
        value = os.environ.get(key, "")
        f = {"key": key, "group": group, "label": label, "kind": kind, "help": help_text,
             "locked": key in LOCKED, "placeholder": DEFAULTS.get(key, "")}
        if kind == "secret":
            f["set"] = bool(value)
        else:
            f["value"] = value
        fields.append(f)
    return {"fields": fields, "suggestions": {"SERVER_MISSIONS_DIR": mission_folders()},
            "data_dir": str(paths.data_dir()), "missions_dir": str(paths.output_dir())}


def mission_folders():
    """DCS Missions folders found under this PC's Saved Games (server and client installs)."""
    saved_games = Path.home() / "Saved Games"
    try:
        return sorted(str(p) for p in saved_games.glob("DCS*/Missions") if p.is_dir())
    except OSError:
        return []


def _check(key, value):
    """Returns an error message, or None. Value is already stripped and non-empty."""
    kind = FIELDS[key][2]
    if len(value) > 500 or re.search(r"[\x00-\x1f]", value):
        return "Too long, or has line breaks."
    if kind == "url" and not re.fullmatch(r"https?://[^\s/]+(/\S*)?", value):
        return "Should start with http:// or https://"
    if key == "DISCORD_WEBHOOK_URL" and not re.fullmatch(
            r"https://(discord|discordapp|canary\.discord|ptb\.discord)\.com/api/webhooks/\S+", value):
        return "Should be a Discord webhook URL (https://discord.com/api/webhooks/...)."
    if kind == "number":
        try:
            n = float(value)
        except ValueError:
            return "Should be a number."
        if key in ("PORT", "SFTP_PORT") and not (n.is_integer() and 1 <= n <= 65535):
            return "Should be a port number (1-65535)."
        if key == "MISSION_TTL_HOURS" and n < 0.25:
            return "At least 0.25 hours."
    if kind == "folder" and not Path(value).is_dir():
        return "That folder doesn't exist on this PC."
    if kind == "file" and not Path(value).is_file():
        return "That file doesn't exist on this PC."
    if key == "SRS_ADDRESS" and not re.fullmatch(r"[\w.\-:\[\]]{1,100}", value):
        return "Should look like srs.example.com:5002"
    return None


def save(changes):
    """Applies {key: value} from the Settings page; secrets left out stay as they are, and
    "" clears a setting. Returns {key: error} (nothing saved) or {} when saved."""
    if not isinstance(changes, dict):
        return {"": "Expected an object."}
    errors, clean = {}, {}
    for key, value in changes.items():
        if key not in FIELDS:
            errors[key] = "Unknown setting."
        elif key in LOCKED:
            errors[key] = "Set in the environment (.env), so it can't be changed here."
        else:
            value = str(value if value is not None else "").strip()
            error = value and _check(key, value)
            if error:
                errors[key] = error
            else:
                clean[key] = value
    if errors:
        return errors
    saved = _read()
    saved.update(clean)
    saved = {k: v for k, v in saved.items() if v}
    tmp = path().with_suffix(".json.tmp")
    tmp.write_text(json.dumps(saved, indent=1), encoding="utf-8")
    os.replace(tmp, path())
    _loaded[0] = None
    refresh()
    return {}
