"""Execute shipped tools/colourlab/colourlab-core.js via Node.

Python supplies fixtures and expected values from tests/colour_lab.py.
It must not re-implement the shipped parser, store, or render path.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "tools" / "colourlab" / "colourlab-core.js"

_BOOTSTRAP = r"""
const path = require("path");
const core = require(process.env.COLOURLAB_CORE);
let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (c) => { raw += c; });
process.stdin.on("end", () => {
  try {
    const req = JSON.parse(raw);
    const out = core.dispatch(req);
    process.stdout.write(JSON.stringify(out));
  } catch (err) {
    process.stderr.write(String(err && err.stack ? err.stack : err));
    process.exit(2);
  }
});
"""


def node_bin() -> str:
    found = shutil.which("node")
    if not found:
        raise RuntimeError("node is required to execute colourlab-core.js")
    return found


def call_core(payload: dict) -> dict:
    env = os.environ.copy()
    env["COLOURLAB_CORE"] = str(CORE)
    proc = subprocess.run(
        [node_bin(), "-e", _BOOTSTRAP],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"node colourlab-core.js failed ({proc.returncode}): {proc.stderr}"
        )
    if not proc.stdout:
        raise AssertionError(f"node produced no stdout; stderr={proc.stderr}")
    return json.loads(proc.stdout)


def require_core() -> Path:
    assert CORE.is_file(), f"missing shipped core: {CORE}"
    return CORE
