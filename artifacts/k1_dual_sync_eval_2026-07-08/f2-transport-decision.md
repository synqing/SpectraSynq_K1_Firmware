---
abstract: "F2 transport decision brief (2026-07-08): recommends BLE-family custom GATT (NimBLE dual-role, sync link at CI 7.5 ms) for the K1-to-K1 sync stream; ESP-NOW/WiFi eliminated while the K718 BLE dial exists because any esp_wifi start engages coexistence time-slicing that demotes the dial link. Evidence: findings/f2-*.md (5 files, primary-source verified). Awaiting Captain ratification."
---

# F2 — K1↔K1 Sync Transport: Decision Brief

> **RATIFIED by Captain 2026-07-08: Option A (BLE-family custom GATT).** Captain-added tier-2 contingency: if all else fails, add a second MCU (another ESP32-S3 or an ESP32-C5) as a dedicated radio co-processor — eliminates the radio-vs-audio Core-0 contention class entirely at the cost of a hardware revision. Contingency order: A fails gates → ESP-NOW (accept coexistence engineering) → 2nd-MCU rev.

**Current state.** Sync architecture is ratified (timestamped replay, leader authority, M1 twins → M2 widened seam-centred). Captain's standard: ~8 ms perceived lag + margin → clock-offset gate ≤~4 ms, delay-line depth D ≤ ~30 ms. Evidence: 5 primary-source research files (`findings/f2-*.md`), all VERIFIED.

**Decision required.** Which transport carries the sync stream: BLE-family custom GATT, ESP-NOW, or WiFi.

## Options considered

**A — BLE custom GATT (NimBLE dual-role), sync link pinned at CI 7.5 ms.**
- Capability CONFIRMED in our exact vendored source: NimBLE-Arduino 2.5.0 runs concurrent central (K718 dial) + peripheral (sync service); the one S3 dual-role showstopper (rc=519, upstream #1016) is fixed in the vendored code (`NimBLEDevice.cpp:923`, ble_max_act=5); 3-connection ceiling (need 2); 2M PHY + DLE reachable; +2–10 KB heap vs ~76 KB headroom.
- The anti-BLE headline ("NimBLE 45 ms median notify") is a **defaults artefact** — NimBLE's 30–50 ms initial connection interval + unapplied DLE; the benchmark author's own tuned retest collapsed it to 22 ms. We own BOTH ends, so we demand CI = 7.5 ms: modelled p50 ≈ 11 ms, **p99.9 ≈ 18–26 ms lateness — inside the 25–30 ms delay line** (CI 15 ms does NOT fit → 7.5 ms is a design constant). BLE link-layer ARQ = lossless delivery with lateness quantised in 7.5 ms steps.
- Clock sync: app-level RTT-burst + min-filter ≈ 0.3–1.5 ms typical, 2–3 ms tails — **passes the 4 ms gate**; drift re-sync piggybacks the 33 Hz stream.
- Duty maths: 33 Hz stream is *below* the K718 link's proven 50 msg/s burst (268/268, zero drops); radio duty ~1–2%.

**B — ESP-NOW broadcast.** Clock accuracy 0.05–0.5 ms (10× overkill vs the budget — buys nothing the design needs). Fatal structural cost: ESP-NOW **cannot run without starting the esp_wifi driver** (Espressif IDF 5.4 docs, primary), which engages SW coexistence and demotes the live K718 NimBLE link from sole radio owner to a ~50%-time-sliced tenant (coexistence period >100 ms, no guaranteed per-event windows). Open Espressif bug **#17874: ESP-NOW RX failure alongside NimBLE, In Progress** — and the clock-sync round-trip needs exactly that RX direction on the leader. S3 coexistence-arbiter bug (#17871) fixed only in IDF newer than our pinned libs. The one strong Espressif mitigation (WiFi and BT stacks on different CPUs) is **foreclosed**: precompiled arduino-esp32 3.2.0 pins both to Core 0, which also runs the 133 Hz audio pipeline.
**C — WiFi (softAP/WebSocket or UDP).** Same coexistence bill as B **plus** TCP/IP-stack jitter, no clock advantage over B, product-deprecated by UF2. Repo evidence exonerates WiFi only at second-granularity scalars; per-frame Core-0 cost never measured against the 716 µs post-ACF p95 margin. Eliminated.

## The deciding logic
Captain's K718 field record (100% uptime, zero drops) exists **because Bluetooth currently owns the RF outright**. Any non-BLE transport necessarily ends that condition on the leader — the K718 keeps NimBLE alive regardless, so coexistence is unavoidable for B and C, and the thing most likely to break is the exact link Captain values most. Option A is the only transport that never engages the WiFi/BT arbiter: it extends the one radio path with a proven record instead of adding a second radio regime to certify. Bayesian read: strong field prior for BLE + confirmed capability + modelled-in-budget tails + adverse primary evidence against B/C ⇒ A, verified on device.

**Honesty box (what the prior does NOT cover — Phase 0 measures these):** the K718 record is idle-dominant, single-link, burst-duty; nothing has ever streamed continuously on this firmware; dual-link connection-event scheduling could add tails to the dial link; the BLE interference A/B (radio vs audio timing) is still DEVICE_BLOCKED; the 16-deep app RX queue is marginal for continuous duty; internal-DRAM watermark under dual-role load is unmeasured (one DRAM crash precedent exists).

## Recommendation
**Ratify BLE-family custom GATT (Option A) as the sync transport.** Not MIDI framing — a purpose-built GATT service (timestamps, batching, ARQ-aware records); the MIDI map/codegen pattern is reused for the control-mirror lane only. Sync link CI = 7.5 ms; K718 link parameters untouched. **Phase 0 narrows from a transport competition to a verification of A** against the four gate numbers (clock error ≤4 ms; p99.9 lateness ≤ D; leader end-to-end ≤50 ms incl. D; render/heap health incl. `internal_min_ever` and dial-link uptime under stream load). **ESP-NOW is eliminated as a concurrent transport while the K718 exists** and retained only as the documented contingency if A fails its gates on silicon.

## Blast radius if wrong
Bench time only: if dual-BLE scheduling degrades the dial or blows the p99.9 gate, we learn it in Phase 0 with numbers, fall back to the ESP-NOW contingency (accepting the coexistence engineering), and no shipped product is touched. Decision is reversible until Phase 1 code lands.

## Default action if Captain does not override
Proceed with A as primary; Phase-0 probe implements A only, with the ESP-NOW rig speced on paper as fallback.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code | Created — F2 decision brief from 5-lens primary-source evidence run (wf_cb736d5e). |
