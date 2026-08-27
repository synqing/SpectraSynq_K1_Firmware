"""Static production contracts for the greenfield Colour Lab Workbench."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "tools" / "colourlab" / "index.html"
PARITY_TWIN = ROOT / "tools" / "colourlab" / "workbench.html"
APP = ROOT / "tools" / "colourlab" / "colourlab-workbench.js"
AUTHORING = ROOT / "tools" / "colourlab" / "colourlab-authoring.js"


def test_workbench_uses_production_modules_not_mockup_maths():
    html = HTML.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    assert '<script src="colourlab-core.js"></script>' in html
    assert '<script src="colourlab-authoring.js"></script>' in html
    assert '<script src="colourlab-workbench.js"></script>' in html
    assert "function hslToRgb" not in html + app
    assert "function tune(" not in html + app
    assert "function mix(" not in html + app
    assert "Proposal only" not in html + app
    assert "Device confirmed — device-reported LUT" not in html + app
    assert "CL.buildRgb1d" in app
    assert "CA.compilePaintStops" in app
    assert "CA.samplePalette" in app
    assert HTML.read_bytes() == PARITY_TWIN.read_bytes()


def test_no_full_hue_path_is_selectable_sendable_or_exportable():
    html = HTML.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    combined = html + app
    assert 'data-stimulus="ramp"' not in combined
    assert 'data-stimulus="spectrum"' not in combined
    assert "CL.serialize.paintSv" not in app
    assert 'CL.serialize.paint("ramp")' not in app
    assert 'type="color"' not in html + app
    assert "previewPaint" not in app
    assert "chromaticPathProhibited(bundle.policy)" in app
    assert "CA.prohibitsChromaticDisplay" in app
    assert "suppressChromaticPath" in app
    assert "all colour pixels suppressed" in app
    assert "exportAllowed" in app


def test_mode_target_and_values_are_local_first():
    app = APP.read_text(encoding="utf-8")
    assert 'bindSegment("targetSeg", "target", "target")' in app
    assert "markSourceDirty" in app
    assert "function sendTarget" not in app
    assert "function sendPaintMode" not in app
    assert 'operations = [["paint_target"' in app
    assert 'operations.push(["paint"' in app
    source_tx = re.search(
        r"async function sendSourceTransaction\(\) \{(.*?)\n  \}", app, re.S
    )
    assert source_tx
    body = source_tx.group(1)
    assert body.index("decision.deviceTestAllowed") < body.index("request(")
    assert body.index('"paint_target"') < body.index('operations.push(["paint"')
    assert body.index("app.sourceDirty = false") > body.index("successful(info)")
    assert "revisionAtStart === app.sourceRevision" in body
    assert "COMMAND_SEQUENCE_PARTIAL" in body
    assert 'queue.enqueuePriorityStop()' in body


def test_gain_and_gamma_are_one_transaction_and_draft_clear_is_last():
    app = APP.read_text(encoding="utf-8")
    tune_tx = re.search(
        r"async function applyTuneTransaction\(\) \{(.*?)\n  \}", app, re.S
    )
    assert tune_tx
    body = tune_tx.group(1)
    assert body.index('"tune_gain"') < body.index('"tune_gamma"')
    assert body.index("app.tuneDirty = false") > body.index("successful(gamma)")
    assert body.index("DRAFT_CLEAR_TUNE") > body.index("successful(gamma)")
    assert "revisionAtStart === app.tuneRevision" in body
    assert "COMMAND_SEQUENCE_PARTIAL" in body
    assert "every unsent field remains drafted" in body


def test_preview_drawing_comparison_and_inspector_share_cached_channel_frames():
    app = APP.read_text(encoding="utf-8")
    assert "var stageFrames = { primary: null, secondary: null };" in app
    assert "stageFrames.primary = CL.stageFrame" in app
    assert "stageFrames.secondary = CL.stageFrame" in app
    inspect = re.search(r"function renderInspector\(safetyBlocked\) \{(.*?)\n  \}", app, re.S)
    assert inspect
    assert "CL.inspectStageFrame(stageFrames.primary, selectedLed)" in inspect.group(1)
    assert "CL.inspectStageFrame(stageFrames.secondary, selectedLed)" in inspect.group(1)
    assert "CL.stageFrame" not in inspect.group(1)
    assert "CL.renderChannel" not in inspect.group(1)
    assert "CL.compareStageFrames(stageFrames.primary, stageFrames.secondary)" in app
    assert "function bindPreviewStrip(which)" in app


def test_preview_is_read_only_and_curve_belongs_to_tune():
    html = HTML.read_text(encoding="utf-8")
    preview = re.search(
        r'<section class="panel preview-panel".*?</section>\s*</div>', html, re.S
    )
    assert preview
    preview_body = preview.group(0)
    assert 'id="previewTitle">Preview<' in preview_body
    assert 'id="nextLink"' in preview_body
    assert 'id="applyTuneBtn"' not in preview_body
    assert 'id="sendStimulusBtn"' not in preview_body
    assert 'id="saveBtn"' not in preview_body
    assert 'id="curveCanvas"' not in preview_body
    assert html.index('class="tune-curve-details"') < html.index('id="previewPanel"')


def test_source_and_tune_are_parallel_authoring_roles_not_numbered_steps():
    html = HTML.read_text(encoding="utf-8")
    assert 'class="step"' not in html
    assert ">01<" not in html
    assert ">02<" not in html


def test_one_policy_and_safety_decision_controls_all_output_boundaries():
    app = APP.read_text(encoding="utf-8")
    assert "CA.validateProductPolicy" in app
    assert "CA.validateProductOutput" in app
    assert "CA.validateDiagnosticReference" in app
    assert "CA.validateDeviceSafety" in app
    assert "CA.resolveOutputDecision" in app
    assert "decision.deviceTestAllowed" in app
    assert "decision.saveAllowed" in app
    assert "decision.exportAllowed" in app
    assert "needsResync" in app
    assert "outputStateUnknown" in app
    assert "recoveryOnly" in AUTHORING.read_text(encoding="utf-8")


def test_legacy_recovery_proof_is_bound_to_each_ramp_incident():
    app = APP.read_text(encoding="utf-8")
    assert "legacyRecoveryGeneration += 1" in app
    assert "legacyRecoveryStopId = queue.enqueuePriorityStop()" in app
    assert "info.id === legacyRecoveryStopId" in app
    assert "legacyRecoveryOffGeneration !== legacyRecoveryGeneration" in app
    assert "legacyRecoveryStatusGeneration !== legacyRecoveryGeneration" in app
    assert 'info.cmd === "paint_status"' in app
    assert 'type: "RECOVERY_FAILED"' in app
    assert "legacyRecoveryOffConfirmed" not in app


def test_real_card_and_eight_stop_contract_are_visible():
    html = HTML.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    assert "K1 Card · 17" in html
    assert "13 greys · R · G · B · K1 Gold" in html
    assert "Rich local draft → 8 Paint stops" in html
    assert "CL.GREYS" in app
    assert "CL.GOLD.slice()" in app
    assert "maxStops: CL.MAX_STOPS" in app


def test_accessibility_and_responsive_contracts_are_present():
    html = HTML.read_text(encoding="utf-8")
    assert 'lang="en-GB"' in html
    assert 'aria-describedby="previewBoundary primarySummary selectedLedHelp"' in html
    assert 'aria-describedby="previewBoundary secondarySummary selectedLedHelp"' in html
    assert 'aria-live="polite"' in html
    assert 'name="previewView"' in html
    assert 'type="number" min="0" max="159"' in html
    assert 'aria-describedby="curveSummary"' in html
    assert "button:focus-visible" in html
    assert "@media (max-width: 760px)" in html
    assert "@media (prefers-reduced-motion: reduce)" in html
