# Lane 5 — CONFIG.DC_OFFSET complete reference trace

SSA AP-1 root cause investigation. Repo: `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/`.
FIRMWARE_VERSION = 40102 (post 2026-05-20 "single-domain noise_cal fix").
Captain's MEMS DC characterised as **negative** (~ -8767) in
`~/.claude/projects/-Users-spectrasynq-SensoryBridge-main-9/memory/MEMORY.md`.

Symbols traced:
- `CONFIG.DC_OFFSET` — the persisted, runtime-mutable field (`int32_t`, in `conf`).
- `dc_offset_sum` — global `int32_t` accumulator in `globals.h` line 196, used only by the cal pass.

No other aliases (`dc_offset`, `DCoffset`, `dcOffset` etc.) name an independent variable. The
only matches outside `CONFIG.DC_OFFSET` are comment text and the accumulator.

## All references (table)

| File:Line | R/W | Function | Value / Use | Trigger |
|-----------|-----|----------|-------------|---------|
| `globals.h:39` | DECL | (struct `conf`) | `int32_t DC_OFFSET;` field declaration | compile-time |
| `globals.h:85` | WRITE (default initialiser) | `CONFIG = {...}` global initialiser | literal `0` (zero sentinel = "uncalibrated") | static init, pre-`setup()` |
| `globals.h:112` | WRITE (default copy target) | `conf CONFIG_DEFAULTS;` (zero-init then overwritten in `init_system`) | `0` initially; rewritten by `memcpy(&CONFIG_DEFAULTS, &CONFIG, …)` inside `init_system` BEFORE any runtime mutation. So `CONFIG_DEFAULTS.DC_OFFSET == 0`. | static + `init_system` |
| `bridge_fs.h` `load_config()` | WRITE | `load_config()` (called from `init_fs()`) | Reads 512-byte LittleFS blob `/CONFIG_<FIRMWARE_VERSION>.BIN` into `CONFIG` via `memcpy(&CONFIG, config_buffer, sizeof(CONFIG))`. For FW 40102 the filename version-segregates from prior 4010x files, so a fresh-boot K1 on a brand-new firmware version reads NOTHING (file absent → returns early → `CONFIG.DC_OFFSET` stays at the static `0`). If a 40102 file IS present, whatever value was last persisted (including possibly `-32767`) is reloaded. | boot — `init_system` → `init_fs` → `load_config` |
| `system.h:359-363` | WRITE | `init_system()` boot-default guard | `if (CONFIG.DC_OFFSET == 0) { CONFIG.DC_OFFSET = 8304; save_config(); }`. Boot-default stamp. Only triggers on the exact `0` sentinel; any non-zero value (including `-32767`) survives. | every `setup()` after `init_fs()` |
| `noise_cal.h:7` | WRITE | `start_noise_cal()` | `CONFIG.DC_OFFSET = 0;` Resets to sentinel before Phase A accumulates. **Also resets `dc_offset_sum = 0;` (line 6) and `SWEET_SPOT_MIN_LEVEL = 0` (line 9).** | NOISE button press (≤250 ms tap), boot-mode magic, or `start_noise_cal` serial command → queued via `noise_transition_queued`, fired by `intro_animation`/`run_transition_fade` in `led_utilities.h:1190` |
| `i2s_audio.h:128` | WRITE | `acquire_sample_chunk()` Phase A→B handoff at `noise_iterations == 128` | `CONFIG.DC_OFFSET = dc_offset_sum / 128;` This is the **provisional stamp** of the mean of `waveform[0]` over iterations 0..127. Because Phase A runs with `CONFIG.DC_OFFSET == 0` and `waveform[i] = sample - 0`, `waveform[0]` equals the clamped raw `sample`. So this writes the mean of the clamped-sample stream. | mid-noise-cal, exactly one frame per cal |
| `serial_menu.h:188-189` | READ | `bridge_impulse()` / settings dump (line 188 region) | `USBSerial.print("CONFIG.DC_OFFSET: "); USBSerial.println(CONFIG.DC_OFFSET);` — diagnostic print of current value | `dump` / `bridge_impulse` serial command |
| `i2s_audio.h:77` | READ | `acquire_sample_chunk()` per-sample loop | `waveform[i] = sample - CONFIG.DC_OFFSET;` Subtracts DC bias from every clamped sample (CONFIG.SAMPLES_PER_CHUNK times per frame) | every audio frame |
| `i2s_audio.h:325` | READ | `acquire_sample_chunk()` AP telemetry printf (gated by `AP_STREAM_ENABLED`, 1 Hz) | `(int)CONFIG.DC_OFFSET` — printed as `DC=%d` in the `[AP]` line | every ~1 s when telemetry enabled |
| `audio_transfer.h:220` | READ | `acquire_data_chunk()` (the FSK-bridge / data-tone capture path) | `waveform[i] = sample - CONFIG.DC_OFFSET;` Same DC-bias subtraction used by the data-transfer pipeline | only when data acquisition runs (separate from main `acquire_sample_chunk`) |

