# K1 native USB-audio prototype

Non-shippable ESP32-S3 UAC1 speaker-only ingress. A Mac can stream 12.8 kHz mono
S16 PCM into K1. Production `k1_hardware` remains the microphone authority.

Evidence: `docs/usb-audio/evidence/20260824T122122Z/`.

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

No resampler unless macOS rejects 12.8 kHz (Phase 17, not executed).

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
`loop()` (~167 Hz). If the mailbox is still empty after the wait, hold the
last live hop instead of writing 96 zeros. Inactive: 7-then-8 tick
`vTaskDelayUntil` (mean 7.5 ms). The `.ino` `vTaskDelay(1)` is unchanged.

USB commit also runs the waveform peak envelope (`waveform_peak_scaled`
follower, USB floor 0). The microphone tail that normally updates that
scalar is skipped by the USB early-return; without this step every
waveform-family effect sits at centre / dark. In-RAM
`CONFIG.SWEET_SPOT_MIN_LEVEL = 0` on first USB hop so SSL-relative
reactive gates do not compare USB peaks to a leftover microphone floor.
This is not persisted.

## 10. Composite UAC + CDC

One TinyUSB device: UAC1 mono speaker + CDC (`USBCDC USBSerial(0)`). No MSC,
DFU, USB mic, HID, MIDI, WebUSB, or second CDC. Strings: manufacturer
`SpectraSynq`, product `SpectraSynq K1 USB Audio`. One `USB.begin()`.

## 11. Build commands

```bash
bash scripts/agent/pio-build.sh k1_hardware
bash scripts/agent/pio-build.sh k1_usb_audio_mac_probe
python3 -m pytest tests/test_k1_usb_audio_*.py tests/test_im69d_env_static.py
```

Probe env: `[env:k1_usb_audio_mac_probe]`. Production src-filter excludes
`audio/k1_usb_audio_input.cpp`; the probe re-adds it.

## 12. Guarded flash procedure

Flash **HOLD** until Captain names a lab ESP32-S3 and an identities row exists
for this OTG probe.

Never flash F887. Never flash 9087 with this OTG probe. Never P4 / K718 / Tab5.

## 13. ROM-download recovery

Because the app owns USB-OTG, Serial-JTAG may vanish:

1. Hold BOOT
2. Pulse RESET/EN
3. Release BOOT
4. Identify the newly enumerated ROM port (do not assume the old `cu.*` name)
5. Guarded upload against that exact port

Do not burn USB-OTG eFuse.

## 14. macOS selection

After a future authorised flash: Audio MIDI Setup → SpectraSynq K1 USB Audio →
output → mono → 16-bit integer → 12800 Hz. Score `[UAC]` serial, not plate
eyes.

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

Evidence: `docs/usb-audio/evidence/20260824T122122Z/`.

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
| A15 | PASS | Probe SUCCESS. Bin SHA-256 `ba0630154cc8cb23be4df0668b07dc9a38f87f0e315b46d04ae3dcd79dff1040` (725088 bytes). `i2s_channel_read` absent. |
| A16 | NOT_RUN | No authorised flash. |
| A17 | NOT_RUN | No authorised flash. |
| A18 | NOT_RUN | No authorised flash. |
| A19 | NOT_RUN | No authorised flash. |
| A20 | NOT_RUN | No authorised flash. |
| A21 | NOT_RUN | No authorised flash. |
| A22 | NOT_RUN | No authorised flash. |
| A23 | NOT_RUN | No authorised flash. |
| A24 | NOT_RUN | No authorised flash. |
| A25 | NOT_RUN | No authorised flash. |
| A26 | NOT_RUN | No authorised flash. |
| A27 | NOT_RUN | Suspend/resume not attempted. |
| A28 | PASS | USB path has no NVS mic-cal writes (host static + source). |
| A29 | HOLD | `DEVICE_FLASH = HOLD_NO_AUTHORISED_TARGET`. Never F887. Never 9087 with this OTG probe. ROM-download recovery is documented, not silicon-proven. |
| A30 | PASS | Focused USB tests green; `test_all_k1_chip_bound_envs_are_registered_in_guard` and tempo-inc wrapper gate re-checked after blocking the probe env. Full `pytest tests` log in `19_final_full_pytest.log` (two misses were this lane; both now fixed). |
| A31 | PASS | Lane commit on `feat/k1-usb-audio-input` (this document). Not pushed. |

## 18. Known limitations

- Device enumeration is unproven until Captain names a lab ESP32-S3 and an identities row exists for `k1_usb_audio_mac_probe`.
- macOS 12.8 kHz acceptance is unknown. No resampler in this lane.
- PlatformIO's unhashed `framework-arduinoespressif32` package is shared: building the probe installs 3.3.11; building `k1_hardware` restores 3.2.0. Always rebuild the env you intend to flash.

## 19. Direct-rate fallback status

Not started. Isolation before any 16 kHz or 48 kHz resampler.

## 20. Production authority

`k1_hardware` remains microphone/production authority. This prototype does not
promote USB ingress, does not change the 54.03.20 platform pin, and does not
ship until a later named promotion.
