# G2 behavioural hardening receipt — 2026-08-11

## Gate verdict

**PASS — host semantics and P4 production build.** Silicon behaviour remains a
G3 claim and is not implied by this receipt.

## Shipped behaviour

- NimBLE callbacks are bounded copy-only producers. Deck state and LVGL mutate
  only from the loop-owned drain path.
- Link and payload queues are separate, bounded, generation-tagged, and
  fail-closed on loss. A connect no longer purges a valid queued HELLO/SNAPSHOT.
- Snapshot and delta transactions use bounded static staging and apply only
  after complete validation. Gaps, corrupt packets, invalid members, timeouts,
  queue loss, and ambiguous CLAMPED/UNAVAILABLE v1 deltas desynchronise and
  require a new snapshot.
- Protocol v1 has no request correlation ID, so REJECTED, CLAMPED, and
  UNAVAILABLE deltas all fail closed and require resnapshot. This also protects
  the identical-value ABA case where map plus value cannot identify a request.
- RSSI is cache-only from the UI, sampled by one bounded worker at a two-second
  cadence with deadline, classification, generation discard, and backoff.
- Production HCI/per-value diagnostics are compile-time disabled and a
  production build with either flag enabled fails compilation.
- The pinned Arduino 3.3.1 dual-connect callback is deduplicated before queueing.
  Packet CRC and snapshot transaction CRC counters remain distinct.
- The flash script requires an explicit port and verifies ESP32-P4 chip type and
  MAC `30:ed:a0:e0:c1:a0` before any write.

## Validation

```text
python3 -m pytest \
  tab5_firmware/tests/test_deck_state_rx_transaction.py \
  tab5_firmware/tests/test_tab5_g2_transport_static.py \
  tab5_firmware/tests/test_tab5_gate1_mutation.py \
  tests/test_deck_state_v1.py \
  tests/test_ble_midi_firmware_decoder.py -q
25 passed in 8.83s

/Users/spectrasynq/.platformio/penv/bin/pio run \
  -d tab5_firmware -e tab5_p4
SUCCESS in 17.52s
RAM 70,780 / 512,000 bytes (13.8%)
Flash 1,315,669 / 3,145,728 bytes (41.8%)

tab5_firmware/scripts/flash_tab5_p4.sh \
  --port /dev/tty.usbmodem12401 --verify-only
PASS: ESP32-P4 revision 1.0, MAC 30:ed:a0:e0:c1:a0; nothing written
```

The PlatformIO `esp_idf_size --ng` compatibility warning remains non-fatal;
PlatformIO's subsequent size check and image generation succeeded.

## Production artefacts

```text
firmware.elf  d12a7e0e35714936b331a30edcdf7ce97de7be481ee72d26c21b8f9b9b4b50e4
firmware.bin  806ec0222ce705c352ff529854f529310ca71679d9048e428c618c1cd92cb000
```

## Boundary

The isolated Tab5 branch intentionally differs from the global IM69D active
lane, so the global repo-truth bootstrap reports that branch mismatch. No C6,
main K1, full71, or IM69D/global authority mutation was made. G3 must still
prove the flashed P4 and peer-dependent reconnect/fault/soak criteria.
