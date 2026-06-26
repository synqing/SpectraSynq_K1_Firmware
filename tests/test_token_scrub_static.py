"""N3 token-scrub — static invariant gate.

The Tab5 wireless control-token macro `K1_CONTROL_TOKEN` must be defined ONLY in the
env that consumes it — `env:k1_wireless_ab_probe`, the sole `SB_K1_WIRELESS_ENABLED`
build and the only one whose `build_src_filter` compiles `network/sb_k1_wireless.cpp`.
It must NOT be defined in the production `env:k1_hardware` (nor, by inheritance, the
~50 probe/harness/bench envs that chain off it), where it has no consumer and was
already dead-stripped from the binary.

This gate pins the scrub: moving the `-D` back into `[env:k1_hardware]` makes
`test_token_absent_from_production_env` go RED. (Production *byte-identity* is proven
separately by the build itself — identical `.flash.text`/`.iram0.text`/`.dram0.data`
section hashes + identical size + `strings | grep k1-tab5 == 0` — see the N3 PR.)
"""
import re
from pathlib import Path

PLATFORMIO_INI = Path(__file__).resolve().parents[1] / "platformio.ini"


def _build_flags(env: str) -> str:
    """Return the `build_flags` block of `[env:<env>]` with inline `;` comments
    stripped. Line-based (not configparser) so platformio's `${env:...}`
    interpolation and multi-line flag lists parse predictably."""
    in_section = False
    in_flags = False
    out = []
    for ln in PLATFORMIO_INI.read_text(encoding="utf-8").splitlines():
        if ln.startswith("["):
            in_section = ln.strip() == f"[env:{env}]"
            in_flags = False
            continue
        if not in_section:
            continue
        if re.match(r"^build_flags\s*=", ln):
            in_flags = True
            continue
        if in_flags:
            if ln and not ln[0].isspace():  # next top-level key ends the block
                in_flags = False
            else:
                out.append(ln.split(";", 1)[0])  # drop inline comment
    return "\n".join(out)


def test_token_absent_from_production_env():
    """The production env must NOT define the wireless control token."""
    assert "-DK1_CONTROL_TOKEN" not in _build_flags("k1_hardware"), (
        "K1_CONTROL_TOKEN must NOT be defined in [env:k1_hardware] (production): it "
        "has no consumer there (network/sb_k1_wireless.cpp is not compiled into prod) "
        "and was dead-stripped. N3 scoped the credential macro to the wireless env."
    )


def test_token_present_in_wireless_env():
    """The wireless env (the only consumer) must define the token directly."""
    assert "-DK1_CONTROL_TOKEN" in _build_flags("k1_wireless_ab_probe"), (
        "K1_CONTROL_TOKEN must be defined in [env:k1_wireless_ab_probe] — the only "
        "SB_K1_WIRELESS_ENABLED build that compiles network/sb_k1_wireless.cpp. After "
        "the scrub it no longer reaches this env via k1_hardware inheritance, so it "
        "must be set on this env directly."
    )
