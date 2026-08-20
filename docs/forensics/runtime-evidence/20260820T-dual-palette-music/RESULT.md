# Dual-unit music + palette soak — RESULT

When: `2026-08-19T19:12:46Z`
Output: Bose Mini II SoundLink at volume 50 (restored 31)

## Identity
- **main_rpl** port `/dev/cu.usbmodem1401` git=`79d220fa` env=`k1_main_rpl_im69d` chip=`9087A500`
- **bench_b489** port `/dev/cu.usbmodem1101` git=`69e21140` env=`k1_bench_im69d` chip=`B489A500`

## Predictions
- **P1_silence**: PASS
- **P2_peak_vs_ambient**: PASS
- **P3_system_fps**: PASS
- **P4_led_fps**: FAIL
- **P5_tempo**: FAIL
- **P6_palette_ack**: PASS
- **P7_honour_palette**: PASS
- **P8_restore**: PASS
- **P9_chroma_flatness_by_palette**: PASS

## Song A (ziggyx 155 BPM, 120 s) AP/VP
- **main_rpl** n=112 silence_frac=0.14285714285714285 lock_frac=0.16071428571428573 conf_mean=0.3938392857142857 peak_mean=0.7386696428571429 bpm_mean=89.45535714285714 SYSTEM_FPS p50=135.49 LED_FPS p50=147.13
- **bench_b489** n=112 silence_frac=0.17857142857142858 lock_frac=0.2857142857142857 conf_mean=0.39901785714285715 peak_mean=0.6895714285714286 bpm_mean=86.08035714285714 SYSTEM_FPS p50=139.34 LED_FPS p50=202.16

## Song B (Querox Time, 90 s) AP/VP
- **main_rpl** n=90 silence_frac=0.022222222222222223 lock_frac=0.5444444444444444 conf_mean=0.5551111111111111 peak_mean=0.6392888888888889 bpm_mean=107.93333333333334 SYSTEM_FPS p50=136.69 LED_FPS p50=145.89
- **bench_b489** n=90 silence_frac=0.044444444444444446 lock_frac=0.5777777777777777 conf_mean=0.5552222222222222 peak_mean=0.6795555555555556 bpm_mean=100.77777777777777 SYSTEM_FPS p50=137.65 LED_FPS p50=201.92

## Colour / honour
- Palette ACKs: 14 writes, all matched names
- Honour path: EDGE_EFFECTIVE must stay `*_palette` (P7).
- No HUEAUD on these ship binaries — pixel hue histograms were not taken.

## Restore
- Palettes restored: yes

