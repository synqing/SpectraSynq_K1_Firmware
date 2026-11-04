#!/usr/bin/env python3
"""Read-only HTTP bridge: Serial Studio dashboard.getData → Web View.

Does not write UART. Does not flash. Does not reopen cadence.
Serves index.html and GET /live for the K1 Dual UART Web View widget.
"""

from __future__ import annotations

import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, "/Users/spectrasynq/Serial-Studio/tests/utils")
from api_client import SerialStudioClient  # noqa: E402

HOST = "127.0.0.1"
PORT = 8765
HTML = HERE / "index.html"

_client: SerialStudioClient | None = None
_last: dict = {"ts": 0, "age_ms": 99999, "bench": {}, "main": {}, "error": "starting"}


def ss() -> SerialStudioClient:
    global _client
    if _client is None:
        _client = SerialStudioClient(timeout=2.0)
        _client.connect()
    return _client


def grab() -> dict:
    global _last
    try:
        data = ss().command("dashboard.getData")
        groups = (data.get("frame") or {}).get("groups") or []
        out = {"ts": int(time.time() * 1000), "bench": {}, "main": {}, "error": None}

        def pack(prefix: str) -> dict:
            g = next((x for x in groups if str(x.get("title") or "").startswith(prefix)), None)
            m = {}
            if not g:
                return m
            for ds in g.get("datasets") or []:
                t = ds.get("title")
                if t:
                    m[t] = ds.get("numericValue")
            return m

        out["bench"] = pack("K1 Bench")
        out["main"] = pack("K1 Main")
        out["age_ms"] = 0
        _last = out
        return out
    except Exception as exc:
        if _client is not None:
            try:
                _client.disconnect()
            except Exception:
                pass
        globals()["_client"] = None
        _last = {
            "ts": int(time.time() * 1000),
            "age_ms": 99999,
            "bench": _last.get("bench") or {},
            "main": _last.get("main") or {},
            "error": str(exc),
        }
        return _last


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("webview-bridge " + (fmt % args) + "\n")

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(204, b"", "text/plain")

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send(200, HTML.read_bytes(), "text/html; charset=utf-8")
            return
        if self.path.startswith("/live"):
            payload = grab()
            self._send(200, json.dumps(payload).encode("utf-8"), "application/json")
            return
        self._send(404, b"not found", "text/plain")


def main() -> int:
    if not HTML.exists():
        print(f"missing {HTML}", file=sys.stderr)
        return 1
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"K1 webview bridge http://{HOST}:{PORT}/  (read-only, no UART writes)", flush=True)
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
