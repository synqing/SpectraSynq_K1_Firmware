# K1 native USB-audio prototype

Non-shippable ESP32-S3 UAC1 speaker-only ingress. A Mac can stream 12.8 kHz mono
S16 PCM into K1. Production `k1_hardware` remains the microphone authority.

**Silicon close (2026-08-24):** Main RPL parented, gated, then **taken off**.
Product restored: `k1_main_rpl_im69d` @ `b625e89a` epoch `1787591762`.
Prototype is **not** A16–A26 PASS (A22 FAIL, A25 FAIL, A24 HOLD, A27 NOT_RUN).

Evidence: `docs/usb-audio/evidence/20260824T122122Z/` (host) and
`docs/usb-audio/evidence/20260824T165900Z-corrected-parent/` (silicon).

## 1. Purpose

Prove that native USB Audio Class 1 (full-speed, speaker-only) can feed the
existing 96-sample canonical hop without changing the shipping IDF 5.4.1
microphone build.

## 2. Architecture

```
Mac (UAC1 speaker sink)
  → TinyUSB UAC + CDC composite (Arduino 3.3.11 USBAudioCard)
  → k1_usb_on_spk_data (ISR-like callback: assembler only)
  → depth-4 drop-oldest mailbox
  → acquire_sample_chunk USB branch
  → k1_audio_commit_canonical_frame
  → waveform[96] / sample_window / waveform_fixed_point
  → existing GDFT / tempo / effects
```

## 3. Why a separate framework env

Production is pinned to pioarduino **54.03.20** (Arduino 3.2.0 / IDF 5.4.1)
because the IM69D PDM slot/order contract is frozen to that driver.
USBAudioCard exists in Arduino **3.3.11** (pioarduino **55.03.311**, IDF 5.5.5).
The probe env overrides `platform` only. It does not move `k1_hardware`.

## 4. Why S3 is UAC1

ESP32-S3 USB-OTG device-mode TinyUSB exposes USB Audio Class 1 at full speed.
This prototype is speaker-only (host → device). No USB microphone.

## 5. Exact USB format

| Field | Value |
|---|---|
| Direction | host → K1 |
| Class | UAC1 FS |
| Sample format | S16LE |
| Channels | 1 (mono speaker, no mic) |
| Rate | 12800 Hz |
| Hop | 96 samples / 192 bytes / 7.5 ms |

No resampler on this prototype. 12.8 kHz was accepted by macOS on Main RPL.
A 48 kHz UAC endpoint is **not** a licence to run AP at 48 kHz.
Authority: [ADR-0008](../architecture/ADR-0008-usb-audio-keeps-12800-ap.md).

## 6. Canonical PCM boundary

USB joins at `waveform[]` after filling a local `int16_t[96]`. Commit helper
`k1_audio_commit_canonical_frame` copies history, shifts `sample_window`, and
applies `audio_response_gain_apply_sample` + `SQ15x16` exactly as the
microphone tail does. USB must not include `i2s_audio.h` from a second TU.

## 7. Microphone stages bypassed

| Mic stage | USB |
|---|---|
| PDM / I2S RX (`init_i2s`, `i2s_channel_read`) | not started |
| IM69 `K1_MIC_IM69D_INPUT_GAIN` (×8) | not applied |
| `CONFIG.DC_OFFSET` | not subtracted |
| `CONFIG.SENSITIVITY` | not applied |
| loud-guard / mic_health / auto-sense | compiled out (`K1_AUDIO_SOURCE_MIC=0`) |
| noise_cal / SSL persist | not written |
| USB floor | 0 (no SSL) |

Post-canonical tail **does** run: history, window, response gain, fixed-point,
and the waveform peak envelope (`waveform_peak_scaled`).

## 8. Queue depth 4 + drop-oldest

`K1UsbFrameMailbox` is a static ring of 4 whole 192-byte frames. A full queue
drops the oldest complete frame. Partial bytes never enter the mailbox; they
stay in the assembler until 192 bytes arrive.

## 9. Underflow, pacing, and waveform envelope

