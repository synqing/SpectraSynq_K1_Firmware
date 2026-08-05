---
abstract: "F2 evidence (2026-07-08): NimBLE-Arduino 2.5.0 dual-role (central to K718 + peripheral GATT sync service to follower K1) on ESP32-S3 is supported and the flagship S3 dual-role bug (rc=519, issue #1016) is FIXED in the vendored 2.5.0 source (NimBLEDevice.cpp:923 sets ble_max_act=5). MAX_CONNECTIONS default 3; updateConnParams down to 7.5 ms; post-connect 2M PHY via updatePhy() without EXT_ADV. Estimated added heap ~4-10 KB against ~76 KB idle internal headroom; gate on internal_min_ever watermark, not idle free."
---

# F2 — NimBLE-Arduino 2.5.0 dual-role (central + peripheral) evidence

**Evidence question:** Can NimBLE-Arduino 2.5.0 on ESP32-S3 run a concurrent central link (K718 BLE-MIDI dial) plus a peripheral GATT sync service (follower K1) reliably, and at what cost?

**Short answer: YES, with a bounded and mostly-already-paid cost.** Dual-role is enabled by default in the vendored library, the one S3-specific dual-role showstopper (advertising fails with rc=519 after the central link connects) was root-caused upstream and the fix is verifiably present in the vendored 2.5.0 source. The connection-parameter and PHY levers the sync stream needs (7.5 ms floor, 2M PHY post-connect) exist in this exact version. Residual risk is not "does dual-role work" but (a) transient internal-heap dips under combined load — a documented K1 incident class — and (b) radio-time sharing, which belongs to the coexistence lane, not this one.

## 1. Vendored library identity

- NimBLE-Arduino **2.5.0** is the vendored version: `library.properties:2` (`version=2.5.0`) in `.pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino/`. [REPO .pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino/library.properties:2]
- Declared in `platformio.ini:302` and `:390` as `h2zero/NimBLE-Arduino@^2.5.0` (BLE demo env + remoted probe env). [REPO platformio.ini:302,390]
- Upstream changelog dates 2.5.0 at 2026-04-01; its fixes include `NimBLEClient` connection-state tracking and connection retry-on-establishment-failure (default 2 retries, app-configurable) — both directly useful for keeping the K718 link robust. [READ primary — h2zero/NimBLE-Arduino CHANGELOG.md (master)]

## 2. Role enables and connection limits (nimconfig.h, vendored)

All four GAP roles are **enabled by default** unless explicitly disabled:

- `CONFIG_BT_NIMBLE_ROLE_CENTRAL 1`, `ROLE_OBSERVER 1`, `ROLE_PERIPHERAL 1`, `ROLE_BROADCASTER 1` (each defaults to 1 unless a `*_DISABLED` macro is defined). [REPO .pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino/src/nimconfig.h:180-210]
- `CONFIG_BT_NIMBLE_MAX_CONNECTIONS` **default 3** (comment notes "esp controller max is 9"). [REPO nimconfig.h:224-226, :22-23]
- No role-disable or max-connection flags appear in `platformio.ini`, so the K1 BLE builds already compile with central+peripheral+broadcaster+observer all on and 3 connection slots. One is used by the K718 link; the follower K1 takes a second; one spare remains. [REPO platformio.ini:240-400]
- Host task: stack 4096 B, **pinned to Core 0 by default** (`CONFIG_BT_NIMBLE_PINNED_TO_CORE 0`, `HOST_TASK_STACK_SIZE 4096`). The NimBLE host task therefore shares Core 0 with the 133 Hz audio pipeline — priority/latency budgeting is a real (existing, not new) constraint; the second connection adds host-event work on that core. [REPO nimconfig.h:212-218]
- MSYS mbuf pool: 12 blocks x 256 B; maintainer guidance for dual-role memory pressure is to raise `CONFIG_BT_NIMBLE_MSYS1_BLOCK_COUNT` (see §4). [REPO nimconfig.h:253-261]
- Note: on ESP_PLATFORM `nimconfig.h` includes `sdkconfig.h` first, so precompiled arduino-esp32 values coexist; the precompiled S3 sdkconfig sets `CONFIG_BT_CTRL_BLE_MAX_ACT 6` and `CONFIG_BT_CTRL_PINNED_TO_CORE 0` (controller also Core 0). NimBLE-Arduino overrides the activity count at runtime (§3). [READ primary — ~/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/qio_opi/include/sdkconfig.h:836-840]

