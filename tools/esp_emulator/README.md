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
- **Startup ordering.** The producer does not stage hop 0 until the render
  task has finished the product startup animation and entered its frame loop
  (`k1_emu_fixture_note_render_loop()`). Startup always runs entirely on the
  pre-audio clock, and the hand-off is deterministic (`pre_audio_shows=113`).
- **Render-loop application-time seam.** Under the fixture, `vp_frame_start_us`
  (the effects-queue tick and the beat-aware/smart director clocks), `LED_FPS`
  dt correction and the effect-context dt use the frame's application time.
  That time is sampled when the fixture accepts a new generation, while the
  producer is blocked. Perf counters keep the emulator timer. Without this
  seam, render output depended on emulation speed, which shifts with host
  load and diagnostic work.
- **Seeded randomness.** Under the fixture, `random_float()` (auto colour
  shift, quantum collapse) draws from xorshift32 seed `0x9E3779B9`
  (`rng=` in `EMU_FIXTURE_ARMED`, `rng_draws=` in `EMU_END`) instead of
  `esp_random()`. `esp_random()` XORs a timing-dependent number of RNG
  register reads.
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

## Client transport (existing client → emulated product)

A case with a `client` block is driven by the existing control client through
the product's own USBSerial and production receive loop (`check_serial` →
`parse_command`), instead of fixture-scheduled commands.

```
pio device monitor --baud 115200 --eol LF --raw --project-dir <run>/<case>/client-project --port <run-owned pty>
   ⇅ run-owned pty (emu_client.py; bytes forwarded unchanged)
esp-emu --console usb-jtag            (stdin/stdout = USB-Serial/JTAG EP1 = product USBSerial)
esp-emu --uart1-tcp 127.0.0.1:<port>  (fixture trace on UART1, read by the runner)
```

- **Client.** The scenario's top-level `client` names it. No dedicated scripted
  typed-command client exists in the repository; `pio device monitor` is the
  documented local client for `:` command lines. The runner supplies
  `--project-dir` (a run-owned empty directory) and `--port` (the pty it
  allocated); a scenario argv that sets either, or `-e`, is rejected, because
  the product envs declare `monitor_port` as a physical device. The client is
  typed at through a second run-owned pty, as an operator would. If the
  executable is not on `PATH` the case is `DEFERRED_EXTERNAL` (a named
  dependency); nothing is installed or replaced.
- **Why UART1.** Measured on esp-emu 0.49.0: `--console usb-jtag` discards
  UART0 output; `--uart-tcp` disconnects stdio entirely, even with
  `--console usb-jtag`; `--uart1-tcp` leaves stdio on EP1. Output on a TCP UART
  before a client connects is dropped. So a client-transport blob (flag bit 4)
  moves the fixture trace (`K1_EMU_LOG`, the rtrace dump, `EMU_FS_BEGIN`,
  `EMU_SHOW_COMMIT`) to UART1 on GPIO 6/7 (the Arduino defaults 15/16 are the
  Main RPL LED pins), and the fixture prints nothing until it reads
  `K1EMU-GO` on UART1. The runner sends that once the client reports its port
  open (`EMU_CLIENT_READY`).
- **Where a line applies.** A blob command record's second word is its kind:
  0 scheduled (the fixture runs it, as before), 1 client. Before staging a hop
  with client records the fixture prints `EMU_CLIENT_GATE hop= expect=`, then
  keeps calling the production `check_serial()` itself until the parser has
  taken that many lines from USBSerial (bounded by `stall_ms`), then
  `EMU_CLIENT_GATE_DONE`. The runner types a hop's lines only after its gate,
  one at a time, each after the previous line's `EMU_HCMD_DONE` and the
  client's display of the product reply. So a client line applies before the
  declared hop exactly like a scheduled one, independent of host timing; its
  first possible effect is generation `hop+1`. The fixture sends nothing on
  USBSerial and changes no state itself.
- **Observation.** `check_serial` reports each parsed line under the fixture:
  `EMU_HCMD hop= sample= text=` (original text, before the parser tokenises
  it), `EMU_HCMD_DONE hop= rejected= ...`, then `EMU_SS when=hcmd`.
  `EMU_FIXTURE_ARMED` carries `commands=` (scheduled), `client_commands=` and
  `transport=client|scheduled`; `EMU_END` carries `host_commands=`, and
  `rejects=` counts both kinds.
- **End and save.** `--exit-on` follows the USB console, so the runner watches
  the UART1 trace for `[RTRACE-END]` and stops esp-emu with SIGINT, which
  exits 0 and still writes the flash back under `--save-state`. Then it sends
  the client its quit key (Ctrl+C), escalating to terminate/kill on its own
  process only. Raw records stay in the case directory: `uart.txt` (trace),
  `usb-device-to-client.bin`, `usb-client-to-device.bin`, `client-terminal.txt`,
  `emu-stderr.txt`, and `result.json` `cases.<id>.client` (argv, pty, typed
  lines with terminal offsets, events, exit codes, failure reasons).
