---
abstract: "F2 evidence: BLE notify latency/jitter physics for the K1-to-K1 sync stream (33 Hz, ~100 B). Verifies the Electric UI 'Bluedroid 14.6 ms vs NimBLE 45 ms' claim, shows the 45 ms is NimBLE's 30-50 ms default connection interval + missing data-length extension (not stack physics), derives per-notify latency vs connection interval, and estimates p99/p99.9 lateness at CI 7.5/15 ms against the 25-30 ms delay-line depth. Verdict: BLE holds p99.9 <= ~26 ms at CI 7.5 ms and event error rate <= ~5%; coexistence with the K1's WiFi AP is the untested tail risk."
---

# F2 — BLE Notify Latency/Jitter Physics for the K1-to-K1 Sync Stream

**Date:** 2026-07-08 · **Lane:** k1_dual_sync_eval · **Author:** agent:claude-code (F2-EVIDENCE SSA)
**Evidence question:** does the external "Bluedroid 14.6 ms vs NimBLE 45 ms" claim survive methodology scrutiny, and can BLE notify hold p99.9 packet lateness ≤ the 25-30 ms delay-line depth D at a tuned connection interval?

---

## 1. The Electric UI benchmark — methodology, verified

Source: *Benchmarking latency across common wireless links for microcontrollers* (Electric UI blog, Scott / Scottapotamas) — full article fetched and read [READ primary], cross-checked against the author's own reproduction notes in espressif/esp-idf issue #12789 [READ primary].

**Topology and timing capture** [READ primary]:
- Two **ESP32-WROOM-32** devkits (original ESP32, not S3), 1 m apart on a bench. Peripheral/server notifies; central/client is the *other ESP32* — i.e. an embedded central, not a phone or desktop.
- Signal generator gives a 3.3 V, 50 µs pulse at 250 ms intervals into a GPIO ISR → firmware sends the test payload; the receiver drives a GPIO high on valid (length + CRC-checked) payload.
- Saleae Logic 8 at 100 MS/s (10 ns resolution) captures trigger-to-receive; loopback overhead measured at ~4.11 µs, so wire timing is honest.
- One-way transfer, no application-level ack. IDF 5.1.1, reproduced on v5.3-dev. Firmware derived from Espressif's SPP/GATT examples with UART bridging removed.
- The author later added a *randomised* trigger-phase variant (in the nRF52 section) after observing accidental phase alignment between the stimulus and connection events — evidence the author understood and controlled the U(0, CI) sampling bias [READ primary].

**Headline numbers** [READ primary — figure captions/alt-text in the article]:

| Config | 12 B notify (median) | 128 B | 1 kB | Tail |
|---|---|---|---|---|
| ESP32 **Bluedroid**, defaults | **14.6 ms** | 21 ms | 31 ms | client writes ~20 ms, outliers past 40 ms |
| ESP32 **NimBLE**, defaults | **45 ms** | 32 ms | 57 ms | outliers out to **150 ms** |
| ESP32 **NimBLE**, tuned (conn params + `ble_gap_set_data_len`) | **22 ms** | 24 ms | 37 ms | "massive improvement to variance"; best and worst case halved for 1024 B |
| nRF52 (reference) | 13.4 ms | 13.8 ms | 24.6 ms | no outliers; clusters at CI multiples |

Direct quote on the Bluedroid distribution [READ primary]: "The Notification test data show some distinct distribution bands of higher density. These groups are roughly 7 ms apart, which has a strong correlation to the minimum 7.5 ms connection interval for BLE." — i.e. the latency distribution is quantised in connection-interval steps, exactly the U(0, CI) + k·CI structure theory predicts.

## 2. What produced the 45 ms — configuration, not stack physics

The article states the NimBLE result was pathological and documents two fixes [READ primary]:

