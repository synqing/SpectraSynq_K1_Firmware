---
abstract: "Doctrine gate output for the K1 PlatformIO + arduino-esp32 3.2.0 + FastLED 3.10.3 migration. Reconciles MIGRATION_PLAN-v2-rebaselined.md against the LightwaveOS doctrine (12 rules) and the K1-local forensic reconstruction (2026-05-23). Captures: relevant doctrine rules, K1-local evidence touched, product-north-star impact, re-test triggers crossed, runtime proof required, minimal edit plan, explicit non-goals, and the conflicts I am NOT silently choosing. Read before producing any Stage-1 edit. Status: gate produced, no firmware touched."
---

# Doctrine gate — K1 PlatformIO / arduino-esp32 3.2.0 / FastLED 3.10.3 migration

| Field | Value |
|------|------|
| Date | 2026-05-24 |
| Repo | `~/SensoryBridge-main 9` |
| HEAD at gate | `799c55e` (branch `main`, working tree DIRTY: `.ino`, `led_utilities.h`) |
| Plan under reconciliation | `LightwaveOS_Official/docs/agent-outputs/analysis/2026-05-24-pio-core-bump-scoping/MIGRATION_PLAN-v2-rebaselined.md` |
| Doctrine source | `LightwaveOS_Official/.../analysis/sensory-bridge-lessons-doctrine.md` (12 rules) |
| K1-local forensic | `docs/forensics/2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html` |
| Author | agent:claude-opus-4-7 (executing model — per v2 §6) |
| Gate result | **NO MATERIAL CONFLICT between doctrine and K1-local evidence on this scope.** Three K1-local nuances flagged below for post-migration §12. Captain APPROVE still required for the Stage-0 WIP commit before any execution begins. |

This is a **gate, not an edit step**. No firmware touched.

---

## 1. Relevant doctrine rules (LightwaveOS — 7 of 12 in-scope; 5 out-of-scope by §3)

