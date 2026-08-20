#!/usr/bin/env python3
"""Capture both K1s while Captain is already playing music. No afplay. Restore palettes."""
from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import serial
from serial.tools import list_ports

HERE = Path(__file__).resolve().parent

UNITS = {
    "main_rpl": {"usb": "B4:3A:45:A5:87:90", "chip": "9087A500", "env": "k1_main_rpl_im69d", "git": "79d220fa"},
    "bench_b489": {"usb": "B4:3A:45:A5:89:B4", "chip": "B489A500", "env": "k1_bench_im69d", "git": "69e21140"},
}
CYCLE = [
    (40, "K1_Naberius_Gold_gp"),
    (41, "K1_Vepar_Pink_gp"),
    (34, "K1_Tropical_Ultraviolet_gp"),
    (32, "Blue_Cyan_Yellow_gp"),
]
DWELL_S = 18.0
HOLD_S = 20.0

BUILD_RE = re.compile(r"BUILD:\s*version=(?P<version>\S+)\s+git=(?P<git>\S+)\s+epoch=(?P<epoch>\S+)\s+env=(?P<env>\S+)")
CHIP_RE = re.compile(r"CHIP ID:\s*([0-9A-Fa-f]+)")
CHROMA_RE = re.compile(r"CONFIG\.CHROMA:\s*([-0-9.]+)")
MOOD_RE = re.compile(r"CONFIG\.MOOD:\s*([-0-9.]+)")
SEC_PAL_RE = re.compile(r"SECONDARY_PALETTE_INDEX:\s*(\d+)\s+\(([^)]+)\)")
AP_RE = re.compile(
    r"\[AP\].*?peak_scaled=(?P<peak>[-0-9.]+).*?silence=(?P<sil>\d+)"
    r".*?bpm=(?P<bpm>[-0-9.]+)\s+conf=(?P<conf>[-0-9.]+)\s+lock=(?P<lock>\d+)"
)
FPS_RE = re.compile(r"^SYSTEM_FPS:\s*([-0-9.]+)")
LED_FPS_RE = re.compile(r"^LED_FPS:\s*([-0-9.]+)")
EDGE_RE = re.compile(r"EDGE_EFFECTIVE_(PRIMARY|SECONDARY):\s*(\S+)")
PAL_ACK_RE = re.compile(r"^PALETTE:\s*(\d+)\s+\(([^)]+)\)")
SEC_ACK_RE = re.compile(r"^SECONDARY_PALETTE_INDEX:\s*(\d+)\s+\(([^)]+)\)")


def find_port(usb: str) -> str:
    want = usb.upper()
    for p in list_ports.comports():
        if (p.serial_number or "").upper() == want:
            return p.device
    raise SystemExit(f"USB {usb} missing")


class Unit:
    def __init__(self, name: str, spec: dict, port: str):
        self.name, self.spec, self.port = name, spec, port
        self.lines: list[tuple[float, str]] = []
        self.lock = threading.Lock()
        self._stop = threading.Event()
        self._fh = (HERE / f"{name}.log").open("w", encoding="utf-8")
        s = serial.Serial()
        s.port = port
        s.baudrate = 115200
        s.timeout = 0.05
        s.write_timeout = 1.0
        s.dtr = True
        s.rts = False
        s.open()
        time.sleep(0.4)
        self.ser = s
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()

    def _read(self) -> None:
        buf = ""
        while not self._stop.is_set():
            try:
                chunk = self.ser.read(4096)
            except Exception:
                break
            if not chunk:
                continue
            buf += chunk.decode("utf-8", "replace")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.rstrip("\r")
                if line:
                    t = time.time()
                    with self.lock:
                        self.lines.append((t, line))
                    self._fh.write(f"{t:.3f} {line}\n")
                    self._fh.flush()

    def send(self, cmd: str) -> None:
        self.ser.write((cmd.strip() + "\n").encode("ascii"))
        self.ser.flush()
        t = time.time()
        with self.lock:
            self.lines.append((t, f"> {cmd.strip()}"))
        self._fh.write(f"{t:.3f} > {cmd.strip()}\n")

    def since(self, t0: float) -> list[str]:
        with self.lock:
            return [ln for t, ln in self.lines if t >= t0]

    def window(self, t0: float, t1: float) -> list[str]:
        with self.lock:
            return [ln for t, ln in self.lines if t0 <= t < t1]

    def close(self) -> None:
        self._stop.set()
        if getattr(self, "_thread", None):
            self._thread.join(timeout=1.0)
        try:
            self.ser.close()
        except Exception:
            pass
        self._fh.close()