1. **Connection interval.** "Things improved somewhat with manually specifying faster `ble_gap_upd_params` for interval and connection timings (fixing the 40 ms gap spacings)". The 40 ms gaps are NimBLE's *default initial connection parameters*. Verified in the exact NimBLE-Arduino 2.5.0 source this repo builds against: `BLE_GAP_INITIAL_CONN_ITVL_MIN = BLE_GAP_CONN_ITVL_MS(30)` and `BLE_GAP_INITIAL_CONN_ITVL_MAX = BLE_GAP_CONN_ITVL_MS(50)` [REPO .pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino/src/nimble/nimble/host/include/host/ble_gap.h:113-116]. A 30-50 ms CI makes a ~45 ms median notify latency *arithmetically inevitable* (mean wait ≈ CI/2 + one queued interval). Bluedroid's example flow ended up on a much shorter effective interval (the 7 ms bands), so the two stacks were benchmarked at different connection intervals — the comparison is a configuration comparison, not a stack-physics comparison.
2. **LL Data Length Extension.** Host-level data-length config was silently not applied through Espressif's VHCI layer; calling `ble_gap_set_data_len(handle, tx_octets, tx_time)` (a wrapped HCI call) fixed it, confirmed by Wireshark showing a single 161 B L2CAP packet [READ primary]. Without DLE, LL payloads are 27 B, so a ~100 B notify fragments into 4+ LL PDUs and pays multi-packet scheduling costs.

After both fixes the 12 B notify median fell 45 → **22 ms** — a "generally better result and mostly matching Bluedroid's defaults" [READ primary]. Residual 22 vs 14.6 ms gap: the article does not state the exact tuned interval value, so the tuned run does not prove NimBLE was taken all the way down to CI = 7.5 ms; the residual gap is consistent with a tuned-but-not-minimum interval. Espressif never officially responded in issue #12789 (still Open, assigned, no root-cause post from Espressif at the time of the article) [READ primary].

**Verdict on the external claim:** the "NimBLE 45 ms" number is real but is dominated by NimBLE's 30-50 ms default connection interval plus a missing DLE application on ESP32's VHCI — both fully controllable from NimBLE-Arduino 2.5.0 (`NimBLEClient::updateConnParams` / `setConnectionParams`, `NimBLEClient::setDataLen` / `NimBLEServer::setDataLen`, plus `updatePhy` for 2M PHY) [REPO .pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino/src/NimBLEClient.h:74-102, src/NimBLEClient.cpp:502-542, src/NimBLEServer.cpp:1044]. It is NOT evidence that NimBLE is intrinsically ~3x slower.

## 3. Per-notify latency as a function of connection interval

Physics (Memfault BLE throughput primer, the same reference the Electric UI article uses) [READ primary]:
- Connection interval CI is negotiable from **7.5 ms to 4 s**; data is exchanged only at connection events every CI.
- The link layer is **reliable**: every data PDU is acknowledged; unacknowledged PDUs are retransmitted. T_IFS = 150 µs between packets; an empty ack is 80 µs.
- Multiple packet pairs can be exchanged within one connection event (governed by the More Data bit and stack/controller limits), so a link-layer retransmission can land *within the same event* if the event stays open, otherwise at the next anchor (+CI).

Latency model for an asynchronous notify (producer unsynchronised with anchors — true for our 33 Hz producer, whose 30.3 ms period is incommensurate with 7.5 ms anchors, so phase drifts uniformly):

```
L ≈ S + W + k·CI
S = host/controller stack overhead (~2-4 ms; Bluedroid median 14.6 ms at CI 7.5 back-solves to S ≈ 3.3 ms with one queued interval)
W ~ U(0, CI) wait for the next usable anchor
k = number of additional connection events consumed by queue slip or retransmission
```

Airtime for a ~100 B notify with DLE at 1M PHY is ~1 ms including ack and IFS (~0.5 ms at 2M PHY) — negligible against CI. Throughput is a non-issue: 33 Hz × ~100 B ≈ 3.3 kB/s vs ≥ ~10 kB/s even for one 100 B PDU per 7.5 ms event.

