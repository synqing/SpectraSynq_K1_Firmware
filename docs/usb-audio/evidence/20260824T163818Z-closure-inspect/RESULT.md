# USB-audio inspect (current silicon, wrong parent)

**Stamp:** `SILICON_WRITTEN / USB_AUDIO_SMOKE_ENUMERATED / HARDWARE_BINDING_UNRESOLVED`

Not PASS. Not FAIL. Not a soak. Not product restore.

## What was already on the unit

Main RPL `9087A500`, USB serial `9087A5453AB4` (MAC `b4:3a:45:a5:87:90`). Image parent is committed `k1_hardware` (GPIO 6/7), not `k1_main_rpl_im69d`.

## Enumeration

| Observation | Result |
|---|---|
| USB product | `SpectraSynq K1 USB Audio` (ioreg) |
| VID:PID | `303A:1001` (TinyUSB reuses Espressif IDs; not proof of Serial-JTAG) |
| Device class | 239 / IAD composite, full-speed |
| Audio MIDI / Core Audio | `TinyUSB UAC1`, manufacturer SpectraSynq, 1 channel, **12800 Hz** |
| TinyUSB CDC | `/dev/cu.usbmodem9087A5453AB41` |
| Old USB-Serial-JTAG as the only function | gone (composite UAC+CDC present instead) |

`system_profiler SPUSBDataType` returned empty in this session (0 bytes). ioreg + Core Audio + pyserial are the USB evidence.

## Smoke play

- Fixture generated: 44.000 s, 12800 mono S16, peak 8192, SHA-256 `feb37d9a…5402ee`
- Default output was `Multi-Output Device`. Temporarily set to `TinyUSB UAC1`, `afplay` rc=0 (44.4 s), restored `Multi-Output Device`.
- First serial open used DTR=false → 0 bytes (TinyUSB CDC idle until DTR).
- DTR=true produced 1 Hz `[UAC]` lines.

Live `[UAC]` after the play (DTR capture):

- `usb_started=1` `speaker_enabled=1` `valid_stream=1`
- `rate=12800` `channels=1` `bits=16`
- `bytes_received` / `frames_assembled` / `frames_consumed` moving and matched
- `frames_dropped_oldest=0` `enqueue_failures=0` `rate_mismatches=0`
- `queue_high_water=2`
- `underflows=863` (not acceptance-clean; includes silence/gaps and prior streams)
- `stream_generation=17` `reset_reason=1` `heap_free=173240`

## Branch taken

**Audio device appears at 12.8 kHz** + **TinyUSB CDC present**. Smoke only. Do not soak this image.

## Next

Re-parent probe to `k1_main_rpl_im69d`, isolated PlatformIO 55.03.311 root, new factory image, identity-guarded flash.
