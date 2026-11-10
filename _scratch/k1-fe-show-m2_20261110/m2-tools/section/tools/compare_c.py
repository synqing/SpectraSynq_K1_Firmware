#!/usr/bin/env python3
"""(c)/(d) comparison: sectioned Loreen stream vs the prediction declared before the compile.

Usage: compare_c.py <project_dir> <prediction.json> <out_dir>
Reads (read-only) M2's pre-edit and whole-track post-edit streams. Writes diff_table.md,
compare_c.json and impact_sectioned.png into out_dir. Exit 1 on any mismatch.
"""
import hashlib, json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

proj, pred_path, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
M2 = Path("/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-compose/projects/loreen/stream")
FRAME, HZ, IMP = 34, 120, 20  # prim8[1] at bytes 20..21 (little-endian u16)

pred = json.loads(pred_path.read_text())
pre = (M2 / "loreen_pre_edit_120hz.prsm").read_bytes()
post = (M2 / "loreen_post_edit_120hz.prsm").read_bytes()
sec = (proj / "out/sectioned/stream_120hz.prsm").read_bytes()
n = len(sec) // FRAME
t0, t1 = pred["span_us"]
tick = lambda i: (i * 1_000_000 + HZ // 2) // HZ
fr = lambda b, i: b[i * FRAME:(i + 1) * FRAME]
imp = lambda b, i: int.from_bytes(fr(b, i)[IMP:IMP + 2], "little")

fails = []
changed, byte_pos = [], set()
for i in range(n):
    a, s = fr(pre, i), fr(sec, i)
    if a != s:
        changed.append(i)
        byte_pos |= {k for k in range(FRAME) if a[k] != s[k]}
    want = fr(post, i) if t0 <= tick(i) < t1 else a
    if s != want:
        fails.append(f"frame {i} t={tick(i)} != predicted source")
if len(sec) != len(pre):
    fails.append("length differs")
if changed != pred["P2_changed_frames"]:
    fails.append(f"changed set {len(changed)} != predicted {len(pred['P2_changed_frames'])}")
if not byte_pos <= {IMP, IMP + 1}:
    fails.append(f"bytes outside impact changed: {sorted(byte_pos)}")
sha = hashlib.sha256(sec).hexdigest()
if sha != pred["expected_stream_sha256"]:
    fails.append("stream sha != predicted")

# Intent Trace: rows in the span carry section chorus_1; every other row equals the pre-edit row text.
pre_tr = (proj / "out/pre_edit/trace_120hz.jsonl").read_text().splitlines()
sec_tr = (proj / "out/sectioned/trace_120hz.jsonl").read_text().splitlines()
tr_in = tr_out_same = 0
for a, s in zip(pre_tr, sec_tr):
    r = json.loads(s)
    if t0 <= r["t_us"] < t1:
        if r.get("section") != "chorus_1":
            fails.append(f"trace row t={r['t_us']} lacks section")
        tr_in += 1
    else:
        if a != s:
            fails.append(f"trace row t={r['t_us']} outside the span differs from pre-edit")
        tr_out_same += 1
if len(pre_tr) != len(sec_tr):
    fails.append("trace length differs")

# (d) reopen -> recompile is byte-identical
reopen = {}
for f in ["showbundle.json", "trace_120hz.jsonl", "stream_120hz.prsm", "mapping_coverage.json", "compile_manifest.json"]:
    a, b = (proj / "out/sectioned" / f).read_bytes(), (proj / "out/reopen" / f).read_bytes()
    reopen[f] = {"identical": a == b, "sha256": hashlib.sha256(b).hexdigest()}
    if a != b:
        fails.append(f"reopen {f} differs")

# Windows: group consecutive changed frames.
wins = []
for i in changed:
    if wins and i == wins[-1][-1] + 1:
        wins[-1].append(i)
    else:
        wins.append([i])
rows = ["| # | frames | t (s) | impact pre (48000 accent) | impact sectioned | whole-track edit | = whole-track |",
        "|---|---|---|---|---|---|---|"]
for k, w in enumerate(wins, 1):
    rows.append(f"| {k} | {w[0]}–{w[-1]} ({len(w)}) | {tick(w[0])/1e6:.3f}–{tick(w[-1])/1e6:.3f} | "
                f"{', '.join(str(imp(pre, i)) for i in w)} | {', '.join(str(imp(sec, i)) for i in w)} | "
                f"{', '.join(str(imp(post, i)) for i in w)} | {'yes' if all(fr(sec, i) == fr(post, i) for i in w) else 'NO'} |")
in_span = sum(1 for i in range(n) if t0 <= tick(i) < t1)
post_changed_outside = sum(1 for i in range(n) if not (t0 <= tick(i) < t1) and fr(pre, i) != fr(post, i))
summary = {
    "frames": n, "frames_in_span": in_span, "changed_vs_pre": len(changed), "predicted_changed": len(pred["P2_changed_frames"]),
    "changed_equals_prediction": changed == pred["P2_changed_frames"], "changed_byte_positions": sorted(byte_pos),
    "unchanged_vs_pre": n - len(changed), "whole_track_edit_changes_outside_span_left_unchanged": post_changed_outside,
    "stream_sha256": sha, "predicted_stream_sha256": pred["expected_stream_sha256"],
    "trace_rows_in_span_with_section": tr_in, "trace_rows_outside_identical_to_pre": tr_out_same,
    "reopen": reopen, "windows": len(wins), "fails": fails[:20], "verdict": "MATCH" if not fails else "MISMATCH",
}
(out / "compare_c.json").write_text(json.dumps(summary, indent=1) + "\n")
(out / "diff_table.md").write_text(
    f"# Frame-level diff: sectioned stream vs pre-edit (verdict {summary['verdict']})\n\n"
    f"Section chorus_1 = segment 4 [{t0}, {t1}) µs. {len(changed)} frames changed in {len(wins)} windows, "
    f"only bytes {sorted(byte_pos)} (impact). {n - len(changed)} frames byte-identical to pre-edit. "
    f"The whole-track edit's {post_changed_outside} changed frames outside the span stay at their pre-edit bytes.\n\n" + "\n".join(rows) + "\n")

# Plot: impact, 40-66 s, plus a zoom; whole-track change markers.
ts = [tick(i) / 1e6 for i in range(n)]
fig, ax = plt.subplots(3, 1, figsize=(13, 9.5), gridspec_kw={"height_ratios": [1.2, 1.2, 0.7]})
lo, hi = int(40e6 * HZ / 1e6), int(66e6 * HZ / 1e6)
for a_, (l_, h_) in zip(ax[:2], [(lo, hi), (int(45.0 * HZ), int(49.0 * HZ))]):
    xs = ts[l_:h_]
    a_.axvspan(t0 / 1e6, t1 / 1e6, color="#f4d58d", alpha=0.35, label="section chorus_1 (segment 4)")
    a_.plot(xs, [imp(pre, i) for i in range(l_, h_)], color="#888", lw=2.2, label="pre-edit (top level, beat 48000)")
    a_.plot(xs, [imp(post, i) for i in range(l_, h_)], color="#4a7fd0", lw=0.9, ls="--", label="whole-track edit (M2, beat 12000)")
    a_.plot(xs, [imp(sec, i) for i in range(l_, h_)], color="#c0392b", lw=1.1, label="sectioned (this build)")
    a_.set_xlim(xs[0], xs[-1])
    a_.set_ylabel("impact u16")
    a_.legend(loc="upper right", fontsize=8)
ax[0].set_title("Loreen impact channel: the bar-accent edit applied to the first chorus only")
ax[1].set_title("zoom 45-49 s: section boundary at 45.68 s")
changed_t = [tick(i) / 1e6 for i in changed]
post_t = [tick(i) / 1e6 for i in range(n) if fr(pre, i) != fr(post, i)]
ax[2].eventplot([post_t, changed_t], colors=["#4a7fd0", "#c0392b"], lineoffsets=[1, 0], linelengths=0.8)
ax[2].set_yticks([0, 1], ["sectioned build", "whole-track edit"])
ax[2].axvspan(t0 / 1e6, t1 / 1e6, color="#f4d58d", alpha=0.35)
ax[2].set_xlabel("time (s), whole track: frames that differ from pre-edit")
fig.tight_layout()
fig.savefig(out / "impact_sectioned.png", dpi=110)
print(json.dumps({k: v for k, v in summary.items() if k != "reopen"}, indent=1))
print(json.dumps(reopen, indent=1))
sys.exit(1 if fails else 0)
