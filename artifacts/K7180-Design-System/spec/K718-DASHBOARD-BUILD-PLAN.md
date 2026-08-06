---
abstract: "Locked spec + gated mockup→firmware bridge plan for the K718 'Remoted' dashboard. Satisfies the Captain's freeze RESUME condition (a locked written spec). Encodes the hardware renderability constraints (360x360 ST77916/CST816S/LVGL, no blur/radial/full-screen-additive), the firmware-verified 71-control BLE-MIDI contract the dashboard must drive, the KEEP/CUT inventory honouring the text-protection law, and a 7-phase plan where every phase is done on a CONCRETE objective gate (first gate = hello-world on the real 360x360 panel), never on taste. Includes an anti-churn lock clause. Does NOT itself lift the freeze — Captain instruction naming K718 is still required."
---

# K718 "Remoted" Dashboard — Locked Spec & Gated Build Plan

> ⛔ **HARD LAWS — see [`K718-UX-LAWS.md`](./K718-UX-LAWS.md) (Captain-ratified 2026-06-30):** NO on-screen PEND/CONF/status text (out-of-band only: LED ring red×5 / solid-red + speaker + haptic) · NO centred value-number · NO on-screen rim dots · mic-honest centre field · single-hand rotary+touch radial model. Banned patterns stop the work.

> **This document is the written spec required by the Captain's freeze RESUME
> condition.** It does not by itself lift the freeze: resume still requires an
> explicit Captain instruction naming K718. When that instruction is given, this
> is the locked spec the work executes against. Root-cause evidence:
> [`K718-CHURN-FORENSIC.md`](./K718-CHURN-FORENSIC.md).
>
> **Authority order:** firmware/source truth > on-device runtime proof > this spec
> > any browser mockup. Where a mockup and this spec disagree, this spec wins;
> where firmware and this spec disagree, firmware wins (update this spec).

## 1. Hardware reality & hard renderability constraints

**Device:** Guition JC3636K718_P — ESP32-S3R8 (LX7 dual-core 240 MHz, **no 2D
GPU/PPA**), 512 KB SRAM / 8 MB PSRAM / 16 MB Flash, 1.8" round IPS **360×360**,
**ST77916 QSPI** display driver, **CST816S** capacitive **single**-touch, rotary
encoder (**rotation only — no hardware press**), **13-LED physical ring outside
the glass**, **BLE-MIDI-only** transport, **LVGL 8.3.x software render**.

> Driver/touch confirmed from the linked knob firmware map
> (`JC3636_K718_REMOTED_BLE_V1.ino.map`): `lvgl` ×11182, `ST77916` ×539,
> `esp_lcd` ×3798, **`CST816S` symbols present, `CST820` = 0** (refutes the
> earlier web-sourced CST820 guess). Resolution 360×360 + BLE-only confirmed by
> `HANDOVER.md:14-17`.

**Hard constraints (CUT list is derived from these — §3):**

| # | Constraint | Consequence |
|---|-----------|-------------|
| H1 | Native target is **360×360** round (NOT 480/960). | Rescale all mockup geometry ×0.75. Keep a ~6% radius bezel-safe margin. |
| H2 | **No runtime Gaussian blur / `shadowBlur`** (no HW blur; none in LVGL 8.3). | Bake all glow into static sprite assets offline. |
| H3 | **No runtime radial gradients** (LVGL 8.3 = linear only). | Bake gradient sprites / use LUTs. |
| H4 | **No full-screen multi-pass additive** (`globalCompositeOperation='lighter'`) per frame. | Additive only on small pre-baked regions. |
| H5 | **Dirty-rect rendering mandatory.** | Static bg drawn once; redraw only changed zones. |
| H6 | Frame budget 16.67 ms must cover SW render **+ QSPI flush (~6–13 ms for full 360×360 RGB565, clock TBD)** + BLE-MIDI + touch + LVGL. | Full-screen recomposite is not viable at 60 fps; reserve ≥40% for non-render work. |
| H7 | **No per-glyph runtime arc/curved text.** | Pre-render curved labels or use straight tangential labels; promote live values to a centre disc. |
| H8 | **Zero heap allocation in the render loop.** | Object pools + ring buffers (`esp32-render-path-safety`). |
| H9 | Full RGB565 framebuffer = 253 KB (double-buffered 506 KB). | Place in PSRAM, or use partial LVGL draw buffers; 512 KB SRAM is tight alongside the BLE stack. |
| H10 | The **13-LED trust ring is physical hardware outside the glass.** | Drive the real ring for trust/confirm; do NOT emulate it on the panel. |
| H11 | **BLE-MIDI commit/CONF is unbacked — K1 never acks the knob.** | All confirm feedback is **local-optimistic only**; no truthful "CONFIRMED" state exists. |

## 2. Firmware / BLE control-map contract the dashboard must drive

