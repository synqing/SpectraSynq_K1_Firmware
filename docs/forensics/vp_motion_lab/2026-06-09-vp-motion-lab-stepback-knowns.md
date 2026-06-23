# VP Motion Lab Stepback: Known, Newly Learned, Still Unknown

Date: 2026-06-09
Status: Non-shippable VPML MVP plus loop-safe built-in validated by byte evidence.

## What We Did Not Know Before This Pass

- Whether the blocking boot intro could be split into a pure per-frame renderer without changing boot behaviour.
- Whether a non-shippable VPML frame-owner branch could render both primary and secondary through the canonical `show_leds()` path.
- Whether VPAB final-byte records could cleanly prove both channels under a VPML context.
- Whether looping the extracted boot intro would be suitable as a live development preview.
- Whether future VPML byte captures had a reusable, fail-closed summary gate rather than an ad hoc parser.

## What We Now Know

- The production boot wrapper remains available and still calls `vp_intro_render_frame(frame, frame_count)` before `show_leds()` and `FastLED.delay(2)`.
- `k1_hardware` builds without `ENABLE_VP_MOTION_LAB`.
- `k1_vp_motion_lab` is non-shippable, extends the harness env, and gates VPML behind `ENABLE_VP_MOTION_LAB`.
- VPML is a frame-owner branch only while armed: it renders, sets VPAB context, calls canonical `show_leds()`, then skips the shipping roster for that frame.
- The first built-in, `intro_bounce`, proves dual-channel VPAB byte transport but includes the boot fade trough when looped. Evidence: `docs/forensics/runtime-evidence/20260609T190853-vpml-intro-bounce-1401.vpml-summary-v2.json`.
- The second built-in, `intro_bounce_loop`, removes the loop trough for live preview without changing boot intro behaviour. Evidence: `docs/forensics/runtime-evidence/20260609T193511-vpml-intro-bounce-loop-1401.vpml-summary.json`.
- The failed high-cadence capture was correctly rejected: `docs/forensics/runtime-evidence/20260609T193419-vpml-intro-bounce-loop-1401.frame-gate.json` has dropped/overflowed records and is not runtime proof.
- The accepted loop capture has strict transport clean, primary and secondary present, mode 250 on all records, no dark sample records, no VP perf over/dropped frames, and chip identity `F887A500`.

## Still Unknown

- Eyes-on visual quality of `intro_bounce_loop` on the LGP remains unverified. VPAB bytes are not aesthetic approval.
- Whether the loop-safe colours and pacing are the right SpectraSynq feel is open to Captain judgement.
- Whether future VPML should support any programme transport remains a separate research/design phase. It is not part of this MVP and must not weaken the current serial parser or add raw receive mode without a new fail-closed protocol gate.
- Whether VPML should eventually expose a host-side authoring grammar remains unresolved. The current accepted surface is fixed built-ins only.
- The broader worktree still contains unrelated dirty Tab5/wireless/protocol files, so VPML scope must remain isolated during any commit or handover.
- The AGENTS reference-doc paths under `firmware-v3/docs/reference/` are absent in this checkout; reference copies exist under adjacent trees, but they are not live authority for this repo.

## Evidence Commands

```bash
python3 scripts/regression-harness/vpab_frame_gate.py docs/forensics/runtime-evidence/20260609T193511-vpml-intro-bounce-loop-1401.frames.log --require-mode 250 --require-channel primary --require-channel secondary --require-kind vpab_bytes --summary --out docs/forensics/runtime-evidence/20260609T193511-vpml-intro-bounce-loop-1401.frame-gate.json
python3 scripts/regression-harness/vpml_runtime_summary.py docs/forensics/runtime-evidence/20260609T193511-vpml-intro-bounce-loop-1401.frames.log --raw-log docs/forensics/runtime-evidence/20260609T193511-vpml-intro-bounce-loop-1401.raw.log --expect-chip-id F887A500 --fail-on-dark-sample --summary --out docs/forensics/runtime-evidence/20260609T193511-vpml-intro-bounce-loop-1401.vpml-summary.json
```

