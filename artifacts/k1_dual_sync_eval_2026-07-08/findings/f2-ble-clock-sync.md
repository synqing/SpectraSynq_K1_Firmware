---
abstract: "F2 evidence (2026-07-08): achievable inter-device clock-offset error between two ESP32-S3s at application level, vs the ~4 ms budget. BLE/NimBLE RTT-burst design: expected 0.3–1.5 ms typical (tails ~2–3 ms under load) — literature shows 69–477 µs mean, 95th pct <1.8 ms app-layer on TI/Nordic; NimBLE 2.5.0 exposes NO connection-event anchor (verified in vendored headers). ESP-NOW two-way exchange with hardware MAC RX timestamps (wifi_pkt_rx_ctrl_t.timestamp, µs, verified in local IDF 5.4 headers): expected 0.05–0.5 ms. Crystal drift ±10 ppm/unit → ≤20 µs/s relative; 4 ms budget consumed only after ≥200 s free-run, so a 33 Hz stream carrying timestamps makes drift a non-issue. Both transports beat the budget; ESP-NOW wins on raw accuracy by ~10×, BLE wins on coexistence with the K718 link."
---

<!-- british-english-guard: ignore — the flagged "artifacts" strings are literal repo directory paths (artifacts/k1_dual_sync_eval_2026-07-08/…), not prose. Prose in this file uses British spellings. -->

# F2 — Inter-device clock-offset error: BLE (NimBLE, application level) vs ESP-NOW

