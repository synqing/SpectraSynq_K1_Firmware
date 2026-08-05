---
abstract: "F2 evidence for the dual-K1 sync transport decision (2026-07-08): quantifies today's K718 BLE-MIDI link duty from the 2026-06-28 phase-G captures (peak 50 msg/s bursts, ~4.3 s; zero drops on the PASS run), computes the multiplier to the proposed 33 Hz / ~100 B sync stream (~1.0-1.7% continuous radio duty vs event-driven bursts), inventories what the WiFi softAP A/B (2026-06-11) and ACF-spread proof (2026-06-30) actually prove about Core-0 headroom vs the 7.5 ms frame budget, and records NimBLE 2.5.0 vendored config actuals (MAX_CONNECTIONS 3, MTU 255, host task Core 0, internal-RAM alloc). All facts [REPO file:line]."
---

<!-- british-english-guard: ignore — "artifacts/" below is the literal repo directory name in evidence-citation paths; prose is British English throughout. -->

# F2 — In-repo duty and headroom quantification for the dual-K1 sync transport

Date: 2026-07-08 · Author: agent:claude-fable-5 (F2-EVIDENCE SSA) · Read-only evidence pass; no device contact, no commits.

Tagging: every fact is `[REPO path:line]`. Numbers explicitly labelled **derived** are computed here from the cited repo facts and are not themselves measurements.

---

## 1. K718 BLE link duty today vs the proposed sync-stream duty

### 1.1 What the current link actually carries (measured, on-silicon)

The only on-device traffic characterisation of the K718→K1 BLE-MIDI link is the 2026-06-28 phase-G 71-control sweep/stress run (K1 = `k1_ble_remoted_probe` on main K1 F887A500, K718 = `JC3636_K718_REMOTED_BLE_V1`):

- **Accepted PASS run (r3):** sweep71 at `interval_ms=12` (67 sent) then stress71, 3 rounds at `interval_ms=20` (201 sent), 268 messages total, `protected_skip=16` [REPO artifacts/ble_midi_71_20260628/phase_g_device_proof/20260628_1529/captures/knob_sweep71_stress71_r3_serial.log: `SWEEP71_BEGIN profile=sweep71 rounds=1 interval_ms=12 count=71` and `SWEEP71_BEGIN profile=stress71 rounds=3 interval_ms=20 count=71` / `SWEEP71_DONE ... sent=201 ... total=213`].
- K1-side final counters on that run: `linked=1 notify=268 decoded=268 enqueued=268 queue_drops=0 decode_errors=0 apply_ok=268 apply_fail=0` [REPO artifacts/ble_midi_71_20260628/phase_g_device_proof/20260628_1529/final_manifest.json:66-81; also tail of k1_sweep71_stress71_r3_serial.log].
- Per-second notify progression on the K1 during that run: 0 → 14 → 60 → 67 → 102 → 144 → 189 → 232 → 268, i.e. **peak measured receive rate ≈ 42-46 notify/s** during the 20 ms-cadence stress phases [REPO artifacts/ble_midi_71_20260628/phase_g_device_proof/20260628_1529/captures/k1_sweep71_stress71_r3_serial.log, 1 Hz `[ble_remoted] counters` lines].
- **A prior 20 ms-cadence attempt (r2) was marginal:** `notify=166 ... enqueued=163 queue_drops=3 ... apply_ok=160 apply_fail=3` [REPO artifacts/ble_midi_71_20260628/phase_g_device_proof/20260628_1529/captures/k1_sweep71_stress71_r2_serial.log], and the manifest records "A prior active BLE treatment attempt at 20 ms cadence showed queue drops and is not accepted as A/B PASS" [REPO artifacts/ble_midi_71_20260628/phase_g_device_proof/20260628_1529/final_manifest.json:95]. The receive queue is a static 16-deep FreeRTOS queue drained from the main-loop poll [REPO SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp:44-48, 245].

**Duty shape (derived):** the stress phase lasts ≈ 213 × 20 ms ≈ **4.3 s**; the full 268-message run spans a ~17-20 s capture (17 counter lines; treatment capture 20.6 s [REPO artifacts/ble_midi_71_20260628/phase_g_device_proof/20260628_1529/ab_ble_active_summary.json:24]). Outside sweeps the link is **event-driven and near-idle**: notifications flow only when the dial moves — the demo build sat at `notify=0` while linked [REPO docs/hardware/im73d-ble-midi-demo-build-2026-07-04.md:60-62]. The K1→K718 mirror is an 8-byte non-response write emitted **only on confirmed-mode change** [REPO SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp:183-202].

