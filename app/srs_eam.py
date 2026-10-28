"""Optional: new SRS External AWACS Mode (EAM) passwords each time a mission is published.

SRS reads server.cfg only when it starts. With SRS_EAM_ROTATE=on, copying a mission to the
server folder (server.publish) then:
  1. makes random blue and red passwords,
  2. stops SRS through its Windows scheduled task (SRS_TASK_NAME) and waits until it has exited,
  3. sets EXTERNAL_AWACS_MODE_BLUE_PASSWORD and _RED_PASSWORD in the [External AWACS Mode
     Settings] section of SRS_CONFIG_PATH, leaving every other byte of the file as it was
     (the previous file is kept as server.cfg.dmm-backup),
  4. starts the task again, even when step 3 failed.
If SRS can't be stopped, nothing is changed. The passwords are kept in srs_eam.json in the
missions folder with the mission they were made for; only that mission's Briefing Room shows
them. Restarting SRS drops everyone on it for a few seconds, so it never happens on kneeboard
or roster changes. Windows only, on the PC running SRS.
"""
import json
import os
import re
import secrets
import subprocess
import threading
import time
from pathlib import Path

from . import paths

SECTION = "External AWACS Mode Settings"
KEYS = {"blue": "EXTERNAL_AWACS_MODE_BLUE_PASSWORD", "red": "EXTERNAL_AWACS_MODE_RED_PASSWORD"}
# No look-alikes (0/O, 1/l/I) and nothing SRS's config format treats specially (#, ;, quotes, =).
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
PASSWORD_LENGTH = 12
BOM = b"\xef\xbb\xbf"
ON_WINDOWS = os.name == "nt"
_lock = threading.Lock()


def enabled():
    return os.environ.get("SRS_EAM_ROTATE", "off").lower() == "on"


def new_password():
    return "".join(secrets.choice(ALPHABET) for _ in range(PASSWORD_LENGTH))


# ------------------------------------------------------------------ server.cfg
def edit_cfg(text, passwords):
    """server.cfg text with the EAM password keys set; everything else unchanged.
    passwords: {"blue": ..., "red": ...}. Adds the keys, or the section, if missing."""
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(newline)
    header = re.compile(r"\s*\[(.*)\]\s*")
    start = next((i for i, line in enumerate(lines)
                  if (m := header.fullmatch(line)) and m.group(1).strip().lower() == SECTION.lower()), None)
    wanted = {KEYS[side]: value for side, value in passwords.items()}
    if start is None:  # appended; the text before it stays exactly as it was
        body = newline.join([f"[{SECTION}]"] + [f"{k}={v}" for k, v in wanted.items()]) + newline
        if not text.strip():
            return text + body
        return text + ("" if text.endswith(newline) else newline) + newline + body
    end = next((i for i in range(start + 1, len(lines)) if header.fullmatch(lines[i])), len(lines))
    seen = set()
    for i in range(start + 1, end):
        m = re.fullmatch(r"(\s*)([^=\s]+)(\s*=\s*)(.*)", lines[i])
        if m and m.group(2) in wanted:
            lines[i] = f"{m.group(1)}{m.group(2)}{m.group(3)}{wanted[m.group(2)]}"
            seen.add(m.group(2))
    missing = [f"{k}={v}" for k, v in wanted.items() if k not in seen]
    if missing:
        last = max((i for i in range(start, end) if lines[i].strip()), default=start)
        lines[last + 1:last + 1] = missing
    return newline.join(lines)


def write_passwords(cfg, passwords):
    """Edits the file in place: same encoding (UTF-8, with or without a BOM) and line endings."""
    raw = cfg.read_bytes()
    bom = raw.startswith(BOM)
    text = raw[len(BOM):].decode("utf-8") if bom else raw.decode("utf-8")
    new = (BOM if bom else b"") + edit_cfg(text, passwords).encode("utf-8")
    cfg.with_name(cfg.name + ".dmm-backup").write_bytes(raw)
    tmp = cfg.with_name(cfg.name + ".dmm-tmp")
    tmp.write_bytes(new)
    tmp.replace(cfg)