def now_playing() -> str:
    try:
        return subprocess.check_output(
            [
                "osascript",
                "-e",
                'tell application "Music" to if it is running then get {player state, name of current track, artist of current track}',
            ],
            text=True,
        ).strip()
    except Exception:
        return "unreadable"


def wait_re(u: Unit, pat: re.Pattern, t0: float, timeout: float = 2.0) -> str | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for ln in u.since(t0):
            if pat.search(ln):
                return ln
        time.sleep(0.04)
    return None


def score_ap(lines: list[str]) -> dict:
    peaks, confs, bpms = [], [], []
    sil = lock = n = 0
    for ln in lines:
        m = AP_RE.search(ln)
        if not m:
            continue
        n += 1
        peaks.append(float(m.group("peak")))
        confs.append(float(m.group("conf")))
        bpms.append(float(m.group("bpm")))
        sil += int(m.group("sil"))
        lock += int(m.group("lock"))
    if not n:
        return {"n": 0}
    return {
        "n": n,
        "silence_frac": sil / n,
        "lock_frac": lock / n,
        "peak_mean": statistics.mean(peaks),
        "peak_max": max(peaks),
        "conf_mean": statistics.mean(confs),
        "bpm_mean": statistics.mean(bpms),
    }


def score_fps(lines: list[str]) -> dict:
    def pct(xs):
        if not xs:
            return {"n": 0}
        xs = sorted(xs)
        return {"n": len(xs), "p50": xs[len(xs) // 2], "min": xs[0], "max": xs[-1], "mean": statistics.mean(xs)}

    sys_ = [float(m.group(1)) for ln in lines if (m := FPS_RE.match(ln))]
    led = [float(m.group(1)) for ln in lines if (m := LED_FPS_RE.match(ln))]
    return {"system": pct(sys_), "led": pct(led)}


def set_pal(units: list[Unit], idx: int, name: str) -> list[dict]:
    out = []
    for u in units:
        t = time.time()
        u.send(f":palette_index={idx}")
        u.send(f":secondary_palette_index={idx}")
        pal = wait_re(u, PAL_ACK_RE, t)
        sec = wait_re(u, SEC_ACK_RE, t)
        pm, sm = PAL_ACK_RE.search(pal or ""), SEC_ACK_RE.search(sec or "")
        out.append({
            "unit": u.name,
            "want": name,
            "primary_ok": bool(pm and int(pm.group(1)) == idx and pm.group(2) == name),
            "secondary_ok": bool(sm and int(sm.group(1)) == idx and sm.group(2) == name),
            "primary_ack": pal,
            "secondary_ack": sec,
        })
        u.send(":edge_status")
        u.send(":fps")
        u.send(":led_fps")
    return out


def restore(units: list[Unit], snaps: dict) -> None:
    for u in units:
        pal = snaps[u.name]["secondary_palette"]
        u.send(f":palette_index={pal}")
        u.send(f":secondary_palette_index={pal}")


def main() -> int:
    units: list[Unit] = []
    snaps: dict = {}
    ids: dict = {}
    acks: list = []
    phases: dict = {}
    playing_start = now_playing()
    try:
        for name, spec in UNITS.items():
            u = Unit(name, spec, find_port(spec["usb"]))
            units.append(u)
        time.sleep(0.3)
        for u in units:
            t = time.time()
            u.send(":build")
            u.send(":dump")
            time.sleep(1.6)
            u.send(":secondary_status=")
            u.send(":edge_status")
            u.send(":ap_stream=1")
            u.send(":vp_stream=1")
            time.sleep(0.6)
            text = "\n".join(u.since(t))
            build = BUILD_RE.search(text)
            chip = CHIP_RE.search(text)
            ident = (build.groupdict() if build else {})
            ident["chip"] = chip.group(1).upper() if chip else ""
            if ident.get("git") and not ident["git"].startswith(u.spec["git"]):
                raise SystemExit(f"{u.name} git {ident.get('git')} != {u.spec['git']}")
            if ident.get("chip") and u.spec["chip"] not in ident["chip"]:
                raise SystemExit(f"{u.name} chip {ident.get('chip')} != {u.spec['chip']}")
            sec = SEC_PAL_RE.search(text)
            if not sec:
                raise SystemExit(f"{u.name} no secondary palette")
            snaps[u.name] = {
                "secondary_palette": int(sec.group(1)),
                "secondary_name": sec.group(2),
                "chroma": float(CHROMA_RE.search(text).group(1)) if CHROMA_RE.search(text) else None,
                "mood": float(MOOD_RE.search(text).group(1)) if MOOD_RE.search(text) else None,
            }
            ids[u.name] = ident
            ids[u.name]["port"] = u.port

        hold0 = time.time()
        while time.time() - hold0 < HOLD_S:
            for u in units:
                u.send(":fps")
                u.send(":led_fps")
            time.sleep(2.0)
        hold1 = time.time()
        for u in units:
            phases.setdefault(u.name, {})["hold"] = {
                "ap": score_ap(u.window(hold0, hold1)),
                "fps": score_fps(u.window(hold0, hold1)),
                "edge": [(m.group(1), m.group(2)) for ln in u.window(hold0, hold1) if (m := EDGE_RE.search(ln))],
            }

        for idx, name in CYCLE:
            acks.extend(set_pal(units, idx, name))
            t0 = time.time()
            while time.time() - t0 < DWELL_S:
                for u in units:
                    u.send(":fps")
                    u.send(":led_fps")
                time.sleep(2.0)
            t1 = time.time()
            for u in units:
                phases[u.name][f"pal_{idx}"] = {
                    "palette": name,
                    "ap": score_ap(u.window(t0, t1)),
                    "fps": score_fps(u.window(t0, t1)),
                    "edge": [(m.group(1), m.group(2)) for ln in u.window(t0, t1) if (m := EDGE_RE.search(ln))],
                }

        restore(units, snaps)
        time.sleep(0.5)
        restore_ok = {}
        for u in units:
            t = time.time()
            u.send(":secondary_status=")
            wait_re(u, SEC_PAL_RE, t)
            sec = SEC_PAL_RE.search("\n".join(u.since(t)))
            restore_ok[u.name] = {
                "want": snaps[u.name]["secondary_palette"],
                "got": int(sec.group(1)) if sec else None,
            }
            u.send(":vp_stream=0")

        playing_end = now_playing()
        result = {
            "when": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fixture": "Captain-played Music.app. No afplay. No pause. No volume change.",
            "now_playing_start": playing_start,
            "now_playing_end": playing_end,
            "identities": ids,
            "config": snaps,
            "acks": acks,
            "phases": phases,
            "restore": restore_ok,
            "ack_all_ok": all(a["primary_ok"] and a["secondary_ok"] for a in acks),
            "honour_ok": all(
                str(e[1]).endswith("_palette")
                for ph in phases.values()
                for v in ph.values()
                for e in v.get("edge") or []
            ),
        }
        (HERE / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
        (HERE / "NOWPLAYING.txt").write_text(
            f"start={playing_start}\nend={playing_end}\n"
        )
        print(json.dumps({
            "now_playing_start": playing_start,
            "now_playing_end": playing_end,
            "ack_all_ok": result["ack_all_ok"],
            "honour_ok": result["honour_ok"],
            "restore": restore_ok,
            "hold": {n: phases[n]["hold"]["ap"] for n in phases},
            "cycle": {n: {k: v["ap"] for k, v in phases[n].items() if k.startswith("pal_")} for n in phases},
            "fps": {n: {k: v["fps"] for k, v in phases[n].items()} for n in phases},
            "config": snaps,
        }, indent=2))
        return 0
    finally:
        try:
            if snaps and units:
                restore(units, snaps)
        except Exception as exc:
            print(f"RESTORE FAIL {exc}", file=sys.stderr)
        for u in units:
            try:
                u.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
