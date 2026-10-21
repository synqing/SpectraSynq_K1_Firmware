#!/usr/bin/env python3
"""Experiment E2: a learned lock score (lane R1, DEF-002). HOST-ONLY; no firmware change.

E1 (agreement held for D seconds) failed because its parameter depends on clip length and agreement alone does
not separate right from wrong. E2 publishes the lane tracker's lock only while a logistic score over signals the
lane already computes says the tracker's CURRENT tempo is right. Every feature is read over a fixed trailing
window of W seconds (default 4 s) or at the current emit, so nothing depends on clip length:

  agree     fraction of the window where tracker and joint estimator agree (4 %, up to an octave)
  trk_stab  fraction of the window where the tracker's tempo is within 4 % of its current tempo
  est_stab  the same for the estimator
  est_mass  estimator posterior mass at its arg-max tempo (current)
  est_r32   log of the estimator's 3:2 margin (current, clipped)
  est_phase log of the estimator's phase-peak ratio (current)
  conf      tracker confidence (current)
  quality   tracker CONF_V2 quality (current)
  tooth     tracker tooth consistency (current)
  votes     fraction of the tracker's comb / point-ACF / Goertzel tempi that agree with its published tempo

Label of an emit: the tracker's current tempo is CORRECT (within 4 % of gold x {1/2, 1, 2}, the scorer's rule).
Lock rule: tracker confidence >= 0.30 (no lock from the NONE band), producer not silent, and score >= THETA.

  tempo_lock_score.py features --manifest M --tracker-traj T --estimator-traj E --out F.npz [--window-s 4]
  tempo_lock_score.py train --features F.npz [F2.npz ...] --out MODEL.json [--folds 5]
     grouped cross-validation by clip: each clip is scored only by a model that never saw it; THETA is the
     smallest threshold whose cross-validated track-level result keeps the upper 95 % Wilson bound on wrong
     locks <= 10 %; the final model is refit on all clips and frozen with that THETA.
  tempo_lock_score.py gate --model MODEL.json --tracker-traj T --estimator-traj E --out G.json
     writes a trajectory for the frozen scorer (tracker BPM unchanged; lock replaced by the E2 rule).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tempo_lane_scorer as tls  # noqa: E402

GEN_S = 96.0 / 12800.0
FEATURES = ("agree", "trk_stab", "est_stab", "est_mass", "est_r32", "est_phase", "conf", "quality", "tooth", "votes")
CONF_FLOOR = 0.30
WILSON_MAX = 0.10


def sha256_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def octave_agree(a, b):
    """Elementwise: a and b within 4 % up to an octave (as tempo_joint_estimator.agree)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    return np.any([np.abs(a - m * b) <= 0.04 * m * b for m in (0.5, 1.0, 2.0)], axis=0)


def trailing_mean(x, n):
    c = np.concatenate([[0.0], np.cumsum(np.asarray(x, float))])
    i = np.arange(1, len(x) + 1)
    lo = np.maximum(0, i - n)
    return (c[i] - c[lo]) / (i - lo)


def correct(bpm, gold):
    bpm = np.asarray(bpm, float)
    return np.any([np.abs(bpm - m * gold) <= tls.TOL_CORRECT * m * gold for m in tls.CORRECT_MULTS], axis=0)


def clip_features(t, e, window_s):
    n = max(1, int(round(window_s / GEN_S)))
    tb, eb = np.asarray(t["bpm"], float), np.asarray(e["bpm"], float)
    ag = octave_agree(tb, eb).astype(float)
    # stability: fraction of the trailing window within 4 % of the current tempo (vectorised over lags)
    def stab(x):
        out = np.zeros(len(x))
        cnt = np.zeros(len(x))
        for lag in range(n):
            prev = np.concatenate([np.full(lag, np.nan), x[:len(x) - lag]])
            ok = ~np.isnan(prev)
            out[ok] += (np.abs(prev[ok] / np.maximum(x[ok], 1e-9) - 1.0) <= 0.04)
            cnt[ok] += 1
        return out / np.maximum(cnt, 1)
    votes = np.mean([octave_agree(tb, np.asarray(t[k], float)) for k in ("comb_bpm", "point_bpm", "goertzel_bpm")], 0)
    F = np.column_stack([
        trailing_mean(ag, n), stab(tb), stab(eb),
        np.asarray(e["mass"], float), np.log(np.clip(np.asarray(e["ratio32"], float), 1e-3, 1e3)),
        np.log(np.maximum(np.asarray(e["phase_peak"], float), 1e-6)),
        np.asarray(t["conf"], float), np.asarray(t["quality"], float), np.asarray(t["tooth"], float), votes])
    gate_ok = (np.asarray(t["conf"], float) >= CONF_FLOOR) & (np.asarray(t.get("producer_silence", [0] * len(tb))) == 0)
    return F, gate_ok


