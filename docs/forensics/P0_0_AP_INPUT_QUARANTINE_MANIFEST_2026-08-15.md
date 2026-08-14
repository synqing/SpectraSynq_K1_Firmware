---
abstract: "P0.0 quarantine manifest for the K1 AP input-integrity lane. Scope is device plus configuration epoch plus dependency: only claims that depend on physical-capsule selection, absolute input level, calibration/silence state, or malformed quiet-state normalisation are quarantined. Code reasoning, palette references, static control flow, unrelated renderer defects and programme-relative findings are not automatically destroyed. G1 is ratified; re-derivation remains later P2/P3 work."
status: closed
scope_id: B489A500_IM69D_MONO_DEFAULT_INPUT_DEPENDENT
authority: docs/plans/AP_INPUT_INTEGRITY_PLAN_2026-08-14.md
---

# P0.0 AP-input quarantine manifest

**Quarantine index:** CLOSED.

**Re-derivation:** NOT STARTED; held behind the later Rev B P2/P3 gates.

**Authorisation:** `CONDITIONAL_GO_P0_MEASUREMENT_ONLY`.

Closing this manifest means every known artefact family from the affected epoch has an
admissibility disposition. It does **not** mean its claims have been re-proven, and it does
not authorise calibration, a production slot change or promotion. G1 separately authorises
T0.3 bench/diagnostic explicit-slot work.

## 1. Epoch boundary — the scope is a predicate

An artefact or claim is quarantined only when all of these are true:

1. Physical device is bench K1v2 `B489A500`.
2. Microphone path is IM69D (`K1_MIC_IM69D_PDM_V1`).
3. Capture is mono and inherits the default slot: neither
   `K1_MIC_IM69D_SLOT_RIGHT` nor `K1_MIC_IM69D_STEREO_V1` is present.
4. Its validity depends on at least one of: physical-capsule identity, absolute raw level,
   calibration state, silence entry/exit, drive/follower thresholds, cross-device amplitude
   ratios, or plate behaviour produced through malformed quiet-state normalisation.

Merely originating in this device/config epoch is not enough. Programme-relative findings,
palette-derived colour references, source-level control-flow findings and renderer defects
unrelated to input amplitude retain their narrower value and need only the acceptance rerun
required by the Rev B plan.

The first known runtime members are `k1_bench_im69d` builds `git=3b59794` at epochs
`1785926464`, `1785927357` and `1785931519`; the later confirmed member
`git=cf66e27 epoch=1785955930` has a full `B489A500` preflight receipt. The predicate
continues through mono-default descendants (`hueaud*`, `colourfix`, `calfix*`, `hpf`) only
for claims meeting dependency condition 4. There is deliberately no date end-cap.

### Excluded from the bad epoch, with narrow claims only

- Unit 2 `0C54FC00`, pins `39/38`, explicit ESP-IDF RIGHT-slot builds: unaffected by this
  B489 epoch; no cross-unit physical-board inference is implied without its own strap receipt.
- B489 historical `k1_bench_im69d_micb`, `hpf_slotr` and other explicit RIGHT captures:
  valid as physical IM1 / board-left / SELECT HIGH evidence within their capture receipts.
- B489 stereo captures: valid for two-array activity, duplication/correlation and response
  where CRC and capture identity are present. G1 maps index 0 to physical IM1 and index 1
  to physical IM2; historical `L/R` array labels are superseded.
- Main K1 `F887A500` / SPH0645 evidence: outside the IM69D epoch.
- Source-only reasoning and byte-inert flag-off proofs: unaffected as reasoning/provenance,
  but any claimed device behaviour still requires acceptance rerun on verified-good input.

The B489 IM69D calibration namespace (`/cal_profile_im69d.bin` and
`/CONFIG_IM69_*.BIN`) is a carrier: a later binary does not cleanse values learned or
restored under the bad predicate.

## 2. Manifest

`TOMBSTONED` means inadmissible as behaviour/measurement evidence. `RE-DERIVED` means the
old artefact remains quarantined until the named later task produces replacement evidence;
the disposition is assigned now, not falsely claimed complete. `UNAFFECTED` always carries
the narrowed claim stated in its row.

The required re-derivation set is deliberately narrow: quiet floors; calibration; silence
entry/exit; drive and follower floors; conclusions based on absolute raw amplitude;
cross-device level ratios; and plate results shaped by malformed quiet-state normalisation.

