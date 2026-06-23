---
abstract: "Operational hardware-gate package for the K1 refactor (Spike #1 FAILED → bounded-bisect hardware VP gating is the locked model). PART 1: the harness contract — exact build flags, AP+VP evidence surfaces with exact serial commands, per-metric PASS/FAIL thresholds, the VP-semantics classifier contract (filepath rules + I/O + effect), hardware-session cadence, WAVEFORM_FAST regression-injection test, and STOP/escalation rules. PART 2: the freeze-baseline capture plan — exact pre-freeze commit order, the immutable Freeze tag, K1-repo reference-artefact locations, the exact Captain capture sequence, and the dependency map between Freeze baseline / WAVEFORM_FAST fix / Deliverables #3+#4 / Spike #2. native_vp is dead and must not re-enter the plan. This doc tells the executing agent exactly what evidence to capture, what runs, what passes, what fails, and when to STOP. Production Row 1/2/3/4 execution does NOT start until this package + the Freeze baseline are locked."
---

# K1 Refactor — Hardware Gate Package (bounded-bisect, Spike #1 FAIL branch)

| Field | Value |
|---|---|
| Date | 2026-05-25 |
| Status | **LOCKED-AS-AMENDED 2026-05-25** — conditional approval + 3 amendments + post-lock source-correction errata (mode count 13→12, deterministic 12→11, quantum_collapse mode 9→6, legacy `ap_stream` split from timed `ap_capture`, legacy `vp_out_test` split from `vp_probe=all`, harness-env verification) + VP Tier B stimulus correction (silence-only; tone belongs to AP). Parts 1+2 are one package; they must not drift. |
| Gate model | Bounded-bisect HARDWARE VP gating (Spike #1 FAILED, Captain ruling 2026-05-25 option B) |
| Baseline anchor | `9423ea0` (hotkey-layer commit); Freeze tag applied after pre-freeze commits (Part 2) |
| Supersedes | native VP gate (DEAD — see line below) |

> **native_vp is DEAD.** No native build, no shim layer, no vendored FixedPoints patch, no `[env:native_vp]` may re-enter the plan. Spike #1 proved the firmware's compiler (xtensa-gcc) is more permissive than any modern desktop compiler (AppleClang 17 + GCC-15 both reject `FixedPoints` `static constexpr SFixed`), so a native build cannot certify hardware equivalence. Evidence: `spike-1-native-compile-outcome.md §8`. The throwaway worktree `/Users/spectrasynq/SB-spike1-native-vp` is retained as evidence only.

---

# PART 1 — Harness contract (what evidence is acceptable)

## 1.1 Build (harness-enabled firmware)

Captain flashes the harness build for every capture session:

```
pio run -e k1_hardware_harness -t upload --upload-port /dev/tty.usbmodem1101
```

- The harness build is the committed env **`[env:k1_hardware_harness]`** in `platformio.ini`: it `extends = env:k1_hardware` and appends the three evidence-surface flags (`-DENABLE_AP_STREAM=1 -DENABLE_FRAME_DUMP=1 -DENABLE_VP_PROBE_CMD=1`). `ENABLE_AP_STREAM` gates the new structured AP capture surface (`:ap_capture=<ms>`); it does **not** redefine the legacy boolean debug command `:ap_stream=on|off`. Verified to resolve the full inherited release flag-set, the three harness flags, and `upload_port=/dev/tty.usbmodem1101` via `pio project config --json-output` (2026-05-25). *(There is no `--build-flag` option in PlatformIO `pio run`; the prior command was invalid — flags must live in a committed env.)*
- Release builds use **`[env:k1_hardware]`** (these three flags absent) → zero hot-path cost. The envelope check (`docs/refactor/baseline-envelope.json`) is measured with the release env, not the harness env.
- Port: `/dev/tty.usbmodem1101` (K1), explicit in the command above (the env also pins `upload_port`/`monitor_port` to it). **NEVER `/dev/tty.usbmodem02` (S2, protected).**
- Agent NEVER opens the port. Captain runs upload + monitor; agent reads the captured log file.

## 1.2 Evidence surfaces

### Existing legacy/debug commands (not sufficient for Freeze baseline)

| Command | Exists? | Emits | Metrics extracted |
|---|---|---|---|
| `:dump_raw=silence` | EXISTS (`99a730b`) | raw I2S frame dump under silence | DC_OFFSET, noise floor |
| `:dump_raw=tone` | EXISTS | raw I2S frame dump under 1 kHz tone | bit-alignment, rail behaviour |
| `:ap_stream=on\|off` | EXISTS | legacy 1 Hz `[AP]` debug telemetry; defaults ON in current source, and `:stop` / stream changes turn it OFF | SSL, DC, max_raw, follower, peak_scaled, silent_scale, silence |
| `:vp_out_test` | EXISTS | legacy 9-mode VP probe (`GDFT`, `GDFT_CHROMAGRAM`, `GDFT_CHROMAGRAM_DOTS`, `BLOOM`, `BLOOM_FAST`, `VU`, `WAVEFORM_FAST`, `WAVEFORM`, `WAVEFORM_HYBRID`) | diagnostic hashes only; **NOT** the Freeze Tier-A baseline after Phase-1 harness lands |

### Phase-1 structured harness commands

| Command | Exists? | Emits | Metrics extracted |
|---|---|---|---|
| `:ap_capture=<ms>` | PHASE-1 ADD (`-DENABLE_AP_STREAM`) | structured AP baseline stream for `<ms>` with distinct harness tags (not legacy `[AP]`) | SSL, max_raw range, peak_scaled range, follower mean, spectrogram argmax @1kHz, chromagram mean, silence_flag |

### VP surface (visual pipeline)

| Command | Exists? | Emits | Metrics extracted |
|---|---|---|---|
| `:vp_probe=all` | PHASE-1 ADD (`-DENABLE_VP_PROBE_CMD`; machinery EXISTS at `lightshow_modes.h:1696-1911`; legacy command is `:vp_out_test`) | per-mode deterministic render hash + energy, seeded synthetic input | **Tier A:** FNV hash + energy per mode |
| `:frame_dump=<metric>,<mode>,<dur>,<every_n>` | PHASE-1 ADD (`-DENABLE_FRAME_DUMP`) | live per-frame stream | **Tier B:** FNV hash, total energy, centre-of-mass (COM) spatial moment, FPS |

**Mode roster (12 total — `NUM_MODES=12`, source-verified `.ino:58-74`):** Tier A covers the **11 deterministic** modes after Deliverable #3 extends `vp_probe_print_mode()` enumeration to the full roster. `quantum_collapse` (**mode 6**; index 9 is `BLOOM_FAST`) is **non-deterministic by design** (`random_float()`→`esp_random()`, `utilities.h:75` / `lightshow_modes.h:1059`, + persistent state arrays) → Tier B + visual smoke only, NOT Tier A.

## 1.3 PASS/FAIL thresholds (per surface)

| Surface | Metric | Threshold | Tolerance type |
|---|---|---|---|
| VP Tier A | per-mode FNV hash (11 det. modes) | **bit-identical vs Freeze Baseline** | ZERO tolerance |
| VP Tier A | per-mode energy | bit-identical | ZERO tolerance |
| VP Tier B | total energy | within ±band (set at baseline, §2.5) | band |
| VP Tier B | COM-slope | within **±10%** | fixed (transport-drift detector — the WAVEFORM_FAST 1.60× class) |
| VP Tier B | FPS | within **±5%** | fixed |
| VP Tier B | `quantum_collapse` | per Deliverable #4 measured run-to-run band (widened) | band; if it wanders beyond a usable band, mode 6 has ZERO automated coverage → mandatory visual smoke on every touch |
| AP | SSL, DC, max_raw range, peak_scaled range, follower mean, spectrogram argmax, chromagram mean | within ±band per metric (set at baseline, §2.5) | band |

A gate PASSES iff: all 11 Tier A hashes bit-identical AND all Tier B metrics within band AND all AP metrics within band. Otherwise FAIL.

## 1.4 Diff scripts (`scripts/regression-harness/`, K1 repo)

| Script | Input | Output | Exit |
|---|---|---|---|
| `parse_serial.py` | captured log file | normalised tagged blocks (JSON) | 0 ok |
| `ap_diff.py` | AP capture JSON + baseline | per-metric PASS/FAIL table | 0=all PASS |
| `vp_diff.py` | VP capture JSON + baseline | Tier A hash match table + Tier B band table | 0=all PASS |
| `run_diff.sh` | log dir + baseline dir | orchestrates all of the above | **0 = gate PASS; nonzero = gate FAIL** |
| `vp_semantics_classifier.py` | git diff (range or staged) | `VP-SEMANTICS: yes/no` + which rule fired | 0 always (advisory) |

Agent runs these off-target (no hardware) on the Captain-captured log files.

**Preflight invalid-capture rule:** if a purported Freeze baseline log contains `Bad command: ap_capture`, `Bad command: vp_probe`, legacy-only `[AP]` telemetry in place of structured AP harness tags, or legacy `:vp_out_test` output in place of `:vp_probe=all`, the capture is invalid. STOP and rebuild/flash the Phase-1 harness firmware before recapturing.

## 1.5 VP-semantics classifier contract

**Purpose:** decide whether a commit needs an in-sub-phase hardware gate (bounded-bisect) or can ride to the next sub-phase boundary.

**Input:** a git diff (commit range or staged hunks).

**Returns `VP-SEMANTICS: yes`** if the diff touches ANY of:
- `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h` (any `light_mode_*` body or `vp_probe_*`)
- post-split `render/**`, `color/**` translation units
- `led_utilities.{h,cpp}` render/color functions (the 58 functions Row 4 relocates)
- shared `vp_*` render state in `globals.{h,cpp}` (`vp_render_secondary_channel`, `hue_position`, `chroma_val`, `chromatic_mode`, waveform/vu `*_primary` state)
- `Palettes.h` palette data (feeds `ColorFromPalette`)
- `constants.h` colour tables: `note_colors`, `hue_lookup`, `incandescent_lookup`, `gamma8_lut`, `dither_table`
- **quantum_collapse-specific** (compensating control): `random_float`, `wave_probabilities[]`, `fluid_velocity[]`, `temp_field[]`, `temp_fluid[]`, `animation_phase`, `wave_phase`, or any audio input it reads (`bass_energy`/`mid_energy`/`high_energy`/`audio_vu_level`)

**Returns `VP-SEMANTICS: no`** otherwise (e.g., comment-only, build-config, AP-neutral system/serial changes).

**Effect:**
- `yes` → commit gets an in-sub-phase hardware VP gate before merge.
- `no` → commit rides to the next sub-phase-boundary hardware gate.
- **Any commit touching `quantum_collapse` or its call-graph ALSO requires mandatory Captain visual smoke** (mode 6 has no Tier A coverage).

**Classifier is advisory, not authoritative:** when in doubt it returns `yes` (fail-safe toward more gating). A `no` that's wrong is caught at the sub-phase boundary; the cost is a wider bisect window, never a missed regression.

## 1.6 Hardware-session cadence

| Trigger | Capture | Who |
|---|---|---|
| Sub-phase boundary (before merge to `refactor/main`) | FULL: AP + VP Tier A + VP Tier B + visual smoke | Captain |
| VP-semantics-flagged commit within a sub-phase | VP Tier A + Tier B (AP only if commit is AP-semantics: 5b globals / 5f audio) | Captain |
| `quantum_collapse`-touching commit | + visual smoke | Captain |
| AP-neutral, VP-neutral commit | none (rides to boundary) | — |

Estimated Captain load: ~15-22 hardware sessions across the refactor (Phase 1 freeze + Phase 3 strips + Phase 4 + ~7 Phase-5 sub-phase boundaries + flagged commits).

## 1.7 WAVEFORM_FAST regression-injection test (proves the gate detects)

Phase 4 hardening, once and recorded:

1. Throwaway branch off `refactor/main`.
2. Revert the WAVEFORM_FAST fix (which lands pre-freeze as commit 1 — see Part 2).
3. Captain captures `:frame_dump=com,7,5000,4` (mode 7, COM metric) on the reverted build.
4. Agent runs `vp_diff.py` vs Freeze Baseline.
5. **Expected: FAIL on COM-slope for mode 7** (the ~1.6× transport drift exceeds ±10%).
6. Record in `docs/forensics/2026-05-27-harness-detector-validation.md`. Discard throwaway branch.

If step 5 PASSES (no FAIL), the harness is NOT a detector → STOP, fix the harness before trusting any gate.

## 1.8 STOP / escalation rules

- **Any Tier A hash mismatch** → STOP. Investigate. Revert the commit if root cause not found in 30 min.
- **COM-slope outside ±10%** → STOP (transport-drift regression).
- **Any AP metric outside band** → STOP.
- **Two same-type failures** → STOP and escalate to Captain (state attempt, mechanism, alternative).
- **Tolerance-widening request** → escalate; default answer NO, fix the code.
- **Any calibration command** (`:start_noise_cal`, `N`/`Y`) → only under Captain-confirmed verbal silence. Agent never auto-fires.

---

# PART 2 — Freeze-baseline capture plan (when/how the evidence is captured)

## 2.1 Pre-freeze commit order (on `feat/pio-core-bump`, each its own commit, IN ORDER)

1. **WAVEFORM_FAST mode-7 fix** (`lightshow_modes.h:1310-1312`, dt-scaled transport mirroring `light_mode_waveform_hybrid`). **The ONLY intentional VP-output change in the entire refactor.** Captain visual smoke before commit. After this, baseline is immutable; gate semantics = "any divergence = regression."
2. **Deliverable #4 — vp_probe reset helper** (`vp_probe_reset_mode_statics()` + call from `vp_probe_prepare_render`). Output-inert on render path. **Runs on hardware — NOT native-dependent — so Spike #1 FAIL does not block it.** Reset scope MUST include the `VU_DOT`, `KALEIDOSCOPE`, and `QUANTUM_COLLAPSE` persistent statics (all absent from the current 9-mode probe but carrying per-frame state). Resetting quantum state does **not** make `quantum_collapse` Tier-A deterministic because it still reads `esp_random()` through `random_float()`. Immediate pass test: current 9 probed modes twice in one run, bit-identical. Final 11-mode bit-identical pass is performed after Deliverable #3 extends enumeration.
3. **Deliverable #3 — vp_probe enumeration → full 12-mode roster** (`lightshow_modes.h:1873-1881`; current probe covers only 9 — omits `VU_DOT`, `KALEIDOSCOPE`, `QUANTUM_COLLAPSE`). Emits **11 Tier A deterministic rows + an explicit non-deterministic/excluded `quantum_collapse` (mode 6) row**; `vp_probe=all` must make unambiguous that quantum is NOT Tier A. Output-inert. Gated on #2.
4. **AP harness firmware** — add the timed structured `ap_capture=<ms>` harness stream behind `-DENABLE_AP_STREAM`. Do **not** overload the existing boolean `ap_stream` (today an unconditional 1 Hz AP-debug toggle, `serial_menu.h:1398` + `i2s_audio.h:444`). Output-inert (release flag OFF).
5. **VP Tier B firmware** — `frame_dump=...`, `-DENABLE_FRAME_DUMP`. Output-inert.
6. **`vp_probe=all` command exposure** — `-DENABLE_VP_PROBE_CMD`, as the harness-facing replacement/alias for the current legacy `:vp_out_test` command. Output-inert. Current `:vp_out_test` remains legacy/debug and must not be used as Freeze Tier-A evidence.

(No `[env:native_vp]` commit — native is dead. Item 7 from the old plan is struck.)

## 2.2 Freeze tag + reference-artefact locations (all in K1 repo)

After commits 1-6, Captain authorises:
- `git tag refactor-baseline-<date> <HEAD>` — immutable.
- Backup branch + push to remote (Weakness 8 fix — Captain chooses remote).
- `refactor/main` branched from the tag.
- Reference artefacts (committed + tagged with the freeze tag; filesystem read-only as defence):
  - `docs/refactor/baseline-envelope.json` — flash/RAM measured with harness flags OFF.
  - `docs/refactor/harness-baselines/freeze-<sha>/` — AP + VP Tier A + VP Tier B canonical captures.
  - `docs/refactor/harness-baselines/freeze-<sha>/CANONICAL.md` — the Freeze Baseline record.
  - `scripts/regression-harness/` — diff scripts (Phase 4 deliverable).

## 2.3 Captain capture session (exact sequence)

**Calibration is NOT part of this sequence.** Noise recalibration (`:start_noise_cal`, or the `N`/`Y` arm/confirm hotkeys) is an **explicit, Captain-only pre-step** — never a scripted harness step. It is fired only under Captain-confirmed verbal silence (project calibration policy; §1.8) and **only when a recal is actually warranted** (e.g. ambient change since the last good cal). Firing it under non-silent conditions poisons the calibration (Stage-7 incident, 2026-05-24: `SWEET_SPOT_MIN_LEVEL` 281 → 745). When a recal is performed it produces its **own recorded artefact**, captured and committed *separately* from the baseline below: `docs/refactor/harness-baselines/freeze-<sha>/recal-<timestamp>.md` (recal trigger/reason, confirmed-silence attestation, resulting `SWEET_SPOT_MIN_LEVEL` and DC values). **This capture sequence assumes the active calibration is already good and Captain-confirmed.**

Baseline capture assumes pre-freeze items 4-6 have landed, the harness build (§1.1) has been flashed, and the harness commands below are accepted without `Bad command` output. Captain then runs in order:

```
# Silence leg (calibration already confirmed-good — see note above; NOT fired here)
:dump_raw=silence
:frame_dump=all,<mode>,5000,4   # VP Tier B: for each of 12 modes under confirmed silence only

# VP Tier A (no acoustic stimulus required)
:vp_probe=all              # 11 deterministic modes; quantum_collapse (mode 6) excluded/marked non-det

# AP tone leg
:dump_raw=tone             # 1 kHz tone applied (stimuli manifest, §2.6)
:ap_capture=5000           # AP tone metrics: spectrogram argmax, raw/scale/follower response

# AP music legs
:ap_capture=5000           # track-A (§2.6)
:ap_capture=5000           # track-B (§2.6)
```

Captain hands the log directory to the agent. Agent parses → writes canonical baseline JSON → `CANONICAL.md`. Files committed + tagged + chmod read-only.

## 2.4 Dependency map (freeze ↔ fixes ↔ deliverables ↔ spike)

```
WAVEFORM_FAST fix (commit 1) ──┐  only intentional VP change; baseline encodes CORRECTED mode 7
Deliverable #4 reset helper ───┤  pre-freeze; hardware; enables reproducible Tier A
Deliverable #3 full 12-mode probe ┤  pre-freeze; gated on #4
AP/VP harness firmware ────────┘  pre-freeze; flag-gated, output-inert
                  │
                  ▼
        FREEZE BASELINE (immutable tag)  ← gate reference for all of Phase 3/5
                  │
   Spike #2 (aggregate-init) ── separate; PASS required before Row 3 + Row 4 (proves
                                CONFIG_DEFAULTS relocation byte-identical). NOT native;
                                builds k1_hardware. Sequence before Row 3 execution.
```

- Deliverables #3/#4 are **hardware**, so Spike #1 FAIL does not block them.
- Spike #2 still required for Row 3 (globals minimal) + Row 4 (led_utilities) — it gates those splits, not the freeze.

## 2.5 Tolerance-band-setting procedure (bands come FROM the baseline)

Exact numeric bands cannot be set before the Freeze Baseline exists. Procedure:
1. Capture Freeze Baseline (§2.3).
2. Capture a SECOND baseline run (same build, same stimulus per surface: silence for VP Tier B; tone/track-A/track-B for AP) → measure run-to-run noise per AP metric and per Tier B metric.
3. AP band per metric = max(run-to-run noise × 2, a Captain-ratified floor). Tier B energy band likewise.
4. Tier A = zero tolerance (bit-identical) regardless — the reset helper guarantees reproducibility (verified by Deliverable #4 pass test).
5. COM-slope ±10% and FPS ±5% are fixed (not baseline-derived).
6. `quantum_collapse` Tier B band = Deliverable #4's measured run-to-run wander; if unusable, mode 6 → visual-smoke-only.

Bands recorded in `CANONICAL.md` and consumed by `vp_diff.py`/`ap_diff.py`.

## 2.6 Stimuli manifest (REQUIRED — bands are stimulus-bound)

The Freeze Baseline bands (§2.5) and every subsequent gate capture are only comparable if the **exact same stimuli** are replayed. A stimuli manifest is therefore a **mandatory baseline artefact** — committed + tagged with the Freeze tag at `docs/refactor/harness-baselines/freeze-<sha>/stimuli-manifest.md`. No gate capture is valid against a baseline whose stimuli it cannot reproduce from this manifest.

Required entries — all three:

| ID | Stimulus | Manifest must record |
|---|---|---|
| `tone-1k` | **1 kHz reference tone** | exact frequency (1000 Hz), waveform (sine), playback level (dBFS or knob position), source device + output path, applied acoustically through the MEMS, duration |
| `track-A` | **Music track #1** (Captain-pinned) | title + artist, file/source + exact duration, the precise start/stop offsets of the captured 5 s window, playback level, source device |
| `track-B` | **Music track #2** (Captain-pinned) | as `track-A` |

Rules:
- VP Tier B `:frame_dump=all,<mode>,5000,4` uses **confirmed silence only**. Do not run tone/music `frame_dump` legs for the freeze baseline.
- `:dump_raw=tone` and the tone `:ap_capture=5000` run use `tone-1k`. The music `:ap_capture=5000` runs use `track-A` then `track-B` (one each).
- The manifest is **immutable once the Freeze tag is applied** (same defence as the baseline captures: committed, tagged, filesystem read-only). Changing any stimulus invalidates the baseline and requires a new Freeze.
- A recal pre-step (§2.3) does not alter stimuli; it is logged in its own `recal-<timestamp>.md`, not here.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-25 | claude-code (Opus 4.7) + Captain Yeap | Created. Hardware gate package (Spike #1 FAIL branch). Part 1: operational harness contract — build flags, AP+VP surfaces with exact commands, PASS/FAIL thresholds, VP-semantics classifier contract, cadence, WAVEFORM_FAST injection test, STOP rules, native_vp-is-dead statement. Part 2: freeze-baseline capture plan — pre-freeze commit order, freeze tag + K1-repo artefact locations, exact Captain capture sequence, dependency map (freeze ↔ WAVEFORM_FAST ↔ Del #3/#4 ↔ Spike #2), tolerance-band-setting procedure. #11 + #13 written as one coupled package. Awaiting Captain lock. |
| 2026-05-25 | claude-code (Opus 4.7) | **LOCKED** after Captain conditional approval. 3 amendments: (1) §1.1 — replaced the invalid `--build-flag` command (no such `pio run` option) with the committed env `[env:k1_hardware_harness]` (added to `platformio.ini`: `extends env:k1_hardware` + the 3 evidence flags; verified resolvable via `pio project config`), pinned command `pio run -e k1_hardware_harness -t upload --upload-port /dev/tty.usbmodem1101`. (2) §2.3 — removed `:start_noise_cal` from the default capture sequence; recal is now an explicit Captain-only pre-step under confirmed silence with its own `recal-<timestamp>.md` artefact, per the load-bearing calibration policy. (3) Added §2.6 — mandatory stimuli manifest (1 kHz tone + 2 Captain-pinned music tracks), immutable at Freeze, bands are stimulus-bound. |
| 2026-05-25 | claude-code (Opus 4.7) | **Source-correction errata after lock; re-locked (LOCKED-AS-AMENDED).** Source beats the lock (Captain ruling). Corrected vs `.ino:58-74`: roster 13→**12** modes; Tier A deterministic 12→**11**; `quantum_collapse` mode 9→**6** (index 9 is `BLOOM_FAST`); Deliverable #3 reframed to full 12-mode enumeration (current probe=9; adds VU_DOT/KALEIDOSCOPE/QUANTUM_COLLAPSE, quantum non-det); Deliverable #4 reset scope extended to VU_DOT + KALEIDOSCOPE + QUANTUM_COLLAPSE statics and split into immediate 9-mode pass + final 11-mode pass after enumeration; AP item #4 reframed as distinct `ap_capture=<ms>`, not an overload of existing boolean `ap_stream`; `vp_probe=all` reframed as the harness-facing replacement/alias for legacy `:vp_out_test`; added invalid-capture preflight rule; §2.3 capture comments corrected (vp_probe=all = 11 det + QC excluded; frame_dump = 12 modes). §1.1 harness-env wording corrected — `pio project config --json-output` resolves the inherited release flags, the 3 harness flags, and upload port. Gate model unchanged. |
| 2026-05-25 | Codex | **VP Tier B stimulus correction.** Captain ruled VP Tier B is **silence-only** for the freeze baseline. Removed the stale dual-stimulus `frame_dump` requirement. Tone remains AP-only (`:dump_raw=tone` + tone `:ap_capture=5000`); music remains AP-only (`track-A`/`track-B` `:ap_capture=5000`). |
