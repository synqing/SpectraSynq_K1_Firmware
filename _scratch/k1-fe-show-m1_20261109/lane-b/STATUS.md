# Lane B status

- 2026-11-09 ~19:50 AWST — `prim8_stream.py` READY for import:
  `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/lane-b/prim8_stream.py`
  API in the module docstring. `sys.path.insert(0, <lane-b dir>); import prim8_stream`.
  Timebase: tick t_us = vm.js tickTimeUs on the asset-anchored grid; sidecar schema `k1-prim8-stream/0`.
- Validator, fixtures, contract doc: in progress.
- 2026-11-09 — DONE. Contract: B-P1-contract.md. Validator: validate_prim8_stream.py. Fixtures: fixtures/ (28 + expected.json).
  pytest 149 passed (raw/pytest_run1.txt). Differential oracle vs firmware 407fdf6f agrees on all 28 fixtures.
  Lane D rejected-input case: use invalid_hz_0 / invalid_hz_241 / bad_version only. Never send bad_magic or truncated_mid_stream to hardware.
- 2026-11-09 — Bench-eligibility tooling DONE. Player must send prim8_stream.RESYNC_PREAMBLE (b"\n" + 33 x NUL) before the first frame of every session/epoch.
  Gate: audit_prsm_bytes.py <stream.prsm> -> exit 0 = bench-eligible (use --allow-rejected-frames only for the bad-hz/bad-version rejected-input case).
  lane-c-emu/stream/loreen_75_155_120hz.prsm (sha ea4b8f45...): audit exit 0, validator VALID. pytest 160 passed (raw/pytest_run2.txt).
- 2026-11-09 — Packet-loss exposure DONE. Unguarded bench stream: 110 calibration-queued + 178,135 persisting loss events. Shaping refuted (magic 'RS', seq, t_us).
  Player MUST write RESYNC_PREAMBLE (now 64 B) then each frame as ONE 64-byte write: 30 NUL + frame (prim8_stream.wire_packets). Guarded: 0 hotkeys over 614,336 events.
  Gate: audit_prsm_bytes.py <stream> --guard 30 (exit 0). Watchdog spec: B-P1-contract.md. pytest 163 passed (raw/pytest_run3.txt).
