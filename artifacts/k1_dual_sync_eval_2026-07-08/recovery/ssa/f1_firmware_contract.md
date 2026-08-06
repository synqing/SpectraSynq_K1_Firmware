# SSA F1 firmware contract

Task: `dual-sync-f1-fw-003`  
Status: `NOT_VERIFIED` until the amended sources pass the focused tests and all four wrapper builds below.  
Scope: source/API/build/identity contract only; no firmware, device, serial, commit or push action was performed.

## Verdict

The proposed F1 implementation is not executable as written. The new
`k1_sync_probe_main_sync_only` environment removes `SB_K1_BLE_REMOTED` and its
translation units, but the proposed `.ino` branch still calls
`sb_k1_ble_remoted_begin()`, and the current leader SyncLink translation unit
still declares/calls `sb_k1_ble_remoted_is_linked()` for every leader. That
produces a compile failure in the sketch and, if the sketch call alone is fixed,
an undefined reference from `k1_sync_link.cpp`.

The installed dependency is exactly NimBLE-Arduino 2.5.0:
`.pio/libdeps/k1_sync_probe_{main,bench}/NimBLE-Arduino/library.properties:2`.
The API contract below is taken from those installed headers and sources, not
from assumed upstream behaviour.

## Exact compile and symbol changes

### `SPECTRASYNQ_K1_FIRMWARE.ino`

Current includes are already correctly independent:

- Remoted header: lines 58-60, under `SB_K1_BLE_REMOTED`.
- SyncLink header: lines 61-63, under `SB_K1_SYNC_PROBE`.

Replace the setup ordering at lines 680-685 with independent feature gates:

```cpp
#if defined(SB_K1_SYNC_PROBE) && defined(K1_SYNC_ROLE_LEADER)
  k1_sync::begin();
#endif
#ifdef SB_K1_BLE_REMOTED
  sb_k1_ble_remoted_begin();
#endif
#if defined(SB_K1_SYNC_PROBE) && defined(K1_SYNC_ROLE_FOLLOWER)
  k1_sync::begin();
#endif
```

This has the required order for the dual-role leader, compiles the sync-only
leader without a Remoted symbol, preserves the Remoted-only build, and starts
the follower exactly once. Do not use the proposed branch that unconditionally
calls Remoted for every sync leader.

The loop calls at lines 824-829 are already independently gated and need no
ordering change.

### `network/k1_sync_link.cpp`

Guard both the declaration at lines 40-44 and the health call at lines 593-596
with:

```cpp
#if defined(K1_SYNC_ROLE_LEADER) && defined(SB_K1_BLE_REMOTED)
```

For a sync-only leader, emit `role=leader dial_linked=0`; the Case-A manifest
must classify dial as not applicable rather than evaluating zero as failure.
Do not introduce a stub symbol or compile the Remoted translation unit into
Case A.

Check `NimBLEDevice::init()` and `NimBLEDevice::setMTU()` boolean returns.
Check `xTaskCreatePinnedToCore()` against `pdPASS` in the follower and Remoted
begin paths. A failed init, preferred-MTU set, or task creation must emit a
diagnostic and leave the affected subsystem not-ready.

Split physical connection from application-ready state:

- add `s_connected` for the raw GAP connection;
- retain `s_linked` for usable SyncLink;
- leader sets `s_connected` in `ServerCB::onConnect`, but sets `s_linked` and
  emits `link up role=leader` only after `onSubscribe` has observed notify
  subscriptions on both stream and clock characteristics;
- follower sets `s_connected` in `ClientCB::onConnect`, but sets `s_linked` and
  emits its `link up` only after both `subscribe()` calls return true;
- reset counters/sequence state at application-ready transition, not raw GAP
  connect, and clear both states on disconnect.

NimBLE 2.5.0 exposes
`NimBLECharacteristicCallbacks::onSubscribe(..., uint16_t subValue)` at
`NimBLECharacteristic.h:292-300`; use it. Without this split, the leader begins
33 Hz transmit and link-gated GPIO immediately on GAP connect, before the
follower has discovered characteristics or installed CCCDs. Those records can
pollute the very epoch F2 calls Link Ready.

The dual-role leader needs two simultaneous links: central→K718 and
peripheral←follower. The installed `nimconfig.h` resolves
`CONFIG_BT_NIMBLE_MAX_CONNECTIONS` to 3 in this build, but make that dependency
fail closed in the leader translation unit:

```cpp
#if defined(K1_SYNC_ROLE_LEADER) && defined(SB_K1_BLE_REMOTED)
static_assert(CONFIG_BT_NIMBLE_MAX_CONNECTIONS >= 2,
              "dual-role sync leader requires at least two BLE connections");
#endif
```

### `network/ble_remoted_central.cpp`

Replace the software scan latch at lines 204-223 with the live controller
state:

```cpp
if (!s_linked && !s_have_target && !scan->isScanning()) {
  const bool started = scan->start(0, false);
  Serial.printf("[ble_remoted_diag] scan_start ok=%u active=%u\n",
                started ? 1U : 0U, scan->isScanning() ? 1U : 0U);
  if (!started) {
    vTaskDelay(pdMS_TO_TICKS(500));
  }
}
```

