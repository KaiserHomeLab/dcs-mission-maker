"""The Windows app: runs the server in the background with a tray icon.

Started by "DCS Mission Maker.exe" (the PyInstaller build, see windows/dcs-mission-maker.spec).
Settings come from the Settings page (settings.json in the data folder); logs go to the
data folder's logs/. Starting it again while it runs just opens the browser.

    --background   don't open the browser (used when it starts with Windows)
    --no-tray      no tray icon: run until stopped (CI, or a PC without a desktop)
"""
import argparse
import contextlib
import json
import logging
import logging.handlers
import os
import sys
import threading
import urllib.request
import webbrowser

from . import __version__, paths

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


def _message(text):
    log.error(text)
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, NAME, 0x10)  # MB_ICONERROR


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
    args = parser.parse_args(argv)

    paths.data_dir().mkdir(parents=True, exist_ok=True)
    _setup_logging()
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

    from waitress import create_server
    try:
        server = create_server(app, host=os.environ.get("HOST", "0.0.0.0"), port=port,
                               threads=int(os.environ.get("THREADS", "6")))
    except OSError as e:
        _message(f"Port {port} is in use by another program ({e}).\n\nSet another port in "
                 f"{paths.output_dir() / 'settings.json'}, e.g. {{\"PORT\": \"8081\"}}, and start it again.")
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