## 3. The S3 dual-role bug — found, fixed, and the fix is IN the vendored source

This is the decision-critical item. Upstream **issue #1016** ("ESP32-S3 dual-role (client + server) fails with rc=519 on all NimBLE-Arduino versions 2.3.x", opened 2025-08-24, closed 2025-09-02) reports exactly our topology: S3 as BLE central (client) + peripheral (server). After the client connects, re-enabling advertising fails with `rc=519, Memory Capacity Exceeded`. Reporter confirmed it is **S3-specific** (does not occur on original ESP32). Maintainer h2zero root-caused it and fixed it in **PR #1018** (merged 2025-09-02): on S3/C3 the controller is configured by *max activities*, which must count scanning and advertising as well as connections — the old code passed only `MAX_CONNECTIONS`, so the controller ran out of activity slots when advertising resumed alongside a live connection. [READ primary — github.com/h2zero/NimBLE-Arduino issues #1016, PR #1018 (API-fetched bodies, comments, and patch)]

The fix is verifiably present in the vendored 2.5.0 source:

```
bt_cfg.ble_max_act =
    MYNEWT_VAL(BLE_MAX_CONNECTIONS) + MYNEWT_VAL(BLE_ROLE_BROADCASTER) + MYNEWT_VAL(BLE_ROLE_OBSERVER);
```
i.e. **ble_max_act = 3 + 1 + 1 = 5** at `NimBLEDevice::init()`. [REPO .pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino/src/NimBLEDevice.cpp:923-924]

Maintainer's position on dual-role generally (issue #981, 2025-06-13): "Yes you can [use dual role, Peripheral and Central] … there is nothing special to consider just create the client and server instances and use them as you need." [READ primary — github.com/h2zero/NimBLE-Arduino issue #981]

### Known dual-role/concurrency caveats that remain (by design, not bugs)

