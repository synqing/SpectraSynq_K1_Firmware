---
abstract: "F2-EVIDENCE: what happens to the leader K1's live NimBLE central link (K718 dial) if ESP-NOW or Wi-Fi is added on the shared ESP32-S3 radio. Primary-source read of IDF 5.4 RF-coexistence + ESP-NOW docs, verified toolchain sdkconfig, and field reports (gh-17874, gh-17871, gh-11280). Verdict: any esp_wifi-based transport converts the dial from sole radio owner to a ~50% time-sliced tenant with open S3 coexistence bugs; BLE-family K1-to-K1 is the only transport that avoids SW coexistence entirely."
---

<!-- british-english-guard: ignore — verbatim Espressif documentation quotes ("customized", "initializing") must stay byte-exact; all non-quoted prose in this file is British English. -->

# F2 — RF Coexistence Evidence: ESP-NOW/Wi-Fi alongside the live NimBLE K718 link (ESP32-S3, IDF 5.4)

Date: 2026-07-08 · Lane: k1_dual_sync_eval · Status: VERIFIED (primary sources read; no device work)

## Evidence question

If the leader K1 adds ESP-NOW (which initialises the esp_wifi driver) alongside its live NimBLE central link to the K718 dial, what happens to BOTH links on the single shared 2.4 GHz radio — and what is the risk of degrading the K718 link (Captain's 100%-uptime experience) for each transport choice?

## 1. The coexistence mechanism (Espressif primary documentation)

Source: ESP-IDF v5.4 RF Coexistence guide for ESP32-S3 — https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32s3/api-guides/coexist.html

- **Time-sliced arbitration, not concurrent operation.** "Wi-Fi and BLE have their fixed time slice to use the RF. In the Wi-Fi time slice, Wi-Fi will send a higher priority request to the coexistence arbitration module. Similarly, BLE can enjoy higher priority at their own time slice." [READ primary]
- **Slice policy by Wi-Fi status** (verbatim categories): (1) IDLE — "RF module is controlled by Bluetooth module"; (2) CONNECTED — "the coexistence period starts at the Target Beacon Transmission Time (TBTT) and is more than 100 ms"; (3) SCAN — Wi-Fi slice and coexistence period longer than CONNECTED; (4) CONNECTING — Wi-Fi slice longer than CONNECTED. [READ primary]
- **50/50 split when both are connected.** For the Wi-Fi CONNECTED + BLE CONNECTED scheme, "the time slices of Wi-Fi and BLE in a coexistence period each account for 50%". [READ primary]
- **Dynamic priority is probabilistic, not guaranteed.** "The coexistence module assigns varying priorities to different statuses of each module, and these priorities are dynamic. For example, in every N BLE Advertising events, there is always one event with high priority. If a high-priority BLE Advertising event occurs within the Wi-Fi time slice, the right to use the RF may be preempted by BLE." The doc describes *some* high-priority BLE events, not guaranteed windows for every BLE connection event. [READ primary]
- **Connectionless Wi-Fi (the ESP-NOW class) has an explicit coexistence caution.** "Some combinations of connectionless power-saving parameters Window and Interval would lead to extra Wi-Fi priority request out of Wi-Fi time slice … leading to impact on Bluetooth performance. … please configure Wi-Fi connectionless power-saving parameters to default values unless you have plenty of coexistence performance tests for customized parameters." [READ primary]
- **No quantified throughput/latency degradation figures are published** in the v5.4 S3 guide — the doc gives support classes (below), not numbers. [READ primary]

### Supported-features table for ESP32-S3 (Wi-Fi × BLE), ESP-NOW rows

Legend (verbatim): "Y: supported and performance is stable · C1: supported but the performance is unstable · X: not supported · **S: supported and performance is stable in STA mode, otherwise not supported**". [READ primary]

- **ESP-NOW RX vs BLE (Scan/Advertising/Connecting/Connected): "S"** — i.e. ESP-NOW *reception* under BLE coexistence is only claimed stable when the Wi-Fi interface is in STA mode; in SoftAP mode it is **not supported**. [READ primary]
- **ESP-NOW TX vs BLE (all four states): "Y"** — transmit is the well-supported direction. [READ primary]

### Espressif's own mitigation guidance

"To ensure better communication performance of Wi-Fi and Bluetooth in the case of coexistence, run the task of the Wi-Fi protocol stack, the task of the Bluetooth Controller and Host protocol stack on **different CPUs**" (via `CONFIG_BT_CTRL_PINNED_TO_CORE_CHOICE` / `CONFIG_BT_NIMBLE_PINNED_TO_CORE_CHOICE` and `CONFIG_ESP_WIFI_TASK_CORE_ID`). Also: `CONFIG_ESP_COEX_SW_COEXIST_ENABLE` must be on for coexistence to work at all. [READ primary]

**This mitigation is unavailable to us.** The precompiled arduino-esp32 3.2.0 libs pin BOTH stacks to Core 0:
- `CONFIG_BT_CTRL_PINNED_TO_CORE=0` / `CONFIG_BT_CTRL_PINNED_TO_CORE_0=y` [REPO ~/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/sdkconfig]
- `CONFIG_ESP_WIFI_TASK_PINNED_TO_CORE_0=y` [REPO same file]
- `CONFIG_ESP_COEX_SW_COEXIST_ENABLE=y` (SW coexistence is compiled in and activates as soon as both drivers run) [REPO same file]

Core 0 also carries the hard-real-time 133 Hz audio pipeline (7.5 ms frame budget). Adding the Wi-Fi task to Core 0 stacks a third real-time consumer on the audio core — a CPU-contention risk *separate from* and additive to the RF contention. [REPO platformio.ini:270-280 — the existing bench-BLE env already warns the NimBLE central Core-0 task "can perturb audio timing"]

## 2. ESP-NOW driver + delivery semantics (Espressif primary documentation)

Source: ESP-IDF v5.4 ESP-NOW reference for ESP32-S3 — https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32s3/api-reference/network/esp_now.html

- **ESP-NOW requires the Wi-Fi driver started.** "ESP-NOW data must be transmitted after Wi-Fi is started, so it is recommended to start Wi-Fi before initializing ESP-NOW." There is no ESP-NOW without `esp_wifi` running — so adding ESP-NOW **always** activates Wi-Fi/BT SW coexistence on the shared radio. [READ primary]
- **Delivery is MAC-ACKed but not application-guaranteed.** The send callback "will return ESP_NOW_SEND_SUCCESS … if the data is received successfully on the MAC layer. … **It is not guaranteed that application layer can receive the data.** If necessary, send back ack data when receiving ESP-NOW data. If receiving ack data timeouts, retransmit." (Broadcast frames get no MAC ACK at all.) [READ primary]
- **Default bit rate 1 Mbps**, vendor-specific action frames, ≤250 B per `esp_now_send()` (v1.0). At our duty (~33 Hz × ~60–100 B ≈ 2–3.5 kB/s) airtime is trivial (~1–3% at 1 Mbps) — confirming throughput is not the constraint; **arbitration slots are**. [READ primary + task brief]
- **Channel discipline:** peers must share the current Wi-Fi channel (`ESP_ERR_ESPNOW_CHAN` if mismatched); channel 0 = "current channel". [READ primary]
- **RX wake window is a coexistence lever:** `esp_now_set_wake_window()` default is maximum ("allowing RX all the time"); non-default connectionless Window/Interval combinations are exactly what the coexistence guide warns will hurt Bluetooth. [READ primary]

## 3. Field reports — what actually happens in the wild

- **espressif/esp-idf#17874 — "ESP-NOW + BLE Coexistence Failure" (IDFGH-16797), opened Nov 2025, label `Status: In Progress` (still open).** ESP32 (classic), IDF 5.5.1, NimBLE: "ESP-NOW packet reception fails completely when BLE scanning is active … **ESP-NOW receive callback is never called** despite packets being sent on the same channel", while each protocol alone works perfectly. Reporter tried BLE scan intervals 10–1280 ms, all Wi-Fi PS modes, `ESP_COEX_PREFER_WIFI`, channels 1/6/11, `esp_now_set_wake_window(65535)`, task priorities — **none worked**; only fully alternating the stacks (not coexistence) worked. This is the exact combination proposed for the leader (NimBLE + ESP-NOW), unresolved by Espressif at time of writing. Hardware caveat: classic ESP32, not S3; BLE *scanning* (dial-reconnect state), not connected-only. [READ primary — https://github.com/espressif/esp-idf/issues/17874]
- **espressif/esp-idf#17871 — ESP32-S3-specific (IDFGH-16793), closed `Resolution: Done` internally.** Wi-Fi STA + NimBLE on S3, IDF 5.2.6: Wi-Fi STA association fails (0x5A0) on certain Android 13+ hotspots **only when BLE is active**; plain Wi-Fi (no BLE) connects everywhere. Reporter's analysis: "the coexistence arbiter may prematurely trigger a disconnect due to BLE connection events firing shortly after association." Demonstrates the S3 coexistence arbiter itself has had recent, real bugs in exactly the Wi-Fi+NimBLE combination; fix status is "done internally", i.e. in an IDF newer than our pinned 5.4.x precompiled libs. [READ primary — https://github.com/espressif/esp-idf/issues/17871]
- **espressif/esp-idf#11280 — BLE connection fails when Wi-Fi coexistence enabled (ESP32-C3, IDFGH-9999), closed `Resolution: Done`.** Logs show the BLE peripheral connecting and then disconnecting seconds later (reason 520/0x208 = supervision timeout class) in a repeating loop while Wi-Fi ping traffic runs — the canonical signature of BLE connection events starved by the Wi-Fi slice. Different chip, same arbitration subsystem. [READ primary — https://github.com/espressif/esp-idf/issues/11280]
- Older esp32.com threads ("WIFI/BLE Simultaneously", multi-page) report BLE latency spikes/drops when Wi-Fi activates on the shared radio; not re-verified in detail. [SEARCH snippet — https://esp32.com/viewtopic.php?t=6707&start=50]

## 4. What this means for the leader K1 specifically

**Adding ESP-NOW to the leader while the NimBLE central link to the K718 is live:**

1. Starting `esp_wifi` flips the K718 link from *sole owner of the radio* (Wi-Fi IDLE ⇒ "RF module is controlled by Bluetooth module") to a *time-sliced tenant*. Once ESP-NOW traffic flows, the connectionless-Wi-Fi coexistence scheme applies; the BLE share of the radio drops materially (50% in the connected/connected reference scheme) and BLE connection events that land in Wi-Fi slices are delayed or lost. [READ primary]
2. The K718 dial is a low-duty BLE-MIDI notify stream; a healthy link tolerates missed connection events via the supervision timeout, so outright *drops* are not certain — but latency jitter on dial events (delays up to the Wi-Fi slice length within a >100 ms coexistence period) and occasional reconnect storms (per #11280/#17871 class bugs) are the documented and field-observed failure modes. Captain's "100% uptime" baseline exists precisely because the radio currently has no Wi-Fi tenant; that condition is what ESP-NOW removes. [READ primary + REPO]
3. Direction nuance (honest): for the K1→K1 stream the leader is mostly **ESP-NOW TX ("Y", the stable direction)** and the follower (no BLE at all) does the RX. The catastrophic #17874 mode (ESP-NOW RX dead under BLE scan) would bite the leader mainly for follower→leader return traffic (acks, clock-sync replies) and during dial-reconnect scan windows. Clock sync needs a round trip — so the return path *is* load-bearing for the ~4 ms clock-offset budget, and it is the weak direction on the leader.
4. Clock-offset budget risk: coexistence can defer a packet's actual TX until the BLE slice ends. Software timestamps taken at `esp_now_send()` therefore carry tail errors of tens of ms; ESP-NOW exposes no hardware TX timestamping to correct this. RTT-filtered sync (min-filtering, accept-only-fast-exchanges) can bound this but the tails widen exactly when the radio is busiest. [READ primary + analysis]
5. Espressif's only strong documented mitigation — Wi-Fi and BT stacks on different CPUs — is foreclosed by the precompiled arduino-esp32 3.2.0 libs (both pinned Core 0), and Core 0 already runs the 133 Hz audio pipeline. [REPO sdkconfig + platformio.ini]

**The reverse option (ESP-NOW-only for K1→K1, dial stays BLE):** there is no reverse that avoids coexistence. The K718 is a BLE device; the leader must keep NimBLE up to hear it. *Any* non-BLE transport (ESP-NOW or Wi-Fi/UDP/WebSocket) puts `esp_wifi` on the same radio next to that NimBLE link — coexistence is unavoidable for every non-BLE K1→K1 transport while the K718 exists. Moving the dial off BLE is not on the table (it is shipped hardware with a 100%-uptime link). [READ primary + task brief]

**Wi-Fi (AP/STA + UDP or WebSocket) as the K1→K1 transport:** same coexistence class as ESP-NOW, plus: if the leader hosts a SoftAP (the existing Tab5 pattern, `sb_k1_wireless`), note the support table marks connectionless RX stable **only in STA mode** — SoftAP-based designs sit in the weaker column; and beacons/association add periodic high-priority Wi-Fi airtime. Risk to the K718 link ≥ ESP-NOW's. [READ primary + REPO SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.*]

**BLE-family K1→K1 (leader takes a second BLE connection to the follower):** the only transport with **no `esp_wifi` driver at all** — SW coexistence never engages; the radio stays 100% Bluetooth-owned as today. Scheduling two BLE connections is native LE-controller behaviour (deterministic anchor-point scheduling around connection intervals), not the Wi-Fi/BT arbiter. NimBLE-Arduino 2.5.0 defaults to `CONFIG_BT_NIMBLE_MAX_CONNECTIONS 3` [REPO .pio/libdeps/k1_ble_remoted_probe/NimBLE-Arduino/src/nimconfig.h:225]. Residual risks are intra-BLE (connection-event collisions between the two links; both hosts' events on the Core-0 controller task) — real but a different, far smaller class than Wi-Fi/BT arbitration, with no open Espressif bugs of the #17874/#17871 severity found for it. [REPO + READ primary]

Repo state corroborates caution: production K1 firmware is deliberately **radio-free**; the 2.4 GHz interference A/B (radio vs audio-pipeline timing) is still open; even the bench BLE build is marked non-shippable until that A/B clears. [REPO platformio.ini:268-300, 344-360]

## 5. Risk grading (degradation of the K718 dial link)

| K1→K1 transport | Coexistence engaged? | K718-link risk | Basis |
|---|---|---|---|
| **BLE-family** (2nd LE connection) | No — no esp_wifi | **LOW** — radio stays BLE-owned; intra-LE scheduling only | Table legend N/A; nimconfig 3-conn default; no coex arbiter involved [READ primary / REPO] |
| **ESP-NOW** | Yes — always (driver requirement) | **HIGH** — BLE demoted to time-sliced tenant; open Espressif bug #17874 (In Progress) for exactly NimBLE+ESP-NOW; S3 arbiter bug history #17871; no separate-CPU mitigation available | [READ primary ×4, REPO sdkconfig] |
| **Wi-Fi (SoftAP/STA + UDP/WS)** | Yes — always | **HIGH, ≥ ESP-NOW** — same arbiter plus beacon/association airtime; connectionless-RX support weaker outside STA mode | [READ primary] |

Confidence: the mechanism and support classes are primary-doc certain; the *magnitude* of dial-latency degradation on S3/IDF-5.4 for our exact low-duty pattern is not published anywhere and could only be closed by the (already-planned, still-open) on-device interference A/B.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (F2-EVIDENCE SSA) | Created: primary-source coexistence evidence for the dual-K1 sync transport decision |
