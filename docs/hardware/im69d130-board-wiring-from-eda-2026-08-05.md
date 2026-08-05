# IM69D130 Dual-Mic Board — Wiring Authority (from EDA)

**Date:** 2026-08-05  
**Status:** VERIFIED from EDA schematic + fab PCB pad-nets (docs only; no firmware / env / flash).  
**Task:** `im69d130-eda-wiring`  
**EDA root:** `/Users/spectrasynq/SpectraSynq-EDA/im69d130-stereo-mic`  
**Companion design:** [`im69d130-dual-mic-eval-design-2026-08-05.md`](./im69d130-dual-mic-eval-design-2026-08-05.md)

---

## 1) Board inventory — what proves the pinout

| Artefact | Path | What it proves |
|---|---|---|
| Final schematic snapshot | `…/fab-final-2026-07-19/snapshots/SCH-FINAL.txt` | Live net names on J1, IM1/IM2, SELECT straps, level-shifter chain (`CLK_IN_3V3`, `DATA_OUT_3V3`, `PDM_CLK`, `PDM_DATA`, `SEL_IM1`, `SEL_IM2`) |
| PCB pad-nets (fab) | `…/fab-final-2026-07-19/snapshots/PCB3-INSPECT.txt` (`PAD_NET` on designator `J1` / `e14`) | J1 pin↔net: 1=`PWR_3V3_IN`, 2=`GND`, 3=`CLK_IN_3V3`, 4=`GND`, 5=`DATA_OUT_3V3`, 6=`GND` |
| SELECT strap canon | `…/SEL-STRAP-TOPOLOGY.html` | R7 FIT / R9 DNP / R13 DNP / R14 FIT; IM1 HIGH, IM2 LOW |
| Ratified J1 map | `…/V2.0-4LAYER-CHANGE-ORDER.md` §RATIFIED ARCHITECTURE (lines 25–26) | Same 6-pin host map; pin 4 retired from LRCLK → GND |
| Netlist handoff | `…/deeppcb-handoff/HANDOFF.md` §3 | Full signal chain incl. U1/U3 translation |
| BOM (R1 fix) | `…/fab-final-2026-07-19/bom-r1-fix-2026-07-26/BOM_PCB3_R1fix.csv` | Fitted 0 Ω: `R7,R8,R14,R23` (confirms R7+R14 FIT; R9/R13 absent = DNP) |
| Parts | same BOM | `J1` = `BM06B-GHS-TBT(LF)(SN)` (JST GH 6P SMT); `IM1,IM2` = `IM69D130V01XTSA1` |
| Canon index | `…/00-CANON.md` | Warns stale LRCLK text elsewhere; **live schematic wins for J1** |

**Not authoritative alone:** FlyingProbe export labels J1.5 / U3.B-side as `NET_3` (`FlyingProbeTesting.json`) — that is a Gerber/probe rename. PCB `PAD_NET` + schematic still name the net `DATA_OUT_3V3`. Copper to J1 pad 5 is on net `DATA_OUT_3V3` (`LINE e1821` in PCB3-INSPECT/WTF).

---

## 2) Net / pin table — dual IM69D130 host interface

### 2.1 Connector J1 (host-facing, all 3.3 V)

Connector: **JST GH SMT top-entry 6-pin** `BM06B-GHS-TBT` (LCSC C189892).  
Source: SCH-FINAL wires `e14624`…`e14645` + PCB `PAD_NET` `e14` pads 1–6.

| J1 pin | Net (verbatim) | Direction (host view) | Role |
|---|---|---|---|
| 1 | `PWR_3V3_IN` | Host → board | 3.3 V supply in |
| 2 | `GND` | — | Return |
| 3 | `CLK_IN_3V3` | Host → board | PDM clock (3.3 V logic) |
| 4 | `GND` | — | Return (was LRCLK; retired) |
| 5 | `DATA_OUT_3V3` | Board → host | PDM data (3.3 V logic, after U3) |
| 6 | `GND` | — | Return |

**SELECT is not on J1.** There is no host GPIO for L/R on this board.

### 2.2 Mic-side nets (1.8 V domain, on-board)

| Net (verbatim) | Members (from SCH-FINAL / HANDOFF) |
|---|---|
| `PDM_CLK` | Shared clock to **IM1** and **IM2** (after U1 + R21) |
| `PDM_DATA` | Wired-OR bus: `IM1_DAT` via R6 + `IM2_DAT` via R12 → RC → R23 → U3 |
| `IM1_DAT` | IM1 data pin only |
| `IM2_DAT` | IM2 data pin only |
| `MIC_L_VDD` | IM1 VDD island (from `PWR_1V8` via R24) |
| `MIC_R_VDD` | IM2 VDD island (from `PWR_1V8` via R25) |
| `SEL_IM1` | IM1 SELECT pin |
| `SEL_IM2` | IM2 SELECT pin |
| `PWR_1V8` | LDO G1 (LP5907-1.8) output |