| Artefact | Originating build/config epoch | Contamination mechanism | Current consumers | Disposition | Replacement evidence |
|---|---|---|---|---|---|
| `_scratch/im69d_env_20260805/` | `B489A500`; `k1_bench_im69d`; `git=3b59794 epoch=1785926464` | Initial mono-default deployment and AP readback observed physical IM2 under ambiguous labels. | Env bring-up and device-proof docs. | **RE-DERIVED** for absolute level, calibration/silence and acoustic suitability; build/upload identity remains valid. | Post-G1 physical-IM1 acceptance. |
| `_scratch/im69d_specialist_check_20260805/` | `B489A500`; `git=3b59794 epoch=1785927357`; mono default | Serial response was attributed without naming physical IM2 or proving suitability. | `im69d130-specialist-check-2026-08-05.md`; later bring-up narrative. | **RE-DERIVED** for absolute response/suitability only; source and identity observations survive. | Post-G1 witnessed response capture. |
| `_scratch/im69d_gain_retune_20260805/` | Same `3b59794/1785927357` mono-default epoch | Gain choice was judged through the contaminated input. | `im69d130-gain-retune-2026-08-05.md`; gain comments/claims. | **RE-DERIVED** at P2; current gain value is not measurement authority. | Held-out verified-input gain/threshold distributions. |
| `_scratch/im69d_vs_main_20260805/` bench legs | `B489A500`; `k1_bench_im69d`; `git=3b59794 epoch=1785931519` | IM69D half of the A/B used the unratified mono slot. | Colour oracle config receipt, AP comparison claims, later config archaeology. | **RE-DERIVED** for audio comparisons. Main-SPH control and exact config readback remain usable provenance. | Verified-input paired A/B with matched integration windows. |
| `_scratch/im69d_phase0_gain8_20260805/` | B489 mono-default build product | Build artefact itself is not acoustic evidence; any device verdict attached to it inherited the bad input. | Phase-0 code-ready/device-proof pair. | **UNAFFECTED** for build provenance only; device behaviour is covered by the separate tombstone row below. | Existing build log; later acceptance rerun for behaviour. |
| `_scratch/im69d_gain4_20260806/` | `B489A500`; `k1_bench_im69d`; `git=cf66e27 epoch=1785955930` | Derived quiet/music distributions describe physical IM2, not the ratified physical-IM1 programme source. | `docs/forensics/im69d-bringup-2026-08-06/`; profile comments; silence/lock analysis. | **RE-DERIVED** for absolute distributions, thresholds and silence/calibration claims; programme-relative observations are not automatically erased. | P2 discovery plus independent held-out capture after G1. |
| `docs/hardware/im69d130-phase0-gain8-device-proof-2026-08-05.md` and `docs/hardware/im69d130-gain-retune-2026-08-05.md` | B489 mono-default measurements above | Device PASS and gain conclusions outran input identity. | Bring-up, profile and AP-advice narrative. | **RE-DERIVED**; source-only implementation claims survive separately. | Post-G1 device acceptance receipt. |
| `docs/forensics/im69d-bringup-2026-08-06/` | Primarily `cf66e27/1785955930`, B489 mono default | Raw distributions, RMS/crest separation, cadence and derived floors came from the contaminated input. | `k1_audio_profile.h`; silence gate; lock-floor comments; later canon. | **RE-DERIVED**. Source-reading observations may be cited only as source analysis, never measurement. | P2 distribution-tail discovery and held-out receipts. |
| `docs/forensics/unit2-bench-transfer-quiet-leg-2026-08-12.md` and `docs/forensics/unit2-bench-transfer-full-2026-08-12.md` plus their raw scratch bundles | Paired Unit 2 RIGHT vs B489 mono default | The Unit 2 leg is valid; the B489 comparator and all between-device ratios inherit the bad mono semantics, so transfer/noise conclusions are not admissible. | Joint silence fraction, transfer claim, profile-population rationale. | **RE-DERIVED** for cross-unit conclusions. Unit 2 raw leg remains valid on its own. | Repeat only if cross-unit transfer is still required, with both slot mappings proven. |
| `K1_SILENCE_JOINT_LEVEL_SSL_FRAC=1.75` and associated comments/tests from `a8b1912a` | Mixed Unit 2 RIGHT and B489 mono-default derivation | One tail in the derivation came from the contaminated comparator; the constant therefore lacks an admissible two-unit derivation. | `i2s_audio.h`, `globals.h`, `test_im69d_env_static.py`, behavioural gate and profile narrative. | **RE-DERIVED** at P2; executable value is quarantined as measurement-derived authority, not changed under P0. | Rev B T2.2 discovery → freeze → held-out validation → mutation RED. |
| `K1_AUDIO_PROFILE_IM69D130_UNIT2` population and comments from `d1fae012` | Mixed provenance: valid Unit 2 RIGHT legs plus contaminated B489/transfer premises | Population collapsed separately sourced constants into a characterised-profile claim before input identity was sound. | `k1_audio_profile.h`, IM69D env ACK removal, handovers and baseline docs. | **RE-DERIVED**; no source/config mutation under P0. | P2 contract with four separately sourced values and held-out validation. |
| `docs/forensics/im69d-consumer-baseline-2026-08-12/raw/*` and `IM69D_CONSUMER_BASELINE.md` Unit 2 rows | `0C54FC00`; explicit RIGHT; matrix build `947e2be8` | Outside B489 epoch. The data supports Unit 2 only; it cannot validate B489 or physical IM1/IM2 mapping. | Profile lock-floor and product-SPL claims. | **UNAFFECTED** as Unit 2 RIGHT-stream evidence only; any profile-wide generalisation is covered by the prior row. | Existing identified Unit 2 receipts. |
| `docs/forensics/im69d-stage1b-stage2-2026-08-12/stage1b-receipt.md` RIGHT-slot G1–G3 data | `B489A500`; explicit `K1_MIC_IM69D_SLOT_RIGHT`; `fa164732` | Outside affected predicate; G1 now identifies this stream as physical IM1. The receipt alone did not prove both capsules. | Dual-mic learnings and physical-population claim. | **UNAFFECTED** for physical-IM1 liveness/floor. The later CRC stereo receipt, not this row alone, proves both capsules alive. | G1 receipt plus retained P0 stereo evidence. |
| `docs/forensics/im69d-stage1b-stage2-2026-08-12/stereo/*` and stereo portions of `stage2-and-matrix-receipt.md` | `B489A500`; stereo env `019086c8` | Stereo delivery is outside mono-default predicate; historical L/R labels were inverted relative to ESP-IDF PDM names. | Coherence/H_C decision and dual-array claims. | **UNAFFECTED** for CRC-valid statistics; reinterpret index 0 as physical IM1 / ESP-IDF RIGHT and index 1 as physical IM2 / ESP-IDF LEFT. | G1 mapping receipt; no new physical test. |
| `_scratch/p0_stereo_20260814/` and `docs/plans/P0_FINDINGS_2026-08-14.md` | `B489A500`; stereo `623997c7`, epoch `1786716073` | Purpose-built replacement evidence; CRC, duplication, correlation and witnessed response are valid. Static straps plus driver semantics and mono/stereo fingerprint establish physical labels. | Current handover, T0.1b and G1. | **UNAFFECTED** and accepted as G1 mapping evidence. | `G1_AP_INPUT_SLOT_RATIFICATION_2026-08-15.md`. |
| B489 `/cal_profile_im69d.bin` and `/CONFIG_IM69_*.BIN` values learned/restored under mono-default builds (including SSL/DC/sweet-spot state carried into later boots) | Device-side persisted state; bad predicate origin may predate the consuming binary | Calibration graded the wrong delivered stream; later load does not cleanse provenance. | B489 mono/default descendants and any measurement that cites `cal_source=persisted_profile`. | **TOMBSTONED** as calibration authority. Do not recalibrate before Captain's verbal silence confirmation and G1-authorised mapping. | Fresh post-G1 calibration receipt, only after verbal silence confirmation. |
| `_scratch/colour_fix_20260813/` and `docs/forensics/colour-fix-baselines-2026-08-13/*.json` | `B489A500`; `k1_bench_im69d_hueaud*`/`colourfix`; mono-default descendants | Absolute/silence-normalised render metrics used physical IM2 without a suitability check; JSONs also omit full identity. | Colour-fix ledger, promotion plan, authored-deployment claims. | **RE-DERIVED** only for silence rest, absolute drive/brightness and malformed quiet-normalisation conclusions. Palette coverage, temporal relationships and programme-relative findings remain provisional evidence. Source-level fixes survive. | Verified-IM1 full-axis acceptance plus render-output oracle. |
| `docs/forensics/colour-fix-lane-2026-08-13.md`, `colour-fix-promotion-plan-2026-08-13.md`, and device-behaviour claims in `colour-nuance-regression-verdict-2026-08-13.md` | B489 mono-default colour epochs; persisted config changed across legs | Claims of absolute music coupling, silence rest and acceptance depended on capsule selection/config; static and programme-relative findings do not. | Colour promotion and handovers/canon. | **RE-DERIVED** for absolute/silence-dependent acceptance. Static flag inventory, code reasoning, palette references, unrelated renderer defects and programme-relative findings are **UNAFFECTED** within those scopes. | T3.3 verified-IM1 rerun and G3 eyes-on. |
| Golden Aug-8 readback `04215afb…` and Aug-5 20:15 config dump | B489 historical bin/config pair; mono input not proven | The pair still records Captain's desired palette/colour appearance and exact config, but cannot prove acoustic coupling or a healthy input. Audio-derived config fields are not calibration authority. | `k1-colour-truth` and colour regression verdict. | **UNAFFECTED** as a visual/config reproduction oracle only. | G3 optical comparison; never cite it as AP-input evidence. |
| Colour and AP source changes PRs #49–#63 (including partial-cal and subsonic-HPF work) | Source reasoning plus bad-epoch acceptance legs | A coherent code argument can survive; device acceptance cannot. Refuted mechanisms are already recorded in current canon. | Current source and historical handovers. | **UNAFFECTED** as source changes; acceptance is **RE-DERIVED** through the rows above. No production promotion follows from this row. | Post-G1/P2/P3 gates, including render-output and plate evidence. |
| `docs/hardware/device-build-registry.md` B489 rows | Identity/deployment readbacks across multiple epochs | Binary/env/chip identity is not invalidated by a deaf input; behavioural adjectives or calibration-health conclusions would be. | Upload targeting and device history. | **UNAFFECTED** for identity/deployment facts only. | Current identity guard plus future post-G1 registry receipt. |
| Production `k1_hardware` stable sections and main-SPH evidence | `F887A500`; SPH0645; production env | Outside device+mic predicate. | Production release baseline. | **UNAFFECTED**; must remain byte-inert until P4. | `mic_stable_byte_gate.sh` receipt in this closeout. |

