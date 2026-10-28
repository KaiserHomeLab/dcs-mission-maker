"""The Windows app: runs the server in the background with a tray icon.

Started by "DCS Mission Maker.exe" (the PyInstaller build, see windows/dcs-mission-maker.spec).
Settings come from the Settings page (settings.json in the data folder); logs go to the
data folder's logs/. Starting it again while it runs just opens the browser.

    --background   don't open the browser (used when it starts with Windows)
    --no-tray      no tray icon: run until stopped (CI, or a PC without a desktop)
    --set-autostart / --unset-autostart
                   turn "Start with Windows" on or off and exit (used by the installer)

If 8080 is taken by another program, it moves to the next free port and saves it in the
settings. On Windows the data folder is made private to the user running the app (plus
administrators), since settings.json holds the Discord webhook and passwords.
"""
import argparse
import contextlib
import json
import logging
import logging.handlers
import os
import socket
import subprocess
import sys
import threading
import urllib.request
import webbrowser

from . import __version__, paths, settings

NAME = "DCS Mission Maker"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
log = logging.getLogger("dcs-mission-maker")


def _setup_logging():
    paths.logs_dir().mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(paths.logs_dir() / "app.log", maxBytes=2_000_000,
                                                   backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handlers = [handler]
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)
    if sys.stdout is None:  # windowed .exe: no console, so print() output goes to the log too
        sys.stdout = sys.stderr = handler.stream


def _running_here(port):
    """This app is already serving on the port (started twice, or from autostart)."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as r:
            return json.load(r).get("app") == "dcs-mission-maker"
    except (OSError, ValueError):
        return False


def _message(text, error=True):
    (log.error if error else log.warning)(text)
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, NAME, 0x10 if error else 0x40)  # error / information


def _port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            return False
    return True


def _protect_data_dir():
    """Windows: only this user, administrators and SYSTEM can open the data folder (other
    accounts can read C:\\ProgramData by default). Done once; a marker file remembers it."""
    if sys.platform != "win32" or not paths.FROZEN:
        return
    folder = paths.data_dir()
    marker = folder / ".private"
    if marker.exists():
        return
    no_window = 0x08000000  # CREATE_NO_WINDOW
    try:
        who = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True, text=True,
                             check=True, creationflags=no_window).stdout.strip().split(",")[-1].strip('"')
        subprocess.run(["icacls", str(folder), "/inheritance:r", "/grant:r",
                        "*S-1-5-32-544:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F", f"*{who}:(OI)(CI)F"],
                       capture_output=True, check=True, creationflags=no_window)
        marker.write_text("The data folder is private to its user (see app/desktop.py).\n", encoding="utf-8")
        log.info("data folder made private to %s", who)
    except (OSError, subprocess.CalledProcessError, IndexError) as e:
        log.warning("couldn't make the data folder private: %s", e)


# ---------------------------------------------------------------- start with Windows
def _autostart_command():
    return f'"{sys.executable}" --background'


def autostart_enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return winreg.QueryValueEx(key, NAME)[0] == _autostart_command()
    except OSError:
        return False


def set_autostart(on):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if on:
            winreg.SetValueEx(key, NAME, 0, winreg.REG_SZ, _autostart_command())
        else:
            with contextlib.suppress(FileNotFoundError):
                winreg.DeleteValue(key, NAME)


# ---------------------------------------------------------------- tray
def _tray(url, server):
    import pystray

    from .icon import draw

    def open_folder(_icon, _item):
        os.startfile(paths.data_dir())

    def toggle_autostart(_icon, _item):
        set_autostart(not autostart_enabled())

    def quit_app(icon, _item):
        log.info("quit from tray")
        icon.stop()
        server.close()

    items = [
        pystray.MenuItem(f"Open {NAME}", lambda: webbrowser.open(url), default=True),
        pystray.MenuItem("Settings", lambda: webbrowser.open(url + "/settings")),
        pystray.MenuItem("Open data folder", open_folder),
        pystray.Menu.SEPARATOR,
    ]
    if paths.FROZEN and sys.platform == "win32":
        items.append(pystray.MenuItem("Start with Windows", toggle_autostart,
                                      checked=lambda _item: autostart_enabled()))
    items.append(pystray.MenuItem("Quit", quit_app))
    pystray.Icon("dcs-mission-maker", draw(64), f"{NAME} {__version__}: {url}", pystray.Menu(*items)).run()


def main(argv=None):
    parser = argparse.ArgumentParser(prog=NAME)
    parser.add_argument("--background", action="store_true", help="don't open the browser")
    parser.add_argument("--no-tray", action="store_true", help="no tray icon")
    parser.add_argument("--set-autostart", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--unset-autostart", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.set_autostart or args.unset_autostart:
        set_autostart(args.set_autostart)
        return 0

    paths.data_dir().mkdir(parents=True, exist_ok=True)
    _setup_logging()
    _protect_data_dir()
    log.info("%s %s starting; data in %s", NAME, __version__, paths.data_dir())
    try:
        from .server import app  # applies settings.json (PORT, ...)
    except Exception:
        log.exception("startup failed")
        _message(f"{NAME} couldn't start. Details are in {paths.logs_dir() / 'app.log'}")
        return 1

    port = int(os.environ.get("PORT") or 8080)
    url = f"http://localhost:{port}"
    if _running_here(port):
        log.info("already running on port %s", port)
        if not args.background:
            webbrowser.open(url)
        return 0

    if not _port_free(port):
        free = next((p for p in range(port + 1, port + 20) if _port_free(p)), None)
        if free is None or settings.save({"PORT": str(free)}):
            _message(f"Port {port} is in use by another program. Pick another port on the Settings page, "
                     f"or in {settings.path()}, and start {NAME} again.")
            return 1
        _message(f"Port {port} is in use by another program, so {NAME} now uses port {free}:\n"
                 f"http://localhost:{free}\n\nYou can change it on the Settings page.", error=False)
        port, url = free, f"http://localhost:{free}"

    from waitress import create_server
    try:
        server = create_server(app, host=os.environ.get("HOST", "0.0.0.0"), port=port,
                               threads=int(os.environ.get("THREADS", "6")))
    except OSError as e:
        _message(f"{NAME} couldn't open port {port}: {e}")
        return 1
    threading.Thread(target=server.run, name="waitress", daemon=True).start()
    log.info("serving on %s", url)
    if not args.background:
        webbrowser.open(url)

    if not args.no_tray:
        try:
            _tray(url, server)
            return 0
        except Exception:  # no desktop session, or pystray isn't available
            log.exception("no tray icon; running until stopped")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.close()
    return 0
