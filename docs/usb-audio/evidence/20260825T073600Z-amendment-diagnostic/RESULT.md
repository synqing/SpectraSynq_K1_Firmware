# USB-audio amendment diagnostic close — 2026-08-25

Captain ruling 2026-08-25: this run is enough. Do not rebuild or reflash
to enable `K1_STM`. Restore product after this freeze.

```text
K1_USB_AUDIO_DIAGNOSTIC = PASS
DIAGNOSTIC_FINISHED     = YES
SECOND_K1_STM_PROBE     = NO
PRODUCT PROMOTION       = NO
USB_SHARED_FINALISER_UNIFICATION = OPEN
```

## Scope claimed

```text
Mac → ESP32-S3 UAC → 12.8 kHz mono S16
→ 96-sample canonical ingress
→ waveform raw peak / peak_scaled
```

## Not claimed

```text
STM loudness
silence semantics
disconnect/suspend concealment
shared-finaliser completion
shipping / product promotion
```

## Frozen observations

| Field | Value |
|---|---|
| Device | Main RPL `9087A500` |
| MAC | `b4:3a:45:a5:87:90` |
| Write port | `/dev/cu.usbmodem112401` (Serial-JTAG) |
| Live CDC | `/dev/cu.usbmodem9087A5453AB41` serial `9087A5453AB4` |
| Product string | `SpectraSynq K1 USB Audio` |
| Host audio | `TinyUSB UAC1` (restored to Multi-Output Device after score) |
| Candidate commit | `feat/k1-usb-audio-input` `0136de678ddf084aa8c174bb590a052294e4e2bb` |
| Env | `k1_usb_audio_mac_probe` extends `k1_main_rpl_im69d` |
| Factory size | 791424 B |
| Factory SHA-256 | `fc5854a5604c5a541d2c82bb17a3651edbdecd835c54a4a41f011762e5c42a54` |
| Write | esptool `write_flash 0x0` + `verify_flash` OK |
| NVS | not erased |
| Negotiated format | 12800 Hz, mono, 16-bit, `valid_stream=1` |
| Frames in/out | assembled = enqueued = consumed (no divergence) |
| Steady play rate | ~131–134 /s in 1 s windows (nominal 133.333 Hz) |
| Drops | 0 |
| `startup_underflows` | 5 |
| `steady_state_underflows` | 0 (held at 5 for the whole play window) |
| Extra underflow | +1 at stream stop (not scored as transport failure) |
| Raw peak range | 0 … ~8192 |
| `peak_scaled` range | 0.000 … 1.000 |
| `loudness` | `BLOCKED` — `K1_STM` not compiled on this probe |
| Runtime `:build` | `git=c1b53860 epoch=1787613527 env=k1_usb_audio_mac_probe` **STALE / NON-AUTHORITATIVE** |

Provenance:

```text
runtime :build string     c1b53860       STALE / NON-AUTHORITATIVE
source candidate          0136de67
factory image SHA-256     fc5854a5604c5a541d2c82bb17a3651edbdecd835c54a4a41f011762e5c42a54
device                    9087A500
MAC                       b4:3a:45:a5:87:90
```

The stale banner does not invalidate the flash. The factory hash, MAC, and
verify-OK establish the bytes on silicon. Future builds must stamp the actual
candidate commit.

## Captain scorecard

```text
USB interface valid              PASS
Negotiated format                PASS — 12,800 Hz mono
Host → K1 frame delivery         PASS
Frames received/consumed match   PASS
Sustained drops                  0
Sustained underflows             0
Canonical waveform raw peak      MOVING
waveform_peak_scaled             MOVING
Main RPL identity                VERIFIED — 9087A500
Factory image write/hash         VERIFIED
NVS/calibration retained         YES

USB transport                    PASS
Canonical waveform ingress       PASS
Waveform peak producer           PASS
STM / EdgeMixer loudness         NOT PRESENT IN BUILD
STM loudness validation          NOT APPLICABLE TO THIS PROBE
```

Hypothesis closed: a clean native USB audio stream can enter Main RPL and
drive the canonical waveform envelope without the microphone acquisition path.

## Receipts

- Write/verify: `_scratch/usb-audio-forensic-20260825/FLASH_GATE.md` (copy here)
- Serial tap: `cdc_score.txt`
- Parsed score: `score_summary.json`

## Residual debt (do not repair on this image)

`USB_SHARED_FINALISER_UNIFICATION = OPEN`. Microphone and USB still fork after
canonical PCM. Before any USB-input product promotion:

```text
MIC source-specific conditioning ─┐
                                  ├→ one shared canonical-hop finaliser
USB source-specific transport ────┘
```

That unification needs golden equivalence tests on the microphone path.

## Product restore target (next act)

```text
device       Main RPL 9087A500
MAC          b4:3a:45:a5:87:90
environment  k1_main_rpl_im69d
commit       b625e89a
factory      docs/usb-audio/evidence/20260824T165900Z-corrected-parent/restore_k1_main_rpl_im69d_b625e89a.factory.bin
SHA-256      973084b464c8a22cab9b1db434a7e385a95c6b1755dc8946ac5af01633a69ce3
NVS          keep (probe did not erase)
```

Do not use `k1-flash-verified.sh` for this restore: it rebuilds HEAD
(`0136de67`), not `b625e89a`. Re-resolve identity after ROM entry.
