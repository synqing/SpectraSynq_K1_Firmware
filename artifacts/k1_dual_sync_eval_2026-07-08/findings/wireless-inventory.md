---
abstract: "Wireless/inter-device comms inventory for the dual-K1 sync lane (2026-07-08): production K1 firmware is RADIO-FREE; WiFi softAP+WebSocket (Tab5) exists but is compiled only in one non-shippable probe env and is product-deprecated per Captain UF2 (2026-06-30, BLE-MIDI is the control surface); zero ESP-NOW in firmware source (heritage SensorySync p2p was removed), though ESP-NOW + SW coexistence are available in the pinned arduino-esp32 3.2.0 / IDF 5.4 framework; K1 BLE role today is NimBLE CENTRAL-only (K718 Remoted peripheral, 71-control MIDI map, Core-0 task); CPU margin ~0.7 ms p95 on the 7.5 ms Core-0 AP budget, ~76 KB idle internal RAM with a known transient-dip abort under combined radio load, BLE stack costs ~305 KB flash."
---

# Wireless & Inter-Device Communication Inventory — Dual-K1 Sync Evaluation

Lane: `artifacts/k1_dual_sync_eval_2026-07-08` · Author: SSA read-only research agent · Date: 2026-07-08

Default stance was refutation; every claim below carries a file:line or document citation that was actually read this session. Physical devices were not touched; no serial ports opened; no builds run.

## Headline verdicts

1. **Production K1 firmware ships with NO radio at all.** Both WiFi and BLE exist only in non-shippable bench/probe envs.
2. **The "WiFi AP-only" mandate is real but strategically superseded**: Captain decision UF2 (2026-06-30) drops WiFi entirely; BLE-MIDI is the control surface.
3. **There is zero ESP-NOW in firmware source** — the Sensory Bridge heritage p2p unit-sync (`SensorySync` over `esp_now`) was deliberately removed — but ESP-NOW and WiFi/BT software coexistence are fully available in the pinned framework, so ESP-NOW is a *re-introduction*, not an invention.
4. **K1's BLE role today is CENTRAL-only** (it consumes the K718 "Remoted" peripheral). A K1-to-K1 BLE link requires adding a peripheral/dual role to one unit; that code does not exist yet.

---

## (a) Exact current WiFi topology and the AP-only mandate

**Topology (code):** `SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp` implements a WiFi **softAP + WebSocket server** for the Tab5 control client:

- SSID `LightwaveOS-AP`, **open network** (empty password) — `sb_k1_wireless.cpp:19-20`
- Static AP address 192.168.4.1/24 (AP = gateway) — `sb_k1_wireless.cpp:21-23`
- `WebSocketsServer` on **port 80, path `/ws`** — `sb_k1_wireless.cpp:24,74`
- AP-only mode is explicit in code: `WiFi.mode(WIFI_AP)` then `softAPConfig` + `softAP` — `sb_k1_wireless.cpp:880-883`. There is no STA code path anywhere in the file.
- The WS service runs as a FreeRTOS task at idle+1 priority on **core 0** by default (`sb_k1_wireless.cpp:32-46`), with a compile-time `#error` forbidding placement on the LED render core (`sb_k1_wireless.cpp:48-50`).
- Bounded queues: 8-deep request/frame queues, 768 B RX / 1024 B TX limits, max 4 requests per AP tick (`sb_k1_wireless.cpp:25-31`).
- Auth token `k1-tab5` (default fallback `sb_k1_wireless.cpp:36-38`; production definition scrubbed to the probe env per `platformio.ini:69-73`).

**Where it is (and is not) compiled:** the entire TU is gated by `#ifdef SB_K1_WIRELESS_ENABLED` (`sb_k1_wireless.cpp:1`, `sb_k1_wireless.h:3`). Exactly **one** environment defines it: `env:k1_wireless_ab_probe` (`platformio.ini:353-365`), which is marked NON-SHIPPABLE and states "Production envs stay wireless-free until the A/B exonerates or convicts the stack" (`platformio.ini:350-351`). The production `k1_hardware` build_src_filter (`platformio.ini:44`) includes no `network/` sources.

**Where the mandate is documented:**
- Repo root `CLAUDE.md` (Platform-Native Production Patterns §5): "K1 runs WiFi AP-only; the Tab5 joins the K1 AP as the control client… Do not add K1 STA fallback."
- `docs/protocol/k1-ws-contract.yaml:4-8`: transport `mode: wifi_ap`, host 192.168.4.1, port 80, path `/ws`, protocol v2 (v1 compat).
- `docs/protocol/k1-rest-contract.yaml:8`: REST deliberately not implemented; "K1 Tab5 control uses the AP-only WebSocket contract".

