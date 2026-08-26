"""Entrypoint: creates the pywebview window, starts the tray icon, and wires
them together so closing the window hides it instead of exiting the app -
in-progress builds/promotions/polling keep running in the background until
the tray icon's "Exit" is used (see core/config.py's MAX_WORKERS comment and
CLAUDE.md section 6.3)."""

import os

import pystray
import webview
from PIL import Image

from api import Api
from core.config import APP_DIR
from core.notifications import notify_toast

INDEX_HTML_PATH = APP_DIR / "ui" / "index.html"
TRAY_ICON_PATH = APP_DIR / "ui" / "assets" / "tray_icon.ico"


def main() -> None:
    api = Api()

    window = webview.create_window(
        "Release Tool",
        url=str(INDEX_HTML_PATH),
        js_api=api,
        width=1080,
        height=720,
        min_size=(860, 560),
    )
    # Api.exit_app()/restart_app() need this to destroy() the WebView2
    # control cleanly before tearing down the process - see api.py. Must be
    # the underscore-prefixed attribute: a public one gets swept into
    # pywebview's js_api introspection and crashes (see api.py's comment).
    api._window = window
    # Plain bookkeeping attribute, not part of pywebview's API - window.destroy()
    # (called from api.py's exit_app()/restart_app() and this file's tray
    # exit_app() below) triggers Form.Close() under the hood, which fires the
    # *same* `closing` event as the user clicking "X". Without this flag,
    # on_closing() can't tell "actually exiting" apart from "X was clicked" and
    # fires the "still running in background" toast on a real exit/restart -
    # misinformation, since the app is not still running at that point.
    window.is_exiting = False

    def on_closing() -> bool:
        if window.is_exiting:
            return True

        # Returning False cancels pywebview's default close behavior, so the
        # "X" button hides the window instead of destroying it.
        window.hide()
        notify_toast(
            "Release Tool",
            "Still running in the background - use the tray icon or the Exit button in the window to close it.",
        )
        return False

    window.events.closing += on_closing

    tray_icon = _build_tray_icon(window)
    # run_detached() runs pystray's message loop on its own background
    # thread, freeing the main thread for webview.start() below (which
    # blocks for the app's lifetime, same as pystray's own icon.run() would).
    tray_icon.run_detached()

    webview.start()


def _build_tray_icon(window: webview.Window) -> pystray.Icon:  # type: ignore[valid-type]
    def show_window(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:  # type: ignore[valid-type]
        window.show()

    def exit_app(icon: pystray.Icon, _item: pystray.MenuItem) -> None:  # type: ignore[valid-type]
        icon.stop()
        # window.destroy() lets WebView2 dispose its helper processes
        # cleanly instead of being orphaned by os._exit() - see api.py's
        # exit_app() for the same treatment on this app's other Exit path.
        # is_exiting=True stops on_closing() from treating this as an "X was
        # clicked" hide-to-tray and firing its misleading toast.
        window.is_exiting = True
        window.destroy()
        # Full process termination, not a graceful shutdown - in-progress
        # builds/promotions are killed outright
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Open", show_window, default=True),
        pystray.MenuItem("Exit", exit_app),
    )

    return pystray.Icon(
        "release-tool",
        icon=Image.open(TRAY_ICON_PATH),
        title="Release Tool",
        menu=menu,
    )


if __name__ == "__main__":
    main()
