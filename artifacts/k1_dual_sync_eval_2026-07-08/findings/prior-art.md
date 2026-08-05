---
abstract: "External prior art for dual-K1 sync (2026-07-08): WLED UDP sync/realtime/sound-sync protocols with packet formats and rates; ESP-NOW latency (5-6 ms per packet, ~80 us broadcast jitter, buffering pathology below 20 ms spacing); BLE MIDI measured latency (ESP32 Bluedroid 14.6 ms median vs NimBLE 45 ms; WIDI 3-10 ms) and BLE 5 2M PHY throughput (~102.5 KB/s measured); commercial sync architectures (Hue 25 Hz Zigbee, Twinkly/Nanoleaf single-master); clock-sync options (ESPNowMeshClock us-level, esp-now SDK time sync, WiFi TSF requires AP association). Read before choosing the dual-K1 transport."
---

# Prior Art — Multi-Device Synchronised LED / Music Systems

Research lane: dual-K1 sync (two K1s merge into one widened ~320-LED surface; each K1 has 160 native LEDs — verified locally at `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:109` `#define NATIVE_RESOLUTION 160`). Candidate transport under study: BLE MIDI piggyback. This document records external evidence only; no design decision is made here.

Confidence tags: **[READ]** = source page fetched and read directly this session; **[SEARCH]** = number quoted inside a web-search result snippet, primary page not independently read — treat as plausible, re-verify before it becomes load-bearing.

---

## (a) WLED — UDP sync family (the closest open-source analogue)

WLED ships three distinct sync mechanisms, and the distinction between them is the single most useful lesson in this corpus: **state sync, pixel streaming, and audio-feature sync are three different products.**

### 1. UDP Notifier ("WLED Sync") — state sync, not frame sync **[READ]**
- Source: https://kno.wled.ge/interfaces/udp-notifier/
- 24-byte UDP broadcast on port 21324 (default), sent **only when a value changes** on the sending device, not continuously.
- Payload (byte-indexed, versioned for cross-version interop): packet-purpose byte, callMode, master brightness, primary RGBW, nightlight state, effect index, effect speed, effect intensity, secondary RGBW, transition duration (16-bit), FastLED palette index, protocol version byte.
- Receivers filter what they apply (brightness / colour / effects checkboxes); a receiver does not adopt sender state on boot — it waits for the next packet.
- **Limitation for the K1 use case:** each device runs its own animation clock; only effect *parameters* are synced. Time-based effects drift between devices. There is no per-frame phase alignment and no notion of a split surface.

### 2. UDP Realtime (WARLS / DRGB / DRGBW / DNRGB) — pixel streaming **[READ]**
- Source: https://kno.wled.ge/interfaces/udp-realtime/
- Byte 0 selects protocol; byte 1 is a timeout in seconds (return to normal mode after last packet; 255 = stay in realtime).
- Formats and per-packet capacity:

| Byte 0 | Protocol | Encoding | Max LEDs/packet |
| --- | --- | --- | --- |
| 1 | WARLS | 4 B/LED (index + RGB) | 255 |
| 2 | DRGB | 3 B/LED, positional | 490 |
| 3 | DRGBW | 4 B/LED, positional | 367 |
| 4 | DNRGB | 2-byte start index + 3 B/LED | 489/packet |

- Recommended sender frame rate 15–30 FPS (audio-reactive-led-strip integration guidance).
- **Spanning pattern:** multiple WLED devices are driven as one surface by broadcasting to `X.X.X.255` with the LED count of the largest device, and each device applies its own **WARLS offset** to select its window of the virtual strip. This is exactly the "one virtual surface, each device renders its half" topology the K1 lane is studying — implemented as master-streams-pixels, followers-are-dumb-sinks.
- **Limitation:** at 320 virtual LEDs × 3 B × 100 FPS ≈ 96 KB/s of pixel traffic — trivial for WiFi UDP, far beyond practical BLE MIDI throughput (see §c).

