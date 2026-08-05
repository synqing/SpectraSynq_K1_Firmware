---
abstract: "Red-team engineering-feasibility attack on the dual-K1 sync draft plan (v0.1). Verdict: SOUND_WITH_FIXES. Four MAJOR wounds verified against source: (1) the mirror-split mechanism as written produces a half-black canvas or a 2x stretch, never the claimed 2x detail; (2) blind 71-path control mirroring fires noise-cal and clobbers follower flip geometry; (3) the 39 B feature subset misses render-path AP globals (spectrogram_smooth -> chromagram_pregate palette coordinates) so seam colour diverges; (4) Phase 0 'bench units only' is not executable with one bench unit. Steel-man: NimBLE 2.5.0 dual-role, host-first Phase 1, and delay-matching maths all survive."
---

# Red-Team — Engineering Feasibility Lens (dual-K1 sync draft v0.1)

**Stance:** adversarial. Every attack below was verified against real source; file:line cited. Steel-man section records where the draft survived attack.

## A1 · MAJOR — The mirror-split mechanism cannot deliver the claimed "2× spatial detail" as specified

**Claim attacked:** plan §1 ("unique content doubles from 80 px to 160 px per arm ... 14/22 modes need zero geometry work") + §2/§5-Phase-2 ("mirror OFF, right K1 renders the arm forward ... transform at the resample seam, `scale_to_strip`/`init_lerp_params`").

**Verified facts:**
- `mirror_image_downwards()` (`visual/led_utilities.h:1222-1232`) fills the lower half [0..79] from the upper half [80..159]. All content lives in the upper half pre-mirror.
- Class-A modes write ONLY the upper half. EMBER (`effects/light_mode_ember.cpp:56`) explicitly zeroes `leds_16[0..HALF)` every frame and writes only `idx = HALF + k` (`:71-75`). With `MIRROR_ENABLED=false` the lower half is **black**, not unique content.
- `init_lerp_params`/`scale_to_strip` (`visual/led_utilities.h:848-897`) is a post-render resample of `leds_16` → `leds_scaled`. It can window and stretch existing pixels (proven parametric by the 160→224 `K1_CUSTOM_LED_V1` upsample, incl. the OOB clamp at `:859-868`); it **cannot create unique content**. `REVERSE_ORDER` flip exists at `:1014-1016`.

**Consequence:** two mutually exclusive v1s are conflated:
- (a) **Window at the resample seam** (mirror ON, sample the upper half [80..159] across 160 output LEDs, flip on the left unit): zero per-effect work, seam-centred — but each unique pixel now covers 2 LEDs, i.e. **spatial density HALVES vs today** (today: 80-px arm at 1 px/LED shown twice). Visibly chunkier; contradicts the headline claim.
- (b) **True arm widening** (effects render 160 unique px): requires the origin/basis change (HALF→NR, anchor 80→0) in effect or shared-helper code for **all 22 modes**, not just the 8 class-B — the census itself says class A needs "the generic seam-origin transform ... plus cosmetic constant review" and warns speed constants need retune "even for class-A modes" (`findings/effect-census.md` §2, §7). "Zero geometry work" is the plan's hardening of a softer census claim.

**Fix:** rewrite §1/§5-Phase-2 to pick one honestly: v1 = (a) with the density halving stated and eyes-on gated, or v1 = (b) with the 22-mode helper-level pass costed. The census supports (b) as bounded and mechanical — the architecture survives; the phase scoping does not.

## A2 · MAJOR — Control mirror "through the existing 71-path facade" ships real defects

**Claim attacked:** plan §2 "Control mirror through `sb_k1_control_apply()` (the 71-path facade)".

**Verified facts (`control/sb_k1_control_facade.cpp:379-452` `kAllowedControls`):**
- The facade includes `calibration.noise.arm`, `calibration.noise.confirm`, `calibration.noise.clear` (`:447-450`). A blind mirror replays the leader's cal arm/confirm on the follower → the follower fires noise calibration against **its own mic**, un-gated — colliding with the Captain-verbal-gated cal policy (load-bearing rule) and poisoning follower cal if room conditions differ.
- It includes `primary.mirror` (`:388`) and `primary.reverse_order` (`:390`). The follower's widened geometry **is** a forced mirror-off/flip state; mirroring these verbatim from the leader clobbers it (leader mirror-off + follower left-flip cannot both be the same literal values).
- Every set path calls `save_config_delayed()` (~30 call sites, `:492-750`) → follower flash write per mirrored control, and `mark_wireless_manual()` (`:481`) flips manual-override state on the follower.

