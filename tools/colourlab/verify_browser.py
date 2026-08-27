#!/usr/bin/env python3
"""Look-layer browser verify for Colour Lab. Does not talk to hardware."""
from __future__ import annotations

import http.server
import os
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SHOTS = ROOT / "screenshots"
PORT = 8765


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *_args):
        return


def serve():
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def main() -> int:
    SHOTS.mkdir(exist_ok=True)
    httpd = serve()
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.on("console", lambda msg: errors.append(f"{msg.type}: {msg.text}") if msg.type in ("error", "warning") else None)
        page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

        cases = [
            ("", "look-disconnected"),
            ("?demo=unsupported", "look-unsupported"),
            ("?demo=main", "look-ready-main"),
            ("?demo=bench", "look-ready-bench"),
            ("?demo=unverified", "look-unverified"),
        ]
        for qs, name in cases:
            page.goto(f"http://127.0.0.1:{PORT}/index.html{qs}", wait_until="networkidle")
            page.wait_for_timeout(250)
            page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)

        page.goto(f"http://127.0.0.1:{PORT}/index.html?demo=main&paint=solid", wait_until="networkidle")
        page.wait_for_timeout(150)
        page.screenshot(path=str(SHOTS / "look-paint-solid.png"), full_page=True)
        page.goto(f"http://127.0.0.1:{PORT}/index.html?demo=main&paint=card", wait_until="networkidle")
        page.wait_for_timeout(150)
        page.screenshot(path=str(SHOTS / "look-paint-card.png"), full_page=True)

        page.keyboard.press("Tab")
        page.keyboard.press("Tab")
        focused = page.evaluate("document.activeElement && document.activeElement.id")
        print(f"TAB_FOCUS={focused}")

        page.set_viewport_size({"width": 740, "height": 1100})
        page.goto(f"http://127.0.0.1:{PORT}/index.html?demo=main", wait_until="networkidle")
        page.screenshot(path=str(SHOTS / "look-viewport-740.png"), full_page=True)

        page.set_viewport_size({"width": 1440, "height": 1100})
        page.evaluate("document.body.style.zoom = '2'")
        page.goto(f"http://127.0.0.1:{PORT}/index.html?demo=main", wait_until="networkidle")
        page.evaluate("document.body.style.zoom = '2'")
        page.screenshot(path=str(SHOTS / "look-zoom-200.png"), full_page=True)

        stop = page.locator("#btnStop")
        print(f"STOP_VISIBLE={stop.is_visible()}")
        print(f"STOP_TEXT={stop.inner_text()}")
        print(f"IDENTITY={page.locator('#btnIdentity').inner_text()}")
        print(f"BOTH_MAIN={page.locator('#bothScaleReadout').is_visible()}")
        page.goto(f"http://127.0.0.1:{PORT}/index.html?demo=bench", wait_until="networkidle")
        print(f"TUNE_BENCH_HIDDEN={not page.locator('#tuneBand').is_visible()}")
        print(f"BOTH_BENCH={page.locator('#bothScaleReadout').is_visible()}")
        print(f"N_BENCH={page.locator('#nPrimary').inner_text()}")
        browser.close()
    httpd.shutdown()
    print("CONSOLE=" + ("; ".join(errors) if errors else "0 errors, 0 warnings"))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
