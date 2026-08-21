"""Static ratchets for K1_WS2816_LEVER2_V1 isolation.

Shippable envs must not define the flag. Main RPL bring-up
(k1_main_rpl_im69d) is the named carrier. Palette HD V2 stays off.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INI = (ROOT / "platformio.ini").read_text(encoding="utf-8")
MANIFEST = json.loads(
    (ROOT / "scripts" / "platformio" / "k1_device_identities.json").read_text(
        encoding="utf-8"
    )
)

FLAG = "K1_WS2816_LEVER2_V1"
DEGAMMA_FLAG = "K1_WS2816_DEGAMMA_V1"
LOOK_FLAG = "K1_LOOK_LIB_V1"
HD_FLAG = "K1_PALETTE_HD_V2"
SHIPPABLE_ENVS = {"k1_hardware", "k1_prod_im73d", "k1_bench_reference"}


def _sections():
    out = {}
    for m in re.finditer(r"^\[env:([^\]]+)\]\n(.*?)(?=^\[|\Z)", INI, re.M | re.S):
        out[m.group(1)] = m.group(2)
    return out


def _effective_flags(env, sections, seen=None):
    seen = seen or set()
    if env in seen or env not in sections:
        return set()
    seen.add(env)
    body = sections[env]
    uncommented = "\n".join(
        l for l in body.splitlines() if not l.lstrip().startswith(("#", ";"))
    )
    flags = set(re.findall(r"-D([A-Za-z0-9_]+)", uncommented))
    ext = re.search(r"^extends\s*=\s*env:([^\s]+)", body, re.M)
    if ext:
        flags |= _effective_flags(ext.group(1), sections, seen)
    return flags


def test_default_envs_unchanged():
    m = re.search(r"(?m)^default_envs\s*=\s*(\S+)", INI)
    assert m, "default_envs missing"
    assert m.group(1) == "k1_hardware"


def test_lever2_env_exists_and_carries_flag():
    sections = _sections()
    assert "k1_main_rpl_im69d" in sections
    body = sections["k1_main_rpl_im69d"]
    assert re.search(r"^extends\s*=\s*env:k1_hardware\s*$", body, re.M)
    have = _effective_flags("k1_main_rpl_im69d", sections)
    assert FLAG in have
    assert LOOK_FLAG in have
    assert DEGAMMA_FLAG not in have
    assert HD_FLAG not in have
    assert "PalettesHD_RangeV2.cpp" not in body
    assert "k1_ws2816_lever2" not in sections


def test_shippable_envs_do_not_define_lever2():
    sections = _sections()
    banned = {FLAG, DEGAMMA_FLAG, LOOK_FLAG, HD_FLAG}
    leaks = {
        env: sorted(_effective_flags(env, sections) & banned)
        for env in SHIPPABLE_ENVS
        if env in sections and (_effective_flags(env, sections) & banned)
    }
    assert leaks == {}, f"eval flags leaked into shippable envs: {leaks}"


def test_lever2_eval_env_is_not_reintroduced():
    assert "k1_ws2816_lever2" not in MANIFEST.get("blocked_envs", [])
    assert "k1_ws2816_lever2" not in {
        env
        for row in MANIFEST.get("authorized", [])
        for env in row.get("envs", [])
    }
