---
abstract: "P1 soak on k1_main_rpl_pcm1808_probe @ 5334cde0: DMA acquisition 47991 Hz matches LRCK. AP hop-drain consumes ~46700 Hz. I2S RX overflow is real (2153 events / 70 s). Exact lost-frame count UNKNOWN. 46.8 kHz was consumption loss, not host CDC."
---

# P1 — PCM continuity / overflow truth

**MEASURED_ON_SILICON** 2026-09-08 Main RPL `9087A500`  
Image: `k1_main_rpl_pcm1808_probe` @ `5334cde0` epoch `1788806735`  
Port: `/dev/cu.usbmodem1101` USB `B4:3A:45:A5:87:90`  
Evidence: `P1_PCM_OVERFLOW.json` + `.log`

## Rates (esp_timer, 2 s windows)

| Quantity | Value | Authority |
|---|---:|---|
| lrck_hz | 47,994.6 | boot PCNT, printed on `[PCMRATE2]` |
| acq_hz | 47,990–47,996 | `on_recv` DMA complete / esp_timer |
| cons_hz | 46,611–46,829 | `i2s_channel_read` into hop-drain / esp_timer |
| canon_hz | 129.5–130.1 | SRC hops / esp_timer (want 133.33) |

## Loss

| Quantity | Value |
|---|---|
| rx_overflow_events | 2153 in ~70 s |
| ovf_bytes (API `event.size` sum) | 775,080 |
| dropped_frames_signaled | 129,180 (= bytes/6) |
| dropped_exact | **UNKNOWN** |
| ring_drop | 0 (no ring yet) |
| reset/WDT | 0 |

Acquisition matches the physical 48 kHz clock. Consumption matches the old 10 min `dma_hz≈46823` telemetry. That discrepancy is **I2S RX queue overflow while AP/DSP holds Core 0**, not a CDC timestamp artefact.

Classification: **real Line-In ingress defect.** Execute P2 immediately.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | agent:grok | 70 s soak on 5334cde0; overflow confirmed. |
