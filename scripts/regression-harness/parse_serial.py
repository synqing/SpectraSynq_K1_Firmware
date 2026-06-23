#!/usr/bin/env python3
"""parse_serial.py — normalise a K1 harness capture log into tagged JSON blocks.

Parses the Phase-1 harness output surfaces:
  VPO,...        VP Tier A per-mode deterministic hashes (vp_probe=all)
  [FDUMP] ...    VP Tier B per-frame stream (frame_dump)
  [APCAP] ...    AP windowed capture (ap_capture)
  [AP] ...       legacy 1 Hz AP debug telemetry (ap_stream) — recorded, but its
                 presence *in place of* structured tags is a pollution signal.

Also runs the 03 §"invalid-capture preflight": flags `Bad command: ap_capture/vp_probe`,
legacy `vp_out_test` output standing in for `vp_probe=all`, and structured-tag absence.

Usage:  parse_serial.py <log-file> [--out parsed.json]
Exit:   0 = parsed & not polluted | 2 = invalid/polluted capture | 1 = error
"""
import sys, json, argparse, re
from pathlib import Path


def _expected_vpo_counts():
    """Return accepted VP probe row counts.

    `12` is the sealed historical Tier-A set. Current firmware can expose every
    declared light mode; derive that count from source so append-only modes do
    not stale this parser again.
    """
    counts = {12}
    try:
        root = Path(__file__).resolve().parents[2]
        config = (root / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "config_types.h").read_text()
        body = config.split("enum lightshow_modes {", 1)[1].split("};", 1)[0]
        counts.add(len(re.findall(r"\bLIGHT_MODE_[A-Z0-9_]+\b", body)))
    except Exception:
        pass
    return sorted(counts)


def _kv(tokens):
    out = {}
    for t in tokens:
        if "=" in t:
            k, v = t.split("=", 1)
            out[k] = v
    return out


def _num(v):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def _range(v):
    # "193/964" -> {"min":193.0,"max":964.0}; else passthrough
    if isinstance(v, str) and "/" in v:
        a, b = v.split("/", 1)
        return {"min": _num(a), "max": _num(b)}
    return _num(v)


def parse(text):
    vpo, fdump, ap_legacy = {}, [], []
    fdump_start, apcap = None, None
    bad_commands, notes = [], []
    saw_vpo_event = False

    for raw in text.splitlines():
        l = raw.strip()
        if not l:
            continue
        if "Bad command" in l:
            bad_commands.append(l)
            continue
        if l.startswith("VPO,"):
            if "event=" in l:
                saw_vpo_event = True
                continue
            f = {k: v for k, v in (kv.split("=", 1) for kv in l.split(",") if "=" in kv)}
            if "mode" in f:
                # numeric-ise hashes/energies left as strings (hex), counts as ints
                vpo[f["mode"]] = f
            continue
        if l.startswith("[FDUMP]"):
            toks = l[len("[FDUMP]"):].split()
            if "start" in l:
                fdump_start = _kv(toks)
            elif "end" in l:
                pass
            else:
                row = _kv(toks)
                fdump.append({k: _num(v) if k != "hash" else v for k, v in row.items()})
            continue
        if l.startswith("[APCAP]"):
            row = _kv(l[len("[APCAP]"):].split())
            apcap = {k: (_range(v) if k in ("max_raw", "peak_scaled") else _num(v))
                     for k, v in row.items()}
            continue
        if l.startswith("[AP]"):
            ap_legacy.append(_kv(l[len("[AP]"):].split()))
            continue

    # ---- invalid-capture / pollution preflight (03 §line 86) ----
    issues = []
    if bad_commands:
        issues.append("Bad-command lines present (old firmware / unrecognised harness cmd): %r"
                      % bad_commands[:3])
    if not vpo:
        issues.append("No VPO Tier-A rows — vp_probe=all did not run (or legacy vp_out_test "
                      "produced no VPO output).")
    if apcap is None and ap_legacy:
        issues.append("Legacy [AP] telemetry present but NO [APCAP] structured capture — "
                      "AP baseline would be polluted by legacy-only output.")
    if vpo:
        n_modes = len(vpo)
        expected_counts = _expected_vpo_counts()
        if n_modes not in expected_counts:
            issues.append("Expected %s VPO modes, got %d." % ("/".join(map(str, expected_counts)), n_modes))
        nondet = [m for m, f in vpo.items() if f.get("nondet") == "1"]
        if nondet != ["6"]:
            issues.append("Expected exactly mode 6 (quantum_collapse) nondet=1; got %r." % nondet)

    return {
        "vp_tier_a": vpo,
        "vp_tier_b": {"start": fdump_start, "frames": fdump},
        "ap_capture": apcap,
        "ap_legacy": ap_legacy,
        "bad_commands": bad_commands,
        "preflight_issues": issues,
        "valid": len(issues) == 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--out")
    a = ap.parse_args()
    try:
        text = open(a.log, "r", errors="replace").read()
    except OSError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    res = parse(text)
    out = json.dumps(res, indent=2)
    if a.out:
        open(a.out, "w").write(out)
        print("wrote %s" % a.out, file=sys.stderr)
    else:
        print(out)
    for i in res["preflight_issues"]:
        print("PREFLIGHT: %s" % i, file=sys.stderr)
    return 0 if res["valid"] else 2


if __name__ == "__main__":
    sys.exit(main())
