---
abstract: "Phase-0 dual-K1 sync probe: GPIO cross-trigger pin audit + shared serial log-line contract. Audits both K1 pinmaps (main K1 prod: LED 6/7, SPH0645 I2S 13/11/14; bench K1: LED 4/5, IM73D PDM clk13/din12/LR14) against constants.h and proposes TRIG_OUT=GPIO15, TRIG_IN=GPIO16 — provably unused on BOTH maps, non-strap, non-USB, non-flash/PSRAM. Includes physical cross-wiring instructions for Captain and the canonical serial log-line grammar shared by P0.4 firmware and the scripts/dual_sync_probe/ oracle."
---

# Phase 0 — Probe pin audit + serial log-line contract

Lane authority:
[`recovery/recovery-plan.md`](./recovery/recovery-plan.md). Transport ratified:
[`f2-transport-decision.md`](./f2-transport-decision.md).
This document fixes two things the oracle and the P0.4 firmware must agree on: **which two GPIOs carry the wired cross-trigger**, and **the exact serial log grammar** that turns two captured device logs into the four Phase-0 gate numbers.

British English throughout. `artifacts/` in a path is a literal directory name, not a spelling.

## 1. Pin audit

### 1.1 What each device already uses

Both K1 units are the **same** ESP32-S3-DevKitC-1 N16R8 devboard (16 MB quad flash + 8 MB **octal/OPI** PSRAM); only the firmware pin map and the mic differ. Pin macros live in `SPECTRASYNQ_K1_FIRMWARE/system/constants.h` under `#if defined(SB_K1_HARDWARE)` (the K1 block), switched by `SB_K1_BENCH_REFERENCE_PINMAP`.

**Main K1 (leader — production pinmap, SPH0645 I2S):**

| Function | GPIO | Source |
|---|---|---|
| WS2812 primary / secondary (LED_DATA / LED_CLOCK) | 6, 7 | `constants.h:329-330` |
| SPH0645 I2S BCLK / LRCLK / DIN | 13, 11, 14 | `constants.h:325-327` |
| I2C SDA / SCL (M5ROTATE8 encoder bus) | 17, 18 | `constants.h:345-346` |
| RNG seed / raw output | 8 | `constants.h:357`, also `audio/audio_transfer.h:172` (`pinMode(8, OUTPUT)`) |
| Physical controls + sweet-spot LEDs | −1 (disabled) | `constants.h:348-355` |

Main K1 occupied set: **{6, 7, 8, 11, 13, 14, 17, 18}**.

**Bench K1 (follower — bench-reference pinmap, IM73D122 PDM mic):**

| Function | GPIO | Source |
|---|---|---|
| WS2812 primary / secondary | 4, 5 | `constants.h:310-311` |
| IM73D PDM CLK / DIN / LR (active under `K1_MIC_IM73D_PDM_V1`) | 13, 12, 14 | `constants.h:318-320`; driven output at `audio/i2s_audio.h:226` |
| SPH0645 I2S pads (defined but UNUSED under the PDM flag) | 14, 12, 13 | `constants.h:306-308` (macros retained, not driven) |
| I2C SDA / SCL | 17, 18 | `constants.h:345-346` |
| RNG seed / raw output | 8 | `constants.h:357`, `audio/audio_transfer.h:172` |
| Physical controls + sweet-spot LEDs | −1 (disabled) | `constants.h:348-355` |

Bench K1 occupied set: **{4, 5, 8, 12, 13, 14, 17, 18}**.

The encoder is an **I2C** peripheral on 17/18 (`persistence/encoders.h:67` toggles `SCL_PIN`), not a dedicated GPIO — no extra pins to avoid there. Buttons (`system/system.h:377,380`) read `noise_button.pin` / `mode_button.pin`, both `−1` on K1, so no button GPIO is live.

**Union occupied across BOTH devices: {4, 5, 6, 7, 8, 11, 12, 13, 14, 17, 18}.**

### 1.2 Reserved / unsafe pins on ESP32-S3 N16R8 (must also avoid)