Per-message size: BLE-MIDI CC records; the decoder accepts packets up to `K1_BLE_MIDI_MAX_PACKET 247` and up to 16 records per packet [REPO SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_decoder.h:10-11]. A single-control notify is of order 5-15 B of ATT payload (header + timestamp + 1-4 MIDI CC messages; CC14/NRPN state machines in the decoder [REPO k1_ble_midi_decoder.h:20-32]) — **derived bound, no on-air byte capture exists in the repo**.

### 1.2 Multiplier to the sync stream (derived from the above)

Sync stream duty (given): 33 Hz × ~100 B notify ≈ 3.3 kB/s continuous, + 1 Hz beacon (~60-100 B) + control mirror.

| Axis | K718 link today (measured) | Sync stream (proposed) | Multiplier |
|---|---|---|---|
| Packet rate, worst measured burst | 50 msg/s for ≈4.3 s (stress71 @ 20 ms) | 33 pkt/s | **×0.66** on rate — the sync rate is *below* the proven burst rate |
| Packet rate, typical use | ~0 (dial idle; `notify=0` while linked) | 33 pkt/s, continuous | **unbounded** — continuous vs event-driven |
| ATT payload bytes/s, worst burst | ~250-750 B/s (50 × 5-15 B, derived) | ~3,300-3,400 B/s | **×4-13** |
| Duty cycle | bursts of seconds, then idle | 24/7 for the whole show | qualitative step change |
| Concurrent links | 1 (K1 central → K718) | 2 (K718 link **plus** follower link) | ×2 connection events |
| Direction | RX-only + rare 8 B TX mirror | sustained TX (leader) or RX (follower) | new TX duty on leader |

**Derived radio-duty estimate:** at the NimBLE default connection interval (30-50 ms, §3) a data-bearing connection event carrying ~100 B at 1M PHY costs roughly 1-1.5 ms of air/controller time including empty-PDU ack; 33 such events/s ≈ **1.0-1.7 % radio duty for the sync link alone**, plus one near-empty event per interval for the K718 link (~0.3-0.5 %). This is arithmetic, not measurement — no on-air sniff or controller-duty capture exists in the repo.

### 1.3 The honest extrapolation gap in Captain's "100 % uptime" prior

The 100 %-uptime experience was earned on a link that is, in evidence terms:

1. **Mostly idle** — event-driven notifications, zero traffic between dial gestures [REPO docs/hardware/im73d-ble-midi-demo-build-2026-07-04.md:60-62]. It has never carried a continuous stream of any rate for any duration in any repo capture.
2. **Single-connection** — one central link, no second concurrent connection has ever been held by a K1 in any capture (NimBLE default allows 3, §3, but 2-link operation is unexercised).
3. **BLE-only radio** — the demo build (`k1_bench_im73d_ble`) has **no WiFi stack** [REPO platformio.ini:378-390 pattern; docs/hardware/im73d-ble-midi-demo-build-2026-07-04.md:18-33], and the WiFi A/B build (`k1_wireless_ab_probe`) has **no BLE** [REPO platformio.ini:353-365]. BLE+WiFi coexistence on one K1 radio has **never been run**, let alone measured.
4. **Not A/B-closed even for BLE alone:** the BLE interference A/B is formally `DEVICE_BLOCKED` — the K718 wedged before a clean harness-paired active treatment [REPO artifacts/ble_midi_71_20260628/final_manifest.json:60, 83-96]. The only BLE-active AP evidence is a claim-limited scalar heartbeat comparison: control ap_heartbeat p95 1008.7 ms vs BLE-active treatment p95 1013.8 ms (mean 1005.1 vs 893.4 ms over a shorter 20.6 s window), with the file itself stating "Scalar AP cadence comparison only; no causal RF attribution" [REPO artifacts/ble_midi_71_20260628/phase_g_device_proof/20260628_1529/ab_ble_active_summary.json:2-25].
5. **Already showed a load-coupled failure once:** the Core-0 BLE build crashed on first noise-cal via internal-DRAM exhaustion inside `fopen()` (fixed `1ac840a`, device-proven with K718 *unlinked*; the K718-linked+streaming crash-condition repro is **still owed**) [REPO docs/hardware/im73d-ble-midi-demo-build-2026-07-04.md:76-82].

**Bottom line:** "100 % uptime" is a true observation about an idle-dominant, single-link, BLE-only control channel. Extrapolating it to a continuous 33 Hz stream on a second concurrent link, with WiFi possibly also active, spans four unmeasured dimensions at once. It is a *prior*, not evidence, for the sync-stream regime — although the ×0.66 packet-rate multiplier (33 Hz < the proven 50 msg/s burst) means the *rate* itself is not the scary axis; continuity, the second link, and coexistence are.

