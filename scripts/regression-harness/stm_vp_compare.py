#!/usr/bin/env python3
"""stm_vp_compare.py — fail-closed STM visual-parity manifest gate (offline).

Evaluates a JSON run manifest for WB-3. Parity claims require independent A/B
provenance and active data. Returns PASS, FAIL, or INDETERMINATE with reason codes.

Exit: 0 = evaluated | 1 = usage/I/O error
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple

ACTIVITY_FLOOR = 1e-6
VALID_DECISIONS = {"PASS", "FAIL", "INDETERMINATE"}


def _reason(code: str, detail: str) -> Dict[str, str]:
    return {"code": code, "detail": detail}


def check_provenance(manifest: Dict[str, Any]) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    ref = manifest.get("reference") or {}
    cand = manifest.get("candidate") or {}
    for side, label in ((ref, "reference"), (cand, "candidate")):
        if not side.get("algorithm_id"):
            issues.append(_reason("missing_algorithm_id", "%s algorithm_id required" % label))
        if not side.get("executable_hash"):
            issues.append(_reason("missing_executable_hash", "%s executable_hash required" % label))
    ref_exe = ref.get("executable_hash")
    cand_exe = cand.get("executable_hash")
    ref_src = ref.get("source_hash")
    cand_src = cand.get("source_hash")
    if ref_exe and cand_exe and ref_exe == cand_exe:
        issues.append(_reason("identical_executable", "reference and candidate executable_hash match"))
    if ref_src and cand_src and ref_src == cand_src and ref_exe == cand_exe:
        issues.append(_reason("identical_provenance", "A==A provenance detected"))
    if ref.get("fft_size") not in (None, 512) and manifest.get("claim") == "source_parity":
        issues.append(_reason("invalid_reference_fft", "reference fft_size must be 512 for source parity claim"))
    return issues


def check_streams(manifest: Dict[str, Any]) -> Tuple[List[Dict[str, str]], str]:
    """Return (issues, suggested_decision_fragment)."""
    issues: List[Dict[str, str]] = []
    streams = manifest.get("streams") or []
    if not streams:
        return [_reason("no_streams", "no stream records")], "INDETERMINATE"

    controls = manifest.get("controls") or {}
    if controls.get("scenario") == "self_shadow" or controls.get("shadow") == "self":
        if manifest.get("claim") == "parity":
            issues.append(_reason("self_shadow", "self_shadow cannot support parity PASS"))
            return issues, "INDETERMINATE"

    ref_energy = 0.0
    cand_energy = 0.0
    for frame in streams:
        ref_energy = max(ref_energy, float(frame.get("reference_energy", 0.0)))
        cand_energy = max(cand_energy, float(frame.get("candidate_energy", 0.0)))

    if ref_energy < ACTIVITY_FLOOR and cand_energy < ACTIVITY_FLOOR:
        issues.append(_reason("blank_both", "both streams below activity floor"))
        return issues, "INDETERMINATE"
    if ref_energy >= ACTIVITY_FLOOR and cand_energy < ACTIVITY_FLOOR:
        return [_reason("candidate_blank", "reference active, candidate blank")], "FAIL"
    if ref_energy < ACTIVITY_FLOOR and cand_energy >= ACTIVITY_FLOOR:
        return [_reason("reference_blank", "reference blank, candidate active")], "INDETERMINATE"
    return issues, "PASS"


def check_negative_control(manifest: Dict[str, Any]) -> List[Dict[str, str]]:
    nc = manifest.get("negative_control") or {}
    if not nc:
        return []
    if nc.get("injected") and not nc.get("expected_fail"):
        return [_reason("negative_control", "injected divergence must set expected_fail")]
    if nc.get("injected") and nc.get("metrics_within_threshold"):
        return [_reason("scorer_insensitive", "deliberate divergence passed thresholds")]
    return []


def evaluate_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    reasons: List[Dict[str, str]] = []
    reasons.extend(check_provenance(manifest))
    stream_issues, stream_hint = check_streams(manifest)
    reasons.extend(stream_issues)
    reasons.extend(check_negative_control(manifest))

    if any(r["code"] == "candidate_blank" for r in reasons):
        decision = "FAIL"
    elif any(r["code"] == "scorer_insensitive" for r in reasons):
        decision = "FAIL"
    elif reasons:
        decision = "INDETERMINATE"
    elif stream_hint == "PASS" and manifest.get("metrics_within_threshold") is True:
        decision = "PASS"
    elif manifest.get("metrics_within_threshold") is False:
        decision = "FAIL"
    else:
        decision = "INDETERMINATE"
        reasons.append(_reason("incomplete_metrics", "metrics_within_threshold not established"))

    if manifest.get("claim") == "parity" and decision == "PASS":
        if not manifest.get("reference", {}).get("fft_size") == 512:
            decision = "INDETERMINATE"
            reasons.append(_reason("reference_unattested", "parity PASS requires attested 512 reference"))

    if decision not in VALID_DECISIONS:
        decision = "INDETERMINATE"
    return {"decision": decision, "reasons": reasons}


def main(argv=None):
    parser = argparse.ArgumentParser(description="STM VP manifest gate")
    parser.add_argument("manifest", help="JSON manifest path")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    args = parser.parse_args(argv)
    try:
        with open(args.manifest, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except OSError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print("error: invalid JSON: %s" % exc, file=sys.stderr)
        return 1

    result = evaluate_manifest(manifest)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("decision=%s" % result["decision"])
        for item in result["reasons"]:
            print("  %s: %s" % (item["code"], item["detail"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
