"""Offline emulator LED report: native-value comparison and page safety.

The comparison must work on native 16-bit wire bytes aligned by
(hop, generation); the page must never present an incompatible or misaligned
pair as an equivalence and must reference no network resource.
"""
import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "tools" / "esp_emulator" / "report.py"
REAL_SAMPLE = Path("/private/tmp/claude-501/-Users-spectrasynq-Workspace-Management-Software-"
                   "SpectraSynq-ESP-Emulator/027d67cb-5535-4d8e-9b48-9ef6d5226cd6/scratchpad/"
                   "report-sample.json")

_spec = importlib.util.spec_from_file_location("esp_emulator_report", REPORT)
report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(report)

PX = 160


def _wire(seed: int) -> bytes:
    out = bytearray()
    for p in range(PX):
        for ch in range(3):
            v = (seed * 7919 + p * 131 + ch * 977) & 0xFFFF
            out += v.to_bytes(2, "big")
    return bytes(out)


def _case(case_id: str, hops, *, seed: int = 1) -> dict:
    frames = []
    for i, hop in enumerate(hops):
        frames.append({"index": i, "hop": hop, "generation": hop + 1, "admitted": (hop + 1) * 96,
                       "processed": (hop + 1) * 96, "app_us": 1_000_000 + hop * 7500, "mode": 3,
                       "limit_scale": 255, "power_mw": 0,
                       "A": _wire(seed + hop).hex(), "B": _wire(seed + 1000 + hop).hex()})
    return {"case": case_id, "status": "PASS", "reasons": [], "run_id": case_id + "-run",
            "profile": {"env": "k1_main_rpl_emu"}, "initial_state": {"flash": "blank"},
            "window": {"start_hop": 0, "end_hop": len(hops)}, "epoch_us": 1_000_000,
            "hop_samples": 96, "rate_hz": 12800, "pcm": {"id": "t", "sha256": "00"},
            "frames": frames, "commands": [], "show_states": []}


def _set_byte(case: dict, frame: int, edge: str, offset: int, value: int) -> None:
    w = bytearray(bytes.fromhex(case["frames"][frame][edge]))
    w[offset] = value
    case["frames"][frame][edge] = w.hex()


def _data(cases, comparisons) -> dict:
    return {"schema": "k1-emu-report-data/1",
            "invocation": {"id": "t", "overall": "PASS", "scenario": "unit", "source": {"head": "x"}},
            "cases": cases, "comparisons": comparisons}


def _comp(cid, kind, a, b, compatible=True):
    return {"id": cid, "kind": kind, "a": a, "b": b, "compatible": compatible,
            "status": "PASS", "detail": "", "strict": kind == "equal", "label": ""}


def _embedded_meta(html: str) -> dict:
    m = re.search(r'<script type="application/json" id="k1-meta">(.*?)</script>', html, re.S)
    assert m, "meta block missing"
    return json.loads(m.group(1))


# (a) identical pair -----------------------------------------------------------

def test_identical_pair_has_zero_differences():
    c = _case("base", range(12))
    r = report.compare_cases(c, copy.deepcopy(c))
    assert r["aligned_ok"] is True
    assert r["aligned_frames"] == 12
    assert r["only_in_a"] == r["only_in_b"] == 0
    assert r["diff_pixels_total"] == 0
    for e in ("A", "B"):
        assert r["edges"][e]["diff_frames"] == 0
        assert r["edges"][e]["diff_pixels"] == 0
    assert r["first_difference"] is None


# (b) exactly one native byte changed -------------------------------------------

def test_single_low_byte_change_is_located_with_native_values():
    base = _case("base", range(10))
    cand = copy.deepcopy(base)
    cand["case"] = "cand"
    frame, pixel = 6, 37
    off = pixel * 6 + 3                       # R low byte: a 1-LSB native change
    old = bytes.fromhex(base["frames"][frame]["B"])
    _set_byte(cand, frame, "B", off, old[off] ^ 0x01)

    # Precondition: the change is invisible in the 8-bit display projection.
    r16_old = old[pixel * 6 + 2] << 8 | old[pixel * 6 + 3]
    r16_new = r16_old ^ 0x01
    assert report.project8(r16_old) == report.project8(r16_new)

    r = report.compare_cases(base, cand)
    assert r["aligned_ok"] is True
    assert r["edges"]["A"]["diff_frames"] == 0 and r["edges"]["A"]["diff_pixels"] == 0
    assert r["edges"]["B"]["diff_frames"] == 1 and r["edges"]["B"]["diff_pixels"] == 1
    fd = r["first_difference"]
    assert (fd["hop"], fd["generation"], fd["edge"], fd["pixel"]) == (6, 7, "B", pixel)
    assert fd["a"]["r16"] == r16_old and fd["b"]["r16"] == r16_new
    g16 = old[pixel * 6] << 8 | old[pixel * 6 + 1]
    b16 = old[pixel * 6 + 4] << 8 | old[pixel * 6 + 5]
    assert fd["a"]["g16"] == fd["b"]["g16"] == g16
    assert fd["a"]["b16"] == fd["b"]["b16"] == b16
    assert [row[4:] for row in r["per_frame"] if row[4] or row[5]] == [[0, 1]]


