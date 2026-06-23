#!/usr/bin/env python3
"""Branch-independent K1 + Tab5 release gate.

The git hook intentionally allows free checkpoints on wip/* branches. This
runner is the explicit release-quality gate for K1 AP/Tab5 changes.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, command: list[str], *, keep_going: bool) -> dict[str, object]:
    started = time.monotonic()
    print(f"==> {name}: {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=REPO_ROOT, check=False)
    duration_ms = int((time.monotonic() - started) * 1000)
    step = {
        "name": name,
        "command": command,
        "returncode": result.returncode,
        "duration_ms": duration_ms,
        "ok": result.returncode == 0,
    }
    if result.returncode != 0 and not keep_going:
        print(f"FAIL {name} rc={result.returncode} duration_ms={duration_ms}", flush=True)
    else:
        print(f"{'OK' if result.returncode == 0 else 'FAIL'} {name} rc={result.returncode} duration_ms={duration_ms}", flush=True)
    return step


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-going", action="store_true", help="Run all steps even after a failed step.")
    parser.add_argument("--skip-k1-build", action="store_true", help="Skip pio run -e k1_hardware.")
    parser.add_argument("--skip-tab5-build", action="store_true", help="Skip the Tab5 PlatformIO build.")
    parser.add_argument("--pytest-args", default="tests/ -q", help="Arguments passed after python -m pytest.")
    parser.add_argument("--evidence-dir", help="Directory for gate-summary.json.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    steps: list[tuple[str, list[str]]] = [
        ("pytest", [sys.executable, "-m", "pytest", *args.pytest_args.split()]),
    ]
    if not args.skip_k1_build:
        steps.append(("k1_hardware_build", ["pio", "run", "-e", "k1_hardware"]))
    if not args.skip_tab5_build:
        steps.append(("tab5_build", ["pio", "run", "-d", "sb-tab5-wireless-controller", "-e", "tab5"]))

    started_at = datetime.now().strftime("%Y%m%d-%H%M%S")
    results: list[dict[str, object]] = []
    for name, command in steps:
        result = run_step(name, command, keep_going=args.keep_going)
        results.append(result)
        if not result["ok"] and not args.keep_going:
            break

    summary = {
        "started_at": started_at,
        "ok": all(bool(step["ok"]) for step in results) and len(results) == len(steps),
        "steps": results,
    }
    if args.evidence_dir:
        evidence_dir = Path(args.evidence_dir)
    else:
        evidence_dir = REPO_ROOT / "evidence" / "k1-tab5-release-gate" / started_at
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "gate-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"evidence={evidence_dir}", flush=True)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
