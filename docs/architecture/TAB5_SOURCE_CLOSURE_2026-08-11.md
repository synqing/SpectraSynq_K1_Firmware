# Tab5 source closure

The Tab5 production source baseline is the Git tree on
`fix/tab5-hardening-20260811`, rooted at
`21d0e593461af468d38394b140e2477bd58bf7f3` and imported as a named closure.
Git is the source-file content manifest; `tab5_firmware/toolchain-lock.json` is
the external dependency manifest.

## Included

- Active P4 application, Deck protocol, hosted-HCI, LVGL and generated-control
  source under `tab5_firmware/src` and `tab5_firmware/include`.
- The tracked `docs/protocol/k1-deck-state-v1.md` wire contract and the
  generator-derived 71-control Tab5 map. The Tab5 map must remain byte-identical
  to `SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_map.h`.
- Production/native configuration, partition table, simulator, build scripts,
  source generators, build/run guides and licences already present in the Git
  tree.
- The device-proven callback-to-loop queue repair in
  `src/ble_midi_transport.cpp`.
- The previously untracked Arduino-on-P4 `include/sdkconfig.h` shim, now an
  explicit source input.
- A fail-closed project-owned overlay for the official Arduino-ESP32 3.3.1
  archive. The hosted HAL is byte-identical to Espressif PR 11804; the sole
  local source delta is the P4 soft-AP guard. CMake wiring links the existing
  filtered ESP-Hosted 2.0.13 and Wi-Fi-remote archives without any absolute
  machine path.

## Excluded

- `.pio`, build outputs, caches, logs, backups and retired fonts.
- Extracted `vendor` packages and local toolchains.
- Historical ESP-Hosted 1.4 A/B source and C6 flash utilities.
- C6, main-K1, full71, IM69D and unrelated dirty-main-worktree material.

## Provenance findings closed by G0

The local framework claimed version 3.3.0 but its complete Arduino core and BLE
sources match official release 3.3.1. The only relevant mismatch is the
two-line `CONFIG_ESP_WIFI_SOFTAP_SUPPORT` guard. Both are now declared and
checksum-gated by `scripts/patch_tab5_framework.py`; an unexpected upstream
file is refused rather than patched heuristically.

The initial G0 receipt was reopened after red-team parity checks found a stale
68-control Tab5 header and an untracked Deck-state protocol document. The
header is now regenerated from the tracked 71-control JSON authority and the
protocol document is tracked. Targeted protocol/decoder tests are part of G0,
not deferred to a later gate.

The first disposable build correctly failed on the missing hosted HAL. The
second correctly failed on the missing C6 slave-target shim. Importing those
inputs made the third build succeed. These failures are retained as G0 evidence,
not erased from the receipt.

## Deliberate compatibility boundary

The canonical 71-control registry identifies itself as
`78fb9af986da36922fae33cb09de3b4b`. The existing K1 and Tab5 Deck-identity
headers both still advertise the older `9b5db3fbb17438367adeaceb541db03b`
wire digest. Changing the K1 identity or flashing main K1 is outside this
programme's approved Tab5/P4 scope. Source closure therefore requires both
identity copies to remain equal and the two generated map headers to remain
equal, while recording the legacy identity digest as an explicit compatibility
exception. G2 must not silently relabel this as canonical; G3 must prove the
actual peer accepts the compatibility identity before any release claim.