Active stream: block on the complete-frame task notify (20 ms stall
timeout) so AP consume rate follows USB produce rate (~133 Hz), not
`loop()` (~167 Hz). Inactive pacing: 7-then-8 tick `vTaskDelayUntil`
(mean 7.5 ms). The `.ino` `vTaskDelay(1)` is unchanged.

**Underflow policy (amended 2026-08-25, Captain verdict):**

- Inactive (stream not valid): emit zeros. Hold is not cleared here;
  clearing on every inactive hop would penalise rapid reconnect.
- Gen-bump (disconnect / suspend / rate change): `s_hold_valid = false`
  and `s_consecutive_underflows = 0` immediately. Resume must wait for
  the first complete fresh frame.
- First missing hop within a generation (`s_consecutive_underflows == 0`
  while `s_hold_valid`): emit a **tail-to-zero ramp** — a linear fade
  applied to the last valid 96-sample frame, not a full PCM replay.
  Replaying the hop verbatim would fabricate a 133.33 Hz periodic signal.
  After emission the hold is invalidated; conceal budget is consumed.
  Comment in source: *holding a ramp from last sample, not derived
  envelope, not a repeated hop.*
- Second or subsequent consecutive underflow, or no prior valid hold:
  emit zeros.
- Concealment is damage-control. PASS requires steady-state underflows=0.

USB commit also runs the waveform peak envelope (`waveform_peak_scaled`
follower, USB floor 0). The microphone tail that normally updates that
scalar is skipped by the USB early-return; without this step every
waveform-family effect sits at centre / dark. In-RAM
`CONFIG.SWEET_SPOT_MIN_LEVEL = 0` on first USB hop so SSL-relative
reactive gates do not compare USB peaks to a leftover microphone floor.
This is not persisted.

## 9a. Shared finaliser ownership table

Every field written in `acquire_sample_chunk` is either **shared** (both
sources call the same finaliser) or **mic-only** (USB path legitimately
skips it). Fields that are **USB-pending** are those where a USB-neutral
implementation is deferred.

| Field / function | Status | Why |
|---|---|---|
| `waveform[]`, `waveform_history[]` | **shared** — `k1_audio_commit_canonical_frame` | canonical PCM copy; source-neutral |
| `sample_window[]` | **shared** — `k1_audio_commit_canonical_frame` | `audio_response_gain_apply_sample`; source-neutral |
| `waveform_fixed_point[]` | **shared** — `k1_audio_commit_canonical_frame` | SQ15x16 normalise; source-neutral |
| `max_waveform_val_raw`, `max_waveform_val` | **shared** — `k1_audio_commit_canonical_frame` | digital peak of the hop; source-neutral (USB floor = 0) |
| `waveform_peak_scaled` / `max_waveform_val_follower` | **shared** — `k1_usb_update_waveform_peak_envelope` (ingress) | USB follower with floor 0; source-neutral; `CONFIG.SWEET_SPOT_MIN_LEVEL = 0` on first hop |
| `agc_loudness_norm` | **shared** — USB branch in `acquire_sample_chunk` (`#ifdef K1_STM`) | USB: peak/32768 normalised from canonical hop. Mic: pre-AGC raw RMS (i2s_audio.h ~681). Both paths are inside `#ifdef K1_STM`. EdgeMixer STM reads this; without the USB write STM modulation depth is always 0. `[USB-WF]` emits `loudness=BLOCKED` if `K1_STM` absent. |
| `CONFIG.SWEET_SPOT_MIN_LEVEL` | mic-only (set to 0 at USB start) | SSL is a mic-RMS concept; USB sets to 0 once at first hop |
| `silence` / `silent_scale` | mic-only (full silence FSM); probe bypass via `K1_USB_FORCE_PRESENT_DIAGNOSTIC` | USB digital silence not implemented; see §9b |
| `i2s_channel_read` / `im69d/im73d` raw RMS | mic-only | hardware PDM; not applicable to USB |
| `loud_guard`, `mic_health`, `auto_sense`, `noise_cal`, `SSL persist` | mic-only | IM69D130 mic-specific quality pipeline |
| AGC feedback (`agc_envelope`, `agc_noise_floor`) | mic-only | audio feedback control; USB has no AGC |
| `raw_dump_request` handler | mic-only | PDM raw frame debug; not applicable |