---

## 2. WiFi absorption evidence — what is proven about Core-0 cost, and what is not

### 2.1 Measured with the WiFi softAP+WebSocket stack ACTIVE (2026-06-11 A/B)

`k1_wireless_ab_probe` = harness + full AP/WS wireless stack (`-DSB_K1_WIRELESS_ENABLED`, WebSockets lib) [REPO platformio.ini:345-365]. Three 90 s ON runs vs three 90 s OFF runs, main K1 F887A500, music stimulus [REPO docs/forensics/runtime-evidence/wireless-ab/20260611/{on,off}_{1..3}.json]:

| Metric (per-run) | OFF (1/2/3) | ON (1/2/3) |
|---|---|---|
| render p95 µs (Core-1 `vpf_frame_us`) | 3987.6 / 3943.0 / 3949.6 | 3982.6 / 3971.0 / 3961.5 |
| render max µs | 39976 / 5485 / 6316 | 5098 / 5644 / 5688 |
| beat lock ratio | 0.864 / 0.864 / 0.955 | 0.835 / 0.972 / 0.873 |
| beat conf mean | 0.825 / 0.850 / 0.846 | 0.811 / 0.833 / 0.728 |
| crash markers / seq gaps | 0 / 0 | 0 / 0 |
| AP status-line cadence p95 jitter | ~1005 ms | ~1006 ms |

[REPO docs/forensics/runtime-evidence/wireless-ab/20260611/on_1.json (full record); off_1.json; on_2/on_3/off_2/off_3.json extracted values]

**What this PROVES:** with the softAP+WS stack up on the shared radio and WiFi task on Core 0, over 3×90 s: no crashes, no VPF sequence gaps, no render-p95 regression (≤ ~40 µs run-to-run noise), and beat lock/confidence within run-to-run spread. Each JSON self-limits the claim: "Scalar symptom capture; not causal attribution" [REPO on_1.json `doctrine_note`].

**What this does NOT measure:** the AP surface in these runs is the **1 Hz status-line cadence** (`ap_cadence` median ~1.005 s), i.e. second-granularity liveness — **not per-frame Core-0 AP microseconds**. No µs-resolution Core-0 AP timing with WiFi active exists anywhere in the repo.

### 2.2 The Core-0 budget numbers (µs-resolution) — measured WITHOUT radio

The ACF work-spreading root-fix carries the only µs-grade Core-0 AP budget proof: "DEVICE-PROVEN at 12.8k/96 (main K1 F887A500, silent A/B): active p95 9088us->6784us, frames over the 7.5ms budget 889/2667->0; 127 BPM lock preserved (100%, conf 0.987)" [REPO platformio.ini:126-133; corroborated REPO docs/handover/2026-06-30-production-readiness-lanes-session-handover.md:17]. That measurement is on the radio-free product-line build.

**Derived headroom:** post-ACF-spread, active-AP p95 6784 µs against the 7.5 ms budget leaves **≈ 716 µs (~9.5 %) p95 headroom on Core 0 — with zero radio load**. Any WiFi (or BLE host) work stealing Core-0 time eats directly into that margin; whether a softAP/STA stack under 3.3 kB/s duplex traffic fits inside 716 µs p95 is **unmeasured**.

### 2.3 Sequencing caveat and the never-measured list

- The WiFi A/B (2026-06-11) **predates** the freeze guard (06-26), ACF spread (06-30), per-band AGC (06-30) and the 12.8k/96 contract era commits — the WiFi-exoneration numbers were taken on a different DSP configuration than today's production build. No post-ACF WiFi-ON run exists.
- **Never measured anywhere in the repo:** (a) device-to-device WiFi (K1↔K1 in any topology); (b) K1 as WiFi **STA** (production doctrine is AP-only, "Do not add K1 STA fallback" [REPO CLAUDE.md, Platform-Native Production Patterns §5]); (c) UDP (or any datagram) latency/jitter on any K1 link — the wireless stack is WebSocket/TCP over softAP [REPO platformio.ini:353-365]; (d) WiFi and BLE **simultaneously** on one K1; (e) Core-0 AP frame µs with any radio active.

---

## 3. NimBLE config actuals (vendored NimBLE-Arduino 2.5.0)

Vendored copy read: `.pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino/` (identical copies exist under `k1_ble_remoted_probe` and `k1_custom`).