- **Strapping pins:** 0, 3, 45, 46 (boot mode / JTAG-source / VDD_SPI voltage / boot strap). Driving these at reset is unsafe. (Per brief; ESP32-S3 strapping spec.)
- **Native USB D−/D+:** 19, 20 — the CDC serial path we depend on for log capture.
- **Default UART0 TX/RX:** 43, 44 — avoid so no serial/boot-log path is disturbed.
- **On-board addressable RGB LED:** 38 (DevKitC-1 v1.1) / 48 (v1.0) — board-revision dependent, so avoid **both** 38 and 48.
- **SPI flash + OPI PSRAM:** GPIO **26–37** are consumed by the quad flash (26–32) *and* the octal PSRAM (33–37) on N16R8. The brief cites "26–32"; the non-K1 devkit branch of `constants.h:363-368` reuses 33–37 for a *different* board, which confirms 33–37 are the OPI data lanes on the S3 and are unavailable here. Treat all of **26–37** as forbidden.
- ESP32-S3 has no GPIO 22–25 (they do not exist on this part).

### 1.3 Proposed trigger pins

Free, interrupt-capable, and unreferenced on **both** pinmaps:

| Device | Role | TRIG_OUT | TRIG_IN |
|---|---|---|---|
| Main K1 (`k1_sync_probe_main`, leader) | leader | **GPIO 15** | **GPIO 16** |
| Bench K1 (`k1_sync_probe_bench`, follower) | follower | **GPIO 15** | **GPIO 16** |

Same pin numbers on both units because the devboards are identical and neither map touches 15 or 16.

**"Unused" proof — GPIO 15 and GPIO 16 appear in NO pin macro and NO GPIO call in the firmware tree.** A whole-tree grep of `SPECTRASYNQ_K1_FIRMWARE/` for pin/GPIO uses of 15 or 16 (across `#define *_PIN`, `pinMode`, `digitalRead/Write`, `attachInterrupt`, `gpio_*`, `GPIO_NUM_*`) returns zero hits; the only occupied pins are the union set in §1.1. Both are valid ESP32-S3 GPIOs (ADC2_CH4 / ADC2_CH5), non-strapping, outside the USB, UART0, RGB-LED and flash/PSRAM ranges, and support GPIO interrupts (all S3 GPIOs do). ADC2 is unused by this firmware and irrelevant to digital I/O; BLE (not WiFi) is the radio, so there is no ADC2/WiFi contention.

### 1.4 Physical wiring (for Captain)

Two signal jumpers, crossed, plus one common ground. With both units powered over their own USB (identity is by chip ID, not port):

```
  Main K1 (leader)                    Bench K1 (follower)
  ----------------                    -------------------
  GPIO 15 (TRIG_OUT) ───────────────► GPIO 16 (TRIG_IN)
  GPIO 16 (TRIG_IN)  ◄─────────────── GPIO 15 (TRIG_OUT)
  GND                ───────────────── GND   (common reference — REQUIRED)
```

- Three wires total: main-15 → bench-16, bench-15 → main-16, and a GND↔GND strap.
- The common ground is mandatory: without it the ISR edge reference floats and the wire-truth offset is meaningless.
- No series resistor needed for a short bench jumper (both are 3V3 push-pull GPIOs); keep leads short. Do not connect either trigger line to 5 V.
- These pins are output-low / input at boot for the probe; they are never driven by production firmware (the probe TU is `-DSB_K1_SYNC_PROBE`, non-shippable).

## 2. Serial log-line contract — version 2

Firmware writes device-local records. The capture helper prefixes every
recognised proof line from both open ports with a timestamp from one shared
host-monotonic origin:

```text
host_us=<u64> <firmware-record>
```

Independent per-port origins are forbidden because they cannot prove that the
leader and follower connection epochs overlap.

The parser has two deliberate modes:

- permissive mode reads archived version-1 captures, including health without
  `role` and clock lines without a local timestamp;
- strict proof mode, required for F2/F3, requires a leading `host_us`, consumes
  the entire versioned record, and rejects duplicate keys, trailing fields,
  missing/wrong roles and untimestamped follower clock records. Contract/input
  errors exit `4`.

### 2.1 Version-2 records

All numeric fields are decimal. Device-local timestamps use 64-bit extended
`micros()` and may not wrap within a proof run.

