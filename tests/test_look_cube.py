"""Host tests for 17³ trilinear look cubes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from look_cube import IDENTITY_CUBE, PROOF_CUBE, apply_cube17, identity_node  # noqa: E402


def test_identity_cube_nodes_match_coordinates():
    for i in (0, 8, 16):
        for j in (0, 8, 16):
            for k in (0, 8, 16):
                idx = (i * 17 * 17 + j * 17 + k) * 3
                assert tuple(IDENTITY_CUBE[idx : idx + 3]) == identity_node(i, j, k)


def test_identity_cube_apply_within_one_code():
    samples = [0, 1, 61, 4096, 32768, 40000, 65534, 65535]
    for r in samples:
        for g in (0, 32768, 65535):
            for b in (0, 8000, 65535):
                out = apply_cube17(r, g, b, IDENTITY_CUBE)
                assert abs(out[0] - r) <= 1
                assert abs(out[1] - g) <= 1
                assert abs(out[2] - b) <= 1


def test_proof_cube_is_not_identity():
    r, g, b = apply_cube17(50000, 8000, 4000, PROOF_CUBE)
    ir, ig, ib = apply_cube17(50000, 8000, 4000, IDENTITY_CUBE)
    assert (r, g, b) != (ir, ig, ib)


def test_firmware_cube_apply_is_not_boot_default():
    look_h = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_look.h"
    src = look_h.read_text(encoding="utf-8")
    assert "k1_look_apply_cube17" in src
    assert "k1_look_table[8].type = K1_LOOK_CUBE_17" in src
    boot = src[src.index("k1_look_boot_from_config") :]
    # Live slot still comes from CONFIG.LOOK (default 0), not the proof slot.
    assert "k1_look_publish(look)" in boot
    assert "k1_look_slot = 8" not in src
