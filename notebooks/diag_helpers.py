#!/usr/bin/env python3
"""Display-only helpers for notebooks/audio_semantic_diagnostics.ipynb.

PURE LOAD + PLOT. numpy + matplotlib + stdlib (json, wave) ONLY. NO pandas, NO
soundfile, and — critically — NO DSP: this module reimplements no tempo, beat,
onset, saliency, or AP pipeline. It loads the canonical harness artifacts
(trajectory JSONs, A/B metric JSONs, the WAV waveform, optional AP_STREAM capture)
and renders them. Every numeric value plotted is produced upstream by the
UNMODIFIED firmware via the host harness; this layer only displays it.

Display-derived things that ARE allowed here (per the task contract): FP/miss
markers, tolerance bands, novelty normalisation for plotting, and the
beat_tick raw-vs-dedup view. These are presentation, not metric definitions —
acceptance numbers come from the JSON artifacts, never from this module.

Mandatory annotations this module enforces:
  * HOST_CEILING_CAPTION on every host-modelled front-end plot.
  * Every host/device overlay labels the host-modelled trace, the device
    AP_STREAM trace, and whether the capture is matched to the same track.
"""

import json
import wave
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless-safe; notebooks override to inline as needed
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------- paths
_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
METRICS_DIR = ROOT / "build" / "audio-semantic-metrics"
TRAJ_DIR = METRICS_DIR / "trajectories"
CORPUS_DIR = ROOT / "Lightwave-Ledstrip/firmware-v3/test/music_corpus/harmonixset/esv11_benchmark/audio_12k8"

# mandatory caption / labels
HOST_CEILING_CAPTION = "MODELLED FRONT-END / HOST CEILING — not guaranteed to match device AP_STREAM."
HOST_TRACE_LABEL = "host-modelled (harness)"
DEVICE_TRACE_LABEL = "device AP_STREAM (capture)"
APCAP_TRACE_LABEL = "device AP_CAPTURE summary"
AGC_TRACE_LABEL = "device AGC debug (band medians)"


# ---------------------------------------------------------------------------- caption helpers
def host_caption(ax):
    """Stamp the mandatory host-ceiling caption under a host-modelled front-end plot."""
    ax.annotate(HOST_CEILING_CAPTION, xy=(0.0, -0.22), xycoords="axes fraction",
                fontsize=8, color="#b00020", style="italic", va="top")


def overlay_match_label(ax, traj_track_id, apstream_track_id):
    """Stamp whether the AP_STREAM capture is matched to the trajectory's track."""
    if apstream_track_id is None:
        note = "device capture: track match UNKNOWN (no track_id on capture)"
    elif apstream_track_id == traj_track_id:
        note = f"device capture MATCHED to track {traj_track_id}"
    else:
        note = f"device capture NOT matched (capture={apstream_track_id} vs traj={traj_track_id})"
    ax.annotate(note, xy=(0.0, -0.30), xycoords="axes fraction",
                fontsize=8, color="#00468b", va="top")