Apply the same pattern in the follower SyncLink scan loop. NimBLE 2.5.0
`NimBLEScan::start(uint32_t, bool, bool)` returns true for both `0` and
`BLE_HS_EALREADY`; `isScanning()` is the independent active-state read-back
(`NimBLEScan.cpp:520-595`).

There is also a pre-existing core-ownership conflict that F1 must not silently
ratify: the Remoted application task is pinned to Core 0 at
`ble_remoted_central.cpp:235`, while its loop performs connect/discovery work
and the repository assigns hard-real-time audio to Core 0. Default resolution:
pin this low-priority application task to Core 1 and retain the existing
non-blocking main-loop queue drain. If that is rejected, record an explicit
probe-only exemption and do not claim Core-0 non-interference before the real AP
profiler exists. NimBLE's own host-task placement is a separate library/runtime
constraint.

For SyncLink discovery, implement `onDiscovered()` and `onResult()` as thin
calls to one idempotent `consider()` function. Match the service UUID, not the
name. `onDiscovered` receives the advertisement before scan-response completion;
the 128-bit service UUID must therefore remain in advertising data, while the
name may live in scan-response data.

### `platformio.ini`

Pin all three sync environments to
`h2zero/NimBLE-Arduino@2.5.0` (remove `^` at current lines 433 and 447).
Add:

```ini
[env:k1_sync_probe_main_sync_only]
extends = env:k1_hardware_harness
build_src_filter =
    ${env:k1_hardware_harness.build_src_filter}
    +<network/k1_sync_link.cpp>
build_flags =
    ${env:k1_hardware_harness.build_flags}
    -DSB_K1_SYNC_PROBE
    -DK1_SYNC_ROLE_LEADER
lib_deps =
    ${env:k1_hardware.lib_deps}
    h2zero/NimBLE-Arduino@2.5.0
```

The environment must not contain `SB_K1_BLE_REMOTED`,
`ble_remoted_central.cpp`, or `k1_ble_midi_decoder.cpp`.

## NimBLE-Arduino 2.5.0 API truth table

| Operation | API return | What it proves | Honest negotiated proof |
|---|---|---|---|
| Initialise host | `NimBLEDevice::init(name) -> bool` | Host initialisation completed | `isInitialized()` may be logged as read-back |
| Preferred local MTU | `NimBLEDevice::setMTU(247) -> bool` | Local preference accepted | `onMTUChange` or peer/client `getMTU()` |
| Enable scan response | `adv->enableScanResponse(true) -> void` | Nothing returnable | Log `configured=1`; never assign its result |
| Add service UUID | `adv->addServiceUUID(...) -> bool` | Advertising-data insertion succeeded | Discovery plus service lookup |
| Set advertised name | `adv->setName(...) -> bool` | Name inserted/truncated successfully | Name is diagnostic only |
| Start advertising | `adv->start() -> bool` | Start call accepted | `adv->isAdvertising()` is immediate active read-back |
| Start scanning | `scan->start(0, false) -> bool` | Start/already-active accepted | `scan->isScanning()` |
| Connect client | `client->connect(...) -> bool` | Connection procedure succeeded | `getConnInfo()`, then service/characteristic/subscription checks |
| Request client parameters | `client->updateConnParams(...) -> bool` | Request accepted only | Later `client->getConnInfo()` interval/latency/timeout |
| Request server parameters | `server->updateConnParams(...) -> void` | No success result | `ServerCB::onConnParamsUpdate(NimBLEConnInfo&)` |
| Request client PHY | `client->updatePhy(...) -> bool` | Request accepted only | `ClientCB::onPhyUpdate(...)` or `getPhy()` |
| Request server PHY | `server->updatePhy(...) -> bool` | Request accepted only | `ServerCB::onPhyUpdate(...)` or `getPhy()` |
| Request client DLE | `client->setDataLen(251) -> bool` | Request accepted only | Not exposed as negotiated octets by this public callback API |
| Request server DLE | `server->setDataLen(handle, 251) -> void` | No success result | Not exposed as negotiated octets by this public callback API |
| Notify | characteristic `notify(...) -> bool` | Stack accepted this notification | Count failures; it does not prove peer application |
| Clock write | remote characteristic `writeValue(...) -> bool` | Stack accepted this write | Response sequence proves peer processing |

Relevant installed declarations:

- `NimBLEAdvertising.h:54-82`: advertising return types; scan-response enable is
  `void`.
- `NimBLEClient.h:57-103`: connect, MTU, DLE, connection-parameter and PHY APIs.
- `NimBLEServer.h:64-85`: server parameter update and DLE are `void`; PHY is
  `bool`.
- `NimBLEConnInfo.h:42-54`: actual handle, interval, timeout, latency and MTU.
- `NimBLEServer.h:215-234`: actual parameter-update and PHY callbacks.
- `NimBLEClient.h:247-266`: actual MTU and PHY callbacks. There is no client
  connection-update-complete callback, so use a later `getConnInfo()` read-back.
- `NimBLEService.h:45-51`: `service->start()` is a deprecated no-op. Advertising
  start invokes `server->start()` internally; do not claim the service no-op as
  proof.

