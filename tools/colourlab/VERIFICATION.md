# Colour Lab — production and hardware verification

Date: 2026-08-28
Branch: `lane/colourlab-bench`
Browser-slice commit: `14d5ddbd`
Contract: `tools/colourlab/README.md`

## Stamps

| Stamp | Result |
|---|---|
| Production Preview R1.1 optical gate | **PASS** |
| Host Colour Lab pytest | **PASS — 92 tests** |
| Browser / accessibility / responsive gate | **PASS — 14 states, zero failures** |
| `DEVICE_IDENTITY_VERIFIED` | **PASS — both named units** |
| Real-device protocol matrix | **PASS — both named units** |
| Production DOM/controller → real devices | **PASS — both named units** |
| `COLOUR_LAB_WEB_UI_HARDWARE_PASS` | **PASS** |
| Wire/LED-buffer truth | **NOT CLAIMED — product builds reject `rtrace_status`** |

## Exact live identities

| Role | Port observed this run | Chip | Build |
|---|---|---|---|
| Main RPL | `/dev/cu.usbmodem1101` | `9087A500` | `git=acaecaa8 epoch=1787773671 env=k1_main_rpl_im69d` |
| Bench led150 | `/dev/cu.usbmodem1401` | `B489A500` | `git=f2014c29 epoch=1787771217 env=k1_bench_im69d_led150` |

Identity came from each unit's `:chip_id` and `:build` replies. Port names were
not used as identity. No firmware was flashed and no calibration command was sent.

## Main RPL — `9087A500`

| Case | Measured result |
|---|---|
| Connect + profile | Production controller resolved verified Main RPL, `160/160`, `ws2816_u16` |
| Capability | Tune visible; Preview details showed `Both target applies ×0.30 on this verified profile.` |
| Source modes | `off`, `solid`, `stops`, `card` each returned matching `PAINT:`; forbidden `ramp` was never sent |
| Targets | `primary`, `secondary`, `both` each confirmed with solid K1 amber `255,184,77` |
| Stops | One stop `140,140,140` and eight warm-family stops confirmed; payload length below 159 |
| Gain bounds | `0.000`, `1.000`, `2.000` each confirmed for R/G/B |
| Gamma bounds | `0.200`, `1.000`, `4.000` each confirmed |
| Session baseline / Revert | Identity established first; exact gain-then-gamma baseline sequence confirmed |
| Reset | Non-identity `1.200,1.100,0.900 / 1.100` reset live to exact identity |
| Save | Exact identity written, `TUNE_SAVE: ok`, then re-queried |
| Reboot / reconnect | CDC reopen reset the unit; profile returned 160/160 and runtime tune returned identity/type 2 |
| Disconnect while active | Production Disconnect queued a current-turn `:paint=off`, received `PAINT: mode=off`, then closed |
| Instrumentation capability | `:rtrace_status=1` → `Bad command`; no wire/LED-buffer claim |
| Final leave-state | Paint off; look 0 IDENTITY; Secondary inherit; slot 15 deliberately **identity-saved** |

## Bench — `B489A500`

| Case | Measured result |
|---|---|
| Connect + profile | Production controller resolved verified Bench, `150/150`, `ws2812_u8` |
| Capability | Tune hidden and all Tune mutation controls disabled; Main-only ×0.30 row hidden |
| Source modes | `off`, `solid`, `stops`, `card` each returned matching `PAINT:`; forbidden `ramp` was never sent |
| Targets | `primary`, `secondary`, `both` each confirmed with solid K1 amber `255,184,77` |
| Stops | One stop and the same eight warm-family stops confirmed |
| Tune | Only `tune_status` was read; it returned `type=na`; no Tune mutation was sent |
| Reconnect | CDC reopen reset and re-profiled the unit as 150/150 |
| Disconnect while active | Production Disconnect received current-turn Paint-off confirmation before close |
| Instrumentation capability | `:rtrace_status=1` → `Bad command`; no wire/LED-buffer claim |
| Final leave-state | Paint off; look 0 IDENTITY; Secondary inherit; Tune not offered |

## Production UI integration boundary

The exact production `index.html` and `colourlab-workbench.js` were run in
headless Chromium. The browser's secure native serial chooser cannot be granted
in headless Playwright (`Unknown permission: serial`), so a test adapter supplied
the same `navigator.serial` port/reader/writer interface and carried bytes to the
real pyserial ports. No command, reply, profile, queue decision or reducer event
was mocked.

This run proved on each real unit:

1. production Connect/hydration resolved the live chip, environment and geometry;
2. production Source sent `paint_target → paint_rgb → paint` and consumed real replies;
3. Main production Tune sent `tune_gain → tune_gamma` and consumed real replies;
4. production Disconnect waited for a new Paint-off reply before closing;
5. the hardware-exposed Bench capability defect was closed: Tune is hidden and
   mutation handlers now fail closed by profile even if called programmatically;
6. Main-only Both-target scaling is disclosed as ×0.30 and absent on Bench.

The bypassed boundary is Chrome's user-mediated permission chooser, not Colour Lab
application logic or K1 hardware behaviour.

## Persist / reboot ledger — Main RPL

| Field | Recorded value |
|---|---|
| Pre-test persisted LUT | `unknown` — boot `TUNE:` is not LUT readback |
| Exact tuning saved | `gain=1.000,1.000,1.000 gamma=1.000` |
| Save reply | `TUNE_SAVE: ok` |
| Reboot result | runtime identity/type 2; browser session knowledge correctly returns to unknown |
| Final state intentionally left | `identity-saved` |
| Restoration authority | `none`; prior unknown LUT was not falsely described as restored |
| Leave-state classifier claim | valid `identity-saved`; never `invalid-restore` or `test-curve-left` |

## Failures encountered and contained

Two verifier expectations were initially too literal:

- firmware returned `Bad command` rather than lowercase `bad_command` for unavailable rtrace;
- the production serializer sent compact `1,1,1` / `1`, not `1.000,1.000,1.000` / `1`.

Neither was a device failure. The first stopped after Main was already Paint off and
identity-saved. The second stopped with Main Paint active; a direct current-turn
`:paint=off` was immediately sent and confirmed before the run resumed. Final
read-only audits on both units passed after all browser/device work.

## Final stamp

```text
COLOUR_LAB_WEB_UI_HARDWARE_PASS
devices = 9087A500, B489A500
main_slot15_leave_state = identity-saved
main_paint = off
bench_paint = off
wire_truth = NOT_CLAIMED
merge_to_main = HOLD pending explicit merge action
```