| Rule | Why it applies here | Re-test trigger crossed? | v2 plan response |
|------|---------------------|--------------------------|------------------|
| **R5** — Tear down monoliths by class extraction, never big-bang | The migration is intentionally narrow (build tooling + I2S driver only). It is not a monolith teardown. | No. | Compliant — §3 binds modifications to `platformio.ini`, `i2s_audio.h`, `globals.h`, `tools/`. |
| **R6** — ESP32-S3 RMT is asymmetric; FastLED config rule is *driver-of-the-day* | FastLED version bump (3.9.16 → 3.10.3) AND ESP-IDF major bump (4.x → 5.4.1) AND switch from FastLED RMT4 path to RMT5 — **three triggers in one stroke**. | **YES — three triggers crossed.** | §8 S1 drops `FASTLED_RMT_BUILTIN_DRIVER=0`, `FASTLED_RMT_MAX_CHANNELS=4`, `FASTLED_RMT_MAX_TICKS_FOR_GTX_SEM=100`, `FASTLED_ESP32_FLASH_LOCK=0`, `FASTLED_INTERRUPT_RETRY_COUNT=0` (all RMT4-era; no-ops or anti-patterns on RMT5). OI-3 in §2 carries the residual risk (RMT5 multi-strip channel allocation on S3). Fallback: `-DFASTLED_RMT_MEM_BLOCKS=1` (Lane 4 / FastLED issue #2147). |
| **R7** — I2S DMA buffer count is the FPS gate | I2S driver change (legacy → `i2s_std`) directly touches DMA sizing. | **YES.** | §8 S3 preserves `dma_desc_num=2`, `dma_frame_num=SAMPLES_PER_CHUNK=96` — explicit 1:1 of the legacy `dma_buf_count=2`, `dma_buf_len=SAMPLES_PER_CHUNK`. R7 re-validation discharges via Stage 7 frame-rate check against `ENABLE_VP_PERF_AUDIT` baseline. |
| **R8** — Q15 fixed-point wins for this 96-bin Goertzel workload | Touches DSP only if `NUM_FREQS`, sample rate, chunk size, or single-core constraint changes. | **No.** All four are unchanged. | §3 explicitly removes v1's sample-rate bump (12800→32000) as out of scope. R8 untouched. |
| **R9** — Memory corruption ⇒ erase flash first | Partition transition `min_spiffs (8 MB)` → `default_16MB.csv` is a partition-class change requiring erase. | **YES** (partition transition, not corruption — but same rule applies per CLAUDE.md). | §8 S6 — `erase_flash` is the **only** sanctioned erase, Captain-owned. G-14 pre-empted. |
| **R10** — Disable, do not delete, carry-over features | Vendored FastLED 3.9.16 + `audio_transfer.h` + dormant `driver/i2s.h` include. | n/a — applies as discipline. | §8 S1 uses `git mv libraries/FastLED → libraries/_FastLED.disabled` (Stage 1); deletion deferred to Stage 8 after Captain accepts. `audio_transfer.h` left in place — dead but disabled-style. Compliant. |
| **R11** — Fence every agentic refactor behind a `pre-*` tag and `backup/*` branch *before* it runs | Multi-file migration; load-bearing Stage 3 is exactly the refactor class this rule was forged for. | n/a — discipline. | §8 S0 creates branch `feat/pio-core-bump`, snapshot-commits the WIP **before** tagging (v1 would have tagged a dirty tree and a `git reset --hard` would have destroyed WIP — v2 §7 corrects this). Tag captured to `/tmp/rollback_tag.txt`. Compliant. |

**Out-of-scope but checked:** R1 (headers declare, .cpp defines) — this fork is the classic single-TU layout (1 `.ino` + 19 `.h`); v2 §8 S1 keeps `build_src_filter = +<*.ino>` only (BT-11, v1's defect 7 corrected). R2 (type-flow one-way), R3 (concurrency model), R4 (lock-free queues), R12 (reference doctrine alongside code) — touch nothing this migration changes.

---

## 2. K1-local evidence touched (the local fork's evidence base)

Per the doctrine bridge: K1 hardware current local source and local forensic report decide current fork state. I read the K1-local forensic (`2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html`). The migration intersects K1-local evidence as follows:

| K1-local fact | Source | Migration relationship |
|---------------|--------|------------------------|
| Working tree DIRTY: `.ino` + `led_utilities.h` carry uncommitted `SB_HAS_ROTATE8` gating + USB-strategy + LEDC-guard hardening. Six modified files total per forensic; current `git status` shows two (`.ino`, `led_utilities.h`) — others already committed at `799c55e`. | Forensic § "current dirty tree" + repo `git status` | **Must protect.** Stage 0 snapshot-commits this WIP **before** the rollback tag. Captain APPROVE required for that commit. |
| Sample extraction at `i2s_audio.h` is `(raw * 0.000512) + 56000 - 5120` then `>> 2` then `* SENSITIVITY` then clamp ±32767 then `- DC_OFFSET`. NOT `>> 14`. Field-tuned; last modified 2026-05-20 ("SINGLE-DOMAIN FIX"). | Forensic "i2s_audio_sample_math_pre_clamp" + plan §1.4 file:line | **PRESERVE VERBATIM.** §3 + §8 S3 bind lines 39-378 byte-identical. v1's defect 4 (telling agent to apply `>>14`) is removed. |
| Two-phase DC-offset calibration in `i2s_audio.h`: iters 0-127 accumulate, iter 128 stamps `CONFIG.DC_OFFSET`, iters 129-240 sample sweet-spot floor. | Forensic + plan §1.4 | **PRESERVE VERBATIM** (inside the lines 39-378 envelope). |
| Bloom transport-history fix is present in source: snapshot `leds_prev_buffer` **before** edge-fade + mirror. | `lightshow_modes.h:944-951, 955-974` (forensic Stratum B) | **OUT OF SCOPE** — `lightshow_modes.h` not touched by §3. Migration must not regress this. Stage 7 visual confirmation discharges. |
| `palette_chroma_colour()` uses circular hue vector via `cosf`/`sinf`/`atan2f`, not the weighted-index helper from memory observation #54002. Creatively useful for pitch-class wraparound; differs from canonical-doctrine suggested form. | `lightshow_modes.h:121-166` (forensic Stratum C) | **OUT OF SCOPE** — palette path not touched. **Noted as K1-local divergence from canonical doctrine** — but doctrine has no R-rule on this, so no conflict. Flag for product/behaviour review (§12 follow-up). |
| WAVEFORM/WAVEFORM-FAST currently use upper-half source trace plus conditional mirror (not symmetric-paired-dot per discussion). Bloom calls `mirror_image_downwards(leds_16)` **unconditionally** (does not obey `CONFIG.MIRROR_ENABLED`). | `lightshow_modes.h:1310-1327, 1440-1453` (forensic Stratum D) | **OUT OF SCOPE.** Product/behaviour question (forensic explicitly says so). Not migration. |
| PSRAM has had a `PSRAM ID read error: 0x00ffffff` in past runtime logs; not closed. | Forensic § "PSRAM" + § "USB Serial" | **Stage 7 must confirm `PSRAM ... 8388608 bytes` (8 MB octal) cleanly in the post-migration boot log.** If 0x00ffffff returns, that is a runtime regression and signals OPI/PSRAM mis-config. Likely orthogonal to the migration (partition-change-induced erase may help), but explicitly named so Stage 7 doesn't miss it. |
| USB serial strategy oscillated: custom descriptors → USBCDC → hardware CDC → USBSerial aliasing. Current source's USB strategy is "unproven until serial smoke captured after latest hardening." | Forensic § "USB Serial" + current dirty-tree work | **Stage 7 must confirm HWCDC enumerates and boot banner prints.** v2 §8 S1 keeps `-DARDUINO_USB_MODE=1 -DARDUINO_USB_CDC_ON_BOOT=1` — mirrors the current `USBMode=hwcdc, CDCOnBoot=cdc` shell-script setting. |
| K1 hardware compile wrapper (`tools/compile-k1-arduino.sh`) currently uses `LoopCore=0, EventsCore=0` per forensic, while docs still show `LoopCore=1, EventsCore=1`. Script and docs are out of sync. | Forensic § "Likely fixes the reported LEDC crash" | Plan §1.2 reads `LoopCore=1, EventsCore=1` from the script. **Conflict resolved by reading current source:** `tools/compile-k1-arduino.sh` HEAD is what v2 sees. PlatformIO env doesn't surface those Arduino-IDE-only FQBN knobs the same way — arduino-esp32 3.x defaults handle task pinning. Will verify in Stage 2/5 that no `xTaskCreatePinnedToCore` regression appears. (Latent forensic-vs-script staleness, not a migration blocker.) |
| Stratum F: "next truth gate is not more archaeology; it is a clean commit boundary, compile, explicit K1 hardware upload, serial boot capture, PSRAM check, I2S check, LED output check, and timing capture on the same binary." | Forensic § "Final Forensic Position" | **The v2 plan's Stage 0→7 IS this gate.** Direct alignment. |

### Auto-memory cross-check (per MEMORY TRUST FREEZE)

The global MEMORY.md surfaced this session contains:

- **`project_sb_esp32_core_pin`** — "Sensory Bridge firmware must build against esp32:esp32@2.0.9 specifically, not 2.0.17 or 3.x." **STALE / SUPERSEDED.** Captain has explicitly authorised this migration to arduino-esp32 3.2.0 via the user prompt. The pin is being retired by the migration itself. Once Stage 7 accepts, this memory needs to be tombstoned.
- **`project_sb_audio_pipeline_debug_2026-05-20`** — "Captain MEMS DC is negative (~-8767)." **APPARENT CONFLICT WITH SOURCE.** Source at `system.h init_system_full` stamps `CONFIG.DC_OFFSET = 8304` (positive) and the extraction does `waveform[i] = sample - CONFIG.DC_OFFSET`. If actual DC bias is negative, subtracting a positive value would compound it. Two possibilities: (a) memory has the sign inverted; (b) source has a sign bug. **OUT OF SCOPE for this migration** (the extraction is preserved verbatim). Flagged for §12.2 DC_OFFSET sentinel hardening. The plan's §12 already names DC_OFFSET hardening as a separate workstream — this anomaly belongs there.

Both stale-memory items are per the MEMORY TRUST FREEZE: not trusted as canonical, verified against current source. No silent acceptance.

---

## 3. Product north-star impact

The product north-star is musically meaningful visualisation that exceeds Sensory Bridge's perceptual impact. Decision rule: architecture improvement that weakens musical responsiveness, independent dual-channel behaviour, colour clarity, motion memory, or visual captivation is a regression.

| North-star pillar | Migration impact | Mechanism | Mitigation |
|-------------------|-----------------|-----------|------------|
| **Musical responsiveness** | **AT-RISK via OI-1** (data_bit_width 32 vs 24). | A clean compile with the wrong width produces silent runtime degradation: raw samples mis-scaled, downstream Goertzel constants no longer match incoming magnitudes, AGC drifts, beat tracking weakens, perceived "musical-ness" decays without any error message. Exactly the failure mode the K1-local forensic warns about. | Stage 0 baseline raw-sample capture + Stage 7 ±20% magnitude comparison + Codex review checkpoint 2 on the boot log. One-line fallback to 24-bit width if magnitude scales reveal it. |
| **Independent dual-channel behaviour** | **NEUTRAL.** | `render_lightshow_for_channel()` containment (commit `039c78a`) and the dual-strip dispatch in `led_utilities.h` are untouched by §3. `led_utilities.h` is one of the two dirty files but is **not** edited by this plan — only carried through the WIP snapshot commit. | Stage 7 visual confirmation: primary Bloom + secondary WAVEFORM-FAST (the firmware-40102 "perfect dual config") still renders independently. |
| **Colour clarity** | **NEUTRAL.** | `palette_chroma_colour()`, palette path, `pal_bl` sampling, palette-bounded sum-color — all in `lightshow_modes.h`, out of scope. No build flag changes touch colour pipeline. `-ffast-math` preserved (DSP numerics depend on it). | Stage 7 visual confirmation. |
| **Motion memory** | **NEUTRAL.** | Bloom transport-history snapshot (snapshot-before-fade-before-mirror) is in `lightshow_modes.h`, out of scope. `leds_prev_buffer` lives in `globals.h` but is not the variable being modified (only `i2s_samples_raw` gains `DRAM_ATTR`). | Stage 7 visual confirmation: Bloom reaches the edges, doesn't die mid-strip. |
| **Visual captivation** | **NEUTRAL** as long as the four pillars above hold. | Aggregate of the above. | Captain visual confirm in Stage 7 — the final acceptance gate (§5: "Captain owns final accept/reject on runtime evidence"). |

**Net:** the migration is **PROTECT-NEUTRAL for the product north star, conditional on the OI-1 runtime gate firing correctly.** The only material risk is the silent-degradation class — exactly what §10 (Stage 7) and Codex review checkpoint 2 exist to catch.

---

## 4. Re-test triggers crossed (binding — runtime proof required)

Per doctrine: "If you cross [a re-test trigger], treat the rule as a hypothesis until you re-verify on the current hardware / driver / workload."

| Rule | Triggers crossed | Re-verification required |
|------|------------------|---------------------------|
| **R6** (RMT driver-of-the-day) | FastLED version bump (3.9.16 → 3.10.3) ✓ ESP-IDF major (4.x → 5.4.1) ✓ FastLED RMT4 → RMT5 path switch ✓ | Stage 7 boot log: no `no free tx channels` / `register channel failed`. Both strips light. Frame rate ≥ baseline per `ENABLE_VP_PERF_AUDIT`. |
| **R7** (I2S DMA = FPS gate) | I2S driver change (legacy `i2s.h` → `i2s_std.h`) ✓ | Stage 7 frame-rate vs baseline. Audio not silent / not pinned. `max_waveform_val_raw` tracks loudness. |
| **R9** (erase flash on partition/corruption class) | Partition layout change `min_spiffs` → `default_16MB.csv` ✓ Flash size 8M → 16M ✓ | Stage 6 Captain-owned `erase_flash`; Stage 7 boot log shows clean boot, no LittleFS corruption, no StoreProhibited, no boot-loop. PSRAM `8388608 bytes` (8 MB OPI) — closes the prior `0x00ffffff` history. |

R8 (Q15 Goertzel), R1/R2/R3/R4 (architecture rules) not crossed.

---

## 5. Runtime proof required (the actual acceptance evidence)

The K1-local forensic explicitly calls this out: source shape is solid, **runtime evidence is incomplete**. The migration must close that gap, not just produce a clean compile.

Per v2 §10 (Stage 7), the boot log from Captain-captured `/tmp/k1_boot_stage6.log` under known audio with `debug_mode` on must show:

1. **HWCDC enumerates; boot banner prints.** (USB strategy proof — closes the forensic-flagged USB oscillation history.)
2. **`PSRAM ... 8388608 bytes`** (8 MB octal). (Closes the prior `0x00ffffff` PSRAM ID read error.)
3. **`INIT I2S (channel): PASS`, `I2S STD INIT: PASS`, `I2S ENABLE: PASS`** (Stage 3 driver-init proof.)
4. **No `CONFLICT! driver_ng` panic** (G-01 — legacy + new I2S driver coexistence.)
5. **Raw-sample magnitudes within ±20% of the Stage-0 baseline** under the same audio. **This is the OI-1 catch.** A boot log alone hides this defect.
6. **`max_waveform_val_raw` tracks loudness; not stuck at 0 or INT32 rails.** (OI-2 slot/strap catch.)
7. **FastLED RMT5: no `no free tx channels` / `register channel failed`.** (OI-3 catch.)
8. **Both LED strips light, correct colour.** (Captain visual confirm — colour pipeline intact, dual-channel independence intact.)
9. **Frame rate ≥ baseline** per `ENABLE_VP_PERF_AUDIT`. (R7 re-validation.)

**Codex review checkpoint 2** independently interprets items 1-9 against the Stage-0 baseline. This is the cross-model guard against same-family "it booted, ship it" optimism — the failure mode v1 exhibited.

**Captain owns final accept/reject.** Visual proof (Bloom doesn't die mid-strip, WAVEFORM-FAST traces correctly, dual-channel renders independently, palette colour clarity preserved) is a Captain decision, not a checklist tick.

---

## 6. Minimal edit plan (binding — matches v2 §3, §8)

**Modified by this migration only:**

| File | Change | Rationale |
|------|--------|-----------|
| `platformio.ini` (NEW, repo root) | Per v2 §8 S1 verbatim. `build_src_filter = +<*.ino>` only (BT-11). `lib_deps` includes `fastled/FastLED@3.10.3`, `file://libraries/FixedPoints`, `file://libraries/M5ROTATE8`. `-O3 -ffast-math` preserved. Dead RMT4-era flags removed. | Build-tooling migration; preserves single-TU classic-Arduino layout. |
| `SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h` | Include `<driver/i2s.h>` → `<driver/i2s_std.h>`. Replace `i2s_config_t`/`i2s_pin_config_t` structs and `init_i2s()` with `i2s_chan_config_t` + `i2s_std_config_t` (Philips defaults + only `slot_mask = I2S_STD_SLOT_RIGHT` overridden — SP-2). Replace one `i2s_read(...)` call with `i2s_channel_read(...)`. **Delete** the `#if CONFIG_IDF_TARGET_ESP32S2` register-poke block. **Preserve lines 39-378 byte-identical** (extraction, DC calibration, sweet-spot, AGC, `calculate_vu`). Keep `void init_i2s()` + `PASS/FAIL` print contract (no `ESP_ERROR_CHECK`). Keep `portMAX_DELAY`. Read size stays `SAMPLES_PER_CHUNK * sizeof(int32_t)` (v1's buffer-`sizeof` bug corrected). | Driver migration only. |
| `SPECTRASYNQ_K1_FIRMWARE/globals.h:186` | `int32_t i2s_samples_raw[...]` → `DRAM_ATTR int32_t i2s_samples_raw[...]`. | BT-04 (PSRAM cache-coherency on I2S DMA), defensive, zero-cost. |
| `libraries/FastLED/` | Stage 1: `git mv` → `libraries/_FastLED.disabled` (R10 — disable, not delete). Stage 8: `git rm` after Captain accepts. | Replaced by `lib_deps`. |
| `tools/compile-k1-arduino.sh` | Stage 8 only: `git mv` → `tools/legacy/compile-k1-arduino.sh.deprecated` after Captain accepts. | Build-tooling retirement; R10-shaped. |

All code edits carry the `.claude/CLAUDE.md` modification-traceability comment template.

**Sequencing:** Stage 0 (pre-flight + WIP commit + tag + baseline build + OI-1 baseline capture) → 1 (platformio.ini + disable vendored FastLED) → 2 (first failing compile) → 3 (I2S migration) → **Codex review checkpoint 1** → 4 (compile-clean sweep) → 5 (link verify, STOP per envelope) → **Captain Stage 6** (erase_flash + upload + serial capture) → 7 (runtime validation + **Codex review checkpoint 2**) → 8 (cleanup commit after Captain accepts).

**Per the execution envelope:** I execute Stages 0–5. Captain owns Stage 6. I resume Stage 7 only after Captain hands me the boot-log path. Stage 8 only after Captain accepts.

---

## 7. Explicit non-goals (binding — anything here = stop and ask)

The following are NOT this migration. Captain APPROVE required for any of these to enter scope; default is "stop and report":

1. **No sample-rate change.** v1 Stage 4 bumped `DEFAULT_SAMPLE_RATE 12800 → 32000` — a DSP change masquerading as a migration. Removed in v2 §3. Separate workstream in §12.1.
2. **No DC_OFFSET sentinel fix.** The corruptible-sentinel bug-class (and the auto-memory MEMS-DC sign anomaly noted in §2) is §12.2.
3. **No arduino-esp32 3.2.0 → 3.3.8 bump.** Carried only once 3.2.0 is proven stable on K1. §12.3.
4. **No `ledcSetup` → `ledcAttach` migration.** Not needed on K1 (all sweet-spot pins are −1 ⇒ `SB_HAS_SWEET_SPOT_LEDS = 0` ⇒ ledc code compiled out). Latent for non-K1 envs only.
5. **No edit to `lightshow_modes.h`, `led_utilities.h`, `GDFT.h`, `encoders.h`, `serial_menu.h`, `system.h`, `bridge_fs.h`, `audio_transfer.h`.** Outside §3 scope.
6. **No DSP, no visual change, no colour-pipeline change.**
7. **No new features. No refactor. No cleanup. No "while we're here" improvements.** If Stage 4 surfaces a real fix needed in an out-of-scope file, **stop and report to Captain**.
8. **No re-enabling any disabled feature flag** (Lane 7 BT-15 — "never implement unauthorised fixes").
9. **No `palette_chroma_colour` rewrite** to the memory-#54002 weighted-index form. K1-local current implementation is circular hue vector; product/behaviour question, not migration.
10. **No mirror-toggle behaviour change.** Bloom's unconditional `mirror_image_downwards()` and WAVEFORM's upper-half source are out of scope.
11. **No serial-port opens by the agent. No upload to `/dev/tty.usbmodem02` (S2, PROTECTED). No `erase_flash` outside Stage 6.**
12. **No tests added.** Acceptance is runtime-evidence-based per Stage 7. Adding tests = scope expansion.
13. **No concurrent refactors.** Migration only.

---

## 8. Doctrine vs K1-local conflicts (the gate's central question)

**Result: NO MATERIAL CONFLICT.**

Both sources push in the same direction for this migration's scope:

| Topic | LightwaveOS doctrine says | K1-local forensic says | Resolution |
|-------|--------------------------|------------------------|------------|
| Erase flash on partition transition | R9 — codified | Stratum F next-truth-gate names "erase + upload + serial boot capture" | **Agree** → v2 §8 S6. |
| Pre-tag + branch before refactor | R11 — verified | Forensic notes the fork carries dirty WIP and that history compression has lost granular repairs; tag-fencing is exactly the right hedge | **Agree** → v2 §7 + §8 S0, with WIP-protection upgrade. |
| RMT5 driver-day | R6 — re-test trigger crossed | K1-local has documented "LED-1-only" history at fork divergence | **Agree** → OI-3 carried, fallback documented. |
| Single-TU build | R1 / BT-11 | Fork is 1 `.ino` + 19 `.h` (current state confirmed) | **Agree** → `build_src_filter = +<*.ino>` only. |
| Q15 fixed-point Goertzel | R8 — re-test trigger NOT crossed | Forensic does not contradict; preserves it | **Agree** → out of scope. |
| Sample extraction math | (no doctrine rule; product-tuned) | `(raw * 0.000512) + 56000 - 5120` then `>>2` — field-tuned, last touched 2026-05-20 | **K1-local wins** → preserve verbatim. |
| Mirror behaviour, palette_chroma circular vs weighted | (no doctrine rule) | K1-local divergence from canonical AP_SOT memory #54002 | **K1-local wins** (it is the local fork truth) → out of scope, flagged for product review. |

**Three K1-local nuances I am preserving for §12 follow-ups (NOT acted on in this migration):**

1. **palette_chroma circular-vector vs weighted-index divergence** from canonical AP_SOT — product/behaviour decision, not migration.
2. **Bloom unconditional `mirror_image_downwards()`** (does not obey `CONFIG.MIRROR_ENABLED`) — product question.
3. **Auto-memory `MEMS DC is negative` vs source `DC_OFFSET = 8304` (positive) sign anomaly** — belongs in §12.2 DC_OFFSET hardening workstream.

None of these alters the migration's edit plan. Recording them here so they survive the migration into the post-migration review surface, instead of being silently dropped.

---

## 9. What I am about to do next (decision-grade)

1. **Run the read-only environment check** (pioarduino 54.03.20 URL reachable; PlatformIO CLI present; board ID resolution path; upload port enumeration; `~/.claude/memory/spectrasynq/L1/CANONICAL_DECISIONS.md` cross-check). No edits, no commits — pure read.
2. **Stop at the Stage-0 APPROVE gate.** Per v2 §8 S0 + the execution envelope: the WIP snapshot commit of the two dirty files (`SPECTRASYNQ_K1_FIRMWARE.ino`, `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h`) requires Captain's explicit confirmation before I run `git commit`. I will present:
   - The exact `git status` output.
   - The exact `git diff --stat` for those two files.
   - The proposed commit message and branch sequence.
   - And ask: **APPROVE the WIP snapshot commit?** (Y/N).
3. **On APPROVE**, execute Stage 0 end-to-end (branch, commit, tag, baseline build, OI-1 baseline capture), report `[COMPILE]` evidence, then propose Stage 1 (`platformio.ini`) as a unified diff and ask APPROVE again. Codex review checkpoint 1 fires after Stage 3.

No firmware edit happens before APPROVE.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-24 | agent:claude-opus-4-7 | Created — doctrine gate output for the PIO/arduino-esp32 3.2.0/FastLED 3.10.3 migration. Reconciled v2 plan against LightwaveOS 12-rule doctrine and 2026-05-23 K1-local forensic. NO MATERIAL CONFLICT found. Three K1-local nuances flagged for §12 post-migration follow-ups. Two stale-memory items (esp32 core pin 2.0.9; MEMS DC sign) flagged per MEMORY TRUST FREEZE. |
