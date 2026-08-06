---
abstract: "End-to-end map of the K1's existing BLE MIDI capability (evidence for the dual-K1 sync transport decision, 2026-07-08): NimBLE-Arduino 2.5.0 Apple BLE-MIDI, K1 is CENTRAL-ONLY (no peripheral/server role exists in K1 firmware), bench/demo envs only (k1_ble_remoted_probe, k1_bench_im73d_ble, k1_custom) — production k1_hardware is radio-free. 71-control CC/PC/NRPN map, RX timestamps discarded, no MTU/conn-interval tuning on either side, no measured link latency/jitter anywhere, BLE app task + NimBLE host both on Core 0 with the audio pipeline (DRAM crash materialised 2026-07-05, guarded by 1ac840a). Interference A/B still open."
---

# BLE MIDI capability map — evidence for the dual-K1 sync transport decision

Status: research evidence only. No design decisions made here. Default posture was refutation; every claim below carries a file:line or document citation that was actually read.

## (a) Stack, profile, and build environments

- **Stack:** NimBLE-Arduino `h2zero/NimBLE-Arduino@^2.5.0` (`platformio.ini:302`, also `:390` for the probe env). Resolved lib copies exist under `.pio/libdeps/k1_ble_remoted_probe/` and `.pio/libdeps/k1_bench_im73d_ble/`.
- **Profile:** standard Apple BLE-MIDI — service `03B80E5A-EDE8-4B33-A751-6CE34EC4C700`, characteristic `7772E5DB-3868-4112-A1A9-F2669D106BF3` (`SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp:38-39`).
- **Envs that compile BLE** (all gated by `-DSB_K1_BLE_REMOTED`; the two BLE TUs are added by `build_src_filter`):
  - `k1_ble_remoted_probe` (`platformio.ini:378-391`) — interference A/B ON-condition; extends the diag harness. NON-SHIPPABLE.
  - `k1_bench_im73d_ble` (`platformio.ini:291-302`) — investor-demo build; extends `k1_bench_im73d` (bench GPIO + IM73D PDM mic), pointedly NOT the harness. NON-SHIPPABLE.
  - `k1_custom` (`platformio.ini:261-265`) — 224-LED wall build; extends `k1_bench_im73d_ble`, so it inherits BLE. NON-SHIPPABLE.
- **Production is radio-free.** `k1_hardware` includes neither BLE TU nor NimBLE (`platformio.ini:44` src filter has no `network/` entries; header block `ble_remoted_central.cpp:6-8` states production never sees this TU). Radio-isolation guard passed in the prior lane (`artifacts/ble_midi_71_20260628/README.md:16`; `logs/k1_radio_isolation_guard.log`). "NON-SHIPPABLE: BLE radio present; production stays radio-free until the A/B clears" (`platformio.ini:288`).
- **No WiFi+BLE env exists.** WiFi lives only in `k1_wireless_ab_probe` (`platformio.ini:353-366`, WebSockets, no NimBLE); the BLE envs pull no WiFi/WS stack (`platformio.ini:375-377`). Coexistence of both radios has never been built or tested in this repo.

## (b) GATT roles — central-only; K1-to-K1 needs new code

