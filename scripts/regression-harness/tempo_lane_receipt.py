#!/usr/bin/env python3
"""Run one gate command and write its receipt (lane R1). The receipt records what happened;
it never asserts PASS on its own — `exit_code` is the command's exit status.

  tempo_lane_receipt.py --gate NAME --receipt docs/receipts/tempo-lock-r1/NAME.json \
      [--input PATH ...] [--output PATH ...] [--target host|emulator] -- CMD ARGS...

Schema: {gate, cmd, exit_code, sha256_inputs, sha256_outputs, stdout_tail, utc, git_sha,
         toolchain, target}
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(path: Path) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def toolchain() -> dict:
    def first(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True).stdout.splitlines()[0]
        except Exception:  # noqa: BLE001
            return None
    return {"python": platform.python_version(), "clang": first(["clang++", "--version"]),
            "platform": platform.platform()}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        raise SystemExit("usage: ... -- CMD ARGS")
    i = argv.index("--")
    p = argparse.ArgumentParser()
    p.add_argument("--gate", required=True)
    p.add_argument("--receipt", required=True, type=Path)
    p.add_argument("--input", action="append", default=[])
    p.add_argument("--output", action="append", default=[])
    p.add_argument("--target", default="host")
    a = p.parse_args(argv[:i])
    cmd = argv[i + 1:]
    sha_in = {s: sha(Path(s)) for s in a.input}
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = (r.stdout + ("\n[stderr]\n" + r.stderr if r.stderr.strip() else "")).splitlines()
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "SPECTRASYNQ_K1_FIRMWARE", "scripts", "tests",
                            "tools", "platformio.ini"], cwd=ROOT, capture_output=True, text=True).stdout
    rec = {"gate": a.gate, "cmd": " ".join(shlex.quote(c) for c in cmd), "exit_code": r.returncode,
           "sha256_inputs": sha_in, "sha256_outputs": {s: sha(Path(s)) for s in a.output},
           "stdout_tail": out[-40:], "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "git_sha": git, "git_dirty_paths": [ln[3:] for ln in dirty.splitlines()][:60],
           "toolchain": toolchain(), "target": a.target}
    a.receipt.parent.mkdir(parents=True, exist_ok=True)
    a.receipt.write_text(json.dumps(rec, indent=1) + "\n")
    print("\n".join(out[-15:]))
    print(f"receipt {a.receipt} exit_code={r.returncode}")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
