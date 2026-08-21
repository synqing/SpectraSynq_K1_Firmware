"""Host replica of 17³ trilinear look cubes (Phase C)."""

from __future__ import annotations

from typing import List, Sequence, Tuple

N = 17
MAX_U16 = 65535


def _lerp_u16(a: int, b: int, t: int) -> int:
    if t <= 0:
        return a
    if t >= 65535:
        return b
    if b >= a:
        num = (b - a) * t
        return a + ((num + 32768) >> 16)
    num = (a - b) * t
    return a - ((num + 32768) >> 16)


def cube_index(v: int) -> Tuple[int, int, int]:
    scaled = v * 16
    lo = scaled // 65535
    if lo >= 16:
        return 16, 16, 0
    return lo, lo + 1, scaled % 65535


def identity_node(i: int, j: int, k: int) -> Tuple[int, int, int]:
    return (
        int(round(i * MAX_U16 / 16)),
        int(round(j * MAX_U16 / 16)),
        int(round(k * MAX_U16 / 16)),
    )


def proof_node(i: int, j: int, k: int) -> Tuple[int, int, int]:
    """Teal–orange split: reds warmer, cyans cooler. Not a measured plate."""
    r, g, b = identity_node(i, j, k)
    r2 = min(MAX_U16, r + (MAX_U16 - b) // 8)
    b2 = min(MAX_U16, b + (MAX_U16 - r) // 8)
    return r2, g, b2


def build_cube(node_fn) -> List[int]:
    out: List[int] = []
    for i in range(N):
        for j in range(N):
            for k in range(N):
                r, g, b = node_fn(i, j, k)
                out.extend((r, g, b))
    return out


def _node(lattice: Sequence[int], i: int, j: int, k: int) -> Tuple[int, int, int]:
    idx = (i * N * N + j * N + k) * 3
    return lattice[idx], lattice[idx + 1], lattice[idx + 2]


def apply_cube17(r: int, g: int, b: int, lattice: Sequence[int]) -> Tuple[int, int, int]:
    r0, r1, fr = cube_index(r)
    g0, g1, fg = cube_index(g)
    b0, b1, fb = cube_index(b)

    def n(i, j, k):
        return _node(lattice, i, j, k)

    c000 = n(r0, g0, b0)
    c001 = n(r0, g0, b1)
    c010 = n(r0, g1, b0)
    c011 = n(r0, g1, b1)
    c100 = n(r1, g0, b0)
    c101 = n(r1, g0, b1)
    c110 = n(r1, g1, b0)
    c111 = n(r1, g1, b1)
    out = []
    for c in range(3):
        c00 = _lerp_u16(c000[c], c100[c], fr)
        c01 = _lerp_u16(c001[c], c101[c], fr)
        c10 = _lerp_u16(c010[c], c110[c], fr)
        c11 = _lerp_u16(c011[c], c111[c], fr)
        c0 = _lerp_u16(c00, c10, fg)
        c1 = _lerp_u16(c01, c11, fg)
        out.append(_lerp_u16(c0, c1, fb))
    return out[0], out[1], out[2]


IDENTITY_CUBE = build_cube(identity_node)
PROOF_CUBE = build_cube(proof_node)