**Supersedence (load-bearing for this lane):** `docs/handover/2026-06-30-n2-freeze-remediation-and-session-handover.md:15` — "**Captain decision (UF2): BLE-MIDI is the control surface; WiFi is dropped entirely.** Consequence: the monorepo's WiFi dual-mode, REST/WS API, and iOS app are product-deprecated". The AP-only WS stack is therefore legacy/deprecated surface, not the go-forward control plane. Any dual-K1 design that resurrects WiFi contradicts a ratified Captain decision and would need explicit re-ratification.

## (b) ESP-NOW usage and radio coexistence

**Existing ESP-NOW usage: NONE in firmware source.** A tree-wide grep for `esp_now|espnow|ESP-NOW` hits only documentation and installed skill files — zero hits under `SPECTRASYNQ_K1_FIRMWARE/`. Two documents confirm this is deliberate removal, not absence:
- `docs/superpowers/plans/2026-05-22-release-feature-recovery-roadmap.md:48`: "The dead p2p control surface was removed from active firmware source: no `esp_now`, `SensorySync`, `IS_MAIN_UNIT`, `get_main_unit`, or `set_main_unit` hits remain in firmware source."
- `docs/k1-refactor-2026-05/phase1-source-survey-from-explore-agents.md:117`: "P2P / ESP-NOW — REMOVED-FROM-SOURCE".

This matters for the dual-sync lane: **upstream Sensory Bridge heritage already synchronised multiple units over ESP-NOW** (main/side unit roles). The capability was excised from this fork, so ESP-NOW for K1-to-K1 would be a re-introduction with prior art, not novel territory.

**Framework availability:** the build pins arduino-esp32 3.2.0 via pioarduino 54.03.20 (`platformio.ini:19-22`). The resolved framework source package on this machine (`~/.platformio/packages/framework-arduinoespressif32@src-6738…`, package.json version 3.2.0) bundles the `ESP_NOW` Arduino library alongside `WiFi`, `BLE`, `SimpleBLE`. No repo-level `sdkconfig*` override exists (verified: no such files at repo root), so radio configuration comes from the precompiled IDF libs.

**Coexistence flags (precompiled IDF libs, `framework-arduinoespressif32-libs`, version 5.4.0+sha.2f7dcd862a, `esp32s3/sdkconfig`):**
- `CONFIG_ESP_COEX_SW_COEXIST_ENABLE=y` and `CONFIG_SW_COEXIST_ENABLE=y` — WiFi/BT software coexistence ON.
- `CONFIG_BT_ENABLED=y`, `CONFIG_BT_CONTROLLER_ENABLED=y` (IDF-level NimBLE host not set — the NimBLE-Arduino lib_dep supplies its own host on top of the controller).
- `CONFIG_ESP_WIFI_ENABLED=y`; `CONFIG_ESP_WIFI_ESPNOW_MAX_ENCRYPT_NUM=7` — ESP-NOW support compiled into the WiFi lib.

**Assessment:** the ESP32-S3 has a **single shared 2.4 GHz radio**; SW coexistence time-slices it between WiFi (incl. ESP-NOW) and BLE. So ESP-NOW+BLE or WiFi+BLE can technically coexist on this config, at the cost of duty-cycle sharing (throughput/latency jitter on both stacks). No env in `platformio.ini` currently combines `SB_K1_WIRELESS_ENABLED` with `SB_K1_BLE_REMOTED` — WiFi+BLE-in-one-build is unproven on this firmware. The 2.4 GHz interference A/B for BLE **alone** is still open (`platformio.ini:277-280`: "radio load can perturb audio timing… the 2.4 GHz interference A/B is still open").

## (c) Tab5 / K718 control plane expectations and conflict surface

Two distinct control clients exist in history; only one is go-forward:

**Tab5 (WiFi WS — deprecated):** expects to *join the K1's AP* as a station and speak the `k1.ws` v2 JSON contract (hello/token, control_set, state_get, capabilities_get — `sb_k1_wireless.cpp:52-58`, `docs/protocol/k1-ws-contract.yaml`). Product-deprecated per UF2. A K1-to-K1 WiFi link (one K1 STA joining the other's AP, or ESP-NOW alongside softAP) would not collide with a Tab5 client in production because production has no WiFi at all — but it would resurrect a dropped surface.

