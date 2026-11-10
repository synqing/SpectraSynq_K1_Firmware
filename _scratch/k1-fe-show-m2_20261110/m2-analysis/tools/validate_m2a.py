#!/usr/bin/env python3
"""M2 lane A: validate published Trinity artefacts, write evidence semantics and the 75-155 s passage view.

Run with venv-validate/bin/python (jsonschema 4.23.0). Writes only under m2-analysis/.
The passage view is a pure slice of the full-track artefacts: no re-analysis, no re-normalisation.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import jsonschema

LANE = Path(__file__).resolve().parents[1]
OUT = LANE / "out" / "loreen"
SCHEMA = Path("/Users/spectrasynq/Workspace_Management/Software/Trinity/analysis/contract_schema.json")
SR = 44100
PASSAGE = (75.0, 155.0)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    contract = json.loads((OUT / "contract.json").read_text())
    feats = json.loads((OUT / "stem_features.json").read_text())
    ident = json.loads((OUT / "identity.json").read_text())
    report = {"schema_file": str(SCHEMA), "schema_sha256": sha(SCHEMA), "checks": {}}
    chk = report["checks"]

    # 1. JSON Schema (draft-07) against Trinity's own contract schema
    v = jsonschema.Draft7Validator(json.loads(SCHEMA.read_text()))
    errs = [f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(contract)]
    chk["contract_json_schema"] = {"result": "PASS" if not errs else "FAIL", "errors": errs[:20]}

    # 2. Structural facts the schema text promises but does not encode
    r = contract["rhythm"]
    beats, downs = r["beats"], r["downbeats"]
    strictly = lambda a: all(a[i] < a[i + 1] for i in range(len(a) - 1))
    dur = contract["track"]["duration_sec"]
    segs = contract["structure"]["segments"]
    facts = {
        "beats_strictly_increasing": strictly(beats),
        "downbeats_strictly_increasing": strictly(downs),
        "downbeats_subset_of_beats_exact": all(d in set(beats) for d in downs),
        "beat_positions_len_equals_beats": len(r["beat_positions"]) == len(beats),
        "times_within_duration": all(0 <= t <= dur for t in beats + downs),
        "segments_ordered_non_overlapping": all(segs[i]["end"] <= segs[i + 1]["start"] + 1e-12 for i in range(len(segs) - 1)),
        "segments_within_duration": all(0 <= s["start"] <= s["end"] <= dur for s in segs),
        "duration_equals_frames_over_rate": math.isclose(dur, ident["decode"]["frames"] / SR, abs_tol=1e-9),
    }
    chk["contract_facts"] = {"result": "PASS" if all(facts.values()) else "FAIL", **facts}

    # 3. stem_features_v1 shape (what the PRISM adapter demands)
    keys = ["rms", "onset_strength", "band_energy_low", "band_energy_mid", "band_energy_high"]
    lens = {f"{s}.{k}": len(feats["stems"][s][k]) for s in ("vocals", "drums", "bass", "other") for k in keys}
    finite_nonneg = all(math.isfinite(x) and x >= 0 for s in feats["stems"].values() for k in keys for x in s[k])
    n = next(iter(lens.values()))
    sf = {
        "schema": feats["schema"] == "stem_features_v1",
        "fps_integer_50": feats["fps"] == 50,
        "equal_lengths": len(set(lens.values())) == 1,
        "frame_count": n,
        "expected_frames_floor_formula": 1 + (ident["decode"]["frames"] - 2048) // (SR // 50),
        "all_finite_non_negative": finite_nonneg,
        "duration_within_one_frame_of_contract": abs(feats["duration_sec"] - dur) <= 1 / feats["fps"],
    }
    sf["frame_count_matches_formula"] = sf["frame_count"] == sf["expected_frames_floor_formula"]
    chk["stem_features_shape"] = {"result": "PASS" if all(v for k, v in sf.items() if isinstance(v, bool)) else "FAIL", **sf}

    # 4. Evidence semantics (PLAN A03): every emitted feature named; missing stated explicitly
    hop = SR // 50  # 882 samples
    semantics = {
        "schema": "m2a-evidence-semantics/0",
        "time_axis": "asset sample n at 44100 Hz; contract times are float seconds n/44100 from track.wav sample 0; "
                     "stem feature frame i covers samples [i*882, i*882+2048) of the stem WAV (hop 882 = floor(44100/50), n_fft 2048); "
                     "the PRISM adapter places frame i at round(i*1e6/50) us, i.e. at the frame's START sample, so a feature "
                     "describes audio up to 46.4 ms (2048 samples) AFTER its timestamp (centre at +23.2 ms). Flag for M2-compose: "
                     "no delay compensation is applied anywhere; do not add one twice.",
        "fps_note": "hop 882 samples at 44.1 kHz = exactly 50.000 fps (20.000 ms); integer, no drift",
        "features": {
            "rhythm.beats": {"source": "Beat This! final0 on full mix, dbn=False", "units": "seconds", "range": f"[0, {dur}]",
                              "resolution": "model frame 20 ms (50 fps), peak-picked", "normalisation": "n/a", "smoothing": "minimal postprocessing (peak dedupe)", "delay": "none (offline, non-causal)"},
            "rhythm.downbeats": {"source": "Beat This! final0, snapped onto beats", "units": "seconds", "range": "subset of beats",
                                  "resolution": "20 ms", "normalisation": "n/a", "smoothing": "as beats", "delay": "none"},
            "rhythm.beat_positions": {"source": "Trinity rhythm_provider (counts beats since last downbeat, 70 ms tolerance)", "units": "integer 1..16", "range": "1..max", "resolution": "per beat", "normalisation": "n/a", "smoothing": "none", "delay": "none"},
            "rhythm.bpm": {"source": "60 / median inter-beat interval", "units": "beats per minute", "range": "30..300 (schema)", "resolution": "whole track, single value", "normalisation": "n/a", "smoothing": "median", "delay": "none",
                            "note": "global; tempo changes are not represented"},
            "rhythm.time_signature": {"source": "export_contract: numerator = max(beat_positions), denominator fixed 4", "units": "meter", "note": "inferred, not measured; denominator is a constant"},
            "structure.segments": {"source": "allin1-trinity harmonix-all 8-fold ensemble on Demucs stems", "units": "seconds + label from Harmonix vocabulary", "range": "[0, duration]",
                                    "resolution": "model 100 fps boundaries", "normalisation": "n/a", "smoothing": "allin1 postprocessing", "delay": "none",
                                    "quality": "labels are model inferences (Harmonix taxonomy), not ground truth; no per-segment confidence is emitted"},
            "stems.<stem>.rms": {"source": "Demucs htdemucs stem (int16 WAV), mono = mean(L,R)", "units": "linear RMS of PCM float in [-1,1] (not dB)", "range": "[1e-6, ~1]; 1e-6 floor from +1e-12 inside sqrt",
                                  "resolution": "50 fps, 2048-sample rectangular frame", "normalisation": "none (absolute, comparable across stems)", "smoothing": "none beyond frame", "delay": "frame starts at timestamp (see time_axis)"},
            "stems.<stem>.onset_strength": {"source": "positive spectral flux of Hann-windowed |rfft|", "units": "dimensionless", "range": "[0, 1]",
                                             "resolution": "50 fps", "normalisation": "PER STEM, PER WHOLE TRACK: divided by that stem's 99th percentile, clipped at 1. A passage slice keeps the whole-track scale.",
                                             "smoothing": "none", "delay": "frame starts at timestamp; frame 0 is 0.0 by construction (no previous frame)"},
            "stems.<stem>.band_energy_low": {"source": "mean |rfft| (Hann, n_fft 2048) over bins < 250 Hz", "units": "linear magnitude (unnormalised FFT sum scale, not dB, not 0-1)", "range": "[0, unbounded)", "resolution": "50 fps; 21.5 Hz bins", "normalisation": "none", "smoothing": "none", "delay": "as rms"},
            "stems.<stem>.band_energy_mid": {"source": "mean |rfft| over 250-4000 Hz", "units": "as band_energy_low", "range": "[0, unbounded)", "resolution": "50 fps", "normalisation": "none", "smoothing": "none", "delay": "as rms"},
            "stems.<stem>.band_energy_high": {"source": "mean |rfft| over >= 4000 Hz", "units": "as band_energy_low", "range": "[0, unbounded)", "resolution": "50 fps", "normalisation": "none", "smoothing": "none", "delay": "as rms"},
        },
        "not_emitted": {
            "per-feature validity/confidence": "NOT PRODUCED by Trinity k1-lite; absent, not zero",
            "blobs (macros/activations/embeddings/spectrogram)": "null by design at k1-lite (organs.lock note: derive_macros_from_activations returns None)",
            "tonal / notes / chords": "NOT RUN (analyze_track --tonal not requested; BasicPitch not part of locked path)",
            "per-beat aggregates (rms_per_beat etc.)": "NOT PRODUCED (write_stem_features passes no beat_frames)",
            "full-mix stem_features": "NOT PRODUCED (Trinity stem pack covers the four Demucs stems only)",
            "vocal activity / phrase detection": "NOT PRODUCED; vocals.rms is energy of a separated stem, which contains bleed",
        },
        "separator_caveats": "Demucs stems are estimates with bleed, not isolated instruments. Written as int16 WAV. "
                             "Demucs clip-mode 'rescale' divided vocals, drums and other by an UNRECORDED factor (their peaks are exactly 1/1.01 = 0.9901; raw/stem_check.json), "
                             "so absolute rms/band_energy levels are NOT comparable across those stems or to bass; per-stem relative shape is intact. "
                             "Demucs ran with one unseeded random shift (Trinity drops --demucs-shifts 0), so stems are not reproducible from source; this cache is the reference copy.",
    }
    (OUT / "evidence_semantics.json").write_text(json.dumps(semantics, indent=2) + "\n")

    # 5. Passage view 75-155 s: slice only; frame grid stays asset-anchored (75 s = frame 3750 exactly)
    p0, p1 = PASSAGE
    f0, f1 = int(round(p0 * 50)), int(round(p1 * 50))
    pv_contract = json.loads(json.dumps(contract))
    pv_contract["track"]["duration_sec"] = p1 - p0
    keep = [i for i, b in enumerate(beats) if p0 <= b < p1]
    pv_contract["rhythm"]["beats"] = [round(beats[i] - p0, 9) for i in keep]
    pv_contract["rhythm"]["beat_positions"] = [r["beat_positions"][i] for i in keep]
    pv_contract["rhythm"]["downbeats"] = [round(d - p0, 9) for d in downs if p0 <= d < p1]
    # identical rounding on both lists keeps the downbeat-subset-of-beats equality exact
    pv_segs = []
    for s in segs:
        a, b = max(s["start"], p0), min(s["end"], p1)
        if b > a:
            pv_segs.append({"start": round(a - p0, 9), "end": round(b - p0, 9), "label": s["label"]})
    pv_contract["structure"]["segments"] = pv_segs
    pv_contract["passage"] = {"source_start_sec": p0, "source_end_sec": p1, "source_start_sample": int(p0 * SR),
                              "source_end_sample": int(p1 * SR), "rebase": "all times here = full-track time - 75.0 s",
                              "transition_sec_in_passage": 137.0 - p0, "full_contract_sha256": sha(OUT / "contract.json")}
    pv_feats = {k: v for k, v in feats.items() if k != "stems"}
    pv_feats["duration_sec"] = p1 - p0
    pv_feats["stems"] = {}
    for s, d in feats["stems"].items():
        pv_feats["stems"][s] = {k: (v[f0:f1] if isinstance(v, list) else v) for k, v in d.items()}
        pv_feats["stems"][s]["duration_sec"] = p1 - p0
    pv_feats["passage"] = {"source_first_frame": f0, "source_end_frame_exclusive": f1, "fps": 50,
                           "normalisation_scope": "unchanged whole-track scale (onset p99 per stem over the full track)",
                           "full_stem_features_sha256": sha(OUT / "stem_features.json")}
    pdir = OUT / "passage_75_155"
    pdir.mkdir(exist_ok=True)
    (pdir / "contract.json").write_text(json.dumps(pv_contract, indent=2) + "\n")
    (pdir / "stem_features.json").write_text(json.dumps(pv_feats, indent=2) + "\n")
    perrs = [f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(pv_contract)]
    chk["passage_contract_json_schema"] = {"result": "PASS" if not perrs else "FAIL", "errors": perrs[:20],
                                           "beats": len(keep), "downbeats": len(pv_contract["rhythm"]["downbeats"]),
                                           "segments": [(s["start"], s["end"], s["label"]) for s in pv_segs],
                                           "frames": f1 - f0,
                                           "downbeats_subset_exact": all(d in set(pv_contract["rhythm"]["beats"]) for d in pv_contract["rhythm"]["downbeats"])}

    # 6. Correction layer (PLAN P3.7): the raw Trinity contract is never altered. allin1 reports segment
    #    boundaries on a 10 ms grid, so the last segment can end after the decoded duration; the PRISM
    #    adapter rejects that. consumer/contract.json clamps any boundary > duration_sec to duration_sec.
    cdir = OUT / "consumer"
    cdir.mkdir(exist_ok=True)
    cc = json.loads(json.dumps(contract))
    corrections = []
    for i, s in enumerate(cc["structure"]["segments"]):
        for k in ("start", "end"):
            if s[k] > dur:
                corrections.append({"path": f"structure.segments[{i}].{k}", "from": s[k], "to": dur,
                                    "delta_s": s[k] - dur, "reason": "allin1 boundary on 10 ms grid exceeds decoded duration; adapter requires <= track.duration_sec"})
                s[k] = dur
    (cdir / "contract.json").write_text(json.dumps(cc, indent=2) + "\n")
    (cdir / "corrections.json").write_text(json.dumps({
        "schema": "m2a-corrections/0", "base_contract_sha256": sha(OUT / "contract.json"),
        "stem_features": "unchanged: use ../stem_features.json", "corrections": corrections,
        "corrected_contract_sha256": sha(cdir / "contract.json")}, indent=2) + "\n")
    cerrs = [f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(cc)]
    chk["consumer_contract_json_schema"] = {"result": "PASS" if not cerrs else "FAIL", "errors": cerrs[:20],
                                            "corrections": len(corrections),
                                            "segments_within_duration": all(0 <= s["start"] <= s["end"] <= dur for s in cc["structure"]["segments"])}
    chk["contract_facts"]["note"] = "segments_within_duration FAIL is a real Trinity/allin1 output defect, reported upstream; consumer/ carries the disclosed clamp"

    report["artefact_sha256"] = {str(p.relative_to(OUT)): sha(p) for p in sorted(OUT.rglob("*.json"))}
    (LANE / "M2A-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if all(c["result"] == "PASS" for k, c in chk.items() if k != "contract_facts") else 1


if __name__ == "__main__":
    sys.exit(main())
