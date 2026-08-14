---
abstract: "Captain-ratified G1 physical-to-digital mapping for the K1v2 B489A500 dual-IM69D input. Both capsules are alive. Physical IM1 / board-left / SELECT HIGH maps to Infineon LEFT, ESP-IDF PDM RIGHT and stereo PCM index 0, and is the future shipped programme source. T0.3 bench/diagnostic explicit-slot work is complete; protected production environments remain byte-identical and promotion is held until P4."
status: ratified
board: K1v2 B489A500
---

# G1 AP-input slot ratification — 2026-08-15

```text
G1                                  = RATIFIED
BOARD                               = K1v2 B489A500

PHYSICAL IM1 / BOARD_LEFT / SELECT_HIGH
  -> INFINEON_LEFT
  -> ESP_IDF_PDM_SLOT_RIGHT
  -> PCM_INDEX_0

PHYSICAL IM2 / BOARD_RIGHT / SELECT_LOW
  -> INFINEON_RIGHT
  -> ESP_IDF_PDM_SLOT_LEFT
  -> PCM_INDEX_1

BOTH_CAPSULES_ALIVE                 = PASS
ONE_MIC_DEAD_OR_UNPOPULATED         = REFUTED
FAULT_CLASS                         = SLOT_SEMANTICS / SOURCE_SELECTION
ORIGINAL_PHYSICAL_TEST              = CANCELLED_INVALID

SHIPPED_PROGRAMME_SOURCE            = PHYSICAL_IM1
PHYSICAL_IM1_SELECT                 = HIGH
ESP_IDF_SLOT                        = RIGHT
STEREO_PCM_INDEX                    = 0
BUILD_FLAG                          = K1_MIC_IM69D_SLOT_RIGHT

ESP_IDF_VERSION                     = 5.4.1
PDM_DRIVER_PATH                     = NEW_DRIVER
PDM_CLK_INV                         = false
STEREO_BUFFER_ORDER                 = RIGHT_THEN_LEFT

NO_FURTHER_PHYSICAL_MICROPHONE_TEST = AUTHORISED_NONE
```

## Why this mapping is accepted

The board straps are IM1 HIGH and IM2 LOW. Infineon calls the HIGH microphone LEFT and the
LOW microphone RIGHT. The active ESP-IDF PDM driver uses the opposite electrical labels:
`I2S_PDM_SLOT_RIGHT` is SELECT pulled up and `I2S_PDM_SLOT_LEFT` is SELECT pulled down.
With clock inversion disabled, the active stereo buffer is RIGHT then LEFT.

The retained mono/stereo fingerprint independently matches that chain:

| Stream | Retained quiet RMS |
|---|---:|
| mono ESP-IDF RIGHT | about 7 |
| stereo PCM index 0 | 7.86 |
| mono ESP-IDF LEFT | 80–112 |
| stereo PCM index 1 | 117.60 |

The stereo capture also showed two responsive, non-duplicated arrays. That fired the
pre-registered kill criterion against the dead/unpopulated-capsule diagnosis.

## Source-identity correction

Captain's decision text named ESP-IDF 5.4.2. The active build does not use that installation.
`platformio.ini` pins pioarduino `54.03.20`, whose Arduino ESP32-S3 headers report
ESP-IDF **5.4.1**. A separate standalone `framework-espidf` 5.4.2 package on the workstation
is not the package used by this firmware build. This correction does not alter the mapping.

T0.3 freezes the live contract in source: exact 5.4.1 version, new PDM driver,
`clk_inv=false`, RIGHT/LEFT enum values, and RIGHT-then-LEFT diagnostic buffer naming.

## T0.3 closeout

```text
T0.3                               = PASS
ALL_MONO_IM69D_ENVS                = EXPLICIT_ESP_IDF_RIGHT
STEREO_ENV                         = EXPLICIT_BOTH_WITH_RIGHT_UNFLAGGED
RETIRED_ALIAS_ENVS                 = micb, hpf_slotr, calfix_dsr16
PRODUCTION_SLOT_CHANGE             = NONE
PRODUCTION_STABLE_BYTE_IDENTITY    = PASS
FLASH                              = NONE
CALIBRATION                        = NONE
```

| Command | Result |
|---|---|
| `python3 scripts/tools/probe_diff.py --self-test` | **PASS**, including deliberately RED no-op/comment/expected-flag cases and inherited-flag removal. |
| `python3 scripts/tools/probe_diff.py k1_bench_im69d_stereo --expect K1_MIC_IM69D_STEREO_V1` | **PASS** — added stereo; removed inherited RIGHT. |
| `python3 scripts/tools/probe_diff.py k1_bench_im69d_hpf --expect K1_AP_SUBSONIC_HPF_V1` | **PASS** — genuine one-flag delta. |
| `python3 -m pytest tests/ -q` | **PASS** — 1079 passed, 1 skipped. The slot-contract mutation test removes base RIGHT in memory and observes the ratchet go RED. |
| `pio run -s -e k1_bench_im69d -e k1_bench_im69d_stereo -e k1_unit2_im69d_right` | **PASS** — all affected configurations compile; existing warnings only. |
| `pio run -s -e k1_hardware` | **PASS** — required production build. |
| `bash scripts/regression-harness/mic_stable_byte_gate.sh` | **PASS** — `k1_hardware`, `k1_bench_reference`, `k1_bench_im73d` stable sections byte-identical; no reference update. |
| `python3 scripts/regression-harness/stereo_probe_decode.py _scratch/p0_stereo_20260814/scap_music.txt` | **PASS** — legacy `LR` marker accepted and interpreted as active RIGHT/LEFT order; CRC true; RMS 7.9/117.6. |

## Execution boundary

- T0.3 bench/diagnostic registry entries and ratchets are complete.
- The future production policy is physical IM1 via `K1_MIC_IM69D_SLOT_RIGHT`.
- Production configuration and production firmware must remain byte-identical until P4.
- No microphone handling, new physical test, calibration or flash is authorised here.
- Calibration remains separately gated by Captain's explicit verbal silence confirmation.

---
**Document Changelog**

| Date | Author | Change |
|---|---|---|
| 2026-08-15 | agent:codex | Closed T0.3 with explicit-slot ratchets, build proof, full host gate and protected production byte identity. |
| 2026-08-15 | Captain / agent:codex | Recorded G1 ratification, corrected active ESP-IDF identity to 5.4.1, and froze the T0.3/production boundary. |
