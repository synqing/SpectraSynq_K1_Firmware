---
abstract: "Non-shippable AP front-end capture contract for K1 tempo/beat/onset diagnostics. Defines why APDBG exists, what it captures, how it is gated, and how device novelty is replayed through the existing host sb_tempo harness without treating clean-file host replay as device truth."
---

# AP front-end capture contract

## Problem

The existing notebook and host harness prove the backend tempo/beat/onset algorithm against a clean WAV-derived novelty map. That is useful, but incomplete: product behaviour includes the mic, I2S, Goertzel spectrum, AGC, silence gate, novelty generation, and tempo tracker. The Loreen capture showed a real divergence between clean host replay and live K1 telemetry, but AP_STREAM/APCAP alone cannot localise the cause.

## Contract

`[APDBG]` is the non-shippable replay surface for the missing half of the system.

It emits one row per `sb_tempo` accepted novelty sample, after the AP loop has run:

1. `process_GDFT()`
2. `calculate_novelty()`
3. `sb_audio_snapshot_update()`
4. `sb_onset_beat_update()`
5. `sb_tempo_update()`

That ordering is mandatory. A pre-update stream is a stale map.

## Firmware boundary

`[APDBG]` is compiled only under `-DENABLE_AP_FRONTEND_DEBUG=1` and depends on `-DENABLE_TEMPO_STREAM=1`.

The new `k1_ap_frontend_probe` environment extends `k1_hardware_harness` and adds:

```ini
-DENABLE_TEMPO_STREAM=1
-DENABLE_AP_FRONTEND_DEBUG=1
-DTEMPO_STREAM_DEFAULT_ON=0
```

The production `k1_hardware` environment does not compile this surface.

The stream is runtime-default-off. Enable it only for a bounded capture:

```text
:apdbg=on
:apdbg=off
```

The existing verbose `TEMPO` / `TEMPO_DBG` stream can be controlled separately:

```text
:tempo_stream=on
:tempo_stream=off
```

## APDBG row fields

Core replay fields:

| Field | Meaning |
|---|---|
| `emit_ms` | firmware timestamp for the accepted tempo novelty sample |
| `emit` | monotonic `sb_tempo` accepted-sample counter |
| `nov` | raw accepted novelty sample after sb_tempo peak-hold downsampling |
| `nov_scaled` | diagnostic scaled novelty; do not use as default replay input |
| `scale` | sb_tempo novelty scale |
| `sil` | snapshot/tempo silence state |

Same-frame context:

| Field | Meaning |
|---|---|
| `peak`, `vu`, `energy`, `low`, `mid`, `high` | post-GDFT/AP snapshot scalars |
| `agc_e`, `agc_floor`, `agc_gain`, `agc_gate` | broadband AGC state |
| `bpm`, `phase`, `conf`, `lock`, `beat`, `str` | published tempo event |
| `win`, `win_bpm`, `top1`, `top1_bpm`, `top2`, `top2_bpm` | winner/candidate evidence |
| `comb`, `point`, `prior`, `v2_q`, `v2_ema`, `v2_lock` | selection/confidence internals |

## Replay rule

Do not feed `[APDBG]` rows directly into `tempo_replay.py` as if they were AP frames. `tempo_replay.py` calls the real `sb_tempo_update()`, which performs its own `/3` peak-hold decimation. `[APDBG]` rows are already accepted samples.

Use:

```bash
python3 scripts/regression-harness/replay_device_apdbg.py <serial-log> --out build/audio-semantic-metrics/device_capture/<name>.apdbg_replay.json
```

The replay script reconstructs three AP frames per accepted sample so the third frame lands on the captured `emit_ms`. This preserves the accepted novelty sequence while letting the existing host `sb_tempo.cpp` remain the authority.

## Interpretation gates

If APDBG replay matches live device tempo but clean-file host replay does not, the front-end territory is the cause class.

If APDBG replay diverges from live device tempo, investigate stream ordering, missed serial rows, timing perturbation, or runtime state not represented in the replay.

If room/mic WAV replay matches APDBG and live device, the acoustic path is implicated.

If room/mic WAV replay matches clean host but APDBG/live device diverge, the firmware AP path is implicated.

## Non-goals

This contract does not tune `SB_TACTUS_BPM`, confidence constants, AGC, onset thresholds, or product visuals.

This contract does not ship telemetry in production firmware.

This contract does not replace MabuTrace when the unknown is timeline/causality rather than scalar replay validity.

---
**Document Changelog**

| Date | Author | Change |
|---|---|---|
| 2026-06-06 | agent:codex | Created APDBG capture/replay contract for AP front-end tempo diagnostics. |
