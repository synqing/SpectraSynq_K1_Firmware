#!/usr/bin/env python3
"""Audition AceStep candidate fixture windows for Captain ears-on spot-check.

Host-only ffplay playback — no device serial, no matrix, no firmware upload.
After approval, set fixture status to active in the manifest (manual edit).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS))

import k1_av_manifest as manifest_mod  # noqa: E402

DEFAULT_FIXTURES = manifest_mod.DEFAULT_FIXTURES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures-json", default=str(DEFAULT_FIXTURES))
    parser.add_argument(
        "--fixture-ids",
        help="Comma-separated ids (default: all status=candidate)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print ffplay commands without playing audio",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List candidate fixtures and exit",
    )
    return parser.parse_args()


def candidate_fixtures(manifest: dict, wanted: set[str] | None) -> list[dict]:
    rows: list[dict] = []
    for fixture in manifest.get("fixtures", []):
        if str(fixture.get("status")) != "candidate":
            continue
        if wanted and fixture["id"] not in wanted:
            continue
        rows.append(fixture)
    return rows


def main() -> int:
    args = parse_args()
    manifest = manifest_mod.load_manifest(Path(args.fixtures_json).expanduser())
    wanted = {item.strip() for item in args.fixture_ids.split(",")} if args.fixture_ids else None
    fixtures = candidate_fixtures(manifest, wanted)
    if not fixtures:
        print("No candidate fixtures matched.", file=sys.stderr)
        return 1

    if args.list:
        for fixture in fixtures:
            start_ms, duration_ms = manifest_mod.resolve_playback_window(fixture)
            print(
                f"{fixture['id']}\tstart_ms={start_ms}\tduration_ms={duration_ms}\t"
                f"path={fixture.get('resolved_path')}\t{fixture.get('purpose', '')}"
            )
        return 0

    for index, fixture in enumerate(fixtures, start=1):
        start_ms, duration_ms = manifest_mod.resolve_playback_window(fixture)
        gain_db, gain_meta = manifest_mod.resolve_playback_gain_db(fixture, manifest)
        cmd = manifest_mod.build_ffplay_command(
            fixture["resolved_path"],
            start_ms=start_ms,
            duration_ms=duration_ms,
            gain_db=gain_db,
            playback_settings=manifest_mod.playback_settings(manifest),
        )
        print(f"\n[{index}/{len(fixtures)}] {fixture['id']}")
        print(f"  purpose: {fixture.get('purpose', '')}")
        print(f"  window:  start_ms={start_ms} duration_ms={duration_ms}")
        print(f"  gain:    {gain_db:+.1f} dB ({gain_meta.get('source')})")
        print(f"  cmd:     {' '.join(cmd)}")
        if args.dry_run:
            continue
        input(f"  Press Enter to play (Ctrl+C to abort)... ")
        subprocess.run(cmd, check=False)

    print("\nSpot-check complete. If approved, promote fixtures to status=active in the manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
