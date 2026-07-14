---
abstract: "Canonical K1 hardware definition. ESP32-S3-DevKitC-1 N16R8 with 16 MB quad flash and 8 MB octal PSRAM. 2x WS2812 LED channels on GPIO 6/7 (320 LEDs total). IM73D PDM microphone on CLK 13 / DIN 12 / LR 14 LOW. I2C SDA 17 / SCL 18. Device identity must be verified by chip ID; ports are session-local."
---

# K1 Hardware Definition (canonical)

K1 hardware = the upload target for Sensory Bridge core firmware.

```
Board:        ESP32-S3-DevKitC-1 N16R8
              - 16 MB Quad Flash
              - 8 MB Octal PSRAM
LED output:   2 channels × 160 × WS2812 (320 LEDs total)
Audio input:  IM73D PDM microphone
Build env:    k1_prod_im73d
```

PSRAM is ALWAYS present on K1 hardware. Do not gate, probe, ask
about, or conditionally compile around PSRAM presence. Build MUST
include `-DBOARD_HAS_PSRAM` and FQBN `PSRAM=enabled`.

Pin assignments (per current firmware dirty tree):

```
LEDs:    GPIO 6, 7
PDM:     CLK 13, DIN 12, LR/SELECT 14 LOW
I2C:     SDA 17, SCL 18
Physical controls / sweet-spot LEDs: disabled (SB_HAS_* gates off)
```

Ports are session-local. Verify the USB identity and expected chip ID before
every upload; never infer identity from a `usbmodem` suffix.

The bench-reference equivalent is `k1_bench_im73d`, with LED GPIO 4/5 and the
same IM73D mic pins. `k1_hardware` and `k1_bench_reference` are legacy
SPH-compatible bases, not hardware authority.

Authority: [`2026-07-15-im73d-production-reference-decision.md`](2026-07-15-im73d-production-reference-decision.md).

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-15 | Captain / Codex | IM73D designated canonical production/reference microphone; port identity made session-local. |
| 2026-05-23 | agent:claude | Created: canonical K1 hardware definition. PSRAM presence is settled — no further probing or gating. |
