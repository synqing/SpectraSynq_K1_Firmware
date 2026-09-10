---
abstract: "Locked parser/receipt contract. Schema v1.2 is 24 slots, append-only from v1.1 (phase + orbit_x/orbit_y). Agents must not invent device fields."
---

# Schema lock (hardening tranche)

Do not invent on-wire fields. Absent remains absent: `run_id`, `firmware_sha`, `audio_frame_seq`, `render_frame_seq`, `AP_us`, `drop_count`, `device_us`, `frame_seq`.

## Provenance classes (never collapse)

| Class | Meaning | Example |
|-------|---------|---------|
| device evidence | bytes on UART | `bpm=` in `[AP]` |
| parser-derived | host inference from those bytes | `record_kind`, `update_mask`, `host_parse_seq` |
| host metadata | Serial Studio / operator config | app version, project title, sourceId, host timestamp |

## Parser slots (1-based, schema v1.2)

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
| 13 | system_fps | device | `SYSTEM_FPS:` |
| 14 | led_fps | device | `LED_FPS:` |
| 15 | lightshow | device | `[AP] lightshow=` |
| 16 | device_ms | device clock | `EVENT_STATUS t=` |
| 17 | frame_ms | device clock | `EVENT_STATUS frame_ms=` |
| 18 | host_parse_seq | parser-derived | every published line; **not** device frame_seq |
| 19 | event_tid | device | `EVENT_STATUS tid=` — not a per-frame counter |
| 20 | record_kind | parser-derived | 1=AP 2=EVENT_STATUS 3=SYSTEM_FPS 4=LED_FPS 5=BUILD |
| 21 | update_mask | parser-derived | bit `i` (0-based) set iff slot `i+1` was written from **this** line |
| 22 | phase | device | `[AP] phase=` / `EVENT_STATUS phase=` |
| 23 | orbit_x | parser-derived | `peak_scaled * cos(2π phase)` on every `[AP]` and `EVENT_STATUS` |
| 24 | orbit_y | parser-derived | `peak_scaled * sin(2π phase)` on every `[AP]` and `EVENT_STATUS` |

v1.2 is **append-only**. Slots 1–21 keep v1.1 indices. Peak and phase are held so an `EVENT_STATUS` line without a prior `[AP]` still publishes orbit (zeros until peak arrives).

Dashboard may still hold last-known values in slots 1–19 and 22–24. Scorer statistics MUST use only rows where the corresponding `update_mask` bit is set (or `record_kind` matches the metric’s origin). Held repeats must not inflate n or move p50/p95/p99.

`record_kind` is inferred from the line prefix only. Do **not** label EVENT_STATUS as POLL — a poll timer is host metadata, not a byte on the line.

BUILD = `VERSION:` prefix (numeric version if present). Identity banners without a numeric field publish kind=5 and empty extras, or are ignored if they cannot be parsed safely.

Malformed / unknown → return `[]` (do not publish a held vector).

## Virtual datasets (host metadata / parser-derived)

- `frame_dt_ms` — cheap, from `device_ms` delta
- `host_device_skew_ms` — diagnostic only, **not** Bench↔Main sync
- `transport_residual_ms` — `(host_elapsed - device_elapsed) - baseline_offset`; jitter/drift/burst, not sync

## Historian (v4.0.3 live)

Path: `~/Documents/Serial Studio/Session Databases/K1 Dual UART Observability/K1 Dual UART Observability.db` (+ WAL).

Tables: `sessions` (project_title, started_at, ended_at, project_json), `columns`, `readings` (timestamp_ns, unique_id, raw/final numeric), `raw_bytes` (device_id, data), `project_metadata`, `table_snapshots`.

Live DB hash = `LIVE_DB_FINGERPRINT` only. Gate identity = SHA-256 of a closed SQLite backup snapshot.

## Receipts

- **instrument receipt** — capture/config/integrity. No experiment PASS/FAIL.
- **gate receipt** — named scoring profile + thresholds. Not in this lock; separate file later.

Do not mutate the live Historian.

## File owners this tranche

| File | Owner |
|------|-------|
| `parsers/k1_ap_parser.js` | SSA-parser |
| `TELEMETRY_SCHEMA.md` | SSA-parser |
| `scorer/session_receipt.py` | SSA-receipt |
| `tests/**` golden fixtures | SSA-golden |
| `apply_engineering_project.py` | orchestrator (after parser) |
| EdgeAI-Lab `src/edgeai/serial_studio.py` | orchestrator |

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-08-31 | agent:grok | v1.2 append-only: phase + tempo-phase orbit_x/orbit_y. |
| 2026-08-31 | agent:grok | Locked v1.1 slots, provenance classes, receipt split. |
