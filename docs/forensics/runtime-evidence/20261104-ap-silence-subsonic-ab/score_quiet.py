#!/usr/bin/env python3
"""Score [AP] lines of a quiet-room capture: how often the show is driven loud.
usage: score_quiet.py LOG [LOG ...]. Skips the first SKIP lines (boot settle) in a 2nd row."""
import re, sys, statistics as st
def rows(fn):
    out = []
    for line in open(fn, "rb").read().decode("latin1").splitlines():
        if not line.startswith("[AP]"): continue
        d = {k: float(v) for k, v in re.findall(r"(?<![a-z_])(SSL|max_raw|peak_scaled|silence|agc_gain|onset|raw_i16_rms)=(-?[\d.]+)", line)}
        if "peak_scaled" in d: out.append(d)
    return out
for fn in sys.argv[1:]:
    r = rows(fn)
    b = re.search(rb"BUILD: [^\r\n]*", open(fn, "rb").read())
    print(fn.rsplit("/", 1)[-1], "|", b.group(0).decode() if b else "no BUILD line", "| SSL", r[-1].get("SSL") if r else "?")
    for label, seg in (("all", r), ("after 40 s", r[40:])):
        if not seg: continue
        ps = [d["peak_scaled"] for d in seg]
        print(f"  {label:10s} n={len(seg):3d} peak_scaled median={st.median(ps):.3f} max={max(ps):.3f} "
              f">=0.5 in {sum(p>=0.5 for p in ps)} lines | silence=1 in {sum(d.get('silence',0)==1 for d in seg)} "
              f"| onsets {sum(d.get('onset',0)==1 for d in seg)} | agc_gain median {st.median(d.get('agc_gain',0) for d in seg):.2f} "
              f"| raw rms median {st.median(d.get('raw_i16_rms',0) for d in seg):.1f}")
