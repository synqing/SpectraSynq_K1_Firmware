"""Executable contract for the isolated Preview R1.1 mockup."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "tools" / "colourlab" / "mockups" / "preview-r1.1" / "index.html"

BOOT = r"""
const fs = require("fs");
const html = fs.readFileSync(process.env.PREVIEW_R11_HTML, "utf8");
const found = html.match(/<script id="previewModel">([\s\S]*?)<\/script>/);
if (!found) throw new Error("previewModel script not found");
const moduleBox = { exports: {} };
const runner = new Function("module", "exports", found[1] + "\nreturn module.exports;");
const api = runner(moduleBox, moduleBox.exports);
let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => raw += chunk);
process.stdin.on("end", () => {
  try { process.stdout.write(JSON.stringify(api.dispatch(JSON.parse(raw)))); }
  catch (error) { process.stderr.write(String(error.stack || error)); process.exit(2); }
});
"""


def call_model(payload: dict) -> dict:
    node = shutil.which("node")
    assert node, "node is required"
    environment = os.environ.copy()
    environment["PREVIEW_R11_HTML"] = str(HTML)
    result = subprocess.run(
        [node, "-e", BOOT],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def source() -> str:
    assert HTML.is_file()
    return HTML.read_text(encoding="utf-8")


def test_preview_is_read_only_and_uses_the_approved_operator_language():
    html = source()
    assert "<h2 id=\"previewTitle\">Preview</h2>" in html
    assert "Compare Primary and Secondary before testing changes on K1." in html
    assert "Not device readback, LUT readback or a physical colour match." in html
    assert "Review Tune" in html
    assert 'nextHref: "../../index.html#tuneTitle"' in html
    assert 'state.nextHref = "../../index.html#deviceTitle"' in html
    assert 'state.nextHref = "../../index.html#sourceTitle"' in html
    assert 'data-scenario-link="slotUnknown"' in html
    assert 'data-scenario-link="slotUnknownDirect"' in html
    for mutation in ("Test on device", "Apply tune", "Save slot", "Apply all"):
        assert mutation not in html


def test_preview_contains_no_prohibited_wheel_spanning_surface_terms():
    lowered = source().lower()
    for forbidden in ("rainbow", "hue wheel", "full spectrum", "full-spectrum"):
        assert forbidden not in lowered


def test_inherit_15_resolves_inside_secondary_frame_without_collapsing_authority():
    result = call_model({"op": "scenario", "name": "inherit15"})
    assert result["primary"]["channel"] == "primary"
    assert result["secondary"]["channel"] == "secondary"
    assert result["primary"]["framingKind"] == "device_effective"
    assert result["secondary"]["framingKind"] == "device_effective"
    assert result["secondary"]["lookResolution"] == {
        "relation": "inherit",
        "reported": "inherit",
        "effectiveKnown": True,
        "effectiveSlot": 15,
        "inheritedFrom": "primary",
    }
    assert result["comparison"]["output"]["status"] == "match"
    assert result["comparison"]["basis"] == {
        "status": "differ",
        "reasons": ["look_relationship"],
    }
    assert result["primary"]["pixels"] is not result["secondary"]["pixels"]


def test_inherit_non15_uses_known_session_simulation_without_device_claim():
    result = call_model({"op": "scenario", "name": "inherit0"})
    assert result["primary"]["framingKind"] == "simulate_session"
    assert result["secondary"]["framingKind"] == "simulate_session"
    assert result["secondary"]["lookResolution"]["effectiveSlot"] == 0
    assert "not modelled" in result["secondary"]["correctionText"]


def test_unknown_primary_with_secondary_inherit_fails_closed():
    result = call_model({"op": "scenario", "name": "inheritUnknown"})
    assert result["primary"]["selection"] == "pre"
    assert result["secondary"]["selection"] == "pre"
    assert result["secondary"]["lookResolution"]["effectiveKnown"] is False
    assert result["secondary"]["lookResolution"]["effectiveSlot"] is None
    assert result["secondary"]["correctionText"] == "Inherits Primary look · Primary look unknown"


def test_slot_knowledge_unknown_keeps_direct_and_inherited_frames_pre_correction():
    result = call_model({"op": "scenario", "name": "slotUnknown"})
    assert result["primary"]["selection"] == "pre"
    assert result["secondary"]["selection"] == "pre"
    assert result["primary"]["tune"] is None
    assert result["secondary"]["tune"] is None
    assert result["primary"]["correctionText"] == "Before correction · slot-15 contents unknown"
    assert result["secondary"]["correctionText"] == "Inherits Primary look · slot-15 contents unknown"
    assert "tune" not in result["primary"]["correctionText"].lower()
    assert "tune" not in result["secondary"]["correctionText"].lower()
    assert result["comparison"]["output"]["status"] == "match"
    assert result["comparison"]["basis"]["reasons"] == ["look_relationship"]


def test_slot_knowledge_unknown_with_direct_secondary_never_claims_a_simulation():
    result = call_model({"op": "scenario", "name": "slotUnknownDirect"})
    for frame in (result["primary"], result["secondary"]):
        assert frame["selection"] == "pre"
        assert frame["tune"] is None
        assert frame["correctionText"] == "Before correction · slot-15 contents unknown"
        assert "confirmed tune" not in frame["correctionText"].lower()
        assert "known tune simulation" not in frame["correctionText"].lower()
    assert result["comparison"]["output"]["status"] == "match"
    assert result["comparison"]["basis"]["status"] == "match"


def test_equal_output_does_not_promote_unequal_basis():
    inherited = call_model({"op": "scenario", "name": "inherit15"})
    assert inherited["comparison"]["output"]["differingLedCount"] == 0
    assert inherited["comparison"]["basis"]["status"] == "differ"


def test_output_and_basis_can_report_independently():
    perturbed = call_model({"op": "scenario", "name": "outputDiffer"})
    assert perturbed["comparison"]["output"]["status"] == "differ"
    assert perturbed["comparison"]["output"]["differingLedCount"] == 1
    assert perturbed["comparison"]["basis"]["status"] == "differ"  # inherit relation remains distinct


def test_different_led_counts_are_geometry_difference():
    result = call_model({"op": "scenario", "name": "geometry"})
    output = result["comparison"]["output"]
    assert output["status"] == "differ"
    assert output["primaryLedCount"] == 150
    assert output["secondaryLedCount"] == 140
    assert output["unmatchedLedCount"] == 10
    assert "led_count" in output["reasons"]


def test_shared_inspector_is_one_state_and_reads_each_cached_frame():
    html = source()
    boot = html.split('<script id="previewModel">', 1)[1]
    assert len(re.findall(r"\bvar selectedLed\s*=", boot)) == 1
    assert "function setSelectedLed(candidate, inputKind, announce)" in html
    assert 'type="number"' in html
    assert 'step="1"' in html
    assert "Model.inspectFrame(stageFrames.primary, selectedLed)" in html
    assert "Model.inspectFrame(stageFrames.secondary, selectedLed)" in html
    assert "getImageData" not in html


def test_view_choice_and_inspector_have_semantic_controls():
    html = source()
    assert '<fieldset class="view-choice">' in html
    assert len(re.findall(r'<input[^>]+name="previewView"', html)) == 2
    assert 'aria-live="polite"' in html
    assert '<table class="inspector-values"' in html
    assert 'scope="row">Primary' in html
    assert 'scope="row">Secondary' in html
