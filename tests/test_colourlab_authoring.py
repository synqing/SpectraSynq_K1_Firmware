"""Production Colour Lab authoring maths and output-policy gate."""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTHORING = ROOT / "tools" / "colourlab" / "colourlab-authoring.js"
CORE = ROOT / "tools" / "colourlab" / "colourlab-core.js"


def call_authoring(function: str, *args):
    script = """
const fs = require('fs');
const api = require(process.argv[1]);
const req = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = api[req.function](...req.args);
process.stdout.write(JSON.stringify(out));
"""
    proc = subprocess.run(
        ["node", "-e", script, str(AUTHORING)],
        input=json.dumps({"function": function, "args": args}),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(proc.stdout)


def stop(position: float, rgb: list[int]) -> dict:
    return {"position": position, "rgb": rgb}


BOUNDED_WARM = [
    stop(0.00, [255, 201, 74]),
    stop(0.34, [255, 138, 0]),
    stop(0.67, [228, 66, 0]),
    stop(1.00, [150, 18, 40]),
]


def test_module_is_umd_and_uses_eight_stop_firmware_contract():
    src = AUTHORING.read_text(encoding="utf-8")
    assert "module.exports" in src
    assert "ColourLabAuthoring" in src
    assert "document." not in src
    assert "navigator.serial" not in src
    assert call_authoring("dispatch", {"op": "constants"}) == {
        "MAX_STOPS": 8,
        "MAX_HUE_TRAVEL": 80,
        "MAX_HUE_FAMILIES": 3,
    }


def test_rgb_interpolation_is_channel_linear():
    result = call_authoring(
        "interpolate",
        [stop(0, [0, 16, 32]), stop(1, [200, 216, 232])],
        0.25,
        "rgb",
    )
    assert result == [50, 66, 82]


def test_hsv_interpolation_takes_shortest_hue_arc():
    left = call_authoring("hsvToRgb", [350, 1, 1])
    right = call_authoring("hsvToRgb", [10, 1, 1])
    middle = call_authoring("interpolate", [stop(0, left), stop(1, right)], 0.5, "hsv")
    assert middle[0] >= 254.9
    assert middle[1] <= 0.1
    assert middle[2] <= 0.1


def test_oklch_primary_reference_and_round_trip():
    red = call_authoring("rgbToOklch", [255, 0, 0])
    assert math.isclose(red[0], 0.627955, abs_tol=2e-5)
    assert math.isclose(red[1], 0.257683, abs_tol=2e-5)
    assert math.isclose(red[2], 29.234, abs_tol=0.02)
    round_trip = call_authoring("oklchToRgb", red)
    assert round_trip[0] > 254.99
    assert round_trip[1] < 0.02
    assert round_trip[2] < 0.02


def test_oklch_comparison_is_not_fake_rgb_interpolation():
    pair = [stop(0, [255, 191, 0]), stop(1, [150, 18, 40])]
    rgb = call_authoring("interpolate", pair, 0.5, "rgb")
    oklch = call_authoring("interpolate", pair, 0.5, "oklch")
    assert any(abs(a - b) > 0.2 for a, b in zip(rgb, oklch, strict=True))


def test_rich_local_draft_compiles_to_uniform_eight_rgb_stops():
    rich = [
        stop(0.00, [255, 212, 128]),
        stop(0.08, [255, 191, 0]),
        stop(0.21, [251, 150, 20]),
        stop(0.42, [255, 126, 0]),
        stop(0.73, [212, 57, 0]),
        stop(1.00, [120, 17, 34]),
    ]
    result = call_authoring(
        "compilePaintStops",
        rich,
        {"interpolation": "oklch", "maxStops": 8, "comparisonSamples": 161},
    )
    assert result["compiledStopCount"] == 8
    assert result["uniformlyDistributed"] is True
    assert [round(item["position"], 8) for item in result["compiledStops"]] == [
        round(i / 7, 8) for i in range(8)
    ]
    assert all(len(rgb) == 3 and all(0 <= channel <= 255 for channel in rgb) for rgb in result["paintStops"])
    assert result["approximation"]["sampleCount"] == 161
    assert result["approximation"]["maxChannelError8"] >= result["approximation"]["rmsChannelError8"] >= 0


def test_compiled_stops_fit_the_existing_wire_contract():
    script = """
const a = require(process.argv[1]);
const core = require(process.argv[2]);
const rich = JSON.parse(process.argv[3]);
const out = a.compilePaintStops(rich, {interpolation:'oklch'});
const line = core.serialize.paintStops(out.paintStops);
process.stdout.write(JSON.stringify({count:out.paintStops.length, line, length:line.length}));
"""
    proc = subprocess.run(
        ["node", "-e", script, str(AUTHORING), str(CORE), json.dumps(BOUNDED_WARM)],
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(proc.stdout)
    assert result["count"] == 8
    assert result["line"].startswith(":paint_stops=")
    assert result["length"] <= 158


def test_bounded_warm_palette_passes_product_policy():
    result = call_authoring("validateProductPolicy", BOUNDED_WARM, {"interpolation": "oklch"})
    assert result["ok"] is True
    assert result["issues"] == []
    assert result["metrics"]["hueTravelDeg"] <= 80
    assert result["metrics"]["hueFamilies"] <= 3
    assert len(result["metrics"]["hueSectors"]) < 5


def test_wheel_spanning_sequence_is_semantically_blocked():
    hue_path = [
        stop(i / 5, call_authoring("hsvToRgb", [i * 60, 1, 0.75]))
        for i in range(6)
    ]
    result = call_authoring("validateProductPolicy", hue_path, {"interpolation": "hsv"})
    codes = {issue["code"] for issue in result["issues"]}
    assert result["ok"] is False
    assert "wheel_spanning" in codes
    assert "hue_travel" in codes


def test_compiled_rgb_payload_is_revalidated_before_output():
    counterexample = [
        stop(0.0, [54, 125, 133]),
        stop(0.5, [141, 142, 118]),
        stop(1.0, [46, 167, 224]),
    ]
    result = call_authoring(
        "validateProductOutput",
        counterexample,
        {"interpolation": "rgb", "maxStops": 8, "comparisonSamples": 161},
    )
    assert result["sourcePolicy"]["ok"] is True
    assert result["sourcePolicy"]["metrics"]["hueTravelDeg"] <= 80
    assert result["payloadPolicy"]["ok"] is False
    assert result["payloadPolicy"]["metrics"]["hueTravelDeg"] > 80
    assert result["ok"] is False
    assert any(
        issue["scope"] == "compiled_payload" and issue["code"] == "hue_travel"
        for issue in result["issues"]
    )


def test_every_allowed_output_has_safe_source_and_compiled_payload():
    families = [
        BOUNDED_WARM,
        [stop(0, [255, 212, 128]), stop(1, [166, 84, 0])],
        [stop(0, [15, 6, 28]), stop(0.5, [66, 24, 91]), stop(1, [132, 37, 96])],
    ]
    for palette in families:
        for interpolation in ("rgb", "hsv", "oklch"):
            result = call_authoring(
                "validateProductOutput",
                palette,
                {"interpolation": interpolation, "maxStops": 8},
            )
            if result["ok"]:
                assert result["sourcePolicy"]["ok"] is True
                assert result["payloadPolicy"]["ok"] is True


def test_safe_diagnostic_references_are_validated_by_shape_not_label():
    neutral = [[value, value, value] for value in range(0, 256, 17)]
    isolated = [[value, 0, 0] for value in range(0, 256, 17)]
    isolated += [[0, value, 0] for value in range(0, 256, 17)]
    isolated += [[0, 0, value] for value in range(0, 256, 17)]
    neutral_result = call_authoring("validateDiagnosticReference", "neutral", neutral)
    isolated_result = call_authoring("validateDiagnosticReference", "isolated_rgb", isolated)
    overlap_result = call_authoring("validateDiagnosticReference", "isolated_rgb", [[255, 64, 0]])
    assert neutral_result["ok"] is True
    assert isolated_result["ok"] is True
    assert overlap_result["ok"] is False
    assert {issue["code"] for issue in overlap_result["issues"]} == {"channels_overlap"}


def test_near_white_product_palette_is_visible_but_non_product():
    bloom_risk = [stop(0, [255, 248, 238]), stop(1, [255, 154, 38])]
    policy = call_authoring("validateProductPolicy", bloom_risk, {"interpolation": "rgb"})
    decision = call_authoring(
        "resolveOutputDecision",
        {"safety": {"ok": True, "issues": []}, "policy": policy, "transportReady": True},
    )
    assert policy["ok"] is False
    assert "near_white" in {issue["code"] for issue in policy["issues"]}
    assert decision["kind"] == "policy_blocked"
    assert decision["stageVisible"] is True
    assert decision["stageDark"] is False
    assert decision["nonProduct"] is True
    assert decision["deviceTestAllowed"] is False
    assert decision["saveAllowed"] is False
    assert decision["exportAllowed"] is False


def test_device_safety_failure_makes_stage_dark_and_recovery_only():
    safety = call_authoring(
        "validateDeviceSafety",
        {"mode": "ramp", "target": "both", "modelKnown": True,
         "deviceEvidenceRequired": True, "profileVerified": True,
         "primaryLedCount": 160, "secondaryLedCount": 160},
    )
    decision = call_authoring(
        "resolveOutputDecision",
        {"safety": safety, "policy": {"ok": True, "issues": []}, "transportReady": True},
    )
    assert safety["ok"] is False
    assert {issue["code"] for issue in safety["issues"]} == {"unsupported_mode"}
    assert decision["kind"] == "safety_blocked"
    assert decision["stageVisible"] is False
    assert decision["stageDark"] is True
    assert decision["recoveryOnly"] is True
    assert decision["deviceTestAllowed"] is False
    assert decision["saveAllowed"] is False
    assert decision["exportAllowed"] is False


def test_device_safety_fails_closed_on_missing_or_uncertain_evidence():
    missing = call_authoring("validateDeviceSafety", {})
    uncertain = call_authoring(
        "validateDeviceSafety",
        {"mode": "stops", "target": "both", "modelKnown": True,
         "deviceEvidenceRequired": True, "profileVerified": True,
         "primaryLedCount": 160, "secondaryLedCount": 160,
         "needsResync": True, "outputStateUnknown": True},
    )
    assert missing["ok"] is False
    assert {"model_unknown", "unsupported_mode", "invalid_target",
            "invalid_primary_count", "invalid_secondary_count"} <= {
        issue["code"] for issue in missing["issues"]
    }
    assert uncertain["ok"] is False
    assert {"resync_required", "output_unknown"} <= {
        issue["code"] for issue in uncertain["issues"]
    }

    recovering = call_authoring(
        "validateDeviceSafety",
        {"mode": "off", "target": "both", "modelKnown": True,
         "deviceEvidenceRequired": True, "profileVerified": True,
         "primaryLedCount": 160, "secondaryLedCount": 160,
         "recoveryPending": True},
    )
    assert recovering["ok"] is False
    assert "recovery_pending" in {issue["code"] for issue in recovering["issues"]}


def test_passed_policy_exports_locally_but_device_requires_transport():
    policy = call_authoring("validateProductPolicy", BOUNDED_WARM, {"interpolation": "rgb"})
    safety = call_authoring(
        "validateDeviceSafety",
        {"mode": "stops", "target": "both", "modelKnown": True,
         "deviceEvidenceRequired": True, "profileVerified": True,
         "primaryLedCount": 160, "secondaryLedCount": 160},
    )
    local = call_authoring(
        "resolveOutputDecision",
        {"safety": safety, "policy": policy, "transportReady": False},
    )
    ready = call_authoring(
        "resolveOutputDecision",
        {"safety": safety, "policy": policy, "transportReady": True},
    )
    assert local["kind"] == "local_only"
    assert local["exportAllowed"] is True
    assert local["deviceTestAllowed"] is False
    assert ready["kind"] == "ready"
    assert ready["deviceTestAllowed"] is True
    assert ready["saveAllowed"] is True
