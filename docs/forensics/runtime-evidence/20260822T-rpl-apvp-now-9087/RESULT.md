---
abstract: "Live AP/VP rates on Main RPL 9087A500 are not regressed. Snappiness feel tracks a quiet drive vs the SSL gate, not SYSTEM_FPS/LED_FPS. Scored serial, not Captain eyes."
---

# Main RPL AP/VP now — 2026-08-22 20:42 AWST

Read-only `:build` / `:dump` / `:fps` / `:led_fps` / `[AP]` 1 Hz. No flash. No cal.

## Identity

`BUILD: version=40103 git=b625e89a epoch=1787400761 env=k1_main_rpl_im69d`
`CHIP ID: 9087A500` · USB `B4:3A:45:A5:87:90` · `/dev/cu.usbmodem1401`

Product restore after music occupancy. Probe is **off**. Hop `12800/96`. Mode 7 (Waveform Fast). Cal inherited (`SSL=157`, `DC=-238`, `persisted_profile`).

## Rates (the AP/VP clocks)

| Clock | Now (6 samples / dump) | Last stamped comparable |
|---|---|---|
| SYSTEM_FPS (AP) | 133.5–138.3 (dump 135.94) | 135–138 after RMT-on-VP |
| LED_FPS (VP) | 141.3–148.2 (dump 142.93) | ~143 (VP interval 6,973 µs, 2026-08-20 fps probe) |

AP p99 soak is **not** on this env (`apcad_*` compiles only with tempo/frontend-debug probes). Do not treat missing p99 as a miss.

## What “snappiness” actually is here

Same mode as the music occupancy dump. Drive is not.

| | Occupancy music dump | This capture (~20:42) |
|---|---|---|
| max_raw median | 652 | 126 |
| follower median | 1094 | 178 |
| agc_gain median | 0.113 | 1.726 |
| tempo lock | 81% | 19% |
| frames below WF gate (SSL×1.10 = 173) | 5% | **70%** |

Waveform Fast gates on `max_waveform_val_raw` vs SSL×1.10. Most frames now sit under that gate, so the show goes dark between hits. That is duty-cycle, not attack latency, and not a dropped AP/VP clock.

Also on this dump: `CONFIG.CHROMA=0.050` (was 0.100 on the 2026-08-18 `:dump`). Photons still 1.0. Independent of FPS.

## Artefact

`observe.log`
