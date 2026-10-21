#!/usr/bin/env python3
"""Joint tempo-and-phase state estimator, HOST-ONLY prototype (lane R1 Phase 2.6, DEF-002).

No firmware change. Reads the shared captured tempo input (I7: emulator N lines, fixture index made
by tempo_lane_replay.py extract) and writes trajectories in the frozen scorer's format, so
tempo_lane_scorer.py judges it exactly like the tracker.

Model (a discrete Bayesian "bar pointer" forward filter, after Whiteley/Cemgil/Godsill 2006 and
Krebs/Boeck/Widmer 2015, reduced to one beat per cycle):
  state      (tempo bin i, beat phase bin j): 96 tempi 60..155 BPM (the tracker's grid) x NPHASE bins
  advance    every emit the phase of tempo i moves bpm_i/60 * dt beats (fractional, two-tap shift)
  tempo      per emit a random walk to the neighbouring bins with probability EPS each (no jumps,
             so a 3:2 move is never a transition; it has to win on evidence)
  evidence   o = rank of the emit's novelty among the last RANK_WIN emits (0..1), so the model is
             invariant to any monotonic transform of the input (M2 by construction). Beat states
             (phase within +-1/LAMBDA of the beat) score o^KAPPA, the rest (1 - o^KAPPA)/(LAMBDA-1).
  silence    producer silence (I9) is an emit with no evidence (flat likelihood), nothing more.
Emits follow the tracker's own schedule (prime on the first frame, peak-hold, every 3rd AP frame).

Per emit it publishes the arg-max tempo of the phase-marginal posterior and three correctness
candidates read off the same posterior:
  mass     posterior mass within +-2 bins of the arg-max tempo (concentration)
  ratio32  arg-max mass / the larger of the masses at 2/3 and 3/2 of it (in range; 3:2 margin)
  phase    peak of the phase distribution at the arg-max tempo x NPHASE (1 = uniform; phase certainty)

  tempo_joint_estimator.py run --fixtures IDX [--fixtures IDX2] --out TRAJ.json [--kappa K ...]
  tempo_joint_estimator.py auc --manifest M --traj TRAJ.json [--tracker-traj T.json] [--out R.json]
     AUC of each per-track candidate (mean over the scored window) for CORRECT vs WRONG, on the
     estimator's own choices and, with --tracker-traj, as a correctness term for the tracker's choices.
  tempo_joint_estimator.py gate --tracker-traj T.json --estimator-traj E.json --out G.json [--hold-s D]
     the tracker's published lock kept only on emits where its BPM agrees with the estimator's, and with
     --hold-s only after lock and agreement have held continuously for D seconds (experiment E1).
Host cost: tempo_joint_pointer_bench.c (same state space in C, window weights quantised to 1/16).

Two state spaces are kept for the record. `--model pointer` (default) is the measured one. `--model emit`
(fractional phase shift at the 44.4 Hz emit rate) is the first attempt: its linear-interpolation shift
blurs phase more per beat at slow tempi, which made slow hypotheses more forgiving and pulled most
clips to 60-75 BPM (dev Acc2 9/36). Use it only to reproduce that finding (pass --rank-win 512).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import tempo_lane_replay as tlr  # noqa: E402
import tempo_lane_scorer as tls  # noqa: E402

NUM_TEMPI, TEMPO_LOW = 96, 60.0
AP_HZ, DECIM = 12800.0 / 96.0, 3
EMIT_DT = DECIM / AP_HZ                       # 0.0225 s, the tracker's emit period
DEFAULTS = {"model": "pointer", "nphase": 64, "lam": 16.0, "kappa": 4.0, "eps": 0.004, "rank_win": 1536,
            "floor": 1e-3, "tempo_q": 0.02, "prior_sigma": 0.0, "input": "novelty"}


def emits_of(rows):
    """Tracker emit schedule on the captured per-AP-frame input: (gen of the emit, peak-held novelty,
    window all-silent)."""
    out, primed, acc, ctr, all_sil = [], False, 0.0, 0, True
    for r in rows:
        gen, nov, sil = r[0], r[1], r[2]
        nov = 0.0 if sil else min(max(nov, 0.0), 1.0)
        all_sil = all_sil and bool(sil)
        if not primed:
            primed, acc, ctr = True, nov, 0
            continue
        acc = max(acc, nov)
        ctr += 1
        if ctr < DECIM:
            continue
        out.append((gen, acc, all_sil))
        acc, ctr, all_sil = 0.0, 0, True
    return out


class JointFilter:
    def __init__(self, nphase=64, lam=16.0, kappa=4.0, eps=0.004, rank_win=512, floor=1e-3):
        self.N, self.lam, self.kappa, self.eps, self.W, self.floor = nphase, lam, kappa, eps, rank_win, floor
        self.bpm = TEMPO_LOW + np.arange(NUM_TEMPI, dtype=float)
        adv = self.bpm / 60.0 * EMIT_DT * nphase            # phase bins advanced per emit, per tempo
        k = np.floor(adv).astype(int)
        self.f = (adv - k)[:, None]
        j = np.arange(nphase)[None, :]
        self.i0 = (j - k[:, None]) % nphase                  # source index for the integer part
        self.i1 = (j - k[:, None] - 1) % nphase              # and one further (fractional part)
        half = max(1, int(round(nphase / lam / 2.0)))
        ph = np.arange(nphase)
        self.beat = (ph < half) | (ph >= nphase - half)      # beat region centred on phase 0
        self.p = np.full((NUM_TEMPI, nphase), 1.0 / (NUM_TEMPI * nphase))
        self.ring = []
        self.state_updates_per_emit = NUM_TEMPI * nphase * 3  # shift (2 taps) + walk + evidence

    def rank(self, x):
        self.ring.append(x)
        if len(self.ring) > self.W:
            self.ring.pop(0)
        a = np.asarray(self.ring)
        return (np.count_nonzero(a < x) + 0.5 * (np.count_nonzero(a == x) - 1)) / max(1, len(a) - 1)

    def step(self, x, silent):
        p = self.p
        p = (1.0 - self.f) * np.take_along_axis(p, self.i0, 1) + self.f * np.take_along_axis(p, self.i1, 1)
        up, dn = np.empty_like(p), np.empty_like(p)
        up[1:], up[0] = p[:-1], p[0]                       # reflecting edges
        dn[:-1], dn[-1] = p[1:], p[-1]
        p = (1.0 - 2.0 * self.eps) * p + self.eps * (up + dn)
        if not silent:
            o = self.rank(x) ** self.kappa
            lb = max(o, self.floor)
            ln = max((1.0 - o) / (self.lam - 1.0), self.floor)
            p = p * np.where(self.beat, lb, ln)[None, :]
        s = p.sum()
        self.p = p / s if s > 0 else np.full_like(p, 1.0 / p.size)
        return self.read()

    def read(self):
        m = self.p.sum(1)
        w = int(np.argmax(m))
        lo, hi = max(0, w - 2), min(NUM_TEMPI, w + 3)
        mass = float(m[lo:hi].sum())

        def around(b):
            t = int(round(b - TEMPO_LOW))
            if t < 0 or t >= NUM_TEMPI:
                return None
            return float(m[max(0, t - 2):min(NUM_TEMPI, t + 3)].sum())
        rivals = [v for v in (around(self.bpm[w] * 2.0 / 3.0), around(self.bpm[w] * 1.5)) if v is not None]
        ratio32 = mass / max(max(rivals), 1e-12) if rivals else 1e3
        row = self.p[w] / max(self.p[w].sum(), 1e-30)
        return float(self.bpm[w]), mass, float(min(ratio32, 1e3)), float(row.max() * self.N), float(row.argmax()) / self.N


class PointerFilter:
    """Bar pointer with EXACT integer periods at the AP frame rate (Krebs/Boeck/Widmer 2015 state space):
    one state per (period P frames, phase slot). No fractional shift, so no phase diffusion and no bias
    toward slow tempi (the emit-rate fractional model above drifts to 60 BPM for exactly that reason).
    Period P in [round(AP_HZ*60/155), round(AP_HZ*60/60)] = 52..133 frames (153.8..60.2 BPM, <= 2 % steps).
    Storage is time-indexed: phase slot phi holds the hypothesis whose position at frame t is (t+phi) mod P,
    so nothing moves per frame; beat states and the wrap are found by index arithmetic (firmware: O(1)).
    Tempo may change only at a beat (wrap), to P-1 or P+1 with probability TEMPO_Q/2 each.
    Evidence o = rank of the frame's novelty among the last RANK_WIN frames; beat states multiply by the
    density g(o) = (KAPPA+1) o^KAPPA (integrates to 1 over the uniform rank), the rest by 1."""

    def __init__(self, lam=16.0, kappa=4.0, tempo_q=0.02, rank_win=1536, prior_sigma=0.0, **_):
        self.P = np.arange(int(round(AP_HZ * 60.0 / 155.0)), int(round(AP_HZ * 60.0 / 60.0)) + 1)
        self.bpm_of = AP_HZ * 60.0 / self.P
        self.off = np.concatenate([[0], np.cumsum(self.P)[:-1]])
        self.n = int(self.P.sum())
        self.kappa, self.q, self.W = kappa, tempo_q, rank_win
        w = 1.0 / NUM_TEMPI
        if prior_sigma > 0:      # optional log-Gaussian tempo prior on the INITIAL state only (reported, not default)
            w = np.exp(-0.5 * (np.log2(self.bpm_of / 120.0) / prior_sigma) ** 2)
            w = w / w.sum()
        self.p = np.repeat(np.full(len(self.P), 1.0) * w / self.P, self.P)   # equal mass per period
        # Beat window: Gaussian weights w(k) around the beat, sigma = P / (lam * sqrt(2 pi)), so sum(w) = P/lam
        # EXACTLY at every tempo (a rounded hard window covers 9.6 % of a 52-frame period but 6.8 % of a
        # 133-frame one, and each covered frame without an onset is a penalty: that biased toward slow tempi).
        # Evidence enters as g(o)^w(k), so the expected log-penalty per second is the same for every tempo.
        ks, ps, ws = [], [], []
        for i, P in enumerate(self.P):
            sig = P / (lam * np.sqrt(2.0 * np.pi))
            h = max(1, int(np.ceil(3.0 * sig)))
            k = np.arange(-h, h + 1)
            wk = np.exp(-0.5 * (k / sig) ** 2)
            ks.append(k); ps.append(np.full(len(k), i)); ws.append(wk * (P / lam) / wk.sum())
        self.bw_k, self.bw_p, self.bw_w = np.concatenate(ks), np.concatenate(ps), np.concatenate(ws)
        self.t = 0
        import bisect, collections
        self._bisect, self.sorted, self.fifo = bisect, [], collections.deque()

    def rank(self, x):
        b = self._bisect
        if self.fifo:
            lo, hi = b.bisect_left(self.sorted, x), b.bisect_right(self.sorted, x)
            r = (lo + 0.5 * (hi - lo)) / len(self.sorted)
        else:
            r = 0.5
        self.fifo.append(x); b.insort(self.sorted, x)
        if len(self.fifo) > self.W:
            old = self.fifo.popleft(); del self.sorted[b.bisect_left(self.sorted, old)]
        return r

    def frame(self, x, silent, o=None):
        """Advance one AP frame. `o` (a rank in [0,1]) overrides the internal rank of x when given."""
        P, off, t = self.P, self.off, self.t
        # wrap: hypotheses at position P-1 now go to position 0 (tempo may step to a neighbour period)
        src = off + (P - 1 - t) % P
        a = self.p[src].copy()
        self.p[src] = (1.0 - self.q) * a
        dst_dn = off[:-1] + (-(t + 1)) % P[:-1]           # P+1 -> P   (receive from the next-longer period)
        dst_up = off[1:] + (-(t + 1)) % P[1:]             # P-1 -> P
        self.p[dst_dn] += 0.5 * self.q * a[1:]
        self.p[dst_up] += 0.5 * self.q * a[:-1]
        self.p[src[0]] += 0.5 * self.q * a[0]             # reflecting edges keep total mass
        self.p[src[-1]] += 0.5 * self.q * a[-1]
        self.t = t + 1
        if not silent:
            r = self.rank(x) if o is None else o
            g = max((self.kappa + 1.0) * r ** self.kappa, 1e-3)   # floor: one quiet frame never zeroes a state
            idx = off[self.bw_p] + (self.bw_k - self.t) % P[self.bw_p]
            self.p[idx] *= g ** self.bw_w
        s = self.p.sum()
        self.p /= s if s > 0 else 1.0

    def read(self):
        m = np.add.reduceat(self.p, self.off)
        w = int(np.argmax(m))
        bpm = self.bpm_of[w]
        near = np.abs(self.bpm_of / bpm - 1.0) <= 0.03
        mass = float(m[near].sum())
        def around(b):
            if b < self.bpm_of.min() * 0.98 or b > self.bpm_of.max() * 1.02:
                return None
            return float(m[np.abs(self.bpm_of / b - 1.0) <= 0.03].sum())
        rivals = [v for v in (around(bpm * 2.0 / 3.0), around(bpm * 1.5)) if v is not None]
        ratio32 = mass / max(max(rivals), 1e-12) if rivals else 1e3
        row = self.p[self.off[w]:self.off[w] + self.P[w]]
        row = row / max(row.sum(), 1e-30)
        k = int(np.argmax(row))
        phase = ((self.t + k) % self.P[w]) / self.P[w]
        return float(round(bpm, 1)), mass, float(min(ratio32, 1e3)), float(row.max() * self.P[w]), float(phase)


class Ranker:
    """Rank of x among the last W values (0..1, ties half); the M2-invariant evidence scale."""

    def __init__(self, W):
        import bisect, collections
        self.b, self.s, self.q, self.W = bisect, [], collections.deque(), W

    def __call__(self, x):
        b = self.b
        r = ((b.bisect_left(self.s, x) + 0.5 * (b.bisect_right(self.s, x) - b.bisect_left(self.s, x))) / len(self.s)
             if self.s else 0.5)
        self.q.append(x); b.insort(self.s, x)
        if len(self.q) > self.W:
            old = self.q.popleft(); del self.s[b.bisect_left(self.s, old)]
        return r


LOW_BINS = (0, 12)        # 110..208 Hz (bin 0 = notes[NOTE_OFFSET=12] = A2): bass and kick body


def spectrum_flux(hexs, prev, lo, hi):
    """Positive flux of the per-note spectrum over bins [lo, hi); returns (flux, new_prev)."""
    if not hexs:
        return 0.0, prev
    v = np.frombuffer(bytes.fromhex(hexs), dtype=">u2").astype(float) / 65535.0
    f = 0.0 if prev is None else float(np.maximum(v[lo:hi] - prev[lo:hi], 0.0).sum())
    return f, v


def run_clip_pointer(rows, params):
    pf = PointerFilter(**params)
    inp = params.get("input", "novelty")
    if inp != "novelty" and (len(rows[0]) < 4 or not rows[0][3]):
        raise SystemExit(f"--input {inp} needs a fixture captured with the per-note spectrum")
    rk_n, rk_s = Ranker(params["rank_win"]), Ranker(params["rank_win"])
    prev = None
    keys = ("gen", "bpm", "conf", "lock", "mass", "ratio32", "phase_peak", "phase")
    c = {k: [] for k in keys}
    cur = (120.0, 0.0, 1.0, 1.0, 0.0)
    for i, r in enumerate(rows):
        g, nov, sil = r[0], r[1], r[2]
        o = None
        if inp != "novelty":
            lo, hi = LOW_BINS if inp in ("lowflux", "nov+low") else (0, 80)
            fx, prev = spectrum_flux(r[3] if len(r) > 3 else "", prev, lo, hi)
            if not sil:
                o = rk_s(fx)
                if inp == "nov+low":
                    o = 0.5 * (o + rk_n(max(nov, 0.0)))
        pf.frame(0.0 if sil else max(nov, 0.0), bool(sil), o)
        if i % DECIM == 0:                                 # read out at the emit rate
            cur = pf.read()
        bpm, mass, r32, pk, ph = cur
        c["gen"].append(g); c["bpm"].append(bpm); c["conf"].append(round(mass, 5)); c["lock"].append(0)
        c["mass"].append(round(mass, 5)); c["ratio32"].append(round(r32, 4)); c["phase_peak"].append(round(pk, 4))
        c["phase"].append(round(ph, 4))
    return c, len(rows)


def run_clip(rows, params):
    if params.get("model") == "pointer":
        return run_clip_pointer(rows, params)
    params = {k: v for k, v in params.items() if k in ("nphase", "lam", "kappa", "eps", "rank_win", "floor")}
    jf = JointFilter(**params)
    em = emits_of(rows)
    keys = ("gen", "bpm", "conf", "lock", "mass", "ratio32", "phase_peak", "phase")
    c = {k: [] for k in keys}
    cur = (TEMPO_LOW + NUM_TEMPI // 2, 0.0, 1.0, 1.0, 0.0)
    ei = 0
    for r in rows:
        g = r[0]
        while ei < len(em) and em[ei][0] == g:
            cur = jf.step(em[ei][1], em[ei][2])
            ei += 1
        bpm, mass, r32, pk, ph = cur
        c["gen"].append(g); c["bpm"].append(bpm); c["conf"].append(round(mass, 5)); c["lock"].append(0)
        c["mass"].append(round(mass, 5)); c["ratio32"].append(round(r32, 4)); c["phase_peak"].append(round(pk, 4))
        c["phase"].append(round(ph, 4))
    return c, len(em)


def cmd_run(a) -> int:
    params = {k: getattr(a, k) for k in DEFAULTS}
    clips, srcs = {}, []
    t0 = time.perf_counter(); n_emits = 0
    for fx in a.fixtures:
        ip = Path(fx); idx = json.loads(ip.read_text()); srcs.append({"fixtures": str(ip.resolve()),
                                                                     "sha256": tlr.sha256_bytes(ip.read_bytes())})
        for cid, meta in sorted(idx["clips"].items()):
            if a.only and cid not in a.only:
                continue
            clips[cid], n = run_clip(tlr.load_fixture(ip, cid, meta), params)
            n_emits += n
    wall = time.perf_counter() - t0
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    doc = {"variant": "joint-" + "-".join(f"{k}{v}" for k, v in params.items()),
           "producer": {"tool": "tempo_joint_estimator.py", "params": params, "git_head": git, "inputs": srcs,
                        "tool_sha256": tlr.sha256_bytes(Path(__file__).read_bytes()),
                        "emits": n_emits, "wall_s_numpy": round(wall, 2),
                        "state_updates_per_emit": NUM_TEMPI * params["nphase"] * 3,
                        "lock_note": "lock is not modelled here (0 everywhere); the scorer is read for detected tempo, "
                                     "and correctness candidates go through `auc`"},
           "clips": clips}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    print(f"clips={len(clips)} emits={n_emits} wall_s={wall:.1f} -> {a.out}")
    return 0


# ---------------------------------------------------------------- AUC of correctness candidates
def auc(pos, neg):
    """Mann-Whitney AUC: P(score of a right track > score of a wrong track), ties count half."""
    if not pos or not neg:
        return None
    gt = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return gt / (len(pos) * len(neg))


def track_mean(c, key):
    v = [x for g, x in zip(c["gen"], c[key]) if g >= tls.SCORE_FROM_GEN]
    return float(np.mean(np.log(np.maximum(v, 1e-12)))) if key == "ratio32" else float(np.mean(v))


def agree(b1, b2):
    """1 if two detected tempi agree within 4 % up to an octave, else 0."""
    return int(any(abs(b1 - m * b2) <= 0.04 * m * b2 for m in (0.5, 1.0, 2.0)))


def cmd_auc(a) -> int:
    man = tls.load_manifest(a.manifest)
    tj = json.loads(Path(a.traj).read_text())["clips"]
    rep = {"traj": a.traj, "traj_sha256": tls.sha256_file(Path(a.traj)), "manifest_sha256": tls.sha256_file(Path(a.manifest))}
    own = {cid: tls.score_clip(c, float(man[cid]["gold_bpm"])) for cid, c in tj.items() if cid in man}
    s = tls.summarise(own)
    rep["estimator"] = {"n": s["n"], "correct_acc2": s["correct"], "detected_32": s["detected_32"],
                        "per_clip": {cid: {"detected": r["detected_bpm"], "gold": r["gold_bpm"], "correct": r["correct"],
                                           "is_32": r["is_32"]} for cid, r in own.items()}}
    feats = ("mass", "ratio32", "phase_peak")
    rep["estimator"]["auc_own_choice"] = {
        f: auc([track_mean(tj[c], f) for c, r in own.items() if r["correct"]],
               [track_mean(tj[c], f) for c, r in own.items() if not r["correct"]]) for f in feats}
    if a.tracker_traj:
        tt = json.loads(Path(a.tracker_traj).read_text())["clips"]
        trk = {cid: tls.score_clip(c, float(man[cid]["gold_bpm"])) for cid, c in tt.items() if cid in man and cid in tj}
        ag = {cid: agree(trk[cid]["detected_bpm"], own[cid]["detected_bpm"]) for cid in trk}
        right = [c for c, r in trk.items() if r["correct"]]
        wrong = [c for c, r in trk.items() if not r["correct"]]
        rep["tracker"] = {"tracker_traj": a.tracker_traj, "n": len(trk), "correct": len(right),
                          "agreement_auc": auc([ag[c] for c in right], [ag[c] for c in wrong]),
                          "agree_and_correct": sum(ag[c] for c in right), "agree_and_wrong": sum(ag[c] for c in wrong),
                          "auc_joint_features_on_tracker_choice": {
                              f: auc([track_mean(tj[c], f) for c in right], [track_mean(tj[c], f) for c in wrong])
                              for f in feats}}
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    show = {k: v for k, v in rep.items() if k != "estimator"}
    show["estimator"] = {k: v for k, v in rep["estimator"].items() if k != "per_clip"}
    print(json.dumps(show, indent=1, sort_keys=True))
    return 0


GEN_S = 1.0 / AP_HZ                           # one trajectory row (generation) = one AP frame = 7.5 ms


def hold(cond, hold_s):
    """1 on a generation only once `cond` has been true on every generation of the last `hold_s` seconds
    (this one included); 0 resets the run. hold_s = 0 returns `cond` unchanged."""
    out, run = [], 0
    for x in cond:
        run = run + 1 if x else 0
        out.append(int(bool(x) and run * GEN_S >= hold_s))
    return out


def cmd_gate(a) -> int:
    """Agreement-gated lock: the tracker's published lock survives an emit only while its BPM agrees with
    the estimator's (within 4 % up to an octave), and, with --hold-s D (experiment E1), only once lock and
    agreement have held continuously for D seconds. Writes a trajectory for the frozen scorer."""
    est = json.loads(Path(a.estimator_traj).read_text())["clips"]
    trk = json.loads(Path(a.tracker_traj).read_text())
    variant = f"{trk.get('variant')}+agreement-gate" + (f"-hold{a.hold_s:g}s" if a.hold_s > 0 else "")
    out = {"variant": variant, "producer": {
        "tool": "tempo_joint_estimator.py gate", "tracker_traj": a.tracker_traj,
        "tracker_sha256": tls.sha256_file(Path(a.tracker_traj)), "estimator_traj": a.estimator_traj,
        "estimator_sha256": tls.sha256_file(Path(a.estimator_traj))}, "clips": {}}
    if a.hold_s > 0:                           # absent at 0 so the p2.6 output stays byte-identical
        out["producer"]["hold_s"] = a.hold_s
    for cid, c in trk["clips"].items():
        eb = dict(zip(est[cid]["gen"], est[cid]["bpm"]))
        lock = hold([bool(l) and agree(b, eb[g]) for g, b, l in zip(c["gen"], c["bpm"], c["lock"])], a.hold_s)
        out["clips"][cid] = {"gen": c["gen"], "bpm": c["bpm"], "lock": lock, "conf": c.get("conf", [0.0] * len(lock))}
    Path(a.out).write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(f"gated {len(out['clips'])} clips -> {a.out}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    gt = sub.add_parser("gate")
    gt.add_argument("--tracker-traj", required=True)
    gt.add_argument("--estimator-traj", required=True)
    gt.add_argument("--out", required=True)
    gt.add_argument("--hold-s", dest="hold_s", type=float, default=0.0)
    r = sub.add_parser("run")
    r.add_argument("--fixtures", action="append", required=True)
    r.add_argument("--only", nargs="*")
    r.add_argument("--out", required=True)
    for k, v in DEFAULTS.items():
        r.add_argument(f"--{k.replace('_', '-')}", dest=k, type=type(v), default=v)
    u = sub.add_parser("auc")
    u.add_argument("--manifest", required=True, type=Path)
    u.add_argument("--traj", required=True)
    u.add_argument("--tracker-traj")
    u.add_argument("--out")
    a = p.parse_args(argv)
    return {"run": cmd_run, "auc": cmd_auc, "gate": cmd_gate}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
