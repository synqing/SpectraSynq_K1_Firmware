"""Brightest-pixel hue statistics per edge. usage: colour_diag_brightest.py <case>/uart.txt"""
import sys, colorsys, numpy as np
def load(path):
    rows=[]
    for line in open(path, errors='replace'):
        if line.startswith('F,'):
            p=line.rstrip().split(',')
            rows.append([np.frombuffer(bytes.fromhex(h),dtype='>u2').reshape(-1,3).astype(float)/65535.0 for h in (p[4],p[5])])
    return rows
rows=load(sys.argv[1])
for edge in (0,1):
    hd=[];br=[]
    for fr in rows:
        a=fr[edge]; i=a.sum(axis=1).argmax(); px=a[i]
        if px.max()<1e-3: continue
        hd.append(colorsys.rgb_to_hsv(*(px/px.max()))[0]*360); br.append(px.max())
    hd=np.array(hd); br=np.array(br); ang=np.deg2rad(hd)
    mean=np.rad2deg(np.arctan2(np.sin(ang).mean(),np.cos(ang).mean()))%360
    dev=((hd-mean+180)%360)-180
    print(f"edge {'AB'[edge]} brightest pixel: circular mean hue {mean:.1f} deg, deviation 2-98 pct {np.percentile(dev,2):.1f}..{np.percentile(dev,98):.1f} deg, r(brightness,hue deviation) {np.corrcoef(br,dev)[0,1]:.3f}, peak level 2-98 pct {np.percentile(br,2):.3f}..{np.percentile(br,98):.3f}")