**Fix:** the plan must specify a mirror policy table over the 71 paths: excluded (cal.*), side-transformed (mirror/reverse_order/secondary.*), and pass-through — not "the existing facade" as-is.

## A3 · MAJOR — The 39 B feature subset does not make the halves colour-identical: render-path AP globals are consumers the census of *effects* missed

**Claim attacked:** plan §2 "spectrum[80] excluded (no shipping consumer)" and the premise "give both devices identical inputs".

**Verified facts:**
- `make_smooth_chromagram()` (`visual/led_utilities.h:1875-1893`) runs in the VP render path and consumes `spectrogram_smooth[0..CHROMAGRAM_RANGE)` — the AP spectrum — every frame, producing `chromagram_smooth` → `chromagram_pregate` (`:1946`).
- Palette colour coordinates read `chromagram_pregate` directly (`visual/lightshow_modes.h:298`, `:518` — the K1 PALETTE VIBRANCY V1 engine, Captain eyes-on-passed 2026-07-03).
- Therefore "spectrum[80] has NO shipping consumer" is true only for **effect** consumers of the snapshot field; the **palette engine** is a shipping consumer of the AP spectrum via its own path. On a follower, `spectrogram_smooth` comes from the follower's own mic (or stale data) → per-pixel hue selection diverges at the seam for every palette-enabled mode, including the whole v1 roster. Streamed `chroma_pc u8×12` does not fix this: the palette engine does not read snapshot chroma.
- Additionally WAVEFORM_HYBRID (mode 11) is class A and not S-flagged, so it sits inside the stated v1 roster ("class A ∖ S"), yet the census itself records it samples raw `waveform_history` (`findings/effect-census.md` row 11, §6) — unreproducible from the 39 B stream.

**Fix:** (i) stream the quantised 12-bin pre-gate chroma (+12 B/frame) and specify the follower-side **injection surface** — the plan never says how streamed features displace the follower's own AP outputs (snapshot publish is clean; the VP-read globals `spectrogram_smooth`/`chromagram_pregate`/`waveform_history` need an explicit mux); (ii) drop mode 11 from the v1 roster or stream its inputs.

## A4 · MAJOR — Phase 0 "bench units only" is not executable as written

**Claim attacked:** plan §5 Phase 0 "Build `k1_sync_probe` env pair (bench units only)".

**Verified facts (`docs/hardware/device-build-registry.md:18-21, 56-59`; `scripts/platformio/k1_upload_guard.py`):**
- Exactly ONE bench unit exists (`B489A500`). The second K1 is the Captain's **main K1** (`F887A500`, production 6/7 LED map, SPH0645 mic, currently the live SPH reference) — or the registry's "⚠ UNREGISTERED 4th S3 — do not flash without Captain ID" (`:59`).
- A single probe env cannot serve both devices: bench is GPIO 4/5 + IM73D PDM; main is 6/7 + SPH `i2s_std`. Flashing the wrong map darkened both LED channels on 2026-07-07 — the exact incident the **uncommitted** `k1_upload_guard.py` edit in the working tree re-blocks.
- The guard passes unknown envs unenforced: `expected_target_for_env()` returns `None` → "no K1 upload mapping enforced" (`k1_upload_guard.py:122-127, 168-170`). New `k1_sync_probe` envs are silently unguarded unless registered.
- The two devices carry **different microphones** (SPH vs IM73D, different SNR/AGC behaviour) — a confound for the AGC/brightness-adoption and leader-mic measurements Phase 0 exists to make.

**Fix:** Phase 0 must name the physical pair (bench + main K1, Captain-visible since it flashes his primary with dev-probe firmware — arguably an F-class fork), define TWO pin-map-specific probe envs, register both in the upload guard and device-build registry, and state the heterogeneous-mic confound. Resolve or land the dirty guard edit before the lane builds on it.

## A5 · MINOR — "Core 1 placement" understates fixed Core-0 radio work; Phase-0 gate omits the heap watermark

- The existing BLE application task is pinned to **Core 0** today: `xTaskCreatePinnedToCore(ble_task, "ble_remoted", 4096, nullptr, 1, &s_task, 0)` (`network/ble_remoted_central.cpp:235`), and `sb_k1_ble_remoted_poll` is called from the main loop (`.ino:819`). NimBLE host-task core is a config choice, but BT **controller** work (ISR/high-priority scheduling) is not freely movable. "Core 0 stays clean" should read "Core-0 radio work minimised and MabuTrace-measured" (the plan does require the measurement — partial credit).
- The documented kill-mode is a **transient internal-heap dip** (BLE link + notify + WiFi-AP + `fopen` → abort while idle headroom is ~76 KB; `ble_remoted_central.cpp:272-285`). Phase 0 *measures* heap headroom but the **gate** criterion (§5 Phase 0) lists only transport p95 and Core-0 AP p95. Add `internal_min_ever` watermark ≥ threshold under worst-case load (dual-role + notify stream + K718 linked) as a third gate term.

