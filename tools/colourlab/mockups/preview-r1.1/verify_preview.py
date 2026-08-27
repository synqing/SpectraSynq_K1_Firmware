#!/usr/bin/env python3
"""Headless visual and interaction gate for the isolated Preview R1.1 mockup."""
from __future__ import annotations

import contextlib
import functools
import http.server
import json
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "evidence"
HOST = "127.0.0.1"
PORT = 0


class ReusableServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: object) -> None:
        return


def state(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const api = globalThis.__previewR11;
          const panel = document.getElementById('previewPanel').getBoundingClientRect();
          const primary = document.getElementById('primaryCanvas').getBoundingClientRect();
          const secondary = document.getElementById('secondaryCanvas').getBoundingClientRect();
          const evidenceNav = document.querySelector('.evidence-nav');
          const evidenceNavRect = evidenceNav.getBoundingClientRect();
          return {
            scenario: api.scenario,
            selectedLed: api.selectedLed,
            view: api.view,
            primarySelection: api.stageFrames.primary && api.stageFrames.primary.selection,
            secondarySelection: api.stageFrames.secondary && api.stageFrames.secondary.selection,
            primaryTune: api.stageFrames.primary && api.stageFrames.primary.tune,
            secondaryTune: api.stageFrames.secondary && api.stageFrames.secondary.tune,
            primaryCorrection: api.stageFrames.primary && api.stageFrames.primary.correctionText,
            secondaryCorrection: api.stageFrames.secondary && api.stageFrames.secondary.correctionText,
            secondaryLook: api.stageFrames.secondary && api.stageFrames.secondary.lookResolution,
            output: api.comparison.output,
            basis: api.comparison.basis,
            primaryPixels: api.stageFrames.primary && api.stageFrames.primary.pixels,
            secondaryPixels: api.stageFrames.secondary && api.stageFrames.secondary.pixels,
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth,
            panelArea: panel.width * panel.height,
            stripsArea: primary.width * primary.height + secondary.width * secondary.height,
            primaryStripOffset: primary.top - panel.top,
            primaryStripHeight: primary.height,
            secondaryStripBottom: secondary.bottom - panel.top,
            evidenceNavClientWidth: evidenceNav.clientWidth,
            evidenceNavScrollWidth: evidenceNav.scrollWidth,
            evidenceNavHeight: evidenceNavRect.height,
            inputDisabled: document.getElementById('selectedLedInput').disabled,
            safetyVisible: document.getElementById('safetyBanner').classList.contains('visible'),
            policyVisible: document.getElementById('policyBanner').classList.contains('visible'),
            nextState: document.getElementById('nextState').textContent,
            nextLabel: document.getElementById('nextLink').textContent,
            nextHref: document.getElementById('nextLink').getAttribute('href'),
            captionWidth: document.getElementById('inspectorCaption').getBoundingClientRect().width,
            primary16: document.getElementById('primaryRgb16').textContent,
            secondary16: document.getElementById('secondaryRgb16').textContent,
          };
        }"""
    )


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    measurements: dict[str, object] = {}

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    handler = functools.partial(QuietHandler, directory=str(ROOT))
    server = ReusableServer((HOST, PORT), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)

            def open_page(
                query: str,
                width: int,
                height: int,
                scale: int = 2,
                *,
                has_touch: bool = False,
            ):
                page = browser.new_page(
                    viewport={"width": width, "height": height},
                    device_scale_factor=scale,
                    has_touch=has_touch,
                    is_mobile=has_touch,
                )
                errors: list[str] = []
                page.on(
                    "console",
                    lambda item: errors.append(f"console:{item.type}:{item.text}")
                    if item.type in {"error", "warning"}
                    else None,
                )
                page.on("pageerror", lambda error: errors.append(f"page:{error}"))
                page.goto(f"http://{HOST}:{port}/index.html{query}", wait_until="networkidle")
                page.wait_for_function("globalThis.__previewR11 !== undefined")
                return page, errors

            desktop, desktop_errors = open_page("?state=inherit15", 1440, 1000)
            desktop_state = state(desktop)
            require(desktop_state["output"]["status"] == "match", "inherit15 output does not match")
            require(desktop_state["basis"] == {"status": "differ", "reasons": ["look_relationship"]},
                    "inherit15 basis does not isolate look relationship")
            require(desktop_state["primaryPixels"] == desktop_state["secondaryPixels"],
                    "inherit15 cached output bytes differ")
            require(desktop.locator("#primaryCanvas").count() == 1 and desktop.locator("#secondaryCanvas").count() == 1,
                    "two permanent channel canvases are not present")
            require(not desktop_errors, "desktop console/page errors: " + " | ".join(desktop_errors))

            desktop.locator("#selectedLedInput").fill("87")
            desktop.locator("#selectedLedInput").press("Enter")
            after_keyboard = state(desktop)
            require(after_keyboard["selectedLed"] == 87, "number input did not update shared selectedLed")
            desktop.locator("#selectedLedInput").press("ArrowRight")
            after_arrow = state(desktop)
            require(after_arrow["selectedLed"] == 88, "keyboard arrow did not update shared selectedLed")
            expected_primary = after_keyboard["primaryPixels"][87 * 3:87 * 3 + 3]
            expected_secondary = after_keyboard["secondaryPixels"][87 * 3:87 * 3 + 3]
            require(all(str(value) in after_keyboard["primary16"] for value in expected_primary),
                    "Primary inspector does not read cached frame")
            require(all(str(value) in after_keyboard["secondary16"] for value in expected_secondary),
                    "Secondary inspector does not read cached frame")
            desktop.screenshot(path=str(EVIDENCE / "preview-desktop-inherit15-1440@2x.png"), full_page=True)

            primary_box = desktop.locator("#primaryCanvas").bounding_box()
            assert primary_box
            desktop.mouse.move(primary_box["x"] + primary_box["width"] * .25, primary_box["y"] + primary_box["height"] * .5)
            pointer_state = state(desktop)
            require(pointer_state["selectedLed"] == 37, "pointer path did not update the shared logical LED index")
            desktop.close()

            asymmetric, asymmetric_errors = open_page("?state=asymmetric", 1200, 900)
            asymmetric_state = state(asymmetric)
            require(asymmetric_state["primarySelection"] == "post", "asymmetric Primary is not post")
            require(asymmetric_state["secondarySelection"] == "pre", "asymmetric Secondary is not pre")
            require(asymmetric_state["output"]["status"] == "differ", "asymmetric output was collapsed")
            require(asymmetric_state["basis"]["status"] == "differ", "asymmetric basis was collapsed")
            asymmetric.screenshot(path=str(EVIDENCE / "preview-asymmetric-1200@2x.png"), full_page=True)
            require(not asymmetric_errors, "asymmetric console/page errors: " + " | ".join(asymmetric_errors))
            asymmetric.close()

            inherited_unknown, inherited_unknown_errors = open_page("?state=inheritUnknown", 1200, 900)
            unknown_state = state(inherited_unknown)
            require(unknown_state["primarySelection"] == unknown_state["secondarySelection"] == "pre",
                    "unknown inherited look did not fail closed")
            require(unknown_state["secondaryLook"]["relation"] == "inherit" and
                    not unknown_state["secondaryLook"]["effectiveKnown"],
                    "unknown inherited relationship was promoted")
            require(inherited_unknown.locator("#outputComparison").text_content() ==
                    "Pre-correction references match",
                    "unknown inherited look overstates output certainty")
            require("unknown Primary look" in inherited_unknown.locator("#basisComparisonNote").text_content(),
                    "unknown inherited basis is not explicit")
            inherited_unknown.screenshot(path=str(EVIDENCE / "preview-inherit-unknown-1200@2x.png"), full_page=True)
            require(not inherited_unknown_errors,
                    "inherit unknown console/page errors: " + " | ".join(inherited_unknown_errors))
            inherited_unknown.close()

            slot_unknown, slot_unknown_errors = open_page("?state=slotUnknown", 1200, 900)
            slot_unknown_state = state(slot_unknown)
            require(slot_unknown_state["primarySelection"] == slot_unknown_state["secondarySelection"] == "pre",
                    "inherited slot-unknown state did not select pre-correction frames")
            require(slot_unknown_state["primaryTune"] is None and slot_unknown_state["secondaryTune"] is None,
                    "inherited slot-unknown state retained an applied tune")
            require(slot_unknown_state["primaryCorrection"] == "Before correction · slot-15 contents unknown",
                    "Primary slot-unknown wording is not truth-derived")
            require(slot_unknown_state["secondaryCorrection"] ==
                    "Inherits Primary look · slot-15 contents unknown",
                    "inherited Secondary slot-unknown wording is not truth-derived")
            require("tune" not in (slot_unknown_state["primaryCorrection"] +
                                    slot_unknown_state["secondaryCorrection"]).lower(),
                    "inherited slot-unknown state still claims tune simulation")
            require(slot_unknown.locator("#outputComparisonNote").text_content() ==
                    "Correction output is not claimed until slot-15 contents are known.",
                    "inherited slot-unknown comparison note names the wrong missing knowledge")
            require(slot_unknown_state["nextHref"] == "../../index.html#deviceTitle",
                    "inherited slot-unknown state does not hand back to Device")
            slot_unknown.screenshot(
                path=str(EVIDENCE / "preview-slot-unknown-inherited-1200@2x.png"),
                full_page=True,
            )
            require(not slot_unknown_errors,
                    "inherited slot-unknown console/page errors: " + " | ".join(slot_unknown_errors))
            slot_unknown.close()

            slot_unknown_direct, slot_unknown_direct_errors = open_page(
                "?state=slotUnknownDirect", 1200, 900
            )
            slot_unknown_direct_state = state(slot_unknown_direct)
            require(slot_unknown_direct_state["primarySelection"] ==
                    slot_unknown_direct_state["secondarySelection"] == "pre",
                    "direct slot-unknown state did not select pre-correction frames")
            require(slot_unknown_direct_state["primaryTune"] is None and
                    slot_unknown_direct_state["secondaryTune"] is None,
                    "direct slot-unknown state retained an applied tune")
            require(slot_unknown_direct_state["primaryCorrection"] ==
                    "Before correction · slot-15 contents unknown" and
                    slot_unknown_direct_state["secondaryCorrection"] ==
                    "Before correction · slot-15 contents unknown",
                    "direct slot-unknown wording is not truth-derived")
            require("tune" not in (slot_unknown_direct_state["primaryCorrection"] +
                                    slot_unknown_direct_state["secondaryCorrection"]).lower(),
                    "direct slot-unknown state still claims tune simulation")
            require(slot_unknown_direct.locator("#outputComparisonNote").text_content() ==
                    "Correction output is not claimed until slot-15 contents are known.",
                    "direct slot-unknown comparison note names the wrong missing knowledge")
            require(slot_unknown_direct_state["basis"]["status"] == "match",
                    "direct slot-unknown basis did not remain direct/direct")
            slot_unknown_direct.screenshot(
                path=str(EVIDENCE / "preview-slot-unknown-direct-1200@2x.png"),
                full_page=True,
            )
            require(not slot_unknown_direct_errors,
                    "direct slot-unknown console/page errors: " +
                    " | ".join(slot_unknown_direct_errors))
            slot_unknown_direct.close()

            narrow, narrow_errors = open_page("?state=inherit15", 740, 1100)
            narrow_state = state(narrow)
            measurements["narrow_740"] = {
                "clientWidth": narrow_state["clientWidth"],
                "scrollWidth": narrow_state["scrollWidth"],
                "primaryStripOffset": round(narrow_state["primaryStripOffset"], 2),
                "primaryStripHeight": round(narrow_state["primaryStripHeight"], 2),
                "secondaryStripBottom": round(narrow_state["secondaryStripBottom"], 2),
                "evidenceNavClientWidth": narrow_state["evidenceNavClientWidth"],
                "evidenceNavScrollWidth": narrow_state["evidenceNavScrollWidth"],
                "evidenceNavHeight": round(narrow_state["evidenceNavHeight"], 2),
                "stripsShare": round(narrow_state["stripsArea"] / narrow_state["panelArea"], 4),
            }
            require(narrow_state["scrollWidth"] == narrow_state["clientWidth"], "740px layout has horizontal overflow")
            require(narrow_state["primaryStripOffset"] <= 340, "740px first strip begins below 340px")
            require(56 <= narrow_state["primaryStripHeight"] <= 64,
                    "740px LED strip is not within the locked compact 56-64px height")
            require(narrow_state["secondaryStripBottom"] <= 700,
                    "740px comparison does not show both channel strips within the first 700px of Preview")
            require(narrow_state["evidenceNavHeight"] <= 50,
                    "740px evidence navigation wrapped into a second row")
            narrow.screenshot(path=str(EVIDENCE / "preview-narrow-740@2x.png"), full_page=True)
            require(not narrow_errors, "740px console/page errors: " + " | ".join(narrow_errors))
            narrow.close()

            phone, phone_errors = open_page("?state=asymmetric", 390, 1300, has_touch=True)
            phone_state = state(phone)
            require(phone_state["scrollWidth"] == phone_state["clientWidth"], "390px layout has horizontal overflow")
            require(phone_state["captionWidth"] >= 250, "390px inspector caption collapsed into a narrow column")
            touch_box = phone.locator("#secondaryCanvas").bounding_box()
            assert touch_box
            phone.touchscreen.tap(
                touch_box["x"] + touch_box["width"] * .75,
                touch_box["y"] + touch_box["height"] * .5,
            )
            phone_touch_state = state(phone)
            require(phone_touch_state["selectedLed"] == 112,
                    "touch path did not update the shared logical LED index")
            measurements["narrow_390"] = {
                "clientWidth": phone_touch_state["clientWidth"],
                "scrollWidth": phone_touch_state["scrollWidth"],
                "captionWidth": round(phone_touch_state["captionWidth"], 2),
                "touchSelectedLed": phone_touch_state["selectedLed"],
                "evidenceNavClientWidth": phone_touch_state["evidenceNavClientWidth"],
                "evidenceNavScrollWidth": phone_touch_state["evidenceNavScrollWidth"],
                "evidenceNavHeight": round(phone_touch_state["evidenceNavHeight"], 2),
            }
            require(phone_touch_state["evidenceNavHeight"] <= 50,
                    "390px evidence navigation wrapped into a second row")
            phone.screenshot(path=str(EVIDENCE / "preview-narrow-390@2x.png"), full_page=True)
            require(not phone_errors, "390px console/page errors: " + " | ".join(phone_errors))
            phone.close()

            zoomed, zoomed_errors = open_page("?state=inherit15", 800, 1100)
            zoomed.locator("#selectedLedInput").focus()
            zoom_state = state(zoomed)
            require(zoom_state["scrollWidth"] == zoom_state["clientWidth"],
                    "200-percent reflow equivalent has horizontal overflow")
            measurements["zoom_200_reflow_equivalent"] = {
                "clientWidth": zoom_state["clientWidth"],
                "scrollWidth": zoom_state["scrollWidth"],
                "primaryStripHeight": round(zoom_state["primaryStripHeight"], 2),
                "selectedLed": zoom_state["selectedLed"],
            }
            zoomed.screenshot(path=str(EVIDENCE / "preview-zoom-200-equivalent-800@2x.png"), full_page=True)
            require(not zoomed_errors, "zoom console/page errors: " + " | ".join(zoomed_errors))
            zoomed.close()

            safety, safety_errors = open_page("?state=safety", 1200, 900)
            safety_state = state(safety)
            require(safety_state["safetyVisible"], "safety failure banner is absent")
            require(safety_state["inputDisabled"], "safety failure did not disable inspection")
            require("Unavailable" in safety_state["primary16"] and "Unavailable" in safety_state["secondary16"],
                    "safety failure left stale numeric values")
            require("Device truth" in safety_state["nextState"] and "Return to Device" in safety_state["nextLabel"],
                    "safety failure offers the wrong read-only handoff")
            require(safety_state["nextHref"] == "../../index.html#deviceTitle",
                    "safety handoff does not navigate to Device")
            safety.screenshot(path=str(EVIDENCE / "preview-safety-failure-1200@2x.png"), full_page=True)
            require(not safety_errors, "safety console/page errors: " + " | ".join(safety_errors))
            safety.close()

            policy, policy_errors = open_page("?state=policy", 1200, 900)
            policy_state = state(policy)
            require(policy_state["policyVisible"], "policy failure banner is absent")
            require(not policy_state["inputDisabled"], "policy failure wrongly disabled local inspection")
            require(policy_state["primaryPixels"] is not None and policy_state["secondaryPixels"] is not None,
                    "policy failure wrongly removed bounded local frames")
            require("colour policy" in policy_state["nextState"] and "Review Source" in policy_state["nextLabel"],
                    "policy failure offers the wrong read-only handoff")
            require(policy_state["nextHref"] == "../../index.html#sourceTitle",
                    "policy handoff does not navigate to Source")
            policy.screenshot(path=str(EVIDENCE / "preview-policy-failure-1200@2x.png"), full_page=True)
            require(not policy_errors, "policy console/page errors: " + " | ".join(policy_errors))
            policy.close()

            diffusion, diffusion_errors = open_page("?state=inherit15&view=diffusion", 1200, 900)
            diffusion_state = state(diffusion)
            require(diffusion_state["view"] == "diffusion", "diffusion view did not initialise")
            require(diffusion_state["primaryPixels"] == desktop_state["primaryPixels"],
                    "diffusion view changed cached LED values")
            diffusion.screenshot(path=str(EVIDENCE / "preview-diffusion-model-1200@2x.png"), full_page=True)
            require(not diffusion_errors, "diffusion console/page errors: " + " | ".join(diffusion_errors))
            diffusion.close()

            browser.close()
    finally:
        server.shutdown()
        server.server_close()

    (EVIDENCE / "MEASUREMENTS.json").write_text(
        json.dumps(measurements, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(measurements, indent=2))
    print(f"FAILURES={len(failures)}")
    for failure in failures:
        print(f"FAIL: {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