### 2.3 Mic pad nets (FlyingProbe / SCH)

| Designator | Pad | Net |
|---|---|---|
| IM1 | 1 | `IM1_DAT` |
| IM1 | 2 | `MIC_L_VDD` |
| IM1 | 3 | `PDM_CLK` |
| IM1 | 4 | `SEL_IM1` |
| IM1 | 5 | `GND` |
| IM2 | 1 | `IM2_DAT` |
| IM2 | 2 | `MIC_R_VDD` |
| IM2 | 3 | `PDM_CLK` |
| IM2 | 4 | `SEL_IM2` |
| IM2 | 5 | `GND` |

Silk boxes in SCH-FINAL: `"LEFT IM69D"` → IM1; `"RIGHT IM69D"` → IM2.

### 2.4 Level translation (load-bearing)

Host never drives the mic rails directly:

```
Host GPIO CLK  → J1.3 CLK_IN_3V3 → U5 ESD → U1 (SN74LV1T34, 3V3→1V8) → U1_Y → R21 → PDM_CLK → IM1/IM2
IM1/IM2 DATA   → IM*_DAT → R6/R12 → PDM_DATA → R23 → U3_A → U3 (SN74LVC1T45, 1V8→3V3) → DATA_OUT_3V3 → U5 → J1.5 → Host GPIO DIN
```

Do not put 3.3 V pull-ups on mic-side `PDM_CLK` / `PDM_DATA`. Do not clock before `PWR_1V8` is valid (HANDOFF §6 / change-order clock note).

---

## 3) SELECT / L–R mechanism

**Hard-strapped with 0 Ω resistors — not GPIO, not jumper header.**

Canon (Captain-ratified 2026-07-14; `SEL-STRAP-TOPOLOGY.html`):

| Mic | SELECT net | Fitted path | Level | Opposite (DNP) |
|---|---|---|---|---|
| IM1 | `SEL_IM1` | **R7** → `PWR_1V8` | **HIGH** | R9 → GND (DNP) |
| IM2 | `SEL_IM2` | **R14** → `GND` | **LOW** | R13 → `PWR_1V8` (DNP) |

XOR rule: exactly one of each pair fitted — never both (dead short `PWR_1V8`↔`GND`).

Stereo is therefore **on-board by population**, not by ESP32 SELECT GPIO. Slot edge assignment follows Infineon SELECT polarity; if silk LEFT/RIGHT feels swapped vs product intent, **fix firmware slot mapping**, do not respin straps (`SEL-STRAP-TOPOLOGY.html` footer).

**Implication for design O-2:** answered for *this* PCB3 board — SELECT is hard-tied (strappable only by moving 0 Ω between R7/R9 and R13/R14). Stereo (C) is **not** blocked: opposite straps are already populated.

Acoustic spacing (change-order “Acoustic baseline”): **72.08 mm** between mic centres (HANDOFF: centres ∓36.04 mm).

---

## 4) Recommended K1 bench attachment — new env `k1_bench_im69d`

Target: bench K1 chip `B489A500`, map = `k1_bench_reference` SPH pads (not IM73D macros).

| Board J1 | Signal | Recommended ESP32-S3 GPIO | Macro (proposed, not yet in code) |
|---|---|---|---|
| 1 | `PWR_3V3_IN` | 3V3 | — |
| 2,4,6 | `GND` | GND | — |
| 3 | `CLK_IN_3V3` | **GPIO14** | `K1_IM69_PDM_CLK_PIN` |
| 5 | `DATA_OUT_3V3` | **GPIO13** | `K1_IM69_PDM_DIN_PIN` |
| — | SELECT | **none — leave unused** | `K1_IM69_PDM_SEL_PIN` may stay defined as unused escape hatch only |

Rationale: lands on existing SPH0645 footprint (`I2S_BCLK_PIN=14`, `I2S_DIN_PIN=13`, `I2S_LRCLK_PIN=12` in `constants.h` bench-reference block). Pin 4 on the board is GND, so the old SPH LRCLK pad (GPIO12) has **no mate on this connector** — do not drive SELECT into a GND return.

**Env rule (Captain):** NEW `k1_bench_im69d` only. **Never** mutate or flash `*im73d*` against this harness.

