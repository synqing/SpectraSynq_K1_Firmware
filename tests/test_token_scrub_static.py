"""N3 token-scrub — static invariant gate.

The Tab5 wireless control-token macro `K1_CONTROL_TOKEN` must be defined ONLY in the
env that consumes it — `env:k1_wireless_ab_probe`, the sole `K1_WIRELESS_ENABLED`
build and the only one whose `build_src_filter` compiles `network/k1_wireless.cpp`.
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
        "has no consumer there (network/k1_wireless.cpp is not compiled into prod) "
        "and was dead-stripped. N3 scoped the credential macro to the wireless env."
    )


def test_token_present_in_wireless_env():
    """The wireless env (the only consumer) must define the token directly."""
    assert "-DK1_CONTROL_TOKEN" in _build_flags("k1_wireless_ab_probe"), (
        "K1_CONTROL_TOKEN must be defined in [env:k1_wireless_ab_probe] — the only "
        "K1_WIRELESS_ENABLED build that compiles network/k1_wireless.cpp. After "
        "the scrub it no longer reaches this env via k1_hardware inheritance, so it "
        "must be set on this env directly."
    )


# ── N3 hardening (2026-06-27): pin the invariant that actually keeps the token
# out of prod — the wireless CONSUMER is not compiled into [env:k1_hardware].
# The token-location checks above are a proxy; this is the binary-truth
# precondition. Even with the -D scrubbed, if network/ is added to the prod
# build_src_filter the in-source #ifndef fallback ("k1-tab5",
# network/k1_wireless.cpp:37) would link into production and ship.


def _src_filter(env: str) -> str:
    """Return the `build_src_filter` block of `[env:<env>]` (inline value after
    `=` plus indented continuation lines), inline `;` comments stripped."""
    in_section = False
    in_filter = False
    out = []
    for ln in PLATFORMIO_INI.read_text(encoding="utf-8").splitlines():
        if ln.startswith("["):
            in_section = ln.strip() == f"[env:{env}]"
            in_filter = False
            continue
        if not in_section:
            continue
        if re.match(r"^build_src_filter\s*=", ln):
            in_filter = True
            out.append(ln.split("=", 1)[1].split(";", 1)[0])  # inline remainder
            continue
        if in_filter:
            if ln and not ln[0].isspace():  # next top-level key ends the block
                in_filter = False
            else:
                out.append(ln.split(";", 1)[0])
    return "\n".join(out)


def test_production_build_filter_excludes_wireless_consumer():
    """Production must NOT compile the wireless control source. This is the real
    'token never ships' guarantee — stronger than the -D location check."""
    prod = _src_filter("k1_hardware")
    assert "network/k1_" not in prod and "<network/" not in prod, (
        "[env:k1_hardware] build_src_filter now compiles network/ sources — the "
        "wireless control consumer (network/k1_wireless.cpp) would link into "
        "production and its hardcoded 'k1-tab5' #ifndef fallback would ship even "
        "with the -D scrubbed. Keep network/ out of the production filter; it "
        "belongs only in env:k1_wireless_ab_probe."
    )


def test_wireless_env_compiles_the_consumer():
    """Counterpart: the only wireless env MUST compile the consumer, else the
    token is configured into a build that never links its sole user."""
    wl = _src_filter("k1_wireless_ab_probe")
    assert "network/k1_" in wl or "<network/" in wl, (
        "[env:k1_wireless_ab_probe] must compile network/k1_*.cpp — it is the only "
        "env that links the wireless control consumer the token authenticates."
    )
