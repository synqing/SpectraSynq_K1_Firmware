# HANDOVER D — SysEx schema transport over BLE-MIDI (host-testable contract library)

**Project folder:** `/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-K1-DualMCU-Firmware`
**Read-only input:** `/Users/spectrasynq/SpectraSynq_K1_Firmware` — `docs/protocol/k1-deck-state-v1.md`, `k1-deck-identity-v1.md`, `k1-ble-midi-map.json`, and `SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_decoder.{h,cpp}` (how the proven 07 Aug BLE-MIDI link frames packets). Never edit that repo.
**Depends on:** Handover C's `contract/control_schema_v1.md` blob format if it exists; otherwise a synthetic blob of the same shape (71 records × ~80 bytes) — say so.
**Agent:** Claude Code or Codex, one session, one branch (`lane/k1-dm-130-sysex-schema`).

---

You are the protocol engineer for the SpectraSynq K1. Ruling of 2 Sep 2026: the K1 publishes its control schema to the Tab5 deck **as MIDI System Exclusive (SysEx) over the existing BLE-MIDI link**. Control values keep travelling as ordinary Control Change messages. No second Bluetooth GATT service. The K1 remains the authority; the deck renders what it is told.

There is **no BLE-MIDI code in this repo yet** (the proven link is in the legacy S3 firmware). You build the framing library and its tests only. Do not add a BLE stack.

## Wire design (fixed; parameters are yours to tune)

Manufacturer ID `0x7D` (non-commercial) for now; one-line TODO to register a real ID before shipping. Message family `K1 SCHEMA`:

| Message | Direction | Payload |
|---|---|---|
| `SCHEMA_HELLO` | K1 → deck, on connect | schema CRC32, schema version, total byte length, chunk count, chunk payload size |
| `SCHEMA_REQUEST` | deck → K1 | "send all" or a list of missing chunk indices |
| `SCHEMA_CHUNK` | K1 → deck | chunk index, 8-to-7-bit packed bytes |
| `SCHEMA_END` | K1 → deck | CRC32 of the reassembled blob |
| `SCHEMA_ACK` | deck → K1 | ok / crc-fail |

Rules: the deck caches by K1 identity + CRC and sends `SCHEMA_REQUEST` only when the CRC differs; chunk payload size is a parameter (BLE-MIDI packets are small — size it from the legacy decoder and the BLE-MIDI spec; default conservatively); reassembly has a timeout and re-requests missing chunks up to N times, then signals **fallback**; the deck's fallback is a built-in tier-1 schema constant so it always works; every buffer is bounded and every index range-checked.

## Repo rules you must follow

- Run `.claude/harness/init.sh` first and last.
- This brief names the active item: append **K1-DM-130 "SysEx schema transport library"** to `.claude/harness/feature_list.json` (append-only, protected; `python3 .claude/harness/harness.py validate`). Work it to `PASSING` or `BLOCKED`.
- `platformio.ini` is protected: pin, name the environments (`native_sysex_schema`, `native_sysex_schema_fuzz` with `-fsanitize=address,undefined`), keep flag order, regenerate build evidence.
- Append your session to `.claude/harness/agent-progress.md`.

## Read first

1. `AGENTS.md`, `docs/agent/AGENT_EXECUTION_STANDARD.md`, `.claude/harness/HARNESS_RULES.md`, `.claude/harness/PROTECTED_FILES.md`.
2. `contract/README.md` (freeze gate), `contract/bridge_protocol.{h,cpp,md}` and `test/test_bridge_protocol/test_main.cpp` — match their style exactly: fixed-width types, explicit version and byte order, explicit offsets, compile-time size checks, golden vectors, malformed cases.
3. The legacy BLE-MIDI decoder and the deck-state/identity documents.
4. `contract/control_schema_v1.md` if Handover C has landed.

## Deliverables

1. `contract/sysex_schema_v1.{h,cpp}` — encoder (K1 side) and decoder/reassembler (deck side). Portable C++ in the `contract/` style; `<cstdint>`/`<cstddef>` only; no heap, no exceptions, no RTTI; caller-supplied buffers. The header must compile unchanged in the Tab5 deck's build later, so no repo-internal includes beyond `contract/`.
2. 8-to-7-bit packing/unpacking with tests.
3. Host tests in `test/test_sysex_schema/`: happy path; lost chunk → request → recovery; reordered chunks; corrupted chunk (CRC fail → re-request); timeout → fallback; oversized blob rejected; golden encode/decode vectors committed; **fuzz test** feeding random bytes to the decoder — never reads or writes out of bounds, ≥ 100 000 iterations under the sanitiser environment.
4. Transfer-cost test: for the 71-record blob, print chunk count and estimated seconds at three assumed throughputs (state the assumptions). This tells Captain whether connect-time download is acceptable.
5. The built-in tier-1 fallback schema constant (mode, palette, photons, mood — the ratified Tier 1).
6. `contract/sysex_schema_v1.md` — the wire format, complete enough for a second engineer to write a compatible decoder without reading the code.

## Constraints

- No hardware. Host only. Integration into an S3 BLE stack and the Tab5 LVGL app is a later item, not this one.
- Do not add a GATT service or any second transport. Do not invent extra message types.
- Do not touch `hal/bridge_transport.h` or `contract/bridge_protocol.*` — the schema never crosses K1BR; the S3 gets the blob at build time (Handover C).
- British English.

## Acceptance

- All tests pass in `native_sysex_schema`; fuzz clean in `native_sysex_schema_fuzz`; both added to `init.sh`.
- Compiles with `-Wall -Wextra -Werror`.
- Golden vectors committed and regenerate identically.
- `.claude/harness/init.sh` green.

## Stop report (repo format)

Files changed; commands run; validation output; chunk size chosen and why; the transfer-cost table; anything in BLE-MIDI framing that forced a design change; blockers; exact next step.
