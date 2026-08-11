# QA Runbook — K1.tab5 Deck

## 0) Preflight
- Clean clone; verify `include/tab5_config.h` **does not exist**.
- Copy `include/tab5_config.sample.h` → `include/tab5_config.h` and fill values.

## 1) Build determinism
- `pio run -e tab5_p4` (or `tab5_s3`) succeeds with pinned deps.
- Artifacts produced: `firmware.bin`, `bootloader.bin`, `partitions.bin` (depending on board).

**PASS if** build succeeds from clean clone with only local config copied.

## 2) Boot UX
- Power on; screen is **black**, no white flash.
- Backlight ramps smoothly to readable level within ~1–2 s.

**PASS if** no white flash; BL steps are smooth (no loop stalls).

## 3) Wi-Fi state machine
- With AP on: device connects, `[net] Wi-Fi ONLINE`, Wi-Fi icon turns green.
- Turn AP off: after disconnect, backoff logs: 10s → 20s → 40s → 60s (cap).
- Turn AP on: reconnects immediately when available; backoff resets.

**PASS if** transitions log once each; UI remains responsive.

## 4) Keep-alive & Host liveness
- Start host app; confirm deck receives `/deck/status` ~5 Hz; Host icon green.
- Stop host for >15 s: Host icon gray; deck **continues** sending `/deck/hello` every 5 s.
- Restart host: Host icon green immediately after first `/deck/status`.

**PASS if** liveness follows the above without user interaction.

## 5) Controls & Persistence
- Tap **Effect** tile → host receives `/k1/vp/effect/select`.
- Tap **Brightness** repeatedly → host sees `/k1/vp/led/brightness` with 0.05 steps. Power cycle:
  - Deck boots; brightness is restored; first TX replays saved value.
- Tap **Param 1/2** → host sees `/k1/vp/effect/param/1` and `/2` in 0.05 steps.

**PASS if** messages & values are correct; brightness persists across reboot.

## 6) Idle memory drift (spot)
- Let deck idle for 10 minutes with host running; ensure no watchdog resets or UI stalls.

**PASS if** stable.
