"""I3 / I10 gate (lane R1, DEF-001 / DEF-002): every fixed constant the tempo tracker gates on lives
once, in audio/k1_tempo_spec.h, with a well-formed provenance line whose value matches the code.

Both truth values: the committed header must pass; deliberately broken headers must fail.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo_spec.h"
TEMPO = ROOT / "SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp"

pytestmark = pytest.mark.tempo_gates

PROV = re.compile(r"^// @prov (K1_[A-Z0-9_]+) value=(\S+) mic=(\S+) fixture=([0-9a-f]{64}|UNPROVENANCED) "
                  r"date=(\d{4}-\d{2}-\d{2}) tuned_on=(.+)$")
DEFINE = re.compile(r"^#define (K1_[A-Z0-9_]+)\s+(\S+)")
STATIC = re.compile(r"^static const \w+\s+(K1_[A-Z0-9_]+)\s*=\s*([^;]+);")


def _num(text: str) -> float:
    return float(text.rstrip("fFuU"))


def check_spec(text: str) -> list[str]:
    """Return the list of violations (empty = compliant)."""
    errors, prov = [], {}
    for ln in text.splitlines():
        if ln.startswith("// @prov"):
            m = PROV.match(ln)
            if not m:
                errors.append(f"malformed @prov line: {ln[:80]}")
                continue
            if m.group(1) in prov:
                errors.append(f"duplicate @prov for {m.group(1)}")
            prov[m.group(1)] = m.group(2)
    defined = {}
    for ln in text.splitlines():
        m = DEFINE.match(ln) or STATIC.match(ln)
        if m:
            sym, val = m.group(1), m.group(2).strip()
            if sym in defined:
                errors.append(f"{sym} defined twice in the spec header")
            defined[sym] = val
    for sym, val in defined.items():
        if sym not in prov:
            errors.append(f"{sym} has no @prov line (I3: a threshold without provenance is a defect)")
        elif abs(_num(val) - _num(prov[sym])) > 1e-9:
            errors.append(f"{sym}: code value {val} != @prov value {prov[sym]}")
    for sym in prov:
        if sym not in defined:
            errors.append(f"@prov for {sym} but no definition")
    return errors


def check_tempo_cpp(cpp: str, spec_symbols: set[str]) -> list[str]:
    errors = []
    if '#include "k1_tempo_spec.h"' not in cpp:
        errors.append("k1_tempo.cpp does not include k1_tempo_spec.h")
    for ln in cpp.splitlines():
        m = DEFINE.match(ln.strip()) or STATIC.match(ln.strip())
        if m and m.group(1) in spec_symbols:
            errors.append(f"k1_tempo.cpp redefines spec constant {m.group(1)} (constants live once)")
    return errors


def _symbols(text: str) -> set[str]:
    return {m.group(1) for ln in text.splitlines() if (m := DEFINE.match(ln) or STATIC.match(ln))}


def test_committed_spec_header_is_compliant():
    text = SPEC.read_text()
    assert check_spec(text) == []
    assert len(_symbols(text)) >= 30


def test_tempo_cpp_reads_constants_only_from_the_spec_header():
    assert check_tempo_cpp(TEMPO.read_text(), _symbols(SPEC.read_text())) == []


def test_lock_threshold_records_that_it_was_never_calibrated_on_the_product_mic():
    line = next(ln for ln in SPEC.read_text().splitlines() if ln.startswith("// @prov K1_LOCK_CONFIDENCE "))
    assert "IM69D" in line and "fixture=UNPROVENANCED" in line


@pytest.mark.parametrize("mutation", [
    ("// @prov K1_LOCK_CONFIDENCE ", "// @prov K1_LOCK_CONFIDENCX "),              # provenance missing
    ("K1_LOCK_CONFIDENCE = 0.60f;", "K1_LOCK_CONFIDENCE = 0.28f;"),                 # retuned by digit
    ("fixture=UNPROVENANCED date=2026-06-03 tuned_on=host tempo_replay", "fixture=TBD date=2026-06-03 tuned_on=host tempo_replay"),
])
def test_broken_spec_headers_fail(mutation):
    text = SPEC.read_text()
    old, new = mutation
    assert text.count(old) == 1, old
    assert check_spec(text.replace(old, new)) != []


def test_constant_redefined_in_cpp_fails():
    spec_syms = _symbols(SPEC.read_text())
    cpp = TEMPO.read_text() + "\nstatic const float K1_LOCK_CONFIDENCE = 0.28f;\n"
    assert check_tempo_cpp(cpp, spec_syms) != []