- The K1 is a **BLE central (GATT client) only**: it scans, connects, and subscribes to the peripheral's notifications (`ble_remoted_central.cpp:105-181`, `NimBLEDevice::createClient()` at `:156`). Init is `NimBLEDevice::init("K1-Remoted-RX")` (`:234`); **no `createServer()`, no advertising, no peripheral role anywhere in K1 firmware** (grep of `SPECTRASYNQ_K1_FIRMWARE/` finds server/advertising code only in the knob repo).
- The **peripheral half is the K718 Remoted dial**, a separate device in a sibling repo: `~/Workspace_Management/Software/JC3636K518CN_knob_EN-bleremote/custom/JC3636_K718_REMOTED_BLE_V1/ble_midi_peripheral.cpp` (NimBLE 2.x server, `createServer()` at `:49`, advertises the BLE-MIDI service, `advertiseOnDisconnect(true)` at `:50`).
- Scan match is by name `"SpectraSynq Remoted"` **or** by advertised BLE-MIDI service UUID (`ble_remoted_central.cpp:110-112`). One connection target; single-link design (`s_client`, `s_rx_char` singletons, `:51-52`).
- **Could one K1 be central to another K1?** Not today: neither K1 build contains a peripheral/server, so there is nothing for a second K1 to connect to. NimBLE-Arduino 2.x supports both roles simultaneously (the knob proves the peripheral side compiles fine on ESP32-S3 with the same lib), so a K1-peripheral role is *feasible* but is **net-new firmware**, not a piggyback. It was built for dial→K1 control (a phone/DAW pairing shape), not device-to-device.
- **Return path exists:** the K1 central WRITEs to the same characteristic to report confirmed modes back to the knob (`ble_remoted_central.cpp:183-202`; knob-side `onWrite` handler `ble_midi_peripheral.cpp:35-41`). So bidirectional traffic over one characteristic is already proven on-silicon.

## (c) Message set, framing, timestamping

- **Framing (RX):** Apple BLE-MIDI packet = header byte (bit7 set) + timestamp byte (bit7 set), then a run of MIDI messages (`k1_ble_midi_decoder.cpp:274-320`). Only **Programme Change** (2 bytes) and **Control Change** (3 bytes) statuses are decoded; anything else marks the packet MALFORMED. **No running status, no SysEx, no mid-packet timestamp bytes** — a sender inserting per-message timestamps (which the BLE-MIDI spec allows) would trip the MALFORMED path and the central then **discards the whole packet's records** (`ble_remoted_central.cpp:83-86`).
- **Timestamps are discarded on RX.** The decoder validates the two framing bytes then never reads the 13-bit timestamp; records carry no time. On TX the K1 encodes `millis() & 0x1FFF` into header+timestamp (`ble_remoted_central.cpp:194-200`). **There is no clock-sync or latency-compensation machinery anywhere** — load-bearing gap for frame-locked dual-K1 rendering.
- **Message set:** a generated 71-control map (`network/k1_ble_midi_map.h:9`, auto-generated from `docs/protocol/k1-ble-midi-map.json`, registry md5 `78fb9af986da36922fae33cb09de3b4b`, `:4,11`). Encodings: PC = mode select; CC14 (MSB/LSB pairs) = continuous params; CC7 bool/enum; NRPN (CC99/98/6/38, `k1_ble_midi_decoder.cpp:13-16`) = presets/edge-mode/scene/calibration. Calibration entries carry `K1MIDI_FLAG_COMMAND | K1MIDI_FLAG_PROTECTED_APPLY` (`k1_ble_midi_map.h:108-111`) — the silence gate survives the radio path.
- **Apply path:** notify → `k1_ble_midi_decode_packet` → static FreeRTOS queue (16 records, `ble_remoted_central.cpp:44`) → main-loop `sb_k1_ble_remoted_poll()` (`SPECTRASYNQ_K1_FIRMWARE.ino:819`) → `sb_k1_control_apply()` → `CONFIG.*` (path verified in `docs/hardware/im73d-ble-midi-demo-build-2026-07-04.md:48`).
- **Limits:** `K1_BLE_MIDI_MAX_PACKET 247`, `K1_BLE_MIDI_MAX_RECORDS_PER_PACKET 16` (`k1_ble_midi_decoder.h:10-11`); K1→knob confirm packet is a fixed 8 bytes carrying two CC messages (CC 0x20/0x21, `ble_remoted_central.cpp:42-43,195-200`).

## (d) Measured throughput / latency / jitter from the prior lane

