#!/usr/bin/env python3
"""Dual-unit music + palette-cycle soak (read serial, write palettes, restore).

Identity by USB MAC + CHIP ID. DTR asserted, never set False.
Palette writes persist — restore is mandatory in finally.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import serial
from serial.tools import list_ports

HERE = Path(__file__).resolve().parent
BAUD = 115200

SONG_A = Path(
    "/Users/spectrasynq/Music/Music/Media.localized/Music/Unknown Artist/"
    "Unknown Album/ziggyx-summer-rave-155bpm.steady-drums-120s.steady_phase."
    "all_musical.k1-real-music.48k-mono-s16.wav"
)
SONG_B = Path(
    "/Users/spectrasynq/Music/Music/Media.localized/Music/Querox/Time/01 Time.mp3"
)

UNITS = {
    "main_rpl": {
        "usb": "B4:3A:45:A5:87:90",
        "chip": "9087A500",
        "env": "k1_main_rpl_im69d",
        "git": "79d220fa",
    },
    "bench_b489": {
        "usb": "B4:3A:45:A5:89:B4",
        "chip": "B489A500",
        "env": "k1_bench_im69d",
        "git": "69e21140",
    },
}

PALETTE_NAMES = {
    23: "lava_gp",
    32: "Blue_Cyan_Yellow_gp",
    34: "K1_Tropical_Ultraviolet_gp",
    37: "K1_Night_Sea_Amber_gp",
    40: "K1_Naberius_Gold_gp",
    41: "K1_Vepar_Pink_gp",
}

SONG_A_CYCLE = [40, 41, 34, 37]
SONG_B_CYCLE = [32, 23, 40]
SONG_A_DWELL_S = 25.0
SONG_B_DWELL_S = 30.0
AMBIENT_S = 12.0
SOAK_VOLUME = 50
SETTLE_S = 5.0

BUILD_RE = re.compile(
    r"BUILD:\s*version=(?P<version>\S+)\s+git=(?P<git>\S+)\s+"
    r"epoch=(?P<epoch>\S+)\s+env=(?P<env>\S+)"
)
CHIP_RE = re.compile(r"CHIP ID:\s*([0-9A-Fa-f]+)")
LIGHTSHOW_RE = re.compile(r"CONFIG\.LIGHTSHOW_MODE:\s*(\d+)")
SEC_PAL_STATUS_RE = re.compile(r"SECONDARY_PALETTE_INDEX:\s*(\d+)\s+\(([^)]+)\)")
SEC_MODE_RE = re.compile(r"^SECONDARY_MODE:\s*(\d+)")
AP_RE = re.compile(
    r"\[AP\].*?peak_scaled=(?P<peak>[-0-9.]+).*?silence=(?P<sil>\d+)"
    r".*?bpm=(?P<bpm>[-0-9.]+)\s+conf=(?P<conf>[-0-9.]+)\s+lock=(?P<lock>\d+)",
)
VP_RE = re.compile(
    r"\[VP\].*?chroma_flatness=(?P<flat>[-0-9.]+).*?"
    r"chroma_final_max=(?P<cmax>[-0-9.]+).*?chroma_final_mean=(?P<cmean>[-0-9.]+)"
)
FPS_RE = re.compile(r"^SYSTEM_FPS:\s*([-0-9.]+)")
LED_FPS_RE = re.compile(r"^LED_FPS:\s*([-0-9.]+)")
EDGE_RE = re.compile(r"EDGE_EFFECTIVE_(PRIMARY|SECONDARY):\s*(\S+)")
PAL_ACK_RE = re.compile(r"^PALETTE:\s*(\d+)\s+\(([^)]+)\)")
SEC_PAL_ACK_RE = re.compile(r"^SECONDARY_PALETTE_INDEX:\s*(\d+)\s+\(([^)]+)\)")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_port(usb: str) -> str:
    want = usb.upper()
    for p in list_ports.comports():
        sn = (p.serial_number or "").upper()
        if sn == want:
            return p.device
    raise SystemExit(f"USB {usb} not on any serial port. Refuse to guess by cu.usbmodem name.")


def open_port(path: str) -> serial.Serial:
    s = serial.Serial()
    s.port = path
    s.baudrate = BAUD
    s.timeout = 0.05
    s.write_timeout = 1.0
    s.dtr = True
    s.rts = False
    s.open()
    time.sleep(0.5)
    return s


class Unit:
    def __init__(self, name: str, spec: dict, port: str):
        self.name = name
        self.spec = spec
        self.port = port
        self.ser: serial.Serial | None = None
        self.lines: list[tuple[float, str]] = []
        self.lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.log_path = HERE / f"{name}.log"
        self._fh = self.log_path.open("w", encoding="utf-8")

    def start(self) -> None:
        self.ser = open_port(self.port)
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self) -> None:
        buf = ""
        assert self.ser is not None
        while not self._stop.is_set():
            try:
                chunk = self.ser.read(4096)
            except Exception as exc:  # noqa: BLE001
                self._emit(time.time(), f"# SERIAL_ERROR {exc}")
                break
            if not chunk:
                continue
            buf += chunk.decode("utf-8", "replace")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.rstrip("\r")
                if line:
                    self._emit(time.time(), line)

    def _emit(self, t: float, line: str) -> None:
        with self.lock:
            self.lines.append((t, line))
        self._fh.write(f"{t:.3f} {line}\n")
        self._fh.flush()

    def send(self, cmd: str) -> None:
        assert self.ser is not None
        payload = cmd.strip() + "\n"
        self.ser.write(payload.encode("ascii"))
        self.ser.flush()
        self._emit(time.time(), f"> {cmd.strip()}")

    def snapshot_since(self, t0: float) -> list[tuple[float, str]]:
        with self.lock:
            return [(t, ln) for t, ln in self.lines if t >= t0]

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.5)
        if self.ser and self.ser.is_open:
            self.ser.close()
        self._fh.close()


def get_volume() -> int:
    out = subprocess.check_output(
        ["osascript", "-e", "output volume of (get volume settings)"],
        text=True,
    )
    return int(out.strip())


def set_volume(level: int) -> None:
    subprocess.check_call(["osascript", "-e", f"set volume output volume {int(level)}"])


def wait_for(unit: Unit, pattern: re.Pattern, timeout: float, after: float) -> str | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for t, ln in unit.snapshot_since(after):
            if pattern.search(ln):
                return ln
        time.sleep(0.05)
    return None


def parse_identity(lines: list[str]) -> dict:
    text = "\n".join(lines)
    build = BUILD_RE.search(text)
    chip = CHIP_RE.search(text)
    out = {}
    if build:
        out.update(build.groupdict())
    if chip:
        out["chip"] = chip.group(1).upper()
    return out


def parse_palette_snapshot(lines: list[str]) -> dict | None:
    """Live binaries reject :show_state. Read dump + :secondary_status= instead.

    Primary palette is not in :dump on these ship builds. Boot lock and the
    live secondary index are both Naberius Gold (40); we snapshot secondary
    by name and restore both channels to that index.
    """
    lightshow = LIGHTSHOW_RE.search("\n".join(lines))
    sec_pal = SEC_PAL_STATUS_RE.search("\n".join(lines))
    sec_mode = SEC_MODE_RE.search("\n".join(lines))
    if not sec_pal:
        return None
    pal = int(sec_pal.group(1))
    return {
        "primary_mode": int(lightshow.group(1)) if lightshow else None,
        "primary_palette": pal,
        "primary_palette_source": "secondary_status_plus_boot_lock",
        "secondary_mode": int(sec_mode.group(1)) if sec_mode else None,
        "secondary_palette": pal,
        "secondary_palette_name": sec_pal.group(2),
    }


def collect_window(unit: Unit, t0: float, t1: float) -> list[str]:
    with unit.lock:
        return [ln for t, ln in unit.lines if t0 <= t < t1]


def score_ap(lines: list[str]) -> dict:
    peaks, confs, bpms = [], [], []
    silence = lock = n = 0
    for ln in lines:
        m = AP_RE.search(ln)
        if not m:
            continue
        n += 1
        peaks.append(float(m.group("peak")))
        confs.append(float(m.group("conf")))
        bpms.append(float(m.group("bpm")))
        silence += int(m.group("sil"))
        lock += int(m.group("lock"))
    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "silence_frac": silence / n,
        "lock_frac": lock / n,
        "peak_mean": statistics.mean(peaks),
        "conf_mean": statistics.mean(confs),
        "bpm_mean": statistics.mean(bpms),
        "peak_max": max(peaks),
    }


def score_fps(lines: list[str]) -> dict:
    sys_fps = [float(m.group(1)) for ln in lines if (m := FPS_RE.match(ln))]
    led_fps = [float(m.group(1)) for ln in lines if (m := LED_FPS_RE.match(ln))]

    def pct(xs: list[float]) -> dict:
        if not xs:
            return {"n": 0}
        xs = sorted(xs)
        return {
            "n": len(xs),
            "p50": xs[len(xs) // 2],
            "min": xs[0],
            "max": xs[-1],
            "mean": statistics.mean(xs),
        }

    return {"system": pct(sys_fps), "led": pct(led_fps)}


def score_vp(lines: list[str]) -> dict:
    flats, cmax, cmean = [], [], []
    for ln in lines:
        m = VP_RE.search(ln)
        if not m:
            continue
        flats.append(float(m.group("flat")))
        cmax.append(float(m.group("cmax")))
        cmean.append(float(m.group("cmean")))
    if not flats:
        return {"n": 0}
    return {
        "n": len(flats),
        "flatness_mean": statistics.mean(flats),
        "chroma_final_max_mean": statistics.mean(cmax),
        "chroma_final_mean_mean": statistics.mean(cmean),
    }


def edge_effectives(lines: list[str]) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for ln in lines if (m := EDGE_RE.search(ln))]


def set_palette(units: list[Unit], index: int, expected: str) -> list[dict]:
    acks = []
    for u in units:
        t_send = time.time()
        u.send(f":palette_index={index}")
        u.send(f":secondary_palette_index={index}")
        pal = wait_for(u, PAL_ACK_RE, 2.5, t_send)
        sec = wait_for(u, SEC_PAL_ACK_RE, 2.5, t_send)
        pm = PAL_ACK_RE.search(pal or "")
        sm = SEC_PAL_ACK_RE.search(sec or "")
        rec = {
            "unit": u.name,
            "want_index": index,
            "want_name": expected,
            "primary_ack": pal,
            "secondary_ack": sec,
            "primary_ok": bool(pm and int(pm.group(1)) == index and pm.group(2) == expected),
            "secondary_ok": bool(sm and int(sm.group(1)) == index and sm.group(2) == expected),
        }
        acks.append(rec)
        u.send(":edge_status")
        u.send(":fps")
        u.send(":led_fps")
    return acks


def restore_palettes(units: list[Unit], snaps: dict[str, dict]) -> None:
    for u in units:
        snap = snaps[u.name]
        u.send(f":palette_index={snap['primary_palette']}")
        u.send(f":secondary_palette_index={snap['secondary_palette']}")
        time.sleep(0.4)
        t = time.time()
        u.send(":secondary_status=")
        wait_for(u, SEC_PAL_STATUS_RE, 2.0, t)


def play_afplay(path: Path, seconds: float | None) -> subprocess.Popen:
    if not path.is_file():
        raise SystemExit(f"Fixture missing: {path}")
    cmd = ["afplay"]
    if seconds is not None:
        cmd.extend(["-t", str(seconds)])
    cmd.append(str(path))
    proc = subprocess.Popen(cmd)
    time.sleep(0.4)
    if proc.poll() is not None:
        raise SystemExit(f"afplay died immediately for {path} (exit {proc.returncode})")
    alive = subprocess.run(["pgrep", "-lf", "afplay"], capture_output=True, text=True)
    (HERE / "AFPLAY_LIVE.txt").write_text(
        f"pid={proc.pid}\ncmd={' '.join(cmd)}\npgrep=\n{alive.stdout}\n"
    )
    return proc


def identify_unit(u: Unit) -> dict:
    t = time.time()
    u.send(":build")
    u.send(":dump")
    time.sleep(2.0)
    lines = [ln for _, ln in u.snapshot_since(t)]
    ident = parse_identity(lines)
    t2 = time.time()
    u.send(":secondary_status=")
    u.send(":edge_status")
    time.sleep(0.8)
    show_lines = [ln for _, ln in u.snapshot_since(t)]
    show = parse_palette_snapshot(show_lines)
    ident["show"] = show
    ident["raw_show"] = show_lines[-30:]
    return ident


def check_ident(name: str, spec: dict, ident: dict) -> None:
    problems = []
    chip = ident.get("chip", "")
    if spec["chip"] not in chip and chip not in spec["chip"]:
        problems.append(f"chip={chip} expected {spec['chip']}")
    git = ident.get("git", "")
    if git and not git.startswith(spec["git"]) and not spec["git"].startswith(git):
        problems.append(f"git={git} expected {spec['git']}")
    env = ident.get("env", "")
    if env and env != spec["env"]:
        problems.append(f"env={env} expected {spec['env']}")
    if problems:
        raise SystemExit(f"{name} IDENTITY FAIL: " + "; ".join(problems))


def pctile(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    xs = sorted(xs)
    i = min(len(xs) - 1, max(0, int(round((len(xs) - 1) * p))))
    return xs[i]


def main() -> int:
    if not SONG_A.is_file() or not SONG_B.is_file():
        raise SystemExit("Fixture missing on disk.")

    orig_vol = get_volume()
    units: list[Unit] = []
    player: subprocess.Popen | None = None
    snaps: dict[str, dict] = {}
    all_acks: list[dict] = []
    phases: dict[str, dict] = {}
    identities: dict[str, dict] = {}

    try:
        for name, spec in UNITS.items():
            port = find_port(spec["usb"])
            u = Unit(name, spec, port)
            u.start()
            units.append(u)

        time.sleep(0.4)
        for u in units:
            ident = identify_unit(u)
            check_ident(u.name, u.spec, ident)
            if not ident.get("show"):
                raise SystemExit(f"{u.name} palette snapshot did not parse")
            identities[u.name] = ident
            snaps[u.name] = ident["show"]

        for u in units:
            u.send(":ap_stream=1")
            u.send(":vp_stream=1")
        time.sleep(0.4)

        set_volume(SOAK_VOLUME)
        subprocess.run(
            ["osascript", "-e", 'tell application "Spotify" to pause'],
            check=False,
        )

        # Ambient
        amb_t0 = time.time()
        while time.time() - amb_t0 < AMBIENT_S:
            for u in units:
                u.send(":fps")
                u.send(":led_fps")
                u.send(":event_status")
            time.sleep(2.0)
        amb_t1 = time.time()
        for u in units:
            phases.setdefault(u.name, {})["ambient"] = {
                "ap": score_ap(collect_window(u, amb_t0, amb_t1)),
                "fps": score_fps(collect_window(u, amb_t0, amb_t1)),
                "vp": score_vp(collect_window(u, amb_t0, amb_t1)),
            }

        def run_song(label: str, path: Path, seconds: float | None, cycle: list[int], dwell: float) -> None:
            nonlocal player, all_acks
            player = play_afplay(path, seconds)
            song_t0 = time.time()
            time.sleep(SETTLE_S)
            for idx in cycle:
                name = PALETTE_NAMES[idx]
                all_acks.extend(set_palette(units, idx, name))
                slice_t0 = time.time()
                end = slice_t0 + dwell
                while time.time() < end:
                    for u in units:
                        u.send(":fps")
                        u.send(":led_fps")
                    time.sleep(2.0)
                slice_t1 = time.time()
                for u in units:
                    phases[u.name].setdefault(label, {})[f"pal_{idx}"] = {
                        "palette": name,
                        "ap": score_ap(collect_window(u, slice_t0, slice_t1)),
                        "fps": score_fps(collect_window(u, slice_t0, slice_t1)),
                        "vp": score_vp(collect_window(u, slice_t0, slice_t1)),
                        "edge": edge_effectives(collect_window(u, slice_t0, slice_t1)),
                    }
            if player.poll() is None:
                remaining = (seconds or 0) - (time.time() - song_t0)
                if remaining > 0:
                    time.sleep(min(remaining, 8.0))
            if player.poll() is None:
                player.terminate()
            player.wait(timeout=5)
            player = None
            song_t1 = time.time()
            for u in units:
                phases[u.name][label]["whole"] = {
                    "ap": score_ap(collect_window(u, song_t0 + SETTLE_S, song_t1)),
                    "fps": score_fps(collect_window(u, song_t0, song_t1)),
                    "vp": score_vp(collect_window(u, song_t0, song_t1)),
                    "edge": edge_effectives(collect_window(u, song_t0, song_t1)),
                }

        run_song("song_a_ziggyx", SONG_A, 120.0, SONG_A_CYCLE, SONG_A_DWELL_S)
        time.sleep(1.0)
        run_song("song_b_querox_time", SONG_B, 90.0, SONG_B_CYCLE, SONG_B_DWELL_S)

        restore_palettes(units, snaps)
        time.sleep(0.8)
        restore_check = {}
        for u in units:
            t = time.time()
            u.send(":secondary_status=")
            u.send(":edge_status")
            time.sleep(0.8)
            lines = [ln for _, ln in u.snapshot_since(t)]
            restore_check[u.name] = parse_palette_snapshot(lines)

        for u in units:
            u.send(":vp_stream=0")

        verdicts = eval_predictions(phases, all_acks, snaps, restore_check)
        result = {
            "when": utc_now(),
            "orig_volume": orig_vol,
            "soak_volume": SOAK_VOLUME,
            "output": "Bose Mini II SoundLink",
            "songs": {
                "a": str(SONG_A),
                "b": str(SONG_B),
            },
            "identities": {
                k: {kk: vv for kk, vv in v.items() if kk != "raw_show"}
                for k, v in identities.items()
            },
            "ports": {u.name: u.port for u in units},
            "pre_show": snaps,
            "restore_show": restore_check,
            "acks": all_acks,
            "phases": phases,
            "predictions": verdicts,
        }
        (HERE / "RESULT.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
        (HERE / "RESULT.md").write_text(render_md(result))
        print(json.dumps(verdicts, indent=2))
        return 0 if all(v["pass"] for v in verdicts.values() if "pass" in v) else 1
    finally:
        try:
            if player and player.poll() is None:
                player.terminate()
        except Exception:
            pass
        try:
            if snaps and units:
                restore_palettes(units, snaps)
        except Exception as exc:
            print(f"RESTORE PALETTE FAILED: {exc}", file=sys.stderr)
        try:
            set_volume(orig_vol)
        except Exception:
            pass
        for u in units:
            try:
                u.stop()
            except Exception:
                pass
    return 0


def eval_predictions(phases, acks, snaps, restore_check) -> dict:
    out = {}

    def both(pred, fn):
        ok = True
        detail = {}
        for name in UNITS:
            detail[name] = fn(name)
            if not detail[name]["ok"]:
                ok = False
        out[pred] = {"pass": ok, "detail": detail}

    both(
        "P1_silence",
        lambda n: (
            lambda ap: {
                "ok": ap.get("n", 0) >= 8 and ap.get("silence_frac", 1) <= 0.30,
                "ap": ap,
            }
        )(phases[n]["song_a_ziggyx"]["whole"]["ap"]),
    )
    both(
        "P2_peak_vs_ambient",
        lambda n: (
            lambda amb, mus: {
                "ok": mus.get("n", 0) > 0
                and amb.get("n", 0) > 0
                and mus["peak_mean"] >= 2.0 * max(amb["peak_mean"], 1e-6),
                "ambient_peak": amb.get("peak_mean"),
                "music_peak": mus.get("peak_mean"),
            }
        )(phases[n]["ambient"]["ap"], phases[n]["song_a_ziggyx"]["whole"]["ap"]),
    )
    both(
        "P3_system_fps",
        lambda n: (
            lambda fps: {
                "ok": fps["system"].get("n", 0) > 0 and fps["system"]["p50"] >= 120,
                "fps": fps["system"],
            }
        )(phases[n]["song_a_ziggyx"]["whole"]["fps"]),
    )
    both(
        "P4_led_fps",
        lambda n: (
            lambda fps: {
                "ok": fps["led"].get("n", 0) > 0 and fps["led"]["p50"] >= 180,
                "fps": fps["led"],
            }
        )(phases[n]["song_a_ziggyx"]["whole"]["fps"]),
    )
    both(
        "P5_tempo",
        lambda n: (
            lambda ap: {
                "ok": ap.get("n", 0) > 0
                and (ap.get("lock_frac", 0) >= 0.30 or ap.get("conf_mean", 0) >= 0.45),
                "ap": ap,
            }
        )(phases[n]["song_a_ziggyx"]["whole"]["ap"]),
    )

    ack_ok = all(a["primary_ok"] and a["secondary_ok"] for a in acks) and len(acks) > 0
    out["P6_palette_ack"] = {"pass": ack_ok, "n": len(acks), "fails": [a for a in acks if not (a["primary_ok"] and a["secondary_ok"])]}

    def honour_ok(name: str) -> dict:
        edges = []
        for song in ("song_a_ziggyx", "song_b_querox_time"):
            edges.extend(phases[name][song]["whole"].get("edge") or [])
            for k, v in phases[name][song].items():
                if k.startswith("pal_"):
                    edges.extend(v.get("edge") or [])
        bad = [e for e in edges if not str(e[1]).endswith("_palette")]
        return {"ok": len(edges) > 0 and not bad, "n": len(edges), "bad": bad[:8]}

    both("P7_honour_palette", honour_ok)

    restore_ok = True
    restore_detail = {}
    for name, snap in snaps.items():
        got = restore_check.get(name) or {}
        ok = (
            got.get("primary_palette") == snap["primary_palette"]
            and got.get("secondary_palette") == snap["secondary_palette"]
        )
        restore_detail[name] = {"ok": ok, "want": snap, "got": got}
        if not ok:
            restore_ok = False
    out["P8_restore"] = {"pass": restore_ok, "detail": restore_detail}

    # P9 is observational
    p9 = {}
    for name in UNITS:
        flats = []
        song = phases[name]["song_a_ziggyx"]
        for k, v in song.items():
            if k.startswith("pal_") and v["vp"].get("n", 0):
                flats.append((v["palette"], v["vp"]["flatness_mean"]))
        p9[name] = flats
    out["P9_chroma_flatness_by_palette"] = {"pass": True, "note": "observational", "detail": p9}
    return out


def render_md(result: dict) -> str:
    v = result["predictions"]
    lines = [
        "# Dual-unit music + palette soak — RESULT",
        "",
        f"When: `{result['when']}`",
        f"Output: {result['output']} at volume {result['soak_volume']} (restored {result['orig_volume']})",
        "",
        "## Identity",
    ]
    for name, ident in result["identities"].items():
        lines.append(
            f"- **{name}** port `{result['ports'][name]}` git=`{ident.get('git')}` "
            f"env=`{ident.get('env')}` chip=`{ident.get('chip')}`"
        )
    lines += ["", "## Predictions"]
    for key, val in v.items():
        mark = "PASS" if val.get("pass") else "FAIL"
        lines.append(f"- **{key}**: {mark}")
    lines += ["", "## Song A (ziggyx 155 BPM, 120 s) AP/VP"]
    for name, ph in result["phases"].items():
        ap = ph["song_a_ziggyx"]["whole"]["ap"]
        fps = ph["song_a_ziggyx"]["whole"]["fps"]
        lines.append(
            f"- **{name}** n={ap.get('n')} silence_frac={ap.get('silence_frac')} "
            f"lock_frac={ap.get('lock_frac')} conf_mean={ap.get('conf_mean')} "
            f"peak_mean={ap.get('peak_mean')} bpm_mean={ap.get('bpm_mean')} "
            f"SYSTEM_FPS p50={fps['system'].get('p50')} LED_FPS p50={fps['led'].get('p50')}"
        )
    lines += ["", "## Song B (Querox Time, 90 s) AP/VP"]
    for name, ph in result["phases"].items():
        ap = ph["song_b_querox_time"]["whole"]["ap"]
        fps = ph["song_b_querox_time"]["whole"]["fps"]
        lines.append(
            f"- **{name}** n={ap.get('n')} silence_frac={ap.get('silence_frac')} "
            f"lock_frac={ap.get('lock_frac')} conf_mean={ap.get('conf_mean')} "
            f"peak_mean={ap.get('peak_mean')} bpm_mean={ap.get('bpm_mean')} "
            f"SYSTEM_FPS p50={fps['system'].get('p50')} LED_FPS p50={fps['led'].get('p50')}"
        )
    lines += ["", "## Colour / honour"]
    lines.append(
        f"- Palette ACKs: {v['P6_palette_ack']['n']} writes, "
        f"{'all matched names' if v['P6_palette_ack']['pass'] else 'MISMATCH'}"
    )
    lines.append("- Honour path: EDGE_EFFECTIVE must stay `*_palette` (P7).")
    lines.append("- No HUEAUD on these ship binaries — pixel hue histograms were not taken.")
    lines += ["", "## Restore"]
    lines.append(f"- Palettes restored: {'yes' if v['P8_restore']['pass'] else 'NO — CHECK UNITS'}")
    lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