| Setting | Value | Source |
|---|---|---|
| `CONFIG_BT_NIMBLE_MAX_CONNECTIONS` | **3** (default; not overridden anywhere in build flags) | [REPO .pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino/src/nimconfig.h:225] |
| Roles | Central, Peripheral, Broadcaster, Observer **all enabled by default** (each `#define ... 1` unless `_DISABLED`) | [REPO nimconfig.h:180-208] |
| `CONFIG_BT_NIMBLE_ATT_PREFERRED_MTU` | **255** | [REPO nimconfig.h:246] |
| `CONFIG_BT_NIMBLE_PINNED_TO_CORE` | **0** — NimBLE host task on Core 0 | [REPO nimconfig.h:213] |
| `CONFIG_BT_NIMBLE_HOST_TASK_STACK_SIZE` | 4096 | [REPO nimconfig.h:217] |
| `CONFIG_BT_NIMBLE_MEM_ALLOC_MODE_INTERNAL` | **1** — NimBLE allocates from internal DRAM (the scarce pool behind the `1ac840a` cal-abort) | [REPO nimconfig.h:220-221] |
| Max bonds / CCCDs | 3 / 8 | [REPO nimconfig.h:233-238] |

**Connection parameters actually requested by the K1 central:** `ble_remoted_central.cpp` makes **no** `setConnectionParams` / `updateConnParams` call — it connects with NimBLE client defaults [REPO SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp:149-181, whole file]. Those defaults are:

- Conn interval **min 30 ms / max 50 ms** (`BLE_GAP_INITIAL_CONN_ITVL_MIN/MAX` = `BLE_GAP_CONN_ITVL_MS(30)/(50)`) [REPO .pio/libdeps/k1_bench_im73d_ble/NimBLE-Arduino/src/nimble/nimble/host/include/host/ble_gap.h:113-116; NimBLEClient.cpp:82-89 `m_connParams{16, 16, ITVL_MIN, ITVL_MAX, ...}`]
- Slave latency **0**, supervision timeout **0x0100 = 2.56 s** [REPO ble_gap.h:121-122]
- Scan interval/window 16/16 (10 ms units) [REPO NimBLEClient.cpp:82-83]

**App-side structure relevant to a sync stream:** BLE app task `xTaskCreatePinnedToCore(ble_task, "ble_remoted", 4096, nullptr, 1, &s_task, 0)` — **Core 0, priority 1** [REPO ble_remoted_central.cpp:235]; static 16-deep record queue, drained from the main loop [REPO ble_remoted_central.cpp:44-48, 239-254]; decoder packet ceiling 247 B [REPO k1_ble_midi_decoder.h:10]. Idle internal-DRAM headroom on the demo build is ~76 KB with a documented transient-dip risk under "BLE link + notify stream + WiFi-AP client + cal-complete fopen" [REPO ble_remoted_central.cpp:272-285 comment].

**Implication (derived):** capacity-wise, the vendored NimBLE build already supports the leader topology (K718 central link + one follower link ≤ 3 connections; peripheral role compiled in; MTU 255 covers a 100 B notify in one PDU). The default 30-50 ms interval also brackets the 30 ms packet cadence — a 33 Hz stream on a 50 ms-interval link would queue ~1.67 packets/event, so the sync link would want explicit conn params (e.g. 15-30 ms interval) rather than defaults; that is a code change, not a config-ceiling problem.

---

## Delegation-relevant summary for F2

- **Rate multiplier is benign; duty-shape multiplier is not.** 33 Hz is below the proven 50 msg/s burst receive rate, but the current link's measured duty is seconds-long bursts on an otherwise idle channel; the sync stream is 24/7, on a **second** concurrent link, with ~10× larger payloads.
- **WiFi is scalar-exonerated at second-granularity on 2026-06-11 hardware/DSP config; Core-0 µs cost with WiFi ON is unmeasured.** The only µs budget proof (p95 6784 µs vs 7.5 ms, ≈716 µs headroom) is radio-free.
- **BLE+WiFi coexistence, K1↔K1 WiFi, STA mode and UDP jitter have zero repo evidence.**
- **NimBLE ceilings are not the constraint** (3 connections, MTU 255, all roles); the constraints in evidence are Core-0 placement of every radio task (NimBLE host, app BLE task, WiFi task — all Core 0 alongside the 7.5 ms audio loop) and internal-DRAM pressure (NimBLE allocates internal; one DRAM-exhaustion crash already materialised and was guarded, not eliminated).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-fable-5 (F2-EVIDENCE SSA) | Created — in-repo quantification: K718 BLE duty vs sync-stream multiplier, WiFi softAP A/B + ACF-spread Core-0 headroom evidence inventory, NimBLE 2.5.0 vendored config actuals. |
