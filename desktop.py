"""Desktop entry point: runs the Flask app in a background thread and shows
it in a native window via pywebview instead of a browser tab. This is what
build.bat packages into a single .exe with PyInstaller."""
import socket
import threading
import time

import webview

from app import app

PORT = 5051


def run_flask():
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)


def wait_until_listening(port, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    wait_until_listening(PORT)
    webview.create_window("예배 자막 소스 도구", f"http://127.0.0.1:{PORT}", width=1000, height=850)
    webview.start()
