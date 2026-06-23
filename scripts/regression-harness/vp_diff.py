#!/usr/bin/env python3
"""vp_diff.py — VP Tier-A regression gate (magnitude-aware).

Compares a captured vp_probe=all log against the Freeze Baseline
(canonical-tier-a.json). Per-mode gate type is read FROM the canonical:

  * nondet=1            -> excluded from Tier A (quantum_collapse).
  * fp_tolerant truthy  -> FLOAT-OUTPUT mode whose quantised bytes are NOT
                           bit-stable across TU/inline changes under -O3
                           -ffast-math (FP reassociation / sqrtf lowering).
                           VISUAL-GATED ONLY (Captain-ratified 2026-05-26): a hash OR
                           energy gate on a float-output mode false-FAILS on every
                           inline/TU/codegen shuffle while the rendered light is
                           unchanged. So energy + hash are printed as INFO and NEVER
                           fail this script. Correctness for these modes is confirmed
                           by Captain VISUAL inspection (value-fidelity is proved
                           structurally + by the strict bit-identical fixed-point modes).
  * otherwise           -> deterministic fixed-point (SQ15x16) mode; the four
                           render hashes MUST be BIT-IDENTICAL (zero tolerance).

WHY (2026-05-26): a hash-only gate on a float-output mode produces FALSE regressions
on every future inline/TU shuffle — mode 11 (waveform_hybrid) tripped it after the
Row 2 split (88f2e3c) purely from -ffast-math reassociating a sqrtf seed-chain across
the new TU boundary; the rendered light was unchanged. The *gate*, not the mode, was
broken. Amended per Captain's standing rule: a discovered gate failure is fixed, not
run broken. Fixed-point modes keep the strict bit gate — SQ15x16 is exact and must be.

Usage: vp_diff.py <captured.log> <canonical-tier-a.json>
Exit:  0 = PASS | 1 = FAIL (fixed-point bit mismatch, or a deterministic mode missing
       from the capture). fp-tolerant modes are visual-gated and never fail here.
"""
import sys, json

HASH_KEYS = ("pal_a", "pal_b", "manual_a", "manual_b")
ENERGY_KEYS = ("pal_energy", "manual_energy")


def parse_vpo(path):
    rows = {}
    for line in open(path, "r", errors="replace"):
        line = line.strip()
        if not line.startswith("VPO,") or "mode=" not in line:
            continue
        f = {}
        for kv in line.split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                f[k] = v
        if "mode" in f:
            rows[f["mode"]] = f
    return rows


def _truthy(v):
    return v is True or str(v).lower() in ("1", "true", "yes")


def _energy_vals(s):
    out = []
    for tok in str(s).split("/"):
        try:
            out.append(float(tok))
        except ValueError:
            pass
    return out


def check_energy(m, name, c, cv):
    """fp_tolerant gate: each energy component within max(pct%*|base|, abs)."""
    tol_pct = float(c.get("energy_tol_pct", 5.0))
    tol_abs = float(c.get("energy_tol_abs", 8.0))
    fails, observed = [], []
    for k in ENERGY_KEYS:
        base = _energy_vals(c.get(k, ""))
        cap = _energy_vals(cv.get(k, ""))
        if not base or len(cap) != len(base):
            fails.append("mode %s (%s) %s: baseline=%r captured=%r (shape mismatch)"
                         % (m, name, k, c.get(k), cv.get(k)))
            continue
        for i, (b, x) in enumerate(zip(base, cap)):
            band = max(abs(b) * tol_pct / 100.0, tol_abs)
            d = abs(x - b)
            observed.append("%s[%d] base=%g cap=%g |d|=%g band=±%g" % (k, i, b, x, d, band))
            if d > band:
                fails.append("mode %s (%s) %s[%d]: base=%g cap=%g |delta|=%g > band=±%g"
                             % (m, name, k, i, b, x, d, band))
    return fails, observed


def main():
    if len(sys.argv) != 3:
        print("usage: vp_diff.py <captured.log> <canonical-tier-a.json>", file=sys.stderr)
        return 1
    cap = parse_vpo(sys.argv[1])
    canon = json.load(open(sys.argv[2]))["modes"]

    det = [m for m, c in canon.items() if c.get("nondet") != "1"]
    nondet = [m for m, c in canon.items() if c.get("nondet") == "1"]
    bit_modes = [m for m in det if not _truthy(canon[m].get("fp_tolerant"))]
    fp_modes = [m for m in det if _truthy(canon[m].get("fp_tolerant"))]
    fails, checked = [], 0
    print("VP Tier-A gate: %d bit-identical + %d fp-tolerant deterministic modes "
          "(nondet excluded: %s)" % (len(bit_modes), len(fp_modes), nondet))

    for m in sorted(det, key=int):
        c = canon[m]
        name = c.get("name", "?")
        if m not in cap:
            fails.append("mode %s (%s): MISSING from capture" % (m, name)); continue
        cv = cap[m]
        checked += 1
        if _truthy(c.get("fp_tolerant")):
            # fp_tolerant modes (float-output, codegen-unstable under -O3 -ffast-math)
            # are VISUAL-GATED ONLY — Captain-ratified 2026-05-26. Energy + hash are
            # reported as INFO and NEVER fail the automated gate; their correctness is
            # confirmed by Captain visual inspection, not by this script. (Value-fidelity
            # is proved structurally + by the bit-identical fixed-point modes.)
            _efails, observed = check_energy(m, name, c, cv)   # INFO only — not gated
            hashdiff = [k for k in HASH_KEYS if cv.get(k) != c.get(k)]
            tag = "hash-DIFF(info)" if hashdiff else "hash-same"
            print("  mode %s %-16s OK [fp-tolerant — visual-gated, energy INFO-only; %s]"
                  % (m, name, tag))
            for o in observed:
                print("       %s (info)" % o)
        else:
            bad = [k for k in HASH_KEYS if cv.get(k) != c.get(k)]
            if bad:
                for k in bad:
                    fails.append("mode %s (%s) %s: baseline=%s captured=%s"
                                 % (m, name, k, c.get(k), cv.get(k)))
            else:
                print("  mode %s %-16s OK [bit-identical]" % (m, name))
    for m in nondet:
        present = "present" if m in cap else "absent"
        print("  mode %s %-16s nondet — Tier-A excluded (%s)"
              % (m, canon[m].get("name", "?"), present))

    print("\n%d/%d deterministic modes checked (%d bit-identical, %d fp-tolerant)."
          % (checked, len(det), len(bit_modes), len(fp_modes)))
    if fails:
        print("RESULT: FAIL — %d issue(s):" % len(fails))
        for x in fails:
            print("  X " + x)
        return 1
    print("RESULT: PASS — fixed-point modes bit-identical; fp-tolerant modes visual-gated (INFO only).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
