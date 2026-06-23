# 2026-06-15 Phase 3/4/5 Runtime Proof

## Verdict

Phase 3/4/5 objective engineering work is implemented, host-gated, flashed to
both registered K1 devices, and runtime-proven on the flashed firmware.

The subjective colour-feel judgement remains an eyes-on product judgement if
Captain disputes it, because serial telemetry cannot prove perceived palette
quality. The source authority, static guards, builds, upload, runtime command
surface, preset/queue path, and 75 s post-flash soak are closed.

## Source Commit

- Firmware source commit: `03b7cdf fix(firmware): prove phase345 runtime controls`
- Branch at deployment: `rescue/1401-head-minus-killset`

Source surfaces:

- Phase 3 percussion substrate: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h`
  adds safe `:event_status` output for onset, kick, snare, hihat, event ids,
  levels, strengths, energy, novelty, and silence state.
- Phase 4 colour authority: `SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h`
  adds `palette_chroma_colour_with_offset()`, and Waveform Fast, Waveform
  Hybrid, Tempo Comet, and Snapwave now consume position/lineage offsets rather
  than collapsing every fallback to one palette coordinate.
- Phase 5 queue/preset proof: `:slot_save=N,primary|secondary` is explicit, and
  `scripts/regression-harness/k1_phase345_runtime_proof.py` validates safe
  slot save/load plus queued commit restore on real devices.

## Gates Run

- `python3 -m pytest tests/ -q` - 441 passed.
- `pio run -e k1_hardware` - success, known `system.h:48` volatile warning only.
- `pio run -e k1_bench_reference` - success, same known warning only.

## Devices Flashed

| Device | Port | Chip | Env | Uploaded commit |
|---|---|---|---|---|
| 1401 main K1 | `/dev/tty.usbmodem12201` | `F887A500` | `k1_hardware` | `03b7cdf` |
| 12201 bench K1v2 | `/dev/tty.usbmodem12401` | `B489A500` | `k1_bench_reference` | `03b7cdf` |

The unregistered `/dev/cu.usbmodem1401` device was not touched.

## Runtime Proof

Runtime proof manifest:
`docs/forensics/runtime-evidence/20260615T024851-phase345-runtime-proof-manifest.json`

Raw logs:

- `docs/forensics/runtime-evidence/20260615T024851-phase345-main-1401.log`
- `docs/forensics/runtime-evidence/20260615T024851-phase345-bench-12201.log`

Result:

- Manifest `failure`: `null`
- Manifest `git_head`: `03b7cdf`
- Both devices answered expected chip IDs and `:version=40103`.
- Both devices started in mode 8, temporarily entered mode 9, loaded queued slot
  3, committed, and restored mode 8.
- Both devices produced complete `EVENT_STATUS` fields for onset, kick, snare,
  hihat, transient ids, per-channel ids, levels, strengths, energy, novelty, and
  silence.
- No calibration, erase, reset, raw dump, factory reset, restore defaults, or
  destructive commands were sent by the proof harness.

Preset side effect:

- Slots 1, 2, and 3 are now valid on both devices. Slot 3 was filled by the
  final committed proof run; slots 1 and 2 were filled by earlier pre-final
  proof attempts during the same phase.

## Post-Flash Soak

Soak manifest:
`docs/forensics/runtime-evidence/20260615T024954-snappiness-manifest.json`

Raw logs:

- `docs/forensics/runtime-evidence/20260615T024954-snappiness-main-1401.log`
- `docs/forensics/runtime-evidence/20260615T024954-snappiness-bench-12201.log`

Result:

- Manifest `failure`: `null`
- Duration: 75 s
- Configure: `false`
- VP performance requested: `true`
- Timing parity: `true`
- Main 1401: AP=98, VP=81, DC=-4746, SSL=154,
  `sample_rate=12800`, `samples_per_chunk=96`, `render_us_mean=626.172840`
- Bench 12201: AP=97, VP=81, DC=-1124, SSL=354,
  `sample_rate=12800`, `samples_per_chunk=96`, `render_us_mean=641.975309`
- Crash/reset marker grep over both soak logs found zero matches for:
  `Guru|panic|rst:|abort|assert|Backtrace|Brownout|WDT|crash|ERROR`

## Product Boundary

The engineering closure is objective. The remaining subjective question is
whether the palette changes look materially better to Captain's eyes on the
actual LGP. If the eyes-on result is rejected, the next lever is tuning palette
offset constants or effect-specific colour authority, not reopening device
identity, calibration, queue/preset persistence, or the percussion event
readout.
