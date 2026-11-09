"""Lane D: one bench run = LED capture + a7S III footage + one player invocation.

Usage:
  python3.13 run_one.py RUN_NAME CAPTURE_S [--no-player] [--idle-s N] -- <show_player.py args...>

Sequence (single owner of the K1 port at any moment; each step closes it):
  1. :rtrace_arm=CAPTURE_S,6 (primary-edge LED capture, every 6th render frame)
  2. a7S III recording starts (video 1280x720@25 + camera mic, one file per run)
  3. player runs (or, with --no-player, an idle wait of --idle-s seconds)
  4. footage stops ('q' to ffmpeg; never left running)
  5. :rtrace_dump=1 -> CRC-verified npz
Everything lands in runs/RUN_NAME/ with run.json (monotonic + UTC times of every step).
Never changes Mac volume; the player owns audio and its own safety checks.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = "/opt/homebrew/opt/python@3.13/bin/python3.13"
CEMU = HERE.parent / "lane-c-emu"
PLAYER_PY = CEMU / ".venv/bin/python"
PLAYER = CEMU / "player/show_player.py"


def now() -> dict:
    return {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mono": time.monotonic()}


def main() -> int:
    argv = sys.argv[1:]
    if "--" in argv:
        i = argv.index("--")
        mine, player_args = argv[:i], argv[i + 1:]
    else:
        mine, player_args = argv, []
    name, cap_s = mine[0], int(mine[1])
    no_player = "--no-player" in mine
    idle_s = float(mine[mine.index("--idle-s") + 1]) if "--idle-s" in mine else 0.0
    rd = HERE / "runs" / name
    if rd.exists():
        raise SystemExit(f"run dir exists: {rd}")
    rd.mkdir(parents=True)
    rec = {"run": name, "capture_s": cap_s, "player_args": player_args, "steps": {}}

    r = subprocess.run([PY, str(HERE / "k1_bench.py"), "arm", str(rd / "arm.txt"), str(cap_s), "6"],
                       capture_output=True, text=True)
    rec["steps"]["armed"] = {**now(), "rc": r.returncode, "out": r.stdout[-200:]}
    if r.returncode != 0:
        (rd / "run.json").write_text(json.dumps(rec, indent=1))
        raise SystemExit("rtrace arm failed")

    cam = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "warning", "-f", "avfoundation",
         "-framerate", "25", "-video_size", "1280x720", "-i", "ILCE-7SM3:ILCE-7SM3",
         "-c:v", "h264_videotoolbox", "-b:v", "10M", "-c:a", "aac", "-b:a", "192k",
         "-y", str(rd / "a7s3.mp4")],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=open(rd / "ffmpeg.log", "w"))
    rec["steps"]["camera_start"] = now()
    time.sleep(1.5)
    try:
        if no_player:
            rec["steps"]["idle_start"] = now()
            time.sleep(idle_s)
            rec["steps"]["idle_end"] = now()
        else:
            rec["steps"]["player_start"] = now()
            if player_args and player_args[0] == "SILENT":
                cmd = [PY, str(HERE / "silent_stream.py"), *player_args[1:]]
                cwd = str(HERE)
            else:
                cmd = [str(PLAYER_PY), str(PLAYER), *player_args]
                cwd = str(CEMU)
            rec["player_cmd"] = cmd
            p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
            rec["steps"]["player_end"] = {**now(), "rc": p.returncode}
            (rd / "player.stdout.txt").write_text(p.stdout)
            (rd / "player.stderr.txt").write_text(p.stderr)
        time.sleep(1.0)
    finally:
        try:
            cam.communicate(b"q", timeout=10)
        except subprocess.TimeoutExpired:
            cam.terminate()
            cam.wait(5)
        rec["steps"]["camera_stop"] = {**now(), "rc": cam.returncode}
        (rd / "run.json").write_text(json.dumps(rec, indent=1))

    # rtrace window must have closed before the dump (device stops capture at end time)
    d = subprocess.run([PY, str(HERE / "k1_bench.py"), "dump", str(rd / "dump.txt")],
                       capture_output=True, text=True)
    rec["steps"]["dump"] = {**now(), "rc": d.returncode}
    (rd / "dump.stdout.txt").write_text(d.stdout + d.stderr)
    (rd / "run.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: v for k, v in rec["steps"].items()}, indent=1)[-1500:])
    return 0 if (d.returncode == 0 and (no_player or rec["steps"]["player_end"]["rc"] == 0)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
