#!/usr/bin/env python3
"""K1-FE-SHOW M2 emulator gates G1-G4 (host only; never opens /dev/cu.*).

One command builds a firmware export in the esp-emu replay, plays a prepared Prim8 stream through
the PROTOTYPE RX-record adapter (lane-c-emu, M1) and judges four gates on BOTH edges' native
payloads (ws2816_wire = edge A, ws2816_wire_secondary = edge B; 160 px x G16BE R16BE B16BE each,
captured after the Lever-2 pack, before FastLED.show()). That is the emulator's WS2816 capture tap,
NOT the bench build's WS2812 8-bit output: same render state, different wire format.
Emulator timing is lockstep (every hop shown exactly once); nothing here is physical latency.

  G1 repeatability   same stream, same PCM, same initial state, two runs -> both edges byte-identical
                     (plus the G3 continuous run, which shares the input prefix, must equal run 1).
  G2 independence    same stream + initial state, three microphone PCMs (the passage, all zeros, a
                     different real-music passage) -> both edges byte-identical for every pair.
  G3 seek            the same musical window reached by continuous play, a forward seek and a
                     backward seek (audio and stream jump together) -> after the declared
                     reconstruction interval both edges byte-identical for every pair.
  G4 M2 stream       the M2-compiled stream and its reopened-and-recompiled twin -> both runs
                     accepted, stream drove AUTHORED, no hotkey state changes, both edges identical.

Usage:
  gates.py --src <firmware export dir> [--profile fe|scenario] [--mode 32] [--gates G1,G2,G3,G4]
           [--m2-stream X.prsm --m2-twin Y.prsm [--m2-window 75:155]] [--label NAME] [--detach]
  --profile fe       = k1_fe_emu (FE / B489 lineage; adds the B489 bench flags via the adapter)
  --profile scenario = k1_main_rpl_emu (Main RPL: k1_main_rpl_im69d + the 4 declared emulator adapters)
  gates.py --analyse <run dir>          (re-judge an existing run; no emulator)

The export is copied into m2-emu/work/src-<tree hash>/ (one run per source tree at a time) (the --src folder is never modified);
if it lacks the RX adapter, PROTOTYPE-ADAPTER-ed0aa984.diff is applied there with patch -p1.
Exit code = number of selected gates that are not PASS (FAIL, BLOCKED). --detach returns 0 at once
and writes the real exit code to <run dir>/exit_code.txt.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

M2 = Path(__file__).resolve().parent
M1 = M2.parent.parent / "k1-fe-show-m1_20261109"
LANEB = M1 / "lane-b"
sys.path.insert(0, str(LANEB))
import prim8_stream as ps  # noqa: E402

DEFAULT_SRC = M2 / "src-ed0aa984"
ADAPTER = M2 / "PROTOTYPE-ADAPTER-ed0aa984.diff"
ADAPTERS = {"fe": [(ADAPTER, "-p1"), (M2 / "PROTOTYPE-ADAPTER-407fdf6f.diff", "-p2")],
            # Main RPL profile: RX adapter only (the B489 bench flags belong to k1_fe_bench_b489, not k1_main_rpl_im69d)
            "scenario": [(M2 / "PROTOTYPE-ADAPTER-ed0aa984-noflags.diff", "-p1")]}
EMU_ENV = {"fe": "k1_fe_emu", "scenario": "k1_main_rpl_emu"}
OTA1_BYTES = 0x640000                 # app1/ota_1 partition the scenario blob lives in (6.25 MB)
M1_STREAM = M1 / "lane-c-emu" / "stream" / "loreen_75_155_120hz_v2.prsm"
M1_STREAM_SHA = "eafb72aecbccedba880364930898420a727d284dbe21182f18c6bff3f1258fdd"
ESP_EMU = "/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-ESP-Emulator/tools/esp-emu-pin/bin/esp-emu"
LOREEN_SHA = "a62e1f095de9c3e06563b40d0842acf64ca1bf6fece341a15190cb1c11ab9b0f"
LOREEN_EXCERPT_START_S = 56.0          # loreen_src excerpt in s3_music_regression.json: 56.0-155.0 s
LOREEN_EXCERPT_END_S = 155.0
BENCH_FLAGS = ["K1_AP_SUBSONIC_HPF_V1", "K1_TEMPO_CONSUMER_BANDS_V1", "K1_FX_BATTERY"]

RATE = 12800
HOP = 96
HOP_US = 7500
REC_DATA = 128
AUTHORED = 2                           # K1_SRC_AUTHORED (k1_authored_source.h)

# ---- G1-G3 timeline (original-file seconds of the Loreen asset; M1 passage 75-155 s) --------------
P0 = 75.0                              # passage start = hop 0 of every G1/G2 case
P_END = 155.0
# G2 "different real music": loreen original 56.0-136.0 s, the scenario's own music_chorus start
# (56 s) extended to passage length. Every hop hears different audio from the passage at 75-155 s.
OTHER = (56.0, 136.0)
# G3: landing position D = 105.0 s (chorus; authored pressure 0.50-1.00, mean 0.73 over 105-115 s,
# so mode 32 trails are lit throughout). Seek offsets are whole multiples of 75 ms = 10 hops = 9
# ticks at 120 Hz, so after the seek every PCM sample, PRSM tick and arrival hop lands at exactly the
# same phase as in continuous play; any difference is renderer state, not resampling.
G3_D = 105.0
G3_FWD_AT_RUN = 10.05                  # play 75.00-85.05 s, then jump forward to 105 s (+19.95 s)
G3_BACK_AT_RUN = 50.025                # play 75.00-125.025 s, then jump back to 105 s (-20.025 s)
G3_WINDOW_HOPS = 1334                  # 10.005 s of the landing window captured densely (every hop)
# Declared reconstruction interval R. The slowest decaying history in Waveform Hybrid K1 (mode 32)
# is the trail: fade = exp(-(0.8 + 3.5*peak)*dt) (light_mode_waveform_hybrid_k1.cpp:297-307). With
# authored pressure >= 0.50 everywhere in 105-115 s the decay rate is >= 2.55/s, so a full-scale
# trail value falls below one 16-bit LSB (2^-16) within ln(65536)/2.55 = 4.35 s. R = 5.0 s adds
# margin; the colour EMAs (tau 80 ms) and peak EMAs are far faster. State that never decays (auto
# colour shift, hue walk, live AGC) cannot be covered by any R: that is what G3 is meant to catch.
G3_R_HOPS = 667                        # 5.0025 s
G3_COMPARE_HOPS = G3_WINDOW_HOPS - G3_R_HOPS   # 667 hops (5.0025 s) judged after R

EXPECTED_TODAY = {
    "G1": "PASS (M1 C4: three authored repeats byte-identical on ed0aa984)",
    "G2": "FAIL (M1 C4: authored over zero PCM differed on 1778/1778 frames; live peak is OR-ed in, "
          "light_mode_waveform_hybrid_k1.cpp:116)",
    "G3": "FAIL (no seek reconstruction; bench S5 colour changed and stayed after a backward seek)",
    "G4": "PASS if the twin is byte-identical and the stream is accepted (determinism, G1)",
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(Path(p).read_bytes())


# ------------------------------------------------------------------------------------------------
# Source preparation
# ------------------------------------------------------------------------------------------------

def tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for rel in ("SPECTRASYNQ_K1_FIRMWARE", "platformio.ini", "tools/esp_emulator", "scripts/platformio"):
        p = root / rel
        files = [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file() and "__pycache__" not in q.parts)
        for f in files:
            h.update(str(f.relative_to(root)).encode() + b"\0" + hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()


def prepare_work(src: Path, label: str, log, profile: str = "fe") -> tuple[Path, dict]:
    src = src.resolve()
    th = tree_hash(src)
    work = M2 / "work" / f"src-{th[:12]}"     # keyed by source tree: reuses the build cache; one run per source at a time
    work.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["rsync", "-a", "--exclude", "/.pio", "--exclude", ".git", "--exclude", "__pycache__",
                    f"{src}/", f"{work}/"], check=True)
    if not (work / ".pio" / "libdeps").is_dir():
        libdeps = src / ".pio" / "libdeps"
        if not libdeps.is_dir():
            libdeps = DEFAULT_SRC / ".pio" / "libdeps"
        (work / ".pio").mkdir(exist_ok=True)
        shutil.copytree(libdeps, work / ".pio" / "libdeps", symlinks=True)
    ident = {"src": str(src), "src_tree_sha256": th, "work": str(work)}
    idf = src / ".k1-source-identity.json"
    if idf.is_file():
        ident["src_identity"] = json.loads(idf.read_text())
    fixture = (work / "SPECTRASYNQ_K1_FIRMWARE/audio/k1_emu_fixture.cpp").read_text(errors="replace")
    runpy = (work / "tools/esp_emulator/run.py").read_text(errors="replace")
    if "k1_emu_fixture_rx_read" in fixture and "rx_stream" in runpy:
        ident["adapter"] = "present in source"
    elif "k1_emu_fixture_rx_read" in fixture or "rx_stream" in runpy:
        raise RuntimeError("RX adapter only partly present in the source; refusing to guess")
    else:
        errs = []
        for diff, strip in ADAPTERS[profile]:              # ed0aa984 variant first (adds the bench flags), then 407fdf6f
            dry = subprocess.run(["patch", strip, "--dry-run", "-s", "-i", str(diff)], cwd=work,
                                 capture_output=True, text=True)
            if dry.returncode == 0:
                subprocess.run(["patch", strip, "-s", "-i", str(diff)], cwd=work, check=True)
                ident["adapter"] = f"applied by gates.py: {diff.name} sha256 {sha256_file(diff)}"
                break
            errs.append(f"{diff.name}: {dry.stdout}{dry.stderr}")
        else:
            raise RuntimeError("no adapter diff applies: " + " | ".join(errs))
    pio = (work / "platformio.ini").read_text()
    sect = pio[pio.index(f"[env:{EMU_ENV[profile]}]"):]
    sect = sect[:sect.find("\n[env:", 1)] if "\n[env:" in sect[1:] else sect
    ident["profile"] = profile
    ident["emu_env"] = EMU_ENV[profile]
    ident["bench_flags_in_k1_fe_emu"] = [f for f in BENCH_FLAGS if f"-D{f}" in sect]
    ident["work_tree_sha256"] = tree_hash(work)
    log(f"work copy {work} ({ident['adapter']})")
    return work, ident


# ------------------------------------------------------------------------------------------------
# Stream schedules (RX records) and PCM layouts
# ------------------------------------------------------------------------------------------------

def read_frames(path: Path) -> dict[int, bytes]:
    data = Path(path).read_bytes()
    if len(data) % ps.FRAME_LEN:
        raise ValueError(f"{path}: {len(data)} bytes is not a whole number of frames")
    out = {}
    for k in range(0, len(data), ps.FRAME_LEN):
        f = data[k:k + ps.FRAME_LEN]
        out[ps.decode_frame(f)["t_us"]] = f
    return out


def arrival_hop(run_us: int) -> int:
    """Bytes for a frame due at run time t are consumed before hop ceil(t / 7.5 ms) - 1 (M1 C4 model)."""
    return max(0, -(-run_us // HOP_US) - 1)


def schedule(frames: dict[int, bytes], segments, total_hops: int):
    """segments: [(run_start_us, mus_start_us, dur_us)], contiguous in run time. Each segment sends
    the stream frames whose musical t lies in [mus_start, mus_start + dur), at run time
    t - mus_start + run_start, with RESYNC_PREAMBLE before its first frame (new epoch).
    Returns (packed records, info)."""
    per_hop: dict[int, bytearray] = {}
    sent = dropped = 0
    for run0, mus0, dur in segments:
        first = True
        for t in sorted(t for t in frames if mus0 <= t < mus0 + dur):
            h = arrival_hop(t - mus0 + run0)
            if h >= total_hops:
                dropped += 1
                continue
            buf = per_hop.setdefault(h, bytearray())
            if first:
                buf += ps.RESYNC_PREAMBLE
                first = False
            buf += ps.wire_packets(frames[t])[0]
            sent += 1
    raw = bytearray()
    for h in sorted(per_hop):
        b = bytes(per_hop[h])
        if len(b) > REC_DATA:
            raise ValueError(f"hop {h} carries {len(b)} bytes > {REC_DATA} (stream rate too high for one record per hop)")
        raw += struct.pack("<II", h, len(b)) + b + b"\0" * (REC_DATA - len(b))
    return bytes(raw), {"frames_sent": sent, "frames_after_end_dropped": dropped, "records": len(per_hop),
                        "bytes": sum(len(v) for v in per_hop.values())}


def us(s: float) -> int:
    return int(round(s * 1_000_000))


def total_hops_for(seconds: float) -> int:
    samples = int(round(seconds * 1000)) * RATE // 1000
    return -(-samples // HOP)


# ------------------------------------------------------------------------------------------------
# Scenario
# ------------------------------------------------------------------------------------------------

def loreen_seg(a: float, b: float, label: str) -> dict:
    lo = round((a - LOREEN_EXCERPT_START_S) * 1000)
    hi = round((b - LOREEN_EXCERPT_START_S) * 1000)
    assert abs(lo - (a - LOREEN_EXCERPT_START_S) * 1000) < 1e-6 and abs(hi - (b - LOREEN_EXCERPT_START_S) * 1000) < 1e-6
    return {"asset": "loreen_src", "from_ms": lo, "to_ms": hi, "label": label}


def m2_stream_info(path: Path) -> dict:
    side = Path(str(path) + ".json")
    if not side.is_file():
        alt = path.with_suffix(".prsm.json")
        side = alt if alt.is_file() else None
    frames = read_frames(path)
    ts = sorted(frames)
    hz = ps.decode_frame(frames[ts[0]])["hz"]
    info = {"path": str(path), "sha256": sha256_file(path), "frames": len(frames), "hz": hz,
            "t_first_s": ts[0] / 1e6, "t_last_s": ts[-1] / 1e6, "sidecar": str(side) if side else None}
    if side:
        sc = json.loads(side.read_text())
        info["sidecar_sha256"] = sha256_file(side)
        info["asset"] = sc.get("asset")
        info["passage_start_sample"] = sc.get("passage_start_sample")
        info["epochs"] = sc.get("epochs")
    return info


def resolve_audio(info: dict, override: Path | None) -> Path:
    """The M2 sidecar names its asset by sha256 + path_hint (may be relative). Find the file."""
    want = (info.get("asset") or {}).get("sha256")
    hint = (info.get("asset") or {}).get("path_hint") or ""
    cands = []
    if override:
        cands.append(Path(override))
    if hint and Path(hint).is_absolute():
        cands.append(Path(hint))
    side = Path(info["sidecar"]).parent if info.get("sidecar") else Path(info["path"]).parent
    roots = [side, side.parent, M2.parent / "m2-compose", M2.parent / "m2-analysis"]
    name = Path(hint).name
    for r in roots:
        if name and r.is_dir():
            cands += sorted(q for q in r.rglob(name) if "venv" not in q.parts)[:20]
    for c in cands:
        if c.is_file() and (want is None or sha256_file(c) == want):
            return c.resolve()
    raise RuntimeError(f"G4 asset sha256 {want} ({hint}) not found; pass --m2-audio")


def build_cases(gates: list[str], mode: int, sched_dir: Path, m2: dict | None, m2_twin: dict | None,
                m2_audio: Path | None = None, inventory: dict | None = None, m2_window=(75.0, 155.0)):
    """Returns (assets, cases, schedules, plan) to merge into the scenario."""
    assets, cases, sched, plan = {}, {}, {}, {}
    m1 = read_frames(M1_STREAM)
    every6 = {"start_hop": 0, "end_hop": None, "every": 6}

    def add(cid, purpose, pcm_id, rx_name, rx_raw, rx_info, capture, plan_entry, pcm_hops=None):
        if pcm_hops is not None:
            est = 256 + 96 * 4 + pcm_hops * HOP * 2 + len(rx_raw) + 4
            if est > OTA1_BYTES:
                raise RuntimeError(f"{cid.split('-')[0].upper()} case {cid}: scenario blob ~{est} B (PCM {pcm_hops} hops + {len(rx_raw)} B RX) "
                                   f"exceeds ota_1 {OTA1_BYTES} B; use a shorter window")
        p = sched_dir / f"{rx_name}.rx"
        p.write_bytes(rx_raw)
        sched[rx_name] = {"schedule": str(p), "sha256": sha256_bytes(rx_raw), **rx_info}
        cases[cid] = {"purpose": purpose, "pcm": pcm_id, "epoch": {"policy": "declared", "us": 1000000},
                      "partial_hop": "zero_pad", "composition": "m2_gates", "capture": capture,
                      "rx_stream": {"schedule": str(p), "sha256": sched[rx_name]["sha256"],
                                    "note": "PROTOTYPE ADAPTER (lane-c-emu RX records)"}}
        plan[cid] = plan_entry

    full = P_END - P0
    th_full = total_hops_for(full)
    full_seg = [(0, us(P0), us(full))]
    if {"G1", "G2"} & set(gates):
        assets["g_passage"] = {"kind": "concat", "qualification": "real_music",
                               "segments": [loreen_seg(P0, P_END, "original 75.0-155.0 s (M1 passage)")],
                               "origin": "M1 lane-a passage inside loreen_src"}
        raw, info = schedule(m1, full_seg, th_full)
        n = "m1_full"
        if "G1" in gates or "G2" in gates:
            add("g1-a1", "G1/G2: M1 stream over the passage PCM, run 1.", "g_passage", n, raw, info, every6,
                {"musical_offset_hops": 0})
        if "G1" in gates:
            cases["g1-a2"] = dict(cases["g1-a1"], purpose="G1: identical inputs, run 2.")
            plan["g1-a2"] = {"musical_offset_hops": 0}
    if "G2" in gates:
        assets["g_zero"] = {"kind": "concat", "qualification": "diagnostic_composite",
                            "segments": [{"zeros_ms": int(full * 1000), "label": "declared all-zero PCM, passage length"}],
                            "origin": "G2 live-independence control"}
        assets["g_other"] = {"kind": "concat", "qualification": "real_music",
                             "segments": [loreen_seg(*OTHER, "original 56.0-136.0 s (different real music at every hop)")],
                             "origin": "G2: s3_music_regression.json loreen_src, music_chorus start extended to 80 s"}
        cases["g2-zero"] = dict(cases["g1-a1"], pcm="g_zero", purpose="G2: same stream, all-zero microphone PCM.")
        cases["g2-other"] = dict(cases["g1-a1"], pcm="g_other", purpose="G2: same stream, different real-music PCM.")
        plan["g2-zero"] = plan["g2-other"] = {"musical_offset_hops": 0}
    if "G3" in gates:
        d_hop = round((G3_D - P0) * 1e6) // HOP_US                     # 4000
        win_end_s = G3_D + G3_WINDOW_HOPS * HOP_US / 1e6               # 115.005 s
        layouts = {
            "g3-cont": [(P0, P0, win_end_s - P0)],
            "g3-fwd": [(P0, P0, G3_FWD_AT_RUN), (P0 + G3_FWD_AT_RUN, G3_D, win_end_s - G3_D)],
            "g3-back": [(P0, P0, G3_BACK_AT_RUN), (P0 + G3_BACK_AT_RUN, G3_D, win_end_s - G3_D)],
        }
        for cid, segs in layouts.items():
            run_len = sum(s[2] for s in segs)
            th = total_hops_for(run_len)
            aid = f"g3_{cid[3:]}"
            assets[aid] = {"kind": "concat", "qualification": "real_music",
                           "segments": [loreen_seg(m, m + d, f"original {m:.3f}-{m + d:.3f} s") for _, m, d in segs],
                           "origin": "G3: audio jumps with the stream (as the bench player seeks both)"}
            r_last, m_last, _ = segs[-1]
            land_run_hop = round((r_last - P0 + G3_D - m_last) * 1e6) // HOP_US
            off = d_hop - land_run_hop
            raw, info = schedule(m1, [(us(r - P0), us(m), us(dd)) for r, m, dd in segs], th)
            add(cid, f"G3: {cid[3:]} reaching 105.0 s; dense capture of the landing window.", aid, cid, raw, info,
                {"start_hop": land_run_hop, "end_hop": land_run_hop + G3_WINDOW_HOPS, "every": 1},
                {"musical_offset_hops": off, "landing_run_hop": land_run_hop, "segments_s": segs})
    if "G4" in gates and m2:
        for cid, info_ in (("g4-m2", m2), ("g4-twin", m2_twin)):
            if not info_:
                continue
            fr = read_frames(Path(info_["path"]))
            ts = sorted(fr)
            t0 = info_["t_first_s"]
            asset = info_.get("asset") or {}
            if "passage_start_sample" in info_ and info_["passage_start_sample"] is not None and asset.get("sample_rate"):
                t0 = info_["passage_start_sample"] / asset["sample_rate"]
            t0 = round(t0 * 1000) / 1000                                # whole ms for the concat
            t_end = round((ts[-1] / 1e6 + 1 / info_["hz"]) * 1000) / 1000
            if m2_window:                                                # play only [w0, w1) of the stream
                t0, t_end = max(t0, m2_window[0]), min(t_end, m2_window[1])
            aid = "g4_passage"
            if asset.get("sha256") == LOREEN_SHA and LOREEN_EXCERPT_START_S <= t0 and t_end <= LOREEN_EXCERPT_END_S:
                assets[aid] = {"kind": "concat", "qualification": "real_music",
                               "segments": [loreen_seg(t0, t_end, f"original {t0:.3f}-{t_end:.3f} s (M2 stream span)")],
                               "origin": "G4: M2 stream's own passage inside loreen_src"}
            else:
                audio = resolve_audio(info_, m2_audio)
                inventory["fixtures"] = [{"id": "m2_asset", "path": str(audio), "status": "active",
                                          "required": False, "fixture_type": "m2_stream_asset"}]
                assets[aid] = {"kind": "inventory_excerpt", "inventory": "tools/esp_emulator/m2_inventory.json",
                               "fixture_id": "m2_asset", "source_sha256": asset.get("sha256"),
                               "excerpt": {"start_ms": int(round(t0 * 1000)), "duration_ms": int(round((t_end - t0) * 1000))},
                               "conversion": {"tool": "ffmpeg", "rate_hz": RATE, "channels": 1,
                                              "downmix": "ffmpeg -ac 1 (mean of L/R)", "resampler": "ffmpeg default (swr)",
                                              "gain": {"peak": 4096, "rule": "same rule as loreen_src: excerpt peak -> 4096 (-18 dBFS)"}},
                               "qualification": "real_music", "origin": f"G4: M2 stream asset {audio.name}"}
            # ffmpeg excerpts may end a few samples short of the nominal span: keep the last 2 hops free
            # of RX records so a short decode can never put a record beyond the run's total hops.
            th = total_hops_for(t_end - t0) - 2
            raw, info = schedule(fr, [(0, us(t0), us(t_end - t0))], th)
            # Declared seeks inside the stream (seq/t_us jumps) are sent as recorded: frames go out in
            # t_us order of the file only when t_us is monotonic. A non-monotonic stream is BLOCKED.
            data = Path(info_["path"]).read_bytes()
            order = [ps.decode_frame(data[k:k + 34])["t_us"] for k in range(0, len(data), 34)]
            if order != sorted(order):
                raise RuntimeError("M2 stream t_us is not monotonic (in-stream seek); G4 needs the run-time map")
            every = max(1, -(-th // 1800))
            add(cid, f"G4: {Path(info_['path']).name}, window {t0:.3f}-{t_end:.3f} s.", aid, cid, raw, info,
                {"start_hop": 0, "end_hop": None, "every": every},
                {"musical_offset_hops": 0, "t0_s": t0, "t_end_s": t_end,
                 "first_frame_seq_sent": ps.decode_frame(fr[min(t for t in fr if t >= us(t0))])["seq"]},
                pcm_hops=th + 2)
    return assets, cases, sched, plan


def write_scenario(work: Path, run_dir: Path, gates, mode, m2, m2_twin, ident, m2_audio=None, m2_window=(75.0, 155.0)) -> tuple[Path, dict]:
    sc = json.loads((work / "tools/esp_emulator/s3_music_regression.json").read_text())
    sc["name"] = "k1-fe-show-m2-emu-gates"
    sc["description"] = ("M2 emulator gates G1-G4 (m2-emu/gates.py). PROTOTYPE ADAPTER RX records; "
                         "Lane B guarded packets + resync preamble.")
    if ident.get("profile", "fe") == "fe":
        sc["profile"]["adapter_flags"] += ident["bench_flags_in_k1_fe_emu"]
    sched_dir = run_dir / "schedules"
    sched_dir.mkdir(parents=True, exist_ok=True)
    inventory: dict = {}
    assets, cases, sched, plan = build_cases(gates, mode, sched_dir, m2, m2_twin, m2_audio, inventory, m2_window)
    if inventory:
        (work / "tools/esp_emulator/m2_inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
        shutil.copy(work / "tools/esp_emulator/m2_inventory.json", run_dir / "m2_inventory.json")
    sc["assets"].update(assets)
    sc["compositions"]["m2_gates"] = {"commands": [f"set_mode={mode}", f"secondary_mode={mode}", "secondary_enabled=true"],
                                      "note": f"both edges mode {mode}"}
    sc["cases"].update(cases)
    suite = list(cases)
    sc["suites"]["m2gates"] = suite
    sc["host_checks"] = {"pytest": ["tests/test_esp_emulator_seams_static.py"], "builds": [],
                         "requires_git": sc.get("host_checks", {}).get("requires_git", [])}
    out = work / "tools/esp_emulator/m2_gates_scenario.json"
    out.write_text(json.dumps(sc, indent=2) + "\n")
    shutil.copy(out, run_dir / "m2_gates_scenario.json")
    plan_doc = {"suite": suite, "cases": plan, "schedules": sched, "mode": mode}
    (run_dir / "plan.json").write_text(json.dumps(plan_doc, indent=2) + "\n")
    return out, plan_doc


# ------------------------------------------------------------------------------------------------
# Analysis
# ------------------------------------------------------------------------------------------------

def load_case(ec, emu_dir: Path, cid: str) -> dict:
    import re
    uart = (emu_dir / cid / "uart.txt").read_text(errors="replace")
    cap = ec.decode(uart)
    frames = {}
    for f in cap.frames:
        frames[ec.frame_hop(cap, f, HOP)] = (bytes(f.A), bytes(f.B))
    auth = [(int(m.group(1)), int(m.group(2))) for m in re.finditer(r"EMU_AUTH after_hop=(-?\d+) state=(\d+)", uart)]
    rx_end = re.search(r"EMU_RX_END (.*)", uart)
    shown = [s for s in cap.show_states if s.get("when") == "shown" and int(s.get("hop", 0)) > 1]
    sa = hashlib.sha256(b"".join(f.A for f in cap.frames)).hexdigest()
    sb = hashlib.sha256(b"".join(f.B for f in cap.frames)).hexdigest()
    return {"frames": frames, "auth": auth, "rx_end": rx_end.group(1).strip() if rx_end else None,
            "show_state_changes_after_hop1": len(shown), "payload_sha256": ec.payload_sha256(cap),
            "edge_sha256": {"A": sa, "B": sb}, "n_frames": len(cap.frames)}


def first_pixel(a: bytes, b: bytes):
    for i in range(0, min(len(a), len(b)), 6):
        if a[i:i + 6] != b[i:i + 6]:
            def rgb(x):
                g, r, bl = struct.unpack(">HHH", x[i:i + 6])
                return [r, g, bl]
            return {"pixel": i // 6, "a_rgb16": rgb(a), "b_rgb16": rgb(b)}
    return None


def compare(ca: dict, cb: dict, off_a: int = 0, off_b: int = 0, lo: int | None = None, hi: int | None = None) -> dict:
    """Compare at musical hops m (= run hop + offset). Per edge: frames compared, differing count,
    first/last differing musical hop and the first differing pixel."""
    ma = {h + off_a: v for h, v in ca["frames"].items()}
    mb = {h + off_b: v for h, v in cb["frames"].items()}
    hops = sorted(set(ma) & set(mb))
    if lo is not None:
        hops = [h for h in hops if h >= lo]
    if hi is not None:
        hops = [h for h in hops if h < hi]
    out = {"compared_frames": len(hops), "musical_hops": [hops[0], hops[-1]] if hops else None}
    for e, idx in (("A", 0), ("B", 1)):
        d = [h for h in hops if ma[h][idx] != mb[h][idx]]
        r = {"differing_frames": len(d), "share": round(len(d) / len(hops), 4) if hops else None,
             "first_diff_hop": d[0] if d else None, "last_diff_hop": d[-1] if d else None,
             "identical": not d}
        if d:
            r["first_diff_pixel"] = first_pixel(ma[d[0]][idx], mb[d[0]][idx])
        out[e] = r
    out["identical_both_edges"] = bool(hops) and out["A"]["identical"] and out["B"]["identical"]
    return out


def judge(run_dir: Path) -> dict:
    plan = json.loads((run_dir / "plan.json").read_text())
    meta = json.loads((run_dir / "meta.json").read_text())
    emu_dir = run_dir / "emu"
    gates = meta["gates"]
    res: dict = {"run_dir": str(run_dir), "source": meta.get("ident"), "expected_today": EXPECTED_TODAY,
                 "gates": {}, "cases": {}}
    if not (emu_dir / "result.json").is_file():
        for g in gates:
            res["gates"][g] = {"verdict": "BLOCKED", "why": "emulator run produced no result.json (see run log)"}
        return res
    rj = json.loads((emu_dir / "result.json").read_text())
    res["emu"] = {"invocation_id": rj.get("invocation_id"), "build": rj.get("emu_build"),
                  "source": rj.get("source"), "tool": rj.get("tool"), "scenario": rj.get("scenario")}
    sys.path.insert(0, str(Path(meta["work"]) / "tools" / "esp_emulator"))
    import emu_capture as ec  # noqa: E402
    cases = {}
    for cid in plan["suite"]:
        st = rj["cases"].get(cid, {})
        rec = {"status": st.get("status", "MISSING"), "reasons": st.get("reasons"), "dir": str(emu_dir / cid),
               "pcm_sha256": (st.get("pcm") or {}).get("sha256"), "rx_stream": st.get("rx_stream")}
        if rec["status"] == "PASS":
            c = load_case(ec, emu_dir, cid)
            cases[cid] = c
            rec.update({k: c[k] for k in ("payload_sha256", "edge_sha256", "n_frames", "auth", "rx_end",
                                         "show_state_changes_after_hop1")})
        res["cases"][cid] = rec

    def need(*ids):
        miss = [i for i in ids if i not in cases]
        return None if not miss else f"case(s) not accepted by emu_capture.accept: {miss} " + \
            "; ".join(f"{i}: {res['cases'].get(i, {}).get('status')} {res['cases'].get(i, {}).get('reasons')}" for i in miss)

    if "G1" in gates:
        why = need("g1-a1", "g1-a2")
        if why:
            res["gates"]["G1"] = {"verdict": "BLOCKED", "why": why}
        else:
            p = {"g1-a1 vs g1-a2": compare(cases["g1-a1"], cases["g1-a2"])}
            if "g3-cont" in cases:
                p["g1-a1 vs g3-cont (shared input prefix, hops 4000-5332 at every 6th)"] = compare(cases["g1-a1"], cases["g3-cont"])
            ok = all(v["identical_both_edges"] for v in p.values())
            res["gates"]["G1"] = {"verdict": "PASS" if ok else "FAIL", "pairs": p}
    if "G2" in gates:
        why = need("g1-a1", "g2-zero", "g2-other")
        if why:
            res["gates"]["G2"] = {"verdict": "BLOCKED", "why": why}
        else:
            p = {"passage vs zero": compare(cases["g1-a1"], cases["g2-zero"]),
                 "passage vs other-music": compare(cases["g1-a1"], cases["g2-other"]),
                 "zero vs other-music": compare(cases["g2-zero"], cases["g2-other"])}
            ok = all(v["identical_both_edges"] for v in p.values())
            res["gates"]["G2"] = {"verdict": "PASS" if ok else "FAIL", "pairs": p}
    if "G3" in gates:
        why = need("g3-cont", "g3-fwd", "g3-back")
        if why:
            res["gates"]["G3"] = {"verdict": "BLOCKED", "why": why}
        else:
            off = {c: plan["cases"][c]["musical_offset_hops"] for c in ("g3-cont", "g3-fwd", "g3-back")}
            d_hop = round((G3_D - P0) * 1e6) // HOP_US
            lo, hi = d_hop + G3_R_HOPS, d_hop + G3_WINDOW_HOPS
            pairs = (("continuous vs forward", "g3-cont", "g3-fwd"), ("continuous vs backward", "g3-cont", "g3-back"),
                     ("forward vs backward", "g3-fwd", "g3-back"))
            judged, whole = {}, {}
            for name, a, b in pairs:
                judged[name] = compare(cases[a], cases[b], off[a], off[b], lo, hi)
                w = compare(cases[a], cases[b], off[a], off[b], d_hop, hi)
                for e in ("A", "B"):
                    last = w[e]["last_diff_hop"]
                    w[e]["agrees_from_hop"] = None if last is None else (last + 1 if last + 1 < hi else "never in window")
                    w[e]["differs_for_s"] = None if last is None else round((last + 1 - d_hop) * HOP_US / 1e6, 4)
                whole[name] = w
            ok = all(v["identical_both_edges"] for v in judged.values())
            res["gates"]["G3"] = {
                "verdict": "PASS" if ok else "FAIL",
                "declared": {"landing_s": G3_D, "landing_musical_hop": d_hop, "reconstruction_hops": G3_R_HOPS,
                             "reconstruction_s": G3_R_HOPS * HOP_US / 1e6, "judged_musical_hops": [lo, hi - 1],
                             "seeks": {"forward": f"run {G3_FWD_AT_RUN} s: 85.05 -> 105.0 s",
                                       "backward": f"run {G3_BACK_AT_RUN} s: 125.025 -> 105.0 s"}},
                "after_reconstruction": judged, "whole_landing_window": whole,
                "auth_transitions": {c: [t for t in cases[c]["auth"]] for c in ("g3-fwd", "g3-back")}}
    if "G4" in gates:
        m2 = meta.get("m2")
        if not m2:
            res["gates"]["G4"] = {"verdict": "BLOCKED", "why": meta.get("g4_error") or "no M2 stream delivered by m2-compose (none passed)"}
        else:
            ids = ["g4-m2"] + (["g4-twin"] if meta.get("m2_twin") else [])
            why = need(*ids)
            if why:
                res["gates"]["G4"] = {"verdict": "BLOCKED", "why": why}
            else:
                checks = {}
                for cid in ids:
                    c = cases[cid]
                    rx = c["rx_end"] or ""
                    fields = dict(kv.split("=", 1) for kv in rx.split() if "=" in kv)
                    q = fields.get("queued")
                    checks[cid] = {"reached_AUTHORED": any(s == AUTHORED for _, s in c["auth"]),
                                   "rx_all_consumed": q is not None and q == fields.get("consumed"),
                                   "rx_end": rx, "hotkey_state_changes": c["show_state_changes_after_hop1"]}
                twin = None
                if "g4-twin" in ids:
                    twin = compare(cases["g4-m2"], cases["g4-twin"])
                ok = all(v["reached_AUTHORED"] and v["rx_all_consumed"] and v["hotkey_state_changes"] == 0
                         for v in checks.values()) and twin is not None and twin["identical_both_edges"]
                why = None if twin is not None else "no twin stream supplied"
                res["gates"]["G4"] = {"verdict": "PASS" if ok else ("BLOCKED" if why else "FAIL"), "why": why,
                                      "streams": {"m2": m2, "twin": meta.get("m2_twin")},
                                      "streams_byte_identical": bool(meta.get("m2_twin")) and
                                      m2["sha256"] == meta["m2_twin"]["sha256"],
                                      "checks": checks, "twin_compare": twin}
    for g in ("G1", "G2", "G3", "G4"):
        if g not in res["gates"]:
            res["gates"][g] = {"verdict": "NOT RUN", "why": "not selected"}
    return res


def table(res: dict) -> str:
    lines = ["| Gate | Verdict | Edge A | Edge B | Detail |", "|---|---|---|---|---|"]
    for g in ("G1", "G2", "G3", "G4"):
        r = res["gates"][g]
        if g == "G3" and "after_reconstruction" in r:
            for name, v in r["after_reconstruction"].items():
                w = r["whole_landing_window"][name]
                cell = lambda e: (f"{v[e]['differing_frames']}/{v['compared_frames']} differ after R; "
                                  f"first m-hop {v[e]['first_diff_hop']}; window agrees from {w[e]['agrees_from_hop']}")
                lines.append(f"| G3 {name} | {r['verdict']} | {cell('A')} | {cell('B')} | R={r['declared']['reconstruction_hops']} hops |")
        elif "pairs" in r:
            for name, v in r["pairs"].items():
                cell = lambda e: f"{v[e]['differing_frames']}/{v['compared_frames']} differ; first hop {v[e]['first_diff_hop']}"
                lines.append(f"| {g} {name} | {r['verdict']} | {cell('A')} | {cell('B')} | |")
        elif g == "G4" and r.get("twin_compare"):
            v = r["twin_compare"]
            cell = lambda e: f"{v[e]['differing_frames']}/{v['compared_frames']} differ"
            lines.append(f"| G4 m2 vs twin | {r['verdict']} | {cell('A')} | {cell('B')} | "
                         f"{json.dumps(r['checks'])[:160]} |")
        else:
            lines.append(f"| {g} | {r['verdict']} | | | {r.get('why') or ''} |")
    return "\n".join(lines)


def plot(res: dict, run_dir: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    meta = json.loads((run_dir / "meta.json").read_text())
    plan = json.loads((run_dir / "plan.json").read_text())
    sys.path.insert(0, str(Path(meta["work"]) / "tools" / "esp_emulator"))
    import emu_capture as ec  # noqa: E402
    import numpy as np
    cache = {}

    def get(c):
        if c not in cache:
            cache[c] = load_case(ec, run_dir / "emu", c)
        return cache[c]

    def series(a, b, oa=0, ob=0):
        ma = {h + oa: v for h, v in get(a)["frames"].items()}
        mb = {h + ob: v for h, v in get(b)["frames"].items()}
        hops = sorted(set(ma) & set(mb))
        out = {}
        for e, i in (("A", 0), ("B", 1)):
            out[e] = [float(np.abs(np.frombuffer(ma[h][i], ">u2").astype(int) - np.frombuffer(mb[h][i], ">u2").astype(int)).mean())
                      for h in hops]
        return np.array(hops), out

    panels = []
    if res["gates"]["G2"].get("pairs"):
        panels += [("G2 passage vs zero PCM", "g1-a1", "g2-zero", 0, 0), ("G2 passage vs other music", "g1-a1", "g2-other", 0, 0)]
    if res["gates"]["G3"].get("after_reconstruction"):
        o = {c: plan["cases"][c]["musical_offset_hops"] for c in ("g3-cont", "g3-fwd", "g3-back")}
        panels += [("G3 continuous vs forward seek", "g3-cont", "g3-fwd", o["g3-cont"], o["g3-fwd"]),
                   ("G3 continuous vs backward seek", "g3-cont", "g3-back", o["g3-cont"], o["g3-back"])]
    if not panels:
        return None
    fig, axs = plt.subplots(len(panels), 1, figsize=(11, 2.6 * len(panels)), squeeze=False)
    for ax, (title, a, b, oa, ob) in zip(axs[:, 0], panels):
        hops, s = series(a, b, oa, ob)
        t = P0 + hops * HOP_US / 1e6
        ax.plot(t, s["A"], lw=0.8, label="edge A")
        ax.plot(t, s["B"], lw=0.8, label="edge B", alpha=0.8)
        if title.startswith("G3"):
            ax.axvline(G3_D + G3_R_HOPS * HOP_US / 1e6, color="k", ls="--", lw=0.8, label="end of R")
        ax.set_title(title, fontsize=10)
        ax.set_ylabel("mean |d| per channel (16-bit)", fontsize=8)
        ax.legend(fontsize=7, loc="upper right")
    axs[-1, 0].set_xlabel("musical position, original-file seconds")
    fig.tight_layout()
    p = run_dir / "gates-diff.png"
    fig.savefig(p, dpi=110)
    return str(p)


# ------------------------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------------------------

def finish(run_dir: Path) -> int:
    res = judge(run_dir)
    res["plot"] = plot(res, run_dir)
    (run_dir / "gates.json").write_text(json.dumps(res, indent=2) + "\n")
    t = table(res)
    (run_dir / "gates.md").write_text(t + "\n")
    print(t)
    sel = json.loads((run_dir / "meta.json").read_text())["gates"]
    bad = sum(1 for g in sel if res["gates"][g]["verdict"] != "PASS")
    print(f"gates.json {run_dir / 'gates.json'}\nfailing gates: {bad}")
    (run_dir / "exit_code.txt").write_text(f"{bad}\n")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC, help="firmware export dir (never modified)")
    ap.add_argument("--label", default=None)
    ap.add_argument("--gates", default="G1,G2,G3,G4")
    ap.add_argument("--mode", type=int, default=32)
    ap.add_argument("--m2-stream", type=Path)
    ap.add_argument("--m2-twin", type=Path)
    ap.add_argument("--m2-audio", type=Path, help="asset file for the M2 stream (default: found by sidecar sha256)")
    ap.add_argument("--m2-window", default="75:155",
                    help="original-file seconds START:END of the M2 stream to play (default 75:155, the M1/C4 window; "
                         "the scenario blob holds ~150 s of PCM+RX); 'all' = whole stream")
    ap.add_argument("--profile", choices=("fe", "scenario"), default="fe",
                    help="run.py profile: fe = k1_fe_emu (FE/B489 lineage, adds bench flags); scenario = k1_main_rpl_emu (Main RPL)")
    ap.add_argument("--analyse", type=Path, help="re-judge an existing run dir")
    ap.add_argument("--detach", action="store_true")
    a = ap.parse_args()
    if a.analyse:
        return finish(a.analyse.resolve())
    gates = [g.strip().upper() for g in a.gates.split(",") if g.strip()]
    label = a.label or f"{a.src.resolve().name}-m{a.mode}"
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    run_dir = M2 / "runs" / f"{label}-{stamp}"
    if a.detach:
        run_dir.parent.mkdir(parents=True, exist_ok=True)
        argv = [sys.executable, __file__] + [x for x in sys.argv[1:] if x != "--detach"] + ["--label", label]
        logf = open(run_dir.parent / f"{run_dir.name}.detached.log", "w")
        p = subprocess.Popen(argv, stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
        print(f"detached pid {p.pid}; log {logf.name}; results under {M2 / 'runs'}/{label}-<stamp>/")
        return 0
    run_dir.mkdir(parents=True, exist_ok=True)
    logp = run_dir / "gates.log"

    def log(msg):
        line = f"{dt.datetime.now().isoformat(timespec='seconds')} {msg}"
        print(line, flush=True)
        with open(logp, "a") as f:
            f.write(line + "\n")

    log(f"gates {gates} src {a.src} mode {a.mode}; expected today: {json.dumps({g: EXPECTED_TODAY[g] for g in gates})}")
    m2_window = None if a.m2_window == "all" else tuple(float(x) for x in a.m2_window.split(":"))
    meta = {"gates": gates, "mode": a.mode, "profile": a.profile, "m2_window": m2_window, "argv": sys.argv,
            "started": dt.datetime.now().isoformat()}
    if sha256_file(M1_STREAM) != M1_STREAM_SHA:
        raise SystemExit(f"M1 stream sha256 mismatch: {M1_STREAM}")
    meta["m1_stream"] = {"path": str(M1_STREAM), "sha256": M1_STREAM_SHA}
    if a.m2_stream:
        meta["m2"] = m2_stream_info(a.m2_stream.resolve())
    if a.m2_twin:
        meta["m2_twin"] = m2_stream_info(a.m2_twin.resolve())
    try:
        work, ident = prepare_work(a.src, label, log, a.profile)
    except Exception as e:  # BLOCKED: source cannot be prepared
        meta.update({"work": str(DEFAULT_SRC), "ident": {"error": str(e)}})
        (run_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
        (run_dir / "plan.json").write_text(json.dumps({"suite": [], "cases": {}}) + "\n")
        log(f"BLOCKED: {e}")
        return finish(run_dir)
    meta.update({"work": str(work), "ident": ident})
    try:
        scen, plan = write_scenario(work, run_dir, gates, a.mode, meta.get("m2"), meta.get("m2_twin"), ident, a.m2_audio, m2_window)
    except Exception as e:
        log(f"scenario error: {e}")
        if "G4" in gates and any(k in str(e) for k in ("G4", "M2")):
            meta["g4_error"] = str(e)
            meta.pop("m2", None)
            scen, plan = write_scenario(work, run_dir, [g for g in gates if g != "G4"], a.mode, None, None, ident)
        else:
            raise
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    env = dict(os.environ)
    env.setdefault("K1_ESP_EMU", ESP_EMU)
    cmd = [sys.executable, str(work / "tools/esp_emulator/run.py"), "--profile", a.profile, "--scenario", str(scen),
           "--suite", "m2gates", "--output", str(run_dir / "emu")]
    log("run: " + " ".join(cmd))
    with open(run_dir / "emu-run.log", "w") as f:
        rc = subprocess.run(cmd, cwd=work, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    log(f"run.py exit {rc} (its SOFTWARE COMPLETE/INCOMPLETE covers the R3 SW criteria, not these gates)")
    return finish(run_dir)


if __name__ == "__main__":
    raise SystemExit(main())
