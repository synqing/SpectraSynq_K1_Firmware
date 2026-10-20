---
abstract: "Maintained contract for the K1 ESP32-S3 emulator replay (R3, 20 October 2026): PCM through the real k1_main_rpl_im69d processing path, paired A/B native capture, production commands, saved composition and recovery, one acceptance function, one command. No hardware is touched."
---

# K1 ESP32-S3 emulator replay

One command runs the bounded suite against the current checkout and returns a
truthful result. It never flashes, resets or opens a board.

```bash
python3 tools/esp_emulator/run.py \
  --scenario tools/esp_emulator/s3_music_regression.json \
  --output _scratch/esp-emulator/<fresh-name>
```

`--suite` selects a suite declared in the scenario. The default is `default`.
The output directory must not exist yet. Exit status is 0 only when every
enabled software criterion passes. The final line is `SOFTWARE COMPLETE` or
`SOFTWARE INCOMPLETE`.

Outputs, all in the run-owned directory:

| File | What it is |
|---|---|
| `result.json` | The one canonical record. It holds source/dirty-input identity, builds and effective flags, tool lock, scenario hash, every case (requested vs observed, executed flash hashes, reasons), comparisons, planted negatives, the SW criteria matrix and labelled historical references. |
| `report.html` | Self-contained offline inspection report (`report.py`), built from `report-data.json`. |
| `<case>/uart.txt` | Raw firmware output, including the native A/B dump. |
| `<case>/flash-run.bin`, `scenario-blob.bin`, `emu-stderr.txt`, `exit_code.txt` | Exact executed input and process outcome. |
| `build-emu.log`, `build-product.log`, `host-pytest.log` | Build and host-check logs. |

## Tool resolution

`tool-lock.json` pins `esp-emu 0.49.0` for `aarch64-apple-darwin` by executable
SHA-256. `run.py` tries `$K1_ESP_EMU`, then `tools/esp_emulator/esp-emu.local.json`
(machine-local, git-ignored, `{"executable": "<path>"}`), then `esp-emu` on
`PATH`. It accepts the first candidate whose SHA-256 matches the lock and records
the rejected ones. It never downloads or installs anything. PlatformIO
(`pio`) builds both envs. `xtensa-esp32s3-elf-nm` comes from
`$PLATFORMIO_CORE_DIR` (default `~/.platformio`). `ffmpeg` is needed only for
`inventory_excerpt` assets. A missing converter or source file marks only the
dependent case `DEFERRED_EXTERNAL`.

There is no Linux lock. Do not reuse the Darwin hash. The official
`SHA256SUMS` beside the pinned archive lists the Linux archive checksums. A
Linux CI job needs that archive supplied through an authorised mechanism and
its own executable hash added to a separate lock.

## Product profile and trace boundary

- **Emulator env `k1_main_rpl_emu`.** This is `k1_main_rpl_im69d` plus exactly the
  declared adapters `K1_RENDER_TRACE_V1`, `K1_EMU_FIXTURE`, `K1_EMU_SKIP_EMIT`
  and `K1_EMU_UART0`, with `-include k1_emu_clock_force.h`. `run.py` verifies that
  set against `pio project config` on every invocation. The upload guard
  blocks the env (`scripts/platformio/k1_device_identities.json`).
- **PCM.** The fixture copies each hop into `im69d_samples_i16` in place of
  `i2s_channel_read`. The production gain, GDFT, DSP, publication, renderer and
  Lever-2 packing then run unchanged. I2S channel enable is skipped, because
  esp-emu never clears `I2S_RX_UPDATE`.
- **Native capture.** The dual-edge tap captures `ws2816_wire` (A) and
  `ws2816_wire_secondary` (B) after both Lever-2 packs, immediately before
  `FastLED.show()`. Submission is suppressed. Each logical pixel is 6 bytes,
  G16BE R16BE B16BE. The UART `rgb16hex` dump is the lossless R16 G16 B16
  reorder (`emu_capture.dump_hex_to_wire`). Both edges have 160 logical
  pixels. A and B are logical names only.