**K718 "Remoted" (BLE-MIDI — go-forward):** the K718 is an Apple-BLE-MIDI **peripheral** named "SpectraSynq Remoted" (service `03B80E5A-EDE8-4B33-A751-6CE34EC4C700`, characteristic `7772E5DB-3868-4112-A1A9-F2669D106BF3` — `ble_remoted_central.cpp:38-40`). The K1 side is a NimBLE-Arduino ^2.5.0 (`platformio.ini:302`) **central**: scans by name+service, connects to exactly one peripheral, subscribes to notify, decodes the generated **71-control map** (`k1_ble_midi_map.h:9`: `K1_BLE_MIDI_CONTROL_COUNT 71`; registry md5 pinned) and applies records via `sb_k1_control_apply()` from the main-loop poll (`ble_remoted_central.cpp:10-13, 239-254`). K1→knob feedback uses CC 0x20/0x21 confirmed-mode writes (`ble_remoted_central.cpp:42-43,195-201`).

**Conflict analysis for a K1-to-K1 link:**
- *BLE:* current K1 code has **no peripheral/advertiser role** — central-only. Dual-K1 over BLE means either (i) one K1 gains a peripheral role (NimBLE supports dual role; unverified in this codebase) so the other K1's existing central machinery can consume it, or (ii) both K1s remain centrals of the K718 and the K718 fans out state — which requires the K718 peripheral to accept ≥2 concurrent centrals (K718 sketch lives outside this repo; `platformio.ini:282-286` records it as protocol-matched but "never been compiled/flashed" as of 2026-07-04). The BLE-MIDI evidence manifest is `PARTIAL_COMPLETE_DEVICE_BLOCKED` (`artifacts/ble_midi_71_20260628/README.md:3`), i.e. end-to-end device proof of even the single-link case was blocked at that date.
- *The BLE central task runs on Core 0* (`ble_remoted_central.cpp:235`: `xTaskCreatePinnedToCore(ble_task, "ble_remoted", 4096, nullptr, 1, &s_task, 0)`) — the same core as the hard-real-time audio pipeline. Any added sync traffic rides on that contention point.
- *BLE-MIDI as transport:* the map is a knob-control vocabulary (PC/CC14/CC7/NRPN), not a streaming surface. Piggybacking sync state (beat phase, mode, seam handshake) is plausible at low rate; per-frame pixel or spectrum streaming is a different traffic class than anything the decoder was built for.

## (d) CPU / RAM / flash headroom evidence for another radio protocol

- **Core-0 CPU margin:** the ACF work-spreading fix is device-proven at 12.8 kHz/96: active AP-frame p95 fell 9088 µs → **6784 µs against the 7.5 ms budget**, frames over budget 889/2667 → 0 (`platformio.ini:126-133`). That leaves ~0.7 ms p95 margin per 133 Hz audio frame on Core 0 — thin. The audio-freeze guard subscribes both the audio loopTask and led_task to a **5 s task watchdog** (`platformio.ini:120-125`); a starving radio task would trip it.
- **Internal RAM:** bench heap telemetry exists precisely because of a radio-load incident: `ble_remoted_central.cpp:272-285` prints internal free / largest block / minimum-ever watermark at 1 Hz; the in-code rationale (`ble_remoted_central.cpp:272-279`) records that a **transient internal-heap dip under combined load (BLE link + notify stream + WiFi-AP client + cal-complete fopen) drove an abort while idle headroom stays ~76 KB**, and that LittleFS writes gate on an 8192-byte largest-free-block threshold. Internal (non-PSRAM) RAM is the binding constraint, and radio stacks allocate from it.
- **Flash:** BLE probe firmware.bin 959,728 B vs production 647,888 B (`artifacts/ble_midi_71_20260628/README.md`, firmware binaries section) — the NimBLE stack costs ≈ **305 KB flash**. Trivial against the 16 MB part (`platformio.ini:28`).
- **PSRAM:** 8 MB present (`board = esp32-s3-devkitc1-n16r8`, `platformio.ini:21`); telemetry prints psram_free but no captured figure was found in-repo this session. Radio stacks largely cannot use PSRAM for their hot allocations, so PSRAM abundance does not relieve the internal-RAM pressure above.

## LED topology cross-check (brief said "~160 LEDs, verify")

- Render canvas: `NUM_FREQS 80` bins; **`NATIVE_RESOLUTION` = 160 px** (`config_types.h:117-121`; `diag/motion_probe.h:43`).
- Physical: default `LED_STRIP_MODE 3` → **`LED_COUNT_VALUE 160` per channel**, comment "K1 / SB v9 hardware: 160 per channel" (`config_types.h:123-140`); **`SECONDARY_LED_COUNT = 160`** (`system/globals.h:825`). So each K1 drives **two** 160-LED edge channels (320 physical LEDs per unit) rendered from one 160-px canvas; `scale_to_strip()` resamples the canvas onto other strip lengths (`config_types.h:126-131`). The brief's "~320-LED virtual surface" is best read as a **320-px virtual render canvas** (2 × 160-px canvases side by side), not 320 physical LEDs.

