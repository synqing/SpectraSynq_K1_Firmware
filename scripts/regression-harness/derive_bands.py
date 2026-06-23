#!/usr/bin/env python3
# Derive freeze-88428a2 baseline bands from captured logs → CANONICAL-ready summary.
# Reuses the tested parse_serial.parse(). Read-only; prints a summary, writes nothing.
#
# Surfaces:
#   VP Tier A  — canonical-tier-a.json (already sealed): confirm 12 modes / 11 det / mode 6 nondet.
#   VP Tier B  — silence_leg_raw.log [FDUMP] per-mode com/energy ranges (silence only).
#                Fixed bands: COM-slope ±10%, FPS ±5%. Energy band = max(2×intra-run range, floor).
#   AP         — ap_*_run*.log [APCAP] (the real 5000 ms capture = last [APCAP] per log).
#                spec_argmax = level-independent invariant (tight). Magnitude metrics = wide
#                (acoustic playback-level variance dominates run-to-run), gross-regression only.
import json, sys, os, glob

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from parse_serial import parse  # noqa: E402

DIR = "/Users/spectrasynq/SensoryBridge-main 9/docs/refactor/harness-baselines/freeze-88428a2"


def rng(vals):
    return (min(vals), max(vals)) if vals else None


def main():
    print("=" * 72)
    print("VP TIER A (canonical-tier-a.json)")
    print("=" * 72)
    ta = json.load(open(os.path.join(DIR, "canonical-tier-a.json")))
    modes = ta.get("modes", {})
    nondet = [m for m, f in modes.items() if f.get("nondet") == "1"]
    print("modes=%d  run-to-run-identical=%s  nondet=%s  (expect 12 / True / ['6'])"
          % (len(modes), ta.get("tier_a_run_to_run_identical"), nondet))

    print("\n" + "=" * 72)
    print("VP TIER B (silence_leg_raw.log) — per-mode com/energy, fixed COM±10% / FPS±5%")
    print("=" * 72)
    sil = parse(open(os.path.join(DIR, "silence_leg_raw.log")).read())
    bymode = {}
    for fr in sil["vp_tier_b"]["frames"]:
        bymode.setdefault(str(fr.get("mode")), []).append(fr)
    for m in sorted(bymode, key=lambda x: int(x) if x.isdigit() else 999):
        fs = bymode[m]
        coms = [f["com"] for f in fs if isinstance(f.get("com"), (int, float))]
        ens = [f["energy"] for f in fs if isinstance(f.get("energy"), (int, float))]
        cr, er = rng(coms), rng(ens)
        eband = None
        if er:
            span = er[1] - er[0]
            eband = max(2 * span, 50)  # floor=50 energy units (conservative)
        print("mode %2s: n=%3d  com=%s  energy=%s  energy_band=±%s"
              % (m, len(fs), cr, er, eband))

    print("\n" + "=" * 72)
    print("AP ([APCAP], real 5000 ms = last APCAP per log)")
    print("=" * 72)
    aps = {}
    for lg in sorted(glob.glob(os.path.join(DIR, "ap_*_run*.log"))):
        r = parse(open(lg).read())
        name = os.path.basename(lg).replace("ap_", "").replace(".log", "")
        cap = r["ap_capture"] or {}
        aps[name] = cap
        bad = "BAD_COMMAND!" if r["bad_commands"] else "clean"
        def g(k):
            v = cap.get(k)
            return v.get("max") if isinstance(v, dict) else v
        print("%-22s [%s] argmax=%s follower=%s peak_max=%s max_raw_max=%s chroma=%s silence=%s SSL=%s"
              % (name, bad, cap.get("spec_argmax"), cap.get("follower_mean"),
                 g("peak_scaled"), g("max_raw"), cap.get("chroma_mean"),
                 cap.get("silence"), cap.get("SSL")))

    # tone run-to-run (the band pair)
    print("\n-- tone run-to-run (level-variance check) --")
    t1, t2 = aps.get("tone_run1", {}), aps.get("tone_run2", {})
    if t1 and t2:
        print("spec_argmax: run1=%s run2=%s  -> INVARIANT band = 38-39 ±2 bins (level-independent)"
              % (t1.get("spec_argmax"), t2.get("spec_argmax")))
        print("follower:    run1=%s run2=%s  -> magnitude band WIDE (playback-level dominated)"
              % (t1.get("follower_mean"), t2.get("follower_mean")))
    print("\nAP gate rule: spec_argmax within ±2 bins of baseline = PASS (primary AP check);")
    print("magnitude metrics = gross-only (flag if 0/near-0 when stimulus present, or silence flag wrong).")
    print("VP Tier A bit-identical is the PRIMARY refactor regression detector.")


if __name__ == "__main__":
    main()