## A6 · MINOR — LittleFS role file vs `factory_reset()` semantics unstated

`factory_reset()` (`persistence/bridge_fs.h:86+`) deletes an **enumerated** file list (config, noise_cal, cal_profile, preset slots); it does not format LittleFS. A new sync-role/pairing file therefore **survives factory reset** unless explicitly added — a factory-reset K1 that silently rejoins as a flipped follower is a surprising device. The plan must state the intended semantics and add (or deliberately exclude) the role file from the reset enumeration.

## A7 · MINOR — Working-tree hygiene: dirty `k1_upload_guard.py`

`git status` shows `scripts/platformio/k1_upload_guard.py` modified (uncommitted re-block of `k1_prod_im73d`, reversing `46525ed`, restoring the `b735524` posture). Any Phase-0 env/guard work stacks on an uncommitted safety change; land it first or the lane risks clobbering the misflash protection it depends on.

## Steel-man — where the draft survived attack

1. **NimBLE dual-role is configured/possible.** NimBLE-Arduino **2.5.0** vendored (`library.properties:2`; `platformio.ini:302,390`). `nimconfig.h` enables CENTRAL/PERIPHERAL/BROADCASTER/OBSERVER by default unless `*_DISABLED` (`:180-192`), `MAX_CONNECTIONS` default 3 (`:224-225`); no role-disable flags in `platformio.ini`. The ~76 KB idle headroom and transient-dip `fopen` abort claims are real and correctly cited. Dual-role is a RAM/coexistence *measurement* question, which Phase 0 owns — the architecture assumption holds.
2. **Host-first Phase 1 is not fiction.** The regression harness genuinely compiles firmware TUs with `clang++` on host (`scripts/regression-harness/onset_beat_replay.py:294-330`, `smart_director_replay.py:515+`, `chord_saliency_replay.py`, `semantic_state_replay.py`). "Two firmware-logic instances" must be two **processes** (module state is global; one process cannot host two instances) — a mechanical detail, not a blocker.
3. **`show_secondary_leds` has the true parallel path** (`led_utilities.h:2249+`: `scale_to_secondary_strip()`, `SECONDARY_REVERSE_ORDER` at `globals.h:837`, `SECONDARY_MIRROR_ENABLED` at `:828`) — deferring the secondary channel to F3 is structurally safe.
4. **The delay-matching maths is self-consistent.** If delivery p95 ≤ seam budget, worst-case inter-half offset ≤ budget even with render-on-arrival; the 1 Hz clock beacon is belt-and-braces, not load-bearing. The Phase-0 gate as latency-gated is sound on this axis.

## Missed considerations (not attacks; the plan is silent)

- **"Render what you send":** the leader renders from full-precision SQ15x16 state while the follower renders from u8-quantised streamed values → systematic (if small) seam differences. The leader should render from the same quantised values it transmits.
- **Leader CPU budget:** the leader runs audio + render + BLE central (K718) + peripheral notify at 66 Hz simultaneously; the follower is relieved, the leader is loaded. Phase 0 measures Core-0 AP p95 but not leader render-FPS under dual-role TX load.
- **`effects/framework` second surface:** dormant in shipping builds (`platformio.ini:816-818` — `k1_hardware` does not define `K1_EFFECT_FRAMEWORK_V1`), so the census skip is defensible today, but Phase 3/4 roster expansion should carry the census §6 warning forward: a widening validated only against the 22 legacy modes may not transfer to EffectRegistry/ZoneComposer effects (K1BufferView is per-strip by doctrine).
- **`mark_wireless_manual()`** on every mirrored control flips the follower's manual-override state; probably desired, never examined.

## Verdict

**SOUND_WITH_FIXES.** No attack kills the leader/follower feature-streaming architecture or the Phase-0-measures-first spine — both survived genuine attempts. But Phase 2's mechanism as written (A1), the control-mirror lane (A2), the feature-subset/injection spec (A3), and Phase 0's device plan (A4) each ship a visible defect or an unexecutable step if implemented from the current text.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (red-team SSA, engineering lens) | Created — source-verified feasibility attack on draft v0.1: 4 MAJOR, 3 MINOR, 4 steel-man survivals, 4 missed considerations. |
