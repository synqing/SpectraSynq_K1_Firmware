---
abstract: "K1 Dual UART Observability schema v1.2: 24 parser slots (v1.1 1–21 unchanged plus phase, orbit_x, orbit_y). Device / parser-derived / host-metadata provenance. host_parse_seq is not device frame_seq. Orbit is peak×(cos,sin)(2π phase) for the 3D tempo-phase widget."
---

# K1 telemetry schema v1.2

Parser marker: `var SCHEMA = 1.2` in `parsers/k1_ap_parser.js`. APPEND-ONLY from v1.1.

Serial Studio is the **acquisition, visualization, recording, and experiment-control** layer. It is **not** the timing or statistical authority.

```
device time     = measurement authority
host time       = transport / acquisition diagnostic
Python scorer   = verdict
dashboard       = situational awareness only (may hold last-known in slots 1-19)
```

## Provenance classes (never collapse)

| Class | Meaning | Example |
|-------|---------|---------|
| device evidence | bytes on UART | `bpm=` in `[AP]` |
| parser-derived | host inference from those bytes | `record_kind`, `update_mask`, `host_parse_seq` |
| host metadata | Serial Studio / operator config | app version, project title, sourceId, host timestamp, poll timer |

A poll timer is host metadata. Do **not** label `EVENT_STATUS` as `POLL`.

## Sources (identity-by-USB-serial)

| Role | chip_id | USB serial | Typical port (advisory) |
|------|---------|------------|-------------------------|
| Bench | B489A500 | B4:3A:45:A5:89:B4 | cu.usbmodem1401 |
| Main RPL | 9087A500 | B4:3A:45:A5:87:90 | cu.usbmodem12201 |

Ports churn on every native-USB reset. Bind by USB serial, never by a hardcoded `usbmodemNNNN`.

## Parser output slots (1-based in Serial Studio)

Array length on a recognised prefix is **24**. Empty / unknown / malformed lines return `[]` and do **not** bump `host_parse_seq`. Slot 18 stays index 18 (renamed from `parse_seq` to `host_parse_seq` so Historian columns do not shift). Slots 22–24 are append-only.

| Index | Name | Class | When written |
|-------|------|-------|----------------|
| 1 | bpm | device | `[AP] bpm=` present |
| 2 | conf | device | `[AP]` or `EVENT_STATUS conf=` |
| 3 | lock | device | `[AP] lock=` |
| 4 | beat | device | `[AP]` / `EVENT_STATUS` |
| 5 | onset | device | `[AP]` / `EVENT_STATUS` |
| 6 | bass | device | `[AP]` / `EVENT_STATUS` |
| 7 | silence | device | `[AP] silence=` / `EVENT_STATUS sil=` |
| 8 | agc_gain | device | `[AP]` |
| 9 | peak_scaled | device | `[AP]` |
| 10 | ssl | device | `[AP] SSL=` |
| 11 | energy | device | `EVENT_STATUS energy=` |
| 12 | nov | device | `EVENT_STATUS nov=` |
| 13 | system_fps | device | `SYSTEM_FPS:` with a finite number |
| 14 | led_fps | device | `LED_FPS:` with a finite number |
| 15 | lightshow | device | `[AP] lightshow=` |
| 16 | device_ms | device clock | `EVENT_STATUS t=` |
| 17 | frame_ms | device clock | `EVENT_STATUS frame_ms=` |
| 18 | host_parse_seq | parser-derived | every published line; **not** device `frame_seq` |
| 19 | event_tid | device | `EVENT_STATUS tid=` — not a per-frame counter |
| 20 | record_kind | parser-derived | prefix only (see below) |
| 21 | update_mask | parser-derived | bit `i` (0-based) set iff slot `i+1` was written from **this** line |
| 22 | phase | device | `[AP] phase=` / `EVENT_STATUS phase=` |
| 23 | orbit_x | parser-derived | `peak_scaled * cos(2π phase)` on every `[AP]` and `EVENT_STATUS` |
| 24 | orbit_y | parser-derived | `peak_scaled * sin(2π phase)` on every `[AP]` and `EVENT_STATUS` |

Dashboard may still hold last-known values in slots 1–19 and 22–24. Scorer statistics MUST use only rows where the corresponding `update_mask` bit is set (or `record_kind` matches the metric origin). Held repeats must not inflate n or move p50/p95/p99.

### record_kind

Inferred from the line prefix only:

| Value | Kind | Prefix |
|-------|------|--------|
| 1 | AP | `[AP]` (not `[APCAP]` / `[APDIST]`) |
| 2 | EVENT_STATUS | `EVENT_STATUS` |
| 3 | SYSTEM_FPS | `SYSTEM_FPS:` |
| 4 | LED_FPS | `LED_FPS:` |
| 5 | BUILD | `VERSION:` (numeric version if present is **not** a slot; do not invent `firmware_sha`) |

