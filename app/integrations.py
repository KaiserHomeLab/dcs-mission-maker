"""Discord webhook posts and publishing missions to a DCS server.

Configured with environment variables (see .env.example):
  DISCORD_WEBHOOK_URL      post briefings + the .miz to a Discord channel
  PUBLIC_URL               how friends reach this app (for sign-up links)
  SERVER_MISSIONS_DIR      a folder mounted into the container (local/SMB/NFS server)
  SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASSWORD or SFTP_KEY_FILE, SFTP_PATH,
  SFTP_KNOWN_HOSTS (optional: verify the server's host key)
"""
import io
import json
import os
import shutil
import urllib.error
import urllib.request
import uuid
from pathlib import Path

MAX_DISCORD_FILE = 10 * 1024 * 1024


def env(name):
    return os.environ.get(name, "").strip()


def status():
    return {
        "discord": bool(env("DISCORD_WEBHOOK_URL")),
        "folder": bool(env("SERVER_MISSIONS_HOST_DIR") and env("SERVER_MISSIONS_DIR"))
                  and Path(env("SERVER_MISSIONS_DIR")).is_dir(),
        "sftp": bool(env("SFTP_HOST") and env("SFTP_USER")),
        "public_url": env("PUBLIC_URL").rstrip("/"),
        "srs": srs(),
    }


def srs():
    """The group's SRS voice server, if set: {"address", "note"} or None. Never the password."""
    address = env("SRS_ADDRESS").strip()
    return {"address": address, "note": env("SRS_NOTE").strip()} if address else None


# ------------------------------------------------------------------ Discord
def _multipart(fields, files):
    boundary = uuid.uuid4().hex
    buf = io.BytesIO()
    for name, value in fields.items():
        buf.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n"
                  "Content-Type: application/json\r\n\r\n".encode())
        buf.write(value.encode() + b"\r\n")
    for i, (filename, data, ctype) in enumerate(files):
        buf.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"files[{i}]\"; "
                  f"filename=\"{filename}\"\r\nContent-Type: {ctype}\r\n\r\n".encode())
        buf.write(data + b"\r\n")
    buf.write(f"--{boundary}--\r\n".encode())
    return buf.getvalue(), f"multipart/form-data; boundary={boundary}"


def post_discord(title, description, fields=(), files=(), url=None, image_name=None):
    """files: [(filename, bytes, content_type)]. Returns None or an error string."""
    hook = env("DISCORD_WEBHOOK_URL")
    if not hook:
        return "Discord isn't configured (DISCORD_WEBHOOK_URL)."
    embed = {"title": title[:256], "description": description[:4000], "color": 0xE0A526,
             "fields": [{"name": n[:256], "value": v[:1024] or "-", "inline": inline}
                        for n, v, inline in fields][:20]}
    if url:
        embed["url"] = url
    if image_name:
        embed["image"] = {"url": f"attachment://{image_name}"}
    files = [f for f in files if len(f[1]) <= MAX_DISCORD_FILE]
    body, ctype = _multipart({"payload_json": json.dumps(
        {"username": "DCS Mission Maker", "embeds": [embed]})}, files)
    req = urllib.request.Request(hook, data=body, method="POST",
                                 headers={"Content-Type": ctype, "User-Agent": "DCSMissionMaker"})
    try:
        with urllib.request.urlopen(req, timeout=30):
            return None
    except urllib.error.HTTPError as e:
        return f"Discord said {e.code}: {e.read()[:200].decode(errors='replace')}"
    except OSError as e:
        return f"Couldn't reach Discord: {e}"


# ---------------------------------------------------------------- publishing
def publish_folder(src: Path):
    dest_dir = env("SERVER_MISSIONS_DIR")
    if not dest_dir or not Path(dest_dir).is_dir():
        return "Server folder isn't configured or isn't mounted (SERVER_MISSIONS_DIR)."
    try:
        shutil.copyfile(src, Path(dest_dir) / src.name)
    except OSError as e:
        return f"Copy failed: {e}"
    return None


def publish_sftp(src: Path):
    if not (env("SFTP_HOST") and env("SFTP_USER")):
        return "SFTP isn't configured (SFTP_HOST, SFTP_USER)."
    try:
        import paramiko
    except ImportError:
        return "paramiko isn't installed."
    try:
        transport = paramiko.Transport((env("SFTP_HOST"), int(env("SFTP_PORT") or 22)))
        key = None
        if env("SFTP_KEY_FILE"):
            key = paramiko.RSAKey.from_private_key_file(env("SFTP_KEY_FILE"))
        hostkey = None
        if env("SFTP_KNOWN_HOSTS"):
            known = paramiko.HostKeys(env("SFTP_KNOWN_HOSTS")).lookup(env("SFTP_HOST")) or {}
            hostkey = next(iter(known.values()), None)
            if hostkey is None:
                return f"{env('SFTP_HOST')} isn't in {env('SFTP_KNOWN_HOSTS')}."
        transport.connect(hostkey=hostkey, username=env("SFTP_USER"),
                          password=env("SFTP_PASSWORD") or None, pkey=key)
        with paramiko.SFTPClient.from_transport(transport) as sftp:
            remote = (env("SFTP_PATH") or ".").rstrip("/") + "/" + src.name
            sftp.put(str(src), remote)
        transport.close()
    except Exception as e:  # noqa: BLE001 - surface any network/auth error to the user
        return f"SFTP upload failed: {e}"
    return None