- **Limiter.** On Main RPL the Lever-2 pack budget is the identity
  (`n*3*65535`), and `init_leds()` returns before
  `FastLED.setMaxPowerInVoltsAndMilliamps()`. So the compiled
  `MAX_CURRENT_MA = 2500` installs no limit. The production `max_current_ma`
  command installs FastLED's single power limit over every registered
  controller, which couples both edges. Each captured frame records the scale
  FastLED's own `calculate_max_brightness_for_power_mW` gives for that
  submission (`limit_scale`, 255 = none) and the installed budget
  (`power_mw`). This is software arithmetic, not measured current.
- **Startup.** The product startup animation, the boot palette lock and the
  master-brightness fade are untouched. The only startup adapter replaces
  `FastLED.delay(2)` with `delay(2)` inside the animation, because submission
  is suppressed.

## Scenario blob (`emu_blob.py` ↔ `audio/k1_emu_fixture.cpp`)

The runner writes one blob into the unused `app1`/`ota_1` partition
(`0x650000`, 6.25 MB) of the run's own merged flash. The application image is
never patched, and every run records that `app0` equals the built
`firmware.bin`. The bootloader, partition table and app are placed exactly as
built, and `otadata` stays erased.

Header (256 bytes, little-endian): magic `K1EMUSC2`, version 2, `run_id[48]`,
`sample_rate`, `hop_samples`, `real_samples`, `pad_samples`,
`capture_start_hop`, `capture_end_hop` (exclusive), `capture_every`,
`flags` (bit0 recovery, bit1 boot-monotonic epoch, bit2 declared epoch),
`command_count`, `command_offset`, `pcm_offset`, `stall_ms`, `blob_bytes`,
`payload_crc32` (commands + PCM), `declared_epoch_us` (u64), reserved, and
`header_crc32`. Commands are 96 bytes each: `u32 hop`, `u32 0`, then
`text[88]`. The PCM is mono s16le, zero-padded inside the blob to a hop
boundary.

## Time and end of input

- **Hop-end clock.**
  `app_us = epoch_us + processed_samples * 1000000 / 12800`, with a 64-bit
  intermediate. One full hop advances exactly 7,500 µs. The fixture stages hop
  *h* at the top of `loop()`, so `t_now` and every `millis()`/`micros()` in
  firmware sources (forced include) read the end time of the hop being
  processed. AGC uses `k1_emu_fixture_app_us()`.
- **Epoch policies.**
  - `zero`: the clock is 0 until the first hop, and the first hop is 7,500 µs.
  - `boot_monotonic`: the clock follows the emulated monotonic timer from reset
    and hands off at the first hop.
  - `declared` (`us`): the same pre-audio clock, with the first hop placed at
    the declared application time. It must not be earlier than the boot time
    already observed.

  Every run prints `EMU_EPOCH policy= epoch_us= boot_us= pre_audio_shows=`.
  The short cases declare 1.0 s, the product's own fade gate. esp-emu boots
  in about 80 ms, and on a real board the gate has passed long before audio
  flows.
- **Coordinates.** A command at hop *h* runs through `parse_command()` (the
  production parser and owner) at replay sample `h*96`, before hop *h* is
  processed. Its first possible effect is generation `h+1`. Original-file
  positions are `excerpt.start_ms` plus the segment offset recorded in the
  case's `pcm` metadata. Declared padding is never counted as original audio.
- **Lockstep.** The producer waits until the render thread has shown each
  generation, so every hop is shown exactly once. This deterministic mode does
  not model hardware scheduling. The wait has a real-time deadline
  (`stall_ms`, default 20 s). A stall prints `EMU_END reason=stall` with the
  last admitted/processed/published/consumed/shown positions and dumps the
  partial capture.
- **End of input.** After the declared real hops plus `tail_hops` zero hops,
  and once the last publication has been shown, the fixture prints
  `EMU_END reason=eof`, dumps the trace and parks. There is no implicit tail.
  A final partial hop is rejected unless the case says
  `"partial_hop": "zero_pad"`, and then its real and padded samples are
  counted separately.

## Firmware lines

