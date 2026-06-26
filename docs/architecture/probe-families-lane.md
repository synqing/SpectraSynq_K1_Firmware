---
abstract: "Lane contract for extracting the gated-out diagnostic 'probe' command families from serial_menu.h parse_command() — one COMPILE-FLAG-family per PR, via the gate-matched structural lift (same mechanism as beat_director, Increment B). Captain-ratified higher bar (2026-06-26): these are PRODUCTION-OFF but they are DIAGNOSTIC surfaces, so production code/data byte-identity is NECESSARY BUT NOT SUFFICIENT — each family's OUTPUT SCHEMA (row-prefix tokens) must be locked (structural golden pins the handler body incl. routing; a NEW permanent row-prefix static test pins the schema tokens). Encodes the verified per-flag classification, the recommended order (GDFT_HARNESS → MOTION_PROBE → FRAME_DUMP; DEFER VP_PROBE + AP_CAPTURE — they couple to render/audio code), the gate-matched recipe, the ORACLE-LINK note, stop conditions, and the do-not-touch list. FRESH CONTEXT ONLY; re-verify every classification first-hand (SSA)."
---

# Lane — Gated-out diagnostic probe families (serial_menu.h)

> **Predecessors:** the gated serial-families lane is COMPLETE (set_mode/secondary_mode = PR #10; beat_director = PR #11). **main = `6d67858`** · serial_struct golden 17 · `oracle_serial_struct.py` locks 7 families. Read `.claude/handoff.md` + `docs/architecture/gated-serial-families-lane.md` (the proven recipe) first. **FRESH CONTEXT ONLY** (Captain). Classification below is a first-pass (subagent + first-hand spot-check 2026-06-26); the executing session **must** re-verify each family first-hand before LOCK.

## 0 · Posture (Captain-ratified, 2026-06-26) — THE DIAGNOSTIC IS THE PRODUCT
- These handlers are **production-OFF** (each behind its own `#ifdef ENABLE_*`; k1_hardware defines none). A verbatim lift is production-byte-identical by construction — BUT they are **evidence infrastructure**. A probe that flashes green on production-identity while silently renaming/fragmenting/dropping a `GDFTP`/`MP`/`[FDUMP]` row is the LayerSense failure mode.
- **Two-pronged bar, every family:** (1) **production code/data byte-identity** — the CODE/DATA-region binary diff, NOT the `.bin` hash (ESP32 `esp_app_desc.app_elf_sha256` + image-SHA256 + checksum always move when DWARF debug-lines shift; see the beat_director lesson in the handoff) + Flash/RAM size; AND (2) **diagnostic schema locked** — the structural golden pins the handler body (incl. its `command_type` routing + any inline prints), and a **NEW permanent row-prefix static test** pins the schema tokens in their source-of-truth header. Where the schema lives in an UNTOUCHED backing header, the lift preserves it by construction; the static test is the guard against a FUTURE silent drop.
- **One COMPILE-FLAG-family per PR.** Never mix flags. Two commands share a PR only if inseparable under the same flag (e.g. the 3 gdft_* commands).

## 1 · Verified classification (first-pass — RE-VERIFY FIRST-HAND, SSA)
| flag | serial_menu.h | commands | schema row-prefixes (source) | backing (linkage) | r/o vs mut | dedicated env | host schema test? |
|---|---|---|---|---|---|---|---|
| **ENABLE_GDFT_HARNESS** | 2630–2689 (whole else-ifs) | `gdft_probe` `gdft_sweep` `gdft_agc_probe` | `GDFTP,` `GDFTP5,` `GDFTAGC,` (emitted in `diag/gdft_harness.h`, 15 tokens) | `gdft_run_single/sweep/agc_probe` **inline in `diag/gdft_harness.h`** (same flag) | READ-ONLY | `k1_bench_reference_harness` | none (add one) |
| **ENABLE_MOTION_PROBE** | 2691–2770 | `mp_step` `mp_flash` `mp_off` `mp_status` | `"MP …"` line prefixes (handler + `diag/motion_probe.h`) | `motion_probe_arm_step/arm_flash/off/status` inline in `diag/motion_probe.h` (same flag) | MUTATES probe state | `k1_motion_probe` | none (add one) |
| **ENABLE_FRAME_DUMP** | 2592–2613 | `frame_dump` | `[FDUMP] start …` (handler) · per-frame `[FDUMP] …` emitted in `visual/lightshow_modes.h` (NOT moved) | sets 4 inline globals in `system/globals.h` (already visible to handlers.cpp) | MUTATES globals | `k1_hardware_harness` | none (add one) |
| **ENABLE_VP_PROBE_CMD** ⛔DEFER | 2615–2628 | `vp_probe` (`all`/`secondary`) | output in `vp_run_output_probe()`/`vp_run_secondary_bleed_probe()` | **inline in `visual/lightshow_modes.h` = RENDER code** | read-only | `k1_hardware_harness` | `test_vp_probe_mode_coverage_static.py` |
| **ENABLE_AP_STREAM** ⛔DEFER | 2574–2590 | `ap_capture` | `"AP_CAPTURE: armed "` | `ap_capture_arm()` **inline in `audio/i2s_audio.h` = AUDIO code** | MUTATES capture | `k1_hardware_harness` | none |

Also present, OUT OF SCOPE unless explicitly added: `ENABLE_VP_MOTION_LAB` (`vpml`, ~2910) — delegates to `vpml_command()`; classify separately. `tempo_stream` STAYS inline (broader gate — straddle scar).

## 2 · Recommended order (FOLLOW THE FLAGS, not this list, if re-classification differs)
1. **ENABLE_GDFT_HARNESS** — cleanest: read-only, backing inline in `diag/gdft_harness.h` (same flag, no render/audio coupling), schema in that untouched header, dedicated env, device-proven (2026-06-21 GDFTP telemetry). The 3 gdft_* commands ship together (one flag).
2. **ENABLE_MOTION_PROBE** — backing inline in `diag/motion_probe.h` (same flag), dedicated env `k1_motion_probe`; mutates probe state (fine — structural gate locks the body); confirm `motion_probe.h` pulls no render TU.
3. **ENABLE_FRAME_DUMP** — handler only sets `globals.h` globals + prints `[FDUMP] start` (no render include needed for the HANDLER; the per-frame `[FDUMP]` emission in `lightshow_modes.h` is NOT moved). env `k1_hardware_harness`.
- ⛔ **DEFER VP_PROBE + AP_CAPTURE** — lifting them forces `handlers.cpp` to `#include` `lightshow_modes.h` (render) / `i2s_audio.h` (audio) to reach their **inline** backing fns (can't forward-declare an inline). That touches the render/AP-algorithm do-not-touch boundary → needs explicit Captain scoping before extraction.

## 3 · Recipe per flag-family (proven on beat_director; one PR each)
- **CLASSIFY (first-hand):** flag + exact `#ifdef … #endif` bounds; every `strcmp(command_type,"X")`; the OUTPUT row-prefix literals + WHERE they live (handler vs backing header); backing fn linkage (inline-in-same-flag-header → `#include` under the flag; external → forward-decl); read-only vs mutating; the dedicated env (confirm it compiles `serial/*.cpp`); existing test.
- **LOCK** (oracle/golden/MANIFEST + the NEW schema test only; ZERO source): add the family to `oracle_serial_struct.py` FAMILIES; regen `serial_struct.golden.jsonl` under the ORIGINAL inline handlers (clean append); add ≥1 body + ≥1 `command_type`-rename tooth. **PLUS the schema-lock:** add a minimal **permanent static test** (mirror `test_k1_loud_guard_static.py`) asserting the family's row-prefix tokens are present in their source header AND the handler routes each command to its backing fn. Gate Fα PROVEN.
- **EXTRACT** (source + call-site-sever tooth only; golden UNTOUCHED): verbatim lift into `serial_cmd_dispatch_<family>()`, **GATE-MATCHED** — decl (handlers.h) + def (handlers.cpp) + call-site (serial_menu.h) ALL behind `#ifdef ENABLE_<FLAG>` (the tempo_stream straddle scar; never a combined gate). The handler stays inside serial_menu.h's existing `#ifdef`; only the body moves.
- **ORACLE-LINK:** backing fns are `inline` in a `diag/*.h` header guarded by the same flag → `#include` that header in handlers.cpp **under `#ifdef ENABLE_<FLAG>`** (resolves inline within the TU, like `light_mode_next_enabled`). The host replay oracle compiles handlers.cpp with the flag OFF → the whole gated dispatcher preprocesses out → no host-link surgery (same as beat_director).
- **PROVE (re-verify yourself):** struct golden reproduces byte-for-byte UNTOUCHED; statement-identity `diff -w -B` empty; anchor guard green (count==1, `"<name>"` comment placeholder); the new schema test green; Gate Fα all teeth; **`pio -e k1_hardware` production CODE byte-identical** (code/data-region binary diff = 0; Flash/RAM unchanged; symbols absent from the production `.o`); **the family's dedicated env builds with the flag ON** (the gated dispatcher links its backing fns there); full `pytest tests/`.
- **PR:** DRAFT until the branch is final + all local gates green (no half-finished PRs); one flag-family per PR.

## 4 · Stop conditions
- a family's verification would need runtime/DEVICE evidence (a verbatim lift does NOT — but if the only way to confirm schema is to run the probe, STOP) · output schema cannot be locked on host · golden changes during EXTRACT · mutation tooth weakened · production code/data delta OUTSIDE the expected gated area · a command crosses into non-probe behaviour · lifting requires touching render/audio/facade code (VP_PROBE/AP_CAPTURE) · branch/HEAD truth ambiguous → STOP at the exact surface.

## 5 · Do-NOT-touch (Captain scope lock)
`.ino`→`main.cpp` keystone (behaviour-changing — device A/B + Captain eyes-on, NOT this lane) · facade / vp_profile/vp_all · `visual/lightshow_modes.h` + effect/render code (so VP_PROBE/FRAME_DUMP emission sites stay put) · AP/GDFT **algorithm** code (`i2s_audio.h` AP path; `gdft_run_*` bodies are touched only by `#include`, not edited) · device flash / serial write / production default flips · device registry.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-26 | agent:claude-code (CTO) | Created after the gated serial-families lane completed (PR #10/#11 merged). Captain ratified the diagnostic-as-product bar (schema-lock necessary, not just byte-identity). Classification from a fresh-context subagent + first-hand spot-check; KEY refinements: VP_PROBE + AP_CAPTURE DEFER (render/audio-code coupling via inline backing fns → would violate do-not-touch); FRAME_DUMP handler-lift is clean (emission site untouched); the "device evidence" stops conflate verifying the probe with verifying the verbatim lift (the lift is host-provable). Recommended first family = GDFT_HARNESS. |
