---
abstract: "P0 freeze 2026-09-08: lane/pcm1808-st25r3916b-bringup HEAD cd38c7f3, Main RPL 9087A500 on usbmodem1101 SER B4:3A:45:A5:87:90, silicon still k1_main_rpl_st25_probe @ 605b855e. Product restore dump hash-verified. NFC parked after identity PASS."
---

# P0 — continuation baseline (2026-09-08)

## Live git

| Item | Value |
|---|---|
| cwd | `/Users/spectrasynq/SpectraSynq_K1_Firmware` |
| branch | `lane/pcm1808-st25r3916b-bringup` |
| HEAD | `cd38c7f3fadbc0e1d1ae12b0f9898e6f07d2c9aa` |
| HEAD subject | `docs: record ST25 0x31 PASS and Main RPL deployed-state 605b855e` |
| dirty | yes — Colour Lab screenshots, BLE leftover, architecture html, `pcmclk-boot.txt`. **Not this lane's firmware TUs.** |
| sibling worktree | none created this session |

## Live target

Discovered this session. Port names remain ephemeral.

| Item | Live value |
|---|---|
| Port | `/dev/cu.usbmodem1101` |
| USB | VID:PID `303A:1001`, serial `B4:3A:45:A5:87:90` |
| Chip | `9087A500` (Main RPL) |
| Handover silicon | `k1_main_rpl_st25_probe` @ `605b855e` epoch `1788795556` |
| Product restore named | `k1_main_rpl_im69d` @ `acaecaa8` |

Do not flash `k1_hardware`. Do not touch F887 (OFFSITE). Do not re-fire `start_noise_cal`.

## Original 20260907 evidence

Intact at `docs/forensics/runtime-evidence/20260907T-pcm1808-st25-bringup/`. Not overwritten.

## NFC

ST25 SPI identity PASS (`0x31` / ST25R3916B) is preserved. RFAL / tag / coexistence **PARKED** until P10.

## Programme constraint

Nothing here authorises promotion of PCM1808, dual-capture, runtime source switching, high-rate features, 96 kHz, or NFC into the default product image.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | agent:grok | P0 freeze from live git + USB serial. |