## Writes by category

### Boot-time defaults

- **`globals.h:85`** — Static C++ initialiser. `DC_OFFSET = 0` is the "uncalibrated" sentinel.
  Runs before `setup()`. Always sets `0`. `CONFIG_DEFAULTS` snapshot in `init_system`
  therefore captures `0` as the canonical "default" too (so a future "restore one field
  from defaults" path would re-zero it — but no such path exists for DC_OFFSET).
- **`system.h:359-363`** — `init_system()` boot guard. Only fires on exact `== 0` sentinel.
  Writes `8304` (Captain's earlier-characterised positive bias for SPH0645 K1 units) and
  immediately `save_config()`. **Critically: this guard does NOT detect `-32767`** —
  any non-zero corrupt value passes through unchanged.

### Cal-time writes

- **`noise_cal.h:7`** — `start_noise_cal()` resets `CONFIG.DC_OFFSET = 0` (intentional —
  Phase A in `i2s_audio.h` requires `0` so `waveform[i] = sample - 0` accumulates the
  raw DC bias into `dc_offset_sum`).
- **`i2s_audio.h:128`** — `acquire_sample_chunk()` at `noise_iterations == 128`:
  `CONFIG.DC_OFFSET = dc_offset_sum / 128;`
  Provisional stamp from Phase A mean of `waveform[0]`.
  **Never persisted by this line itself.** Persistence happens at `GDFT.h:166`
  (`save_config()` inside the `noise_iterations >= 256` completion block).

### LittleFS load

- **`bridge_fs.h` `load_config()`** — `memcpy(&CONFIG, config_buffer, sizeof(CONFIG))`
  overwrites `DC_OFFSET` from persisted bytes if the version-stamped config file exists.
  Filename is `update_config_filename(FIRMWARE_VERSION)`; FW 40102 expects
  `/CONFIG_40102.BIN`. **Whatever value was persisted by the last successful
  `save_config()` is restored verbatim — including the pathological `-32767`.**
- `save_config()` itself (called from `init_system`'s boot-default branch and from
  `GDFT.h:166` cal-completion) writes the current in-memory `CONFIG.DC_OFFSET`
  unmodified.

### Serial command writes

- **None.** There is no `dc=…` serial setter, no `dc_offset=…` path, no field assignment
  in `serial_menu.h` that targets `CONFIG.DC_OFFSET`. Only the read at line 188-189
  and the indirect triggers (`start_noise_cal` line 658, `clear_noise_cal` line 666,
  `factory_reset`/`restore_defaults` lines 624/632) exist.

### Sanity-clamp writes

- **None for `DC_OFFSET`.** The sanity clamp at `system.h:369-387` covers
  `SWEET_SPOT_MIN_LEVEL` (threshold 3000), `STANDBY_DIMMING`, and `noise_samples[]` —
  but **not** `DC_OFFSET`. The only guard on `DC_OFFSET` is the `== 0` sentinel check
  (line 359), which does not detect `-32767` or any other out-of-range value.

## Fresh-boot K1 lifecycle (timeline)

Assumed sequence for a K1 with FW 40102 freshly flashed (no `/CONFIG_40102.BIN` yet,
no `/noise_cal.bin`), Captain's negative-DC MEMS.

| Step | Site | DC_OFFSET state | Notes |
|------|------|-----------------|-------|
| 1. Pre-`setup()` static init | `globals.h:85` | `0` | C++ static initialiser. |
| 2. `setup()` → `init_system()` early | `system.h init_system` | `0` | Hardware/pin/USB init. |
| 3. `memcpy(&CONFIG_DEFAULTS, &CONFIG, …)` | `system.h:` (just after mode names) | still `0`; `CONFIG_DEFAULTS.DC_OFFSET = 0` | Defaults snapshot. |
| 4. `init_fs()` → `LittleFS.begin(true)` + `load_ambient_noise_calibration()` + `load_config()` | `bridge_fs.h init_fs` | `0` (file absent on fresh flash) | If file IS present, value restored verbatim — see "smoking gun" below. |
| 5. Boot-default guard `if (CONFIG.DC_OFFSET == 0)` | `system.h:359-363` | `0` → **`8304`**; `save_config()` flushes `/CONFIG_40102.BIN` with DC_OFFSET=8304 | This is the value Captain observes pre-cal. |
| 6. SSL sanity clamp / NOISE+MODE held check | `system.h:369-394` | unchanged | Does not touch DC_OFFSET. |
| 7. `init_leds()` etc. | — | unchanged | — |
| 8. `setup()` returns; `loop()` runs | — | `8304` | WAVEFORM pipeline works on this DC value. |
| 9. `intro_animation()` (called inside `init_system` at `system.h:417`) | `led_utilities.h:1058` | `8304` | Visual boot animation. Does NOT touch DC_OFFSET. (However the noise-transition consumer at `led_utilities.h:1184-1190` lives inside `run_transition_fade()`, which only runs if `noise_transition_queued == true`. On a clean boot this is false.) |
| 10. Captain triggers noise cal (NOISE button tap ≤250 ms, or boot-mode magic, or `start_noise_cal` serial cmd) → `noise_transition_queued = true` → next `run_transition_fade()` calls `start_noise_cal()` | `noise_cal.h:1-17` | `8304` → **`0`** (line 7) | `dc_offset_sum = 0`, `noise_iterations = 0`, `SWEET_SPOT_MIN_LEVEL = 0`, `noise_complete = false`. |
| 11. Phase A: `noise_iterations = 0..127` | `i2s_audio.h:125-126` | `0` (unchanged) | Each frame: `dc_offset_sum += waveform[0]` where `waveform[0] = sample - 0 = clamped_sample`. |
| 12. `noise_iterations == 128`: provisional stamp | `i2s_audio.h:127-128` | **`dc_offset_sum / 128`** | THIS IS THE SMOKING GUN. With Captain's negative MEMS, the clamped-sample stream skews so negative that the mean lands at or near `-32767`. |
| 13. Phase B: `noise_iterations = 129..240`: SSL accumulator | `i2s_audio.h:130-136` | `-32767` (post-Phase-A stamp, unchanged here) | `waveform[i] = sample - (-32767) = sample + 32767`. Every frame's `waveform[i]` is now hugely positive (or saturating into upper rail of the `short` storage). `max_waveform_val_raw` becomes enormous. `SWEET_SPOT_MIN_LEVEL = max_waveform_val_raw * 1.10` inflates correspondingly. |
| 14. `noise_iterations == 256`: cal complete | `GDFT.h:144-167` | unchanged `-32767` | `noise_complete = true`. `save_ambient_noise_calibration()`. **`save_config()`** ← persists DC_OFFSET=-32767 to `/CONFIG_40102.BIN`. |
| 15. Steady state main loop | `i2s_audio.h:65-91` per frame | `-32767` | `waveform[i] = sample - (-32767) = sample + 32767` is wildly wrong; downstream `max_waveform_val_raw`, follower, `waveform_peak_scaled`, SSL all polluted. |
| 16. Next reboot | `bridge_fs.h load_config` | `-32767` reloaded from LittleFS | Boot-default guard `== 0` does not fire (value is `-32767`, not `0`). System stays broken across reboots. |

Note re step 9 vs step 10: `intro_animation()` is invoked inside `init_system` at
`system.h:417`. The `noise_transition_queued` consumer (which calls `start_noise_cal`)
is in `run_transition_fade()` (`led_utilities.h:1184-1190`), which itself is invoked
from the LED thread main loop (`SPECTRASYNQ_K1_FIRMWARE.ino:528` shows
`if (mode_transition_queued == true || noise_transition_queued == true)
run_transition_fade();`). So `start_noise_cal()` does NOT auto-fire on a clean boot
unless Captain or the boot-mode magic explicitly queues it.

## The -32767 write site (smoking gun)

**File: `SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h:127-128`**

```c
} else if (noise_iterations == 128) {
  CONFIG.DC_OFFSET = dc_offset_sum / 128;  // provisional stamp; locked from here
}
```

### Why it produces -32767 on Captain's K1

Within the per-sample loop at `i2s_audio.h:65-77` (Phase A, `CONFIG.DC_OFFSET == 0`):

```c
for (uint16_t i = 0; i < CONFIG.SAMPLES_PER_CHUNK; i++) {
  int32_t sample = (i2s_samples_raw[i] * 0.000512) + 56000 - 5120;  // (1)
  sample = sample >> 2;                                              // (2)
  sample *= CONFIG.SENSITIVITY;                                      // (3)
  if (sample > 32767)   sample = 32767;                              // (4) clamp
  else if (sample < -32767) sample = -32767;                         // (5) clamp
  waveform[i] = sample - CONFIG.DC_OFFSET;                           // (6) DC_OFFSET = 0 in Phase A
  …
}
```

Then at `noise_iterations < 128` (line 126):
```c
dc_offset_sum += waveform[0];   // accumulating CLAMPED samples (because DC_OFFSET=0)
```

Captain's MEMS is documented as DC-negative (~ -8767 in the legacy / pre-FW-40102
characterisation — see `MEMORY.md`). The chain above is sensitive to the raw I2S
bias in two compounding ways:

1. Step (1) adds `+50880` after the `*0.000512` scaling. On Captain's K1, that
   intercept does not compensate the raw MEMS bias enough — the result already enters
   step (2) as a large-magnitude negative number.
2. Step (3) multiplies by `CONFIG.SENSITIVITY` (default `2.4`). This magnifies a
   pre-existing negative bias well below `-32767`.
3. Step (5) saturates at `-32767`. Every sample in the chunk pins at the negative rail.
4. Step (6) is the no-op `- 0`, so `waveform[i]` is itself the saturated `-32767`.
5. Phase A accumulates 128 frames of `waveform[0] == -32767`, giving
   `dc_offset_sum == -32767 * 128 == -4194176`.
6. Provisional stamp at line 128: `dc_offset_sum / 128 == -32767`.

**Locking conditions for the bug:**

- Captain's MEMS produces a sample stream that, after the linear bias chain and the
  `SENSITIVITY` multiply, saturates against the **`-32767` floor** in step (5) of
  `acquire_sample_chunk()`.
- Because `CONFIG.DC_OFFSET == 0` during Phase A, `waveform[i]` IS the saturated
  `-32767`, not the post-DC-corrected AC sample.
- The arithmetic mean of a constant-`-32767` stream IS `-32767`.
- There is no sanity clamp on `CONFIG.DC_OFFSET` anywhere — only the `== 0` sentinel
  check at boot, which does not catch this corrupt value.
- `save_config()` at `GDFT.h:166` persists the corrupt value to LittleFS; the boot
  guard then misses it forever because the persisted file is non-zero on every
  subsequent boot.

## Reads that observe -32767

Once `CONFIG.DC_OFFSET == -32767` (steady state post-bad-cal, and across reboots):

1. **`i2s_audio.h:77`** (`acquire_sample_chunk`) — every sample of every audio frame:
   `waveform[i] = sample - (-32767) = sample + 32767`.
   - `sample` is the clamped `[-32767, +32767]` value from step (5).
   - `waveform[i]` is therefore in `[0, 65534]` — outside the `short` storage range
     (`waveform[]` is `short` per `globals.h:188`). The implicit narrowing conversion
     from `int32_t` to `short` produces signed overflow (implementation-defined behaviour;
     on ESP32-S2/S3 GCC this typically wraps modulo `2^16`, so positive results above
     32767 wrap into negative shorts). End result: `waveform[]` becomes a
     wraparound-corrupted stream that is neither AC-meaningful nor DC-meaningful.
2. **`i2s_audio.h:88-90`** — `max_waveform_val_raw = abs(waveform[i])` operates on
   the corrupted stream → garbage value (likely pinned near 32767 by absolute-value
   of wrapped negatives).
3. **`i2s_audio.h:148`** — `max_waveform_val = max_waveform_val_raw - SWEET_SPOT_MIN_LEVEL`,
   `i2s_audio.h:150-161` follower math, `i2s_audio.h:163-169` `waveform_peak_scaled` —
   all downstream from the corrupted `max_waveform_val_raw`.
4. **`i2s_audio.h:325`** — `[AP]` telemetry prints `DC=-32767` (this is exactly the
   value Captain observed post-cal in the AP log).
5. **`audio_transfer.h:220`** — `acquire_data_chunk()` does the same subtraction:
   `waveform[i] = sample - CONFIG.DC_OFFSET`; same wrap-around corruption when that
   path runs.
6. **`serial_menu.h:189`** — diagnostic dump prints `-32767` when Captain inspects.

The AP log signature `DC=-32767` reading on the gated 1 Hz `[AP]` line at
`i2s_audio.h:323-328` is therefore the direct, observable surface of the bug.

## Hypothesis ranking

1. **PRIMARY (high confidence): Negative-rail saturation in `acquire_sample_chunk`
   Phase A.** The clamp at `i2s_audio.h:73-75` pins every Phase A sample at `-32767`
   on Captain's K1 because the bias chain at lines 66-69 produces a strongly negative
   intermediate. With `CONFIG.DC_OFFSET == 0` during Phase A, `waveform[i] = sample`,
   so the accumulator integrates `-32767 * 128`. The provisional stamp at line 128
   writes `-32767`. This perfectly explains the observed `DC=-32767` post-cal
   telemetry and matches the "negative MEMS DC ~ -8767" hardware fact (after `*2.4`
   sensitivity the operating point is well below the `-32767` floor).
2. **SECONDARY (medium): Persisted `-32767` survives reboots via `load_config()`
   because the only DC_OFFSET guard is `== 0` at `system.h:359`.** Confirmed by
   trace — there is no sanity clamp on DC_OFFSET anywhere.
3. **TERTIARY (low, not consistent with evidence): MEMS gain or hardware fault
   producing rail-pinned input.** Possible, but unnecessary to explain the
   observation — the existing linear chain plus 2.4× sensitivity is enough to
   saturate the floor for a -8767-mean MEMS.
4. **NOT THE CAUSE: serial `dc=` command corruption.** No such command exists.
5. **NOT THE CAUSE: `restore_defaults()` zeroing it incorrectly.** `restore_defaults`
   deletes the config file and reboots; the boot-default guard then stamps `8304`.
   That path is healthy.
6. **NOT THE CAUSE: `CONFIG_DEFAULTS` snapshot timing.** Captured at `init_system`
   right after struct setup but before `init_fs()`, so it always holds the static
   `0`. No field-level revert path uses it for DC_OFFSET.

## Open questions

1. What is Captain's exact pre-clamp `sample` value in Phase A (before line 73 clamps
   to `-32767`)? Needs serial-stream `audio=` dump or a temporary unclamped print at
   `i2s_audio.h:70` to confirm the floor-saturation hypothesis directly, vs. the bias
   chain hitting the rail only sometimes.
