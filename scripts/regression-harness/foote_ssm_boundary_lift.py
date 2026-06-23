#!/usr/bin/env python3
"""Independent Foote SSM / recurrence-novelty boundary-lift back-test (BT-SAL).

Adversarial, from-scratch re-derivation of the structure-feature claim behind RC-4
and V-RC4. Does NOT reuse V-RC4's (deleted) scripts. The ONLY shared dependency is
the corpus + the GT segment loader; the Foote self-similarity-matrix novelty and the
boundary-lift / boundary-recall logic are implemented here independently.

Three independent structure features computed at the fork's own framing
(12.8 kHz, HOP=96 -> 133.33 Hz, NFFT=512, Hanning), then evaluated against
HarmonixSet segment boundaries with the SAME boundary-lift semantics the committed
benchmark uses (mean feature in music frames within +/-W of a boundary / mean
elsewhere, silence excluded):

  1. foote_ssm_novelty   : Foote (2000) checkerboard-kernel novelty over a cosine
                           self-similarity matrix of pooled MFCC frames. THE standard
                           structure feature. Computed at multiple pooling resolutions
                           because Foote is a SLOW feature and pooling resolution is the
                           single most load-bearing knob (RC-4's whole point).
  2. mfcc_delta          : ||d MFCC|| per frame (instantaneous timbral change).
  3. recurrence_novelty  : |d (lag-novelty)| from a thresholded recurrence matrix.

Also a DECISIVE boundary-detection check (not just lift): peak-pick the Foote novelty
and recall GT boundaries at +-3 s, vs a random-peak chance baseline (same peak count).

Outputs JSON to stdout. Host-only, no firmware, no device.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wavfile

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "Lightwave-Ledstrip/firmware-v3/test/music_corpus/harmonixset/esv11_benchmark/audio_12k8"
DEFAULT_GT = Path("/Users/spectrasynq/Workspace_Management/Software/K1.reinvented/Implementation.plans/harmonixset-main/dataset")

SAMPLE_RATE = 12800
HOP = 96
NFFT = 512
N_MEL = 40
N_MFCC = 13
FRAME_RATE = SAMPLE_RATE / HOP  # 133.33 Hz


# ----------------------------- feature front-end -----------------------------

def _to_mono_float(data):
    x = data.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if np.issubdtype(data.dtype, np.integer):
        x /= float(np.iinfo(data.dtype).max)
    return x


def _mel_filterbank(sr, nfft, n_mel, fmin=20.0, fmax=None):
    if fmax is None:
        fmax = sr / 2.0
    def hz2mel(f):
        return 2595.0 * np.log10(1.0 + f / 700.0)
    def mel2hz(m):
        return 700.0 * (10.0 ** (m / 2595.0) - 1.0)
    mels = np.linspace(hz2mel(fmin), hz2mel(fmax), n_mel + 2)
    hzs = mel2hz(mels)
    bins = np.floor((nfft + 1) * hzs / sr).astype(int)
    fb = np.zeros((n_mel, nfft // 2 + 1))
    for i in range(1, n_mel + 1):
        l, c, r = bins[i - 1], bins[i], bins[i + 1]
        if c == l:
            c = l + 1
        if r == c:
            r = c + 1
        for k in range(l, c):
            if 0 <= k < fb.shape[1] and c != l:
                fb[i - 1, k] = (k - l) / (c - l)
        for k in range(c, r):
            if 0 <= k < fb.shape[1] and r != c:
                fb[i - 1, k] = (r - k) / (r - c)
    return fb


def _dct_matrix(n_mfcc, n_mel):
    n = np.arange(n_mel)
    k = np.arange(n_mfcc).reshape(-1, 1)
    return np.cos(np.pi * k * (2 * n + 1) / (2 * n_mel)) * np.sqrt(2.0 / n_mel)


_MEL_FB = _mel_filterbank(SAMPLE_RATE, NFFT, N_MEL)
_DCT = _dct_matrix(N_MFCC, N_MEL)


def wav_to_mfcc_and_silence(path):
    """Return (frame_ms, mfcc[nframes, N_MFCC], silence[nframes]) at the fork framing.

    Silence computed identically to novelty_from_wav (RMS < max(0.005, 0.05*median))
    so silence exclusion matches the committed benchmark exactly.
    """
    sr, data = wavfile.read(str(path))
    if sr != SAMPLE_RATE:
        raise ValueError(f"{path}: sr {sr} != {SAMPLE_RATE}")
    x = _to_mono_float(data)
    n = x.shape[0]
    if n < NFFT:
        raise ValueError(f"{path}: too short")
    nframes = 1 + (n - NFFT) // HOP
    starts = np.arange(nframes) * HOP
    frames = np.lib.stride_tricks.sliding_window_view(x, NFFT)[starts]
    win = np.hanning(NFFT)
    mag = np.abs(np.fft.rfft(frames * win, axis=1))
    power = mag ** 2
    melspec = power @ _MEL_FB.T              # [nframes, N_MEL]
    logmel = np.log(np.maximum(melspec, 1e-10))
    mfcc = logmel @ _DCT.T                    # [nframes, N_MFCC]
    rms = np.sqrt((frames ** 2).mean(axis=1))
    med = float(np.median(rms))
    floor = max(0.005, 0.05 * med)
    silence = (rms < floor).astype(np.int8)
    frame_ms = np.round(starts * 1000.0 / SAMPLE_RATE).astype(np.int64)
    return frame_ms, mfcc, silence


# ----------------------------- structure features -----------------------------

def _pool(mfcc, pool):
    """Mean-pool MFCC frames by `pool` (>=1). Returns pooled features and the
    pooled->original frame stride (for mapping novelty back to ms)."""
    if pool <= 1:
        return mfcc, 1
    nb = mfcc.shape[0] // pool
    if nb < 4:
        return mfcc, 1
    pooled = mfcc[: nb * pool].reshape(nb, pool, mfcc.shape[1]).mean(axis=1)
    return pooled, pool


def foote_novelty_from_mfcc(mfcc, pool, kernel_pooled):
    """Standard Foote (2000) checkerboard-kernel novelty.

    1. mean-pool MFCC to a slower resolution (Foote is a slow feature),
    2. cosine self-similarity matrix S,
    3. correlate a Gaussian-tapered checkerboard kernel along the diagonal,
    4. up-sample novelty back to per-frame (133 Hz) by repetition for lift scoring.

    Returns per-(original)-frame novelty array, length == mfcc.shape[0] (truncated to
    the pooled coverage; tail padded with the last value).
    """
    pooled, stride = _pool(mfcc, pool)
    P = pooled.shape[0]
    if P < 2 * kernel_pooled + 2:
        return np.zeros(mfcc.shape[0])
    # cosine self-similarity
    norm = np.linalg.norm(pooled, axis=1, keepdims=True)
    norm = np.where(norm < 1e-9, 1e-9, norm)
    U = pooled / norm
    S = U @ U.T                               # [P, P] in [-1, 1]
    # checkerboard kernel, Gaussian-tapered (Foote/Cooper-Foote)
    L = kernel_pooled
    coords = np.arange(-L, L + 1)
    sign = np.sign(np.outer(coords, coords))  # +1 same-quadrant, -1 cross-quadrant
    g = np.exp(-0.5 * (np.outer(coords, coords ** 0) ** 2 + np.outer(coords ** 0, coords) ** 2) / (L / 2.0) ** 2)
    kernel = sign * g
    nov = np.zeros(P)
    for i in range(L, P - L):
        block = S[i - L:i + L + 1, i - L:i + L + 1]
        nov[i] = float((block * kernel).sum())
    nov = np.maximum(nov, 0.0)               # novelty peaks (boundaries) are positive
    # up-sample to per-frame
    per = np.repeat(nov, stride)
    if per.shape[0] < mfcc.shape[0]:
        per = np.concatenate([per, np.full(mfcc.shape[0] - per.shape[0], per[-1] if per.size else 0.0)])
    else:
        per = per[: mfcc.shape[0]]
    return per


def recurrence_novelty_from_mfcc(mfcc, pool, k_neighbours=5):
    """Recurrence-matrix novelty: pooled cosine recurrence, row-novelty = change in the
    lag profile between consecutive pooled frames. Up-sampled to per-frame."""
    pooled, stride = _pool(mfcc, pool)
    P = pooled.shape[0]
    if P < 8:
        return np.zeros(mfcc.shape[0])
    norm = np.linalg.norm(pooled, axis=1, keepdims=True)
    norm = np.where(norm < 1e-9, 1e-9, norm)
    U = pooled / norm
    S = U @ U.T
    # binarise recurrence: top-k per row
    R = np.zeros_like(S)
    for i in range(P):
        idx = np.argsort(S[i])[-k_neighbours:]
        R[i, idx] = 1.0
    # novelty = L1 change of the recurrence row between consecutive frames
    dR = np.abs(np.diff(R, axis=0, prepend=R[:1])).sum(axis=1)
    per = np.repeat(dR, stride)
    if per.shape[0] < mfcc.shape[0]:
        per = np.concatenate([per, np.full(mfcc.shape[0] - per.shape[0], per[-1] if per.size else 0.0)])
    else:
        per = per[: mfcc.shape[0]]
    return per


def mfcc_delta(mfcc):
    return np.abs(np.diff(mfcc, axis=0, prepend=mfcc[:1])).sum(axis=1)


# ----------------------------- GT + scoring -----------------------------

def load_segments(gt_dir):
    """yt_id -> segment boundary times (ms). Mirrors the benchmark's loader exactly."""
    gt_dir = Path(gt_dir)
    yt2key = {}
    with open(gt_dir / "index.jsonl", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("youtube_id") and row.get("file_key"):
                yt2key[row["youtube_id"]] = row["file_key"]
    out = {}
    for yt, key in yt2key.items():
        seg_file = gt_dir / "segments" / f"{key}.txt"
        if not seg_file.exists():
            continue
        segs = []
        with open(seg_file, encoding="utf-8") as fh:
            for line in fh:
                parts = line.strip().split()
                if not parts:
                    continue
                try:
                    segs.append(float(parts[0]) * 1000.0)
                except ValueError:
                    continue
        if segs:
            out[yt] = segs
    return out


def boundary_lift_sums(frame_ms, feature, silence, segs_ms, win_ms):
    """IDENTICAL semantics to musical_saliency_benchmark._boundary_lift_sums:
    near = frames within +/-win of any boundary; silence excluded; pooled lift =
    mean(near)/mean(far). Returns (near_sum, near_n, far_sum, far_n)."""
    import bisect
    if not len(frame_ms) or not segs_ms:
        return 0.0, 0, 0.0, 0
    segs = sorted(segs_ms)
    ns = nn = 0
    fs_ = fn = 0
    ns_f = 0.0
    fs_f = 0.0
    for i in range(len(frame_ms)):
        if silence[i]:
            continue
        ms = int(frame_ms[i])
        idx = bisect.bisect_left(segs, ms)
        near = False
        for ci in (idx - 1, idx):
            if 0 <= ci < len(segs) and abs(segs[ci] - ms) <= win_ms:
                near = True
                break
        if near:
            ns_f += float(feature[i])
            nn += 1
        else:
            fs_f += float(feature[i])
            fn += 1
    return ns_f, nn, fs_f, fn


def peak_pick(novelty, frame_ms, silence, min_sep_ms=3000):
    """Local maxima of novelty (music frames), with a minimum separation, sorted by
    height. Returns list of peak times (ms). Mirrors textbook structure-boundary
    peak-picking."""
    nov = novelty.copy()
    nov[silence.astype(bool)] = -np.inf
    n = nov.shape[0]
    cand = []
    for i in range(1, n - 1):
        if nov[i] > nov[i - 1] and nov[i] >= nov[i + 1] and np.isfinite(nov[i]) and nov[i] > 0:
            cand.append((nov[i], int(frame_ms[i])))
    cand.sort(reverse=True)
    chosen = []
    for _, t in cand:
        if all(abs(t - c) >= min_sep_ms for c in chosen):
            chosen.append(t)
    return sorted(chosen)


def recall_boundaries(peaks_ms, segs_ms, tol_ms=3000):
    if not peaks_ms or not segs_ms:
        return 0, len(segs_ms)
    hit = 0
    for b in segs_ms:
        if any(abs(b - p) <= tol_ms for p in peaks_ms):
            hit += 1
    return hit, len(segs_ms)


def random_peak_chance(n_peaks, duration_ms, segs_ms, tol_ms=3000, trials=200, rng=None):
    if rng is None:
        rng = np.random.default_rng(12345)
    if n_peaks == 0 or not segs_ms:
        return 0.0
    recalls = []
    for _ in range(trials):
        pk = rng.uniform(0, duration_ms, size=n_peaks)
        hit = sum(1 for b in segs_ms if np.any(np.abs(b - pk) <= tol_ms))
        recalls.append(hit / len(segs_ms))
    return float(np.mean(recalls))


# ----------------------------- driver -----------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    ap.add_argument("--gt", default=str(DEFAULT_GT))
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)

    segs_by_yt = load_segments(args.gt)
    wavs = sorted(Path(args.corpus).glob("*.wav"))
    if args.limit:
        wavs = wavs[: args.limit]

    # pooling resolutions (in original 133 Hz frames): ~0.5 s, ~1 s, ~2 s.
    pools = {"0.5s": int(round(0.5 * FRAME_RATE)),
             "1.0s": int(round(1.0 * FRAME_RATE)),
             "2.0s": int(round(2.0 * FRAME_RATE))}
    # kernel half-width scaled DOWN for coarse pools so short clips still yield a
    # valid Foote matrix (P >= 2L+2). 0.5s/1.0s keep L=8; 2.0s drops to L=4.
    pool_kernel = {"0.5s": 8, "1.0s": 8, "2.0s": 4}
    kernel_pooled = 8  # default checkerboard half-width in pooled frames
    windows = {"250ms": 250, "1500ms": 1500, "3000ms": 3000}

    feat_keys = []
    for p in pools:
        feat_keys.append(f"foote_{p}")
    feat_keys += ["recurrence_1.0s", "mfcc_delta"]

    sums = {fk: {w: [0.0, 0, 0.0, 0] for w in windows} for fk in feat_keys}
    foote_peak_hits = 0
    foote_peak_total = 0
    chance_hits_frac = []
    n_scored = 0

    for wav in wavs:
        yt = wav.stem.replace("_12k8", "")
        segs = segs_by_yt.get(yt)
        if not segs:
            continue
        frame_ms, mfcc, silence = wav_to_mfcc_and_silence(wav)
        if mfcc.shape[0] < 100:
            continue
        n_scored += 1

        feats = {}
        for label, p in pools.items():
            feats[f"foote_{label}"] = foote_novelty_from_mfcc(mfcc, p, pool_kernel[label])
        feats["recurrence_1.0s"] = recurrence_novelty_from_mfcc(mfcc, pools["1.0s"])
        feats["mfcc_delta"] = mfcc_delta(mfcc)

        for fk, fv in feats.items():
            for wlabel, wms in windows.items():
                ns, nn, fs_, fn = boundary_lift_sums(frame_ms, fv, silence, segs, wms)
                acc = sums[fk][wlabel]
                acc[0] += ns; acc[1] += nn; acc[2] += fs_; acc[3] += fn

        # decisive: Foote @1s peak boundary recall vs chance
        foote = feats["foote_1.0s"]
        peaks = peak_pick(foote, frame_ms, silence, min_sep_ms=3000)
        h, tot = recall_boundaries(peaks, segs, tol_ms=3000)
        foote_peak_hits += h
        foote_peak_total += tot
        dur = float(frame_ms[-1]) if len(frame_ms) else 0.0
        chance_hits_frac.append(random_peak_chance(len(peaks), dur, segs, tol_ms=3000))

    lift_table = {}
    for fk in feat_keys:
        lift_table[fk] = {}
        for w in windows:
            ns, nn, fs_, fn = sums[fk][w]
            nm = ns / nn if nn else 0.0
            fm = fs_ / fn if fn else 0.0
            lift_table[fk][w] = round((nm / fm) if fm > 0 else 0.0, 4)

    result = {
        "n_tracks_scored": n_scored,
        "boundary_lift": lift_table,
        "foote_peak_recall": round(foote_peak_hits / foote_peak_total, 4) if foote_peak_total else 0.0,
        "foote_peak_hits": foote_peak_hits,
        "foote_peak_total": foote_peak_total,
        "random_peak_chance": round(float(np.mean(chance_hits_frac)), 4) if chance_hits_frac else 0.0,
        "params": {
            "frame_rate_hz": round(FRAME_RATE, 3),
            "pools_frames": pools,
            "kernel_pooled_halfwidth": kernel_pooled,
            "n_mfcc": N_MFCC,
            "peak_min_sep_ms": 3000,
            "recall_tol_ms": 3000,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