def test_alignment_uses_hop_and_generation_not_list_position():
    base = _case("base", range(8))
    cand = copy.deepcopy(base)
    cand["case"] = "cand"
    cand["frames"].reverse()
    r = report.compare_cases(base, cand)
    assert r["aligned_ok"] is True and r["diff_pixels_total"] == 0


# (c) differing hop sets ---------------------------------------------------------

def test_differing_hop_sets_are_not_aligned_and_not_comparable(tmp_path):
    a = _case("base", range(10))
    b = _case("short", range(2, 10))
    for f in b["frames"]:                        # identical bytes on the shared hops
        f["A"] = next(x["A"] for x in a["frames"] if x["hop"] == f["hop"])
        f["B"] = next(x["B"] for x in a["frames"] if x["hop"] == f["hop"])
    r = report.compare_cases(a, b)
    assert r["aligned_ok"] is False
    assert r["only_in_a"] == 2 and r["only_in_b"] == 0
    assert any("hop sets differ" in s for s in r["alignment_reasons"])

    out = tmp_path / "r.html"
    report.write_report(_data([a, b], [_comp("eq", "equal", "base", "short")]), out)
    comp = _embedded_meta(out.read_text())["comparisons"][0]
    assert comp["state"] == "not_comparable"
    assert any("hop sets differ" in s for s in comp["state_reasons"])


def test_incompatible_flag_is_never_shown_as_equivalence(tmp_path):
    a = _case("base", range(6))
    b = copy.deepcopy(a)
    b["case"] = "twin"
    out = tmp_path / "r.html"
    report.write_report(_data([a, b], [_comp("eq", "equal", "base", "twin", compatible=False),
                                       _comp("eq2", "equal", "base", "twin")]), out)
    comps = _embedded_meta(out.read_text())["comparisons"]
    assert comps[0]["state"] == "not_comparable"
    assert any("incompatible" in s for s in comps[0]["state_reasons"])
    assert comps[1]["state"] == "equivalent"


def test_labelled_difference_is_never_an_equivalence(tmp_path):
    a = _case("base", range(6))
    b = copy.deepcopy(a)
    b["case"] = "ctl"
    _set_byte(b, 3, "A", 0, 0xFF)
    same = copy.deepcopy(a)
    same["case"] = "same"
    out = tmp_path / "r.html"
    report.write_report(_data([a, b, same], [_comp("lab", "labelled", "base", "ctl"),
                                             _comp("lab0", "labelled", "base", "same")]), out)
    comps = _embedded_meta(out.read_text())["comparisons"]
    assert comps[0]["state"] == "intended_difference"
    assert comps[1]["state"] == "labelled_difference_absent"


# (d) self-contained page --------------------------------------------------------

def test_html_has_no_network_references(tmp_path):
    a = _case("base", range(4))
    a["profile"]["note"] = "see https://example.invalid/x and http://example.invalid/y"
    out = tmp_path / "r.html"
    report.write_report(_data([a], []), out)
    html = out.read_text()
    assert "http://" not in html and "https://" not in html
    assert not re.search(r"<(link|img|iframe)\b", html, re.I)
    assert not re.search(r"<script[^>]*\bsrc=", html, re.I)
    assert "@import" not in html and "url(" not in html
    # The URL text is still carried as data, only made inert.
    assert _embedded_meta(html)["cases"][0]["profile"]["note"].startswith("see https://")


def test_cli_writes_report(tmp_path):
    data_path = tmp_path / "d.json"
    data_path.write_text(json.dumps(_data([_case("base", range(3))], [])))
    out = tmp_path / "o.html"
    assert report.main([str(data_path), str(out)]) == 0
    assert out.stat().st_size > 0


# real sample --------------------------------------------------------------------

@pytest.mark.skipif(not REAL_SAMPLE.exists(), reason="real emulator sample not present")
def test_real_sample_comparisons(tmp_path):
    data = json.loads(REAL_SAMPLE.read_text())
    cases = {c["case"]: c for c in data["cases"]}
    base = cases["smoke-base"]
    assert report.compare_cases(base, base)["diff_pixels_total"] == 0

    r = report.compare_cases(base, cases["ctl-a"])
    assert r["aligned_ok"] and r["aligned_frames"] == len(base["frames"])
    assert r["edges"]["B"]["diff_pixels"] == 0
    assert r["edges"]["A"]["diff_pixels"] > 0
    assert r["first_difference"]["edge"] == "A" and r["first_difference"]["hop"] >= 40
    assert all(row[0] >= 40 for row in r["per_frame"] if row[4])

    r = report.compare_cases(base, cases["ctl-b"])
    assert r["edges"]["A"]["diff_pixels"] == 0 and r["edges"]["B"]["diff_pixels"] > 0

    out = tmp_path / "real.html"
    report.write_report(data, out)
    html = out.read_text()
    assert "http://" not in html and "https://" not in html
    comps = {c["id"]: c for c in _embedded_meta(html)["comparisons"]}
    assert comps["ctl-a-vs-base"]["state"] == "intended_difference"
    assert comps["ctl-b-vs-base"]["state"] == "intended_difference"
