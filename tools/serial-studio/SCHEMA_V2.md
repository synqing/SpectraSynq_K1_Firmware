---
abstract: "Design-only schema v2 intent. Do not implement in product firmware from this folder. device_us + frame_seq are the per-record bandwidth worth paying for."
---

# Schema v2 intent (design only)

Not in the active firmware lane unless that lane already has a named experiment. This document is intent, not a flash brief.

## Why v1 is frozen-honest

v1 refuses to invent `firmware_sha`, `run_id`, `audio_frame_seq`, `AP_us`, `drop_count`. Keep that rule. Host-configured facts stay **host metadata**. Parser inferences stay **parser-derived**. Device-emitted bytes stay **device evidence**.

## Record classes

### Boot / session metadata (once / low-rate)

Telemetry schema version, firmware SHA, build epoch, device identity, boot ID. Emit once; join in the receipt. Do **not** put SHA on every AP line.

### Hot telemetry (every authoritative record)

`record type`, **`device_us`**, **`frame_seq`**, essential measurements. Prefer microseconds if the clock supports it. `frame_seq` is the device counter that can prove pre-parser loss; `host_parse_seq` cannot.

### Pipeline-specific (only if already produced)

audio frame sequence, render sequence, bridge sequence — not invented.

### Health (low-rate)

drop counters, queue health, reset/error counters.

### Probe-only timing

`AP_us`, stage timings: **only** when measuring performance. Measure `telemetry OFF` vs `telemetry ON` so the tap does not eat the AP budget (observer effect). Product builds keep this compiled out.

## Binary / batched (later, Task 10)

Text path stays until v2 timing authority exists **and** a measured comparison (bytes/s, USB writes/s, encode CPU, AP impact, loss detection) beats text. A batch must keep per-sample device timestamps. Never assign one host packet-arrival time to every sample in the batch.

## Not now

gRPC, MCP, Serial Studio plugins, camera, dashboard spectacle.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-08-31 | agent:grok | Design-only v2 classes; device_us+frame_seq hot; SHA once. |