| Line | Meaning |
|---|---|
| `EMU_FIXTURE_ARMED run= source=blob valid= rate= hop= real_samples= pad_samples= total_hops= capture=a..b every= recovery= commands= payload_crc32= stall_ms= clock=hop_end_us epoch= mode=lockstep` | What the firmware actually read from flash. |
| `EMU_SS gen= when=boot\|cmd\|shown hop= hex=` | `k1_show_state_encode(k1_show_state_capture_live())`, i.e. every serialized field. Printed at boot (before any command), after each command, and on every shown change. |
| `EMU_EPOCH ...` | Clock hand-off. |
| `EMU_CMD hop= sample= text=` / `EMU_CMD_DONE hop= rejected= ...` | Scheduled production commands and their result. |
| `EMU_SAVE kind=config\|show ok= hop=` | A save reached LittleFS. |
| `EMU_REJECT <type>` | The production parser rejected a command. |
| `EMU_POWER_LIMIT installed_mw=` | A production site installed FastLED's power limit. |
| `EMU_END reason=eof\|stall\|... run= admitted= processed= staged_hops= total_hops= published= last_generation= consumed= shown= last_shown= pre_audio_shows= captured= commands= rejects= saves= unstaged_admits= publications_without_hop= app_us=` | Terminal event. |
| `[RTRACE-BEGIN frames= every=1 px=160 fmt=rgb16hex bpp=16 edges=2 crc32=]`, then `S,idx,generation,admitted,processed,app_us,limit_scale,power_mw` and `F,idx,ms,mode,A,B` | The native capture. The CRC is esp_crc32_le (= zlib.crc32) over the wire bytes of A then B for every frame. |

## Acceptance (`emu_capture.accept`)

One function serves every run, comparison and planted case. It rejects any of
the following:

- process exit ≠ 0, or the exit-on string not reported
- decode errors: duplicate keys, frames or sidecars; malformed hex; a missing
  channel
- a header other than px=160 bpp=16 edges=2 rgb16hex every=1
- a CRC mismatch
- a frame count that differs from the declared window and cadence (no fixed
  135)
- unordered frames, a missing or extra sidecar, or wrong per-frame
  generation/processed/admitted/app_us for its hop
- firmware run id, scenario CRC or window differing from the request
- a missing boot show-state
- epoch or counter mismatches (including unstaged admits and publications
  without a hop)
- commands not executed at their requested hop in order, or a rejection
  outcome different from the declared one
- a recovery run that issued commands or saves
- a failure end without positions

Run ids and wall-clock fields are never part of repeat equality
(`deterministic_view`).

## Scenario (`k1-emu-scenario/2`)

Unknown fields, duplicate JSON keys, unsupported command names, invalid
windows, an epoch without its value, a recovery case with commands, unknown
assets or cases, and a time contract other than 12,800 Hz / 96 / hop_end are
all rejected before anything is built.

- `assets`
  - `c_array_inc`: the compiled smoke PCM.
  - `inventory_excerpt`: a fixture id from
    `scripts/regression-harness/fixtures/k1_av_regression_fixtures.template.json`,
    with the source SHA-256, the excerpt, and an ffmpeg mono 12,800 Hz
    conversion with one uniform peak gain. The whole recipe and the ffmpeg
    version are recorded.
  - `concat`: hop-exact slices of other assets plus declared zero sections.

  Each asset declares `qualification`: `synthetic_diagnostic`, `real_music` or
  `diagnostic_composite`.
- `compositions`: lists of production command strings applied at hop 0.
- `cases`: `pcm`, `tail_hops`, `partial_hop`, `epoch`, `capture`
  `{start_hop, end_hop, every}`, `commands` `[{hop, text, expect}]`,
  `composition`, `flash` `{from: blank|<case>, recovery}`, `save_state`,
  `stall_ms`, and `expect` `{end_reason, saves}`. A recovery run starts from the
  source case's saved LittleFS region in a freshly merged flash, with zero
  commands.
- `comparisons`: `equal`, `isolation`, `limit_coupling`, `recovery_state`,
  `fallback_state`, `differs` and `case`, each mapped to an SW criterion.
- `planted.base_case`: the fresh capture that the planted negative cases
  mutate.

## Not covered (by design)

Microphone wiring, PDM/I2S/DMA/GPIO/RMT wire timing, hardware scheduling,
current draw, thermal and optical appearance, USB transport, and live
audiovisual quality. No software trace here proves any of them.

---

| Date | Author | Change |
|---|---|---|
| 2026-10-20 | agent:claude-code (R3 owner) | Replaced the R2 one-hop GDB contract with the PCM → production processing → paired-capture/control/persistence interface. |