## 9b. USB digital silence — diagnostic only

`K1_USB_FORCE_PRESENT_DIAGNOSTIC` (added 2026-08-25) is set in the probe
env build flags. It forces `silence = false` so peak-reactive effects can
activate during bench smoke tests. This is a **peak-path smoke bypass**,
not complete USB silence semantics.

Full USB digital silence requires: `valid_stream` + host mute off + hop
RMS/peak below threshold + hysteresis + minimum quiet-frame count. That
FSM (`K1_USB_SILENCE_SEMANTICS_V1` or equivalent) does not exist in this
probe. Do not claim fixture silence sections are valid until it does.

Never set `K1_USB_FORCE_PRESENT_DIAGNOSTIC` in `k1_hardware` or any
production env.

## 10. Composite UAC + CDC

One TinyUSB device: UAC1 mono speaker + CDC (`USBCDC USBSerial(0)`). No MSC,
DFU, USB mic, HID, MIDI, WebUSB, or second CDC. Strings: manufacturer
`SpectraSynq`, product `SpectraSynq K1 USB Audio`. One `USB.begin()`.

## 11. Build commands

```bash
bash scripts/agent/pio-build.sh k1_hardware
bash scripts/agent/pio-build-usb-audio.sh
python3 -m pytest tests/test_k1_usb_audio_*.py tests/test_im69d_env_static.py
```

Probe env: `[env:k1_usb_audio_mac_probe]`. Production src-filter excludes
`audio/k1_usb_audio_input.cpp`; the probe re-adds it.

## 12. Guarded flash procedure

Captain named Main RPL (`9087A500` / MAC `B4:3A:45:A5:87:90`) for this OTG
probe. Identities JSON maps `k1_usb_audio_mac_probe` to that serial.

Never flash F887. Never P4 / K718 / Tab5. Do not burn `USB_PHY_SEL`.

ROM-download (1200 bps on TinyUSB CDC, or BOOT/RESET) is the recovery path
once the app owns USB-OTG. TinyUSB CDC is expected on this composite; it is
not Serial-JTAG. DTR must be asserted to receive `[UAC]` lines. Missing CDC
is not automatically “expected OTG failure”.

Product restore after the probe: `k1_main_rpl_im69d` @ `b625e89a`.

## 13. ROM-download recovery

Because the app owns USB-OTG, Serial-JTAG may vanish:

1. Hold BOOT
2. Pulse RESET/EN
3. Release BOOT
4. Identify the newly enumerated ROM port (do not assume the old `cu.*` name)
5. Guarded upload against that exact port

Do not burn USB-OTG eFuse.

## 14. macOS selection

Audio MIDI Setup → TinyUSB UAC1 (product `SpectraSynq K1 USB Audio`) →
output → mono → 16-bit integer → 12800 Hz. Score `[UAC]` / `[USB-WF]` serial,
not plate eyes. `afplay` follows the Mac default output — switch to TinyUSB
UAC1, then restore Multi-Output Device.

## 15. Fixture command

```bash
python3 tools/usb_audio/generate_k1_usb_audio_fixture.py \
  --output docs/usb-audio/evidence/20260824T122122Z/k1_usb_audio_fixture_12800_mono_s16.wav
```

44 s programme: silence, 110/440/1000/3000/5000 Hz sines at 0.25 FS, 120 BPM
windowed clicks. No clipping.

## 16. Telemetry field definitions

1 Hz `[UAC]` line on the AP path (never in `k1_usb_on_spk_data`):

`usb_started, suspended, speaker_enabled, valid_stream, rate, channels, bits,
host_mute, host_volume_db, callback_count, bytes_received, samples_received,
frames_assembled, frames_enqueued, frames_consumed, queue_depth,
queue_high_water, frames_dropped_oldest, enqueue_failures, underflows,
rate_mismatches, stream_generation, partial_bytes, stale_generation_drops,
queue_age_p50/p95/p99/max_us, heap_free, reset_reason`

Host mute zeros samples. Volume is logged only; `applyVolume()` is not called.

