#!/usr/bin/env python3
"""TRINITY-FIX: compare two cold runs byte for byte, validate the contract against Trinity's
schema, and state the rhythm facts. Run with any Python that has jsonschema (the M2A
venv-validate interpreter is used read-only).

Usage: python compare_runs.py runs/<view>_A runs/<view>_B
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import jsonschema

SCHEMA = Path("/Users/spectrasynq/Workspace_Management/Software/Trinity/analysis/contract_schema.json")
RELS = ["audio/track.wav", *[f"demix/htdemucs/track/{s}.wav" for s in ("vocals", "drums", "bass", "other")],
        "stem_features.json", "analysis.json", "contract.json"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    a, b = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    out = {"a": str(a), "b": str(b), "files": {}}
    for rel in RELS:
        ha, hb = sha(a / rel), sha(b / rel)
        out["files"][rel] = {"a": ha, "b": hb, "identical": ha == hb}
    out["all_identical"] = all(v["identical"] for v in out["files"].values())

    c = json.loads((a / "contract.json").read_text())
    schema = json.loads(SCHEMA.read_text())
    errs = [f"{list(e.absolute_path)}: {e.message}" for e in jsonschema.Draft7Validator(schema).iter_errors(c)]
    out["schema"] = {"file": str(SCHEMA), "sha256": sha(SCHEMA), "result": "PASS" if not errs else "FAIL", "errors": errs[:20]}
    dur = c["track"]["duration_sec"]
    r, segs = c["rhythm"], c["structure"]["segments"]
    out["facts"] = {
        "version": c["version"],
        "duration_sec": dur,
        "segments_within_duration": all(0 <= s["start"] <= s["end"] <= dur for s in segs),
        "last_segment_end": segs[-1]["end"] if segs else None,
        "clamps": c["structure"].get("clamps"),
        "beats": len(r["beats"]), "downbeats": len(r["downbeats"]),
        "downbeats_subset_of_beats": set(r["downbeats"]) <= set(r["beats"]),
        "bpm": r["bpm"], "bpm_rounded": r.get("bpm_rounded"), "tempo": r.get("tempo"),
        "time_signature": r.get("time_signature"),
        "low_confidence_regions": r.get("low_confidence_regions"),
        "debug_meta_demucs": c.get("debug_meta", {}).get("demucs"),
    }
    print(json.dumps(out, indent=2))
    return 0 if out["all_identical"] and out["schema"]["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
