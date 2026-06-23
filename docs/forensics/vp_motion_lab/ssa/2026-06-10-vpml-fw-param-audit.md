# VPML firmware parameter audit

Task ID: `VPML-FW-PARAM-AUDIT`
Status: `NOT_VERIFIED`
Method: read-only source audit of the live dirty working tree. No build, tests, serial, flash, AP/REST/WebSocket/Tab5 inspection, or docs/tests authority claims. Source changed during inspection; this file reflects the final bounded refresh.
Snapshot: `HEAD=88a1bc3`; SHA256 `led_utilities.h=d56328c25354ef4feb78c855d09d8afd7ebc31e53e8643da3cb911e67b19809f`, `vp_motion_lab.h=41bb0285f14829c8d58028771150e873f69e59fa94bdfd0461625f18d08212bd`, `serial_menu.h=54e912655cccd52bb3b26cc4702c7bc8d8a23c5d6a4d607437f533006f8c1bc2`, `platformio.ini=cde2f46d6efbd3c4c1ab508122111a355cf524faf09b3841e82e4d706a912888`.

## Source seams

- Non-shippable build seam: `platformio.ini:149-160` defines `k1_vp_motion_lab`, extends `k1_hardware_harness`, and adds only `-DENABLE_VP_MOTION_LAB=1`. `platformio.ini:14-18` keeps `k1_hardware` as default, and `platformio.ini:61-90` has no `ENABLE_VP_MOTION_LAB`.
- Compile/loop seam: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:59-60` includes `vp_motion_lab.h` only under `ENABLE_VP_MOTION_LAB`; `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:670-695` lets VPML own the frame, set VPAB context, then call the canonical `show_leds()` path.
- Serial seam: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:57-58` forward-declares `vpml_command` only under `ENABLE_VP_MOTION_LAB`; help text now includes `play_params,<programme>,frames=N,...` at `serial_menu.h:2199-2206`; dispatch is still a single `vpml` branch at `serial_menu.h:3113-3118`.
- Current VPML command body: `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:382-406` accepts `status`, two `play_builtin` values, `play_params`, and `stop`; unsupported data still returns `false` to `bad_command`.
- Current VPML boundary declaration: `vp_motion_lab.h:6-14` now allows bounded whitelisted parameter transport, while still forbidding arbitrary runtime code, audio modulation, persistence, Smart Director, and AP/REST/Tab5/wireless scope.
- Current render parameter seam: `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1126-1186` adds `VPMLRenderParams`, `vpml_runtime_params`, and reset/accessors. The current live render body reads those params in `vp_intro_render_frame()` at `led_utilities.h:1262-1315` and `vp_intro_render_loop_frame()` at `led_utilities.h:1317-1354`.
- Current parser shape: `vp_motion_lab.h:93-100` whitelists only `intro_bounce` and `intro_bounce_loop`; `vp_motion_lab.h:114-128` parses finite float tokens through a fixed `char token[24]`; `vp_motion_lab.h:130-221` whitelists field names; `vp_motion_lab.h:223-271` parses comma-separated `key=value` pairs into a stack candidate before returning it.

## Hazards