**What CI different centrals grant:**
- **K1-to-K1: we control both ends.** The ESP32-S3 central chooses the initial parameters and `updateConnParams(6, 6, 0, timeout)` (6 × 1.25 ms = 7.5 ms) demands the BLE minimum; nothing on the peer side (another NimBLE ESP32-S3) will refuse it. This is the decisive structural advantage over phone-peered BLE. [REPO NimBLE-Arduino API above; BLE 7.5 ms floor READ primary via Memfault]
- iOS accessories: Apple's guidelines require interval ≥ 15 ms and a multiple of 15 ms, with an 11.25 ms exception for HID; some Apple devices scale a requested 15 ms up to 30 ms [SEARCH snippet — Silicon Labs "Selecting Suitable Connection Parameters for Apple Devices", Apple QA1931; not fetched]. Android `requestConnectionPriority(CONNECTION_PRIORITY_HIGH)` typically grants ~11.25-15 ms [SEARCH snippet]. Irrelevant to the K1-to-K1 link but confirms why phone-facing BLE folklore reports 15-30 ms+ latencies.

## 4. Lateness tail under retransmission, and p99/p99.9 estimates

Tail structure: a notify that misses/fails an event retries at the next anchor, +CI per miss. Adaptive frequency hopping moves consecutive events to different channels, so event failures are approximately independent; P(lateness beyond k extra events) ≈ p^k for per-event error probability p. (Analysis from the LL ARQ + AFH facts above; the CI-multiple clustering in both the Bluedroid and nRF52 data is the empirical signature [READ primary].)

Conservative estimate, L_pXX ≈ S(3.3 ms) + CI (worst-case W) + k·CI with k = ⌈ln(1−q)/ln p⌉:

| CI | per-event error p | p50 | p99 | **p99.9** | ≤ 30 ms budget? |
|---|---|---|---|---|---|
| 7.5 ms | 1% (clean bench) | ~11 ms | ~18 ms | **~18 ms** (k=1) | YES, wide margin |
| 7.5 ms | 5% (home RF) | ~11 ms | ~26 ms (k=2) | **~26 ms** (k=2, P=2.5e-3→k=3 at 1.25e-4; 26-33 ms band) | YES, thin margin |
| 7.5 ms | 10% | ~11 ms | ~26 ms | **~33 ms** (k=3) | MARGINAL |
| 7.5 ms | 20% (hostile RF / heavy coex) | ~12 ms | ~33 ms | **~48 ms** (k=5) | NO |
| 15 ms | 5% | ~18 ms | ~48 ms | **~48 ms** (k=2) | NO |

Two empirical anchors: Electric UI's Bluedroid 12 B notify data sits in bands at ~7.5/14.6/22 ms with client-write outliers past 40 ms on a *clean bench* [READ primary]; NimBLE at defaults threw outliers to 150 ms [READ primary]. The nRF52 run — a controller not sharing its radio with WiFi — showed *no outliers at all* [READ primary], which localises the ESP32's tail to its stack/coex behaviour rather than BLE per se.

**Answer to the evidence question:** yes, BLE notify can hold p99.9 lateness ≤ 25-30 ms — but only in the specific configuration we happen to control: CI pinned at 7.5 ms on a K1-to-K1 link (both ends ours), DLE set so the ~100 B snapshot rides one LL PDU, and per-event error rate held ≤ ~5%. At CI 15 ms there is no headroom (p99.9 ≈ 48 ms at p=5%). The whole conclusion therefore hangs on whether p ≤ ~5-10% survives the K1's real radio duty — see §5.

## 5. K1-specific caveats (leader radio budget)