# ------------------------------------------------------------------ the scheduled task
# The task name and SRS folder reach PowerShell through environment variables, never the script text.
_FIND = r"""
$ErrorActionPreference = 'Stop'
try {
  $name = $env:DMM_SRS_TASK
  if ($name.Contains('\')) {
    $path = $name.Substring(0, $name.LastIndexOf('\') + 1); $name = $name.Substring($name.LastIndexOf('\') + 1)
    $find = { Get-ScheduledTask -TaskName $name -TaskPath $path }
  } else { $find = { Get-ScheduledTask -TaskName $name | Select-Object -First 1 } }
  $task = & $find
"""
_STOP = _FIND + r"""
  Stop-ScheduledTask -InputObject $task
  foreach ($i in 1..60) {
    $left = Get-Process | Where-Object { $_.Path -and ((Split-Path $_.Path) -eq $env:DMM_SRS_DIR) }
    if ((& $find).State -ne 'Running' -and -not $left) { exit 0 }
    Start-Sleep -Milliseconds 500
  }
  Write-Output 'SRS is still running 30 s after stopping its task (does the task start SRS through a script?)'
  exit 3
} catch { Write-Output $_.Exception.Message; exit 1 }
"""
_START = _FIND + r"""
  Start-ScheduledTask -InputObject $task
  foreach ($i in 1..20) { if ((& $find).State -eq 'Running') { exit 0 }; Start-Sleep -Milliseconds 500 }
  Write-Output 'the task did not start'
  exit 4
} catch { Write-Output $_.Exception.Message; exit 1 }
"""


def _task(action, task_name, srs_dir):
    """Stops or starts the SRS task. Returns None, or what went wrong."""
    script = _STOP if action == "stop" else _START
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                           env={**os.environ, "DMM_SRS_TASK": task_name, "DMM_SRS_DIR": str(srs_dir)},
                           capture_output=True, text=True, timeout=90, creationflags=0x08000000)  # no window
    except (OSError, subprocess.TimeoutExpired) as e:
        return str(e)
    return None if r.returncode == 0 else (r.stdout or r.stderr).strip()[:300] or f"exit code {r.returncode}"


# ------------------------------------------------------------------ rotation
def _state_path():
    return paths.output_dir() / "srs_eam.json"


def current_for(stem):
    """{"blue", "red", "at"} when the passwords in force were made for this mission, else None."""
    try:
        st = json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {k: st[k] for k in ("blue", "red", "at")} if st.get("mission") == stem else None


def rotate(stem):
    """New EAM passwords for a mission being published. Returns "ok" or what went wrong."""
    if not ON_WINDOWS:
        return "SRS password rotation works only on the Windows PC running SRS."
    cfg = Path(os.environ.get("SRS_CONFIG_PATH", "").strip())
    task = os.environ.get("SRS_TASK_NAME", "").strip()
    if not cfg.name or not cfg.is_file():
        return f"SRS server.cfg not found ({cfg or 'set SRS_CONFIG_PATH on the Settings page'})."
    if not task:
        return "Set the SRS scheduled task name on the Settings page."
    with _lock:
        passwords = {"blue": new_password(), "red": new_password()}
        error = _task("stop", task, cfg.parent)
        if error:
            return f"Couldn't stop SRS, so its passwords weren't changed: {error}"
        try:
            write_passwords(cfg, passwords)
            written = None
        except (OSError, UnicodeError) as e:
            written = f"Couldn't write {cfg}: {e}"
        finally:
            started = _task("start", task, cfg.parent)
        if written:
            return written + ("" if not started else f" SRS didn't start again either: {started}")
        tmp = _state_path().with_suffix(".json.tmp")
        tmp.write_text(json.dumps({**passwords, "mission": stem, "at": time.time()}), encoding="utf-8")
        tmp.replace(_state_path())
        if started:
            return f"New passwords are in server.cfg, but SRS didn't start again: {started}. Start it by hand."
    return "ok"