### 3. UDP Sound Sync (WLED-SR / MoonModules) — audio-feature sync **[READ]**
- Sources: https://mm.kno.wled.ge/WLEDSR/UDP-Sound-Sync/ and https://kno.wled.ge/interfaces/udp-realtime/ (§UDP Sound Sync v2)
- A 'master' device with a microphone transmits **pre-processed summary audio data** (treated by receivers as a discrete microphone sample, including FFT data between ESP32s) via UDP *multicast* `239.0.0.1:11988`.
- Rate: **one packet every ~20 ms; an external sender may be slower but not faster than 20 ms = 50 fps** (v2 documentation).
- Receivers **disable their own microphone sampling and FFT** and substitute the network audio. Animations are *not* synced — each device runs its effect locally against shared audio features.
- Known operational pain: UDP multicast unreliable on consumer WiFi routers; WLED docs insist on "Disable WiFi sleep" ("caused us innumerable problems").
- Standalone library for the same packet format: https://github.com/netmindz/WLED-sync
- **Relevance:** this is the strongest architectural precedent for K1 — one K1 remains the audio authority and publishes semantic features (analogous to AudioSemanticState) rather than pixels. WLED's experience shows the failure mode is transport reliability, not bandwidth.

---

## (b) ESP-NOW LED sync — latency and reliability numbers

