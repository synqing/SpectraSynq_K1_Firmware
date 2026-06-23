#!/usr/bin/env python3
"""PREFERRED headless export: execute notebooks/audio_semantic_diagnostics.ipynb with
nbconvert (real kernel) once per RUN_MODE and write the three HTML files:

  build/audio-semantic-visuals/{baseline,final,ab_diff}/index.html

papermill is absent, so RUN_MODE / TRACK_ID are injected by a tiny param override:
the notebook's `parameters`-tagged cell is rewritten in a temp copy before execution
(the same mechanism papermill uses, minus the dependency). The notebook itself is
unchanged on disk. Execution uses whichever Jupyter kernel has numpy + matplotlib +
ipykernel (default: the `nerf-diag` kernel registered from the nerfstudio conda env).

This is run BY the miniforge jupyter (which has nbconvert); it dispatches to the
chosen kernel. If no such kernel exists, fall back to render_diagnostics.py.

Run (note: invoked via the miniforge jupyter's python, see render docs):
  python3 scripts/regression-harness/render_via_nbconvert.py --kernel nerf-diag --track 7vevOMWY6MY
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parents[1]
NB = ROOT / "notebooks" / "audio_semantic_diagnostics.ipynb"
OUT_BASE = ROOT / "build" / "audio-semantic-visuals"
RUN_DIR = {"baseline": "baseline", "final": "final", "ab": "ab_diff"}
DEFAULT_TRACK = "7vevOMWY6MY"

# nbconvert binary (miniforge has it); overridable
DEFAULT_NBCONVERT = str(Path.home() / "miniforge3" / "bin" / "jupyter-nbconvert")


def inject_params(nb_json, run_mode, track_id, apstream_path):
    """Rewrite the `parameters`-tagged cell to set RUN_MODE/TRACK_ID/APSTREAM_PATH."""
    # use repr() so Python literals (None, str) are emitted, NOT JSON (null)
    inject = [
        f'TRACK_ID = {track_id!r}\n',
        f'RUN_MODE = {run_mode!r}\n',
        'TIME_WINDOW_S = None\n',
        'BEAT_TOL_MS = 70\n',
        'SHOW_GT = True\n',
        'SHOW_BEAT_TICK = True\n',
        f'SHOW_APSTREAM = {bool(apstream_path)!r}\n',
        f'APSTREAM_PATH = {apstream_path!r}\n',
        'CONF_RAW_VS_SMOOTH = True\n',
        'BEAT_RAW_VS_DEDUP = "dedup"\n',
        'NORMALIZE_NOVELTY = True\n',
    ]
    for cell in nb_json.get("cells", []):
        if cell.get("cell_type") == "code" and "parameters" in cell.get("metadata", {}).get("tags", []):
            cell["source"] = inject
            return True
    return False


def render_one(run_mode, track_id, apstream_path, kernel, nbconvert_bin, timeout):
    nb_json = json.loads(NB.read_text(encoding="utf-8"))
    if not inject_params(nb_json, run_mode, track_id, apstream_path):
        print("  WARN: no parameters-tagged cell found; running notebook defaults", file=sys.stderr)
    out_dir = OUT_BASE / RUN_DIR[run_mode]
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        tmp_nb = Path(td) / f"diag_{run_mode}.ipynb"
        tmp_nb.write_text(json.dumps(nb_json), encoding="utf-8")
        cmd = [
            nbconvert_bin, "--to", "html", "--execute",
            "--ExecutePreprocessor.kernel_name=" + kernel,
            f"--ExecutePreprocessor.timeout={timeout}",
            "--output", "index", "--output-dir", str(out_dir),
            str(tmp_nb),
        ]
        import os
        env = {**os.environ, "DIAG_REPO_ROOT": str(ROOT)}
        r = subprocess.run(cmd, text=True, capture_output=True,
                           cwd=str(ROOT / "notebooks"), env=env)
        out_path = out_dir / "index.html"
        ok = r.returncode == 0 and out_path.exists()
        if not ok:
            print(f"  FAILED ({run_mode}):\n{r.stderr[-2000:]}", file=sys.stderr)
        return ok, out_path, r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--track", default=DEFAULT_TRACK)
    ap.add_argument("--apstream", default=None)
    ap.add_argument("--kernel", default="nerf-diag")
    ap.add_argument("--nbconvert", default=DEFAULT_NBCONVERT)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--run", action="append", default=[], choices=list(RUN_DIR))
    args = ap.parse_args(argv)

    runs = args.run or ["baseline", "final", "ab"]
    all_ok = True
    for rm in runs:
        ok, path, _r = render_one(rm, args.track, args.apstream,
                                  args.kernel, args.nbconvert, args.timeout)
        if ok:
            print(f"  [{rm:8}] -> {path}  ({path.stat().st_size} bytes)")
        else:
            all_ok = False
    print(f"\nnbconvert export {'OK' if all_ok else 'INCOMPLETE'} -> {OUT_BASE}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
