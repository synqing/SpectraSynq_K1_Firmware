---
abstract: "READ FIRST. Handover 2026-08-14b. P0 refuted the dead/unpopulated diagnosis; Captain RATIFIED G1 on 2026-08-15. IM1 HIGH → ESP-IDF PDM RIGHT → PCM index 0 is the future programme source; IM2 LOW → ESP-IDF PDM LEFT → PCM index 1. T0.3 is COMPLETE: all active mono IM69D diagnostic envs resolve explicitly to RIGHT, stereo removes the inherited mono flag, misleading/no-op aliases are retired, full tests/builds pass, and protected production environments remain byte-identical. No further physical microphone test is authorised. Production slot promotion remains held until P4."
status: active
branch: main
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

**Captain verdict: G1 `RATIFIED` under the existing conditional lane authority.**

| Authorised now | Held |
|---|---|
| T0.3 is complete; documentation closeout/read-only audit | All production-env slot changes → until **P4** |
| | P1/P2 implementation → existing later gates |

G1 has passed. **Production must stay byte-inert until P4** — prove with
`mic_stable_byte_gate.sh`. No flash, calibration or physical microphone handling is
authorised by T0.3.

## 3. Where the lane actually stands

**The colour work is finished and correct as far as anyone can tell — it was being judged
through an instrument that could not see.** Six colour fixes landed and measured 3/4
authored palette deployment. That result is not the blocker.

**The blocker is AP input integrity.** For roughly nine days the bench consumed physical
IM2 under ambiguous inherited slot naming without checking that the selected input was
suitable. Both capsules are alive. The affected calibration, silence, absolute-level and
quiet-normalised plate conclusions require re-derivation on the ratified physical-IM1 source;
unrelated code reasoning and programme-relative findings are not automatically destroyed.

### P0 already refuted the leading diagnosis

A CRC-verified stereo capture shows **two distinct, non-duplicated, both-responsive
channels** (duplication 0.32%, r = +0.306, +19.6 dB and +28.4 dB response, 15× level split).
So **"one capsule is dead" is REFUTED.** The fault is **mono slot semantics** — and there is
a concrete lead: the stereo array labels are inverted relative to `slot_mask` (mono
`SLOT_RIGHT` ≈ 7 matches stereo array 0; the mono default 80–112 matches array 1), the same
IDF 5.4.1 inversion already documented for the SPH0645 at `i2s_audio.h` ~L18-34. And array 1
responds strongly in stereo while the mono default did not respond at all — **the mono
single-slot path is not delivering what the stereo path delivers. Chase that.**

## 4. T0.3 — complete

All active mono IM69D environments now resolve to the ratified ESP-IDF RIGHT source. Stereo
explicitly removes the inherited mono flag and selects both slots. The retired `micb`,
`hpf_slotr` and no-op `calfix_dsr16` aliases are no longer active environments. Do not ask
Captain to operate or interpret another measurement.

```text
PHYSICAL IM1 (SELECT HIGH) → Infineon PDM LEFT  → ESP-IDF mask RIGHT → PCM index 0
PHYSICAL IM2 (SELECT LOW)  → Infineon PDM RIGHT → ESP-IDF mask LEFT  → PCM index 1
RATIFIED FUTURE SHIPPED MONO SLOT → K1_MIC_IM69D_SLOT_RIGHT
```

The chain is board SELECT strapping + the active ESP-IDF PDM enum + the retained
mono/stereo floor fingerprint. Full authority:
`docs/forensics/G1_AP_INPUT_SLOT_RATIFICATION_2026-08-15.md`.

The active build is ESP-IDF **5.4.1**, not 5.4.2. Freeze 5.4.1, the new PDM driver,
`clk_inv=false`, and stereo order RIGHT then LEFT. This source-truth correction does not
alter the mapping.

Closeout authority and exact commands:
`docs/forensics/G1_AP_INPUT_SLOT_RATIFICATION_2026-08-15.md`.

The earlier plate comparison and occlusion protocol is cancelled. Both render channels consume
shared audio features, so plate-channel strength cannot identify a microphone. Occlusion is
an uncontrolled fallback, not a baseline requirement.

**Closed 2026-08-15:**
`docs/forensics/P0_0_AP_INPUT_QUARANTINE_MANIFEST_2026-08-15.md` dispositions the
`B489A500` IM69D mono-default epoch and its consumers. It quarantines only claims dependent
on capsule identity, absolute level, calibration/silence state or malformed quiet
normalisation. Re-derivation remains P2/P3 work.

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
| `k1_bench_im69d` | ratified physical IM1 programme source (`SLOT_RIGHT`) after T0.3 |
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
| 2026-08-15 | Captain / agent:codex | G1 ratified; T0.3 bench/diagnostic work authorised; production held until P4; no further physical test authorised. |
| 2026-08-15 | agent:codex | Replaced the invalid Captain-operated plate/occlusion procedure with the resolved static mapping and proposed G1 statement. |
| 2026-08-15 | agent:codex | Added active authority metadata and linked the closed P0.0 device+config-epoch quarantine manifest. |
| 2026-08-14 | agent:claude-code | Created at session close — P0 kill criterion fired; next action is two physical checks gating G1. |
