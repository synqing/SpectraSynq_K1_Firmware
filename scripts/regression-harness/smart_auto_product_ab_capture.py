#!/usr/bin/env python3
"""Capture Smart Auto product A/B serial logs and optional camera video.

This script sends only colon-framed runtime commands. It never sends
calibration, erase, reset, or factory commands.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    import serial
except ImportError:
    serial = None


SONG_DIR = Path("/Users/spectrasynq/Workspace_Management/Software/AceStep-Eval/Songs")
DEFAULT_OUT_DIR = Path("docs/forensics/runtime-evidence")
BAUD = 115200
STATUS_PERIOD = 5.0


def default_devices():
    return [
        {
            "role": "l1-reference",
            "name": "main-k1v2",
            "port": "/dev/tty.usbmodem12201",
            "scene": "l1",
        },
        {
            "role": "smart-auto-candidate",
            "name": "bench-k1-2nd",
            "port": "/dev/tty.usbmodem1401",
            "scene": "auto",
        },
    ]


def default_clips():
    return [
        {
            "id": "steady-groove",
            "track": "Regard_Ride_It.mp3",
            "path": str(SONG_DIR / "Regard_Ride_It.mp3"),
            "start": 125,
            "duration": 25,
        },
        {
            "id": "kick-drop-heavy",
            "track": "Shelter-Mix-Cut-Yoel-Lewis-Remix.mp3",
            "path": str(SONG_DIR / "Shelter-Mix-Cut-Yoel-Lewis-Remix.mp3"),
            "start": 75,
            "duration": 25,
        },
        {
            "id": "sparse-breakdown-build",
            "track": "Carte-Blanche-Mixed.mp3",
            "path": str(SONG_DIR / "Carte-Blanche-Mixed.mp3"),
            "start": 20,
            "duration": 25,
        },
    ]


def load_clip_manifest(path):
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    clips = payload.get("clips") if isinstance(payload, dict) else payload
    if not isinstance(clips, list) or not clips:
        raise ValueError("clip manifest must contain a non-empty clips list")

    required = ("id", "track", "path", "start", "duration")
    validated = []
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            raise ValueError("clip %d must be an object" % index)
        missing = [field for field in required if field not in clip]
        if missing:
            raise ValueError("clip %d missing required fields: %s" % (index, ", ".join(missing)))

        item = dict(clip)
        item["id"] = str(item["id"])
        item["track"] = str(item["track"])
        item["path"] = str(item["path"])
        item["start"] = float(item["start"])
        item["duration"] = float(item["duration"])
        if item["start"] < 0:
            raise ValueError("clip %s start must be >= 0" % item["id"])
        if item["duration"] <= 0:
            raise ValueError("clip %s duration must be > 0" % item["id"])
        if not Path(item["path"]).exists():
            raise ValueError("clip %s path does not exist: %s" % (item["id"], item["path"]))
        validated.append(item)
    return validated


def commands_for_scene(scene):
    base = [
        ":ap_stream=on",
        ":vp_stream=on",
        ":vp_perf=start",
    ]
    if scene == "l1":
        return base + [":smart_scene=l1", ":smart_status", ":edge_status", ":vp_status"]
    if scene == "auto":
        return base + [":smart_scene=auto", ":smart_status", ":edge_status", ":vp_status"]
    raise ValueError("unsupported scene: %s" % scene)


def safe_shutdown_commands():
    return [
        ":ap_stream=off",
        ":vp_stream=off",
        ":vp_perf=stop",
        ":smart_status",
        ":edge_status",
        ":vp_status",
    ]


def timestamp():
    return "%.3f" % time.time()


def extract_identity(lines):
    identity = {"version": None, "chip_id": None}
    chip_pattern = re.compile(r"\b[0-9A-Fa-f]{8}\b")
    for line in lines:
        if "VERSION:" in line:
            identity["version"] = line.split("VERSION:", 1)[1].strip().split()[0]
            continue
        match = chip_pattern.search(line)
        if match and "VERSION" not in line:
            identity["chip_id"] = match.group(0).upper()
    return identity


class DeviceSession:
    def __init__(self, device, baud):
        if serial is None:
            raise RuntimeError("pyserial is not installed")
        self.device = dict(device)
        self.baud = baud
        self.lines = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self.ser = None

    def open(self):
        port = self.device["port"]
        if not os.path.exists(port):
            raise RuntimeError("serial node missing: %s" % port)
        self.ser = serial.Serial(port, self.baud, timeout=0.05, write_timeout=0.5)
        time.sleep(2.0)
        self.ser.reset_input_buffer()
        self.lines.append(
            "# role=%s name=%s port=%s scene=%s"
            % (self.device["role"], self.device["name"], self.device["port"], self.device["scene"])
        )

    def start_reader(self):
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        while not self._stop.is_set():
            raw = self.ser.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if line:
                with self._lock:
                    self.lines.append("[%s] %s" % (timestamp(), line))

    def send(self, command, settle=0.25):
        if not command.startswith(":"):
            raise ValueError("command must be colon-framed: %s" % command)
        with self._lock:
            self.lines.append("[%s] >>> %s" % (timestamp(), command))
        self.ser.write((command + "\n").encode("ascii"))
        self.ser.flush()
        time.sleep(settle)

    def verify_identity(self):
        self.send(":version", settle=0.8)
        self.send(":chip_id", settle=0.8)
        identity = extract_identity(self.lines)
        self.device.update(identity)
        if not identity["version"] or not identity["chip_id"]:
            raise RuntimeError("identity probe failed for %s: %s" % (self.device["port"], identity))

    def configure(self):
        for command in commands_for_scene(self.device["scene"]):
            self.send(command, settle=0.55)

    def mark(self, text):
        with self._lock:
            self.lines.append("[%s] %s" % (timestamp(), text))

    def close(self):
        if self.ser:
            try:
                for command in safe_shutdown_commands():
                    self.send(command, settle=0.2)
            except Exception as exc:
                self.mark("#SHUTDOWN_ERROR %s" % exc)
            self._stop.set()
            if self._thread:
                self._thread.join(timeout=1.0)
            self.ser.close()

    def write_log(self, path):
        with self._lock:
            text = "\n".join(self.lines) + "\n"
        path.write_text(text, encoding="utf-8")


def run_video_capture(video_device, out_path, duration):
    if not video_device:
        return None
    return subprocess.Popen(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "avfoundation",
            "-framerate",
            "30",
            "-i",
            video_device,
            "-t",
            str(duration),
            str(out_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def finish_video_capture(video_proc, timeout=5.0):
    killed = False
    try:
        stdout, stderr = video_proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        video_proc.terminate()
        try:
            stdout, stderr = video_proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            video_proc.kill()
            killed = True
            stdout, stderr = video_proc.communicate(timeout=timeout)
    return stdout, stderr, killed


def extract_video_frames(video_path, frames_dir):
    frames_dir.mkdir(parents=True, exist_ok=True)
    pattern = frames_dir / "frame_%03d.jpg"
    return subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video_path), "-vf", "fps=1", str(pattern)],
        text=True,
        capture_output=True,
        check=False,
    )


def play_clip(clip):
    return subprocess.run(
        [
            "ffplay",
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "error",
            "-ss",
            str(clip["start"]),
            "-t",
            str(clip["duration"]),
            clip["path"],
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def run_capture(devices, clips, out_dir, video_device=None, baud=BAUD):
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    sessions = [DeviceSession(device, baud) for device in devices]
    video_outputs = []

    try:
        for session in sessions:
            session.open()
            session.start_reader()
            session.verify_identity()
            session.configure()

        for clip in clips:
            for session in sessions:
                session.mark("### CLIP_START id=%s track=%s start=%s duration=%s" %
                             (clip["id"], clip["track"], clip["start"], clip["duration"]))
            video_path = out_dir / ("%s-smart-auto-ab-%s.mp4" % (run_id, clip["id"]))
            video_proc = run_video_capture(video_device, video_path, clip["duration"] + 2)
            start = time.time()
            next_status = start
            ffplay = subprocess.Popen(
                [
                    "ffplay",
                    "-nodisp",
                    "-autoexit",
                    "-loglevel",
                    "error",
                    "-ss",
                    str(clip["start"]),
                    "-t",
                    str(clip["duration"]),
                    clip["path"],
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            while ffplay.poll() is None:
                now = time.time()
                if now >= next_status:
                    for session in sessions:
                        session.send(":smart_status", settle=0.05)
                        session.send(":vp_status", settle=0.05)
                    next_status += STATUS_PERIOD
                time.sleep(0.05)
            _, clip_stderr = ffplay.communicate()
            video_rc = None
            video_err = None
            if video_proc is not None:
                _, video_err, video_killed = finish_video_capture(video_proc, timeout=5.0)
                video_rc = video_proc.returncode
                if video_rc == 0:
                    frame_result = extract_video_frames(video_path, out_dir / ("%s-frames-%s" % (run_id, clip["id"])))
                    video_outputs.append({
                        "clip_id": clip["id"],
                        "video": str(video_path),
                        "video_rc": video_rc,
                        "frames_rc": frame_result.returncode,
                        "frames_stderr": frame_result.stderr,
                    })
                else:
                    video_outputs.append({
                        "clip_id": clip["id"],
                        "video": str(video_path),
                        "video_rc": video_rc,
                        "video_stderr": video_err,
                        "video_killed": video_killed,
                    })
            for session in sessions:
                session.mark("### CLIP_END id=%s ffplay_rc=%s video_rc=%s" %
                             (clip["id"], ffplay.returncode, video_rc))
                if clip_stderr:
                    session.mark("### FFPLAY_STDERR %s" % clip_stderr.strip().replace("\n", " | "))
                if video_err:
                    session.mark("### VIDEO_STDERR %s" % video_err.strip().replace("\n", " | "))
    finally:
        for session in sessions:
            session.close()

    manifest = {
        "created_at": datetime.now().isoformat(),
        "repo": str(Path.cwd()),
        "devices": [],
        "clips": clips,
        "video_device": video_device,
        "video_outputs": video_outputs,
        "notes": "No calibration, erase, upload, or firmware source edits by this capture script.",
    }
    for session in sessions:
        log_path = out_dir / ("%s-smart-auto-ab-%s.log" % (run_id, session.device["name"]))
        session.write_log(log_path)
        payload = dict(session.device)
        payload["log"] = str(log_path)
        manifest["devices"].append(payload)

    manifest_path = out_dir / ("%s-smart-auto-ab-manifest.json" % run_id)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-port", default="/dev/tty.usbmodem12201")
    parser.add_argument("--bench-port", default="/dev/tty.usbmodem1401")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--baud", type=int, default=BAUD)
    parser.add_argument("--video-device", help='AVFoundation video input, for example "0:none"')
    parser.add_argument("--clip-manifest", help="JSON file containing clips for this capture run")
    args = parser.parse_args(argv)

    devices = default_devices()
    devices[0]["port"] = args.main_port
    devices[1]["port"] = args.bench_port
    clips = load_clip_manifest(args.clip_manifest) if args.clip_manifest else default_clips()
    manifest = run_capture(devices, clips, Path(args.out_dir), video_device=args.video_device, baud=args.baud)
    print("wrote %s" % manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
