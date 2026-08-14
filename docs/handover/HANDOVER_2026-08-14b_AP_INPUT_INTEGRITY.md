---
abstract: "READ FIRST. Handover 2026-08-14b. The colour lane's real blocker was found: the AP input. A fortnight of measurement went through a PDM path that produced no acoustic response. Authorisation is CONDITIONAL_GO_P0_MEASUREMENT_ONLY (Captain) against docs/plans/AP_INPUT_INTEGRITY_PLAN_2026-08-14.md Rev B. P0's pre-registered kill criterion ALREADY FIRED: both IM69D capsules are alive, so the fault is MONO SLOT SEMANTICS, not a dead part. Next action is two PHYSICAL checks that only Captain can perform, then G1. Do not mutate config before G1; production stays byte-inert until P4. Skills k1-measurement-discipline and k1-colour-truth auto-load the rules."
---

# HANDOVER — 2026-08-14b · AP input integrity

## 1. Read in this order

1. **This file.**
2. `docs/plans/AP_INPUT_INTEGRITY_PLAN_2026-08-14.md` — **Rev B**, the authorised plan.
3. `docs/plans/P0_FINDINGS_2026-08-14.md` — the kill criterion firing. **Your starting state.**
4. `docs/canon/SESSION_CANON_2026-08-14b_MEASUREMENT_INTEGRITY.md` — HF-69..80.
5. Skills `k1-measurement-discipline` (preflight, auto-loads) and `k1-colour-truth`.
6. Prior canon HF-50..68 only if you need archaeology.

## 2. Authorisation — read before touching anything

**Captain verdict: `CONDITIONAL_GO_P0_MEASUREMENT_ONLY`.**

| Authorised now | Held |
|---|---|
| P0.0 evidence quarantine · T0.1 · T0.1b · T0.2 | T0.3 accepted-config mutation → until **G1** |
| | All production-env slot changes → until **P4** |
| | P1/P2 implementation → Rev B is written; await ratification |

**Do not mutate configuration before G1.** Source may be prepared in an isolated worktree.
**Production must stay byte-inert until P4** — prove with `mic_stable_byte_gate.sh`.

## 3. Where the lane actually stands

**The colour work is finished and correct as far as anyone can tell — it was being judged
through an instrument that could not see.** Six colour fixes landed and measured 3/4
authored palette deployment. That result is not the blocker.

**The blocker is the AP input.** For roughly nine days the bench read a PDM path that
produced no acoustic response, and nothing in the system asked whether the input was real.
Everything downstream followed: calibration rejecting 112/112 silence frames, silence never
latching, the tempo engine locking 115 BPM in a dead-silent room, the plate 0–128 lit in
silence and *more* active than with music.

### P0 already refuted the leading diagnosis

A CRC-verified stereo capture shows **two distinct, non-duplicated, both-responsive
channels** (duplication 0.32%, r = +0.306, +19.6 dB and +28.4 dB response, 15× level split).
So **"one capsule is dead" is REFUTED.** The fault is **mono slot semantics** — and there is
a concrete lead: the stereo array labels are inverted relative to `slot_mask` (mono
`SLOT_RIGHT` ≈ 7 matches stereo array 0; the mono default 80–112 matches array 1), the same
IDF 5.4.1 inversion already documented for the SPH0645 at `i2s_audio.h` ~L18-34. And array 1
responds strongly in stereo while the mono default did not respond at all — **the mono
single-slot path is not delivering what the stereo path delivers. Chase that.**

## 4. YOUR NEXT ACTION

**Two physical checks that only Captain can perform.** They gate G1 and therefore everything.

1. **Directed near-field stimulus** at the IM1 position, then at the IM2 position.
2. **Acoustic occlusion** of each capsule position in turn.

Ask for them in one plain sentence. Two live signals is not the same as knowing which array
is which capsule — a 15× level split could be sensitivity, placement or exposure.

Everything else in P0 (duplication, correlation, decoder-mapping swap) is **done**; the
receipts are in `P0_FINDINGS_2026-08-14.md` and `_scratch/p0_stereo_20260814/`.