- ESP-NOW is a connectionless 802.11 action-frame protocol: **250 bytes usable payload, typically 1 Mbps PHY rate**, no AP required. Sources: Electric UI benchmark **[READ]** (https://electricui.com/blog/latency-comparison), Espressif docs.
- **Electric UI microbenchmark [READ]:** across 12 wireless links tested (>200 test runs), ESP-NOW placed in the **top three lowest upper-quartile latency** for 12 B and 128 B payloads, alongside nRF24 and raw 802.15.4 (ESP32-C6 802.15.4 measured 2.5 ms @ 12 B, 8.7 ms @ 128 B for comparison). The top three all degrade to BLE-class latency at 1 KiB payloads because of small MTUs.
- **Buffering pathology [READ]:** espressif/esp-now issue #115 (https://github.com/espressif/esp-now/issues/115) — 140-byte packets sent at <20 ms spacing through the esp-now component caused average 50 ms / max 200 ms delays (buffer build-up); with >20 ms spacing each packet delivered in the **5–6 ms** range. Lesson: sub-frame-rate command traffic is fine; naive high-rate streaming through the component wrapper is not.
- **[SEARCH]** community measurements: <1 ms round-trip for ~95% of packets with deviations of 2–3 ms and max ~6 ms (micropython ESPNOW characterisation, https://github.com/orgs/micropython/discussions/11757 — fetched but numbers not independently located in page text this session); broadcast to 5 slaves showed inter-slave **jitter ≈ 80 microseconds** (Arduino forum broadcast test, https://forum.arduino.cc/t/esp-now-broadcast-transmisison-latency/1347159).
- **Reliability [READ]:** Espressif indoor study (https://developer.espressif.com/blog/reliability-esp-now/) — 8 nodes at 4 packets/s: only ~50% of node placements were "reliable"; packet loss dominated by wall count/structure; range up to 200 m open-space claim. Recommendation from the authors: application-level delivery control is required.
- **Constraint for K1:** ESP-NOW and a SoftAP can coexist (same radio), but K1 currently runs WiFi AP for Tab5 control — channel coupling between AP and ESP-NOW peers is a real design constraint to evaluate, not researched here.

---

## (c) BLE MIDI on ESP32 — throughput, latency, jitter

### Protocol-level facts
- **BLE-MIDI 1.0 spec [SEARCH — spec PDF located, not read]:** every message carries a **13-bit millisecond timestamp** (max 8,191 ms, monotonically increasing, split across header/timestamp bytes). Purpose per spec: preserve inter-event spacing at the receiver, i.e. **remove connection-interval jitter by scheduling, not by transport**. Source: https://www.hangar42.nl/wp-content/uploads/2017/10/BLE-MIDI-spec.pdf
- Apple constraints **[SEARCH]**: minimum connection interval **11.25 ms on iOS, 7.5 ms on macOS**; Apple accessory guidelines cite 15 ms minimum interval. (https://developer.apple.com/forums/thread/7496, Nordic DevZone BLE-MIDI timing blog.)
- BLE spec minimum connection interval: **7.5 ms** — hard floor on per-event latency quantisation for connection-oriented BLE. Electric UI **[READ]**.

### Measured ESP32 numbers
- **Electric UI [READ]** (ESP32, GATT, 12 B payload unless stated):
  - **Bluedroid**: server Notification median **14.6 ms**; client Write-Without-Response median **20 ms** (outliers past 40 ms). 128 B = **21 ms**; 1 KiB = **31 ms**. Latency distribution bands ~7 ms apart, correlating with the 7.5 ms connection interval.
  - **NimBLE**: Notification median **45 ms**, Write **28 ms**; 128 B = 32 ms; 1 KiB = 57 ms; outliers to 150 ms — "meaningfully slower and far less consistent than the Bluedroid stack" in this benchmark.
  - For reference, nRF52840 (Zephyr) achieved median 13.4 ms @ 12 B with direction-independent behaviour.
- **Throughput [SEARCH]:** GATT-notification throughput between 56 and 128 kbps depending on OS-enforced parameters (Electric UI/Memfault-derived); ESP32-S3 NimBLE user measurement **102.5 KB/s with 2M PHY vs 68.6 KB/s with 1M PHY** (https://esp32.com/viewtopic.php?f=13&t=40607); Espressif FAQ: 2M PHY theoretical max ≈ **1.4 Mbps ≈ 170 KB/s** (https://docs.espressif.com/projects/esp-faq/en/latest/software-framework/bt/ble.html).
- **2M PHY availability:** BLE 5 features (2M PHY, extended advertising, coded PHY) are present on ESP32-S3/C3-class chips, not the original ESP32 **[SEARCH]** (ESP-IDF ESP32-S3 Bluetooth overview). K1 is ESP32-S3, so 2M PHY is in reach *if* the peer negotiates it.
- **Commercial BLE MIDI reference (CME WIDI, nRF-based) [READ]** (https://www.cme-pro.com/the-truth-about-bluetooth-midi/): oscilloscope-measured device-to-device latency **3 ms best / 10 ms worst / 5–6 ms average**; **group mode (1 central + up to 4 peripherals) deliberately extends the connection interval and measurably increases jitter**; groups capped at 4 peripherals to keep jitter "acceptable"; MIDI clock over a direct pair is "rock solid", over groups it is not.

### Synthesis for the K1 candidate transport
BLE MIDI between two ESP32-S3s is realistic for **event/feature/beat-phase traffic** (tens of bytes per event, ~7.5–15 ms delivery quantum, ~5–20 ms typical one-way latency depending on stack) and unrealistic for pixel streaming (a 160-LED half-frame at 100 FPS needs ~48 KB/s sustained *minimum*, at the edge of measured GATT throughput and hostage to connection-interval scheduling). The BLE-MIDI 13-bit timestamp mechanism is directly reusable prior art for jitter-free event scheduling across the seam.

---

## (d) Commercial multi-panel music-reactive sync architectures

| Product | Audio source / clock master | Distribution | Rate | Source |
| --- | --- | --- | --- | --- |
| Philips Hue Entertainment | Streaming app is master; bridge re-times | App → bridge: UDP+DTLS 1.2 PSK, port 2100, ≤10 channels/packet; bridge → lights: custom Zigbee unicast to a proxy node, then **non-repeating MAC-layer broadcast** heard by all nearby lights simultaneously | App may stream 50–60 Hz; bridge caps Zigbee at **25 Hz** | iotech.blog **[READ]** https://iotech.blog/posts/philips-hue-entertainment-api/ |
| Nanoleaf Rhythm | Rhythm mic module attached to the panel chain; single controller renders all panels | Panels are one logical display behind one controller (wired link-bus) — no cross-device RF sync problem exists | n/a | **[SEARCH]** Nanoleaf forum/manuals |
| Twinkly Music | Dedicated USB mic dongle with on-board DSP + BPM counter; works with app closed | Dongle broadcasts to Twinkly devices/groups over WiFi; grouped devices "act as one giant display" with a master device per group | not published | **[SEARCH]** twinkly.com product/help pages |

**Pattern across all three:** exactly one audio/clock authority; followers never analyse audio themselves; the last hop to multiple fixtures prefers a *broadcast* primitive (Zigbee MAC broadcast, WiFi/UDP) so all fixtures hear the same frame at the same instant. Nobody does symmetric peer-to-peer audio analysis on both fixtures.

---

## (e) Clock synchronisation techniques for two ESP32s (sub-10 ms target)

1. **ESP-NOW broadcast time sync — ESPNowMeshClock [READ]** (https://github.com/Hemisphere-Project/ESPNowMeshClock): distributed mesh clock over ESP-NOW claiming "wireless micro-seconds accuracy"; 10-byte broadcast ("MCK" + 56-bit timestamp) every ~1000 ms ± 10% random variation; receivers **forward-only slew** toward the most advanced clock with a smoothing parameter (`slew_alpha`, default 0.25) explicitly "so jumps are absorbed rather than causing AV/motion artefacts"; large-step threshold 10,000 us; built on a 64-bit hardware timer. Purpose-built for synchronised DMX/MIDI/lighting.
2. **Espressif esp-now SDK internal time sync [READ]** (https://docs.espressif.com/projects/esp-now/en/latest/esp32/api-reference/time/espnow_time.html): official Initiator/Responder module — initiator broadcasts authoritative time and never adjusts its own clock; responder adjusts and can request sync (`espnow_time_responder_request`, non-blocking, event on completion). No accuracy figure published on the page read.
3. **WiFi TSF:** 802.11 stations synchronise their hardware TSF counters to AP beacons; ESP-IDF exposes `esp_mesh_get_tsf_time()` in mesh contexts. **Hard caveat [SEARCH]:** with pure ESP-NOW (no AP association) **the WiFi TSF is zero** — TSF-based sync requires an AP/STA relationship (https://www.esp32.com/viewtopic.php?t=33611). K1 already runs a SoftAP; a second K1 joining as STA would inherit beacon-disciplined TSF — plausible but **not verified for SoftAP mode in this session**.
4. **Local oscillator quality [SEARCH → ESP-IDF docs]:** ESP32 `esp_timer` gives 1 us resolution from APB_CLK with < ±10 ppm frequency deviation (https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/system/system_time.html). At 10 ppm, two free-running units drift ≤ 20 us/s relative — a re-sync every few seconds holds alignment orders of magnitude inside a 10 ms budget; even a 60 s resync interval bounds drift at ~1.2 ms.
5. **BLE path:** no off-the-shelf ESP32 BLE clock-sync library surfaced in this research. The BLE-MIDI 13-bit ms timestamp (§c) provides *event* scheduling to ~1 ms granularity without a shared wall clock, which may be sufficient for beat-phase alignment; an NTP-style exchange over GATT is feasible in principle but no measured ESP32 implementation was found this session.

**Bottom line for (e):** sub-10 ms mutual clock alignment between two ESP32s is a solved problem several times over; ESP-NOW broadcast sync reaches tens-of-microseconds class, and even coarse periodic offset exchange beats the 10 ms bar comfortably given ±10 ppm oscillators. The binding constraint is transport coexistence (BLE + SoftAP + optional ESP-NOW on one radio), not sync mathematics.

---

## Numbers (consolidated)

| Quantity | Value | Source |
| --- | --- | --- |
| K1 LEDs per device (local verification) | 160 (`NATIVE_RESOLUTION`) | constants.h:109 **[READ]** |
| WLED notifier packet | 24 bytes, port 21324, on-change | kno.wled.ge udp-notifier **[READ]** |
| WLED DNRGB capacity | 489 LEDs/packet, 3 B/LED | kno.wled.ge udp-realtime **[READ]** |
| WLED realtime recommended rate | 15–30 FPS | kno.wled.ge udp-realtime **[READ]** |
| WLED Sound Sync rate | 1 packet/~20 ms (max 50 fps), multicast 239.0.0.1:11988 | kno.wled.ge udp-realtime §v2 **[READ]** |
| ESP-NOW payload / PHY | 250 B / 1 Mbps typical | Electric UI **[READ]** |
| ESP-NOW per-packet delivery (>20 ms spacing) | 5–6 ms | esp-now issue #115 **[READ]** |
| ESP-NOW pathological buffering (<20 ms spacing, 140 B) | avg 50 ms, max 200 ms | esp-now issue #115 **[READ]** |
| ESP-NOW broadcast inter-receiver jitter | ~80 us (5 slaves) | Arduino forum **[SEARCH]** |
| ESP-NOW indoor reliability | ~50% of node placements reliable through walls | Espressif blog **[READ]** |
| BLE min connection interval | 7.5 ms (spec); 11.25 ms iOS / 7.5 ms macOS (Apple) | Electric UI **[READ]** / Apple forum **[SEARCH]** |
| ESP32 Bluedroid BLE notify median (12 B) | 14.6 ms (128 B: 21 ms; 1 KiB: 31 ms) | Electric UI **[READ]** |
| ESP32 NimBLE BLE notify median (12 B) | 45 ms, outliers to 150 ms | Electric UI **[READ]** |
| BLE GATT throughput (practical) | 56–128 kbps | Electric UI/Memfault **[READ/SEARCH]** |
| ESP32-S3 BLE 2M PHY measured throughput | 102.5 KB/s (1M PHY: 68.6 KB/s); theoretical ≈170 KB/s | esp32.com forum / ESP-FAQ **[SEARCH]** |
| BLE MIDI device-to-device (WIDI, nRF) | 3 ms best / 5–6 ms avg / 10 ms worst; groups ≤4 peripherals, higher jitter | cme-pro.com **[READ]** |
| BLE-MIDI timestamp | 13-bit ms, max 8,191 ms | BLE-MIDI 1.0 spec **[SEARCH]** |
| Hue Entertainment | app 50–60 Hz → bridge Zigbee 25 Hz, ≤10 channels/packet, UDP+DTLS :2100 | iotech.blog **[READ]** |
| ESPNowMeshClock sync beacon | 10 B every ~1000 ms ±10%, us-class accuracy claim, slew-limited | GitHub README **[READ]** |
| ESP32 oscillator stability | < ±10 ppm, 1 us timer resolution → ≤20 us/s mutual drift | ESP-IDF docs **[SEARCH]** |
| Pixel-stream cost for 320-LED surface @100 FPS | ~96 KB/s (RGB) — WiFi-trivial, BLE-marginal | arithmetic from above |

---

## Risks (evidence-backed)

1. **NimBLE latency on ESP32 measured 3× worse than Bluedroid** in the only controlled benchmark found (45 ms vs 14.6 ms median notify) — if the K1 BLE MIDI stack is NimBLE-based, measured-on-K1 numbers must precede any transport decision.
2. **BLE MIDI throughput ceiling** makes pixel streaming across the seam non-viable; only event/feature sync fits. Any architecture that later grows toward pixel hand-off would force a transport change.
3. **ESP-NOW buffering collapse below ~20 ms packet spacing** (issue #115) means a naive per-frame (10 ms) message cadence over the esp-now component is exactly the pathological regime.
4. **Radio coexistence untested:** K1 simultaneously running SoftAP (Tab5), BLE MIDI, and any new sync transport shares one 2.4 GHz radio; none of the external numbers above were measured under that load.
5. **UDP multicast unreliability on consumer routers** is WLED's dominant field complaint for exactly this feature class — relevant if the K1s sync over the K1 AP's WiFi.
6. **Search-derived numbers** (2M PHY throughput, 80 us jitter, Apple intervals, BLE-MIDI spec fields) were not refutation-checked against primary pages this session.

## Open questions

1. Does the K1 SoftAP expose a beacon-disciplined TSF usable by a STA-joined second K1 (`esp_wifi` TSF APIs in SoftAP mode)? Not verified.
2. Which BLE stack does the existing K1 BLE MIDI capability use (NimBLE vs Bluedroid), and what MTU/connection interval does it negotiate today? (Local-code question — owned by the BLE MIDI reader lane, not this external lane.)
3. Can ESP32-S3 ↔ ESP32-S3 BLE negotiate 2M PHY + DLE in the existing MIDI service, and what does that do to the 7.5 ms interval floor in practice?
4. What accuracy does the Espressif esp-now time-sync module actually achieve? (No figure published on the page read.)
5. Hue's Zigbee MAC-layer broadcast final hop is the cleanest "all fixtures hear the same frame simultaneously" primitive — is there an equivalent single-transmission primitive available to two K1s (ESP-NOW broadcast qualifies; BLE connection-oriented traffic does not)?

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (SSA prior-art reader) | Created — external prior art for dual-K1 sync: WLED UDP protocols, ESP-NOW latency/reliability, BLE MIDI/BLE 5 numbers, commercial sync architectures, ESP32 clock-sync techniques, with consolidated numbers table, risks, and open questions. |
