# Lane 10 — [AP] serial print path verification

Date: 2026-05-23
Lane: 10 of 10 (SSA AP-1 root cause)
Scope: READ-ONLY trace of the `[AP]` serial telemetry emission path. Goal:
prove (or disprove) that the values Captain sees over USB match the actual
in-memory state of the AP pipeline.

## Print emission site

| File:Line | Function | Print statement |
|-----------|----------|-----------------|
| `SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h:324-326` | `acquire_sample_chunk()` (chunk loop, tail) | `USBSerial.printf("[AP] SSL=%u DC=%d max_raw=%.0f follower=%.0f peak_scaled=%.3f silent_scale=%.3f silence=%d\n", CONFIG.SWEET_SPOT_MIN_LEVEL, (int)CONFIG.DC_OFFSET, (float)max_waveform_val_raw, (float)max_waveform_val_follower, (float)waveform_peak_scaled, (float)silent_scale, silence ? 1 : 0);` |

Single emission site. No second `[AP]` printer anywhere in the firmware.

## Field-by-field source verification

| Field | Source variable | Declared type | Decl. site | Format spec | Cast/transform in print | Verified accurate? |
|-------|-----------------|--------------|------------|-------------|--------------------------|--------------------|
| `SSL`         | `CONFIG.SWEET_SPOT_MIN_LEVEL`     | `uint32_t`              | `globals.h:37` (in `conf` struct) | `%u` | none (passed as-is)                  | YES — matches type/spec |
| `DC`          | `CONFIG.DC_OFFSET`                | `int32_t`               | `globals.h:39`                    | `%d` | explicit `(int)` (no-op on ESP32-S3 where `int == int32_t`) | YES — matches type/spec |
| `max_raw`     | `max_waveform_val_raw`            | `float`                 | `globals.h:192`                   | `%.0f`| explicit `(float)` (no-op)           | YES — already float |
| `follower`    | `max_waveform_val_follower`       | `float`                 | `globals.h:194`                   | `%.0f`| explicit `(float)` (no-op)           | YES — already float |
| `peak_scaled` | `waveform_peak_scaled`            | `float`                 | `globals.h:195`                   | `%.3f`| explicit `(float)` (no-op)           | YES — already float |
| `silent_scale`| `silent_scale`                    | `float`                 | `globals.h:198`                   | `%.3f`| explicit `(float)` (no-op)           | YES — already float |
| `silence`     | `silence`                         | `bool`                  | `globals.h:197`                   | `%d`  | `silence ? 1 : 0` (explicit promotion to int) | YES — defensive, correct |

All seven fields use either a native-typed pass (`uint32_t`/`%u`,
`int32_t`/`%d`) or a no-op explicit cast onto an already-matching format.
There is **no SQ15x16 → printf path** in this statement. (`max_waveform_val_raw`
et al. were converted to plain `float` in an earlier refactor; see
`globals.h:192-198`.) `int32_t → int` is well-defined on the S3 toolchain
where `sizeof(int) == sizeof(int32_t) == 4`.

## Emission gating / frequency

`i2s_audio.h:322-328`:

```
static uint32_t last_ap_dbg = 0;
if (AP_STREAM_ENABLED && millis() - last_ap_dbg > 1000) {
  USBSerial.printf("[AP] ...", ...);
  last_ap_dbg = millis();
}
```

- Gating flag: `AP_STREAM_ENABLED` (`globals.h:330`, `bool AP_STREAM_ENABLED = true;`).
- Cadence: ≥ 1 s between emissions (1 Hz max).
- Position: end of `acquire_sample_chunk()`, AFTER all chunk math
  (`waveform[i] = sample - CONFIG.DC_OFFSET`, max-tracking, smoothing,
  follower update, `silent_scale` update). Values are **NOT stale**: they
  are the freshly-computed values for the current chunk. No frame counter
  or modulo; the only filter is the wall-clock 1 Hz throttle.
- `last_ap_dbg` is a function-local `static uint32_t` — survives across
  calls but is private to this function; cannot be raced by other tasks.

