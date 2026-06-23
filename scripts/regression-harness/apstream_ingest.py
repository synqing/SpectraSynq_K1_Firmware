#!/usr/bin/env python3
"""Ingest device capture logs for notebook overlays.

DISPLAY-ONLY. This parses what the firmware ALREADY emits over serial; it computes
no DSP. It exists so the notebook can overlay real on-device telemetry against
host-modelled front-end outputs and expose where the host ceiling and the device
diverge.

Supported serial surfaces:
- `[AP]` — legacy 1 Hz AP stream (bpm/conf/lock/phase beat/onset/bass/ostr)
- `[APCAP]` — AP capture summary per 5 s aggregate (`max_raw`, `peak_scaled`,
  `follower_mean`, `spec_argmax`, `chroma_mean`, `silence`, `SSL`, `DC`,
  `cal_source`, `cal_valid`)
- `NOV,` — non-shippable full-rate accepted novelty stream for host replay
- `APDBG,` / `[APDBG]` — non-shippable AP front-end truth stream emitted after
  novelty/snapshot/tempo update
- `sbs((agc_debug=...))` — multi-band AGC debug stream
  (`energy`, `gain`, `threshold`, `floor`)

Lines may be wrapped in other serial chatter; parse is marker-driven and tolerant.
Unknown formats are skipped with counted warnings, never fatal.

RETURNED STRUCTURE (backward-compatible + extended):

Top-level keys remain the legacy AP stream shape:

  {
    "source": "capture_log",
    "track_id": str | None,
    "t_ms": [int, ...], "bpm": [float, ...], "conf": [float, ...],
    "lock": [int, ...], "phase": [float, ...], "beat": [int, ...],
    "bstr": [float, ...], "onset": [int, ...], "bass": [int, ...],
    "ostr": [float, ...],
    "n_parsed": int, "n_skipped": int, "warnings": [str, ...]

Legacy AP_STREAM fields are in `out` directly for notebook compatibility, plus:

  {
    "ap_stream": {legacy AP_STREAM keys + warnings + counts},
    "ap_capture": {
      "source": "ap_capture",
      "n_parsed": int, "n_skipped": int,
      "records": [dict...], "last": dict | None, "warnings": [str, ...]
    },
    "agc_debug": {
      "source": "agc_debug",
      "n_parsed": int, "n_skipped": int,
      "samples": {"t_ms": [...], "energy": [...], "gain": [...],
                  "threshold": [...], "floor": [...]},
      "warnings": [str, ...]
    },
    "ap_frontend_debug": {
      "source": "ap_frontend_debug",
      "n_parsed": int, "n_skipped": int,
      "records": [dict...], "warnings": [str, ...]
    },
    "novelty_stream": {
      "source": "novelty_stream",
      "n_parsed": int, "n_skipped": int,
      "records": [dict...], "warnings": [str, ...]
    }
  }
"""

import argparse
import json
import re
import sys
from pathlib import Path


# keys that the host-modelled tempo front-end overlays from `[AP]`
TEMPO_KEYS = ["bpm", "conf", "lock", "phase", "beat", "bstr"]
ONSET_KEYS = ["onset", "bass", "ostr"]
EXPECTED_KEYS = set(TEMPO_KEYS + ONSET_KEYS)

# [AP] keeps these as int, everything else parse-floats
AP_INT_KEYS = {"lock", "beat", "onset", "bass"}
AP_IGNORE_KEYS = {
    "SSL", "DC", "max_raw", "follower", "peak_scaled", "silent_scale",
    "silence", "cal_source", "cal_valid",
}

# APCAP keys we parse (and tolerate missing/extra with warning)
APCAP_KEYS = {
    "frames", "max_raw", "peak_scaled", "follower_mean", "spec_argmax",
    "chroma_mean", "silence", "SSL", "DC", "cal_source", "cal_valid",
}

# AGC debug field families
AGC_KEYS = {"energy", "gain", "threshold", "floor"}

APDBG_KEYS = {
    "t", "frame_ms", "emit_ms", "emit", "nov", "nov_scaled", "scale",
    "ssl", "dc", "max_raw", "follower", "peak_scaled", "ap_sil", "tempo_sil",
    "cal_valid", "peak", "vu", "energy", "low", "mid", "high", "sil",
    "agc_e", "agc_floor", "agc_gain", "agc_gate",
    "bpm", "phase", "conf", "lock", "beat", "str",
    "win", "win_bpm", "top1", "top1_bpm", "top1_sel",
    "top2", "top2_bpm", "top2_sel", "comb", "point", "prior",
    "v2_q", "v2_ema", "v2_lock",
}
APDBG_INT_KEYS = {
    "t", "frame_ms", "emit_ms", "emit", "ssl", "dc", "ap_sil", "tempo_sil",
    "cal_valid", "sil", "agc_gate",
    "lock", "beat", "win", "top1", "top2", "v2_lock",
}
NOV_KEYS = {"t", "emit", "nov", "nov_scaled", "scale", "sil", "acf"}
NOV_INT_KEYS = {"t", "emit", "sil", "acf"}

