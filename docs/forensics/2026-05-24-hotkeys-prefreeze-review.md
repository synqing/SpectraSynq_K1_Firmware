---
abstract: "Pre-freeze review note for K1 serial hotkeys. Records the final ':'-mandatory command surface, N/Y noise-calibration safety gate, verification evidence, and accepted residual risk before freezing the hotkey baseline."
---

# K1 Serial Hotkeys Pre-Freeze Review

## Scope

This note covers the K1 serial hotkey feature in `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h` and the accompanying static contract in `tests/test_serial_hotkeys_static.py`.

The goal is fast bench control of K1 hardware without returning to slow typed serial commands for every adjustment.

## Final command model

- Normal serial input is hotkey-first.
- Typed legacy serial commands require a leading `:` and Enter.
- Examples:
  - `:dump`
  - `:vp_status`
  - `:ap_stream=on`
  - `:start_noise_cal`

The parser rule is implemented in `check_serial()`: without command mode, incoming bytes are treated only as hotkeys; `parse_command()` is reached only after `:` command mode is entered.

## Final keymap

| Key | Behaviour |
|---|---|
| `h` | Print hotkey help |
| `;` | Print hotkey status |
| Space | Toggle primary/secondary hotkey target |
| `[` / `]` | Previous / next mode on active target |
| `i` / `I` | Increase / decrease photons on active target |
| `o` / `O` | Increase / decrease chroma on active target |
| `p` / `P` | Increase / decrease mood on active target |
| `j` / `J` | Increase / decrease saturation on active target |
| `k` / `K` | Increase / decrease prism count on active target |
| `l` / `L` | Increase / decrease base-coat intensity on active target |
| `q` / `Q` | Increase / decrease `CONFIG.SQUARE_ITER` |
| `w` / `W` | Increase / decrease `CONFIG.SENSITIVITY` |
| `e` / `E` | Increase / decrease `VP_WAVEFORM_SHIFT_RATE` |
| `r` / `R` | Increase / decrease `VP_BLOOM_SHIFT_SCALE` |
| `t` / `T` | Increase / decrease `VP_BLOOM_ALPHA` |
| `1` | Toggle chromatic mode |
| `2` | Toggle auto colour shift on active target |
| `3` | Toggle base coat on active target |
| `4` | Toggle incandescent mode on active target |
| `5` | Toggle reverse order on active target |
| `6` | Toggle temporal dithering |
| `,` / `.` | Previous / next palette on active target |
| `/` | Toggle palette mode on active target |
| `a` | Toggle AP stream |
| `s` | Toggle VP stream |
| `d` | Toggle AGC debug stream |
| `f` | Stop all streams |
| `N` | Arm noise calibration for 5 seconds |
| `Y` | Confirm armed noise calibration and queue the existing calibration path |

## Noise calibration safety model

K1's pin profile sets `NOISE_CAL_PIN` to `-1` (`constants.h:181`), which compile-gates out the physical noise-button path in `buttons.h` (`#if NOISE_CAL_PIN >= 0`). The original Sensory Bridge populates that button; the K1 board does not. So K1 bench calibration needs a keyboard path.

The final design is `N` then `Y`:

- `N` arms calibration and prints `NOISE_CAL: armed - confirm silence, press Y within 5s`.
- `N` does not set `noise_transition_queued`.
- `Y` calls `serial_confirm_noise_cal()`.
- `serial_confirm_noise_cal()` first checks `serial_noise_cal_arm_active()`.
- If the arm window expired or was never opened, `Y` disarms, prints `NOISE_CAL: not armed - press N first`, and returns.
- If armed and in-window, `Y` disarms, sets `noise_transition_queued = true`, and prints `NOISE_CAL: queued`.

This keeps K1 bench calibration available while removing the accidental single-byte serial trigger.

### Revision history — why `N`/`Y`, not a single key

An earlier revision (revision 3) bound noise calibration to a single keystroke: `N` set
`noise_transition_queued` directly. Pre-freeze audit flagged this as a hard blocker — a
single stray serial byte could start a calibration, the exact hazard the `CLAUDE.md`
calibration-command policy and the Fix-D guards exist to prevent (origin: the 2026-05-24
Stage 7 incident, where `start_noise_cal` ran during music and poisoned
`SWEET_SPOT_MIN_LEVEL`). The audit also found the static test had been written to *assert*
the single-key trigger rather than forbid it. The `N`/`Y` arm-then-confirm design, and the
test that now guards it, are the resolution of that finding — not an arbitrary choice. Do
not collapse `N`/`Y` back to a single key.

## Test contract

`tests/test_serial_hotkeys_static.py` is the guard for this surface:

- Requires the allowlisted hotkeys.
- Requires `N` and `Y` to be present.
- Requires `N` to call `serial_arm_noise_cal()` and not touch `noise_transition_queued`.
- Requires `Y` to call `serial_confirm_noise_cal()` and not touch `noise_transition_queued` directly.
- Requires `serial_confirm_noise_cal()` to check `serial_noise_cal_arm_active()` before queueing calibration.
- Requires `check_serial()` to route typed commands through `:` command mode rather than the old timing-dependent `USBSerial.available() == 0` heuristic.

## Verification evidence

Commands run in this session:

- `python3 -m unittest tests/test_serial_hotkeys_static.py` -> PASS, 5 tests.
- `pio run -e k1_hardware` -> SUCCESS.
- `pio run -e k1_hardware -t upload` -> SUCCESS on `/dev/tty.usbmodem1101`.

Runtime smoke performed on `/dev/tty.usbmodem1101`:

- `h` printed hotkey help including `N arm noise calibration` and `Y confirm armed noise calibration`.
- `N` printed `NOISE_CAL: armed - confirm silence, press Y within 5s`.
- After waiting beyond 5 seconds, `Y` printed `NOISE_CAL: not armed - press N first`.
- No `STARTING NOISE CAL` was observed during the negative smoke.

## Accepted residual

If arbitrary text containing `N` and then `Y` is pasted into the hotkey surface within 5 seconds, it can arm and confirm calibration. This is accepted for the bench workflow because closing that residual by timing queued bytes would reintroduce the timing-dependent parser behaviour removed by this feature.

Operator rule: do not paste arbitrary text into the hotkey surface. Use `:` command mode for typed commands.

## Freeze decision

Freeze requires Captain's explicit keymap sign-off:

`Approve K1 hotkey layout v1 for freeze.`
