---
abstract: "Change request to the FW lead: add one read-only typed command, :authored_status, that prints the authored-source state (STANDALONE / AUTHORED_ACQUIRE / AUTHORED / AUTHORED_DRAIN / RECOVERY) and PRSM frame counters. No persistence. About 45 lines in 4 files. Lane D's state-transition evidence needs it; today only an indirect snapshot readout exists."
---

# CR-A8 — read-only authored status command

Raised by Lane A, K1-FE-SHOW-M1 Rev 2, 9 November 2026. Source basis: HEAD `407fdf6f`.

## Problem (FACT)

- The authored state machine (`audio/k1_authored_source.cpp:5–122`) keeps `s_state`, `s_last_seq`, `s_last_prsm_ms` as file statics and exposes only `k1_authored_state()` (`:109`). Nothing in `serial/` prints it: a search of `serial/`, `director/` for `authored`, `STANDALONE`, `RECOVERY`, `prsm` print sites returns none.
- The PRSM branch of `check_serial()` (`serial/serial_menu.cpp:4154–4163`) counts nothing and prints nothing: accepted frames, frames rejected by the parser (`K1_PRSM_SCAN_FRAME_BAD`), and frames rejected for hz out of 30–240 (`k1_authored_map_prim8` returns false, `k1_authored_source.cpp:28–30`, `:66–68`) are all silent.
- The only readout today is indirect: `:smart_status` prints `SMART_AUDIO_NOVELTY` and `SMART_AUDIO_ENERGY` from `k1_audio_snapshot_read()` (`serial/serial_menu.cpp:568`, `:621–624`). That shows the snapshot values (authored pressure or live energy) but not the state, the counters, or why a frame was rejected. The 16 August silicon proof used exactly this (`CHANGELOG.md`, commit `3fc8cd8f`; harness `scripts/agent/k1_authored_silicon_proof.py`).

Consequence for Lane D: D2/D3 must show STANDALONE→ACQUIRE→AUTHORED, seek re-acquire, and AUTHORED→RECOVERY→STANDALONE within 50 ms plus one tick. With the current image this can only be inferred from snapshot values, and ACQUIRE is never observable because `k1_authored_on_frame()` passes through ACQUIRE to AUTHORED inside one call (`:70–87`).

## Requested change

| # | File | Change | Est. lines |
|---|---|---|---|
| a | `audio/k1_authored_source.{h,cpp}` | Add a counters struct: `frames_ok`, `frames_hz_reject`, `acquire_entries` (incremented where `continuous` is false or the prior state was STANDALONE/RECOVERY, `:71–75`), `recovery_entries`, `standalone_entries` (in `k1_authored_tick`, `:97–105`), `last_seq`, `last_hz`, `last_frame_ms`. Getter `k1_authored_stats(k1_authored_stats_t*)`. | ~20 |
| b | `serial/serial_menu.cpp:4158–4161` | Count `K1_PRSM_SCAN_FRAME_BAD` and bytes that fell through to the hotkey path while a frame was incomplete (see CR-A3); store in the same stats via a setter. | ~4 |
| c | `serial/serial_typed_cmd_table.def` | `SERIAL_TYPED_CMD("authored_status", serial_typed_authored_status, SC_SAFE, 0)` — flags 0: no persistence, not harness-gated, so it exists in `k1_fe`. | 1 |
| d | `serial/serial_typed_dispatch.cpp` | Handler printing one `sbr{{ … }}` block: `AUTHORED_STATE`, the counters, `AGE_MS = millis() - last_frame_ms`, and the current intent values. Uses existing `tx_begin()/tx_end()`. | ~20 |

Read-only, Core-1/serial context only, no allocation, no `save_config*`, no change to arbitration behaviour. Optional, same CR: one rate-limited log line on each state change (`[AUTHORED] state=… seq=…`), off unless `:authored_status=stream`; leave out if the FW lead prefers polling only.

## Acceptance

1. Host: extend `tests/test_authored_ingress_native.py` (it already compiles the authored source natively) to assert counters after a scripted frame sequence: good frames, one hz=20 frame, one seq jump, then 60 ms of no frames → `frames_hz_reject=1`, `acquire_entries=2`, `recovery_entries=1`, `standalone_entries=1`.
2. Device (Lane D): `:authored_status` before, during and after a PRSM stream shows the three states and matching counters; `:dump` shows no settings change.

Changelog
- 2026-11-09 Lane A: created.
