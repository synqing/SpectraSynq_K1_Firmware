# 2026-06-15 New Effects Partial VP Smoke

## Verdict

Modes 24-27 have partial live VP smoke evidence on both registered K1s.

This is **not** a complete mode 24-29 smoke. The run was stopped before modes
28-29 completed, and those modes remain unproven by this evidence bundle.

No further audio playback should be run from this lane unless Captain explicitly
authorises it.

## Source Boundary

Current source has already closed the two blockers recorded in the 2026-06-11
effects recovery handover:

- Persisted mode IDs 24/25 are no longer remapped to old Snapwave/Pulse Prism
  aliases. Current source retires the old aliases because 24/25 are now real
  current modes, and `light_mode_sanitize_persisted()` only rejects out-of-range
  or disabled modes (`SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:82`,
  `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:157`).
- Production AP telemetry no longer reads `SBAudioSnapshot` or emits chord
  debug fields. The live AP block reads tempo and onset events only
  (`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:563`).

The static gates cover those two repairs:

- `tests/test_snapwave_pulse_static.py:129` guards persisted mode IDs 24/25.
- `tests/test_chord_hue_consumer_static.py:72` guards the no-chord-telemetry AP
  contract.

## Verification Before Live Smoke

Focused host gate:

```text
python3 -m pytest tests/test_chord_hue_consumer_static.py tests/test_new_effects_batch_static.py tests/test_snapwave_pulse_static.py tests/test_palette_authority_static.py tests/test_impact_lane_static.py -q
38 passed
```

Build gate:

```text
pio run -e k1_hardware
pio run -e k1_bench_reference
```

Both builds passed with the known `system.h:48` volatile warning only.

## Evidence Bundle

Runtime evidence path:

```text
docs/forensics/runtime-evidence/20260615T222315-new-effects-mode24-29-vp-smoke/
```

Devices:

| Role | Port | Chip ID | Env |
|---|---|---|---|
| Main K1 | `/dev/cu.usbmodem12201` | `F887A500` | `k1_hardware` |
| Bench K1 | `/dev/cu.usbmodem12401` | `B489A500` | `k1_bench_reference` |

Manifest labels still use historical `main-1401` / `bench-12201` names. Chip ID
is the identity source of truth.

## Completed Mode Rows

The runner manifests for modes 24-27 have `failure=null` and
`capture_returncode=0`. The music process return code is `-15` because the
wrapper terminates the player at the end of each completed 60 s capture.

| Mode | Device | VP rows | render_us mean | render_us max | Tuple | Device failure |
|---:|---|---:|---:|---:|---|---|
| 24 | Main K1 | 85 | 3319.647 | 4155 | 12800 / 96 | null |
| 24 | Bench K1 | 86 | 3091.384 | 3631 | 12800 / 96 | null |
| 25 | Main K1 | 85 | 1282.988 | 1417 | 12800 / 96 | null |
| 25 | Bench K1 | 85 | 928.941 | 1013 | 12800 / 96 | null |
| 26 | Main K1 | 85 | 1253.440 | 1550 | 12800 / 96 | null |
| 26 | Bench K1 | 85 | 984.765 | 1196 | 12800 / 96 | null |
| 27 | Main K1 | 85 | 1056.059 | 1378 | 12800 / 96 | null |
| 27 | Bench K1 | 85 | 733.553 | 967 | 12800 / 96 | null |

Crash scan:

```text
rg -n "Guru Meditation|Task watchdog|Backtrace:|Brownout|panic|abort|rst:" docs/forensics/runtime-evidence/20260615T222315-new-effects-mode24-29-vp-smoke
0 matches
```

## Open Boundary

- Modes 24-27: partial VP runtime smoke only; not eyes-on acceptance and not a
  full AP+VP product gate.
- Modes 28-29: not covered by this evidence bundle.
- The interrupted mode-28 attempt is deliberately not promoted as evidence.
- Continue with non-playback static/docs/harness work unless Captain explicitly
  authorises another audio window.