- **Delivery-integrity numbers exist; link latency/jitter numbers do NOT.** Phase G device proof (2026-06-28, `artifacts/ble_midi_71_20260628/phase_g_device_proof/20260628_1529/ab_ble_active_summary.json`): knob sent 268 items (71-control sweep + stress), K1 counters `notify=268 decoded=268 enqueued=268 apply_ok=268, queue_drops=0 decode_errors=0 apply_fail=0` over a 20.6 s treatment capture (~13 msg/s average — a functional sweep, not a saturation test).
- The only timing measurement is the **1 Hz AP heartbeat cadence** as an interference proxy: control mean 1005.06 ms / p95 1008.67 ms / max 1009.73 ms vs BLE-active treatment mean 893.43 ms / p95 1013.76 ms / max 1014.66 ms — with the explicit claim limit "Scalar AP cadence comparison only; no causal RF attribution" (same JSON, `claim_limit`).
- The **2.4 GHz interference A/B is unresolved** — `"ble_interference_ab": "DEVICE_BLOCKED"` (`phase_g_device_proof/20260628_1529/final_manifest.json`, gate_summary; the K718 stopped booting during the final rerun). Still open as of the 2026-07-04 demo doc (`im73d-ble-midi-demo-build-2026-07-04.md:14`).
- Grep of the artefact tree and docs for latency/jitter of the BLE link itself: **no such measurement exists**. Any <50 ms audio-to-LED sync budget claim over this transport is currently unsubstantiated.

## (e) Coexistence with Core 0 audio and Core 1 render

- **BLE app task: Core 0, priority 1, 4096-word stack**, 150 ms scan/connect loop — `xTaskCreatePinnedToCore(ble_task, "ble_remoted", 4096, nullptr, 1, &s_task, 0)` (`ble_remoted_central.cpp:235`). **NimBLE host task also defaults to Core 0**: `CONFIG_BT_NIMBLE_PINNED_TO_CORE 0` (`.pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino/src/nimconfig.h:212-213`); no override in the repo.
- The audio pipeline runs in the Arduino loop task pinned to Core 0 (`-DARDUINO_RUNNING_CORE=0`, `platformio.ini:60-63`) and the LED task on Core 1 (`-DSB_K1_LED_TASK... -DSB_LED_TASK_CORE=1`, `platformio.ini:67`). So **radio, host stack, and hard-real-time audio all share Core 0** in the BLE builds.
- Decode work happens in the NimBLE notify callback (Core 0); apply happens in the main loop via the queue — no mutexes added to the audio path (static queue, non-blocking sends, drops counted, `ble_remoted_central.cpp:92-98`).
- **The Core-0 contention risk materialised on-silicon (2026-07-05):** first accepted noise-cal aborted inside `fopen()` because BLE left internal DRAM tight (newlib lock alloc failed) → hard reboot. Fixed by an internal-RAM precondition guard, commit `1ac840a` (`im73d-ble-midi-demo-build-2026-07-04.md:76-82`). 1 Hz heap telemetry was added behind `:ble_stream=on` (`ble_remoted_central.cpp:29-32,261-286`).
- **No radio-coexistence flags anywhere:** no sdkconfig files in the repo, no `CONFIG_SW_COEXIST*`/coexistence build flags (grep of `platformio.ini` + firmware tree: zero hits). Moot today because no env combines WiFi and BLE.
- Standing prohibition: **never measure mic SNR on BLE builds** (`platformio.ini:279-281`; `im73d-ble-midi-demo-build-2026-07-04.md:14`) — radio load can perturb audio timing and the A/B is open.

## (f) MTU and connection-interval settings

- **None configured, either side.** Grep for `setMTU` / `updateConnParams` / `setConnectionParams` / interval settings across `SPECTRASYNQ_K1_FIRMWARE/` and the knob sketch (`ble_midi_peripheral.cpp`, `JC3636_K718_REMOTED_BLE_V1.ino`): zero hits. Both ends run NimBLE-Arduino defaults — `CONFIG_BT_NIMBLE_ATT_PREFERRED_MTU 255` (`nimconfig.h:245-246`) and stack-default connection interval. The decoder's 247-byte packet cap (`k1_ble_midi_decoder.h:10`) and the knob's 245-byte MIDI payload cap (`ble_midi_peripheral.cpp:23-24`) are application-side, not negotiated values.
- Consequence for dual-K1 sync: connection interval (the dominant BLE latency term) is currently whatever the NimBLE/controller defaults negotiate; it has never been tuned or measured. Any latency-critical design must set and verify it explicitly.

