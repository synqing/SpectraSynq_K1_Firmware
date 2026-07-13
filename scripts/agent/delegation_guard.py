#!/usr/bin/env python3
"""Stateful circuit breaker for subagent launches and checkpoints."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE = ROOT / ".devin" / "delegations.json"
OPEN = {"registered", "acknowledged"}


def load_state(path: Path) -> dict:
    if not path.is_file():
        return {"schema_version": 1, "delegations": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def problems(state: dict, now: int) -> list[str]:
    found = []
    for item in state.get("delegations", []):
        if item.get("status") == "registered" and now > item.get("ack_deadline_epoch", 0):
            found.append(f"{item['id']}: launch acknowledgement deadline missed")
        if item.get("status") in OPEN and now > item.get("checkpoint_deadline_epoch", 0):
            found.append(f"{item['id']}: checkpoint deadline missed")
    return found


def register(state: dict, *, delegation_id: str, classification: str, checkpoint_seconds: int,
             artefact: str, fallback: str, now: int) -> dict:
    existing_problems = problems(state, now)
    if existing_problems:
        raise RuntimeError("unresolved delegation failure: " + "; ".join(existing_problems))
    active = [item for item in state.get("delegations", []) if item.get("status") in OPEN]
    if len(active) >= 2:
        raise RuntimeError("active delegation cap is 2; consume or close an existing delegation")
    if any(item.get("id") == delegation_id and item.get("status") in OPEN for item in state.get("delegations", [])):
        raise RuntimeError(f"delegation {delegation_id} is already active")
    if not 30 <= checkpoint_seconds <= 300:
        raise RuntimeError("checkpoint-seconds must be between 30 and 300")
    item = {
        "id": delegation_id,
        "classification": classification,
        "status": "registered",
        "registered_epoch": now,
        "ack_deadline_epoch": now + 30,
        "checkpoint_deadline_epoch": now + checkpoint_seconds,
        "artefact": artefact,
        "fallback": fallback,
    }
    state.setdefault("delegations", []).append(item)
    return item


def update(state: dict, delegation_id: str, status: str, *, now: int, agent_id: str = "", evidence: str = "") -> dict:
    item = next((row for row in state.get("delegations", []) if row.get("id") == delegation_id), None)
    if item is None:
        raise RuntimeError(f"unknown delegation {delegation_id}")
    if status == "acknowledged":
        if item.get("status") != "registered" or now > item.get("ack_deadline_epoch", 0):
            raise RuntimeError(f"delegation {delegation_id} cannot be acknowledged after its deadline")
        item["agent_id"] = agent_id
        item["acknowledged_epoch"] = now
    else:
        item["evidence"] = evidence
        item["closed_epoch"] = now
    item["status"] = status
    return item


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    sub = parser.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("register")
    reg.add_argument("--id", required=True)
    reg.add_argument("--classification", choices=("load-bearing", "optional"), required=True)
    reg.add_argument("--checkpoint-seconds", type=int, required=True)
    reg.add_argument("--artefact", required=True)
    reg.add_argument("--fallback", required=True)
    ack = sub.add_parser("ack")
    ack.add_argument("--id", required=True)
    ack.add_argument("--agent-id", required=True)
    close = sub.add_parser("close")
    close.add_argument("--id", required=True)
    close.add_argument("--status", choices=("received", "replaced", "missing", "blocked", "aborted"), required=True)
    close.add_argument("--evidence", required=True)
    sub.add_parser("check")
    args = parser.parse_args()
    state = load_state(args.state)
    now = int(time.time())
    try:
        if args.command == "register":
            item = register(state, delegation_id=args.id, classification=args.classification,
                            checkpoint_seconds=args.checkpoint_seconds, artefact=args.artefact,
                            fallback=args.fallback, now=now)
        elif args.command == "ack":
            item = update(state, args.id, "acknowledged", now=now, agent_id=args.agent_id)
        elif args.command == "close":
            item = update(state, args.id, args.status, now=now, evidence=args.evidence)
        else:
            failures = problems(state, now)
            if failures:
                print("\n".join(failures))
                return 2
            print("delegation ledger PASS")
            return 0
    except RuntimeError as exc:
        print(f"delegation guard FAIL: {exc}")
        return 2
    save_state(args.state, state)
    print(json.dumps(item, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
