---
abstract: "Canonical K1 hardware definition. ESP32-S3-DevKitC-1 N16R8 with 16 MB quad flash and 8 MB octal PSRAM (always present — do not gate, probe, or conditionally compile around PSRAM presence). 2x WS2812 LED channels on GPIO 6/7 (320 LEDs total). SPH0645 I2S MEMS mic on BCLK 13 / LRCLK 11 / DIN 14. I2C SDA 17 / SCL 18. Physical controls and sweet-spot LEDs disabled (SB_HAS_* gates off). Upload port /dev/tty.usbmodem1101. Protected S2 capture unit at /dev/tty.usbmodem02 — never touch."
---

# K1 Hardware Definition (canonical)

K1 hardware = the upload target for Sensory Bridge core firmware.

```
Board:        ESP32-S3-DevKitC-1 N16R8
              - 16 MB Quad Flash
              - 8 MB Octal PSRAM
LED output:   2 channels × 160 × WS2812 (320 LEDs total)
Audio input:  SPH0645 I2S MEMS microphone
```

PSRAM is ALWAYS present on K1 hardware. Do not gate, probe, ask
about, or conditionally compile around PSRAM presence. Build MUST
include `-DBOARD_HAS_PSRAM` and FQBN `PSRAM=enabled`.

Pin assignments (per current firmware dirty tree):

```
LEDs:    GPIO 6, 7
I2S:     BCLK 13, LRCLK 11, DIN 14
I2C:     SDA 17, SCL 18
Physical controls / sweet-spot LEDs: disabled (SB_HAS_* gates off)
```

Upload port (active session): `/dev/tty.usbmodem1101`
Protected S2 capture unit: `/dev/tty.usbmodem02`   ← never touch

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:claude | Created: canonical K1 hardware definition. PSRAM presence is settled — no further probing or gating. |
