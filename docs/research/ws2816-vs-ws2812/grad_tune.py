#!/usr/bin/env python3
"""Artefact-boundary verification for the WS2816 8-bit-vs-16-bit COLOUR-DEPTH
gradient test patterns. Replicates the EXACT device packer math and reports, per
candidate pattern, whether 8-bit posterizes (visible plateaus) while 16-bit stays
smooth — BEFORE anything is flashed to the Captain's eye.

Device math replicated (led_utilities.h):
  SQ15x16 store  : v_q = trunc(clamp(x,0,1) * 65536) / 65536   (FixedPoints ctor trunc)
  16-bit wire    : w16 = round(v_q * 65535)                    (k1_ws2816_to16)
  8-bit  wire    : v8  = trunc(v_q * 255) ; w = v8 * 257        (map8_to_16, dither OFF)
  8-bit dithered : decimal=v_q*254; whole=trunc; +1 if frac>=dither_table[(p+i)%4]
                   dither_table = {0.25,0.50,0.75,1.00}, 4-frame average
LGP note: plateau >= ~5-6 px survives the light-guide diffusion; that is the bar.
"""
COUNT = 160
DITHER = [0.25, 0.50, 0.75, 1.00]


def sq(x):
    x = 0.0 if x < 0 else (1.0 if x > 1 else x)
    return int(x * 65536) / 65536.0            # SQ15x16 truncation


def w16(v):                                    # 16-bit packer
    return int(sq(v) * 65535.0 + 0.5)


def w8(v):                                     # 8-bit packer, dither OFF (map8_to_16)
    return int(sq(v) * 255.0)                  # uint8_t cast truncates; *257 is monotone in v8


def dith8_levels(vs):
    """Effective distinct levels the eye integrates with 4-frame dither ON."""
    seen = set()
    for i, v in enumerate(vs):
        acc = 0
        for p in range(4):
            dec = sq(v) * 254.0
            whole = int(dec)
            frac = dec - whole
            if frac >= DITHER[(p + i) % 4]:
                whole += 1
            acc += whole
        seen.add(round(acc / 4.0, 3))          # time-averaged level
    return len(seen)


def metrics(vs):
    c8 = [w8(v) for v in vs]
    c16 = [w16(v) for v in vs]
    # plateau = longest run of identical 8-bit codes
    run = best = 1
    for k in range(1, len(c8)):
        run = run + 1 if c8[k] == c8[k - 1] else 1
        best = max(best, run)
    return {
        "d8": len(set(c8)), "plateau8": best, "d16": len(set(c16)),
        "d8_dith": dith8_levels(vs),
    }


def frac(i):
    return i / (COUNT - 1)


# ── candidate patterns: (name, per-channel funcs r,g,b of f) ──────────────────
def const(c):
    return lambda f: c


LO, MD = 0.08, 0.12
PATTERNS = [
    ("2 grad-grey  (blk->%.0f%% neutral)" % (LO*100),   lambda f: LO*f,        lambda f: LO*f,        lambda f: LO*f),
    ("3 grad-blue  (blk->%.0f%% blue)"    % (LO*100),   const(0),              const(0),              lambda f: LO*f),
    ("4 grad-red   (blk->%.0f%% red)"     % (MD*100),   lambda f: MD*f,        const(0),              const(0)),
    ("5 grad-amber (blk->dim amber)",                    lambda f: MD*f,        lambda f: 0.40*MD*f,   const(0)),
    ("6 grad-blend (dim teal<->magenta)",                lambda f: LO*f,        lambda f: LO*(1-f),    const(LO)),
    ("7 grad-perc-blue (blk->%.0f%% b, f^2.2)" % (MD*100), const(0),           const(0),              lambda f: MD*(f**2.2)),
    ("8 grad-mid   (42%%->54%% neutral)",                lambda f: 0.42+0.12*f, lambda f: 0.42+0.12*f, lambda f: 0.42+0.12*f),
    ("9 grad-warm  (blk->dim warm-white)",               lambda f: LO*f,        lambda f: 0.85*LO*f,   lambda f: 0.60*LO*f),
    ("10 grad-full (blk->white CONTROL)",                lambda f: f,           lambda f: f,           lambda f: f),
]

print(f"{'pattern':40s} {'chan':4s} {'d8':>4s} {'plat8':>6s} {'d16':>5s} {'d8+dith':>8s}  verdict")
print("-" * 92)
for name, rf, gf, bf in PATTERNS:
    fs = [frac(i) for i in range(COUNT)]
    ch = {}
    for cn, fn in (("R", rf), ("G", gf), ("B", bf)):
        vs = [fn(f) for f in fs]
        if max(vs) <= 0:      # dead channel, skip
            continue
        ch[cn] = metrics(vs)
    # verdict on the channel with the widest plateau (the visible banding)
    lead = max(ch.values(), key=lambda m: m["plateau8"])
    control = name.startswith("10")
    ok = (lead["plateau8"] >= 5 and lead["d16"] >= 2 * lead["d8"])
    verdict = ("CONTROL (should NOT band)" if control
               else ("BANDS 8b / smooth 16b  OK" if ok else "WEAK — retune"))
    first = True
    for cn, m in ch.items():
        tag = name if first else ""
        print(f"{tag:40s} {cn:4s} {m['d8']:>4d} {m['plateau8']:>6d} {m['d16']:>5d} {m['d8_dith']:>8d}"
              + (f"  {verdict}" if first else ""))
        first = False
    print()