def cmd_features(a) -> int:
    man = tls.load_manifest(a.manifest)
    tt = json.loads(Path(a.tracker_traj).read_text())["clips"]
    ee = json.loads(Path(a.estimator_traj).read_text())["clips"]
    Fs, ys, oks, clip, gens, bpms = [], [], [], [], [], []
    names = sorted(c for c in tt if c in man)
    for k, cid in enumerate(names):
        t, e = tt[cid], ee[cid]
        if t["gen"] != e["gen"]:
            raise SystemExit(f"{cid}: tracker and estimator generations differ")
        F, ok = clip_features(t, e, a.window_s)
        Fs.append(F); oks.append(ok); ys.append(correct(t["bpm"], float(man[cid]["gold_bpm"])))
        clip.append(np.full(len(F), k)); gens.append(np.asarray(t["gen"])); bpms.append(np.asarray(t["bpm"], float))
    np.savez_compressed(a.out, X=np.vstack(Fs), y=np.concatenate(ys), ok=np.concatenate(oks),
                        clip=np.concatenate(clip), gen=np.concatenate(gens), bpm=np.concatenate(bpms),
                        names=np.array(names), gold=np.array([float(man[c]["gold_bpm"]) for c in names]),
                        meta=json.dumps({"manifest_sha256": sha256_file(a.manifest),
                                         "tracker_sha256": sha256_file(a.tracker_traj),
                                         "estimator_sha256": sha256_file(a.estimator_traj),
                                         "window_s": a.window_s, "features": FEATURES}))
    print(f"clips={len(names)} rows={sum(len(f) for f in Fs)} -> {a.out}")
    return 0


# ---------------------------------------------------------------- model (standardised logistic regression)
def fit(X, y, l2=1.0):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    from sklearn.linear_model import LogisticRegression
    m = LogisticRegression(C=1.0 / l2, max_iter=2000).fit(Z, y)
    return {"mu": mu.tolist(), "sd": sd.tolist(), "w": m.coef_[0].tolist(), "b": float(m.intercept_[0])}


def predict(model, X):
    Z = (X - np.asarray(model["mu"])) / np.asarray(model["sd"])
    return 1.0 / (1.0 + np.exp(-(Z @ np.asarray(model["w"]) + model["b"])))