## Required diagnostic contract

Use separate `requested` and `negotiated` records. Suggested minimum:

```text
[k1_sync_diag] init role=... ok=... mtu_pref_ok=... task_ok=...
[k1_sync_diag] adv scan_rsp_configured=1 uuid=... name=... start=... active=...
[k1_sync_diag] link_request role=... conn_params=issued|accepted phy=... dle=issued|accepted
[k1_sync_diag] link_actual role=... handle=... mtu=... interval_units=... latency=... timeout_units=... tx_phy=... rx_phy=...
[k1_sync_diag] dle role=... requested_octets=251 negotiated=UNMEASURED
```

Leader:

- On physical connect, log `connected`, the initial `NimBLEConnInfo`, and issue
  requests, but do not label request results negotiated or emit `link up`.
- Emit `link up` only after both notification subscriptions are active.
- Override `onConnParamsUpdate`, `onMTUChange`, and `onPhyUpdate` to emit actual
  values. `getPhy()` may provide paired read-back.
- `updateConnParams()` and `setDataLen()` are `void`: log only `issued`.
- Remove advertising restart from `onConnect`. On disconnect, check
  `adv->start()` and `adv->isAdvertising()`, and log the reason code.

Follower:

- Log `getLastError()` after a failed connect and step-specific failures for
  service, characteristic and subscription discovery.
- Add `onMTUChange` and `onPhyUpdate`.
- `updateConnParams`, `updatePhy` and `setDataLen` booleans mean request accepted,
  not negotiated. Read `getConnInfo()` and `getPhy()` later from the existing
  Core-1 service path, after the update has had time to complete.
- Emit `link up` only after service lookup, both characteristic lookups and both
  subscriptions succeed.

Check every steady-state `notify()` and clock `writeValue()` return. Increment
bounded counters and emit failure-only diagnostics; do not print every success
at 33 Hz.

## Identity and build guard changes

1. Add `k1_sync_probe_main_sync_only` to the main-K1 `K1Target.envs` tuple in
   `scripts/platformio/k1_upload_guard.py` beside `k1_sync_probe_main`.
2. Add it to both the displayed allowlist and exact `case` arm in
   `scripts/agent/pio-build.sh`.
3. Extend `test_sync_probe_envs_are_bound_to_their_devices` to assert the new
   environment accepts the main port and reports chip `F887A500`.
4. Extend `test_cross_flash_attempts_are_rejected` with the new environment on
   the bench port.
5. Retain `test_all_k1_chip_bound_envs_are_registered_in_guard`
   (`tests/test_k1_upload_guard.py:204-242`); it is the fail-closed drift catcher.
   Without registration, `validate_upload_target()` currently returns success
   for an unknown environment (`k1_upload_guard.py:171-173`).
6. Add a static assertion that the wrapper contains the new environment and
   rejects suffix/argument injection.

## Required static tests

In addition to the proposed tests, assert:

- the `.ino` Remoted call is inside its own `SB_K1_BLE_REMOTED` gate;
- the Remoted linked declaration and call in SyncLink both require
  `SB_K1_BLE_REMOTED`;
- the sync-only section contains neither Remoted source nor macro;
- upload-guard main binding and cross-flash rejection for sync-only;
- `enableScanResponse(true)` occurs before `setName`, but is not assigned;
- request log fields are not named `granted`, `negotiated` or `actual`;
- `onConnParamsUpdate`, both `onMTUChange` paths and both `onPhyUpdate` paths
  exist;
- server `updateConnParams` and `setDataLen` results are not assigned;
- link-up is textually after both subscription checks;
- leader link-up is subscription-gated through `onSubscribe`, and raw GAP
  connect cannot start stream/GPIO service;
- advertising is not restarted from leader `onConnect`;
- task creation and init failures are observable.
- the dual-role leader has a compile-time `CONFIG_BT_NIMBLE_MAX_CONNECTIONS >= 2`
  assertion.
- the Remoted application task is not newly accepted on the hard-real-time audio
  core without an explicit probe-only exception.

## Re-run commands

Focused host contract:

```bash
pytest -q \
  tests/test_dual_sync_probe_firmware_static.py \
  tests/test_k1_upload_guard.py \
  tests/test_dual_sync_oracle.py
```

Required wrapper builds:

```bash
bash scripts/agent/pio-build.sh k1_sync_probe_main
bash scripts/agent/pio-build.sh k1_sync_probe_bench
bash scripts/agent/pio-build.sh k1_sync_probe_main_sync_only
bash scripts/agent/pio-build.sh k1_hardware
```

Required commit gate:

```bash
pytest tests/
```

Record the exact dependency after each probe build:

```bash
rg '^version=' \
  .pio/libdeps/k1_sync_probe_main/NimBLE-Arduino/library.properties \
  .pio/libdeps/k1_sync_probe_bench/NimBLE-Arduino/library.properties \
  .pio/libdeps/k1_sync_probe_main_sync_only/NimBLE-Arduino/library.properties
```

No F1 silicon action is authorised until every command above is green and the
staged diff contains only the declared F1 paths.
