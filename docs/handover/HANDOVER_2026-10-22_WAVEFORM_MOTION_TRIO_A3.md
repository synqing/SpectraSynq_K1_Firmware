# Waveform motion trio (A3) — flag-gated native motion levers on mode 8

Ruling: Captain, 2026-10-22 — "A3 motion trio, flag-gated, that's what we'll do."
Executor: Claude Code or Codex on the Mac, in `/Users/spectrasynq/SpectraSynq_K1_Firmware`. Reviewer: Claude. Oracle: Astra's bench at `SpectraSynq-PRISM/K1-S3/bench/waveform-oracle/`.

## 0. Read in this order (stop and report if a file is missing; do not substitute)

| # | Path | Why |
|---|---|---|
| 1 | `docs/process/SPECTRASYNQ-GIT-DOCTRINE.md`, `docs/process/SPECTRASYNQ-HOUSEKEEPING-DOCTRINE.md` | Lane branch, commit/record vs integrate, no auto-commit, `_scratch` birth rule |
| 2 | `docs/defects/` (DEF-001, DEF-002) and the tempo-lane rulings in `docs/architecture/tempo-lock-hardening-plan.md` | The flag-gated / off-flag-byte-identical discipline this lane copies; the tempo lane is live in this checkout — do not touch `k1_tempo*` |
| 3 | `docs/architecture/effect-decomposition/01-waveform-class.md` §Pass 4 lever table, `LEVERS-MATRIX.md` §0–§1 | The three levers and their current constants |
| 4 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform.cpp` (mode 8), `light_mode_waveform_fast.cpp` (7), `light_mode_waveform_hybrid.cpp` (11, inverted law) | Mechanism; the fade line; where the law already differs across the class |
| 5 | Trace of `square_iter`: `system/config_types.h`, `system/globals_config.cpp`, `visual/render_params.h/.cpp`, `serial/serial_cmd_handlers.cpp`, `serial/serial_menu.cpp`, `control/k1_control_facade.cpp`, `network/k1_ble_midi_map.h`, `docs/protocol/k1-ws-controls-registry.yaml`, `docs/protocol/k1-ble-midi-map.json`, `system/presets.h` | The exact path a native parameter walks; copy it, do not invent another |
| 6 | `tools/esp_emulator/run.py` (`SUPPORTED_COMMANDS`) | The bench oracle rejects commands not on this list |
| 7 | `SpectraSynq-PRISM/K1-S3/bench/waveform-oracle/README.md` and `evidence/2026-10-22/delivery-evidence-2026-10-22-v2.json` | How to render a comparison and what a receipt looks like |
| 8 | `/Users/spectrasynq/.codex/visualizations/2026/10/21/01a15d95-48fe-72d1-86f3-7a193ddad244/waveform-workbench-review.html` and `/Users/spectrasynq/.codex/visualizations/2026/10/21/01a15d95-48fe-72d1-86f3-7a193ddad244/waveform-lever-atlas.html` (open locally in a browser; the canvases draw on load) | The review and the atlas that ranked these three levers. Reference only — the ruling and the four names are in §1 of this file, not in the atlas |

## 1. Hard rules

- Scope is mode 8 only. Modes 7/11/18/32 untouched. No audio-pipeline, tempo, GDFT or registry-v2 work.
- Flag `K1_WF_MOTION_TRIO` (build-time) gates ALL new code. With the flag off, `firmware.bin` for `k1_main_rpl_emu` must be byte-identical to the pinned baseline (`05ace4cb…`, hash in `K1-S3/bench/waveform-oracle/engine/manifest.json`), proven by SHA-256, not by "looks the same".
- With the flag on and all four values at their defaults, the oracle's `changed_values` against the baseline capture must be 0 on the retained real-music passage (same track, same passage, same recipe) — the default preserves today's behaviour exactly.
- Defaults are today's constants: law = shorter, depth = 0.10, follow = 0.08, scroll = 1 px/hop. Ranges: depth 0.02–0.25, follow 0.02–0.60, scroll 1–8 integer px/hop (dt-scaling is mode 7's job; keep mode 8 hop-locked).
- Four parameters, no more: `wf_persist_law` (enum 0 shorter / 1 constant / 2 longer), `wf_persist_depth`, `wf_follow`, `wf_scroll`. Names are final; they are also the K1 Live pattern control names later.
- Walk the `square_iter` path for each: CONFIG field + default, RenderParams snapshot, serial parse + help + dump, facade range check, BLE map row, both protocol registry files, presets. Add the four names to the emulator `SUPPORTED_COMMANDS`.
- No physical device. Emulator only. No rebuild of any lane other than `k1_main_rpl_emu` and the hardware env needed to prove the flag-off hash.
- Git doctrine: lane branch `lane/k1-wf-motion-trio`; commit/record only; no merge; push at session end; CHANGELOG entry prepared, not applied to main.
- Receipts never mutated; new dated receipts only.

## 2. Execution order

1. Build baseline with the flag off; record `firmware.bin` SHA-256; confirm it equals the manifest hash. If it does not, STOP — the checkout is not at the oracle's baseline; report and do nothing else.
2. Add the four parameters along the `square_iter` path, all inside `#if K1_WF_MOTION_TRIO`. In `light_mode_waveform.cpp`: EMA coefficient from `wf_follow`; fade = `1 − depth · law(|peak|)` with law ∈ {|peak|, 1, 1−|peak|}; shift count from `wf_scroll` (both mirror and non-mirror branches).
3. Rebuild flag-off; prove byte-identical (gate 1).
4. Rebuild flag-on; render the retained passage on the oracle with defaults; prove `changed_values == 0` (gate 2).
5. Render four variations on the same passage: law=longer; depth=0.03; follow=0.30; scroll=3. Each must change native output (`changed_values > 0`) and each must reproduce exactly on a second fresh run (gate 3).
6. Save one variation as a bench effect, reload, re-render, prove identical (gate 4).
7. Issue the receipt and a four-panel contact sheet (defaults + three variations) for Captain's eye.