_TOKEN_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([^,\s]+)")
_TS_HMS_RE = re.compile(r"\[(\d{1,2}):(\d{2}):(\d{2}(?:\.\d+)?)\]")
_TS_NUM_RE = re.compile(r"\[(-?\d+(?:\.\d+)?)\]")
_AGC_RE = re.compile(r"sbs\(\(agc_debug=([^)]*)\)\)")

NOMINAL_APSTREAM_CADENCE_MS = 1000
NOMINAL_APCAP_CADENCE_MS = 5000
NOMINAL_AGC_CADENCE_MS = 100
NOMINAL_APDBG_CADENCE_MS = 23


def _to_num(raw):
    """Parse a token to int/float; return None if unparsable."""
    try:
        return int(raw)
    except (TypeError, ValueError):
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None


def _parse_value(key, raw):
    """Parse a marker value to int/float. Returns (ok, value)."""
    if raw is None:
        return False, None
    val = _to_num(raw)
    if val is None:
        return False, None
    if key in AP_INT_KEYS and isinstance(val, bool):
        # bool is a subclass of int; force canonical ints
        return True, int(val)
    if key in AP_INT_KEYS:
        return True, int(round(float(val)))
    return True, float(val)


def _split_payload(line):
    """Extract all key=value pairs from a payload string."""
    return {
        m.group(1): m.group(2)
        for m in _TOKEN_RE.finditer(line)
        if "=" in m.group(0)
    }


def _parse_range_or_num(raw):
    """Parse `a/b` as min/max dict, otherwise scalar.

    The firmware prints `max_raw` and `peak_scaled` as slash ranges in APCAP.
    """
    if raw is None:
        return None
    if isinstance(raw, str) and "/" in raw:
        left, right = raw.split("/", 1)
        return {"min": _to_num(left), "max": _to_num(right)}
    return _to_num(raw)


def _parse_timestamp_ms(line):
    """Attempt to parse a leading timestamp from the line to absolute ms.

    Supports:
    - [HH:MM:SS(.mmm)]
    - [1234] (treated as milliseconds)

    Returns int milliseconds or None.
    """
    m = _TS_HMS_RE.search(line.strip())
    if m:
        h, mnt, sec = m.groups()
        return int(h) * 3600_000 + int(mnt) * 60_000 + int(float(sec) * 1000)

    m = _TS_NUM_RE.search(line.strip())
    if m:
        raw = _to_num(m.group(1))
        if raw is None:
            return None
        if raw >= 1000:
            return int(raw)
        return int(raw * 1000)

    return None


def _warn_once(target, seen, msg):
    if msg not in seen:
        seen.add(msg)
        target.append(msg)


def parse_ap_line(line):
    """Parse one `[AP]` line.

    Returns (fields, unknown_keys, missing_keys) or None if no `[AP]` marker.
    """
    marker = line.find("[AP]")
    if marker < 0:
        return None
    payload = line[marker + len("[AP]"):]
    found = {}
    seen = set()
    for k, v in _split_payload(payload).items():
        seen.add(k)
        if k in EXPECTED_KEYS:
            ok, value = _parse_value(k, v)
            if ok:
                found[k] = value

    unknown = seen - EXPECTED_KEYS - AP_IGNORE_KEYS - {"SSL", "DC"}
    missing = EXPECTED_KEYS - set(found.keys())
    return found, unknown, missing


def parse_apcap_line(line):
    """Parse one `[APCAP]` line.

    Returns a dict keyed by APCAP fields, with slash ranges parsed as
    `{min:..., max:...}` for `max_raw`/`peak_scaled`, or None if marker missing.
    """
    marker = line.find("[APCAP]")
    if marker < 0:
        return None
    payload = line[marker + len("[APCAP]"):]
    raw = _split_payload(payload)
    out = {}
    for key in APCAP_KEYS:
        if key not in raw:
            continue
        if key in ("max_raw", "peak_scaled"):
            out[key] = _parse_range_or_num(raw[key])
        elif key in {"frames", "spec_argmax", "silence", "SSL", "DC", "cal_valid"}:
            out[key] = _to_num(raw[key])
        else:
            # numeric scalars / strings
            value = _to_num(raw[key])
            out[key] = raw[key] if value is None else value
    return out