- **Readback.** Each applied line must show a framed product reply
  (`sbr{{…}}`) without `Bad command`; each rejected line must show
  `Bad command: <name>` on the client's own terminal.
- **Scope.** This qualifies the local client chain only, not physical USB,
  HWCDC timing or a host driver.

The `client` suite runs the client cases with their scheduled references:
`client-a`/`client-b` must equal `ctl-a`/`ctl-b` exactly and isolate their
edge; `client-reject` must equal `smoke-a`; `client-comp-save` →
`client-comp-recover` must recover every K1ShowState field with zero commands
and equal `comp-ref` (SW13).

```bash
python3 tools/esp_emulator/run.py --scenario tools/esp_emulator/s3_music_regression.json \
  --suite client --output _scratch/esp-emulator/<fresh-name>
```

## Watching a run (`player.py`)

```bash
python3 tools/esp_emulator/player.py --run _scratch/esp-emulator/<run> \
  --case music-a --case client-a --case startup-sqr --output _scratch/esp-emulator/<run>/player.html
open _scratch/esp-emulator/<run>/player.html
```

A self-contained page that plays the captured A/B frames in time with the
exact PCM the firmware processed, with the render thread's tempo, confidence,
lock, beat ticks and onsets per frame, a seekable timeline (beat ticks and
commands marked), frame stepping (arrow keys) and native 16-bit values on
hover. Only accepted cases are played; audio is rebuilt from the run's own
`scenario.json` and attached only when its sha256 equals the case record.
A frame shows from its hop-end time: replay application time, not device
latency, and the same display projection as `report.py`, not an optical
model. The page embeds the audio, so keep players of private music local.
esp-emu itself has no LED view (its browser dashboard shows CPU, GPIO pads,
registers and memory), and LED emission is suppressed in this profile.

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
- a recovery run that issued commands, client lines or saves
- a failure end without positions
- client lines parsed at another hop, with other text or another outcome than
  declared, a missing or incomplete `EMU_CLIENT_GATE`, an undeclared client
  line, or a client-transport run without `EMU_CLIENT_READY`

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

## Host checks and clean exports

`host_checks.pytest` (the repository suite) and `host_checks.builds` (the
shipping `k1_hardware` build) run on every invocation. In a clean export
(`git archive`, no `.git`), the test files listed in
`host_checks.requires_git` cannot run, because they read git history. They are
excluded by name, the exclusion is recorded in `result.json`
(`host_checks.excluded_without_git`), and they run in the maintained checkout
at the same commit. The export carries its commit in
`.k1-source-identity.json`, and `SW11` passes only for an export
invocation.

## Diagnostics (opt-in, never part of acceptance)

`"trace_novelty": true` adds one `N,generation,novelty,vu_level,silence,producer_crc`
line per hop. `producer_crc` covers the published audio snapshot, spectrogram,
smoothed spectrogram and chromagram. Every captured frame also has
`V,` lines (producer and render-thread audio meaning for its generation) and
`R,` lines (raw render-thread hue position and mix, master brightness, silent
scale, `LED_FPS`, VU and waveform peak). Use these to localise any future
repeat divergence to the producer or the render side.

## Determinism stress and divergence localisation

```bash
python3 tools/esp_emulator/stress_repeat.py run --case music-a --runs 20 --parallel 4 \
  --output _scratch/esp-emulator/<fresh>
python3 tools/esp_emulator/stress_repeat.py analyse <uart.txt> ...
```

`run` repeats one case under parallel host load, with `trace_novelty`
forced on. It groups the native payloads, reports where each divergent run
first departs (producer, hand-off or render, with the first differing
hop/field/pixels), and prints the 3/N bound. Exit status is 0 only for zero
divergences with every run accepted. `tests/test_esp_emulator_seams_static.py`
ratchets the seams that make replays deterministic.

## Lessons and traps (read before changing anything here)

`/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-ESP-Emulator/docs/LESSONS.md`
is the canonical inventory of the R3 session's failures (F1–F26), their
causes, fixes and guards. The skill `k1-esp-emulator-replay` loads its
must-follow rules.

## Not covered (by design)

Microphone wiring, PDM/I2S/DMA/GPIO/RMT wire timing, hardware scheduling,
current draw, thermal and optical appearance, USB transport, and live
audiovisual quality. No software trace here proves any of them.

---

| Date | Author | Change |
|---|---|---|
| 2026-10-20 | agent:claude-code (R3 owner) | Replaced the R2 one-hop GDB contract with the PCM → production processing → paired-capture/control/persistence interface. |
| 2026-10-20 | agent:claude-code (next phase) | Added the client transport: existing client → run-owned pty → USB-Serial/JTAG → production receive loop, trace on UART1, client gates, SW13 cases. |