| Emitter | Exact grammar |
|---|---|
| role initialisation | `[k1_sync] begin role=<leader\|follower>` |
| settled usable link | `[k1_sync] link up role=<leader\|follower> epoch=<u32> handle=<u16> mtu=<u16>` |
| link loss | `[k1_sync] link down role=<leader\|follower> epoch=<u32> reason=<i32>` |
| settled BLE values | `[k1_sync] negotiated role=<leader\|follower> epoch=<u32> interval_units=<u16> latency=<u16> mtu=<u16> phy_tx=<u8> phy_rx=<u8>` |
| device raised TRIG_OUT | `[sync_oracle] trig_out seq=<u32> t_us=<u64>` |
| device ISR captured TRIG_IN | `[sync_oracle] trig_in seq=<u32> t_us=<u64>` |
| follower clock estimate | `[k1_sync] clk role=follower t_local_us=<u64> est_offset_us=<i64> rtt_us=<u32> n=<u32>` |
| leader stream send | `[k1_sync] tx seq=<u32> t_leader_us=<u64>` |
| follower stream receive | `[k1_sync] rx seq=<u32> t_leader_us=<u64> t_local_us=<u64>` |
| follower scheduled consume | `[k1_sync] apply seq=<u32> t_render_us=<u64>` |
| 1 Hz health | `[k1_sync] health role=<leader\|follower> fps=<f> heap_min=<u32> ap_p95_us=<u32> dial_linked=<0\|1> loss=<u32> dup=<u32> [honest-extra=<value> ...]` |
| host segment marker | `[sync_host] segment name=<token> phase=<start\|end> t_host_us=<u64>` |

`t_host_us` in a segment marker must equal its leading `host_us`.

`link up` means application-usable, not merely a raw GAP connection. Both
stream and clock subscriptions must be established before either role emits
it. A request-submission return is not a negotiated-value measurement.
Connection interval, latency, MTU and PHY are settled values. DLE remains
`REQUESTED_UNVERIFIED` unless a lower-level proof surface is added.

Role-local epoch counters need not have the same numeric value. The host-time
overlap and each role's own negotiation epoch establish coherence.

### 2.2 Link Ready and integrity

Only evidence at or after each role's sole `link up` is eligible. Pre-link
records, records from a disconnected epoch and accumulated reconnect counts
cannot certify readiness.

Link Ready is `PASS` only when:

1. both roles have one overlapping, positive-duration connection epoch;
2. neither log contains a reset, link-down or reconnect;
3. each role records one post-link negotiated record matching its own epoch;
4. leader unique TX count is at least 300;
5. follower unique RX and apply counts are each at least 300;
6. the follower has at least 10 timestamped clock records;
7. at least 10 complete four-event GPIO rounds exist;
8. transport expected count is non-zero; and
9. TX/RX/apply sequences are dense where required, monotonic, non-duplicated
   and contain no unexpected RX or apply sequence.

Each GPIO round uses the same sequence in both directions. The oracle derives
the wire-truth offset and ISR asymmetry from the four paired events.
`est_offset_us` is `follower_local − leader_local`, so clock error is
`est_offset_us − wire_truth`.

Integrity is split and must not be collapsed:

- transport: leader TX → follower RX;
- application consume: follower RX → follower apply.

The silicon-shaped `drop10` control preserves RX and omits apply. It is an
application-loss fault, not transport loss.

### 2.3 Verdict schema

Every gate and the overall verdict uses:

`PASS | FAIL | BLOCKED | UNMEASURED`

- `overall_status` is the enum.
- `overall_pass` is true only when `overall_status == "PASS"`.
- CLI exits are `0=PASS`, `1=FAIL`, `2=BLOCKED`, `3=UNMEASURED`,
  `4=contract/input error`.
- Zero observations are `BLOCKED`.
- Missing instrumentation is `UNMEASURED`.
- Link Ready not-PASS blocks all timing gates.

The measured gates are:

1. clock-offset error p95 ≤ 4000 µs;
2. leader-stamp→follower-consume lateness p99.9 ≤ 30000 µs;
3. leader-stamp→follower-consume worst case ≤ 50000 µs; and
4. per-role health, leader dial uptime, transport/application integrity and
   honest instrumentation.

Gate 3 is not mic→LED and must not be described that way. A firmware health
field named `ws2812_glitch` does not prove a physical glitch. Until an explicit
physical instrument contract exists, `physical_ws2812_glitch` remains
`UNMEASURED` and prevents overall PASS.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code | Created — GPIO cross-trigger pin audit (TRIG_OUT 15 / TRIG_IN 16, both maps) + shared serial log-line contract for P0.3 oracle and P0.4 firmware. |
| 2026-07-27 | Codex SSA orchestrator | Version 2 — strict shared-host-time grammar, coherent Link Ready epoch, role-specific health, split transport/apply integrity and explicit verdict/exit schema. |
