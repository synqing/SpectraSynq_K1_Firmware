#!/usr/bin/env python3
"""Fallback headless renderer for the audio-semantic diagnostics — runs the SAME
diag_helpers logic the notebook uses, under /opt/homebrew/bin/python3 (which HAS
numpy + matplotlib), and writes the three RUN_MODE HTML files:

  build/audio-semantic-visuals/{baseline,final,ab_diff}/index.html

This exists for the case where no Jupyter kernel can execute the .ipynb (the
miniforge base lacks numpy/ipykernel). It mirrors the notebook's 12 sections,
embedding each matplotlib figure as a base64 PNG in an HTML template. It is
DISPLAY-ONLY and reimplements no DSP — it imports notebooks/diag_helpers.py and
calls the exact same plot functions, with the exact same mandatory captions/labels.

The PREFERRED path is `render_via_nbconvert.py` (executes the real notebook);
this is the documented fallback per the package spec. Run:
  /opt/homebrew/bin/python3 scripts/regression-harness/render_diagnostics.py
  /opt/homebrew/bin/python3 scripts/regression-harness/render_diagnostics.py --track 7vevOMWY6MY
"""

import argparse
import base64
import io
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))
sys.path.insert(0, str(_HERE))
import diag_helpers as dh  # noqa: E402

OUT_BASE = ROOT / "build" / "audio-semantic-visuals"
DEFAULT_TRACK = "7vevOMWY6MY"
RUN_MODES = ["baseline", "final", "ab"]
RUN_DIR = {"baseline": "baseline", "final": "final", "ab": "ab_diff"}


def fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=90, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# Mandatory host-ceiling caption, emitted as HTML TEXT under every figure so the
# disclaimer is greppable/auditable, not only baked into the PNG pixels.
HOST_CEILING_CAPTION = ("MODELLED FRONT-END / HOST CEILING — not guaranteed to "
                        "match device AP_STREAM.")


def section(html_parts, n, title, fig=None, text=None):
    html_parts.append(f"<h2>{n}. {title}</h2>")
    if text:
        html_parts.append(f"<pre>{text}</pre>")
    if fig is not None:
        b64 = fig_to_b64(fig)
        html_parts.append(f'<img src="data:image/png;base64,{b64}" style="max-width:100%;"/>')
        html_parts.append(
            '<p class="host-ceiling" style="color:#777;font-size:11px;margin:2px 0 0">'
            f'{HOST_CEILING_CAPTION}</p>')


