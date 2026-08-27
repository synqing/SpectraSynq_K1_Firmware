# Colour Lab — what was actually run

Date: 2026-08-27  
Branch: `feat/k1-usb-audio-input`  
Contract: `tools/colourlab/README.md`  
Look unlock: **`COLOUR_LAB_WEB_UI_T0_LOOK_WAIVER_V1`** (not optical PASS)

## Stamps (do not collapse these)

| Stamp | Meaning | Status |
|-------|---------|--------|
| Host Colour Lab pytest | Colour Lab tests execute shipped `colourlab-core.js` | **PASS** (re-run after Disconnect/persist classifiers) |
| Browser / a11y look verify | Chromium, keyboard, 740 px, 200% zoom, 0 console errors | **PASS** (demo store only) |
| **`DEVICE_IDENTITY_VERIFIED`** | Both expected devices connected and profiled correctly | **NOT RUN** — no USB serial ports present |
| **`COLOUR_LAB_WEB_UI_HARDWARE_PASS`** | The load-bearing real-device programme passed on both units | **NOT RUN** — this, not identity alone, closes the lane |

Connecting to `9087A500` and `B489A500` and writing those strings here
would only establish `DEVICE_IDENTITY_VERIFIED`. It would **not** close
the implementation lane.

## Already true (host)

- `colourlab-core.js` is the functional oracle. Look work did not rewrite
  it. A later safety edit added `classifyDisconnectShutdown` and
  `classifyPersistLeaveState` (SHA
  `ea8c6f60e53379ef33a16c91ee3a2006769eb3ff7f719f155a42551310a53a29`).
- `index.html` is the same IDs and script, with the webflash void/gold
  layer applied under the named waiver. Disconnect now waits for a
  this-turn `paint=off` before closing the port.
- Host pytest `tests/test_colourlab_*.py`: **34 passed**.
- No firmware and no `platformio.ini` edits.

## Browser (ran)

Local `python3 tools/colourlab/verify_browser.py` (Chromium, headless):

| URL | What I checked |
|-----|----------------|
| `/index.html` | Disconnected; Connect enabled; Stop Output visible; Set Identity |
| `?demo=unsupported` | Connection `unsupported`; paint/tune disabled |
| `?demo=main` | Ready · `9087A500` · 160/160 · Both-scale shown · Tune shown · **Set Identity** · slot-15 unknown · pre-LUT label |
| `?demo=bench` | Ready · `B489A500` · 150/150 · Both-scale hidden · Tune well hidden |
| `?demo=unverified` | Unverified Device Profile · no exact-parity claim |
| `?demo=main&paint=solid` | RGB 140/140/140 + Send RGB; status `paint: solid/both` |
| `?demo=main&paint=card` | Card strip: greys then R/G/B/gold; n=160 both channels |
| keyboard Tab | Stop Output is reachable (`#btnStop`) |
| 740 px and 200% zoom | Page still usable; stills saved |

Console: **0 errors, 0 warnings**.

Look stills (post-waiver page; **not** the rejected T3 shell):
`tools/colourlab/screenshots/look-ready-main.png`,
`look-ready-bench.png`, `look-paint-card.png`, `look-disconnected.png`.
Pixel-inspected: `PIXEL_INSPECT_RECEIPT.json`. Design verdict is **open**.
These are not a device proof.

`?demo=` is a local store only. It does not open a serial port.

## Device programme (mandatory — not run)

No `/dev/cu.usbmodem*` or `/dev/tty.usb*` was present. I did not flash
either K1. I did not send `:rtrace_dump`.

When both units are plugged in, run **this** programme on each
identity. Record every row. Do not substitute “we saw the chip id”.

### On `9087A500` (Main RPL, `k1_main_rpl_im69d`)

| Case | Expected | Result |
|------|----------|--------|
| Connect + profile | chip `9087A500`, env `k1_main_rpl_im69d`, LEDs **160/160**, look backend WS2816 u16 | |
| Capability | Both-scale shown (×0.30); Tune band shown | |
| Paint modes | off, solid, ramp, stops, card each confirm `PAINT:` | |
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
| Paint modes | off, solid, ramp, stops, card each confirm `PAINT:` | |
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
Host green + look waiver + browser verify are necessary and already
true. They are not sufficient.
