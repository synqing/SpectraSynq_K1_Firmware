#!/usr/bin/env python3
"""Build / extend the tempo corpus manifest (tests/fixtures/tempo_corpus/manifest.json).

Lane R1 (DEF-002, invariant I5): every corpus clip carries a role. The 36 HarmonixSet clips are
DEVELOPMENT data (the 88 BPM prior and CONF_V2 were tuned on them); held-out rows come from a
Captain-approved corpus and are merged with `add-heldout`. tempo_lane_scorer.py reads only this
file; a clip that is not in it is not scored.

  tempo_corpus_manifest.py build-dev   [--out PATH]
  tempo_corpus_manifest.py add-heldout --rows ROWS.json [--out PATH]
  tempo_corpus_manifest.py verify      [--out PATH]      # re-hash every source file
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import tempo_accuracy as ta  # noqa: E402

DEFAULT_OUT = ROOT / "tests/fixtures/tempo_corpus/manifest.json"
DEV_CORPUS = Path("/Users/spectrasynq/SensoryBridge-main 9/Lightwave-Ledstrip/firmware-v3/test/music_corpus/"
                  "harmonixset/esv11_benchmark/audio_12k8")
SCHEMA = "k1-tempo-corpus-manifest/1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(out: Path) -> dict:
    if out.exists():
        return json.loads(out.read_text())
    return {"schema": SCHEMA, "range_bpm": [60, 155],
            "note": "role dev = tuning/selection data; role heldout = acceptance only (scorer refuses dev acceptance).",
            "rows": []}


def save(out: Path, doc: dict) -> None:
    doc["rows"].sort(key=lambda r: r["id"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"wrote {out} rows={len(doc['rows'])} sha256={sha256_file(out)}")


def build_dev(out: Path) -> int:
    gt = ta.load_gt(ta.DEFAULT_GT)
    doc = load(out)
    doc["rows"] = [r for r in doc["rows"] if r["role"] != "dev"]
    for wav in sorted(DEV_CORPUS.glob("*_12k8.wav")):
        yt = wav.name.split("_12k8")[0]
        g = gt.get(yt)
        if not g:
            print(f"no gold for {yt}; not added", file=sys.stderr)
            continue
        doc["rows"].append({"id": f"hx:{yt}", "path": str(wav), "sha256": sha256_file(wav),
                            "gold_bpm": float(g["bpm"]), "role": "dev", "genre": g.get("genre", ""),
                            "title": g.get("title", ""),
                            "source": f"HarmonixSet metadata.csv BPM via tempo_accuracy.load_gt({ta.DEFAULT_GT})",
                            "excerpt": {"start_ms": 0, "duration_ms": None}})
    save(out, doc)
    return 0


def add_heldout(rows_path: Path, out: Path) -> int:
    rows = json.loads(rows_path.read_text())
    doc = load(out)
    have = {r["id"] for r in doc["rows"]}
    for r in rows:
        for k in ("id", "path", "sha256", "gold_bpm", "role", "source"):
            if k not in r:
                raise SystemExit(f"row {r.get('id')!r} lacks {k}")
        if r["role"] != "heldout":
            raise SystemExit(f"row {r['id']!r} role {r['role']!r} != heldout")
        if r["id"] in have:
            raise SystemExit(f"row {r['id']!r} already present")
        doc["rows"].append(r)
    doc["heldout_rows_sha256"] = sha256_file(rows_path)
    save(out, doc)
    return 0


def verify(out: Path) -> int:
    doc = load(out)
    bad = 0
    for r in doc["rows"]:
        p = Path(r["path"])
        if not p.is_file() or sha256_file(p) != r["sha256"]:
            print(f"MISMATCH {r['id']} {p}")
            bad += 1
    print(f"verified rows={len(doc['rows'])} mismatches={bad}")
    return 1 if bad else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("build-dev", "add-heldout", "verify"):
        s = sub.add_parser(name)
        s.add_argument("--out", type=Path, default=DEFAULT_OUT)
        if name == "add-heldout":
            s.add_argument("--rows", type=Path, required=True)
    a = p.parse_args(argv)
    if a.cmd == "build-dev":
        return build_dev(a.out)
    if a.cmd == "add-heldout":
        return add_heldout(a.rows, a.out)
    return verify(a.out)


if __name__ == "__main__":
    sys.exit(main())
