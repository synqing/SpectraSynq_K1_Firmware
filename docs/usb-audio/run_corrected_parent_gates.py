#!/usr/bin/env python3
"""Runtime gates A16–A26 / A29 on the Main-RPL-parented USB-audio image.

Score serial + host USB/audio trees. Do not ask anyone to look at the plate.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from serial.tools import list_ports
import serial

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "docs/usb-audio/evidence/20260824T165900Z-corrected-parent"
FIXTURE = ROOT / "docs/usb-audio/evidence/20260824T122122Z/k1_usb_audio_fixture_12800_mono_s16.wav"
ESPTOOL = Path.home() / ".platformio/packages/tool-esptoolpy/esptool.py"
ESPTOOL_PY = Path.home() / ".platformio/penv/bin/python"
UAC_NAME = "TinyUSB UAC1"
K1_SERIAL = "9087A5453AB4"
MAC = "B4:3A:45:A5:87:90"
KV = re.compile(r"(\w+)=(-?\d+(?:\.\d+)?)")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def say(msg: str) -> None:
    print(f"[{utc_now()}] {msg}", flush=True)


def run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def list_usb_audio() -> dict:
    ports = [
        {
            "device": p.device,
            "vid": p.vid,
            "pid": p.pid,
            "serial": p.serial_number,
            "product": p.product,
        }
        for p in list_ports.comports()
        if p.vid
    ]
    audio = run(["SwitchAudioSource", "-a"]).stdout
    current = run(["SwitchAudioSource", "-c"]).stdout.strip()
    return {"ports": ports, "audio_devices": audio, "current_output": current}


def find_cdc() -> str | None:
    for p in list_ports.comports():
        if p.serial_number and K1_SERIAL in p.serial_number:
            return p.device
        if p.product and "SpectraSynq" in p.product:
            return p.device
    return None


def find_jtag() -> str | None:
    for p in list_ports.comports():
        ser = (p.serial_number or "").upper().replace("-", ":")
        if MAC in ser:
            return p.device
        if p.product and "JTAG" in p.product and p.vid == 0x303A:
            return p.device
    return None


def uac_present() -> bool:
    out = run(["SwitchAudioSource", "-a"]).stdout
    return UAC_NAME in out


def switch_output(name: str) -> None:
    r = run(["SwitchAudioSource", "-t", "output", "-s", name])
    if r.returncode != 0:
        say(f"SwitchAudioSource to {name!r} failed: {r.stderr or r.stdout}")


def parse_kv(line: str) -> dict:
    out = {}
    for k, v in KV.findall(line):
        out[k] = float(v) if "." in v else int(v)
    return out


class CdcTap:
    def __init__(self, path: Path):
        self.path = path
        self.lines: list[tuple[float, str]] = []
        self._stop = threading.Event()
        self._ser: serial.Serial | None = None
        self._thr: threading.Thread | None = None
        self.t0 = 0.0
        self.open_error: str | None = None

    def start(self, port: str) -> bool:
        try:
            self._ser = serial.Serial(port, 115200, timeout=0.2)
            self._ser.dtr = True
            self._ser.rts = False
        except Exception as exc:
            self.open_error = f"{type(exc).__name__}: {exc}"
            return False
        self.t0 = time.time()
        self._thr = threading.Thread(target=self._loop, daemon=True)
        self._thr.start()
        return True

    def _loop(self) -> None:
        buf = b""
        assert self._ser is not None
        while not self._stop.is_set():
            try:
                chunk = self._ser.read(4096)
            except Exception:
                break
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                line = raw.decode("utf-8", "replace").rstrip("\r")
                self.lines.append((time.time() - self.t0, line))

    def send(self, text: str) -> None:
        if self._ser is None:
            return
        self._ser.write(text.encode("utf-8"))
        self._ser.flush()

    def stop(self) -> None:
        self._stop.set()
        if self._thr:
            self._thr.join(timeout=2)
        if self._ser:
            try:
                self._ser.close()
            except Exception:
                pass
        body = "".join(f"{t:8.3f} {line}\n" for t, line in self.lines)
        write_text(self.path, body)

    def tagged(self, tag: str, t_min: float | None = None, t_max: float | None = None) -> list[tuple[float, str]]:
        out = []
        for t, line in self.lines:
            if tag not in line:
                continue
            if t_min is not None and t < t_min:
                continue
            if t_max is not None and t > t_max:
                continue
            out.append((t, line))
        return out


def capture_trees(prefix: str) -> None:
    sp_usb = run(["system_profiler", "SPUSBDataType"], timeout=90)
    write_text(EV / f"{prefix}_spusb.txt", sp_usb.stdout or sp_usb.stderr or "")
    sp_aud = run(["system_profiler", "SPAudioDataType"], timeout=90)
    write_text(EV / f"{prefix}_spaudio.txt", sp_aud.stdout or sp_aud.stderr or "")
    ioreg = run(["ioreg", "-p", "IOUSB", "-l", "-w", "0"], timeout=90)
    write_text(EV / f"{prefix}_ioreg.txt", ioreg.stdout or "")
    snapshot = list_usb_audio()
    write_text(EV / f"{prefix}_snapshot.json", json.dumps(snapshot, indent=2))


def play_fixture(seconds: float | None = None) -> subprocess.CompletedProcess:
    cmd = ["afplay"]
    if seconds is not None:
        cmd += ["-t", str(seconds)]
    cmd.append(str(FIXTURE))
    return subprocess.run(cmd, capture_output=True, text=True)


def phase_enum() -> dict:
    EV.mkdir(parents=True, exist_ok=True)
    subprocess.run(["open", "-g", "-a", "Audio MIDI Setup"], check=False)
    capture_trees("14")
    snap = json.loads((EV / "14_snapshot.json").read_text())
    audio = snap.get("audio_devices", "")
    spa = (EV / "14_spaudio.txt").read_text()
    rate_ok = ("12800" in spa) or ("12800" in audio)
    cdc = find_cdc()
    result = {
        "A16": "PASS" if cdc or "SpectraSynq" in json.dumps(snap) or UAC_NAME in audio else "FAIL",
        "A17": "PASS" if UAC_NAME in audio else "FAIL",
        "A18": "PASS" if (UAC_NAME in audio and rate_ok) else "FAIL",
        "cdc": cdc,
        "uac": UAC_NAME in audio,
        "rate_12800": rate_ok,
        "current_output": snap.get("current_output"),
    }
    write_text(EV / "14_enum.json", json.dumps(result, indent=2))
    say(f"enum {result}")
    return result


def score_fixture(tap: CdcTap, play_t0_offset: float, play_dur: float) -> dict:
    uac = tap.tagged("[UAC]", play_t0_offset, play_t0_offset + play_dur + 2)
    wf = tap.tagged("[USB-WF]", play_t0_offset, play_t0_offset + play_dur + 2)
    ap = tap.tagged("[AP]", play_t0_offset, play_t0_offset + play_dur + 2)
    parsed_uac = [(t, parse_kv(line)) for t, line in uac]
    parsed_wf = [(t, parse_kv(line)) for t, line in wf]
    parsed_ap = [(t, parse_kv(line)) for t, line in ap]

    def window(rows, a, b):
        return [kv for t, kv in rows if play_t0_offset + a <= t <= play_t0_offset + b]

    pre = window(parsed_uac, 0, 1.8)
    mid = window(parsed_uac, 7.0, 9.0)  # 440 Hz
    click = window(parsed_ap, 23.0, 41.0)
    sil_wf = window(parsed_wf, 0.2, 1.8)
    tone_wf = window(parsed_wf, 6.5, 9.0)

    bytes_delta = 0
    frames_delta = 0
    if len(parsed_uac) >= 2:
        a, b = parsed_uac[0][1], parsed_uac[-1][1]
        bytes_delta = int(b.get("bytes_received", 0) - a.get("bytes_received", 0))
        frames_delta = int(b.get("frames_consumed", 0) - a.get("frames_consumed", 0))

    def last_int(rows, key, default=0):
        return int(rows[-1][key]) if rows else default

    # Steady-state: 440 Hz window, counters must not climb.
    drop_ss = 0
    uf_ss = 0
    if len(mid) >= 2:
        drop_ss = int(mid[-1].get("frames_dropped_oldest", 0) - mid[0].get("frames_dropped_oldest", 0))
        uf_ss = int(mid[-1].get("underflows", 0) - mid[0].get("underflows", 0))

    sil_peak = max((kv.get("peak_scaled", 0) for kv in sil_wf), default=0)
    tone_peak = max((kv.get("peak_scaled", 0) for kv in tone_wf), default=0)
    onset_hits = sum(1 for kv in click if kv.get("onset", 0) == 1 or kv.get("bass", 0) == 1)
    bpm_vals = [kv.get("bpm", 0) for kv in click if kv.get("bpm", 0)]

    last = parsed_uac[-1][1] if parsed_uac else {}
    out = {
        "uac_lines": len(uac),
        "wf_lines": len(wf),
        "ap_lines": len(ap),
        "bytes_delta": bytes_delta,
        "frames_delta": frames_delta,
        "bytes_per_s": bytes_delta / max(play_dur, 1),
        "frames_per_s": frames_delta / max(play_dur, 1),
        "rate": last.get("rate"),
        "valid_stream": last.get("valid_stream"),
        "speaker_enabled": last.get("speaker_enabled"),
        "dropped_total": last.get("frames_dropped_oldest"),
        "underflows_total": last.get("underflows"),
        "drop_ss_delta": drop_ss,
        "underflow_ss_delta": uf_ss,
        "queue_high_water": last.get("queue_high_water"),
        "heap_free": last.get("heap_free"),
        "reset_reason": last.get("reset_reason"),
        "stream_generation": last.get("stream_generation"),
        "rate_mismatches": last.get("rate_mismatches"),
        "sil_peak_scaled": sil_peak,
        "tone_peak_scaled": tone_peak,
        "onset_hits_clicks": onset_hits,
        "bpm_during_clicks": bpm_vals[-3:] if bpm_vals else [],
        "A19": "PASS" if bytes_delta > 10000 else "FAIL",
        "A20": "PASS" if frames_delta > 400 else "FAIL",
        "A21": "PASS" if tone_peak > sil_peak and tone_peak > 0.05 else "FAIL",
        "A22": "PASS" if onset_hits >= 3 or any(110 <= b <= 130 for b in bpm_vals) else "FAIL",
        "A23": "PASS" if drop_ss == 0 and uf_ss == 0 else "FAIL",
    }
    write_text(EV / "15_fixture_score.json", json.dumps(out, indent=2))
    return out


def phase_fixture(restore_output: str) -> dict:
    cdc = find_cdc()
    if not cdc:
        say("NO CDC for fixture")
        return {"error": "no_cdc"}
    tap = CdcTap(EV / "15_serial.txt")
    if not tap.start(cdc):
        say(f"CDC open failed {tap.open_error}")
        return {"error": tap.open_error}
    time.sleep(1.5)
    tap.send(":ap_stream=on\n")
    time.sleep(1.0)
    orig = restore_output
    switch_output(UAC_NAME)
    time.sleep(0.4)
    play_offset = time.time() - tap.t0
    say(f"afplay fixture from tap+{play_offset:.2f}s")
    r = play_fixture()
    play_dur = time.time() - tap.t0 - play_offset
    say(f"afplay rc={r.returncode} dur={play_dur:.1f}")
    time.sleep(1.5)
    score = score_fixture(tap, play_offset, play_dur)
    tap.stop()
    switch_output(orig)
    score["afplay_rc"] = r.returncode
    score["play_dur"] = play_dur
    write_text(EV / "15_afplay.txt", f"rc={r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}\n")
    say(f"fixture score { {k: score[k] for k in score if k.startswith('A') or k in ('bytes_delta','frames_delta','drop_ss_delta','underflow_ss_delta','tone_peak_scaled','onset_hits_clicks')} }")
    return score


def enter_download_and_reset() -> bool:
    cdc = find_cdc()
    if not cdc:
        say("reconnect: no CDC")
        return False
    try:
        s = serial.Serial(cdc, 1200)
        time.sleep(0.15)
        s.close()
    except Exception as exc:
        say(f"1200 fail {exc}")
        return False
    deadline = time.time() + 6
    jtag = None
    while time.time() < deadline:
        if not uac_present():
            jtag = find_jtag()
            if jtag:
                break
        time.sleep(0.2)
    if not jtag:
        say("reconnect: no JTAG after 1200")
        return False
    py = str(ESPTOOL_PY if ESPTOOL_PY.exists() else sys.executable)
    cmd = [
        py,
        str(ESPTOOL),
        "--chip",
        "esp32s3",
        "--port",
        jtag,
        "--before",
        "default_reset",
        "--after",
        "hard_reset",
        "chip_id",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    write_text(EV / "reconnect_last_esptool.txt", r.stdout + "\n" + r.stderr)
    if "ESP32-S3" not in r.stdout and r.returncode != 0:
        say(f"chip_id weak rc={r.returncode}")
    time.sleep(1.5)
    # After USB-JTAG hard_reset the PHY can stay on Serial-JTAG until a host
    # open; that open is what lets TinyUSB take the device (seen after flash).
    jtag2 = find_jtag()
    if jtag2 and not uac_present():
        try:
            s = serial.Serial(jtag2, 115200, timeout=0.2)
            s.dtr = False
            time.sleep(0.2)
            s.close()
        except Exception as exc:
            say(f"jtag nudge {type(exc).__name__}: {exc}")
    deadline = time.time() + 15
    while time.time() < deadline:
        if uac_present() and find_cdc():
            return True
        time.sleep(0.3)
    say("reconnect: UAC/CDC did not return")
    return False


def phase_reconnect(restore_output: str, cycles: int = 10) -> dict:
    rows = []
    ok = 0
    switch_output(UAC_NAME)
    for i in range(1, cycles + 1):
        say(f"reconnect cycle {i}/{cycles}")
        before_gen = None
        cdc = find_cdc()
        tap = None
        if cdc:
            tap = CdcTap(EV / f"26_cycle_{i:02d}_pre.txt")
            if tap.start(cdc):
                time.sleep(1.2)
                uacs = tap.tagged("[UAC]")
                if uacs:
                    before_gen = parse_kv(uacs[-1][1]).get("stream_generation")
                tap.stop()
                time.sleep(0.4)
        removed_ok = enter_download_and_reset()
        time.sleep(1.0)
        cdc2 = find_cdc()
        pcm_ok = False
        after_gen = None
        heap = None
        if removed_ok and cdc2:
            tap2 = CdcTap(EV / f"26_cycle_{i:02d}_post.txt")
            if tap2.start(cdc2):
                time.sleep(1.0)
                switch_output(UAC_NAME)
                off = time.time() - tap2.t0
                play_fixture(seconds=6)
                time.sleep(0.8)
                uacs = tap2.tagged("[UAC]", off)
                parsed = [parse_kv(line) for _, line in uacs]
                if len(parsed) >= 2:
                    delta = parsed[-1].get("bytes_received", 0) - parsed[0].get("bytes_received", 0)
                    pcm_ok = delta > 2000
                    after_gen = parsed[-1].get("stream_generation")
                    heap = parsed[-1].get("heap_free")
                tap2.stop()
        cycle = {
            "i": i,
            "removed_and_reenum": removed_ok,
            "pcm_ok": pcm_ok,
            "gen_before": before_gen,
            "gen_after": after_gen,
            "heap": heap,
        }
        rows.append(cycle)
        if removed_ok and pcm_ok:
            ok += 1
        say(f"  cycle {i}: {cycle}")
    switch_output(restore_output)
    result = {"ok": ok, "cycles": cycles, "rows": rows, "A26": "PASS" if ok == cycles else "FAIL"}
    write_text(EV / "26_reconnect.json", json.dumps(result, indent=2))
    return result


def phase_soak(restore_output: str, minutes: float = 30.0) -> dict:
    cdc = find_cdc()
    if not cdc:
        return {"error": "no_cdc"}
    tap = CdcTap(EV / "25_soak_serial.txt")
    if not tap.start(cdc):
        return {"error": tap.open_error}
    time.sleep(1.0)
    tap.send(":ap_stream=on\n")
    switch_output(UAC_NAME)
    t_end = time.time() + minutes * 60.0
    plays = 0
    say(f"soak start {minutes} min")
    while time.time() < t_end:
        r = play_fixture()
        plays += 1
        say(f"soak play {plays} rc={r.returncode} remain={t_end - time.time():.0f}s")
        if not uac_present() or not find_cdc():
            say("soak lost UAC/CDC")
            break
    time.sleep(1.0)
    uac = tap.tagged("[UAC]")
    parsed = [(t, parse_kv(line)) for t, line in uac]
    tap.stop()
    switch_output(restore_output)
    heaps = [kv.get("heap_free") for _, kv in parsed if "heap_free" in kv]
    resets = {kv.get("reset_reason") for _, kv in parsed}
    drops = [kv.get("frames_dropped_oldest", 0) for _, kv in parsed]
    ufs = [kv.get("underflows", 0) for _, kv in parsed]
    gens = [kv.get("stream_generation") for _, kv in parsed if "stream_generation" in kv]
    hwm = [kv.get("queue_high_water") for _, kv in parsed if "queue_high_water" in kv]
    # Steady-state: ignore first 15 s of soak.
    ss = [(t, kv) for t, kv in parsed if t >= 15]
    drop_ss = 0
    uf_ss = 0
    if len(ss) >= 2:
        drop_ss = int(ss[-1][1].get("frames_dropped_oldest", 0) - ss[0][1].get("frames_dropped_oldest", 0))
        uf_ss = int(ss[-1][1].get("underflows", 0) - ss[0][1].get("underflows", 0))
    heap_delta = (heaps[-1] - heaps[0]) if len(heaps) >= 2 else None
    result = {
        "plays": plays,
        "uac_lines": len(uac),
        "heap_first": heaps[0] if heaps else None,
        "heap_last": heaps[-1] if heaps else None,
        "heap_delta": heap_delta,
        "reset_reasons": sorted(x for x in resets if x is not None),
        "drop_ss_delta": drop_ss,
        "underflow_ss_delta": uf_ss,
        "dropped_last": drops[-1] if drops else None,
        "underflows_last": ufs[-1] if ufs else None,
        "stream_generation_last": gens[-1] if gens else None,
        "queue_high_water_max": max(hwm) if hwm else None,
        "A25": "PASS" if plays >= 35 and drop_ss == 0 and uf_ss == 0 and len(resets) <= 1 else "FAIL",
    }
    write_text(EV / "25_soak.json", json.dumps(result, indent=2))
    say(f"soak done {result}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["enum", "fixture", "reconnect", "soak", "all"], default="all")
    parser.add_argument("--soak-minutes", type=float, default=30.0)
    parser.add_argument("--reconnect-cycles", type=int, default=10)
    args = parser.parse_args()
    EV.mkdir(parents=True, exist_ok=True)
    orig = run(["SwitchAudioSource", "-c"]).stdout.strip() or "Multi-Output Device"
    write_text(EV / "00_original_output.txt", orig + "\n")
    say(f"original output={orig!r}")
    summary: dict = {"original_output": orig}
    try:
        if args.phase in ("enum", "all"):
            summary["enum"] = phase_enum()
        if args.phase in ("fixture", "all"):
            summary["fixture"] = phase_fixture(orig)
        if args.phase in ("reconnect", "all"):
            summary["reconnect"] = phase_reconnect(orig, args.reconnect_cycles)
        if args.phase in ("soak", "all"):
            summary["soak"] = phase_soak(orig, args.soak_minutes)
    finally:
        switch_output(orig)
        write_text(EV / "99_summary.json", json.dumps(summary, indent=2, default=str))
        say("DONE")
        print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
