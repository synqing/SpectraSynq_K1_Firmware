---
abstract: "Stage 7 handoff. K1 PIO migration is FUNCTIONAL: audio response confirmed, LEDs visibly reactive, peak_scaled varying 0.04-0.63 under music. Stage 8 cleanup partially done (TEMP DIAGNOSTIC blocks stripped from i2s_audio.h, compile clean). REMAINING: K1 operates at higher magnitudes than S2 reference — likely K1-specific noise floor or operating point. Read this BEFORE continuing the migration in a new session. Working tree has uncommitted Stage 1-8 changes ready for the consolidated commit per plan §8 S8."
---

# Stage 7 / 8 Handoff — K1 PIO Migration

## Status: WORKING but not yet committed

The migration is **functional**. K1 boots, captures I2S audio via `driver/i2s_std.h`, extracts waveform, drives LEDs visibly responsive to music. Stage 7 acceptance was confirmed verbally by Captain ("YO! THAT IS REMARKABLY BETTER. I can see the K1 ACTUALLY being responsive now").

## The fix that worked (lock this in)

`SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h` `init_i2s()` uses a **hand-built `i2s_std_config_t.slot_cfg`** with:
- `data_bit_width = I2S_DATA_BIT_WIDTH_32BIT`
- `slot_bit_width = I2S_SLOT_BIT_WIDTH_32BIT` (explicit, never trust AUTO on IDF 5.4.1)
- `slot_mode = I2S_SLOT_MODE_STEREO`
- **`slot_mask = I2S_STD_SLOT_LEFT`** ← key: hardware-RIGHT mic (SEL=3V3) on K1 is read via LEFT mask because IDF 5.4.1's slot semantic inverts when `ws_pol=true`
- `ws_width = 32`
- **`ws_pol = true`** ← Emotiscope/K1.node2 "School A" lineage
- **`bit_shift = false`** ← School A, no Philips delay
- `left_align = true, big_endian = false, bit_order_lsb = false`

The Philips macro defaults give 17-bit truncated samples on this stack (IDF 5.4.1 + S3 + SPH0645). 5 knob attempts on the Philips path failed before adopting Lixie Labs Emotiscope's `microphone.h` (then flipping slot_mask to compensate for the IDF-5.1→5.4.1 semantic shift).

## K1 vs S2 reference signature comparison

| Field | S2 reference (healthy) | K1 current | Notes |
|---|---|---|---|
| `SSL` (SWEET_SPOT_MIN_LEVEL) | 369 | 6092 | K1's silence floor is ~16× higher — different room noise, mic unit variation, or operating-point characteristic |
| `DC_OFFSET` | -8102 | 0 | S2's negative DC reflects MEMS bias correctly captured. K1's 0 means current cal averaged samples roughly centered (possibly the slot-mask=LEFT flip places sign symmetric around 0 — needs verification) |
| `max_raw` under music | 1162-8652 | 4603-12184 | ~5-10× higher magnitude on K1 |
| `follower` | 1873-7641 (tracking) | 6092-6619 (mostly pinned at SSL) | K1's follower is less dynamic — possibly because SSL is so high relative to active signal |
| `peak_scaled` under music | 0.440-0.789 | 0.087-0.629 | K1 audio dynamics compressed; midpoint lower than S2 |
| LEDs visibly responsive? | yes (S2 baseline) | **yes (Captain visual confirm)** | ✓ |

**Interpretation**: K1 has found a working operating point that differs from S2. The visual response confirms audio→waveform→LED chain is intact. The magnitude differences are probably K1-unit-specific or environment-specific, not a fault. May want to:
- Try a tighter noise calibration during deeper silence (HVAC off, machine idle, etc.): use `:start_noise_cal` or the K1 bench hotkey sequence `N` then `Y` within 5 seconds under confirmed silence.
- Consider reducing `CONFIG.SENSITIVITY` from 2.4 to ~1.5 to bring magnitudes closer to S2 range
- Accept as-is and proceed to Stage 8 commit

## What's done