def wilson_upper(x, n, z=1.96):
    if n == 0:
        return 1.0
    p = x / n
    return (p + z * z / (2 * n) + z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def load_sets(paths):
    parts, off, names = {k: [] for k in ("X", "y", "ok", "clip", "gen", "bpm")}, 0, []
    golds, metas = [], []
    for p in paths:
        d = np.load(p, allow_pickle=False)
        for k in parts:
            parts[k].append(d[k] + off if k == "clip" else d[k])
        names += list(d["names"]); golds += list(d["gold"]); metas.append(json.loads(str(d["meta"])))
        off += len(d["names"])
    return {k: np.concatenate(v) for k, v in parts.items()}, names, golds, metas


def track_counts(score, D, golds, theta):
    """Locked-right and locked-wrong track counts for lock = ok & score >= theta, judged by the frozen
    scorer's own score_clip (no re-implementation of its rules)."""
    lock = (D["ok"] & (score >= theta)).astype(int)
    right = wrong = 0
    for k in np.unique(D["clip"]):
        m = D["clip"] == k
        r = tls.score_clip({"gen": D["gen"][m].tolist(), "bpm": D["bpm"][m].tolist(), "lock": lock[m].tolist()},
                           float(golds[k]))
        right += r["locked"] and r["correct"]
        wrong += r["wrong_lock"]
    return int(right), int(wrong)


def cmd_train(a) -> int:
    D, names, golds, metas = load_sets(a.features)
    X, y, ok, clip = D["X"], D["y"].astype(int), D["ok"], D["clip"]
    rng = np.random.default_rng(20261022)
    uclips = np.unique(clip)
    fold_of = dict(zip(uclips, rng.permutation(len(uclips)) % a.folds))
    cv = np.zeros(len(y))
    for f in range(a.folds):
        te = np.array([fold_of[c] == f for c in clip])
        tr = ~te & ok
        cv[te] = predict(fit(X[tr], y[tr], a.l2), X[te])
    grid = np.round(np.arange(0.50, 0.995, 0.005), 3)
    table = []
    for th in grid:
        r, w = track_counts(cv, D, golds, th)
        table.append({"theta": float(th), "right": r, "wrong": w, "wilson_upper": round(wilson_upper(w, r + w), 4)})
    ok_rows = [t for t in table if t["right"] + t["wrong"] > 0 and t["wilson_upper"] <= WILSON_MAX]
    pick = min(ok_rows, key=lambda t: t["theta"]) if ok_rows else max(table, key=lambda t: (t["right"] - 5 * t["wrong"]))
    model = fit(X[ok], y[ok], a.l2)
    from sklearn.metrics import roc_auc_score
    emit_auc = float(roc_auc_score(y[ok], cv[ok])) if len(set(y[ok])) > 1 else None
    doc = {"experiment": "E2 learned lock score", "features": list(FEATURES), "model": model, "theta": pick["theta"],
           "theta_rule": f"smallest theta with CV Wilson upper <= {WILSON_MAX}" if ok_rows else
                         "NO theta met the Wilson bound; recorded the best right-5*wrong row (not a pass)",
           "wilson_bound_met_in_cv": bool(ok_rows), "cv_pick": pick, "cv_table": table, "cv_emit_auc": emit_auc,
           "n_clips": len(names), "folds": a.folds, "l2": a.l2, "conf_floor": CONF_FLOOR,
           "inputs": [{"features": str(p), "sha256": sha256_file(p), **m} for p, m in zip(a.features, metas)]}
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({k: doc[k] for k in ("theta", "theta_rule", "wilson_bound_met_in_cv", "cv_pick",
                                          "cv_emit_auc", "n_clips")}, indent=1))
    print("weights:", dict(zip(FEATURES, np.round(model["w"], 3))))
    return 0


def cmd_gate(a) -> int:
    M = json.loads(Path(a.model).read_text())
    tt = json.loads(Path(a.tracker_traj).read_text())
    ee = json.loads(Path(a.estimator_traj).read_text())["clips"]
    w = json.loads(json.dumps(M["inputs"][0]))["window_s"]
    out = {"variant": f"{tt.get('variant')}+e2-lockscore", "producer": {
        "tool": "tempo_lock_score.py gate", "model": a.model, "model_sha256": sha256_file(a.model),
        "tracker_traj": a.tracker_traj, "tracker_sha256": sha256_file(a.tracker_traj),
        "estimator_traj": a.estimator_traj, "estimator_sha256": sha256_file(a.estimator_traj)}, "clips": {}}
    for cid, t in tt["clips"].items():
        F, ok = clip_features(t, ee[cid], w)
        lock = (ok & (predict(M["model"], F) >= M["theta"])).astype(int).tolist()
        out["clips"][cid] = {"gen": t["gen"], "bpm": t["bpm"], "lock": lock, "conf": t["conf"]}
    Path(a.out).write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(f"gated {len(out['clips'])} clips -> {a.out}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("features")
    f.add_argument("--manifest", required=True)
    f.add_argument("--tracker-traj", required=True)
    f.add_argument("--estimator-traj", required=True)
    f.add_argument("--out", required=True)
    f.add_argument("--window-s", type=float, default=4.0)
    t = sub.add_parser("train")
    t.add_argument("--features", nargs="+", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--folds", type=int, default=5)
    t.add_argument("--l2", type=float, default=1.0)
    g = sub.add_parser("gate")
    g.add_argument("--model", required=True)
    g.add_argument("--tracker-traj", required=True)
    g.add_argument("--estimator-traj", required=True)
    g.add_argument("--out", required=True)
    a = p.parse_args(argv)
    return {"features": cmd_features, "train": cmd_train, "gate": cmd_gate}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
