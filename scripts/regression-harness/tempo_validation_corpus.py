#!/usr/bin/env python3
"""Validation tempo corpus (lane R1, experiment E1 and later lock candidates; DEF-002).

GTZAN Genre (Tzanetakis & Cook 2002; 1,000 x 30 s, 10 genres) with the tempo annotations of
github.com/TempoBeatDownbeat/gtzan_tempo_beat (Marchand & Peeters 2015, one BPM per clip). Disjoint from
the development clips (HarmonixSet) and from the held-out acceptance corpus (Ballroom + GiantSteps).
Validation is NOT acceptance: it screens a lock candidate before the single held-out run.

Split, pre-registered before any clip is run: a clip goes to V1 when the first byte of sha256(row id) is
even, else to V2. V1 judges experiment E1 once. V2 stays untouched for the next candidate, so judging E1
does not spend all the validation material.

Gold tempo is folded by octave into [60, 155] exactly like the held-out loader (tempo_heldout_corpus.fold_bpm);
the scorer already counts x1/2 and x2 as correct. Audio is decoded at run time by tempo_lane_emu.py exactly as
the development clips (ffmpeg to mono 12.8 kHz, one gain to peak 4096); this tool only writes manifest rows.

  tempo_validation_corpus.py prepare --audio DIR --annotations DIR --out-v1 V1.json --out-v2 V2.json
     [--excluded EXCLUDED.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tempo_heldout_corpus import FOLD_HI, FOLD_LO, fold_bpm  # noqa: E402

SOURCE = ("GTZAN Genre (Tzanetakis & Cook 2002), audio genres.tar.gz via huggingface.co/datasets/marsyas/gtzan; "
          "tempo annotations github.com/TempoBeatDownbeat/gtzan_tempo_beat (Marchand & Peeters 2015)")
SPLIT_RULE = ("V1 if sha256(row id)[0] is even, else V2; row id = gz:<genre>_<number>, e.g. gz:blues_00000 "
              "(pre-registered 2026-10-22, before any clip was run)")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def split_of(row_id: str) -> str:
    return "V1" if hashlib.sha256(row_id.encode()).digest()[0] % 2 == 0 else "V2"


def cmd_prepare(a) -> int:
    audio = {p.stem: p for p in Path(a.audio).rglob("*") if p.suffix.lower() in (".au", ".wav")}
    rows, excluded = {"V1": [], "V2": []}, []
    for bpm_file in sorted(Path(a.annotations).glob("gtzan_*.bpm")):
        _, genre, num = bpm_file.stem.split("_")           # gtzan_blues_00000
        stem = f"{genre}.{num}"                             # audio file stem (blues.00000)
        rid = f"gz:{genre}_{num}"                           # no dot: extract cuts clip ids at the first dot
        try:
            gold_raw = float(bpm_file.read_text().split()[0])
        except (ValueError, IndexError):
            excluded.append({"id": rid, "reason": "annotation unreadable"})
            continue
        if stem not in audio:
            excluded.append({"id": rid, "reason": "no audio file"})
            continue
        gold = fold_bpm(gold_raw)
        if not FOLD_LO <= gold <= FOLD_HI:
            excluded.append({"id": rid, "reason": f"folded gold {gold} outside [{FOLD_LO},{FOLD_HI}]"})
            continue
        rows[split_of(rid)].append({
            "id": rid, "path": str(audio[stem].resolve()), "sha256": sha256_file(audio[stem]),
            "gold_bpm": round(gold, 4), "gold_bpm_raw": gold_raw, "genre": genre, "role": "validation",
            "split": split_of(rid), "source": SOURCE, "excerpt": {"start_ms": 0, "duration_ms": None},
            "annotation_sha256": sha256_file(bpm_file)})
    for stem in sorted(set(audio) - {f"{p.stem.split('_')[1]}.{p.stem.split('_')[2]}"
                                     for p in Path(a.annotations).glob("gtzan_*.bpm")}):
        excluded.append({"id": "gz:" + stem.replace(".", "_"), "reason": "no tempo annotation"})
    for name, out in (("V1", a.out_v1), ("V2", a.out_v2)):
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps({"schema": "k1-tempo-manifest/1", "split": name, "split_rule": SPLIT_RULE,
                                         "rows": rows[name]}, indent=1) + "\n")
    if a.excluded:
        Path(a.excluded).write_text(json.dumps(excluded, indent=1) + "\n")
    print(f"V1={len(rows['V1'])} V2={len(rows['V2'])} excluded={len(excluded)}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("prepare")
    r.add_argument("--audio", required=True)
    r.add_argument("--annotations", required=True)
    r.add_argument("--out-v1", required=True)
    r.add_argument("--out-v2", required=True)
    r.add_argument("--excluded")
    a = p.parse_args(argv)
    return {"prepare": cmd_prepare}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