1. All migration code changes in working tree:
   - `platformio.ini` (NEW) — pioarduino 54.03.20, arduino-esp32 3.2.0, FastLED 3.10.3, board=esp32-s3-devkitc1-n16r8, partition default_16MB.csv
   - `SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h` — i2s_std migration, hand-built slot_cfg (School A + LEFT-mask flip), traceability comments
   - `SPECTRASYNQ_K1_FIRMWARE/globals.h` — DRAM_ATTR on `i2s_samples_raw`
   - `SPECTRASYNQ_K1_FIRMWARE/strings.h` — `#pragma once`, PASS→SB_PASS, FAIL→SB_FAIL
   - `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h`, `serial_menu.h`, `bridge_fs.h` — PASS/FAIL token renames
2. `.claude/CLAUDE.md` — added "Calibration command policy" (start_noise_cal must wait for Captain-confirmed silence)
3. `docs/forensics/2026-05-24-doctrine-gate-pio-migration.md` — doctrine gate output (created earlier)
4. `docs/forensics/2026-05-24-codex-review-checkpoint-1.md` — Codex review package (created earlier)
5. **TEMP DIAGNOSTIC blocks STRIPPED** from i2s_audio.h. Compile clean: 552622 B flash, 83024 B RAM.
6. Stage 0 WIP commit `93052a9` already on `feat/pio-core-bump` branch with rollback tag `pre-pio-migration-20260524-1320`.

## What's NOT done

1. **No consolidated commit yet.** Plan §8 S8 commit is queued but not executed. Per CLAUDE.md "NEVER commit changes unless the user explicitly asks". Captain confirmed acceptance verbally but hasn't said "commit".
2. **`audio_transfer.h:1`** still `#include <driver/i2s.h>` (legacy header). It's a DEAD file (not in .ino include list). Captain's earlier guidance: leave as dormant G-01 item for §12. Verified at Stage 5.
3. **`.gitignore`** does NOT include `.pio/` or `*.ino.cpp`. Minor hygiene fix queued for cleanup.
4. **Auto-memory tombstones**: `project_sb_esp32_core_pin.md` says "must build against esp32:esp32@2.0.9" — false post-migration. Need to update or delete.
5. **K1 operating-point investigation** (see comparison table above) — Captain may want to investigate before locking commit, or accept as-is.

## Recovery commands for the next session

```bash
# Working tree (uncommitted)
cd "/Users/spectrasynq/SensoryBridge-main 9"
git status                       # see modified files + staged FastLED renames (668)
git diff --stat                  # see line-level changes

# Branch + rollback tag
git branch --show-current        # feat/pio-core-bump
cat /tmp/rollback_tag.txt        # 93052a9c6522de8f3712233b320fba8b09ec5be7
                                 # tag: pre-pio-migration-20260524-1320

# Build state
pio run -e k1_hardware           # should succeed, 552622 B flash, 83024 B RAM, 1 warning (system.h:48 [-Wvolatile] — out of scope)
ls -la .pio/build/k1_hardware/firmware.bin   # 553024 B signed esp32s3 image

# Serial commands (Captain has direct access authorised this session)
# Typed serial commands now require ':' command mode. Without ':' the serial
# surface is hotkey-first and will not enter parse_command().
# - `:debug=true` / `:debug=false` — toggle [RAWR] stream (NOTE: [RAWR] block was stripped; debug now only triggers the legacy DEBUG print)
# - `:ap_stream=on` / `:ap_stream=off` — toggle [AP] stream  (always available, gated by AP_STREAM_ENABLED)
# - `:start_noise_cal` — ONLY during Captain-confirmed silence per calibration policy
# - `:dump` — dump CONFIG + state
# - `N` then `Y` within 5 seconds — K1 bench hotkey path for noise calibration; `N` only arms, `Y` confirms while armed

# Upload sequence (no erase needed for in-place updates)
pio run -e k1_hardware -t upload         # uses platformio.ini's upload_port=/dev/tty.usbmodem1101

# Upload with erase (full LittleFS wipe — partition transition only)
pio run -e k1_hardware -t erase
pio run -e k1_hardware -t upload

# DO NOT touch /dev/tty.usbmodem02 (S2 PROTECTED)
```