- Boundary leak: `VPMLRenderParams` and `vpml_runtime_params` are not behind `ENABLE_VP_MOTION_LAB` in `led_utilities.h:1126-1186`, so a VPML-named mutable parameter object now ships in production builds even though the serial VPML surface is gated.
- Production boot coupling: `intro_animation()` still calls `vp_intro_render_frame()` at `led_utilities.h:1356-1368`; because `vp_intro_render_frame()` now reads `vpml_current_params()` at `led_utilities.h:1266`, parameter work can accidentally alter the production boot intro unless boot defaults are kept fixed or the parameterised path is VPML-only.
- Silent clamp risk: `vpml_apply_param_token()` clamps out-of-range values at `vp_motion_lab.h:140-218` instead of rejecting them. That hides host/tool mistakes and weakens evidence; a bounded forensic command should fail closed on out-of-range inputs.
- Range risk: current clamps allow `frames=16..240`, widths up to `22/24`, `tail_scale=2.20`, and `edge_level/centre_level=1.2` at `vp_motion_lab.h:140-181`. These are still finite and bounded, but wider than needed for the current loop-safe preview and can smear motion or saturate output.
- Partial/default risk: `vpml_parse_params_command()` accepts any subset of recognised `key=value` pairs at `vp_motion_lab.h:241-267`, with missing keys defaulting silently. That may be acceptable if documented, but it is not an exact parameter contract and does not detect duplicates.
- Torn state: `vpml_runtime_params` is a multi-field global read from the render task (`led_utilities.h:1198-1210`, `1266`, `1320`). `vpml_play_program_with_params()` assigns it while `vpml_active` may already be true at `vp_motion_lab.h:322-330`; the safe sequence is deactivate first, assign once, reset counters, then activate last.
- Programme scope risk: `play_params` accepts both `intro_bounce` and `intro_bounce_loop` via `vp_motion_lab.h:93-100` and `223-239`. Because `intro_bounce` shares the production boot renderer, the lower-risk bounded surface is `intro_bounce_loop` only unless production boot coupling is deliberately separated.
- Parser widening risk: the current parser remains whitelisted and does not implement raw programme transport, which is good. Keep it that way: do not add begin/chunk/commit/raw programme upload, persistence, AP/REST/WebSocket, Tab5, host compilation, `String`, heap allocation, or runtime code/programme transport.

## Recommended bounded `play_params` set

Accept only the existing serial-only VPML command shape `vpml=play_params,intro_bounce_loop,<key=value...>` unless the production boot renderer is separated from VPML params. Recommended keys are exactly the current struct: `frames`, `secondary_phase`, `primary_width`, `secondary_width`, `tail_scale`, `primary_level_base`, `primary_level_gain`, `secondary_level_base`, `secondary_level_gain`, `edge_level`, `centre_level`, `primary_red`, `primary_green`, `primary_blue`, `secondary_red`, `secondary_green`, `secondary_blue`, `impact_red`, `impact_green`, `impact_blue`.

Bounds should be fail-closed before any state mutation: `frames` 48-180; `secondary_phase` 0.0-0.35; `primary_width` and `secondary_width` 2.0-18.0; `tail_scale` 0.25-2.0; level fields 0.0-1.0 with `primary_level_base + primary_level_gain <= 1.0` and `secondary_level_base + secondary_level_gain <= 1.0`; `edge_level` 0.0-0.75; `centre_level` 0.0-0.70; all RGB channels 0.0-1.0 and finite. Reject bad field count, trailing garbage, non-finite values, and out-of-range values; do not silently clamp command inputs.

Implementation shape that would refute unsafe/open-ended transport: keep help and dispatch under `ENABLE_VP_MOTION_LAB`; keep `play_builtin` reset-to-default as currently done at `vp_motion_lab.h:341-343`; parse into a stack `VPMLRenderParams candidate`; reject out-of-range values instead of clamping; either require exact keys once or explicitly document partial defaults and reject duplicate keys; assign only after all validation passes; set `vpml_active=false` before assignment; activate the programme last; print a concise accepted/rejected status; keep all parameter use deterministic and centre-origin in the existing `intro_draw_centre_band()` path; do not add heap, `String`, delay, serial output, file I/O, WiFi, persistence, or AP/REST/Tab5 scope to render-reachable code.

## Verdict

`NOT_VERIFIED` for the current working tree as a fully safe `play_params` transport. The source now has a whitelisted key/value parser and no raw programme upload, which refutes the worst arbitrary-code/programme-transport failure mode. It still has a non-gated VPML-named mutable parameter object, production boot coupling, silent clamp behaviour, partial/default ambiguity, broad ranges, and torn-state risk when restarting while active.