While waiting, the one useful autonomous task is closing the **P0.0 quarantine manifest**
(epoch-anchored, not calendar). Note `d1fae012` populated an audio profile from device
measurement on 08-13, and `a8b1912a` re-derived the joint silence level fraction on 08-12 —
both prime candidates. **Scope by device+config epoch:** Unit 2 (`0C54FC00`, pins 39/38) may
be entirely unaffected and must not be swept up by date.

## 5. Device truth

| | |
|---|---|
| Bench | K1v2 `B489A500` on **`/dev/cu.usbmodem12401`** (port drifts — always `--upload-port`; identity by chip, never port) |
| Running | `k1_bench_im69d_stereo` @ `623997c7`, epoch 1786716073 |
| Cal state | last accepted cal was on the `hpf_slotr` build: `dc_learned=148`, `ssl_valid=1`, 112/112 frames, `p50=32 p90=47` |
| Witness | MacBook Pro Microphone — **resolve BY NAME every run**; its index shifts on Bluetooth connect |
| Stimulus | `_scratch/im69d_vs_main_20260805/.../stimulus_35s_30s.wav` — the lane's own track. **Not synthetic noise.** |

## 6. Traps that already bit this session (full text: canon HF-69..80)

- A **probe that tested nothing** — run `scripts/tools/probe_diff.py <env> --expect FLAG`
  before believing any A/B. When a result is null, first ask whether the experiment existed.
- The **witness recorded the wrong device** twice. Resolve by name; assert non-zero samples.
- **Mismatched integration times** (7.5 ms vs 1 s) manufactured a false "the mic is deaf".
- **Adjacency across a lossy transport** — `:stream=audio` drops chunks; a "seam
  discontinuity" and a railing analysis were both parser artefacts.
- **1 Hz telemetry cannot characterise a 133 Hz latch** (665 consecutive frames needed).
- **An acceptance stamp is not a system verdict** — `NOISE CAL ACCEPTED` was reported as
  "the front end is healthy" alongside a locked beat in a silent room.
- **`:stream=magnitudes` is a dead command** — acks `K1OK`, emitter is commented out.
- **When Captain's observation contradicts your metric, the metric is the suspect.** Three
  for three this session.

## 7. Instruments available (reuse; do not rebuild)

| Tool | Use |
|---|---|
| `scripts/tools/probe_diff.py` | prove a probe env differs from its base (`--self-test` included) |
| `:tune` (44 params, env `k1_bench_im69d_tune`) | live single-variable kills instead of rebuild-per-value |
| `scripts/tools/gen_tunables.py` | regenerate the registry; ratcheted against drift |
| `scratchpad/witness_ab.py` | paired A/B with the MacBook witness resolved by name |
| `k1_bench_im69d_stereo` + `:scap_arm/status/dump` | both PDM channels, CRC-verified |
| `k1_bench_im69d_micb` | mic B independently (`SLOT_RIGHT`) |
| `scripts/agent/k1-flash-verified.sh` | flash + prove (honours `--port` since this session) |
| `scripts/regression-harness/mic_stable_byte_gate.sh` | production byte-inertness |

## 8. Landed this session

PRs **#57–#64**: cal partial-commit (first cal result the lane ever kept) · byte-gate repair
(drift was stale-by-toolchain, not a leak) · subsonic HPF on the drive peak with a
NOTE_OFFSET-derived cutoff · flash-script `--port` fix · the wrong-slot root-cause probe ·
the `:tune` runtime registry (44 params, generated + ratcheted) · Rev B plan · P0 findings ·
canon HF-69..80 · skill `k1-measurement-discipline`.

Main is green: **1069+ tests**, production stable sections byte-identical.

## 9. Open debt

Silence latch still does not fire (needs frame-level instrumentation, not 1 Hz) ·
`silent_scale` pinned 1.0 by Captain's 2026-08-09 strike — recommendation is to fix the
drive, not reinstate dimming · the four-value AP contract is designed but **not built** ·
auto-sensitivity parked with reasons · one stray file (`K1_STEREO_DSP_DECISION_2026-08-11.md`)
was swept into PR #60 by a `git add -A docs/` — another lane's, harmless, revert if wanted.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-14 | agent:claude-code | Created at session close — P0 kill criterion fired; next action is two physical checks gating G1. |