## Proposed Stage 8 commit (when Captain authorises)

```bash
cd "/Users/spectrasynq/SensoryBridge-main 9"
git add platformio.ini
git add SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h
git add SPECTRASYNQ_K1_FIRMWARE/globals.h
git add SPECTRASYNQ_K1_FIRMWARE/strings.h
git add SPECTRASYNQ_K1_FIRMWARE/led_utilities.h
git add SPECTRASYNQ_K1_FIRMWARE/serial_menu.h
git add SPECTRASYNQ_K1_FIRMWARE/bridge_fs.h
git add .claude/CLAUDE.md
git add docs/forensics/2026-05-24-doctrine-gate-pio-migration.md
git add docs/forensics/2026-05-24-codex-review-checkpoint-1.md
git add docs/forensics/2026-05-24-stage7-handoff.md
# FastLED renames already staged from Stage 1

git status --short               # verify

git commit -m "$(cat <<'EOF'
feat(build): migrate K1 to PlatformIO + arduino-esp32 3.2.0 + FastLED 3.10.3

- Add platformio.ini (pioarduino 54.03.20 = arduino-esp32 3.2.0 / IDF 5.4.1);
  retire tools/compile-k1-arduino.sh.
- Migrate i2s_audio.h to ESP-IDF 5.x i2s_std driver with hand-built slot_cfg
  (School A pattern from Lixie-Labs/Emotiscope with slot_mask=LEFT to
  compensate for IDF-5.1→5.4.1 slot-semantic inversion when ws_pol=true).
  Stage 7 confirmed audio response on K1 hardware.
- DRAM_ATTR on i2s_samples_raw (BT-04).
- Rename PASS/FAIL → SB_PASS/SB_FAIL across strings.h, led_utilities.h,
  serial_menu.h, bridge_fs.h, i2s_audio.h to resolve collision with
  arduino-esp32 3.x rom/ets_sys.h STATUS enum.
- Add #pragma once to strings.h.
- Replace vendored FastLED 3.9.16 with lib_deps fastled/FastLED@3.10.3 (RMT5).
- Flash 8M→16M (N16R8); partitions min_spiffs → default_16MB.csv.
- Add Calibration command policy to .claude/CLAUDE.md (start_noise_cal must
  wait for Captain-confirmed silence).

Scope: build tooling + I2S driver. No DSP / visual / sample-rate change.
Plan: docs/agent-outputs/analysis/2026-05-24-pio-core-bump-scoping/MIGRATION_PLAN-v2-rebaselined.md
Doctrine gate: docs/forensics/2026-05-24-doctrine-gate-pio-migration.md
Handoff: docs/forensics/2026-05-24-stage7-handoff.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

## Open follow-ups (post-commit)

1. **K1 operating point**: SSL=6092 vs S2's 369 is striking. Worth investigating whether a deeper silence cal or SENSITIVITY tweak brings it closer. Not blocking acceptance.
2. **`audio_transfer.h` cleanup**: dead file with legacy I2S include. Move to `tools/legacy/` or delete entirely. Captain-decided.
3. **`.gitignore` hygiene**: add `.pio/` and `*.ino.cpp`.
4. **Auto-memory tombstones**: `project_sb_esp32_core_pin.md` is now false.
5. **i2s_std bit-position discovery as a knowledge doc**: write up the IDF-5.1→5.4.1 slot-semantic inversion finding for future SPH0645/S3 work.
6. **Stage 6 erase + Stage 7 re-cal protocol**: document the calibration workflow (Captain pauses music → erase → upload → boot-cal under silence → start_noise_cal → resume music) as the canonical Stage 7 procedure.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-24 | agent:claude-opus-4-7 | Created at end of Stage 7 / mid Stage 8. K1 functional; commit not yet authorised. Captures full fix rationale, K1 vs S2 comparison, recovery commands, proposed Stage 8 commit. |