def parse_agc_line(line):
    """Parse one `sbs((agc_debug=...))` stream line.

    Expected format: `sbs((agc_debug=energy:0.1,0.2;gain:1,2;threshold:..;floor:..))`

    Returns a dict `{field: [float, ...]}` with AGC fields as arrays, or None
    if marker missing or parse failed.
    """
    m = _AGC_RE.search(line)
    if not m:
        return None

    raw = m.group(1).strip()
    # Compatibility with both variants:
    #   sbs((agc_debug=...))  -> group is "agc_debug=..."
    #   older emitters may capture only the payload after the key.
    if raw.startswith("agc_debug="):
        body = raw[len("agc_debug="):]
    else:
        body = raw
    groups = [part for part in body.split(";") if part]

    parsed = {}
    for g in groups:
        if ":" not in g:
            continue
        k, csv = g.split(":", 1)
        if not k or k not in AGC_KEYS:
            continue
        vals = []
        for tok in csv.split(","):
            tok = tok.strip()
            if not tok:
                continue
            v = _to_num(tok)
            if v is None:
                continue
            vals.append(float(v))
        if vals:
            parsed[k] = vals

    return parsed if parsed else None


def parse_apdbg_line(line):
    """Parse one APDBG front-end debug line.

    Returns a dict of parsed scalar fields, or None if the marker is absent.
    Unknown numeric keys are retained so future firmware additions stay visible
    to offline tooling.
    """
    if "[APDBG]" in line:
        marker = line.find("[APDBG]")
        payload = line[marker + len("[APDBG]"):]
    elif "APDBG," in line:
        marker = line.find("APDBG,")
        payload = line[marker + len("APDBG,"):]
    else:
        return None
    raw = _split_payload(payload)
    out = {}
    for key, value in raw.items():
        parsed = _to_num(value)
        if parsed is None:
            continue
        out[key] = int(round(float(parsed))) if key in APDBG_INT_KEYS else float(parsed)
    return out


def parse_nov_line(line):
    """Parse one compact full-rate NOV line."""
    marker = line.find("NOV,")
    if marker < 0:
        return None
    payload = line[marker + len("NOV,"):]
    raw = _split_payload(payload)
    out = {}
    for key, value in raw.items():
        parsed = _to_num(value)
        if parsed is None:
            continue
        out[key] = int(round(float(parsed))) if key in NOV_INT_KEYS else float(parsed)
    return out