## 3. Consumer rule

Any future document, constant, test fixture or promotion plan that cites a `TOMBSTONED` or
`RE-DERIVED` claim must cite this manifest and the replacement evidence. Merely copying a
number into a new file does not create a new epoch. Do not expand a row-level quarantine
beyond the dependency stated in that row. Where source reasoning survives, the claim must
say “source-reasoned; device acceptance pending”, not “proven”.

## 4. Completeness gate and residual boundary

The manifest inventory was built from the epoch predicate, the `70b03e54` env introduction,
runtime build/config receipts and consumer tracing from the two promoted candidates
`a8b1912a` and `d1fae012`. The mechanical anchor gate requires every known root below to
appear in this file:

```text
_scratch/im69d_env_20260805/
_scratch/im69d_specialist_check_20260805/
_scratch/im69d_gain_retune_20260805/
_scratch/im69d_vs_main_20260805/
_scratch/im69d_gain4_20260806/
docs/forensics/im69d-bringup-2026-08-06/
docs/forensics/unit2-bench-transfer-full-2026-08-12.md
K1_SILENCE_JOINT_LEVEL_SSL_FRAC=1.75
K1_AUDIO_PROFILE_IM69D130_UNIT2
_scratch/colour_fix_20260813/
docs/forensics/colour-fix-baselines-2026-08-13/
/cal_profile_im69d.bin
_scratch/p0_stereo_20260814/
mic_stable_byte_gate.sh
```