## Numbers

| Quantity | Value | Source |
|---|---|---|
| NimBLE-Arduino version | ^2.5.0 | platformio.ini:302 |
| BLE-MIDI controls in map | 71 (+21 text values) | k1_ble_midi_map.h:9-10 |
| Max RX packet / records per packet | 247 B / 16 | k1_ble_midi_decoder.h:10-11 |
| Cmd queue capacity | 16 records, static | ble_remoted_central.cpp:44-48 |
| BLE app task | Core 0, prio 1, 4096 stack, 150 ms loop | ble_remoted_central.cpp:222,235 |
| NimBLE host task core | 0 (default) | nimconfig.h:212-213 (libdeps) |
| Preferred ATT MTU (default) | 255 | nimconfig.h:245-246 (libdeps) |
| Phase G sweep delivery | 268/268/268 applied, 0 drops, 0 errors | ab_ble_active_summary.json |
| Treatment capture duration | 20.62 s (~13 msg/s avg) | ab_ble_active_summary.json |
| AP heartbeat p95, control vs BLE-on | 1008.7 ms vs 1013.8 ms | ab_ble_active_summary.json |
| Demo firmware size / RAM / Flash | 912,224 B / 38.0% / 13.9% | im73d-ble-midi-demo-build-2026-07-04.md:52,56 |
| Production (radio-free) firmware size | 647,888 B | ble_midi_71_20260628/README.md:37 |
| K1→knob confirm packet | 8 B, 2×CC, 13-bit millis timestamp | ble_remoted_central.cpp:194-200 |
| LEDs per channel (verifies brief) | 160 native (NATIVE_RESOLUTION 160); dual-channel per K1; 224 only in k1_custom | system/constants.h:109; system/config_types.h:132-140 |

## Risks (for the transport decision)

1. **Central-only today.** K1-as-peripheral is net-new firmware; "piggyback" overstates readiness — the reusable parts are the NimBLE dependency, the decoder, the map/codegen tooling, and the queue/apply pattern.
2. **No timing substrate.** RX timestamps discarded, no clock sync, no measured link latency/jitter — the entire timing story for a widened synchronised display is unbuilt and unmeasured.
3. **Core-0 contention is real, not theoretical.** DRAM-exhaustion crash materialised 2026-07-05; audible-dropout risk under heavy BLE traffic is documented and unresolved; the interference A/B is DEVICE_BLOCKED/open.
4. **Production is deliberately radio-free** pending the A/B — dual-K1 BLE sync would break that gate for shipping firmware, a Captain-level product decision.
5. **Decoder brittleness for new senders:** packets containing mid-message timestamp bytes, running status, or non-PC/CC statuses are dropped whole — a K1→K1 protocol must either conform to the narrow subset or extend the decoder.
6. **Single-link design:** the central manages exactly one client/characteristic; multi-peer topologies need restructuring.

## Open questions

- What connection interval do the two NimBLE ends actually negotiate on-silicon (drives worst-case one-way latency)? Never logged.
- Can BLE (radio on Core 0) meet the <50 ms audio-to-LED budget with margin on BOTH units simultaneously? No evidence either way.
- Is WiFi (already used for Tab5 control, ESP-NOW-capable hardware) a stronger sync transport? Out of this file's scope but the coexistence question (BLE+WiFi never built together) bounds any combined design.
- Does the K718 dial need to keep its link while two K1s also link to each other (3-node topology)? Current code supports exactly one link.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-fable-5 (SSA research) | Created — end-to-end BLE MIDI capability map for the dual-K1 sync transport evaluation; all claims cited to file:line or documents read this session. |