def load_apstream(path, track_id=None):
    """Parse a captured serial log into a device telemetry dict.

    Returns None if `path` is absent. Robust: never raises on malformed lines.
    """
    p = Path(path)
    if not p.exists():
        return None

    out = {
        "source": "capture_log",
        "track_id": track_id,

        # Backward-compatible legacy AP_STREAM top-level
        "t_ms": [], "bpm": [], "conf": [], "lock": [], "phase": [],
        "beat": [], "bstr": [], "onset": [], "bass": [], "ostr": [],
        "n_parsed": 0, "n_skipped": 0, "warnings": [],

        # Parsed blocks
        "ap_stream": {
            "source": "ap_stream",
            "t_ms": [], "bpm": [], "conf": [], "lock": [], "phase": [],
            "beat": [], "bstr": [], "onset": [], "bass": [], "ostr": [],
            "track_id": track_id,
            "n_parsed": 0, "n_skipped": 0, "warnings": [],
        },
        "ap_capture": {
            "source": "ap_capture",
            "records": [],
            "n_parsed": 0,
            "n_skipped": 0,
            "last": None,
            "warnings": [],
        },
        "agc_debug": {
            "source": "agc_debug",
            "n_parsed": 0,
            "n_skipped": 0,
            "samples": {"t_ms": [], "energy": [], "gain": [],
                        "threshold": [], "floor": []},
            "warnings": [],
        },
        "ap_frontend_debug": {
            "source": "ap_frontend_debug",
            "records": [],
            "n_parsed": 0,
            "n_skipped": 0,
            "warnings": [],
        },
        "novelty_stream": {
            "source": "novelty_stream",
            "records": [],
            "n_parsed": 0,
            "n_skipped": 0,
            "warnings": [],
        },
    }
    warn_seen = set()
    stream_warn_seen = set()
    apcap_warn_seen = set()
    agc_warn_seen = set()
    apdbg_warn_seen = set()
    nov_warn_seen = set()

    # sample counters for synthetic times when logs have no explicit timestamp
    idx_ap = 0
    idx_cap = 0
    idx_agc = 0
    idx_apdbg = 0
    idx_nov = 0

    try:
        raw_lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:  # noqa: BLE001
        return {**out, "warnings": [f"could not read {path}: {e}"]}

    for line in raw_lines:
        parsed_any = False
        ts_ms = _parse_timestamp_ms(line)

        parsed = parse_ap_line(line)
        if parsed is not None:
            fields, unknown, missing = parsed
            if not fields:
                _warn_once(out["warnings"], warn_seen, "AP line had marker but no parseable expected keys (malformed?)")
                out["n_skipped"] += 1
                out["ap_stream"]["n_skipped"] += 1
                parsed_any = True
            else:
                if unknown:
                    _warn_once(out["warnings"], warn_seen,
                               f"AP line had unexpected key(s) (ignored): {sorted(unknown)}")
                    _warn_once(out["ap_stream"]["warnings"], stream_warn_seen,
                               f"AP line had unexpected key(s) (ignored): {sorted(unknown)}")
                if missing:
                    _warn_once(out["warnings"], warn_seen,
                               f"AP line missing expected key(s): {sorted(missing)}")
                    _warn_once(out["ap_stream"]["warnings"], stream_warn_seen,
                               f"AP line missing expected key(s): {sorted(missing)}")

                t_ms = ts_ms if ts_ms is not None else (idx_ap * NOMINAL_APSTREAM_CADENCE_MS)
                idx_ap += 1

                ap_row = {
                    "t_ms": t_ms,
                    "bpm": fields.get("bpm", float("nan")),
                    "conf": fields.get("conf", float("nan")),
                    "lock": int(fields.get("lock", 0)),
                    "phase": fields.get("phase", float("nan")),
                    "beat": int(fields.get("beat", 0)),
                    "bstr": fields.get("bstr", float("nan")),
                    "onset": int(fields.get("onset", 0)),
                    "bass": int(fields.get("bass", 0)),
                    "ostr": fields.get("ostr", float("nan")),
                }

                out["t_ms"].append(t_ms)
                out["bpm"].append(ap_row["bpm"])
                out["conf"].append(ap_row["conf"])
                out["lock"].append(ap_row["lock"])
                out["phase"].append(ap_row["phase"])
                out["beat"].append(ap_row["beat"])
                out["bstr"].append(ap_row["bstr"])
                out["onset"].append(ap_row["onset"])
                out["bass"].append(ap_row["bass"])
                out["ostr"].append(ap_row["ostr"])

                for k, v in ap_row.items():
                    if k != "t_ms":
                        out["ap_stream"][k].append(v)
                out["ap_stream"]["t_ms"].append(t_ms)
                out["ap_stream"]["n_parsed"] += 1
                out["n_parsed"] += 1
                parsed_any = True

        apcap = parse_apcap_line(line)
        if apcap is not None:
            if not apcap:
                _warn_once(out["warnings"], warn_seen, "[APCAP] marker with no parseable keys")
                _warn_once(out["ap_capture"]["warnings"], apcap_warn_seen,
                           "[APCAP] marker with no parseable keys")
                out["ap_capture"]["n_skipped"] += 1
            else:
                row = dict(apcap)
                row["t_ms"] = ts_ms if ts_ms is not None else (idx_cap * NOMINAL_APCAP_CADENCE_MS)
                idx_cap += 1
                out["ap_capture"]["records"].append(row)
                out["ap_capture"]["last"] = row
                out["ap_capture"]["n_parsed"] += 1
            parsed_any = True

        agc = parse_agc_line(line)
        if agc is not None:
            if not agc:
                _warn_once(out["warnings"], warn_seen,
                           "AGC stream marker present but no expected AGC fields parsed")
                _warn_once(out["agc_debug"]["warnings"], agc_warn_seen,
                           "AGC stream marker present but no expected AGC fields parsed")
                out["agc_debug"]["n_skipped"] += 1
            else:
                t_ms = ts_ms if ts_ms is not None else (idx_agc * NOMINAL_AGC_CADENCE_MS)
                idx_agc += 1
                block = out["agc_debug"]["samples"]
                block["t_ms"].append(t_ms)
                for key in AGC_KEYS:
                    vals = agc.get(key, [])
                    # store per-band medians; if field missing this frame, keep NaN
                    block[key].append(sum(vals) / len(vals) if vals else float("nan"))
                out["agc_debug"]["n_parsed"] += 1
            parsed_any = True

        nov = parse_nov_line(line)
        if nov is not None:
            if not nov:
                _warn_once(out["novelty_stream"]["warnings"], nov_warn_seen,
                           "NOV marker with no parseable keys")
                out["novelty_stream"]["n_skipped"] += 1
            else:
                row = dict(nov)
                t_token = row.get("t")
                if "t_ms" not in row:
                    row["t_ms"] = int(t_token) if t_token is not None else (
                        ts_ms if ts_ms is not None else idx_nov * 23
                    )
                idx_nov += 1
                missing = NOV_KEYS - set(row.keys())
                if missing:
                    _warn_once(out["novelty_stream"]["warnings"], nov_warn_seen,
                               f"NOV line missing key(s): {sorted(missing)}")
                unknown = set(row.keys()) - NOV_KEYS - {"t_ms"}
                if unknown:
                    _warn_once(out["novelty_stream"]["warnings"], nov_warn_seen,
                               f"NOV line had unexpected numeric key(s) retained: {sorted(unknown)}")
                out["novelty_stream"]["records"].append(row)
                out["novelty_stream"]["n_parsed"] += 1
            parsed_any = True

        apdbg = parse_apdbg_line(line)
        if apdbg is not None:
            if not apdbg:
                _warn_once(out["ap_frontend_debug"]["warnings"], apdbg_warn_seen,
                           "APDBG marker with no parseable keys")
                out["ap_frontend_debug"]["n_skipped"] += 1
            else:
                row = dict(apdbg)
                t_token = row.get("t")
                if "t_ms" not in row:
                    row["t_ms"] = int(t_token) if t_token is not None else (
                        ts_ms if ts_ms is not None else idx_apdbg * NOMINAL_APDBG_CADENCE_MS
                    )
                idx_apdbg += 1
                unknown = set(row.keys()) - APDBG_KEYS - {"t_ms"}
                if unknown:
                    _warn_once(out["ap_frontend_debug"]["warnings"], apdbg_warn_seen,
                               f"APDBG line had unexpected numeric key(s) retained: {sorted(unknown)}")
                out["ap_frontend_debug"]["records"].append(row)
                out["ap_frontend_debug"]["n_parsed"] += 1
            parsed_any = True

        if not parsed_any:
            out["n_skipped"] += 1

    if out["n_parsed"] == 0:
        _warn_once(out["warnings"], warn_seen,
                   "no [AP] lines parsed — AP_STREAM capture absent or wrong format")

    if out["ap_capture"]["n_parsed"] == 0:
        _warn_once(out["ap_capture"]["warnings"], apcap_warn_seen, "no APCAP lines parsed")

    if out["agc_debug"]["n_parsed"] == 0:
        _warn_once(out["agc_debug"]["warnings"], agc_warn_seen, "no AGC debug stream lines parsed")

    # propagate child warnings to top-level summary for compatibility and visibility
    for child in (out["ap_stream"]["warnings"], out["ap_capture"]["warnings"],
                  out["agc_debug"]["warnings"], out["novelty_stream"]["warnings"],
                  out["ap_frontend_debug"]["warnings"]):
        for w in child:
            _warn_once(out["warnings"], warn_seen, w)

    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="captured serial log (AP_STREAM / APCAP / AGC stream)")
    ap.add_argument("--track-id", default=None)
    ap.add_argument("--json", action="store_true", help="dump the full telemetry as JSON")
    args = ap.parse_args(argv)

    data = load_apstream(args.path, track_id=args.track_id)
    if data is None:
        print(f"NO FILE: {args.path}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=1))
        return 0

    print(f"path={args.path} track_id={data['track_id']} source={data['source']}")
    print(f"AP_STREAM parsed={data['ap_stream']['n_parsed']} skipped={data['ap_stream']['n_skipped']}")
    print(f"APCAP parsed={data['ap_capture']['n_parsed']} skipped={data['ap_capture']['n_skipped']}"
          f" last={('none' if data['ap_capture']['last'] is None else data['ap_capture']['last'].get('frames', 'n/a'))}")
    print(f"AGC parsed={data['agc_debug']['n_parsed']} skipped={data['agc_debug']['n_skipped']}" )
    print(f"NOV parsed={data['novelty_stream']['n_parsed']} skipped={data['novelty_stream']['n_skipped']}")
    print(f"APDBG parsed={data['ap_frontend_debug']['n_parsed']} skipped={data['ap_frontend_debug']['n_skipped']}")

    if data["bpm"]:
        import statistics

        valid = [b for b in data["bpm"] if b == b]  # drop NaN
        if valid:
            print(f"  bpm range {min(valid):.1f}..{max(valid):.1f} median {statistics.median(valid):.1f}")
        print(f"  lock frames {sum(data['lock'])}/{data['n_parsed']}  "
              f"beat ticks {sum(data['beat'])}  onset ticks {sum(data['onset'])}")

    for w in data["warnings"]:
        print(f"  WARN: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