## 3. Defaults for anything not ruled

- Enum carried as integer over serial (`wf_persist_law=2`), with the three words in the help text.
- BLE map: CC14 rows for depth/follow/scroll; law as a 3-value CC.
- Flag defined in `platformio.ini` for `k1_main_rpl_emu` only during this lane; hardware envs stay flag-off.
- If the oracle's parser allow-list is hash-checked (it is — `host-tools` hashes in the manifest), update the manifest with a dated note; do not silently re-hash.

## 4. Out of scope

Any fifth parameter; dt-scaled scroll on mode 8; chroma/colour levers; position curve; asymmetric follower; registry v2; Tab5/deck exposure; K1 Live port; hardware flash.

## 5. Output paths

- Source: lane branch in `SpectraSynq_K1_Firmware`.
- Evidence: `SpectraSynq-PRISM/K1-S3/bench/waveform-oracle/evidence/<date>/motion-trio/` — baseline hash, flag-off hash, four gate receipts, contact sheet, `SHA256SUMS`.
- Handover close-out: append results to this file under `## 6. Results`; do not rewrite sections 0–5.

## 0b. Contract alignment (added 2026-10-22, Captain ruling)

The effect-control contract v1 is being admitted into PRISM-Core (`PRISM-Core/_scratch/control-contract_20261022/HANDOVER.md`). The four names, types, ranges, defaults and enum values in §1 are final in both briefs; the contract carries them unchanged as `examples/waveform-mode8.json`. A3 does not wait for that lane and does not read PRISM-Core. If a reviewer finds the two disagree, the A3 brief §1 wins and the contract example is corrected.

## 6. Results — 22 October 2026

Implemented all four approved controls on the separate `lane/k1-wf-motion-trio`
source branch. The active tempo branch, source and index were not used for the
A3 build. Records use an alternate index and a commit rooted at the actual
05ace4cb oracle source, without a new worktree or a checkout switch.

The first baseline mismatch stopped execution as required. Captain then explicitly
ordered diagnosis and repair. The cause was a different active source revision
plus unrecorded build provenance/compiler date inputs. The retained original export,
original build log and ELF established the exact inputs. Recovery uses provenance
epoch 1792509834 and compiler SOURCE_DATE_EPOCH=1792538651 at the original build
path. Full firmware and ELF hashes match; no repin, stripping, binary patch or
normalised comparison was used. Original failed receipts remain intact.

| Gate | Result |
|---|---|
| 1: final flag-off image | PASS — firmware `6329fe3f28f9ec330687792fdb26b8059196139b665d5a3603333d7ecd50a6b5`; ELF also exact |
| 2: enabled defaults | PASS — 0 changed values, same PCM and 1,334 frames on both edges |
| 3: four variations | PASS — changed values 572,574 / 572,632 / 534,144 / 592,824; every fresh repeat exact |
| 4: save/reload | PASS — page save, full reload, same passage, 0 changed values against the saved variation |

The saved effect is **Waveform · longer on loudness · A3**. Its record carries
candidate firmware `ae3e1da7bf984505ce328bd99433faf73f483ce575e3240c083625fa3a7c5d38`,
manifest and source-overlay identity. Workbench: `K1-S3/bench/waveform-oracle/page/index.html`,
served at http://127.0.0.1:65036/k1-authoring-product-review.html.

Host checks preserve the original 68-control deck digest and all golden outputs;
they separately validate the four conditional declarations and reject planted
range/default/type/address faults. The hardware configuration compiled with A3
absent. The original full-suite attempt (16 failed / 1,739 passed / 21 skipped)
is retained: 13 failures were missing Git context and three were conditional-oracle
integration. Corrected focused runs passed: 227 Git-context tests, nine golden/deck
and deliberate-regression tests, nine A3 checks, 19 bench tests and service checks.
This is cumulative checked coverage, not a claim that one final monolithic full
suite was run green. No hardware, main merge, lane repin or A3 release tag.

Evidence and hashes: `/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-PRISM/K1-S3/bench/waveform-oracle/evidence/2026-10-22/motion-trio/RESULTS.md`
and `SHA256SUMS-final` beside it. The four-panel `contact-sheet.png` and actual
`workbench-final.png` were opened and visually inspected. Reproduction and prepared
CHANGELOG are retained under `_scratch/waveform-motion_20261022/` on the source branch.

Scope of proof: the retained Loreen MP3 passage requested at 68–78 seconds, hop-aligned
to 67.995–78.000 seconds, with the same preceding PCM. No physical appearance,
full-song continuous state or other native mode modification is claimed.