### Conflict matrix

| Signal | This board → recommended | IM73D (`K1_MIC_IM73D_PDM_V1`) | SPH I²S (bench-ref default) |
|---|---|---|---|
| Clock | **GPIO14** out | GPIO13 out (`K1_PDM_CLK_PIN`) | BCLK GPIO14 |
| Data | **GPIO13** in | GPIO12 in (`K1_PDM_DIN_PIN`) | DIN GPIO13 |
| SELECT / LR | **hard-strap on board** | GPIO14 out LOW (`K1_PDM_LR_PIN`) | LRCLK GPIO12 |

Flashing any `*im73d*` env with CLK=14/DATA=13 wiring → **GPIO13 output-vs-output contention** (SoC PDM CLK vs mic DATA). Standing prohibition; see design doc §2.2.

---

## 5) Compatibility vs Captain’s CLK=14 / DATA=13 claim

| Claim | Verdict | Evidence |
|---|---|---|
| CLK → IO14 | **MATCHES** board `J1.3` = `CLK_IN_3V3` | SCH-FINAL `e14633`; PCB `PAD_NET e14` pad 3; change-order J1 map |
| DATA → IO13 | **MATCHES** board `J1.5` = `DATA_OUT_3V3` | SCH-FINAL `e14641`; PCB `PAD_NET e14` pad 5 |
| SELECT on a host GPIO | **N/A for this board** | SELECT not on J1; R7/R14 hard-strap |
| Design doc §2.4 “SELECT on GPIO12” | **Optional / unused** for PCB3; keep as escape hatch for other breakouts only | — |

Captain’s completed SPH-pad wiring is the **correct host attachment** for this EDA board. New env pin macros should follow 14/13, not the IM73D 13/12/14 map.

---

## 6) Gaps / open items

| ID | Gap | Impact |
|---|---|---|
| G1 | FlyingProbe net name `NET_3` ≠ schematic `DATA_OUT_3V3` on J1.5/U3 | Cosmetics in probe export only; do not rewire from FlyingProbe names |
| G2 | Infineon SELECT→slot polarity vs silk “LEFT/RIGHT” not datasheet-verified in this pass | If mono-A (IM1) lands in RIGHT slot, swap `slot_mask` in firmware — do not reflash straps blindly |
| G3 | Physical harness on Captain’s bench not continuity-probed this session | Doc proves **board intent**; confirm cable J1 pin-1 orientation before first power-on |
| G4 | Stale docs still mention J1 pin 4 = `LRCLK_IN_3V3` (lower sections of change-order) | Superseded by §RATIFIED + live SCH; ignore |
| G5 | Clock range / DSR_16S (design O-1) | Electrical wiring OK; still blocking for first power-on policy |
| G6 | Env / firmware not implemented | **CLOSED 2026-08-05** — `k1_bench_im69d` landed; see [`im69d130-env-implement-receipt-2026-08-05.md`](./im69d130-env-implement-receipt-2026-08-05.md) |

---

## Source file index (exact)

| Fact | Source |
|---|---|
| J1 pin nets | `SCH-FINAL.txt` WIRE attrs `e14626`/`e14631`/`e14635`/`e14639`/`e14643`/`e14647`; `PCB3-INSPECT.txt` `PAD_NET e14` pads 1–6 |
| Mic nets IM1/IM2 | `SCH-FINAL.txt` `e8467` `IM1_DAT`, `e8470` `MIC_L_VDD`, `e8473` `PDM_CLK`, `e8476` `SEL_IM1`; IM2 counterparts `e8482`…`e8491` |
| Shared `PDM_DATA` | `SCH-FINAL.txt` `e8584`, `e8530`, etc. |
| Host 3V3 I/O names | `SCH-FINAL.txt` `CLK_IN_3V3`, `DATA_OUT_3V3` |
| SELECT straps | `SEL-STRAP-TOPOLOGY.html`; BOM `R7,R8,R14,R23` fitted 0 Ω |
| Architecture | `V2.0-4LAYER-CHANGE-ORDER.md` lines 15–29; `deeppcb-handoff/HANDOFF.md` §3 |
| Bench GPIO conflict | `SPECTRASYNQ_K1_FIRMWARE/system/constants.h` ~305–320 |

---

**Document Changelog**

| Date | Author | Change |
|---|---|---|
| 2026-08-05 | agent:cursor (SSA im69d130-eda-wiring) | Created from EDA SCH-FINAL + PCB3 PAD_NET + SEL-STRAP + BOM + change-order. |
