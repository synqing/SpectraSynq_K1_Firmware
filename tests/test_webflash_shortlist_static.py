"""Static locks for the webflash home shortlist + MAC identity gate.

Captain 2026-08-26: three S3 homes only. Registry is the identity source.
The page must refuse unknown MACs and must not host ESP32-P4 images.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKE_MANIFEST = ROOT / "tools" / "webflash" / "make_manifest.py"
INDEX = ROOT / "tools" / "webflash" / "index.html"
README = ROOT / "tools" / "webflash" / "README.md"
IDENTITIES = ROOT / "scripts" / "platformio" / "k1_device_identities.json"
PIO_BUILD = ROOT / "scripts" / "agent" / "pio-build.sh"

HOMES = (
    "k1_main_rpl_im69d",
    "k1_bench_im69d_led150",
    "k1_unit2_im69d_right",
)

EXPECTED_CHIPS = {
    "k1_main_rpl_im69d": ("9087A500", "B4:3A:45:A5:87:90"),
    "k1_bench_im69d_led150": ("B489A500", "B4:3A:45:A5:89:B4"),
    "k1_unit2_im69d_right": ("0C54FC00", "AC:A7:04:FC:54:0C"),
}


def _assign(source: str, name: str):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"no assignment named {name} in make_manifest.py")


def test_curated_envs_are_the_three_s3_homes():
    src = MAKE_MANIFEST.read_text(encoding="utf-8")
    curated = _assign(src, "CURATED_ENVS")
    assert curated == list(HOMES)
    assert _assign(src, "SIMPLE_ENV") == "k1_main_rpl_im69d"
    assert "k1_hardware" not in curated
    assert not any(env.startswith("k1_p4_") for env in curated)


def test_labels_name_device_and_pin_fact():
    labels = _assign(MAKE_MANIFEST.read_text(encoding="utf-8"), "LABELS")
    assert "9087" in labels["k1_main_rpl_im69d"]
    assert "WS2816" in labels["k1_main_rpl_im69d"]
    assert "B489" in labels["k1_bench_im69d_led150"]
    assert "GPIO39/40" in labels["k1_bench_im69d_led150"]
    assert "0C54" in labels["k1_unit2_im69d_right"]
    assert "206" in labels["k1_unit2_im69d_right"]
    assert "CLK39" in labels["k1_unit2_im69d_right"]


def test_each_home_has_exactly_one_registry_chip():
    identities = json.loads(IDENTITIES.read_text(encoding="utf-8"))
    by_env: dict[str, list[dict]] = {env: [] for env in HOMES}
    for rec in identities["authorized"]:
        for env in rec.get("envs", []):
            if env in by_env:
                by_env[env].append(rec)
    for env, (chip, serial) in EXPECTED_CHIPS.items():
        recs = by_env[env]
        assert recs, f"{env} missing from k1_device_identities.json"
        chips = {r["chip_id"] for r in recs}
        serials = {r["usb_serial"] for r in recs}
        assert chips == {chip}, f"{env} chips {chips}"
        assert serials == {serial}, f"{env} serials {serials}"
    assert EXPECTED_CHIPS["k1_bench_im69d_led150"][1] != EXPECTED_CHIPS["k1_unit2_im69d_right"][1]


def test_manifest_writer_stamps_identity_from_registry():
    src = MAKE_MANIFEST.read_text(encoding="utf-8")
    assert "permittedChipIds" in src
    assert "k1_device_identities.json" in src
    assert "stamp_variant_identity" in src
    assert "unknownMac" in src
    assert '"refuse"' in src or "refuse" in src


def test_page_mac_gate_refuses_unknown_and_keeps_simple_on_main_rpl():
    page = INDEX.read_text(encoding="utf-8")
    assert "readMac" in page
    assert "identityVerdict" in page
    assert "Unknown chip. Public flasher refuses unregistered units." in page
    assert "const SIMPLE_ENV = \"k1_main_rpl_im69d\";" in page
    assert "state.simpleMode" in page
    assert "is not a webflash home; leaving the selected variant unchanged" in page
    assert "PAGE_VERSION = \"1.2.0\"" in page


def test_pio_build_wrapper_allows_all_three_homes():
    wrapper = PIO_BUILD.read_text(encoding="utf-8")
    for env in HOMES:
        assert env in wrapper
        assert re.search(rf'ALLOWED_ENVS="[^"]*{re.escape(env)}', wrapper), env
        assert re.search(rf"\|{re.escape(env)}\|", f"|{wrapper}|") or env in wrapper.split("case", 1)[-1]


def test_readme_says_identity_is_enforced():
    text = README.read_text(encoding="utf-8")
    assert "does **not** enforce `k1_upload_guard.py`" not in text
    assert "MAC" in text
    assert "CURATED_ENVS" in text
    assert "?mode=simple" in text
    assert "k1_unit2_im69d_right" in text
