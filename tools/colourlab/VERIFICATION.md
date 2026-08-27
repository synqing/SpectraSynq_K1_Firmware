# Colour Lab — what was actually run

Date: 2026-08-28
Branch: `lane/colourlab-bench`
Contract: `tools/colourlab/README.md`
Optical authority: **PASS — PRODUCTION PREVIEW R1.1 CUTOVER**

## Stamps (do not collapse these)

| Stamp | Meaning | Status |
|-------|---------|--------|
| Host Colour Lab pytest | Colour Lab tests execute the shipped JS authorities | **PASS — 90 tests** |
| Browser / a11y verify | Chromium, keyboard, 740/390 px, 200% reflow, 13 states | **PASS — zero failures** |
| **`DEVICE_IDENTITY_VERIFIED`** | Both expected devices connected and profiled correctly | **NOT RUN in this branch-freeze receipt** |
| **`COLOUR_LAB_WEB_UI_HARDWARE_PASS`** | The load-bearing real-device programme passed on both units | **NOT RUN** — this, not identity alone, closes the lane |

Connecting to `9087A500` and `B489A500` and writing those strings here
would only establish `DEVICE_IDENTITY_VERIFIED`. It would **not** close
the implementation lane.

## Already true (host)

- `colourlab-core.js` owns protocol, effective-look resolution, Preview
  framing/comparison/inspection and safety classifiers (SHA
  `5314b24a9ae2eef1e2f3c62619d7b7a27e9ee7080012cf29654272c1bf0670c2`).
- `index.html` and `workbench.html` are byte-identical production entries
  (SHA `ce023f219b54bb1b7c7b3d6c0e26f69afaf716df131f5df0b1e806167aa0b43e`).
- Host pytest `tests/test_colourlab_*.py`: **90 passed**.
- No firmware and no `platformio.ini` edits.

## Browser (ran)

Local `python3 tools/colourlab/verify_workbench.py` (Chromium, headless):

| URL | What I checked |
|-----|----------------|
| `/index.html` | Disconnected local model; Connect and Stop Output visible |
| `?demo=ready` | Asymmetric Primary-known / Secondary-unknown truth |
| inheritance matrix | `P15/S=inherit`, `P0/S=inherit`, unknown inheritance |
| slot-unknown matrix | inherited and direct slot 15 both remain pre-correction with no tune claim |
| transport fixture | local-first Source and Tune sequences; Stop pre-emption; recovery |
| safety / policy | Preview unavailable for safety; local analysis retained for policy failure |
| keyboard / pointer / touch | one shared selected LED reads both cached frames |
| 740 px, 390 px and 200% reflow | no horizontal document overflow; 13 stills saved |

Browser failures: **0**.

Production stills: `tools/colourlab/screenshots/workbench-r1.1/`.
The design verdict is closed; these stills remain browser evidence, not device proof.

`?demo=` is a local store only. It does not open a serial port.

## Device programme (mandatory — not run in this branch-freeze receipt)

No firmware flash is authorised. `:rtrace_dump` is sent only if the running
build proves that capability.

When both units are plugged in, run **this** programme on each
identity. Record every row. Do not substitute “we saw the chip id”.

### On `9087A500` (Main RPL, `k1_main_rpl_im69d`)

| Case | Expected | Result |
|------|----------|--------|
| Connect + profile | chip `9087A500`, env `k1_main_rpl_im69d`, LEDs **160/160**, look backend WS2816 u16 | |
| Capability | Both-scale shown (×0.30); Tune band shown | |
| Paint modes | off, solid, stops and card each confirm `PAINT:`; forbidden legacy ramp is never requested | |
| Targets | primary, secondary, both; both-scale only on both | |
| Stops | 1-stop and 8-stop; string &lt; 159 chars | |
| Gain | 0.0, 1.0, 2.0 | |
| Gamma | 0.20, 1.0, 4.00 | |
| Set Identity before baseline | action is Set Identity; after success slot-15 known-this-session | |
| Reset | live identity; does not persist; does not restore last-saved | |
| Revert Session | appears only after a known session baseline exists; resends that baseline | |
| Save | `TUNE_SAVE: ok` then re-query; UI persist=saved this session only | |
| Reboot / reconnect | slot-15 unknown again; pre-LUT label; Set Identity, not Revert; no Device Effective | |
| Unplug / reconnect | re-profile; LUT knowledge discarded | |
| Stop Output | discards queued mutations; `paint=off`; unknown-on-timeout if no confirm. **Does not prove Disconnect.** | |
| Disconnect with paint active | Paint active → Disconnect → this-turn `paint=off` accepted **before** port close; or timeout/failure, close, output unknown. Must not claim safe shutdown from a previously confirmed Paint Off. Distinct from Stop Output. | |
| Slot-15 leave-state | Fill the persist ledger below. Do not write "restored" without known-this-session rewrite authority. Do not leave a verification curve. | |
| `:rtrace_dump` | only after the running build proves the command; else record unavailable | |

### On `B489A500` (bench led150, `k1_bench_im69d_led150`)

| Case | Expected | Result |
|------|----------|--------|
| Connect + profile | chip `B489A500`, env `k1_bench_im69d_led150`, LEDs **150/150**, look backend WS2812 u8 | |
| Capability | Both-scale **hidden**; Tune band **hidden** | |
| Paint modes | off, solid, stops and card each confirm `PAINT:`; forbidden legacy ramp is never requested | |
| Targets | primary, secondary, both; **no** both-scale transform shown | |
| Stops | 1-stop and 8-stop | |
| Tune mutations | not offered; `tune_status` may print `TUNE: type=na` and still must not create LUT knowledge | |
| Unplug / reconnect | re-profile 150/150 | |
| Stop Output | same priority path. **Does not prove Disconnect.** | |
| Disconnect with paint active | Same this-turn wait as Main. Tune/Save N/A. | |
| Slot-15 leave-state | N/A — Tune hidden; no Save. Record "not offered". | |
| `:rtrace_dump` | capability-gated as above | |

## Persist / reboot ledger (Main RPL — mandatory for hardware PASS)

Boot `TUNE:` is identity even when slot 15 already holds a saved curve.
That is **not** pre-test LUT knowledge and **not** restoration authority.

| Field | Value (fill on device; do not invent) |
|-------|----------------------------------------|
| Pre-test persisted LUT | `unknown` / `known-this-session {gain,gamma}` / `could-not-reconstruct` |
| Exact tuning saved during the test | gain_r, gain_g, gain_b, gamma |
| Reboot result | slot-15 status, Set Identity vs Revert, `TUNE:` line |
| Final state intentionally left | `identity-saved` / `prior-restored` / `test-curve-left` / `could-not-reconstruct` |
| Restoration authority | `none` / `session snapshot rewritten` |
| `classifyPersistLeaveState` claim | must not be `invalid-restore` or `test-curve-left` |

Required close-out when the prior LUT cannot be reconstructed: Set
Identity + Save, then record **identity-saved**. Hardware PASS is refused
if the leave-state is a leftover verification curve.

Only when **every row on both devices** is filled and matches expected
may `COLOUR_LAB_WEB_UI_HARDWARE_PASS` be written.

No flash unless a required Colour Lab command is absent from the
running build — that is a separate Captain gate.

## Source mismatch still in force

`tune_status` on bench still prints `TUNE:` with `type=na`. That reply
does not create slot-15 knowledge.

## Lane close

The Colour Lab Web UI lane closes on **`COLOUR_LAB_WEB_UI_HARDWARE_PASS`**.
Host green + optical PASS + browser verify are necessary and already
true. They are not sufficient.
