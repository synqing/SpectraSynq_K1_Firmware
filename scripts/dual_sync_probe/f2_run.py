"""Create one immutable, authority-bound F2 run and pre-A port manifest."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from . import f2_capture, f2_image_set, f2_ports


class F2RunError(RuntimeError):
    """F2 run authority, root, image, or initial identity gate failure."""


def _created_at_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _write_once(path: Path, payload: dict) -> None:
    try:
        with path.open("x", encoding="utf-8") as output:
            json.dump(payload, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
    except OSError as error:
        raise F2RunError(f"cannot create immutable run manifest: {error}") from error


def create_run(
    args,
    *,
    repo_root_override: Path | None = None,
    bindings_resolver=f2_ports.resolve_bindings,
) -> dict:
    repo_root = (
        repo_root_override.resolve()
        if repo_root_override is not None
        else Path(__file__).resolve().parents[2]
    )
    host_sha = f2_capture._git_head(repo_root)
    if host_sha != args.host_execution_sha:
        raise F2RunError(
            "host execution SHA does not equal current committed HEAD"
        )
    if args.host_execution_sha == args.firmware_source_sha:
        raise F2RunError(
            "host execution SHA and firmware source SHA must remain distinct"
        )
    f2_capture._require_clean_host_inputs(repo_root)
    try:
        image_set = f2_image_set.load(
            args.image_set_manifest, repo_root=repo_root
        )
    except f2_image_set.F2ImageSetError as error:
        raise F2RunError(f"image set is not ready: {error}") from error
    if image_set["firmware_source_sha"] != args.firmware_source_sha:
        raise F2RunError(
            "firmware source SHA does not match image-set manifest"
        )
    raw_root = args.run_root.resolve()
    if (
        not f2_capture._inside(raw_root, repo_root / "_scratch")
        or not raw_root.name.startswith("dual_sync_f2_abc_")
    ):
        raise F2RunError(
            "run root must be _scratch/dual_sync_f2_abc_<run-id>"
        )
    run_id = raw_root.name.removeprefix("dual_sync_f2_abc_")
    f2_capture._validate_run_id(run_id)
    tracked_root = repo_root / f2_capture.TRACKED_F2_REL / run_id
    if raw_root.exists() or tracked_root.exists():
        raise F2RunError("refusing to overwrite an existing F2 run")

    authority_paths = (
        repo_root
        / "artifacts/k1_dual_sync_eval_2026-07-08/recovery/recovery-plan.md",
        repo_root
        / "artifacts/k1_dual_sync_eval_2026-07-08/recovery/task_plan.md",
        repo_root
        / "artifacts/k1_dual_sync_eval_2026-07-08/recovery/f2/README.md",
        image_set["manifest_path"],
    )
    authority = {}
    for path in authority_paths:
        if not path.is_file() or path.is_symlink():
            raise F2RunError(f"run authority is missing or indirect: {path}")
        authority[f2_capture._repo_relative(path, repo_root)] = {
            "sha256": f2_capture._sha256(path),
            "size": path.stat().st_size,
        }

    bindings = bindings_resolver()
    raw_root.mkdir(parents=True, exist_ok=False)
    runtime = tracked_root / "runtime"
    runtime.mkdir(parents=True, exist_ok=False)
    ports = f2_ports.write_ports_manifest(
        "pre_A",
        runtime,
        bindings,
        host_execution_sha=host_sha,
        firmware_source_sha=args.firmware_source_sha,
    )
    ports_path = runtime / "ports_pre_A.json"
    manifest = {
        "schema_version": 1,
        "status": "OPEN",
        "run_id": run_id,
        "created_at_utc": _created_at_utc(),
        "host_execution_sha": host_sha,
        "firmware_source_sha": args.firmware_source_sha,
        "f3_authorised": False,
        "image_set_manifest": f2_capture._evidence_record(
            image_set["manifest_path"], repo_root
        ),
        "ports_pre_A_manifest": f2_capture._evidence_record(
            ports_path, repo_root
        ),
        "port_bindings": ports,
        "authority": authority,
    }
    _write_once(tracked_root / "RUN_MANIFEST.json", manifest)
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create one immutable F2 run after all image gates pass."
    )
    parser.add_argument("--host-execution-sha", required=True)
    parser.add_argument("--firmware-source-sha", required=True)
    parser.add_argument("--image-set-manifest", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = create_run(args)
    except (
        F2RunError,
        f2_capture.F2ContractError,
        f2_ports.F2PortsError,
        OSError,
        ValueError,
    ) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