**Does K718 firmware exist? YES.** A built, compiling K718 knob firmware exists
(`JC3636_K718_REMOTED_BLE_V1.ino`, knob commit `9c0d1cb74042`) with the LVGL +
ST77916 + CST816S display stack **linked**, the rotary encoder, and the full
71-control BLE-MIDI emission path. All firmware-side gates are green (exit 0):
contract parity, encoder parity, encoder selftest, remoted-emission gate +
selftest, Arduino compile. **What does NOT yet exist: (a) any on-device render
proof — Phase G found the knob ABSENT from the serial bus (`device_absent`),
manifest status `PARTIAL_COMPLETE_DEVICE_BLOCKED`; and (b) the designed dashboard
UI itself.** So the bridge is "drive the existing, proven BLE contract from a new,
on-device-gated UI," not a from-scratch firmware port.

**Locked contract (the dashboard must emit exactly this — do not redefine):**

- **Transport: BLE-MIDI only.** WiFi is rejected. (`k1-ap-websocket-stack` does
  not apply to the knob link.)
- **71 controls**, frozen by a registry→BLE-MIDI map oracle + parity gate:
  - registry `control_count == 71`; map covers exactly 71/71, no collisions;
    every control typed; **calibration controls are protected**.
  - registry md5 `78fb9af986da…`; contract SHA-256
    `5e4dd4c1804a4f29d6bd097918c463c003dad0cc0ae89040ad5074d3b86690ab`;
    K1/knob JSON byte-match = True.
- **K1-side decoder:** `SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.{cpp,h}`,
  compiled under `-DSB_K1_BLE_REMOTED`; host test
  `tests/test_ble_midi_firmware_decoder.py`.
- **Light modes:** **30 enumerated / 22 enabled** (from `config_types.h`);
  authoritative **disabled set = {0,1,2,4,5,6,10,17}**. The dashboard's mode list
  MUST be generated from `config_types.h`, never hand-typed, and must not expose a
  disabled mode.
- **No K1→knob acknowledgement** (see H11) — confirm UI is local-optimistic.

## 3. KEEP (locked design laws) vs CUT