Residual boundary: ignored scratch data without a build/config receipt cannot be proven to
belong to, or be outside, the epoch. Such data is **inadmissible for device/config-dependent
claims by default**, not silently classified as unaffected. T0.1b, T0.2 and G1 are closed.
No further physical microphone test is authorised. Every listed P2/P3 re-derivation remains
open.

## 5. Validation receipt

Run from repo root on `main` at `d4a6fb87`:

| Command | Result |
|---|---|
| `bash scripts/agent/session-bootstrap.sh` | **PASS** after active-authority routing was repaired. |
| Manifest anchor checker with `_scratch/im69d_gain4_20260806/` deleted in-memory | **RED_CAUGHT** — omitted bad-epoch bundle detected. |
| Same checker on this manifest | **GREEN_PASS**, 14/14 required anchors present. |
| `bash scripts/regression-harness/mic_stable_byte_gate.sh` | **PRE-G1 PASS** — `k1_hardware`, `k1_bench_reference`, `k1_bench_im73d` stable sections byte-identical; no `--update`. T0.3 rerun is recorded in the G1 receipt. |
| `git diff --check` plus firmware/config/reference path guard | **PRE-G1 PASS** for the manifest closeout. T0.3 later changes bench/diagnostic source/config under G1 authority and is separately gated. |

Post-G1 T0.3 closeout is recorded in
`docs/forensics/G1_AP_INPUT_SLOT_RATIFICATION_2026-08-15.md`: full host suite
**1079 passed, 1 skipped**; affected and production builds PASS; protected stable sections
remain byte-identical.

No screenshots, renders, device capture or calibration were produced in this documentation
closeout.

## 6. Stop state

- G1 is **RATIFIED**; T0.3 bench/diagnostic configuration and ratchets are **COMPLETE**.
- No calibration was started.
- No production slot was changed.
- P0.0 quarantine indexing is closed.
- No further Captain microphone handling is authorised.

---
**Document Changelog**

| Date | Author | Change |
|---|---|---|
| 2026-08-15 | Captain / agent:codex | Ratified G1 and narrowed quarantine to capsule/absolute-level/calibration/silence dependencies; cancelled all further physical microphone handling. |
| 2026-08-15 | agent:codex | Closed P0.0 as a device+config-epoch admissibility manifest; dispositioned bad measurements, derived constants, consumers, exclusions and residual unknowns. |
