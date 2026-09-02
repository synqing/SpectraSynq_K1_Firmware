# HANDOVER C — One descriptor table: generated BLE-MIDI map, tiers, schema blob

**Project folder:** `/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-K1-DualMCU-Firmware`
**Read-only input:** `/Users/spectrasynq/SpectraSynq_K1_Firmware` — `SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_map.h`, `docs/protocol/k1-ble-midi-map.json`, `docs/protocol/k1-ws-controls-registry.yaml`, `docs/protocol/protocol-map-hashes.json`, `scripts/regression-harness/golden/oracle_ble_midi_map.py`, `oracle_ble_midi_diff.py`. Never edit that repo.
**Agent:** Claude Code or Codex, one session, one branch (`lane/k1-dm-120-control-schema`).

---

You are the control-plane engineer for the SpectraSynq K1 DualMCU firmware. Control authority lives on the **RT1062** (`core/control/`). The ESP32-S3 is a radio-only bridge and must never hold control policy (`AGENTS.md`; `HARNESS_RULES.md` rule 11 — violating it is an immediate failure).

Today the controls are described in three places: `core/control/control_catalogue.cpp` (71 `ControlDescriptor` rows: id, path, value type, consumer), `contract/product/control_map_v1.json` (71 rows generated from the legacy header by `scripts/import_legacy_product_catalogues.py`, gated by `harness/check_product_catalogues.py`), and the frozen legacy registry (`kFrozenControlRegistryMd5`). None of them carries what the Tab5 deck needs to draw a control: label, widget kind, tier, step, default. The deck is blocked on "registry v2" for exactly that reason.

Your job: make **one table in `core/control/` the source of truth**, generate the map and a schema blob from it, and prove the generated map is identical to today's.

## Design (fixed; do not redesign)

Extend `ControlDescriptor` in place — do not add a parallel table:

```cpp
struct ControlDescriptor final {
  std::uint8_t id;                    // existing
  const char* path;                   // existing — stable persistence key, never renamed once shipped
  bridge::ControlValueType value_type;// existing
  ControlConsumer consumer;           // existing
  const char* label;                  // UI label, ≤ 31 chars
  ControlUi ui;                       // kSlider | kToggle | kSelect | kMode | kNone
  std::uint8_t tier;                  // 1 always shown, 2 page 2, 0 hidden/system
  float minimum, maximum, step, initial;
  Provenance provenance;              // the frozen registry's label set, unchanged
};
```

Every operation is **one loop over the table**: clamp, set-by-path, get-by-path, save (path-keyed, caller-supplied buffer), load (path-keyed), emit-map-JSON, emit-schema-blob. No per-control code anywhere else.

## Repo rules you must follow

- Run `.claude/harness/init.sh` first and last.
- This brief names the active item: append **K1-DM-120 "Descriptor-table control schema: one source for map, tiers and schema blob"** to `.claude/harness/feature_list.json` (append-only, protected; `python3 .claude/harness/harness.py validate`). Work it to `PASSING` or `BLOCKED`.
- `platformio.ini` is protected: pin, name the environment (`native_control_schema`), keep flag order, regenerate build evidence.
- No behaviour change to any control's semantics. If you believe one is needed, it goes in `docs/plans/deferred-upgrade-register.md` and stops there.
- Append your session to `.claude/harness/agent-progress.md`.

## Read first

1. `AGENTS.md`, `docs/agent/AGENT_EXECUTION_STANDARD.md`, `.claude/harness/HARNESS_RULES.md`, `.claude/harness/PROTECTED_FILES.md`.
2. `core/control/control_catalogue.{h,cpp}`, `core/control/bridge_command_processor.{h,cpp}`, `contract/bridge_protocol.h` (`ControlValueType`, `kControlMapEntries`), `contract/product/control_map_v1.json`, `scripts/import_legacy_product_catalogues.py`, `harness/check_product_catalogues.py`, `firmware/s3_bridge/README.md`.
3. Legacy protocol files listed above — for label, tier, step and default values, and for how `oracle_ble_midi_map.py` derives the golden.

## Deliverables

1. Extended `ControlDescriptor`, all 71 rows populated (labels, widget kinds, tiers, ranges, steps, defaults, provenance) from the legacy registry; the seven loops; bounded buffers everywhere (no unchecked `strcat`/`snprintf` into fixed arrays). Tier 1 is the ratified set: mode, palette, photons, mood. Everything else tier 2 unless the legacy registry marks it hidden/system.
2. Generator `scripts/generate_control_map.py` (or C++ emitter run by a native environment) producing `control_map_v1.json` **from the table**. It must reproduce the current file's 71 rows exactly — `harness/check_product_catalogues.py` and `catalogue_sha256` stay green with no change to the JSON. Any field that cannot be reproduced: list it and why, do not alter the check.
3. Path-keyed persistence host test: save the table, **add a control**, reload, every pre-existing value survives. (Offset-keyed presets — the ancestor's failure mode — cannot pass this.)
4. Schema blob `contract/control_schema_v1.{h,cpp}` + `contract/control_schema_v1.md`: little-endian, versioned header, per-record fixed layout, CRC32 trailer, explicit byte offsets, compile-time size checks (the contract README's freeze-gate items 1–4). A build-time generated `contract/product/control_schema_v1_blob.h` (bytes + CRC) that **both** images compile in — the S3 carries it as static data for Handover D to broadcast; no new K1BR message type, the 13 frozen types stay frozen. Report blob size for 71 records.
5. Host unit tests for every loop, in `test/test_control_schema/`, run by `native_control_schema` and added to `init.sh`.

## Constraints

- No hardware. Host only.
- Do not change any control's path, CC, NRPN, range or flags. The 71 are frozen inputs. If the 68-control registry and the 71-row map disagree, report the reconciliation; do not reinterpret.
- Do not put policy, clamping or defaults on the S3 side. Data only.
- Do not port the legacy serial menu.
- British English.

## Acceptance

- `check_product_catalogues.py` green with `control_map_v1.json` byte-identical (or every difference listed).
- Add-a-control persistence test passes.
- Blob round-trips (serialise → parse → identical table) and its CRC catches a single flipped bit.
- `check_architecture_ownership.py` and `check_s3_radio_only_image.py` still green with the blob header included in the S3 image. If either gate rejects static data, report — do not weaken the gate.
- `.claude/harness/init.sh` green.

## Stop report (repo format)

Files changed; commands run; validation output; the JSON diff result; blob size in bytes; anything in the frozen registry the descriptor shape could not express; blockers; exact next step.