**Evidence question:** What clock-offset error is achievable over BLE between two ESP32-S3s at APPLICATION level (NimBLE, no controller hacks), versus over ESP-NOW? Budget to beat: **~4 ms** (Captain's ~8 ms perceived-lag standard, halved for margin).

**Context respected:** timestamped-replay design absorbs raw transport latency in delay depth D; only (i) clock-offset error and (ii) lateness tails matter. This file covers (i). Leader must simultaneously hold the NimBLE CENTRAL link to the K718 BLE-MIDI dial.

---

## 1. What actually limits application-level clock sync

Clock-offset error in a two-way timestamp exchange is bounded by the **asymmetry** of the outbound vs return path delays, not their magnitude (NTP identity: error ≤ half the RTT asymmetry). At application level on ESP32-S3 the asymmetry sources are:

1. **Send-side quantisation** — time between reading the local clock and the packet actually going on air (BLE: wait for next connection event, 0–1 connection interval; ESP-NOW: CSMA channel access, ~0.1–2 ms under contention).
2. **Receive-side notification jitter** — time between packet on air and the application callback observing it (FreeRTOS scheduling; NimBLE host task hop; WiFi task hop). Order 0.1–1 ms, worse when Core 0 is loaded (our 133 Hz audio pipeline is pinned there, as is the WiFi task).
3. **Clock drift between exchanges** — §4.

Both (1) and (2) have a stable minimum plus a heavy right tail, which is exactly what **min-filtering / regression across many samples** removes. All credible application-level results below use that structure.

---

## 2. BLE at application level (NimBLE 2.5.0, ESP32-S3)

### 2.1 API surface: no anchor, RTT only [READ primary — vendored source]

- Grep of the exact vendored library (`.pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino`, `library.properties` version=2.5.0): the host GAP API exposes `conn_event_counter` **only** inside the `conn_iq_report` struct (Constant Tone Extension / direction-finding, `src/nimble/nimble/host/include/host/ble_gap.h:1613`), a feature the ESP32-S3 controller does not support. **No connection-event anchor timestamp is available to the application.** [REPO .pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino/src/nimble/nimble/host/include/host/ble_gap.h:1613]
- Anchor-point APIs (`ble_ll_conn_get_anchor`, `anchor_point`) exist only in the NimBLE **controller** sources (`src/nimble/nimble/controller/include/controller/ble_ll_conn.h:294,451`), which are compiled only for nRF ports. On ESP32-S3 the controller is Espressif's precompiled binary behind VHCI (`CONFIG_BT_CTRL_PINNED_TO_CORE=0` per lane context) — controller-level timestamping is a controller hack we ruled out. [REPO .pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino/src/nimble/nimble/controller/include/controller/ble_ll_conn.h:451]

Consequence: the BLE design is limited to **characteristic write/notify RTT exchange with statistical filtering** — timestamps taken in application code either side of GATT operations.

### 2.2 What controller-level literature achieves (upper bound, NOT reachable here)

- **BlueSync** (IEEE Sensors Journal 2021): sync error as low as **320 ns** using advertising radio-event timestamps — requires radio event capture in the controller. Not achievable at NimBLE application level. [SEARCH snippet — ieeexplore.ieee.org/document/9555832, ResearchGate abstract]
- **CheepSync** (2015): ~**10 µs** class over BLE advertising, again with hardware timestamping. [SEARCH snippet]
- These establish that the *radio* is microsecond-capable; everything above the host stack is what costs us three orders of magnitude.

### 2.3 What application-layer literature achieves (directly applicable)

**Primary result — Sensors 23(8):3954, 2023 (PMC10144216), "Application-Layer Time Synchronization and Data Alignment Method for Multichannel Biosignal Sensors Using BLE Protocol"** [READ primary]:

- Method: application-layer only, explicitly built to be portable across vendor stacks — timestamp pairs generated each connection interval (central timestamps arrival, adds one connection interval; peripheral timestamps ADC events), then an **affine (offset + skew) regression across many update intervals** smooths transmission-delay noise.
- Measured inter-peripheral time alignment: **69 ± 71 µs** absolute error on the TI platform (15 ms connection interval) and **477 ± 490 µs** on the Nordic nRF platform (10 ms connection interval); **95th-percentile absolute errors < 1.8 ms on both**. 4900 epochs per cell.
- Their stated failure mode: blocked/retransmitted packets inflate single-sample errors by whole connection intervals; the regression buffer absorbs most of this. Their RF environment was quiet; they warn errors grow in congested 2.4 GHz environments.

**Supporting result — Sensors 23(5):2465, 2023 (PMC10007376)** [READ primary]: same group's earlier two-method comparison achieved **189.9 ± 204.7 µs** and **384.3 ± 386.5 µs** inter-node alignment at application layer; it also reviews prior art — 9 ± 17 µs requires custom hardware; 39.92 ± 14.19 µs requires simultaneous connection establishment (one-shot, drifts thereafter).

**Raw GATT RTT sanity check** [SEARCH snippet — TI E2E forum]: a naive GATT write-with-response round trip measures ~**22 ms ≈ 3× connection interval** — i.e. a *single* RTT sample is useless against a 4 ms budget; the information is in the **minimum and the regression**, not the mean. This matches the quantisation model in §1.

### 2.4 Expected band for a K1 BLE RTT-burst design

Design assumed: follower connects to leader (leader = NimBLE central to both K718 and follower, or leader adds a peripheral role); sync bursts of 30–100 write/notify RTT samples, min-filter + affine offset/skew tracker; continuous refresh piggybacked on the 33 Hz stream.

| Component | Estimate | Basis |
|---|---|---|
| Literature floor (nRF/TI, quiet RF) | 0.07–0.5 ms | PMC10144216 [READ primary] |
| ESP32-S3 penalty: NimBLE host task + FreeRTOS hops both ends, Core 0 shared with 133 Hz audio + WiFi task | +0.2–1 ms typical | §1 mechanism; electricui benchmark shows ESP32 stack-hop costs dominate small-payload latency [READ secondary] |
| Congestion/coexistence tails (K718 link concurrent, 2.4 GHz neighbours) | occasional samples +1 conn interval; removed by min-filter, residual +0.5–1 ms on the estimate under sustained load | PMC10144216 blocked-transmission analysis [READ primary] |

**Expected clock-offset error band (BLE RTT-burst): ~0.3–1.5 ms typical, worst-case tails ~2–3 ms under heavy coexistence.** Meets the 4 ms budget, with modest margin at the ugly end. Requires: many-sample min-filtering (never trust one RTT), skew tracking, and outlier rejection keyed to retransmission-length gaps.

---

## 3. ESP-NOW

### 3.1 Hardware RX timestamp available at application level [READ primary — local toolchain headers]

The decisive structural advantage: ESP-NOW's receive callback delivers a **MAC-layer hardware RX timestamp**, removing receive-side jitter (§1 item 2) entirely on both ends of a two-way exchange:

- `esp_now_recv_info_t` contains `wifi_pkt_rx_ctrl_t *rx_ctrl` [REPO ~/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/include/esp_wifi/include/esp_now.h:89-93 — the exact IDF 5.4.x headers this project builds against].
- `wifi_pkt_rx_ctrl_t.timestamp`: "The local time when this packet is received. It is precise only if modem sleep or light sleep is not enabled. unit: microsecond" (32-bit) [REPO …/esp32s3/include/esp_wifi/include/local/esp_wifi_types_native.h:64].
- Neither K1 sleeps (mains-powered, hard-real-time audio), so the precision caveat is satisfied.

With HW RX timestamps both ways, the only remaining asymmetry is the *difference* between the two directions' channel-access delays (send-side, §1 item 1) — zero-mean and min-filterable; RF propagation is nanoseconds.

### 3.2 Prior art and measured numbers

- **ESPNowMeshClock** (Hemisphere-Project) [READ primary — README]: purpose-built for synchronised DMX/MIDI/lighting meshes; 10-byte broadcast ("MCK" + 56-bit µs timestamp) every ~1000 ms ± 10 %; forward-only slew (`slew_alpha` 0.25) so corrections never cause visible motion artefacts; 64-bit hardware timer clock source. Claims "wireless micro-seconds accuracy sync" — **no measured accuracy figure is published in the README**; treat the claim as design intent, order-of-magnitude plausible given §3.1. Note it is one-way broadcast (no RTT cancellation), so its floor is send-side channel-access jitter, mitigated by slewing across many beacons. GPL-3.0 licence — compatible with this repo (GPL-3.0 derivative) but note the obligation.
- **Espressif esp-now SDK time-sync module (`espnow_time`)** [READ primary — docs.espressif.com esp-now SDK]: initiator broadcasts time (default interval 60 s, example 30 s), responder adjusts when drift exceeds `max_drift_ms` (default/example **100 ms**); drift is *reported in whole ms*. It exists to give deep-sleep sensor nodes a sane wall clock, not AV-grade sync. **Wrong tool for a 4 ms budget — coarse by design; a custom exchange is required.** Its packet type (`ESPNOW_DATA_TYPE_TIMESYNC`) confirms Espressif considers timestamp exchange over ESP-NOW a supported pattern.
- **FTSP over ESP-NOW** (ACM SIET 2023, dl.acm.org/doi/10.1145/3626641.3626683): academic implementation of Flooding Time Synchronization Protocol on ESP-NOW; evaluates receiver-vs-root offsets in **microseconds** post-sync. [SEARCH snippet — paywalled, numbers not extracted this session]. FTSP itself achieves tens of µs with MAC-layer timestamping [READ primary — dishbreak/bluesync survey of Maróti et al.], which is exactly what §3.1 provides.
- **Community measurements** (already in this lane's `prior-art.md` [REPO artifacts/k1_dual_sync_eval_2026-07-08/findings/prior-art.md:56,119]): <1 ms round trip for ~95 % of packets; broadcast to 5 receivers arrived with **~80 µs inter-receiver jitter** — inter-receiver spread is the quantity closest to achievable sync error for a broadcast design.

### 3.3 Expected band for a K1 ESP-NOW design

Two-way exchange (leader↔follower, both logging `rx_ctrl->timestamp` against `esp_timer_get_time()`, min-filter + skew tracker), or one-way broadcast with slewing:

**Expected clock-offset error band (ESP-NOW): ~0.05–0.5 ms** (two-way with HW RX timestamps at the low end; one-way broadcast under contention at the high end). **~10× inside the 4 ms budget.**

Caveat that dominates the transport decision (outside this file's scope but load-bearing): ESP-NOW requires WiFi active, so the shared 2.4 GHz radio must time-slice WiFi against the existing NimBLE K718 central link (coexistence arbitration). The clock error is not the binding constraint for ESP-NOW — coexistence degradation of the 100 %-uptime K718 link is (see F1/F3 lanes).

---

## 4. Crystal drift between sync bursts, and re-sync cadence

- ESP32-S3 hardware design guidelines require the 40 MHz crystal to be **within ±10 ppm** (compulsory external crystal; larger deviation is classed as a manufacturing defect degrading RF). [READ primary — docs.espressif.com esp-hardware-design-guidelines ESP32-S3 schematic checklist, "the accuracy of the selected crystal should be within ±10 ppm"]
- `esp_timer` provides 1 µs resolution and both K1s run it from the same crystal-derived clock; ESP-IDF states < ±10 ppm frequency deviation for the high-resolution timer path. [READ primary — ESP-IDF docs; also already recorded in prior-art.md:100]
- **Relative drift between two units:** worst case within spec = 20 ppm = **20 µs/s = 1.2 ms/min**. Allowing for temperature gradients and ageing pushing units toward the lane brief's ±10–40 ppm assumption, plan for **up to ~80 µs/s relative** at the pathological end (both units at opposite ±40 ppm extremes).

| Relative drift | Time to consume 4 ms budget | Time to consume a 1 ms drift allocation |
|---|---|---|
| 20 µs/s (both in spec, ±10 ppm) | 200 s | 50 s |
| 40 µs/s (±20 ppm) | 100 s | 25 s |
| 80 µs/s (±40 ppm extremes) | 50 s | 12.5 s |

- **Required cadence:** a re-sync (or piggybacked timestamp) every **~10 s** holds drift residual ≤ 0.2–0.8 ms even at the pathological end; every ~1 s makes it ≤ 20–80 µs. The K1 stream already sends **33 packets/s** — embedding a leader timestamp in every Nth packet gives continuous correction essentially for free, and an affine skew estimator (as in PMC10144216) reduces inter-burst drift error by a further 10–100× because the *rate* difference is learned, not just the offset. **Drift is a non-issue for this design; it only matters across stream outages, where even a 30 s dropout stays inside budget.** [DERIVED from READ-primary crystal spec]

---

## 5. Conclusion — expected clock-error bands vs the 4 ms budget

| Design | Expected clock-offset error | vs 4 ms budget | Key dependency |
|---|---|---|---|
| **(a) BLE RTT-burst** (NimBLE app-level write/notify bursts, min-filter + affine tracker, refresh via the 33 Hz stream) | **~0.3–1.5 ms typical; tails ~2–3 ms** under heavy coexistence | **PASS**, margin 2.5–13× typical, ≥1.3× worst tail | Statistical filtering is mandatory (single RTT ≈ 3× conn interval); accuracy degrades gracefully, not catastrophically, with RF load |
| **(b) ESP-NOW** (two-way exchange with hardware MAC RX timestamps, or slewed broadcast) | **~0.05–0.5 ms** | **PASS**, margin 8–80× | Requires WiFi active → BLE/WiFi coexistence risk to the K718 link; HW RX timestamp valid only with sleep modes off (true for K1) |
| Crystal drift between syncs | ≤ 20–80 µs/s relative; 4 ms consumed only after 50–200 s free-run | Non-binding with any re-sync ≤ 10 s cadence | 33 Hz stream provides continuous correction |

Bottom line: **both transports beat the 4 ms clock budget.** ESP-NOW is ~an order of magnitude more accurate because the application gets hardware RX timestamps; BLE has no anchor access at application level on ESP32-S3 (verified in NimBLE 2.5.0 sources) but published application-layer methods with min-filtering/regression land sub-millisecond, and the failure tail (~2–3 ms) still clears the budget. Therefore **clock sync should not drive the transport choice — coexistence with the K718 BLE-MIDI link should**, since that is where the two options genuinely differ (BLE-family: same scheduler, no new coexistence mode; ESP-NOW: introduces WiFi/BT time-slicing on the shared radio).

---

## Sources

| Source | Type | Tag |
|---|---|---|
| NimBLE-Arduino 2.5.0 vendored source (`ble_gap.h`, `ble_ll_conn.h`, `library.properties`) | code | [REPO .pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino] |
| IDF 5.4.x toolchain headers (`esp_now.h:89-93`, `esp_wifi_types_native.h:64`) | code | [REPO ~/.platformio/packages/framework-arduinoespressif32-libs/esp32s3] |
| PMC10144216 — Sensors 2023, app-layer BLE sync (69 µs TI / 477 µs Nordic, 95th <1.8 ms) | paper full text | [READ primary] |
| PMC10007376 — Sensors 2023, sync-method comparison (190–384 µs; survey: 9 µs needs HW, 40 µs needs reconnection) | paper full text | [READ primary] |
| ESPNowMeshClock README (method, parameters, no measured figure) | project doc | [READ primary] |
| Espressif esp-now SDK `espnow_time` docs (60 s interval, 100 ms drift threshold, ms-grade) | vendor doc | [READ primary] |
| ESP32-S3 Hardware Design Guidelines — schematic checklist (±10 ppm crystal) | vendor doc | [READ primary] |
| ESP-IDF esp_timer / system-time docs (1 µs resolution, <±10 ppm) | vendor doc | [READ primary] |
| dishbreak/bluesync design doc (FTSP mechanism, tens-of-µs with MAC timestamps) | project doc | [READ primary] |
| Electric UI wireless latency benchmark (stack-hop latency costs; ESP-NOW top-3 low latency) | benchmark | [READ secondary] |
| BlueSync IEEE Sensors J. 2021 (320 ns, controller-level) | abstract only | [SEARCH snippet] |
| CheepSync (~10 µs, HW timestamping) | abstract only | [SEARCH snippet] |
| FTSP-over-ESP-NOW, ACM SIET 2023 | abstract only | [SEARCH snippet] |
| TI E2E: GATT write RTT ≈ 22 ms ≈ 3× conn interval | forum | [SEARCH snippet] |
| ESP-NOW community latency/jitter measurements | via prior-art.md | [REPO artifacts/k1_dual_sync_eval_2026-07-08/findings/prior-art.md:56,117-119] |

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (SSA F2-EVIDENCE) | Created — clock-offset evidence for BLE (NimBLE app-level) vs ESP-NOW: API surface verified in vendored sources, literature accuracies, crystal-drift cadence maths, expected error bands vs 4 ms budget. |
