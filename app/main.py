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
    api._window = window
    window.is_exiting = False

    def on_closing() -> bool:
        if window.is_exiting:
            return True

        window.hide()
        notify_toast(
            "Release Tool",
            "Still running in the background - use the tray icon or the Exit button in the window to close it.",
        )
        return False

    window.events.closing += on_closing

    tray_icon = _build_tray_icon(window)
    tray_icon.run_detached()

    webview.start()


def _build_tray_icon(window: webview.Window) -> pystray.Icon:  # type: ignore[valid-type]
    def show_window(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:  # type: ignore[valid-type]
        window.show()

    def exit_app(icon: pystray.Icon, _item: pystray.MenuItem) -> None:  # type: ignore[valid-type]
        icon.stop()
        window.is_exiting = True
        window.destroy()
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
