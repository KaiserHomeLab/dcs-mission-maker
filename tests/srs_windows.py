"""Windows only (CI): SRS EAM password rotation against a real scheduled task.

A stand-in for SRS (a task that just sleeps) is registered, a sample server.cfg is rotated,
and the task must have been stopped and started again. Needs admin rights to register a task.

    python -m tests.srs_windows
"""
import os
import pathlib
import subprocess
import sys
import tempfile

tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["OUTPUT_DIR"] = str(tmp / "missions")
(tmp / "missions").mkdir()

from app import srs_eam  # noqa: E402

TASK = "DMM SRS stand-in"
fails = []


def ok(cond, msg):
    print(("ok  " if cond else "FAIL"), msg)
    if not cond:
        fails.append(msg)


def ps(command):
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                          capture_output=True, text=True, check=False).stdout.strip()


def state():
    return ps(f"(Get-ScheduledTask -TaskName '{TASK}').State")


ps(f"$a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -Command Start-Sleep 900'; "
   f"Register-ScheduledTask -TaskName '{TASK}' -Action $a -Force | Out-Null; Start-ScheduledTask -TaskName '{TASK}'")
try:
    ok(state() == "Running", f"stand-in task running ({state()})")
    cfg = tmp / "srs" / "server.cfg"
    cfg.parent.mkdir()
    original = ("[General Settings]\r\nEXTERNAL_AWACS_MODE=true\r\n\r\n[External AWACS Mode Settings]\r\n"
                "EXTERNAL_AWACS_MODE_BLUE_PASSWORD=blue\r\nEXTERNAL_AWACS_MODE_RED_PASSWORD=red\r\n")
    cfg.write_text(original, encoding="utf-8", newline="")
    os.environ.update(SRS_CONFIG_PATH=str(cfg), SRS_TASK_NAME=TASK)

    result = srs_eam.rotate("mission1")
    ok(result == "ok", f"rotate: {result}")
    pw = srs_eam.current_for("mission1")
    expected = srs_eam.edit_cfg(original, {"blue": pw["blue"], "red": pw["red"]}) if pw else None
    ok(cfg.read_bytes().decode() == expected, "server.cfg has the new passwords, nothing else changed")
    ok(state() == "Running", f"stand-in task started again ({state()})")

    os.environ["SRS_TASK_NAME"] = "No such task here"
    before = cfg.read_bytes()
    result = srs_eam.rotate("mission2")
    ok(result.startswith("Couldn't stop SRS") and cfg.read_bytes() == before,
       f"unknown task: nothing changed ({result})")
finally:
    ps(f"Stop-ScheduledTask -TaskName '{TASK}'; Unregister-ScheduledTask -TaskName '{TASK}' -Confirm:$false")

print(f"srs windows checks done, {len(fails)} failures")
sys.exit(1 if fails else 0)