- **Cannot initiate a connection while scanning, or scan while a connection attempt is in flight** — the NimBLE host returns `BLE_HS_EBUSY` (e.g. scan validation rejects when `ble_gap_conn_active()`; connect rejects when discovery is active). The K1's existing central code already respects this: the scan callback stops the scan (`NimBLEDevice::getScan()->stop()`) before attempting connection. Sequencing scan/connect/advertise from one state machine is required — which the current `ble_task` structure already is. [REPO NimBLE src nimble/host/src/ble_gap.c:6120-6135; REPO SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp:109-121, 204-224]
- **Advertising + two live connections concurrently is within the 5-activity budget** (2 conns + 1 adv + spare); steady-state dual-role after both links are up does not contend for activity slots.
- Historical S3 crash reports (scan-continuous panics #636, arduino-core 3.x crashes #676/#686) date from the NimBLE 1.4.x / early core-3.x era and are superseded by the 2.x line the K1 vendors; they are context, not live risks. [SEARCH snippet — github issue titles/summaries, not re-verified line-by-line]

## 4. Levers the sync stream needs — present in 2.5.0

- **`updateConnParams(minInterval, maxInterval, latency, timeout)`** exists on both `NimBLEClient` (for the K718 link) and `NimBLEServer` (per-connHandle, for the follower link). Units are documented in-source as **1.25 ms**; the BLE-spec floor of 6 units = **7.5 ms** applies (host/controller enforce spec ranges). So a 7.5-15 ms connection interval on the sync link is API-reachable. [REPO NimBLEClient.cpp:519-543 (doc comment "in 1.25ms units" + `ble_gap_update_params`); NimBLEServer.h:69]
- **2M PHY:** `updatePhy(txPhyMask, rxPhyMask, phyOptions)` and `getPhy()` are compiled **unconditionally** on both client and server (they call `ble_gap_set_prefered_le_phy` post-connect). Only `setConnectPhy()` (choosing the PHY to *initiate* on) is gated behind `CONFIG_BT_NIMBLE_EXT_ADV`, which is off by default. Practical path: connect on 1M, immediately request 2M — no EXT_ADV needed. [REPO NimBLEClient.h:99-103 (`# if CONFIG_BT_NIMBLE_EXT_ADV` closes before `updatePhy`); NimBLEClient.cpp:437-470; NimBLEServer.cpp:955-978]
- **ESP32-S3 controller supports 2 Mbps PHY and Coded PHY** (Bluetooth 5 LE). [READ primary — espressif.com ESP32-S3 product page: "higher transmission speed and data throughput, with 2 Mbps PHY"]
- **`setDataLen()`** (DLE, up to 251 B payloads) also present on both roles — our 60-100 B sync packets fit a single DLE PDU. [REPO NimBLEClient.cpp:552-565; NimBLEServer.h:83]
- ATT preferred MTU default 255. [REPO nimconfig.h:245-247]

## 5. Heap cost of the second connection + advertising set

Baseline: the bench BLE build's own telemetry comment records **~76 KB idle internal-RAM headroom**, with a known **transient-dip abort** under combined load (BLE link + notify stream + WiFi-AP client + cal-complete `fopen`) — i.e. the watermark (`internal_min_ever`), not idle free, is the binding number. [REPO SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp:272-285]

What the second role actually adds, given the current build already initialises the full stack:

| Item | Cost | Basis |
|---|---|---|
| Controller activity memory (ble_max_act=5) | **0 (already paid)** | Set at `NimBLEDevice::init()` regardless of how many links are used; current central-only build initialises identically [REPO NimBLEDevice.cpp:923-924] |
| Host connection pool (3 slots) | **0 (static BSS, already sized)** | `ble_hs_conn_elem_mem` is a compile-time `os_membuf_t` array sized by `BLE_MAX_CONNECTIONS` [REPO nimble/host/src/ble_hs_conn.c:34-36, 581-583] |
| MSYS mbuf pool (12 x 256 B) | **0 (allocated at init)**; +~3.5 KB **if** raised to 24 per maintainer's dual-role guidance in #1016 | [REPO nimconfig.h:253-261; READ primary — issue #1016 comments] |
| `NimBLEServer` + 1 GATT service + 2-3 characteristics + CCCD | ~1-3 KB heap | Order-of-magnitude from object sizes/att value allocs (default 20 B init length, nimconfig.h:33-39); not device-measured |
| Legacy advertising set (31 B adv + 31 B scan-rsp) | <0.5 KB | Legacy adv, no EXT_ADV pools |
| Transient during connect/GATT discovery by follower | ~2-4 KB peak | mbuf/proc churn; transient, returns to pool |

**Estimated steady-state added heap: ~2-4 KB; worst-case budget including an MSYS bump: ~10 KB — against ~76 KB idle headroom.** It fits with margin on paper, but the documented transient-dip incident class means the go/no-go must be the measured `internal_min_ever` watermark under worst-case load (dual-role + notify stream + K718 linked + sync stream at 33 Hz), which the existing 1 Hz heap telemetry already prints. The estimate rows marked "order-of-magnitude" are the only non-primary numbers in this file; everything else is source-verified.

## 6. What this does NOT cover

- Radio-time sharing between BLE connection events and any WiFi/ESP-NOW duty, and Core-0 ISR load versus the 7.5 ms audio frame budget — the coexistence lane's question. This file establishes only that the BLE host/controller *configuration* supports the topology.
- On-device proof. No device was touched (read-only lane). The Phase-0 bench measurement (dual link up, 33 Hz notify stream, K718 uptime soak, `internal_min_ever` watermark) remains the closing gate.

## Verdict input

NimBLE-Arduino 2.5.0 as vendored supports the leader-K1 dual-role topology out of the box: all roles enabled, 3 connection slots (2 needed), and the one S3-specific dual-role failure (rc=519 on advertising with a live central link) is fixed in this exact version — verified in the vendored source line, not just the changelog. Connection-interval floor 7.5 ms and post-connect 2M PHY are reachable through the public API without enabling extended advertising. Added memory is small (~2-10 KB) against ~76 KB idle headroom, but the K1's own incident history says transient watermark, not idle free, decides — keep `internal_min_ever` as a hard Phase-0 gate. The K718-link-degradation risk is not a stack-capability risk; it is a radio-scheduling and Core-0 load risk, owned by the coexistence evidence lane.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (F2-EVIDENCE SSA) | Created — NimBLE 2.5.0 dual-role evidence: vendored-source verification (nimconfig.h, NimBLEDevice.cpp #1018 fix, PHY/connparams API), upstream issues #1016/#981/PR #1018, heap-cost estimate vs ~76 KB headroom |
