"""Colour against energy in a captured run: per edge, summed-RGB hue against the
luma-weighted distance of light from the strip centre (Waveform Hybrid shows energy as position).
usage: colour_diag.py <case>/uart.txt"""
import sys, colorsys, numpy as np
def load(path):
    rows=[]
    for line in open(path, errors='replace'):
        if line.startswith('F,'):
            p=line.rstrip().split(',')
            e=[]
            for h in (p[4],p[5]):
                a=np.frombuffer(bytes.fromhex(h),dtype='>u2').reshape(-1,3).astype(float)/65535.0
                e.append(a)
            rows.append(e)
    return rows
rows=load(sys.argv[1])
for edge in (0,1):
    hue=[];pos=[];lum=[]
    for fr in rows:
        a=fr[edge]; s=a.sum(axis=0); l=a.sum(axis=1)
        if l.sum()<1e-4: continue
        idx=np.arange(len(a)); centre=(len(a)-1)/2
        pos.append((np.abs(idx-centre)*l).sum()/l.sum()/centre)
        m=s.max()
        hue.append(colorsys.rgb_to_hsv(*(s/m))[0]); lum.append(l.sum())
    hue=np.array(hue); pos=np.array(pos)
    # circular-safe: report on unit circle spread
    ang=hue*2*np.pi; R=np.hypot(np.cos(ang).mean(),np.sin(ang).mean())
    huedeg=hue*360
    lo,hi=np.percentile(huedeg,[2,98])
    r=np.corrcoef(pos,huedeg)[0,1] if (hi-lo)<180 else float('nan')
    print(f"edge {'AB'[edge]}: lit frames {len(hue)}/{len(rows)}; hue 2-98 pct {lo:.1f}..{hi:.1f} deg (span {hi-lo:.1f}); circular R {R:.3f}; distinct hues(1deg) {len(set(np.round(huedeg)))}; r(position,hue) {r:.3f}; position 2-98 pct {np.percentile(pos,2):.2f}..{np.percentile(pos,98):.2f}")
