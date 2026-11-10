---
abstract: "Emulator gates G1–G4 on the current FE head 8b202f46 (10 Nov 2026, 16:08–16:28 AWST): every result matches the expectations declared beforehand in EXPECTED.md, and the captured LED payloads are byte-identical to the ed0aa984 baseline in both configurations. The Lane B byte-safety oracle, re-pointed at 8b202f46, gives the same verdicts as at 407fdf6f. This is the baseline the FW lead's fixes are judged against."
---

# Baseline at 8b202f46 — result

Plain English: nothing the FE lane changed since `ed0aa984` (Gx board support, mode-32 silence fix, serial input validation) altered prepared-show behaviour in the emulator. The two known faults are still there (live microphone leaks into prepared shows; seeking leaves stale state), and the two passing gates still pass.

## Gates (declared before running: G1 PASS, G2 FAIL, G3 FAIL, G4 PASS, exit 2)

| Run | G1 | G2 | G3 | G4 | Exit | Run directory (under `m2-emu/runs/`) |
|---|---|---|---|---|---|---|
| `--profile fe --mode 32` | PASS 0/1778 | FAIL 1775–1778/1778 | FAIL 594–667/667 | PASS 0/1778 | 2 | `fe-8b202f46-m32-20261110T160813` |
| `--profile scenario --mode 32` | PASS 0/1778 | FAIL 1773–1778/1778 | FAIL 602–667/667 | PASS 0/1778 | 2 | `rplproxy-8b202f46-m32-20261110T160813` |
| `--profile scenario --mode 18` | PASS 0/1778 | FAIL 1705–1778/1778 | FAIL 665–667/667 | PASS 0/1778 | 2 | `rplproxy-8b202f46-m18-20261110T161818` |

All counts equal the `ed0aa984` runs (`M2E-receipt.md`). G4 in every run: `records=9599/9599 queued=614400 consumed=614400 auth_state=2`.

## Risk 1 checked (Gx power logic could darken the FE edges)

Decoded with the work copy's own `emu_capture` (lead, 16:35 AWST):

| Run / case | Frames | Edge A mean (16-bit) | Edge A sha256 (12) | Edge B sha256 (12) |
|---|---|---|---|---|
| FE 8b202f46 g1-a1 | 1778 | 3077.5, max 65534 | `25b0dcc3a580` | `94ba3fdfad24` |
| FE ed0aa984 g1-a1 | 1778 | 3077.5, max 65534 | `25b0dcc3a580` | `94ba3fdfad24` |
| FE 8b202f46 g4-m2 | 1778 | 2944.7 | `31400a441330` | `594f8288a0ad` |
| FE ed0aa984 g4-m2 | 1778 | 2944.7 | `31400a441330` | `594f8288a0ad` |
| RPL proxy 8b202f46 g1-a1 | 1778 | 3075.4 | `94b83c05934f` | `9a79f63a544d` |
| RPL proxy ed0aa984 g1-a1 | 1778 | 3075.4 | `94b83c05934f` | `9a79f63a544d` |
| RPL proxy 8b202f46 g4-m2 | 1778 | 3010.9 | `f20c43f05472` | `e4738db40bee` |
| RPL proxy ed0aa984 g4-m2 | 1778 | 3010.9 | `f20c43f05472` | `e4738db40bee` |

Both edges are lit and byte-identical to the old baseline. [FACT] The Gx profile does not change the emulated payload. [INFERENCE] The Gx LED current budget is not applied on the captured path in emulation; whether it limits brightness on a real Gx board is a G5 bench item (FW lead), not testable here.

## Lane B oracle re-pointed (`lane-b/ORACLE-8b202f46.md`)

- PRSM/authored files byte-identical; `check_serial`, `serial_hotkey_is_immediate`, `serial_handle_hotkey` text-identical (all `serial_menu.cpp` changes sit inside `parse_command`). Lead re-check: the `check_serial` region (407fdf6f lines 4100–4220 vs 8b202f46 4130–4250) `cmp`-identical.
- Suite: 163 passed with `LANE_B_FW=fw_8b202f46 LANE_B_RAW=raw_8b202f46` (lead re-ran: 163 passed).
- M2 stream byte audit `--guard 30`: BENCH-ELIGIBLE, 26870/26870 frames, 0 hotkeys (lead re-ran). M1 stream: eligible, 9600/9600.
- Loss exposure unchanged: guard 0 → 110 cases queue noise calibration, 178,135 persist something; guard 30 → 0 shortcut bytes.
- `set_mode` still declared non-persisting (`serial_typed_cmd_table.def:141`) while its handler saves (`serial_cmd_handlers.cpp:1740` at 8b202f46).
- Limit: the oracle's demux is a hand-written replica of `check_serial`. The receiver-isolation fix will change `check_serial`, so that fix must be judged on the real firmware path (emulator RX adapter feeds the production `check_serial`), and the replica updated alongside it.

## Process note for whoever runs gates.py next

`gates.py` keys its work copy by source tree only. Run each profile from its own export with the adapter pre-applied (`fe`: `PROTOTYPE-ADAPTER-ed0aa984.diff -p1`; `scenario`: `PROTOTYPE-ADAPTER-ed0aa984-noflags.diff -p1`), so the two profiles get different tree hashes and can run in parallel. Exports used here: session scratchpad `src-8b202f46-fe`, `src-8b202f46-rpl` (`git archive 8b202f46` + adapter; reproducible).

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude (K1-FE-SHOW lead, session 2) | Created after the runs; every decision-critical number re-run or read by the lead. |