There is one prior `[AP]` observation (claude-mem #53705) noting the gate.
That gate is a **publication** gate, not a **value** gate — the printed
fields are not buffered or sampled; they read live state at print time.

## Cast/transform anomalies

None of the casts on the print line introduce any value mutation:

1. `(int)CONFIG.DC_OFFSET`: `int32_t → int`. On `xtensa-esp32s3-elf` and
   `xtensa-esp32s2-elf` `int` is 32-bit two's-complement, so this is a
   pure type alias.
2. `(float)max_waveform_val_raw` etc.: `float → float` — pure pass-through.
3. `silence ? 1 : 0`: bool flattened to `int`. Always 0 or 1. Cannot
   produce any "fake silence" value.
4. `%u` on `SWEET_SPOT_MIN_LEVEL`: matches `uint32_t`. Cannot underflow into
   negative display.

The DC progression Captain observed (`+8304 → 0 → −32767`) is **NOT** a
print artifact. It traces directly to legitimate writes to
`CONFIG.DC_OFFSET`:

- `+8304`: boot-default stamp at `system.h:359-363` when persisted
  `DC_OFFSET == 0`.
- `0`: noise-cal Phase A in `i2s_audio.h:125-129`. Note: `dc_offset_sum`
  is `int32_t` (`globals.h:196`). When Captain forces a re-cal, line 128
  overwrites `CONFIG.DC_OFFSET = dc_offset_sum / 128` mid-cal. **However**,
  `dc_offset_sum` is NEVER reset to 0 at the start of a new cal in the
  code I traced — see Open Questions. If a re-cal begins with a stale
  sum, the divided value can be anywhere on the `int32_t` line.
- `−32767`: legitimate signed-`int32_t` value being printed correctly.
  This is the actual value sitting in `CONFIG.DC_OFFSET`, not a display
  glitch. The downstream `waveform[i] = sample - CONFIG.DC_OFFSET` will
  then add `+32767` to every sample, blowing the AC envelope into the
  positive ceiling clamp — but that is a **pipeline bug**, not a
  **print** bug.

In particular, `−32767` is not the bit-pattern artifact for any plausible
`uint16_t` (32769 as int16_t prints as `−32767`, but `CONFIG.DC_OFFSET`
is `int32_t` and `int32_t 32769` formats correctly as `32769` under `%d`).
Captain is seeing the real value.

## S2 cross-check

Captain S2 trace: `DC=-8102 max_raw=2280 peak_scaled=0.684`.

- `DC = −8102`: plausible (within `(int)dc_offset_sum/128` range for a
  unit whose MEMS bias settles negative — the Captain MEMS bias is
  documented negative in `~/.../memory/MEMORY.md:project_sb_audio_pipeline_debug_2026-05-20`,
  `~−8767`).
- `max_raw = 2280`, `peak_scaled = 0.684`: format specs match types; no
  signed/unsigned divergence.

Print path is **identical** between S2 and S3/K1 builds (same source file,
no `#ifdef` around the printf). No K1-specific print divergence exists.

## Verdict: are displayed values trustworthy?

**YES.** The `[AP]` stream is value-faithful. Every field is read directly
from its canonical in-memory storage at print time, formatted with a
matching specifier, and emitted at most 1 Hz from the end of
`acquire_sample_chunk()`. No fixed-point conversions, no buffering, no
stale-frame risk, no sign-bit mangling, no S2-vs-S3 print divergence.

If Captain sees `DC=−32767`, then `CONFIG.DC_OFFSET == −32767` literally.
If Captain sees `peak_scaled=0.000`, then `waveform_peak_scaled` is below
0.0005 in actual float storage. The diagnostic stream can be relied on as
evidence for AP-1.

## Hypothesis ranking (what AP-1 should attack next)

Given the print path is clean, the K1 AP-1 symptoms are real signal-domain
events that other lanes must localise:

1. **HIGH — `dc_offset_sum` is never reset to 0 at the start of a noise
   cal.** Declaration at `globals.h:196` initialises it once at boot, but
   I see no `dc_offset_sum = 0;` anywhere on a re-cal path (verify in
   Lane-2 / `system.h` `init_noise_cal()` or equivalent). If a second
   noise cal runs without resetting the accumulator, Phase A produces a
   garbage `DC_OFFSET` (`old_sum + 128 fresh waveform[0]s) / 128`),
   easily landing at extreme negative values like `−32767`.
2. **MEDIUM — Saved-config corruption.** `save_config()` at boot
   (`system.h:362`) and elsewhere can persist a bad `DC_OFFSET` that the
   "is 0?" rescue in `system.h:359` does not catch (it only fires on the
   exact zero sentinel; `−32767` is not zero, so it survives).
3. **LOW — S2-vs-K1 sample chain divergence.** The print path is unified;
   any difference is upstream in `(raw * 0.000512) + 56000 - 5120` (line
   66) interacting with K1-specific MEMS bias / I²S timing — a Lane-2 /
   Lane-3 concern, not a print concern.

## Open questions for adjacent lanes

- **Lane 2** (`i2s_audio.h`): confirm whether `dc_offset_sum` is reset
  before each noise-cal entry. The only assignment I found in this lane
  is the accumulation (`+=`) at line 126; the only initialisation is
  the file-static at `globals.h:196`. If no reset exists, that is the
  AP-1 root cause and explains the `0 → −32767` jump.
- **Lane equivalent for `system.h`**: confirm `save_config()` is not
  called mid-cal with the provisional Phase-A `DC_OFFSET` snapshot.
- **Lane equivalent for `serial_menu.h`**: `serial_menu.h:188-189`
  prints `CONFIG.DC_OFFSET` separately via `USBSerial.print(int32_t)` —
  also clean, no transform.

## Files referenced (absolute)

- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h:322-328` — print site
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h:125-129` — `dc_offset_sum` accumulate + Phase-A stamp
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h:65-91` — sample chain producing `waveform[i]` and `max_waveform_val_raw`
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/globals.h:37-39` — `SWEET_SPOT_MIN_LEVEL`, `DC_OFFSET` types
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/globals.h:192-198` — float AP fields, `silence`, `silent_scale`
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/globals.h:196` — `int32_t dc_offset_sum = 0;` (one-time init)
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/globals.h:330` — `AP_STREAM_ENABLED = true`
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/system.h:354-363` — boot `DC_OFFSET = 8304` rescue
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/system.h:369-379` — SSL sanity reset (does not touch `DC_OFFSET`)
