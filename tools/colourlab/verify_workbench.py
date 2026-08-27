#!/usr/bin/env python3
"""Headless browser gate for the production Colour Lab Workbench.

This harness never opens Web Serial. The transport fixture acknowledges the real
queue and reducer contracts entirely inside the browser.
"""
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
SCREENSHOTS = ROOT / "screenshots" / "workbench-r1.1"
HOST = "127.0.0.1"
PORT = 8768


class ReusableServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: object) -> None:
        return


def browser_state(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const api = globalThis.__colourLabWorkbench;
          const nonBlack = frame => {
            if (!frame || !frame.pixels) return 0;
            let count = 0;
            for (let i = 0; i < frame.pixels.length; i += 3) {
              if (frame.pixels[i] || frame.pixels[i + 1] || frame.pixels[i + 2]) count++;
            }
            return count;
          };
          return {
            decision: api.decision.kind,
            safety: api.safety.ok,
            policy: api.policy.ok,
            policyIssues: api.policy.issues,
            sourcePolicyOk: api.policy.sourcePolicy && api.policy.sourcePolicy.ok,
            payloadPolicyOk: api.policy.payloadPolicy && api.policy.payloadPolicy.ok,
            txCount: api.txCount,
            txTrace: api.txTrace,
            transaction: api.transaction,
            sourceDirty: api.app.sourceDirty,
            tuneDirty: api.app.tuneDirty,
            primarySelection: api.stageFrames.primary && api.stageFrames.primary.selection,
            secondarySelection: api.stageFrames.secondary && api.stageFrames.secondary.selection,
            primaryPixels: api.stageFrames.primary && api.stageFrames.primary.pixels,
            secondaryPixels: api.stageFrames.secondary && api.stageFrames.secondary.pixels,
            primaryFramePresent: !!api.stageFrames.primary,
            secondaryFramePresent: !!api.stageFrames.secondary,
            primaryCorrection: document.getElementById('primaryCorrection').textContent,
            secondaryCorrection: document.getElementById('secondaryCorrection').textContent,
            outputComparison: document.getElementById('outputComparison').textContent,
            basisComparison: document.getElementById('basisComparison').textContent,
            selectedLed: api.selectedLed,
            primaryInspect: ColourLab.inspectStageFrame(api.stageFrames.primary, api.selectedLed),
            secondaryInspect: ColourLab.inspectStageFrame(api.stageFrames.secondary, api.selectedLed),
            primaryNonBlack: nonBlack(api.stageFrames.primary),
            secondaryNonBlack: nonBlack(api.stageFrames.secondary),
            sendDisabled: document.getElementById('sendStimulusBtn').disabled,
            applyDisabled: document.getElementById('applyTuneBtn').disabled,
            saveDisabled: document.getElementById('saveBtn').disabled,
            exportDisabled: document.getElementById('exportBtn').disabled,
            stopDisabled: document.getElementById('stopBtn').disabled,
            nonProductVisible: document.getElementById('nonProductStamp').classList.contains('visible'),
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth,
            confirmedTune: api.coreState.confirmed.tune,
            persistence: api.coreState.persistence,
            needsResync: api.coreState.needsResync,
            outputStateUnknown: api.coreState.outputStateUnknown,
            recoveryPending: api.recoveryPending,
            legacyForbiddenDetected: api.legacyForbiddenDetected,
            legacyRecoveryGeneration: api.legacyRecoveryGeneration,
            legacyRecoveryOffGeneration: api.legacyRecoveryOffGeneration,
            legacyRecoveryStatusGeneration: api.legacyRecoveryStatusGeneration,
            confirmedPaintMode: api.coreState.confirmed.paint && api.coreState.confirmed.paint.mode,
          };
        }"""
    )


def hue_sector_count(page: Page, canvas_id: str = "primaryCanvas") -> int:
    return page.evaluate(
        """channel => {
          const frame = globalThis.__colourLabWorkbench.stageFrames[channel];
          if (!frame || !frame.pixels) return 0;
          const row = frame.pixels;
          const sectors = new Set();
          for (let i = 0; i < row.length; i += 3) {
            const r = row[i] / 255, g = row[i + 1] / 255, b = row[i + 2] / 255;
            const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
            const s = max === 0 ? 0 : d / max;
            if (s < 0.20 || max < 0.10) continue;
            let h = 0;
            if (max === r) h = 60 * (((g - b) / d) % 6);
            else if (max === g) h = 60 * (((b - r) / d) + 2);
            else h = 60 * (((r - g) / d) + 4);
            if (h < 0) h += 360;
            sectors.add(Math.floor(h / 60) % 6);
          }
          return sectors.size;
        }""",
        "secondary" if canvas_id == "secondaryCanvas" else "primary",
    )


def main() -> int:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    messages: list[str] = []
    handler = functools.partial(QuietHandler, directory=str(ROOT))
    server = ReusableServer((HOST, PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://{HOST}:{PORT}/index.html"

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)

            def open_page(suffix: str = "", width: int = 1600, height: int = 1000, scale: int = 2):
                page = browser.new_page(
                    viewport={"width": width, "height": height},
                    device_scale_factor=scale,
                )
                page_errors: list[str] = []
                page.on(
                    "console",
                    lambda item: page_errors.append(f"console:{item.type}:{item.text}")
                    if item.type in {"error", "warning"} else None,
                )
                page.on("pageerror", lambda error: page_errors.append(f"page:{error}"))
                page.goto(base + suffix, wait_until="networkidle")
                page.wait_for_function("globalThis.__colourLabWorkbench !== undefined")
                return page, page_errors

            normal, normal_errors = open_page()
            normal.locator("details.console").evaluate("element => element.open = true")
            initial = browser_state(normal)
            require(initial["decision"] == "local_only", "default must be local_only")
            require(initial["safety"] and initial["policy"], "default gates must pass")
            require(initial["txCount"] == 0, "default emitted a transport write")
            require(initial["primaryNonBlack"] > 0 and initial["secondaryNonBlack"] > 0,
                    "default neutral Preview is empty")
            require(not initial["exportDisabled"], "safe local palette export is disabled")
            before = normal.evaluate("__colourLabWorkbench.stageFrames.primary.pixels.slice()")
            normal.locator("#gainR").fill("1.400")
            drafted = browser_state(normal)
            after = normal.evaluate("__colourLabWorkbench.stageFrames.primary.pixels.slice()")
            require(drafted["tuneDirty"], "local tune edit did not create a draft")
            require(drafted["txCount"] == 0, "local tune edit emitted transport")
            require(before != after, "local tune draft did not alter the Preview model")
            normal.screenshot(path=str(SCREENSHOTS / "normal-full-1600@2x.png"), full_page=True)
            require(not normal_errors, "normal console/page errors: " + " | ".join(normal_errors))
            normal.close()

            ready, ready_errors = open_page("?demo=ready")
            asymmetric = browser_state(ready)
            require(asymmetric["primarySelection"] == "post", "Primary known look is not post-LUT")
            require(asymmetric["secondarySelection"] == "pre", "Secondary unknown look is not pre-LUT")
            require(asymmetric["primaryPixels"] != asymmetric["secondaryPixels"],
                    "asymmetric channel frames collapsed to one pixel buffer")
            frame = asymmetric["primaryPixels"]
            canvas = ready.locator("#primaryCanvas")
            box = canvas.bounding_box()
            assert box
            canvas.hover(position={"x": box["width"] * 0.5, "y": box["height"] * 0.5})
            inspected = browser_state(ready)
            index = inspected["selectedLed"]
            expected = frame[index * 3:index * 3 + 3]
            inspector_text = ready.locator("#primaryRgb16").inner_text()
            require(inspected["selectedLed"] == index and inspected["primaryInspect"]["rgb16"] == expected,
                    "shared inspector does not consume the painted Primary frame")
            require(all(str(value) in inspector_text for value in expected),
                    "persistent Primary RGB16 row does not show the selected cached frame")
            require(not ready_errors, "ready console/page errors: " + " | ".join(ready_errors))
            ready.close()

            preview_cases = (
                ("inherit15", "post", "post", "Inherits Primary look · slot 15 browser model"),
                ("inherit0", "post", "post", "Inherits Primary look · active look 0 not modelled"),
                ("inheritUnknown", "pre", "pre", "Inherits Primary look · Primary look unknown"),
                ("slotUnknown", "pre", "pre", "Inherits Primary look · slot-15 contents unknown"),
                ("slotUnknownDirect", "pre", "pre", "Before correction · slot-15 contents unknown"),
            )
            for fixture, primary_selection, secondary_selection, correction in preview_cases:
                preview, preview_errors = open_page(f"?demo=ready&preview={fixture}")
                preview_state = browser_state(preview)
                require(preview_state["primarySelection"] == primary_selection,
                        f"{fixture} Primary selection is wrong")
                require(preview_state["secondarySelection"] == secondary_selection,
                        f"{fixture} Secondary selection is wrong")
                require(preview_state["secondaryCorrection"] == correction,
                        f"{fixture} visible Secondary correction is wrong")
                if fixture.startswith("slotUnknown"):
                    visible_copy = (preview_state["primaryCorrection"] + " " +
                                    preview_state["secondaryCorrection"]).lower()
                    require("tune" not in visible_copy and "confirmed" not in visible_copy,
                            f"{fixture} falsely claims tune knowledge")
                    require(preview_state["outputComparison"] == "Pre-correction references match",
                            f"{fixture} does not qualify its output as pre-correction")
                require(not preview_errors,
                        f"{fixture} console/page errors: " + " | ".join(preview_errors))
                preview.screenshot(
                    path=str(SCREENSHOTS / f"preview-{fixture}-full-1600@2x.png"),
                    full_page=True,
                )
                preview.close()

            transport, transport_errors = open_page("?demo=transport")
            transport.locator('[data-stimulus="bounded"]').click()
            require(browser_state(transport)["txCount"] == 0,
                    "local source selection emitted transport before Test")
            transport.locator("#sendStimulusBtn").click()
            transport.wait_for_function("__colourLabWorkbench.transaction === null && !__colourLabWorkbench.app.sourceDirty")
            after_source = browser_state(transport)
            require(after_source["txCount"] == 3, "Source transaction did not emit exactly target, stops, mode")
            require([line.split("=", 1)[0] for line in after_source["txTrace"]] ==
                    [":paint_target", ":paint_stops", ":paint"],
                    "Source transaction order is wrong")
            transport.locator("#gainR").fill("1.400")
            transport.locator("#gamma").fill("2.200")
            require(browser_state(transport)["txCount"] == 3,
                    "Tune draft emitted transport before Apply")
            transport.locator("#applyTuneBtn").click()
            transport.wait_for_function("__colourLabWorkbench.transaction === null && !__colourLabWorkbench.app.tuneDirty")
            after_tune = browser_state(transport)
            require(after_tune["txCount"] == 5, "Tune transaction did not emit gain plus gamma")
            require(after_tune["confirmedTune"]["gain_r"] == 1.4 and
                    after_tune["confirmedTune"]["gamma"] == 2.2,
                    "Tune transaction lost one field confirmation")
            transport.locator("#saveBtn").click()
            transport.wait_for_function("__colourLabWorkbench.transaction === null")
            after_save = browser_state(transport)
            require(after_save["persistence"] == "saved", "Save did not confirm session persistence")
            require(not transport_errors,
                    "transport console/page errors: " + " | ".join(transport_errors))
            transport.close()

            source_revision, source_revision_errors = open_page("?demo=transport&ackDelay=75")
            source_revision.locator("#sendStimulusBtn").click()
            source_revision.locator('[data-stimulus="solid"]').click()
            source_revision.wait_for_function(
                "__colourLabWorkbench.transaction === null && __colourLabWorkbench.txCount === 3"
            )
            source_revision_state = browser_state(source_revision)
            require(source_revision_state["sourceDirty"],
                    "mid-sequence Source edit was silently marked confirmed")
            require(source_revision_state["txTrace"][-1] == ":paint=stops",
                    "Source sequence did not preserve its start-of-sequence snapshot")
            require(not source_revision_errors,
                    "Source revision console/page errors: " + " | ".join(source_revision_errors))
            source_revision.close()

            tune_revision, tune_revision_errors = open_page("?demo=transport&ackDelay=75")
            tune_revision.locator("#gainR").fill("1.400")
            tune_revision.locator("#gamma").fill("2.200")
            tune_revision.locator("#applyTuneBtn").click()
            tune_revision.locator("#gamma").fill("2.800")
            tune_revision.wait_for_function(
                "__colourLabWorkbench.transaction === null && __colourLabWorkbench.txCount === 2"
            )
            tune_revision_state = browser_state(tune_revision)
            require(tune_revision_state["tuneDirty"],
                    "mid-sequence Tune edit was silently marked confirmed")
            require(tune_revision_state["confirmedTune"]["gamma"] == 2.2,
                    "Tune sequence did not preserve its start-of-sequence snapshot")
            require(tune_revision.locator("#gamma").input_value() == "2.800",
                    "newer local Gamma edit was overwritten by a reply")
            require(not tune_revision_errors,
                    "Tune revision console/page errors: " + " | ".join(tune_revision_errors))
            tune_revision.close()

            preempt, preempt_errors = open_page("?demo=transport&ackDelay=150")
            preempt.locator("#sendStimulusBtn").click()
            preempt.locator("#stopBtn").click()
            preempt.wait_for_function(
                "__colourLabWorkbench.transaction === null && "
                "__colourLabWorkbench.txTrace.some(line => line === ':paint=off') && "
                "!__colourLabWorkbench.recoveryPending && "
                "__colourLabWorkbench.coreState.confirmed.paint.mode === 'off'"
            )
            preempt_state = browser_state(preempt)
            require(preempt_state["sourceDirty"],
                    "priority Stop cleared the superseded Source draft")
            require(preempt_state["transaction"] is None,
                    "priority Stop left the Source sequence hung")
            require(not preempt_errors,
                    "priority Stop console/page errors: " + " | ".join(preempt_errors))
            preempt.close()

            partial, partial_errors = open_page("?demo=transport&failCommand=tune_gamma")
            partial.locator("#gainR").fill("1.400")
            partial.locator("#gamma").fill("2.200")
            partial.locator("#applyTuneBtn").click()
            partial.wait_for_function(
                "__colourLabWorkbench.transaction === null && "
                "__colourLabWorkbench.coreState.needsResync && "
                "__colourLabWorkbench.txTrace.some(line => line === ':paint=off') && "
                "!__colourLabWorkbench.recoveryPending && "
                "__colourLabWorkbench.coreState.confirmed.paint.mode === 'off'"
            )
            partial_state = browser_state(partial)
            require(partial_state["decision"] == "safety_blocked",
                    "partial Tune sequence did not fail the Device Safety gate")
            require(partial_state["needsResync"],
                    "partial Tune sequence did not require Resync")
            require(partial_state["tuneDirty"],
                    "partial Tune sequence discarded the local draft")
            require(":paint=off" in partial_state["txTrace"],
                    "partial Tune sequence did not queue Stop output")
            require(not partial_errors,
                    "partial sequence console/page errors: " + " | ".join(partial_errors))
            partial.close()

            recovery, recovery_errors = open_page("?demo=transport&ackDelay=10")
            recovery.locator("#stopBtn").click()
            recovery.wait_for_function(
                "__colourLabWorkbench.txTrace.some(line => line === ':paint=off') && "
                "!__colourLabWorkbench.recoveryPending && "
                "__colourLabWorkbench.coreState.confirmed.paint.mode === 'off'"
            )
            recovery.evaluate("__colourLabWorkbench.testOnlySetFailCommand('paint')")
            recovery.evaluate("__colourLabWorkbench.testOnlySetDevicePaintMode('ramp')")
            recovery.evaluate(
                "__colourLabWorkbench.testOnlyEmit({kind:'paint',mode:'ramp',target:'both',r:140,g:140,b:140,s:1,v:0.55,stops:[]})"
            )
            recovery.wait_for_function(
                "__colourLabWorkbench.legacyForbiddenDetected && "
                "__colourLabWorkbench.coreState.outputStateUnknown"
            )
            first_incident = browser_state(recovery)
            require(first_incident["legacyRecoveryOffGeneration"] == 0,
                    "new Ramp incident reused an earlier manual Stop confirmation")
            recovery.evaluate("__colourLabWorkbench.testOnlyHydrate()")
            recovery.wait_for_function(
                "__colourLabWorkbench.coreState.connection === 'ready' && "
                "__colourLabWorkbench.coreState.confirmed.paint.mode === 'ramp' && "
                "__colourLabWorkbench.legacyForbiddenDetected && "
                "__colourLabWorkbench.coreState.outputStateUnknown"
            )
            stale_proof = browser_state(recovery)
            require(stale_proof["decision"] == "safety_blocked" and
                    stale_proof["safety"] is False,
                    "stale Stop proof reopened the safety gate after a new Ramp incident")
            require(stale_proof["confirmedPaintMode"] == "ramp" and
                    not stale_proof["primaryFramePresent"],
                    "Ramp recovery failure exposed Preview pixels or hid confirmed Ramp state")
            require(stale_proof["legacyRecoveryOffGeneration"] !=
                    stale_proof["legacyRecoveryGeneration"],
                    "failed current-generation Stop was treated as confirmed")
            require(not recovery_errors,
                    "legacy recovery console/page errors: " + " | ".join(recovery_errors))
            recovery.close()

            lost, lost_errors = open_page("?demo=ready")
            lost.evaluate("__colourLabWorkbench.testOnlyDeviceLost()")
            lost_state = browser_state(lost)
            require(lost_state["decision"] == "safety_blocked" and
                    lost_state["needsResync"] and lost_state["outputStateUnknown"],
                    "unexpected device loss did not fail the safety gate closed")
            require(not lost_state["primaryFramePresent"] and
                    lost_state["primaryNonBlack"] == 0,
                    "unexpected device loss left Preview pixels visible")
            require(not lost_errors,
                    "device-lost console/page errors: " + " | ".join(lost_errors))
            lost.close()

            failed_resync, failed_resync_errors = open_page("?demo=transport&failCommand=chip_id")
            failed_resync.evaluate("__colourLabWorkbench.testOnlyDeviceLost()")
            failed_resync.evaluate("__colourLabWorkbench.testOnlyHydrate()")
            failed_resync_state = browser_state(failed_resync)
            require(failed_resync_state["decision"] == "safety_blocked" and
                    failed_resync_state["needsResync"] and
                    failed_resync_state["outputStateUnknown"],
                    "failed Resync erased device-loss uncertainty")
            require(not failed_resync_state["primaryFramePresent"] and
                    failed_resync_state["primaryNonBlack"] == 0,
                    "failed Resync reopened Preview pixels")
            require(not failed_resync_errors,
                    "failed-resync console/page errors: " + " | ".join(failed_resync_errors))
            failed_resync.close()

            policy, policy_errors = open_page("?demo=policy")
            policy_state = browser_state(policy)
            require(policy_state["decision"] == "policy_blocked", "policy fixture did not fail closed")
            require(policy_state["primaryNonBlack"] > 0 and policy_state["secondaryNonBlack"] > 0,
                    "policy failure hid bounded local analysis")
            require(policy_state["sendDisabled"] and policy_state["applyDisabled"] and
                    policy_state["saveDisabled"] and policy_state["exportDisabled"],
                    "policy failure left an output boundary enabled")
            require(policy_state["nonProductVisible"], "policy failure lacks NON-PRODUCT stamp")
            policy.screenshot(path=str(SCREENSHOTS / "policy-blocked-full-1600@2x.png"), full_page=True)
            require(not policy_errors, "policy console/page errors: " + " | ".join(policy_errors))
            policy.close()

            chromatic, chromatic_errors = open_page("?demo=policy")
            four_sector = [
                {"position": 0.0, "rgb": [255, 0, 0]},
                {"position": 0.333, "rgb": [255, 255, 0]},
                {"position": 0.667, "rgb": [0, 255, 0]},
                {"position": 1.0, "rgb": [0, 255, 255]},
            ]
            chromatic.evaluate(
                "stops => __colourLabWorkbench.testOnlyApplyPalette(stops)",
                four_sector,
            )
            four_state = browser_state(chromatic)
            suppression = chromatic.evaluate(
                """() => ({
                  swatches: [...document.querySelectorAll('.stop-swatch')].every(
                    item => getComputedStyle(item).backgroundColor === 'rgb(17, 17, 17)'
                  ),
                  tracks: ['rgbTrack','oklchTrack','hsvTrack'].every(
                    id => getComputedStyle(document.getElementById(id)).backgroundImage.includes('repeating-linear-gradient')
                  )
                })"""
            )
            inspector_before = chromatic.locator("#primaryRgb16").inner_text()
            selected_before = browser_state(chromatic)["selectedLed"]
            chromatic.locator("#primaryCanvas").dispatch_event(
                "pointermove", {"clientX": 300, "clientY": 30, "pointerType": "mouse"}
            )
            inspector_after = chromatic.locator("#primaryRgb16").inner_text()
            selected_after = browser_state(chromatic)["selectedLed"]
            require(four_state["decision"] == "policy_blocked",
                    "four-sector chromatic path was not policy-blocked")
            require(not four_state["primaryFramePresent"] and not four_state["secondaryFramePresent"],
                    "four-sector chromatic path remains present in Preview frames")
            require(four_state["primaryNonBlack"] == 0 and four_state["secondaryNonBlack"] == 0,
                    "four-sector chromatic path remains visible on Preview")
            require(suppression["swatches"] and suppression["tracks"],
                    "four-sector chromatic path remains visible in authoring surfaces")
            require(inspector_before == inspector_after and selected_before == selected_after,
                    "inspector exposed a prohibited chromatic frame")
            require(four_state["txCount"] == 0 and four_state["exportDisabled"],
                    "four-sector chromatic path reached an output boundary")

            six_sector = [
                {"position": index / 5, "rgb": colour}
                for index, colour in enumerate([
                    [255, 0, 0], [255, 255, 0], [0, 255, 0],
                    [0, 255, 255], [0, 0, 255], [255, 0, 255],
                ])
            ]
            chromatic.evaluate(
                "stops => __colourLabWorkbench.testOnlyApplyPalette(stops)",
                six_sector,
            )
            six_state = browser_state(chromatic)
            require(not six_state["primaryFramePresent"] and six_state["primaryNonBlack"] == 0,
                    "six-sector wheel path was not completely suppressed")
            require(six_state["txCount"] == 0,
                    "six-sector wheel path emitted transport")
            require(not chromatic_errors,
                    "chromatic suppression console/page errors: " + " | ".join(chromatic_errors))
            chromatic.close()

            payload, payload_errors = open_page("?demo=policy")
            payload.locator('[data-space="rgb"]').click()
            payload.evaluate(
                "stops => __colourLabWorkbench.testOnlyApplyPalette(stops)",
                [
                    {"position": 0.0, "rgb": [54, 125, 133]},
                    {"position": 0.5, "rgb": [141, 142, 118]},
                    {"position": 1.0, "rgb": [46, 167, 224]},
                ],
            )
            payload_state = browser_state(payload)
            require(payload_state["sourcePolicyOk"] is True and
                    payload_state["payloadPolicyOk"] is False,
                    "compiled RGB payload counterexample did not reach the intended gate")
            require(payload_state["decision"] == "policy_blocked" and
                    not payload_state["primaryFramePresent"] and
                    payload_state["primaryNonBlack"] == 0,
                    "unsafe compiled RGB payload remained visible or output-eligible")
            require(payload_state["txCount"] == 0 and payload_state["exportDisabled"],
                    "unsafe compiled RGB payload reached an output boundary")
            require(not payload_errors,
                    "payload policy console/page errors: " + " | ".join(payload_errors))
            payload.close()

            safety, safety_errors = open_page("?demo=safety")
            safety_state = browser_state(safety)
            require(safety_state["decision"] == "safety_blocked", "safety fixture did not fail")
            require(safety_state["primaryNonBlack"] == 0 and safety_state["secondaryNonBlack"] == 0,
                    "safety failure did not make Preview unavailable")
            require(safety_state["sendDisabled"] and safety_state["applyDisabled"] and
                    safety_state["saveDisabled"] and safety_state["exportDisabled"],
                    "safety failure left an output boundary enabled")
            require(not safety_state["stopDisabled"], "safety failure disabled Stop output recovery")
            safety.screenshot(path=str(SCREENSHOTS / "safety-blocked-full-1600@2x.png"), full_page=True)
            require(not safety_errors, "safety console/page errors: " + " | ".join(safety_errors))
            safety.close()

            diagnostics, diagnostic_errors = open_page()
            for stimulus in ("neutral", "solid", "bounded", "card", "rgb", "sv"):
                diagnostics.locator(f'[data-stimulus="{stimulus}"]').click()
                state = browser_state(diagnostics)
                sectors = hue_sector_count(diagnostics)
                require(state["policy"], f"safe source {stimulus} failed its policy")
                require(sectors < 5, f"safe source {stimulus} spans {sectors} hue sectors")
                messages.append(f"SOURCE_{stimulus.upper()}_SECTORS={sectors}")
            diagnostics.locator('label[for="viewDiffusion"]').click()
            diagnostics.screenshot(path=str(SCREENSHOTS / "diffusion-model-full-1600@2x.png"), full_page=True)
            require(not diagnostic_errors,
                    "diagnostic console/page errors: " + " | ".join(diagnostic_errors))
            diagnostics.close()

            for width, label in (
                (740, "responsive-740"),
                (390, "responsive-390"),
                (800, "zoom-200pc-equivalent-800"),
            ):
                responsive, responsive_errors = open_page(width=width, height=900)
                responsive_state = browser_state(responsive)
                require(responsive_state["scrollWidth"] == responsive_state["clientWidth"],
                        f"{label} has horizontal overflow")
                responsive.screenshot(path=str(SCREENSHOTS / f"{label}@2x.png"), full_page=True)
                require(not responsive_errors,
                        f"{label} console/page errors: " + " | ".join(responsive_errors))
                responsive.close()

            focus, focus_errors = open_page()
            focus.locator("#exportBtn").focus()
            outline = focus.locator("#exportBtn").evaluate(
                "element => ({style:getComputedStyle(element).outlineStyle, width:getComputedStyle(element).outlineWidth, colour:getComputedStyle(element).outlineColor})"
            )
            require(outline["style"] == "solid" and outline["width"] == "2px",
                    "keyboard focus outline is not the locked 2 px treatment")
            focus.screenshot(path=str(SCREENSHOTS / "focus-state-full-1600@2x.png"), full_page=True)
            require(not focus_errors, "focus console/page errors: " + " | ".join(focus_errors))
            focus.close()

            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    for message in messages:
        print(message)
    print(f"SCREENSHOTS={len(list(SCREENSHOTS.glob('*.png')))}")
    print(f"FAILURES={len(failures)}")
    for failure in failures:
        print("FAIL " + failure)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