No `POLL` kind. `FIRMWARE_VERSION:` and `BUILD: version=` banners are unknown → `[]`.

### update_mask bits

| Bit | Slot | Name |
|-----|------|------|
| 0 | 1 | bpm |
| 1 | 2 | conf |
| 2 | 3 | lock |
| 3 | 4 | beat |
| 4 | 5 | onset |
| 5 | 6 | bass |
| 6 | 7 | silence |
| 7 | 8 | agc_gain |
| 8 | 9 | peak_scaled |
| 9 | 10 | ssl |
| 10 | 11 | energy |
| 11 | 12 | nov |
| 12 | 13 | system_fps |
| 13 | 14 | led_fps |
| 14 | 15 | lightshow |
| 15 | 16 | device_ms |
| 16 | 17 | frame_ms |
| 17 | 18 | host_parse_seq |
| 18 | 19 | event_tid |
| 19 | 20 | record_kind |
| 20 | 21 | update_mask |
| 21 | 22 | phase |
| 22 | 23 | orbit_x |
| 23 | 24 | orbit_y |

Every published vector sets bits 17, 19, and 20. `[AP]` and `EVENT_STATUS` also set bits 22 and 23 (orbit). Bit 21 (phase) only when `phase=` is on **this** line. `setKv` ORs a bit only when that key is present and finite on **this** line. Mask resets each `parse()`.

Not on the wire (do not invent in the parser): `run_id`, `firmware_sha`, `audio_frame_seq`, `render_frame_seq`, `AP_us`, `drop_count`, `device_us`, `frame_seq`. Those wait for a compact binary schema. Until then they are **absent**, not zero-meaning.

## Host timestamp

Serial Studio stamps at the driver boundary with the host monotonic clock. That value is:

- preserved through CSV / Historian / API
- **not** K1 generation time
- **not** usable to align Bench vs Main by itself

## Virtual datasets (host metadata / parser-derived)

Live transforms are cheap diagnostics. Orchestrator owns `apply_engineering_project.py`; this section is the contract those transforms must match.

### frame_dt_ms

From `device_ms` delta. First sample 0; negative wrap clamped to 0.

```javascript
var prev = NaN;
function transform(value) {
  var dt = (isFinite(prev) && isFinite(value)) ? (value - prev) : 0;
  prev = value;
  if (dt < 0)
    dt = 0;
  return dt;
}
```

### host_device_skew_ms

Diagnostic only. **Not** Bench↔Main sync. **Not** a clock-offset to apply to either device.

`skew = (host_now - host_t0) - (device_ms - device_t0)` after the first finite `device_ms` sample. Growth means USB/UART stall or host scheduling delay.

```javascript
var t0Host;
var t0Dev;
function transform(value, info) {
  if (value === undefined || value === null || !isFinite(value))
    return 0;
  if (info === undefined || info.timestampMs === undefined)
    return 0;
  if (t0Host === undefined) {
    t0Host = info.timestampMs;
    t0Dev = value;
    return 0;
  }
  return (info.timestampMs - t0Host) - (value - t0Dev);
}
```

### transport_residual_ms

Diagnostic of jitter / drift / burst, **not** sync:

`transport_residual_ms = (host_elapsed - device_elapsed) - baseline_offset`

where `host_elapsed = host_ms - t0_host`, `device_elapsed = device_ms - t0_device`, and `baseline_offset` is the first-sample (or warmup-median) skew so residual starts near 0. Not wired in `apply_engineering_project.py` yet.

## CSV

Row interval must stay **0 ms** (one row per received frame). v4.0.3 has no `csvExport.setInterval` command; the process default is 0. Do not set a timer interval in Preferences.

## FFT / Waterfall

Serial Studio does not infer sample rate. The FFT `Sampling rate` field is a **declared** axis scale.

- Bench `[AP]` cadence is ~declared AP Hz (typically 133.33). Use **133**, never 100, if you enable FFT on those channels.
- Main RPL without `[AP]` is poll-driven (~4 Hz). Use **4** for FFT on that source. The poll is host metadata, not a `record_kind`.
- Authoritative spectra are computed offline from `device_ms` / `frame_ms`.

## Transforms vs scorer

Allowed live (cheap): `frame_dt_ms`, `host_device_skew_ms`, `transport_residual_ms`, instantaneous Hz.

Forbidden live: p95/p99, correlations, lag search, Gate scores. Those belong in `scorer/session_receipt.py`. Scorer must filter by `update_mask` / `record_kind` so held last-known dashboard values are not treated as new measurements.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-08-31 | agent:grok | v1.2 append-only phase + orbit_x/orbit_y for tempo-phase 3D. |
| 2026-08-31 | agent:grok | v1.1: provenance classes, host_parse_seq rename, record_kind, update_mask, virtual-transform contract. |
| 2026-08-31 | agent:grok | Schema v1 from the K1 Dual UART observability policy. |
