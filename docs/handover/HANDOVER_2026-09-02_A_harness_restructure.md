# HANDOVER A — Harness restructure — **WITHDRAWN 2 Sep 2026**

**Do not launch this brief.**

The premise ("the 24 Aug 2026 audit's three structural fixes are still open") was taken from the 24–28 Aug record before the DualMCU repo was connected. Reading the repo at HEAD `553b6be` shows the repairs landed on 27 Aug:

- Single composition root: PlatformIO environment `rt1062_production`, checked by `harness/check_production_composition.py` (required sources + runtime call-graph tokens).
- Post-link gates: `RT1062_LINK_PRESENCE`, `S3_LINK_PRESENCE`, `check_rt1062_realtime_image.py`, `check_s3_radio_only_image.py`; artefact SHA-256 in `harness/generate_release_manifest.py`.
- Verifier independent of the build claim: `check_production_build_identity.py` (clean-worktree source identity), 35 connected-runtime mutation cases, positive-control injections (`INJECTED_CRGB=CAUGHT` … `HARDWARE_EMISSION_REMOVAL=CAUGHT`).
- Evidence: `docs/evidence/k1-dm-080-software-trust-f2f19a1.md`; ledger K1-DM-080 = PASSING. The earlier false-green result (`5d2d316`) is recorded there as invalid, which is the audit's own finding closed.

What remains is not a restructure: `docs/plans/2026-08-28-output-stage-fidelity-execution-plan.md` G0.3 asks only to *confirm* these repairs are landed before WP1. That confirmation belongs to whoever picks up K1-DM-100 part 2, on hardware.