def render_run(track_id, run_mode, apstream_path=None):
    run = "final" if run_mode == "ab" else run_mode
    traj = dh.load_trajectory(track_id, run)
    ab_baseline = dh.load_ab("baseline")
    ab_final = dh.load_ab("final")
    ab_onset = dh.load_ab("onset_v2_ab")
    ab_chord = dh.load_ab("chord_v2_ab")
    apstream = dh.load_apstream(apstream_path, track_id=track_id) if apstream_path else None

    H = []
    H.append(f"<h1>Audio Semantic Diagnostics — {track_id} [{run_mode}]</h1>")
    H.append('<p style="color:#b00020"><b>DISPLAY-ONLY.</b> No DSP reimplemented. '
             'Every value is firmware-produced via the host harness; this is the host ceiling, '
             'not a device-matched result. Acceptance numbers come from the JSON artifacts.</p>')

    # 1 Provenance
    if traj:
        p = traj["provenance"]
        prov = (f"branch         : {p['branch']}\n"
                f"head           : {p['head']}\n"
                f"run / flags    : {traj['run']}  {p['flags']}\n"
                f"sample_rate_hz : {p['sample_rate_hz']}   hop: {p['hop']}\n"
                f"ap_frame_hz    : {p['ap_frame_hz']:.3f}   novelty_rate_hz(/3): {p['novelty_rate_hz']:.3f}\n"
                f"corpus_path    : {p['corpus_path']}\n"
                f"gt_source      : {p['gt_source']}\n"
                f"harness_cmd    : {p['harness_cmd']}\n"
                f"curated_reason : {p['curated_reason']}\n"
                f"GT bpm / title : {traj['gt']['bpm']}  {traj['gt']['title']} ({traj['gt']['genre']})")
        section(H, 1, "Provenance", text=prov)
    else:
        section(H, 1, "Provenance", text=f"NO TRAJECTORY for {track_id} [{run}] — run the exporter.")

    # 2 waveform
    fig, ax = plt.subplots(figsize=(12, 2.6)); dh.plot_waveform(track_id, ax=ax)
    section(H, 2, "Track metadata + waveform", fig=fig)

    if traj:
        # 3 novelty
        fig, ax = plt.subplots(figsize=(12, 2.8)); dh.plot_novelty(traj, ax=ax)
        section(H, 3, "Modelled front-end novelty", fig=fig)
        # 4 apstream
        fig, ax = plt.subplots(figsize=(12, 3.0))
        dh.plot_apstream_overlay(traj, apstream, show=apstream is not None, ax=ax)
        section(H, 4, "AP_STREAM overlay", fig=fig)
        # 5 tempogram
        fig, ax = plt.subplots(figsize=(12, 3.0)); dh.plot_tempogram(traj, ax=ax)
        section(H, 5, "Tempogram / ACF / comb heatmap", fig=fig)
        # 6 bpm vs gt
        fig, ax = plt.subplots(figsize=(12, 3.0)); dh.plot_bpm_vs_gt(traj, ax=ax)
        section(H, 6, "BPM over time vs GT", fig=fig)
        # 7 conf+lock
        fig, ax = plt.subplots(figsize=(12, 3.0)); dh.plot_conf_lock(traj, ax=ax)
        section(H, 7, "Confidence + lock overlay", fig=fig)
        # 8 beat vs gt
        fig, ax = plt.subplots(figsize=(12, 2.6)); dh.plot_beat_vs_gt(traj, beat_tol_ms=70, ax=ax)
        raw_n = int(dh.beat_tick_times_ms(traj, dedup=False).size)
        dd_n = int(dh.beat_tick_times_ms(traj, dedup=True).size)
        section(H, 8, "Predicted beat_tick vs GT", fig=fig,
                text=f"beat_tick density — raw: {raw_n}, dedup: {dd_n} "
                     "(raw carries the 133 Hz stale-republish; dedup is the leading-edge view)")
        # 9 onset channels
        fig, ax = plt.subplots(figsize=(12, 2.6)); dh.plot_onset_channels(traj, ax=ax)
        section(H, 9, "Onset channels", fig=fig)

    # 10 harmonic
    fig, ax = plt.subplots(figsize=(10, 4.0)); dh.plot_harmonic_state(ab_chord, ax=ax)
    section(H, 10, "Harmonic / chord state (synthetic A/B)", fig=fig)

    # 11 A/B
    fig, ax = plt.subplots(figsize=(11, 4.5)); dh.plot_ab_summary(ab_baseline, ab_final, ab_onset, ax=ax)
    ab_text_lines = ["headline aggregate deltas (baseline -> final):"]
    for label, b, f, d in dh.ab_aggregate_rows(ab_baseline, ab_final):
        ab_text_lines.append(f"  {label:48} {b:8.4f} -> {f:8.4f}   ({'+' if d>=0 else ''}{d:.4f})")
    ab_text_lines.append("false-lock (silence/noise) lock_frac, max_conf:")
    for name, probe, lf, mc in dh.false_lock_rows(ab_baseline, ab_final):
        ab_text_lines.append(f"  {name:8} {probe:8} lock_frac={lf}  max_conf={mc}")
    op = dh.onset_proxy_rows(ab_onset)
    if op:
        ab_text_lines.append(f"onset proxy incumbent: {op['incumbent_pr']}")
        ab_text_lines.append(f"onset proxy v2       : {op['v2_pr']}")
        ab_text_lines.append(f"AGC-clamp survival   : {op['agc']}")
    section(H, 11, "A/B comparison (baseline vs final)", fig=fig, text="\n".join(ab_text_lines))

    # 12 interpretation
    rows = dh.ab_aggregate_rows(ab_baseline, ab_final)
    interp = ["WHAT IMPROVED:"]
    interp += [f"  + {l}: {b:.4f} -> {f:.4f} (+{d:.4f})" for l, b, f, d in rows if d > 0.001]
    interp.append("WHAT REGRESSED / DOWN:")
    interp += [f"  - {l}: {b:.4f} -> {f:.4f} ({d:.4f})" for l, b, f, d in rows if d < -0.001]
    interp += [
        "HOST-OR-DEVICE-UNCERTAIN:",
        "  * All front-end/tempo/beat plots are the MODELLED HOST CEILING (clean onset curve,",
        "    not the device AGC-clamped GDFT novelty).",
        "  * No device AP_STREAM overlaid unless a matched capture is supplied.",
        "  * Harmonic/chord state is a synthetic labelled-fixture A/B, not real-music chords.",
        "NEEDS THE FINAL DEVICE CHECK:",
        "  * On-device AP_STREAM bpm/conf/lock vs this host ceiling on the SAME track.",
        "  * Per-beat phase alignment (AP_STREAM ~1 Hz is too coarse; needs a device beat log).",
        "  * Onset per-band behaviour under the real device broadband AGC clamp.",
    ]
    section(H, 12, "Interpretation", text="\n".join(interp))

    page = ("<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>diagnostics {track_id} {run_mode}</title>"
            "<style>body{font-family:-apple-system,Helvetica,Arial,sans-serif;max-width:1100px;"
            "margin:1.5em auto;padding:0 1em;color:#222} h1{font-size:1.4em} h2{font-size:1.1em;"
            "border-top:1px solid #ddd;padding-top:0.6em;margin-top:1.2em} pre{background:#f6f6f6;"
            "padding:0.6em;border-radius:4px;overflow-x:auto;font-size:12px}</style></head><body>"
            + "".join(H) + "</body></html>")

    out_dir = OUT_BASE / RUN_DIR[run_mode]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"
    out_path.write_text(page, encoding="utf-8")
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--track", default=DEFAULT_TRACK)
    ap.add_argument("--apstream", default=None, help="optional captured [AP] log to overlay")
    ap.add_argument("--run", action="append", default=[], choices=RUN_MODES)
    args = ap.parse_args(argv)
    runs = args.run or RUN_MODES
    for rm in runs:
        path = render_run(args.track, rm, apstream_path=args.apstream)
        size = path.stat().st_size
        print(f"  [{rm:8}] -> {path}  ({size} bytes)")
    print(f"\nRENDERED {len(runs)} HTML file(s) under {OUT_BASE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