## 17. Acceptance results

Host evidence: `docs/usb-audio/evidence/20260824T122122Z/`.
Silicon evidence: `docs/usb-audio/evidence/20260824T165900Z-corrected-parent/`.

Corrected-parent factory: 791328 B, SHA-256
`a257809e39d2d377ac3f31dc8f1ceea7b2f951fc291ec7870135b4dff7b92d71`,
git=`c1b53860`, env=`k1_usb_audio_mac_probe`, extends `k1_main_rpl_im69d`.

| ID | Result | Note |
|---|---|---|
| A0 | PASS | `feat/k1-usb-audio-input` from `c3e13ffd`. Pre-existing dirty: `tools/webflash/index.html` (not staged). |
| A1 | PASS | Unrelated dirty file left unstaged. |
| A2 | PASS | Baseline `k1_hardware` bin SHA-256 `6b4fd2b07bc45d0ed32d5e55ba67c60aa77d19b28e079f987c24715951822fee` (712416 bytes). |
| A3 | PASS | Baseline `pytest tests`: 1490 passed, 1 skipped. |
| A4 | PASS | Probe platform `55.03.311`. |
| A5 | PASS | Probe Arduino 3.3.11 / IDF 5.5.5 (`framework-arduinoespressif32 @ 3.3.11`). |
| A6 | PASS | Probe sdkconfig has TinyUSB audio+CDC; `nm` shows `USBAudioCard` (13) and `tud_audio` (13). |
| A7 | PASS | Production still `default_envs = k1_hardware`, mic source, `-<audio/k1_usb_audio_input.cpp>`. |
| A8 | PASS | Probe `-DK1_AUDIO_SOURCE_USB=1 -DK1_AUDIO_SOURCE_MIC=0`, re-adds USB TU. |
| A9 | PASS | IM69 5.4.1 `#error` string still in `i2s_audio.h` under `K1_AUDIO_SOURCE_MIC`. |
| A10 | PASS | Host assembler/commit tests. |
| A11 | PASS | Host fragmentation tests (odd lengths / split samples). |
| A12 | PASS | Host mailbox depth-4 drop-oldest + underflow. |
| A13 | PASS | USB sample-domain tests (no IM69 ×8, no DC, no `applyVolume`). |
| A14 | PASS | Final `k1_hardware` SUCCESS. Bin SHA-256 `baf23454df448b1cd90c5c9b630005fe6a3273b9aa9a1944636f9f8245213a09` (712416 bytes). Hash moved vs A2 because `i2s_audio.h` gained fail-closed USB `#if` seams + `k1_audio_ingress.h`; `nm` has `i2s_channel_read` and no `USBAudioCard`. Packages remain Arduino 3.2.0 / 54.03.20. |
| A15 | PASS | Probe SUCCESS (Main-RPL parent, isolated PIO). Factory SHA-256 `a257809e…` (791328 bytes). |
| A16 | PASS | TinyUSB CDC `/dev/cu.usbmodem9087A5453AB41`, product `SpectraSynq K1 USB Audio`. `SPUSBDataType` was empty this host; ioreg + pyserial used. |
| A17 | PASS | Core Audio output `TinyUSB UAC1`, manufacturer SpectraSynq. |
| A18 | PASS | Negotiated 12800 Hz mono S16 (`Current SampleRate: 12800`, `[UAC] rate=12800`). |
| A19 | PASS | 44 s fixture: `bytes_delta=1155840` (~25628 B/s). |
| A20 | PASS | `frames_delta=6020` (~133.5 fps); assembled=enqueued=consumed. |
| A21 | PASS | `[USB-WF]` tone peak_scaled 0.785 > silence 0.668; 110 Hz hop raw rose to ~8191. No GDFT bin print on the USB early-return path. |
| A22 | FAIL | `[AP]` onset/tempo never emits on USB: `acquire_sample_chunk` returns before the `[AP]` printf. `:ap_stream=on` acknowledged. Click energy is visible on `[USB-WF]` during the 120 BPM section. `process_GDFT()` still runs after acquire. |
| A23 | PASS | Fixture 440 Hz window: drop_ss_delta=0, underflow_ss_delta=0. Totals: dropped=0, underflows=3 (startup only), queue_high_water=1, rate_mismatches=0. |
| A24 | HOLD | `apcad_soak` is not compiled on this probe (plan: reuse only if already compiled). Queue age p50≈32 µs / p99≈40–50 µs; hop cadence ~133 Hz. Production AP p99 was not re-measured. |
| A25 | FAIL | 30 min soak aborted at play 22/41 (~16 min): UAC/CDC disappeared. Until then drop_ss_delta=0, underflow_ss_delta=0, heap 172768→172584 (−184 B), reset_reason stayed 11, queue_high_water=1. Device later reappeared as Serial-JTAG product `SpectraSynq K1 ESP32-S3-WROOM N16R8`. |
| A26 | PASS | Ten 1200-bps disconnect → JTAG → hard_reset → UAC+CDC → 6 s fixture. 10/10 PCM. Heap 172768 stable. `esptool` via PlatformIO penv python. |
| A27 | NOT_RUN | Mac suspend/resume not attempted (would disrupt the operator). |
| A28 | PASS | USB path has no NVS mic-cal writes (host static + source). Restore inherited `SSL=157 persisted_profile`. |
| A29 | PASS | ROM-download proven twice on 9087: 1200 bps → USB-Serial/JTAG serial `B4:3A:45:A5:87:90` → esptool `read_mac` + factory `0x0` + `verify_flash` OK (probe and product restore). Never F887. Never eFuse. |
| A30 | PASS | Focused USB tests green; `test_all_k1_chip_bound_envs_are_registered_in_guard` and tempo-inc wrapper gate re-checked after blocking the probe env. Full `pytest tests` log in `19_final_full_pytest.log` (two misses were this lane; both now fixed). |
| A31 | PASS | Lane commit on `feat/k1-usb-audio-input` (parent + isolation). Not pushed. |