# ---------------------------------------------------------------------------- loaders
def load_json(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def load_trajectory(track_id, run):
    """Load build/audio-semantic-metrics/trajectories/<track_id>__<run>.json or None."""
    return load_json(TRAJ_DIR / f"{track_id}__{run}.json")


def list_trajectory_tracks():
    """Track ids that have at least one exported trajectory."""
    if not TRAJ_DIR.is_dir():
        return []
    ids = set()
    for p in TRAJ_DIR.glob("*__*.json"):
        ids.add(p.name.split("__", 1)[0])
    return sorted(ids)


def find_wav(track_id):
    """Locate the corpus WAV for a track_id (stem startswith track_id)."""
    if not CORPUS_DIR.is_dir():
        return None
    cands = list(CORPUS_DIR.glob(f"{track_id}*.wav"))
    return cands[0] if cands else None


def load_waveform(track_id, max_points=200_000):
    """Load a corpus WAV via stdlib `wave` + numpy (NO soundfile). Returns
    (t_s[], mono[], sr) downsampled to <= max_points for plotting, or None."""
    wav = find_wav(track_id)
    if wav is None:
        return None
    with wave.open(str(wav), "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        sw = w.getsampwidth()
        nframes = w.getnframes()
        raw = w.readframes(nframes)
    if sw == 2:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif sw == 1:
        data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128.0) / 128.0
    elif sw == 4:
        data = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if nch > 1:
        data = data.reshape(-1, nch).mean(axis=1)
    t = np.arange(data.size) / float(sr)
    if data.size > max_points:
        step = data.size // max_points
        data = data[::step]
        t = t[::step]
    return t, data, sr


def load_apstream(path, track_id=None):
    """Thin wrapper around scripts/regression-harness/apstream_ingest.load_apstream.
    Returns a device telemetry dict (legacy AP_STREAM at top-level plus\n+    optional `ap_stream`, `ap_capture`, `agc_debug` blocks), or None if the\n+    path is absent/empty."""
    if not path:
        return None
    import importlib.util
    mod_path = ROOT / "scripts" / "regression-harness" / "apstream_ingest.py"
    spec = importlib.util.spec_from_file_location("apstream_ingest", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.load_apstream(path, track_id=track_id)


def load_ab(name):
    """Load an A/B metric artifact by base name (baseline/final/onset_v2_ab/chord_v2_ab)."""
    return load_json(METRICS_DIR / f"{name}.json")


def ab_track(ab_json, track_id):
    """Pull the per-track record for a youtube_id out of a baseline/final A/B json."""
    if not ab_json:
        return None
    for t in ab_json.get("tracks", []):
        if t.get("youtube_id") == track_id:
            return t
    return None


# ---------------------------------------------------------------------------- small utils
def _arr(d, *keys):
    cur = d
    for k in keys:
        if cur is None:
            return np.array([])
        cur = cur.get(k) if isinstance(cur, dict) else None
    return np.array(cur if cur is not None else [], dtype=float)


def _window_mask(t_ms, window_s):
    if window_s is None:
        return np.ones(t_ms.shape, dtype=bool)
    lo, hi = window_s
    return (t_ms >= lo * 1000.0) & (t_ms <= hi * 1000.0)


def smooth(y, k=15):
    """Display-only moving-average smoother (presentation, not a DSP/metric change)."""
    y = np.asarray(y, dtype=float)
    if y.size < 3 or k < 2:
        return y
    k = min(k, y.size)
    ker = np.ones(k) / k
    return np.convolve(y, ker, mode="same")


def beat_tick_times_ms(traj, dedup=True):
    """Event-time list (ms) where beat_tick fired (dedup or raw)."""
    f = traj.get("frames", {})
    t = np.array(f.get("t_ms", []), dtype=float)
    key = "beat_tick_dedup" if dedup else "beat_tick_raw"
    tk = np.array(f.get(key, []), dtype=int)
    if t.size == 0 or tk.size == 0:
        return np.array([])
    return t[tk[: t.size] == 1]


def _series(records, key):
    """Extract numeric series from APCAP records (`dict` or scalar values)."""
    out = []
    for r in records:
        if not isinstance(r, dict):
            out.append(np.nan)
            continue
        v = r.get(key)
        if isinstance(v, dict):
            lo = v.get("min")
            hi = v.get("max")
            nums = [x for x in (lo, hi) if isinstance(x, (int, float, np.number))]
            out.append(float(np.nanmean(nums)) if nums else np.nan)
        elif v is None:
            out.append(np.nan)
        elif isinstance(v, (int, float, np.number)):
            out.append(float(v))
        else:
            try:
                out.append(float(v))
            except (TypeError, ValueError):
                out.append(np.nan)
    return np.array(out, dtype=float)


def _series_range(records, key):
    lo, hi = [], []
    for r in records:
        v = r.get(key) if isinstance(r, dict) else None
        if isinstance(v, dict):
            lo.append(v.get("min", np.nan))
            hi.append(v.get("max", np.nan))
        else:
            lo.append(np.nan)
            hi.append(np.nan)
    return np.array(lo, dtype=float), np.array(hi, dtype=float)


# ---------------------------------------------------------------------------- PLOTS (sections)
def plot_waveform(track_id, window_s=None, ax=None):
    """Section 2 — track waveform (corpus audio samples; this IS the source music,
    not a modelled signal, so no host-ceiling caption is required)."""
    wf = load_waveform(track_id)
    ax = ax or plt.gca()
    if wf is None:
        ax.text(0.5, 0.5, f"no WAV for {track_id}", ha="center", va="center")
        return ax
    t, y, sr = wf
    if window_s is not None:
        m = (t >= window_s[0]) & (t <= window_s[1])
        t, y = t[m], y[m]
    ax.plot(t, y, lw=0.4, color="#444")
    ax.set_title(f"Waveform — {track_id} (corpus audio @ {sr} Hz)")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("amplitude")
    return ax


def plot_novelty(traj, window_s=None, normalize=True, ax=None):
    """Section 3 — modelled front-end novelty (HOST CEILING)."""
    ax = ax or plt.gca()
    f = traj.get("frames", {})
    t = np.array(f.get("t_ms", []), dtype=float) / 1000.0
    nov = np.array(f.get("novelty", []), dtype=float)
    m = _window_mask(t * 1000.0, window_s)
    t, nov = t[m], nov[m[: nov.size]] if nov.size else nov
    if normalize and nov.size and nov.max() > 0:
        nov = nov / nov.max()
    ax.plot(t, nov, lw=0.7, color="#1f77b4", label=HOST_TRACE_LABEL + " novelty")
    ax.set_title(f"Modelled front-end novelty — {traj.get('track_id')} [{traj.get('run')}]")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("novelty" + (" (norm)" if normalize else ""))
    ax.legend(loc="upper right", fontsize=8)
    host_caption(ax)
    return ax


def plot_apstream_overlay(traj, apstream, show=True, ax=None):
    """Section 4 — device AP_STREAM overlay vs host-modelled bpm/conf/lock.
    If no capture, prints the explicit 'host-modelled only' note."""
    ax = ax or plt.gca()
    f = traj.get("frames", {})
    t = np.array(f.get("t_ms", []), dtype=float) / 1000.0
    bpm = np.array(f.get("bpm", []), dtype=float)
    ax.plot(t, bpm, lw=0.7, color="#1f77b4", label=HOST_TRACE_LABEL + " bpm")
    stream = apstream
    if isinstance(apstream, dict) and "ap_stream" in apstream:
        stream = apstream.get("ap_stream")
    if not show or stream is None or stream.get("n_parsed", 0) == 0:
        ax.set_title(f"AP_STREAM overlay — {traj.get('track_id')} "
                     "(NO device capture — host-modelled only)")
        ax.text(0.5, 0.9, "no device capture — host-modelled trajectory only",
                transform=ax.transAxes, ha="center", color="#b00020", fontsize=9)
    else:
        dt = np.array(stream.get("t_ms", []), dtype=float) / 1000.0
        dbpm = np.array(stream.get("bpm", []), dtype=float)
        ax.plot(dt, dbpm, "o-", ms=3, lw=0.8, color="#d62728",
                label=DEVICE_TRACE_LABEL + " bpm (~1 Hz)")
        ax.set_title(f"AP_STREAM overlay — {traj.get('track_id')} [{traj.get('run')}]")
        overlay_match_label(ax, traj.get("track_id"), stream.get("track_id"))
    ax.set_xlabel("time (s)")
    ax.set_ylabel("bpm")
    ax.legend(loc="upper right", fontsize=8)
    host_caption(ax)
    return ax


def plot_ap_capture_summary(ap_capture, window_s=None, ax=None):
    """Section 4a — APCAP summary stream for the current track session."""
    ax = ax or plt.gca()
    if not ap_capture:
        ax.text(0.5, 0.5, "no APCAP block requested or loaded", ha="center", va="center",
                color="#b00020")
        return ax

    recs = ap_capture.get("records", [])
    if not recs:
        ax.text(0.5, 0.5, "APCAP requested but no records parsed from this capture", ha="center", va="center",
                color="#b00020")
        return ax

    t = np.array([r.get("t_ms", i * 5000) for i, r in enumerate(recs)], dtype=float) / 1000.0
    m = _window_mask(t * 1000.0, window_s)
    t = t[m]
    if t.size == 0:
        t = np.array([r.get("t_ms", i * 5000) for i, r in enumerate(recs)], dtype=float) / 1000.0
        m = np.ones(t.shape, dtype=bool)
    follower = _series(recs, "follower_mean")
    chroma = _series(recs, "chroma_mean")
    spec = _series(recs, "spec_argmax")
    frames = _series(recs, "frames")
    max_raw_lo, max_raw_hi = _series_range(recs, "max_raw")
    peak_lo, peak_hi = _series_range(recs, "peak_scaled")

    follower = follower[m[: follower.size]]
    chroma = chroma[m[: chroma.size]]
    spec = spec[m[: spec.size]]
    frames = frames[m[: frames.size]]
    max_raw_lo = max_raw_lo[m[: max_raw_lo.size]]
    max_raw_hi = max_raw_hi[m[: max_raw_hi.size]]
    peak_lo = peak_lo[m[: peak_lo.size]]
    peak_hi = peak_hi[m[: peak_hi.size]]

    if follower.size:
        ax.plot(t[:follower.size], follower, lw=0.8, color="#1f77b4", label="follower_mean")
    if chroma.size:
        ax.plot(t[:chroma.size], chroma, lw=0.8, color="#2ca02c", label="chroma_mean")
    if spec.size:
        ax.plot(t[:spec.size], spec, lw=0.8, color="#9467bd", label="spec_argmax")
    if frames.size:
        ax.plot(t[:frames.size], frames, lw=0.8, color="#8c564b", alpha=0.75, label="frames")
    if np.isfinite(max_raw_lo).any() and np.isfinite(max_raw_hi).any():
        x = t[:max_raw_lo.size]
        ax.plot(x, (max_raw_lo + max_raw_hi) / 2.0, lw=0.8, color="#d62728", label="max_raw mean")
        ax.fill_between(x, max_raw_lo, max_raw_hi, color="#d62728", alpha=0.08)
    if np.isfinite(peak_lo).any() and np.isfinite(peak_hi).any():
        x = t[:peak_lo.size]
        ax.plot(x, (peak_lo + peak_hi) / 2.0, lw=0.8, color="#ff7f0e", label="peak_scaled mean")
        ax.fill_between(x, peak_lo, peak_hi, color="#ff7f0e", alpha=0.08)

    last = ap_capture.get("last", {})
    notes = [
        f"APCAP parsed={ap_capture.get('n_parsed', 0)}",
        f"skipped={ap_capture.get('n_skipped', 0)}",
        f"last.frames={last.get('frames', 'n/a')}",
    ]
    ax.annotate(" | ".join(notes), xy=(0.0, -0.20), xycoords="axes fraction",
                fontsize=7, color="#00468b", va="top")
    ax.set_title(f"APCAP capture summary — {APCAP_TRACE_LABEL}")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("APCAP scalar")
    ax.legend(loc="upper right", fontsize=7)
    return ax


def plot_agc_debug(agc_debug, window_s=None, ax=None):
    """Section 4b — AGC debug debug stream (band medians over time)."""
    ax = ax or plt.gca()
    if not agc_debug:
        ax.text(0.5, 0.5, "no AGC debug block requested or loaded", ha="center", va="center",
                color="#b00020")
        return ax

    s = agc_debug.get("samples", {})
    t = np.array(s.get("t_ms", []), dtype=float) / 1000.0
    if t.size == 0:
        ax.text(0.5, 0.5, "AGC stream requested but no samples parsed", ha="center", va="center",
                color="#b00020")
        return ax
    m = _window_mask(t * 1000.0, window_s)
    t_plot = t[m] if m.size == t.size else t

    for key in ("energy", "gain", "threshold", "floor"):
        v = np.array(s.get(key, []), dtype=float)
        if m.size == t.size:
            v = v[m[: v.size]]
        if v.size == 0:
            continue
        if v.size > t_plot.size:
            v = v[:t_plot.size]
            t_local = t_plot
        elif t_plot.size > v.size:
            t_local = t_plot[:v.size]
        else:
            t_local = t_plot

        if key == "floor":
            color = "#2ca02c"
        elif key == "gain":
            color = "#d62728"
        elif key == "energy":
            color = "#1f77b4"
        else:
            color = "#ff7f0e"
        ax.plot(t_local, v, lw=0.8, label=f"{AGC_TRACE_LABEL} {key}", color=color)

    ax.set_title(f"AGC debug stream — {agc_debug.get('n_parsed', 0)} samples")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("AGC fields")
    ax.legend(loc="upper right", fontsize=7)
    return ax


def plot_tempogram(traj, ax=None):
    """Section 5 — tempogram / ACF / comb heatmap from the RAWSPEC artifact, else fallback."""
    ax = ax or plt.gca()
    tg = traj.get("tempogram")
    if not tg or not tg.get("magnitude"):
        ax.text(0.5, 0.5, "tempogram not available as artifact —\nhost BPM trajectory shown instead",
                ha="center", va="center", color="#b00020", fontsize=9)
        f = traj.get("frames", {})
        t = np.array(f.get("t_ms", []), dtype=float) / 1000.0
        ax.plot(t, np.array(f.get("bpm", []), dtype=float), lw=0.6, color="#1f77b4")
        ax.set_title(f"BPM trajectory (no tempogram) — {traj.get('track_id')}")
        host_caption(ax)
        return ax
    bpm_axis = np.array(tg["bpm_axis"], dtype=float)
    mag = np.array(tg["magnitude"], dtype=float)
    ax.bar(bpm_axis, mag, width=1.0, color="#1f77b4")
    gt_bpm = traj.get("gt", {}).get("bpm")
    if gt_bpm:
        ax.axvline(gt_bpm, color="#2ca02c", ls="--", lw=1.2, label=f"GT {gt_bpm:.0f} BPM")
        ax.legend(loc="upper right", fontsize=8)
    ax.set_title(f"Tempo periodicity surface (sb_tempo RAWSPEC) — {traj.get('track_id')} [{traj.get('run')}]")
    ax.set_xlabel("BPM (Goertzel bin = 60+i)")
    ax.set_ylabel("magnitude")
    host_caption(ax)
    return ax


def plot_bpm_vs_gt(traj, window_s=None, show_gt=True, ax=None):
    """Section 6 — BPM over time vs GT line."""
    ax = ax or plt.gca()
    f = traj.get("frames", {})
    t = np.array(f.get("t_ms", []), dtype=float) / 1000.0
    bpm = np.array(f.get("bpm", []), dtype=float)
    m = _window_mask(t * 1000.0, window_s)
    ax.plot(t[m], bpm[m[: bpm.size]] if bpm.size else bpm, lw=0.7, color="#1f77b4",
            label=HOST_TRACE_LABEL + " bpm")
    gt_bpm = traj.get("gt", {}).get("bpm")
    if show_gt and gt_bpm:
        ax.axhline(gt_bpm, color="#2ca02c", ls="--", lw=1.2, label=f"GT {gt_bpm:.0f} BPM")
        for k, lab in [(0.5, "½×"), (2.0, "2×")]:
            ax.axhline(gt_bpm * k, color="#2ca02c", ls=":", lw=0.6, alpha=0.6)
    ax.set_title(f"BPM over time vs GT — {traj.get('track_id')} [{traj.get('run')}]")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("bpm")
    ax.legend(loc="upper right", fontsize=8)
    host_caption(ax)
    return ax


def plot_conf_lock(traj, window_s=None, lock_threshold=0.60, raw_vs_smooth=True, ax=None):
    """Section 7 — confidence + lock overlay; threshold line; lock/unlock events."""
    ax = ax or plt.gca()
    f = traj.get("frames", {})
    t = np.array(f.get("t_ms", []), dtype=float) / 1000.0
    conf = np.array(f.get("conf", []), dtype=float)
    locked = np.array(f.get("locked", []), dtype=int)
    m = _window_mask(t * 1000.0, window_s)
    tw = t[m]
    cw = conf[m[: conf.size]] if conf.size else conf
    lw_ = locked[m[: locked.size]] if locked.size else locked
    ax.plot(tw, cw, lw=0.6, color="#1f77b4", alpha=0.6, label=HOST_TRACE_LABEL + " conf (raw)")
    if raw_vs_smooth and cw.size:
        ax.plot(tw, smooth(cw, 21), lw=1.3, color="#ff7f0e", label="conf (smoothed, display)")
    ax.axhline(lock_threshold, color="#777", ls="--", lw=1.0, label=f"lock threshold {lock_threshold:.2f}")
    # lock/unlock edge events
    if lw_.size > 1:
        edges = np.diff(lw_)
        for i in np.where(edges == 1)[0]:
            ax.axvline(tw[i + 1], color="#2ca02c", lw=0.8, alpha=0.6)
        for i in np.where(edges == -1)[0]:
            ax.axvline(tw[i + 1], color="#d62728", lw=0.8, alpha=0.6)
    ax.set_ylim(-0.02, 1.05)
    ax.set_title(f"Confidence + lock — {traj.get('track_id')} [{traj.get('run')}] "
                 "(green=lock, red=unlock)")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("confidence")
    ax.legend(loc="upper right", fontsize=7)
    host_caption(ax)
    return ax


def plot_beat_vs_gt(traj, window_s=None, beat_tol_ms=70.0, show_gt=True,
                    raw_vs_dedup="dedup", ax=None):
    """Section 8 — predicted beat_tick vs GT with tolerance band, FP/miss highlight.
    Highlighting is DISPLAY-derived (allowed). Density note printed in the title."""
    ax = ax or plt.gca()
    use_dedup = raw_vs_dedup != "raw"
    pred = beat_tick_times_ms(traj, dedup=use_dedup)
    gt = np.array(traj.get("gt", {}).get("beat_times_s", []), dtype=float) * 1000.0
    if window_s is not None:
        pred = pred[(pred >= window_s[0] * 1000.0) & (pred <= window_s[1] * 1000.0)]
        gt = gt[(gt >= window_s[0] * 1000.0) & (gt <= window_s[1] * 1000.0)]
    # GT lane (y=1), predicted lane (y=0)
    if show_gt and gt.size:
        ax.vlines(gt / 1000.0, 0.6, 1.0, color="#2ca02c", lw=1.0, label="GT beats")
        for g in gt:
            ax.axvspan((g - beat_tol_ms) / 1000.0, (g + beat_tol_ms) / 1000.0,
                       0.0, 0.5, color="#2ca02c", alpha=0.07)
    # match pred to GT (display-only greedy ±tol) for FP/miss colouring
    matched_pred = np.zeros(pred.size, dtype=bool)
    matched_gt = np.zeros(gt.size, dtype=bool)
    for j, g in enumerate(gt):
        if pred.size == 0:
            break
        d = np.abs(pred - g)
        i = int(np.argmin(d))
        if d[i] <= beat_tol_ms and not matched_pred[i]:
            matched_pred[i] = True
            matched_gt[j] = True
    for i, p in enumerate(pred):
        col = "#1f77b4" if matched_pred[i] else "#d62728"  # blue=hit, red=false-positive
        ax.vlines(p / 1000.0, 0.0, 0.4, color=col, lw=1.0)
    # missed GT beats (no predicted within tol)
    if gt.size:
        ax.plot(gt[~matched_gt] / 1000.0, np.full((~matched_gt).sum(), 0.8),
                "x", color="#d62728", ms=6, label="missed GT")
    n_pred, n_gt = pred.size, gt.size
    dens = n_pred / max((window_s[1] - window_s[0]) if window_s else
                        ((traj["frames"]["t_ms"][-1] / 1000.0) if traj["frames"]["t_ms"] else 1.0), 1e-6)
    ax.set_yticks([0.2, 0.8]); ax.set_yticklabels(["predicted", "GT"])
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(f"Beat tick vs GT — {traj.get('track_id')} [{traj.get('run')}]  "
                 f"({raw_vs_dedup}: {n_pred} pred vs {n_gt} GT, ~{dens:.2f} Hz; blue=hit red=FP/miss)")
    ax.set_xlabel("time (s)")
    ax.legend(loc="upper right", fontsize=7)
    host_caption(ax)
    return ax


def plot_onset_channels(traj, window_s=None, ax=None):
    """Section 9 — onset channels (transient/kick/snare/hihat). final run only."""
    ax = ax or plt.gca()
    oc = traj.get("onset_channels", {})
    chans = [("transient_ms", "#9467bd"), ("kick_ms", "#8c564b"),
             ("snare_ms", "#e377c2"), ("hihat_ms", "#17becf")]
    any_ev = False
    for row, (key, col) in enumerate(chans):
        ev = np.array(oc.get(key, []), dtype=float)
        if window_s is not None and ev.size:
            ev = ev[(ev >= window_s[0] * 1000.0) & (ev <= window_s[1] * 1000.0)]
        if ev.size:
            any_ev = True
        ax.vlines(ev / 1000.0, row + 0.1, row + 0.9, color=col, lw=0.8)
    ax.set_yticks([i + 0.5 for i in range(len(chans))])
    ax.set_yticklabels([c[0].replace("_ms", "") for c in chans])
    if not any_ev:
        ax.text(0.5, 0.5, "no onset channels (baseline run — V2-only)\n"
                "beat/downbeat are sb_tempo-owned; downbeat not available",
                transform=ax.transAxes, ha="center", va="center", color="#b00020", fontsize=9)
    ax.set_title(f"Onset channels — {traj.get('track_id')} [{traj.get('run')}]  "
                 "(beat/downbeat are sb_tempo-owned; downbeat N/A)")
    ax.set_xlabel("time (s)")
    host_caption(ax)
    return ax


def plot_harmonic_state(chord_ab, ax=None):
    """Section 10 — harmonic/chord state from chord_v2_ab.json (SYNTHETIC A/B).
    There is no per-track chord stream; this displays the harness's chord-detection
    confidences + harmonic-saliency-axis A/B."""
    ax = ax or plt.gca()
    if not chord_ab:
        ax.text(0.5, 0.5, "chord_v2_ab.json not available", ha="center", va="center")
        return ax
    cd = chord_ab.get("chord_detection", {}).get("confidences", {})
    names = list(cd.keys())
    vals = [cd[n] for n in names]
    ax.barh(range(len(names)), vals, color="#1f77b4")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("detector confidence")
    hsa = chord_ab.get("harmonic_saliency_axis", {})
    sub = (f"harmonic axis A/B: incumbent dead={hsa.get('incumbent_peak_dead')}, "
           f"v2 root-spike={hsa.get('v2_raw_root_change_spike')}, "
           f"v2 type-spike={hsa.get('v2_raw_type_change_spike')}, "
           f"v2 alive-peak={hsa.get('v2_smoothed_peak_alive')}")
    ax.set_title("Harmonic / chord state (SYNTHETIC fixtures — chord_v2_ab.json)\n" + sub,
                 fontsize=8)
    ax.annotate("Synthetic labelled-fixture A/B; NOT a per-track real-music chord stream.",
                xy=(0.0, -0.18), xycoords="axes fraction", fontsize=8,
                color="#b00020", style="italic", va="top")
    return ax


# ---------------------------------------------------------------------------- A/B (section 11)
def ab_aggregate_rows(baseline, final):
    """Build the headline A/B delta table from baseline.json + final.json aggregates.
    Returns a list of (metric, baseline_val, final_val, delta). Metrics come straight
    from the JSON aggregates — this module computes no acceptance logic."""
    if not baseline or not final:
        return []
    ba, fa = baseline.get("aggregate", {}), final.get("aggregate", {})
    keys = [
        ("frac_tracks_ever_reach_060", "conf reachability (frac tracks reach .60)"),
        ("frac_tracks_ever_locked", "frac tracks ever locked"),
        ("median_settled_conf", "median settled conf"),
        ("median_max_conf", "median max conf"),
        ("beat_F_metrical_best_mean", "beat-F (metrical-best, mean)"),
        ("beat_F_x1_mean", "beat-F (x1, mean)"),
        ("cmlt_like_mean", "CMLt-like continuity (mean)"),
        ("amlt_like_mean", "AMLt-like continuity (mean)"),
        ("frac_tracks_density_in_band", "frac tracks density-in-band"),
        ("median_pred_density_hz", "median pred density (Hz)"),
    ]
    rows = []
    for k, label in keys:
        b, fv = ba.get(k), fa.get(k)
        if b is None or fv is None:
            continue
        rows.append((label, float(b), float(fv), float(fv) - float(b)))
    return rows


def false_lock_rows(baseline, final):
    """False-lock A/B (silence/noise lock_frac + max_conf) from the aggregates."""
    out = []
    for name, j in [("baseline", baseline), ("final", final)]:
        fl = (j or {}).get("aggregate", {}).get("false_lock", {})
        for probe in ("silence", "noise"):
            d = fl.get(probe, {})
            out.append((name, probe, d.get("lock_frac"), d.get("max_conf")))
    return out


def onset_proxy_rows(onset_ab):
    """Onset proxy P/R/F1 incumbent-vs-v2 + AGC-clamp survival from onset_v2_ab.json."""
    if not onset_ab:
        return None
    s = onset_ab.get("summary", {})
    agc = onset_ab.get("agc_clamp", {})
    return {
        "incumbent_pr": s.get("incumbent_pr_proxy"),
        "v2_pr": s.get("v2_pr_proxy"),
        "n_tracks": s.get("n_tracks_scored"),
        "agc": agc,
    }


def plot_ab_summary(baseline, final, onset_ab=None, ax=None):
    """Section 11 — baseline vs final headline deltas as a labelled bar chart."""
    ax = ax or plt.gca()
    rows = ab_aggregate_rows(baseline, final)
    if not rows:
        ax.text(0.5, 0.5, "baseline.json / final.json not available", ha="center", va="center")
        return ax
    labels = [r[0] for r in rows]
    bvals = [r[1] for r in rows]
    fvals = [r[2] for r in rows]
    y = np.arange(len(labels))
    ax.barh(y - 0.2, bvals, height=0.4, color="#777", label="baseline")
    ax.barh(y + 0.2, fvals, height=0.4, color="#1f77b4", label="final (CONF_V2+FLYWHEEL_V2)")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("metric value (from JSON aggregates)")
    ax.set_title("A/B: baseline vs final (host harness aggregates — no notebook acceptance logic)")
    ax.legend(loc="lower right", fontsize=8)
    return ax
