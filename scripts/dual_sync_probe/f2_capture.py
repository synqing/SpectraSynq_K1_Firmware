"""Identity-checked, ordered F2 A/B/C Link Ready capture controller.

This controller never flashes. It proves the already-flashed binaries and
devices before capture, enforces A -> B -> C, and writes a compact manifest.
It is deliberately separate from Gate-0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from . import capture, gate_eval

CASE_CONTRACT = {
    "A": {
        "physical_state": "sync-only",
        "leader_env": "k1_sync_probe_main_sync_only",
    },
    "B": {
        "physical_state": "dial-off",
        "leader_env": "k1_sync_probe_main",
    },
    "C": {
        "physical_state": "dial-on",
        "leader_env": "k1_sync_probe_main",
    },
}
FOLLOWER_ENV = "k1_sync_probe_bench"
LEADER_CHIP = "F887A500"
FOLLOWER_CHIP = "B489A500"


class F2ContractError(RuntimeError):
    """F2 ordering, identity, binary, or manifest contract failure."""


def _git_head(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise F2ContractError(f"cannot resolve source HEAD: {error}") from error


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise F2ContractError(f"binary evidence does not exist: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise F2ContractError(f"invalid prior manifest {path}: {error}") from error


def validate_case_order(case_name: str, out_root: Path, source_sha: str) -> None:
    prior = {"B": "A", "C": "B"}.get(case_name)
    if prior is None:
        return
    manifest_path = out_root / f"case_{prior}" / "MANIFEST.json"
    manifest = _read_manifest(manifest_path)
    if manifest.get("case_status") != gate_eval.PASS:
        raise F2ContractError(
            f"Case {case_name} requires Case {prior} PASS"
        )
    if manifest.get("source_sha") != source_sha:
        raise F2ContractError(
            f"Case {case_name} source differs from Case {prior}"
        )


def _atomic_manifest(path: Path, payload: dict) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("x", encoding="utf-8") as output:
        json.dump(payload, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def run(args) -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    source_sha = _git_head(repo_root)
    contract = CASE_CONTRACT[args.case]
    if args.physical_state != contract["physical_state"]:
        raise F2ContractError(
            f"Case {args.case} requires physical state "
            f"{contract['physical_state']}"
        )
    validate_case_order(args.case, args.out_root, source_sha)

    leader_bin = args.leader_bin.resolve()
    follower_bin = args.follower_bin.resolve()
    leader_bin_sha = _sha256(leader_bin)
    follower_bin_sha = _sha256(follower_bin)

    if args.case == "C":
        case_b = _read_manifest(args.out_root / "case_B" / "MANIFEST.json")
        if (
            case_b.get("leader_bin_sha256") != leader_bin_sha
            or case_b.get("follower_bin_sha256") != follower_bin_sha
        ):
            raise F2ContractError(
                "Case C must use the exact Case-B firmware binaries"
            )

    expectations = {
        "leader": {
            "chip_id": LEADER_CHIP,
            "env": contract["leader_env"],
            "source_sha": source_sha,
        },
        "follower": {
            "chip_id": FOLLOWER_CHIP,
            "env": FOLLOWER_ENV,
            "source_sha": source_sha,
        },
    }
    case_dir = args.out_root / f"case_{args.case}"
    results = capture.run_segments(
        leader_port=args.leader_port,
        follower_port=args.follower_port,
        out_dir=case_dir,
        segments=("off",),
        duration_s=args.duration_s,
        ack_timeout_s=args.ack_timeout_s,
        settle_s=args.settle_s,
        baud=args.baud,
        identity_expectations=expectations,
    )
    link_ready = results[0]["link_ready"]
    evidence_paths = {
        "leader_session": case_dir / "leader_session.log",
        "follower_session": case_dir / "follower_session.log",
        "verdict": case_dir / "off" / "verdict_off.json",
        "identity": case_dir / "IDENTITY.json",
    }
    manifest = {
        "schema_version": 1,
        "case": args.case,
        "case_status": (
            gate_eval.PASS if link_ready == gate_eval.PASS else gate_eval.BLOCKED
        ),
        "link_ready": link_ready,
        "physical_state": args.physical_state,
        "source_sha": source_sha,
        "leader": {
            "port": args.leader_port,
            "chip_id": LEADER_CHIP,
            "env": contract["leader_env"],
        },
        "follower": {
            "port": args.follower_port,
            "chip_id": FOLLOWER_CHIP,
            "env": FOLLOWER_ENV,
        },
        "leader_bin": str(leader_bin),
        "leader_bin_sha256": leader_bin_sha,
        "follower_bin": str(follower_bin),
        "follower_bin_sha256": follower_bin_sha,
        "capture_parameters": {
            "duration_s": args.duration_s,
            "settle_s": args.settle_s,
            "ack_timeout_s": args.ack_timeout_s,
            "baud": args.baud,
            "segments": ["off"],
        },
        "evidence_sha256": {
            name: _sha256(path) for name, path in evidence_paths.items()
        },
        "capture_index": str(case_dir / "INDEX.md"),
        "identity_evidence": str(case_dir / "IDENTITY.json"),
        "verdict": str(case_dir / "off" / "verdict_off.json"),
    }
    _atomic_manifest(case_dir / "MANIFEST.json", manifest)
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture one ordered, identity-checked F2 A/B/C case."
    )
    parser.add_argument("--case", choices=tuple(CASE_CONTRACT), required=True)
    parser.add_argument("--physical-state", required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--leader-port", required=True)
    parser.add_argument("--follower-port", required=True)
    parser.add_argument("--leader-bin", type=Path, required=True)
    parser.add_argument("--follower-bin", type=Path, required=True)
    parser.add_argument("--duration-s", type=float, default=60.0)
    parser.add_argument("--settle-s", type=float, default=10.0)
    parser.add_argument("--ack-timeout-s", type=float, default=3.0)
    parser.add_argument("--baud", type=int, default=capture.DEFAULT_BAUD)
    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        manifest = run(args)
    except (F2ContractError, capture.CaptureContractError, OSError) as error:
        parser.error(str(error))
    return 0 if manifest["case_status"] == gate_eval.PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
