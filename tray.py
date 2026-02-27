import contextlib
import os
import socket
import sys
import threading
import time

import pystray
import uvicorn
import webview
from PIL import Image

from config import PORT, validate_config
from paths import ASSETS_DIR

APP_TITLE = "Voice Transcriber"
HOST = "127.0.0.1"
WIN_W = 420
WIN_H = 680
MARGIN = 16
TASKBAR_H = 48

ICON_PNG = os.path.join(ASSETS_DIR, "icon.png")
ICON_ICO = os.path.join(ASSETS_DIR, "icon.ico")

_window: webview.Window | None = None
_icon: pystray.Icon | None = None
_server: uvicorn.Server | None = None
_hwnd: int = 0
_screen_w: int = 1920
_screen_h: int = 1080


class WindowApi:
    def hide_window(self):
        if _window:
            threading.Thread(target=_window.hide, daemon=True).start()


def _set_window_pos(x: int, y: int, w: int, h: int) -> None:
    if sys.platform == "win32" and _hwnd:
        import ctypes

        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        ctypes.windll.user32.SetWindowPos(_hwnd, 0, x, y, w, h, SWP_NOZORDER | SWP_NOACTIVATE)
    elif _window:
        win = _window

        def _reposition() -> None:
            win.resize(w, h)
            time.sleep(0.1)
            win.move(x, y)

        threading.Thread(target=_reposition, daemon=True).start()


def _anchor(window: webview.Window) -> None:
    global _screen_w, _screen_h, _hwnd

    time.sleep(0.15)

    try:
        screens = webview.screens
        if screens:
            _screen_w = screens[0].width
            _screen_h = screens[0].height
    except Exception:
        pass

    if sys.platform == "win32":
        import ctypes

        _hwnd = ctypes.windll.user32.FindWindowW(None, APP_TITLE) or 0

    x = _screen_w - WIN_W - MARGIN
    y = _screen_h - WIN_H - TASKBAR_H
    _set_window_pos(x, y, WIN_W, WIN_H)


def _load_tray_icon() -> Image.Image:
    if os.path.exists(ICON_PNG):
        return Image.open(ICON_PNG).convert("RGBA").resize((64, 64), Image.LANCZOS)  # type: ignore[attr-defined]
    from PIL import ImageDraw

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse([0, 0, 63, 63], fill="#7c6dfa")
    return img


def _find_free_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex((HOST, preferred)) != 0:
            return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def _start_server(port: int) -> None:
    global _server
    from main import app

    config = uvicorn.Config(app=app, host=HOST, port=port, log_level="warning", lifespan="on")
    _server = uvicorn.Server(config)
    _server.run()


def _wait_for_server(port: int, timeout: float = 12.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.3):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _shutdown() -> None:
    if _server:
        _server.should_exit = True
    if _icon:
        with contextlib.suppress(Exception):
            _icon.stop()
    time.sleep(0.3)
    os._exit(0)


def on_tray_open(icon=None, item=None):
    if _window:
        _window.show()


def on_tray_exit(icon, item):
    if _window:
        with contextlib.suppress(Exception):
            _window.destroy()
    threading.Thread(target=_shutdown, daemon=True).start()


def on_window_closing() -> bool:
    assert _window is not None
    threading.Thread(target=_window.hide, daemon=True).start()
    return False


def main() -> None:
    global _window, _icon

    try:
        validate_config()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        os._exit(1)

    port = _find_free_port(PORT)
    url = f"http://{HOST}:{port}/?mode=app"

    threading.Thread(target=_start_server, args=(port,), daemon=True).start()

    if not _wait_for_server(port):
        print("ERROR: server failed to start", file=sys.stderr)
        os._exit(1)

    _window = webview.create_window(
        title=APP_TITLE,
        url=url,
        width=WIN_W,
        height=WIN_H,
        x=100,
        y=100,
        resizable=False,
        frameless=True,
        on_top=True,
        shadow=True,
        js_api=WindowApi(),
    )
    assert _window is not None
    _window.events.closing += on_window_closing

    tray_image = _load_tray_icon()
    menu = pystray.Menu(
        pystray.MenuItem("Open", on_tray_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_tray_exit),
    )
    _icon = pystray.Icon(APP_TITLE, tray_image, APP_TITLE, menu, on_activate=on_tray_open)
    if os.path.exists(ICON_ICO):
        with contextlib.suppress(Exception):
            _icon.icon = Image.open(ICON_ICO)

    threading.Thread(target=_icon.run, daemon=True).start()

    webview.start(_anchor, debug=False)

    _shutdown()


if __name__ == "__main__":
    main()
