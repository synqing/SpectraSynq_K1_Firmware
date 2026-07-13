#!/usr/bin/env python3
"""Phase 5 Headroom compression-only A/B harness (library path).

Forbidden: memory, learn, proxy, wrap, output shaping.
Run from repo root (requires headroom-ai==0.31.0 on PYTHONPATH):

  ~/miniforge3/bin/python3 scripts/agent/phase5-headroom-ab.py

Homebrew python3 often lacks the package (PEP 668); miniforge or venv recommended.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from headroom import compress
from headroom.compress import CompressConfig

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "knowledge/research/phase5-ab-metrics.json"
ADVERSARIAL = REPO / "knowledge/research/phase5-adversarial-eval.json"


def git_head() -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def build_task(task_type: str, task_id: str, head: str) -> tuple[list[dict], list[str], str]:
    adv = json.loads(ADVERSARIAL.read_text())
    extra_paths = {
        "debug": [
            "knowledge/research/phase3-test2-bug-resurrection.md",
            "SPECTRASYNQ_K1_FIRMWARE/system/constants.h",
        ],
        "implement": [
            "knowledge/research/phase2-openknowledge-mcp-proof.md",
            "docs/agent-stack/PHASED-ROLLOUT.md",
        ],
        "review": [
            "knowledge/research/phase4-exit-gate-summary.md",
            "docs/agent-stack/ACTIONABLE-TASKS.md",
        ],
    }[task_type]
    files = {}
    for rel in extra_paths:
        p = REPO / rel
        files[rel] = p.read_text() if p.exists() else ""
    canaries = {
        "debug": [
            "light_mode_beat_pulse",
            "k1_hardware",
            "F887A500",
            "session-bootstrap.sh",
            head[:7],
            "scripts/agent/session-bootstrap.sh",
        ],
        "implement": [
            "AudioSemanticState",
            "session-bootstrap.sh",
            "SB_ONSET_V2",
            "Goertzel",
            head[:7],
            "k1_hardware",
        ],
        "review": [
            "k1_hardware",
            "session-bootstrap.sh",
            "P4-R07",
            "AUTHORITY-CONTRACT",
            head[:7],
            "docs/agent-stack/AUTHORITY-CONTRACT.md",
        ],
    }[task_type]
    payload = {
        "task_id": task_id,
        "git_head": head,
        "repo": str(REPO),
        "adversarial_grid": adv,
        "file_hits": files,
        "pytest_log_excerpt": (
            "PASSED tests/test_rate_consistency.py\n"
            "PASSED tests/test_dev_instrumentation_boundary.py\n" * 200
        ),
        "pio_build_tail": (
            "Linking .pio/build/k1_hardware/firmware.elf\n"
            "RAM:   [==        ]  45.2%\nFlash: [========  ]  78.1%\n" * 150
        ),
        "canaries": canaries,
    }
    tool_body = json.dumps(payload)
    messages = [
        {
            "role": "system",
            "content": "K1 firmware agent. Preserve paths, env names, and git SHAs in tool output.",
        },
        {"role": "user", "content": f"Task {task_id}: analyze tool output for {task_type}."},
        {
            "role": "tool",
            "tool_call_id": "t1",
            "name": "run_terminal_cmd",
            "content": tool_body,
        },
    ]
    return messages, canaries, tool_body


def main() -> int:
    try:
        import headroom as _hr  # noqa: F401
    except ImportError:
        print("headroom-ai not installed; pip install 'headroom-ai==0.31.0'", file=sys.stderr)
        return 1

    head = git_head()
    cfg = CompressConfig(
        protect_recent=0,
        protect_analysis_context=False,
        min_tokens_to_compress=100,
    )
    results = []
    for task_type, task_id in [
        ("debug", "T-DEBUG"),
        ("implement", "T-IMPLEMENT"),
        ("review", "T-REVIEW"),
    ]:
        messages, canaries, raw = build_task(task_type, task_id, head)
        r = compress(messages, model="gpt-4o", config=cfg, optimize=True)
        out = r.messages[-1]["content"]
        lost = [c for c in canaries if c not in out]
        head_ok = head in out or head[:7] in out
        results.append(
            {
                "task_id": task_id,
                "task_type": task_type,
                "tokens_baseline": r.tokens_before,
                "tokens_compressed": r.tokens_after,
                "tokens_saved": r.tokens_saved,
                "pct_reduction": round(100 * r.compression_ratio, 2),
                "compression_ratio": r.compression_ratio,
                "chars_baseline": len(raw),
                "chars_compressed": len(out),
                "transforms": r.transforms_applied,
                "canaries_checked": canaries,
                "canaries_lost": lost,
                "git_head_full_present": head in out,
                "identifier_ok": len(lost) == 0 and head_ok,
            }
        )

    try:
        import importlib.metadata as md

        ver = md.version("headroom-ai")
    except Exception:
        ver = "unknown"

    doc = {
        "headroom_version": ver,
        "package": "headroom-ai (PyPI)",
        "env": {
            "mode": "library compress() only",
            "forbidden": "memory,learn,wrap,proxy,output-shaping",
        },
        "git_head_at_run": head,
        "results": results,
    }
    OUT.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"Wrote {OUT}")
    for row in results:
        print(
            row["task_id"],
            row["tokens_baseline"],
            "->",
            row["tokens_compressed"],
            f"{row['pct_reduction']}%",
            "id_ok" if row["identifier_ok"] else "FAIL",
        )
    return 0 if all(r["identifier_ok"] for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