## 18. Known limitations

- `[AP]` 1 Hz onset/tempo is compiled but unreachable on USB because
  `acquire_sample_chunk` returns first. A22 stays FAIL until that print (or a
  USB-side equivalent) is moved before the return, then re-flashed.
- 30-minute soak did not complete; UAC vanished at ~16 min (A25 FAIL).
- `system_profiler SPUSBDataType` returned 0 bytes on this host; ioreg and
  Core Audio were used instead.
- TinyUSB CDC needs DTR asserted. Opening Serial-JTAG after TinyUSB hard_reset
  sometimes needs a host open to finish PHY handoff.
- Isolated PIO root `~/.platformio-k1-usb-audio` + `.pio-usb-audio/` is
  mandatory. Homebrew `pio` is not the production Core.
- PlatformIO's unhashed `framework-arduinoespressif32` package is shared:
  building the probe installs 3.3.11 into a **separate** package dir; production
  stays 3.2.0 in `~/.platformio/packages`. Always rebuild the env you intend to
  flash.

## 19. Direct-rate fallback status (ADR-0008)

**This prototype stays 12.8 kHz / 96 / 7.5 ms.** Do not set
`DEFAULT_SAMPLE_RATE` to 48000. Do not put a resampler in `loopTask`,
`acquire_sample_chunk`, canonical commit, GDFT, tempo, or the TinyUSB
`onData` callback.

macOS Multi-Output Device is **not** a contract that 12.8 kHz K1 plus 48 kHz
speakers will convert correctly. The preferred path is Mac-side grouped
output: 48 kHz to Bose / laptop, independent SRC to 12.8 kHz for K1.

If native mixed-rate Multi-Output becomes a named product requirement, that
is a **new** lane (`K1_USB_AUDIO_48K_TRANSPORT_SRC`): UAC 48 kHz copy-only
callback → Core-1 4/15 polyphase 360→96 → existing mailbox → unchanged AP.
No measurement, no promotion. See ADR-0008.

## 20. Production authority

`k1_hardware` remains microphone/production authority. Main RPL silicon was
restored to `k1_main_rpl_im69d` @ `b625e89a` epoch `1787591762`
(`IDENTITY OK` on `:build`). This prototype does not promote USB ingress.