## Numbers

| Quantity | Value | Source |
|---|---|---|
| WS server port / path | 80 / `/ws` | sb_k1_wireless.cpp:24,74 |
| AP address | 192.168.4.1/24 | sb_k1_wireless.cpp:21-23 |
| WS RX / TX limits | 768 B / 1024 B | sb_k1_wireless.cpp:26-27 |
| WS queue depth / req per tick | 8 / 4 | sb_k1_wireless.cpp:25,30 |
| BLE-MIDI control count | 71 | k1_ble_midi_map.h:9 |
| BLE task stack / priority / core | 4096 B / 1 / core 0 | ble_remoted_central.cpp:235 |
| BLE cmd queue depth | 16 | ble_remoted_central.cpp:44 |
| Core-0 AP frame budget / p95 after ACF spread | 7.5 ms / 6.784 ms | platformio.ini:129-132 |
| Idle internal-RAM headroom (bench, BLE build) | ~76 KB | ble_remoted_central.cpp:279 |
| LittleFS internal largest-block gate | 8192 B | ble_remoted_central.cpp:273 |
| Flash cost of NimBLE stack (probe vs prod bin) | 959,728 − 647,888 ≈ 305 KB | artifacts/ble_midi_71_20260628/README.md |
| Render canvas / physical LEDs per K1 | 160 px / 2 × 160 | config_types.h:121-140; globals.h:825 |
| Audio frame rate / sample map | 133 Hz, 12.8 kHz / 96 | platformio.ini:75-77 |
| Task watchdog timeout | 5 s | platformio.ini:122 |

## Risks

1. **Single 2.4 GHz radio, time-sliced coexistence:** any second protocol (ESP-NOW or WiFi) added next to BLE shares one radio via SW coexistence; latency jitter lands on both links — directly against the "seam jitter imperceptible" bar.
2. **Core-0 contention:** the only proven radio task placement is Core 0, beside the hard-real-time audio loop with ~0.7 ms p95 margin; the interference A/B for BLE alone is still open (`platformio.ini:277-280`).
3. **Internal-RAM transient dips:** a combined-radio-load heap dip already caused a real abort; adding a second stack raises the dip amplitude.
4. **WiFi is product-dropped (UF2):** choosing a WiFi or softAP-based K1-to-K1 link reopens a ratified Captain decision — escalation-grade, not agent-resolvable.
5. **Role gap:** K1 is BLE central-only; K1-to-K1 BLE needs new peripheral/dual-role code or a K718 fan-out whose peripheral firmware is outside this repo and (as of 2026-07-04) never flashed.
6. **All radio builds are currently non-shippable** — production is radio-free; a sync feature converts a bench-only surface into shipped product and inherits every open gate (interference A/B, device eyes-on).

## Open questions

1. Which exact `framework-arduinoespressif32-libs` package (and hence sdkconfig) pioarduino 54.03.20 resolves for this repo's builds — the machine-local package reads 5.4.0+sha while docs claim IDF 5.4.1; confirm via a build log or `.pio` metadata before relying on flag-level coexistence details.
2. Can NimBLE-Arduino 2.5.0 run concurrent central+peripheral (dual role) within the K1's internal-RAM budget? Upstream supports it; unproven in this codebase.
3. Provenance of the "BLE link + … + WiFi-AP client" combined-load incident in the heap-telemetry comment — no K1 env builds both stacks, so was the WiFi-AP client on the K718 side or a since-deleted bench build? Determines whether WiFi+BLE-on-one-K1 has ever actually run.
4. Current K718 flash/link status: `env:k1_custom` (2026-07-06, `platformio.ini:253`) says the Remoted dial "controls the wall live", which post-dates the "never compiled/flashed" note of 2026-07-04 — reconcile before assuming a working BLE link exists today.
5. Measured BLE-MIDI notify latency/throughput on the live link — not found anywhere in-repo; needed for any seam-sync latency budget.
6. What the removed heritage `SensorySync` ESP-NOW protocol actually carried (frame data vs control state) — the pre-removal source was not excavated this session; worth one archaeology pass before designing a successor.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (SSA wireless-inventory reader) | Created — full wireless/inter-device inventory with citations for the dual-K1 sync evaluation lane. |