2. Why was Captain's prior "8304" working baseline correct, given the same hardware?
   - Hypothesis: `CONFIG.SENSITIVITY` was lower (e.g., 1.0 vs. the default 2.4),
     keeping the chain in-range so Phase A produced an actual mean instead of a rail
     saturation.
   - Hypothesis: a prior firmware version's bias chain had different constants
     (the `+ 56000 - 5120 = +50880` intercept on line 66 is suspicious — verify against
     pre-K1 SB / LightwaveOS upstream).
3. Should the Phase-A accumulation use the **pre-clamp `sample`** value, not
   `waveform[0]`? Currently `dc_offset_sum += waveform[0]` (line 126) — but
   `waveform[0]` lost information at the clamp step. Accumulating pre-clamp would
   make the mean honest for high-bias hardware (at the cost of needing a wider
   accumulator type, which `int32_t` already is — no widening required for 128 ×
   30-bit samples).
4. Does `noise_cal.h:7` (`CONFIG.DC_OFFSET = 0` at cal start) need to instead seed
   from the existing 8304 default, then do iterative refinement? Current design
   relies on Phase A seeing the raw bias, which is exactly what fails for Captain.
5. Should there be a post-cal sanity clamp at `i2s_audio.h:129` rejecting any value
   outside, say, `[-16000, +16000]` and falling back to `8304` with a warning?
6. Is `CONFIG.DC_OFFSET` declared `int32_t` (per `globals.h:39`) but practically
   constrained to fit the AC-domain waveform math (which uses `short`)? Yes —
   the static initialiser is `0`, the boot default is `8304`, both well within
   `int16_t`. Treating DC_OFFSET as bounded `[-32767, +32767]` for sanity-clamp
   purposes is safe.