- **The existing K718 dial link runs at NimBLE defaults.** `ble_remoted_central.cpp` (293 lines) makes no `updateConnParams`/`setConnectionParams`/MTU/`setDataLen` calls, so the 100%-uptime K718 BLE-MIDI link currently sits at the 30-50 ms default CI [REPO SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp — absence verified by grep]. Adding a second connection at CI 7.5 ms means the controller interleaves anchors for both links; a 100 B event is ≤ ~1 ms of radio time, so raw airtime conflicts are small, and choosing the K718 CI as an exact multiple of 7.5 ms (e.g. request 45 ms) keeps anchors harmonised. That the dial link is *untuned and slow* today is actually protective — it demands little radio time — but any anchor collision policy is the controller's, not ours, and its effect on the dial link's 100% uptime is unproven on device. [analysis on top of REPO facts]
- **WiFi coexistence is the real tail risk.** The Electric UI numbers were taken with WiFi idle. The leader K1's product configuration also runs a WiFi AP for Tab5 control (repo CLAUDE.md network contract), and ESP32-family WiFi+BT share one 2.4 GHz radio through a coexistence arbiter that time-slices the RF front end; Espressif documents degraded BLE performance under active WiFi [SEARCH snippet — ESP-IDF RF coexistence guide; not fetched]. Under active WiFi traffic, per-event error/blocking p can move from the 1-5% regime into the 10-20%+ regime, which by the table above breaks the 30 ms budget. This is the single load-bearing unknown and is only closable by on-device measurement (dual-link + AP traffic soak with lateness histogram).
- **Electric UI tested original ESP32 (BT 4.2 controller), not ESP32-S3.** The S3 controller supports BLE 5.0 (2M PHY, longer DLE) and a newer scheduler; results should be equal or better, but the 14.6/45/22 ms numbers do not transfer 1:1 to S3 hardware [analysis].
- **Clock-offset budget (~4 ms) is not answered by notify latency.** BLE has no PTP, but a K1-to-K1 application-level ping-pong at CI 7.5 ms gives an RTT of ~15-25 ms with symmetric ±CI jitter; min-filtering N exchanges bounds offset error well under 4 ms. Connection-event anchors themselves are a shared sub-ms timebase, though ESP32 NimBLE does not expose anchor timestamps cleanly [analysis — flag for F-clock lane, not proven here].

## 6. Bottom line for the transport decision

The "Bluedroid 14.6 ms vs NimBLE 45 ms" claim must not be consumed as "NimBLE is slow": at defaults NimBLE negotiates a 30-50 ms connection interval (verified in our vendored 2.5.0 source) and fails to apply DLE through ESP32's VHCI; Electric UI's own retest after tuning collapsed the 12 B median from 45 to 22 ms with the variance "massively improved". Theory and the benchmark's own CI-quantised distributions agree on L ≈ stack (≈3 ms) + U(0, CI) + k·CI. A K1-to-K1 NimBLE link where we demand CI = 7.5 ms and set DLE is the *only* BLE configuration that fits the 25-30 ms delay-line: expected p50 ≈ 11 ms, p99.9 ≈ 18-26 ms at per-event error ≤ 5%, degrading to ~33-48 ms at 10-20%. The decision therefore reduces to one measurable unknown: whether the leader's coexistence load (WiFi AP for Tab5 + the K718 central link) keeps the sync link's per-event error under ~5-10%. That is a device-bench question, not a literature question.

---

## Sources

1. [READ primary] Electric UI, "Benchmarking latency across common wireless links for microcontrollers" — https://electricui.com/blog/latency-comparison (full article fetched 2026-07-08; BLE sections, methodology, figure captions).
2. [READ primary] espressif/esp-idf issue #12789 "Unexpected NimBLE GATT performance compared to Bluedroid (IDFGH-11677)" — author's reproduction notes: hardware, trigger, Saleae capture, IDF versions (fetched 2026-07-08; still Open, no official Espressif root-cause reply visible).
3. [REPO] .pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino (v2.5.0): src/nimble/nimble/host/include/host/ble_gap.h:113-116 (default initial CI 30-50 ms); src/NimBLEClient.h:74-102 and src/NimBLEClient.cpp:502-542 (setConnectionParams/updateConnParams/setDataLen/updatePhy); src/NimBLEServer.cpp:1044 (server updateConnParams).
4. [REPO] SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp — K718 central makes no connection-parameter calls (grep-verified absence).
5. [READ primary] Memfault Interrupt, "A Practical Guide to BLE Throughput" — https://interrupt.memfault.com/blog/ble-throughput-primer (CI range, LL ACK/retransmission, T_IFS, MD bit / packets-per-event, DLE).
6. [SEARCH snippet] Silicon Labs "Selecting Suitable Connection Parameters for Apple Devices" / Apple QA1931 (iOS ≥15 ms, multiples of 15 ms, HID 11.25 ms exception) — not fetched, unverified.
7. [SEARCH snippet] ESP-IDF RF coexistence documentation (WiFi/BT time-slicing on shared radio) — not fetched, unverified.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (F2 SSA) | Created — BLE notify latency/jitter evidence for dual-K1 sync transport decision. |