### KEEP — locked, may not be re-litigated (see §6 anti-churn)
- **Text-protection law** (Captain-ratified, obs #71725): rim/radial text is
  allowed **only if size-aware AND given a keep-out scrim**; it is **never
  blanket-deleted**. Minimum legible size is verified on-device, not in browser.
- **Freeze + resume discipline** (obs #72590): one canonical artifact, no new
  variant files, resume only on Captain instruction + this locked spec.
- **Firmware truth** (§2): BLE-MIDI-only, the 71-control contract bytes, the
  22/30 modes + disabled set, no false CONF, the physical 13-LED ring.
- **Native 360×360 round** target with bezel-safe margin (H1).
- **Centre disc carries live values** (legible); labels straight/tangential (H7).

### CUT — deleted scope (derived from §1 hardware reality)
- 960×960 / 480 geometry → rescale to 360 (H1).
- Runtime Gaussian/`shadowBlur` glow → baked sprites (H2).
- Runtime radial gradients → baked/LUT (H3).
- Full-screen multi-pass additive `lighter` compositing per frame (H4).
- Per-glyph runtime arc/curved text (H7).
- On-glass **emulated** 13-LED trust ring (H10 — drive the physical ring).
- The "60 fps full-screen composited glow" mandate (spec Rule M-1) — unreachable.
- Any "CONFIRMED" screen implying a real ack (H11).
- **Variant proliferation**: candidate-dial galleries, T1–T6 theme fan-outs,
  N-option viz menus — CUT until *after* the first on-device gate passes.

> **Gap (not a deletion):** the fine-grained taste-side component KEEP/CUT
> inventory that forensic Lane D would have produced was not delivered (Lane D
> arrived as a duplicate). The CUT list above is hardware-derived and the KEEP
> list is law-derived; treat neither as the exhaustive *component* inventory.
> See Risks.

## 4. Gated mockup → firmware bridge plan

**Anti-churn principle: no phase is "done" on taste. Each phase is done on a
concrete, objective gate, run in infra or on-device. Captain eyes-on is a
tracked, NON-blocking follow-up, never the gate.** One unit = one commit;
rollback-on-red.

| Phase | Goal | Acceptance GATE (objective) |
|-------|------|------------------------------|
| **P0 — Scope & spec lock** | Resolve the BRIEF (effect-select-only) vs HANDOVER (full dual-channel) conflict into ONE written scope; name the ONE canonical git-tracked artifact; locate & version-control the knob firmware **source** (only built binaries are in-repo today). | This spec + the resolved single-scope statement are committed to git in-repo; the knob source builds reproducibly from a tracked tree; Captain one-time scope sign-off recorded. No new variant files exist. |
| **P1 — Hello-world on the real panel** | Render a known LVGL test pattern at native 360×360 on the actual JC3636K718_P, on the device with verified chip ID. | Serial log + photograph of the physical 360×360 panel showing the test pattern; device present on serial (resolves `device_absent`); chip ID matches the knob identity. **This is the first gate — nothing proceeds until physics is proven.** |
| **P2 — Static dashboard skeleton + render loop** | Baked static background + centre value disc + dirty-rect loop; zero heap in the render path. | On-device sustained FPS ≥ agreed floor, logged via a serial frame counter (objective number, not taste); render-path lint passes `esp32-render-path-safety` (no heap alloc in loop). |
| **P3 — Input → BLE-MIDI emission parity** | Encoder + touch drive the exact 71-control contract. | `knob_contract_parity` + `knob_remoted_emission` gates exit 0 against registry md5 `78fb9af986da` / contract SHA `5e4dd4…`; round-trip into the K1 decoder gate green (`test_ble_midi_firmware_decoder.py`). Reuses the existing oracle — no new contract invented. |
| **P4 — Effect-select face (locked single slice, BRIEF §7)** | Select among the 22 enabled modes; local-optimistic confirm only; drive the physical 13-LED ring. | On-device: selecting each enabled mode changes K1 state (observed on K1 serial/LED); mode list is generated from `config_types.h` (parity check), no disabled mode {0,1,2,4,5,6,10,17} is selectable; no "CONFIRMED"/ack screen present. |
| **P5 — Legibility & visual hardening** | Apply the text-protection law and bake all glow/gradient assets. | Every rim/radial label passes the text-protection rule (size-aware + keep-out scrim) verified on an on-device photo at native res; render-path lint confirms zero `shadowBlur` / radial-gradient / full-screen-additive in the firmware path; frame budget (P2 floor) still met. |
| **P6 — Acceptance & freeze-lift package** | Assemble the decision-grade evidence pack for Captain. | Full gate battery green in infra (contract parity, emission, encoder, K1 decoder pytest, render-path lint, on-device FPS, on-device photo pack); ONE canonical artifact, atomic commits, rollback-on-red demonstrated. Captain eyes-on sign-off is tracked & non-blocking. |

## 5. Reuse / production-pattern hooks
- Render path: `esp32-render-path-safety`, `embedded-graphics-patterns`
  (dirty-flags, object pools, ring buffers, baked sprites).
- Effects/contract truth: `config_types.h` is the single source for the mode set;
  the existing registry→map oracle is the single source for the 71-control bytes.
- Build/gate: the existing `artifacts/ble_midi_71_*` gate scripts are the harness
  — extend them, do not author a parallel one (`autonomous-agentic-build`: the
  harness is the product).

## 6. ANTI-CHURN clause (locked — derived from the root cause)

The following are LOCKED and **may not be re-litigated** without an explicit
Captain scope-change instruction. Re-opening any of them from taste alone is the
churn symptom and is forbidden as a substitute for passing a gate:

1. **Transport is BLE-MIDI only.** WiFi stays rejected.
2. **The 71-control contract** (registry md5 `78fb9af986da`, SHA `5e4dd4…`) is
   frozen; the dashboard conforms to it.
3. **Native target is 360×360.** No 480/960 geometry.
4. **Banned render techniques** (H2–H4, H7): no runtime blur, radial gradient,
   full-screen additive, or per-glyph arc text — bake offline.
5. **No false CONF** — confirm is local-optimistic only (H11).
6. **ONE git-tracked canonical artifact. No new variant files / galleries /
   theme fan-outs** until the first on-device gate (P1) passes.
7. **Gates are objective and on-device.** Taste is a tracked, non-blocking
   follow-up — never a gate, never a convergence signal.
8. **Text-protection law** stays in force (KEEP §3).

> "Produce another mockup / gallery / spec / theme-variant" is the churn symptom.
> The only progress signals are a passed gate and a committed, gated slice.

## 7. Risks / open gaps (do not fabricate around these — surface them)

1. **Lane C & Lane D forensic returns were not delivered** (duplicated A/B). The
   firmware contract here was re-verified from repo source and is HIGH-confidence;
   the taste-side **component-level** KEEP/CUT inventory is UNVERIFIED — do not
   treat §3's CUT/KEEP as the exhaustive component list.
2. **Device availability blocks P1.** Phase G found the knob ABSENT from serial
   (`device_absent_20260628.log`). The "hello-world on panel" gate may itself be
   blocked until the physical device is on-hand and flashable in this environment
   — confirm before committing to any timeline.
3. **Knob firmware SOURCE is not in this repo** — only built `.bin/.elf/.map`
   (knob commit `9c0d1cb`). P0 must locate and version-control the source or the
   build is not reproducible/rollbackable.
4. **Scope conflict unresolved** — BRIEF (effect-select-only) vs HANDOVER (full
   dual-channel controller). P0 must resolve it or re-churn recurs (failure mode 4).
5. **QSPI clock unknown (40 vs 80 MHz)** → flush time 12.6 vs 6.3 ms → FPS ceiling
   is provisional until measured on-device (H6). Read the board init to resolve.
6. **LVGL pin (8.3.11 vs 9) and PSRAM framebuffer budget** alongside the BLE
   stack are unverified (H9) — confirm before committing the draw-buffer strategy.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:claude-code (SSA synthesis) | Created. Locked spec satisfying the freeze RESUME condition: hardware constraints (firmware-verified CST816S/ST77916/LVGL), the firmware-locked 71-control BLE-MIDI contract (k718FirmwareExists=yes), KEEP/CUT honouring the text-protection law, a 7-phase gate-driven bridge plan (first gate = hello-world on the real 360×360 panel), an anti-churn lock clause, and surfaced risks for the missing Lane C/D content. |
