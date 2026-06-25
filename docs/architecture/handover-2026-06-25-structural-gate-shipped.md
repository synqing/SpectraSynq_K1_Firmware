---
abstract: "CURRENT handover (2026-06-25, supersedes handover-2026-06-25-serial-decomposition.md) for the SpectraSynq K1 de-Arduino serial_menu.h decomposition. main=614706c (firmware tip da4258e, HARDWARE-SMOKED on the main K1). Both behaviour-lock recipes are now proven on host AND silicon: (A) replay-lock for GLOBAL-WRITE families, (B) the STRUCTURAL-CONTRACT GATE (oracle_serial_struct.py) for FUNCTION-CALL families — the keystone, built + Gate-Fα-proven + exercised by real extractions (queue PR#6, smart_director/smart_visual/edge_mixer PR#7). Encodes both recipes, the next facade-free families (preset → secondary_* → gated set_mode/beat_director), the load-bearing discipline, and the device/flash reality (incl. the script-pty flash gotcha). Read this + .claude/handoff.md before touching anything."
---

# Handover — K1 serial_menu.h decomposition: structural gate shipped + device-smoked (2026-06-25)

> **You are the SpectraSynq CTO-agent continuing a de-Arduino modernization.** Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware` (origin `github.com/synqing/SpectraSynq_K1_Firmware`). DECOY repo to NEVER touch: `/Users/spectrasynq/SensoryBridge-main 9`. Goal: decompose the `serial_menu.h` god-header into clean TUs **without regressing the musical light-show** (perceptual product = sacred; behaviour-preservation = the floor). Method = **strangler-fig: verbatim-lift handler families out of `parse_command()` into `serial_cmd_dispatch_*()` behind golden behaviour-locks.** THE VERIFICATION HARNESS IS THE PRODUCT.

## 0 · TL;DR — where we are
- **`main` = `614706c`** (CI-green). Firmware tip **`da4258e`** is **HARDWARE-SMOKED** on the main K1 (`614706c` = `da4258e` + a docs-only registry commit, so the device firmware == main). Active branch **`feat/serial-decomposition`** (fresh off main, even 0/0).
- **Two behaviour-lock recipes, both proven on host AND silicon:**
  - **(A) Replay-lock** (`oracle_serial_replay.py`) for **GLOBAL-WRITE** handlers (mutate an `inline` global the host can observe). Captures the triple: echo text + global/CONFIG delta + side-effect flags.
  - **(B) STRUCTURAL-CONTRACT GATE** (`oracle_serial_struct.py`) — **THE KEYSTONE** — for **FUNCTION-CALL** handlers (call host-stubbed subsystems → replay-blind). Pure source-parse; pins per-command `(normalized body, reachable-from-parse_command, presence)`, invariant across a verbatim lift (TRIZ #13/#22).
- The decomposition is mid-flight and **mechanical from here** — adding a family is a `FAMILIES` entry + LOCK + EXTRACT.

## 1 · What shipped this session (all merged to `main`, host+CI-proven; da4258e device-smoked)
| Lane | Commits / PR | Proof |
|---|---|---|
| `response_gain` (global-write) | `d288434` lock + `aa0bb28` extract — **PR #5** | replay golden reproduces; Gate Fα +2; pio green; 562 |
| **Structural-contract gate** (keystone) + `queue` family | `f180eb1` lock + `ea6f3b5` extract — **PR #6** | `oracle_serial_struct.py` registered; struct golden reproduces; Gate Fα +3→4 |
| `smart_director` + `smart_visual` + `edge_mixer` | `93ca888` lock + `0ff8936` extract — **PR #7** | struct golden 13 records reproduce; Gate Fα 12 struct; 8 bodies statement-identical |
| **Device smoke** of `da4258e` | registry `614706c` | 67s soak 0 crashes + 74 `[AP]`; all 8 relocated handlers parse/ack/mutate on silicon |

**Harness state:** `ORACLE_MODULES` = `onset_beat, chord, smart_director, render, gdft, serial_replay, serial_struct`. `serial_replay.golden.jsonl` = 103 records; `serial_struct.golden.jsonl` = 13 records (queue 5 + smart_director 4 + smart_visual 1 + edge_mixer 3). pytest = **562 passed / 1 skipped**.

## 2 · RECIPE A — replay-lock a GLOBAL-WRITE family (ref: vivid / response_gain)
**LOCK (test-infra only, handlers stay inline):** extend `oracle_serial_replay.py` — add the family's globals to `snapshot()` (FieldSnap arrays sized 64), add CORPUS entries incl. **clamp-boundary** cases, add ≥2 Gate-Fα mutations (a **write-misroute** + a **clamp-shift**). Regen golden under the ORIGINAL handlers (`python3 oracle_serial_replay.py > tests/golden/serial_replay.golden.jsonl`), recompute its `MANIFEST.sha256` line. Prove non-blind (boundary corpus records the CLAMPED value).
**EXTRACT:** verbatim-lift into `serial_cmd_dispatch_<family>()`; golden REPRODUCES byte-for-byte. **⚠ ORACLE-LINK:** if the dispatcher calls an `sb_*` subsystem fn used ONLY by the handlers TU (no longer odr-used in serial_menu.h) AND that subsystem's `.cpp` is **not** in the replay-oracle `MODULE_CPPS`, add a **guaranteed external** stub in the DRIVER (`oracle_serial_replay.py`), NOT `static inline`/`inline` in `serial_replay_host_stubs.h` (static = TU-internal; inline = emitted only where odr-used → arm64 -O0 link error). `serial_cmd_handlers.cpp` must `#include` the subsystem's real header.

## 3 · RECIPE B — structural-contract gate for a FUNCTION-CALL family (THE keystone; ref: queue / smart_*/edge_*)
The replay oracle is BLIND to these (they call host-stubbed `sb_queue_*`/`sb_smart_*`/`sb_edgemixer_*`). TRIZ #13/#22: for a **verbatim** lift, *statement-identity + dispatch-routing-preservation is behaviour-preserving BY CONSTRUCTION* (the stub sees a byte-identical call at a byte-identical control-flow position). So pin STRUCTURE, not behaviour.
1. **LOCK** — add a `FAMILIES` entry to `oracle_serial_struct.py` (`{name, dispatcher: "serial_cmd_dispatch_<name>", commands: [...]}`). Add ≥1 **body** mutation + ≥1 **command_type-rename** mutation per family to `MUTATIONS` (routing-sever mutations come in EXTRACT — no call-site exists yet). Regen golden (`python3 oracle_serial_struct.py > tests/golden/serial_struct.golden.jsonl`) under the ORIGINAL inline handlers (handlers captured inline, `reachable:true`); recompute `MANIFEST.sha256`. Prove Gate Fα catches them.
2. **EXTRACT** — verbatim-lift into `serial_cmd_dispatch_<name>()` (`if(false){}` opener, `else if` chain, `else { return false; }`, `return true;`); ungated `else if (serial_cmd_dispatch_<name>(command_type, command_data)) {}` call-site. Add a **routing-sever** mutation per dispatcher (`serial_cmd_dispatch_<name>(command_type, command_data)` → `..._SEVERED(...)` — bare-arg form matches ONLY the call-site). The struct golden REPRODUCES byte-for-byte (capture is location-agnostic: finds the body inline OR in the dispatcher, normalizes identically; `reachable` stays true via the call-site). **Golden NOT touched in EXTRACT = anti-gaming.**
- **`serial_cmd_handlers.cpp` includes/forward-decls:** for the subsystem types/config-fns, `#include` the real header (e.g. `sb_smart_director.h`). If the subsystem's `.cpp` is ALREADY in the replay-oracle `MODULE_CPPS` (director/* are), the link is free — **no host-stub surgery** (unlike `sb_queue_*`, whose `.cpp` is excluded). serial_menu.h-local helpers used by the bodies (e.g. `sb_print_smart_status`/`sb_apply_smart_scene`/`sb_parse_edge_mode`) are external-linkage → forward-declare them (vivid pattern).
- **The `oracle_serial_struct.py` body-extractor** is brace-balanced + comment/string-aware; normalization collapses whitespace (tolerates re-indent) but preserves every token/literal. `capture()` is pure-parse (no compile) — so a compile/link break is caught by the REPLAY oracle's `test_golden_master` compile + `pio`, NOT by the struct golden.

## 4 · ORCHESTRATOR RE-VERIFY (every increment, do NOT trust an agent's "VERIFIED")
Re-run yourself: struct/replay golden reproduces (`pytest tests/test_golden_master.py`), Gate Fα (`python3 scripts/regression-harness/golden/harness_selftest.py` → `GATE_F-alpha: PROVEN`), statement-identity (`diff -w -B` extracted body vs `git show <LOCK-commit>:…serial_menu.h`), gate-consistency grep (decl+def+call-site same `#ifdef`), full `pytest tests/` (562), `pio run -e k1_hardware`, `git status` (only expected files; **zero golden in the EXTRACT commit**). **Static-test fallout is EXPECTED** — extractions break static tests that grep serial_menu.h for the moved handlers (amend-broken-gates): re-point the test's mechanism to `serial_cmd_handlers.cpp` (or the menu+handlers "dispatch surface") while PRESERVING its invariant; never weaken a tooth. (This session: `test_audio_response_gain_static`, `test_effect_queue_static`, `test_smart_visual_engine_static` were re-pointed.)

## 5 · NEXT WORK (mechanical; facade-free families, re-verify each first)
1. **`preset`** (serial_menu.h ~3294) — calls `set_preset()` (`presets.h`, NOT facade) + `save_config_delayed()`. Has a replay-observable side-effect (save flag) so it could ALSO be replay-locked; the structural gate works regardless. ~1 family.
2. **`secondary_*`** target controls — a cluster of secondary-channel setters/controls. Map them (grep `command_type, "secondary_`), classify global-write (replay) vs function-call (structural), extract.
3. **GATED families (gate-match decl/def/call-site):** `set_mode` (`#ifdef K1_EFFECT_REGISTRY_V1`, ASYNC — the real CONFIG write is deferred to `led_utilities.h`; model it or use the structural gate) + `beat_director` (`#ifdef K1_EFFECT_FRAMEWORK_V1`). **The gate-straddle scar:** a single-flag handler must NEVER land under a different/combined gate (it once broke `k1_tempo_probe`).
4. Then the gated-out probe families (filler) + the `.ino → main.cpp` keystone (the actual de-Arduino goal — behaviour-CHANGING, high-blast-radius → device A/B + Captain eyes-on; NOT pure-autonomous).

## 6 · ⛔ SCOPE LOCK (Captain, 2026-06-25 — load-bearing)
**`vp_profile`/`vp_all` + the control-facade (`control/sb_k1_control_facade.cpp`) profile logic are a SEPARATE architectural lane. Do NOT touch them in the function-call tranche. HARD STOP if a gate requires changing or interpreting the duplicated profile/facade logic.** Why: there is a duplicated, byte-identical `vp_apply_profile` (+ `parse_vp_profile`, `vp_profile_name`) across `serial_menu.h` and the committed facade (the facade is live — included by the wireless/Tab5 path). The firmware links the serial_menu.h:465 copy (proven via `.ino.cpp.o` nm); the facade is an in-flight/abandoned migration. This is the Captain's lane, not the decomposition's.

## 7 · LOAD-BEARING DISCIPLINE
- **The harness IS the product.** No structural refactor merges without: `pio -e k1_hardware` green AND all registered goldens reproduce AND Gate Fα PROVEN AND CI green.
- **Anti-gaming two-commit split:** LOCK (oracle + golden + MANIFEST) then EXTRACT (source; **zero golden**). Git-prove the EXTRACT touched no golden.
- **SSA — re-run every subagent claim.** This session an Explore agent self-contradicted on `preset`; a prior session had agents read the WRONG repo + introduce a gate-straddle. **Every delegation brief starts with a cwd-guard** (`git -C /Users/spectrasynq/SpectraSynq_K1_Firmware rev-parse --show-toplevel`; abort if not the fork) + absolute paths. Decision-critical calls (facade-cleanliness, blind-lock) → the orchestrator personally re-runs the decisive artifact.
- **Branch flow:** per-increment branch → PR → poll `MERGEABLE` (async) → `gh pr merge --merge --delete-branch` → re-cut fresh `feat/serial-decomposition` off updated main. Handoff/registry docs commit directly to main (docs-only, no gate). main always current + green. No pre-commit hook installed → your manual gate runs + CI are the gate.
- **`compile ≠ runtime proof`** only where it matters: command-parse relocations are closed by the host gate; the Captain may request a narrow **device smoke** (see §8). The render/perceptual path is untouched by these relocations.

## 8 · DEVICE / FLASH REALITY (verify identity by CHIP-ID before ANY write)
- **Main K1 = chip `F887A500` = USB serial `B4:3A:45:A5:87:F8` = env `k1_hardware`.** Currently on **`/dev/cu.usbmodem2101`** (drifts; chip-ID is truth). **Bench K1v2 = `B489A500` = `k1_bench_reference`** — DIFFERENT GPIO map, NEVER cross-flash. Read `docs/hardware/device-build-registry.md` before any flash; update its deployed-state table after.
- **Verify identity yourself first:** `ioreg -p IOUSB -l | grep "USB Serial Number"` → confirm `B4:3A:45:A5:87:F8` present (and `B489A500` absent). The `k1_upload_guard.py` pre-script re-verifies + aborts on mismatch (last line of defence).
- **⚠ FLASH GOTCHA (load-bearing, found 2026-06-25):** `pio … -t upload` **piped/redirected silently no-ops** (esptool needs a TTY; `pio_exit=0` but NOTHING writes). **WRAP IN `script`:** `script -q <log> pio run -e k1_hardware -t upload --upload-port /dev/cu.usbmodem2101` — then grep the log for `Hash of data verified.` + `Hard resetting` to CONFIRM the write. A "smoke pass" on an unflashed device (old build) is a false pass.
- **Serial protocol:** typed commands MUST be `:`-prefixed (`check_serial` enters command-mode on `:`; bare bytes hit the HOTKEY path). `[AP]` telemetry streams ~1.1 Hz by default (render-alive signal). Device I/O via the Bash tool needs `dangerouslyDisableSandbox: true`. A reusable pyserial smoke harness lives at the session scratchpad (`k1_smoke_da4258e.py`) — pattern: boot-soak + crash-scan + `:`-command dispatch + render-alive + restore. **Never auto-fire `noise_cal`.**
- These handler writes are RAM-only (no `save_config`) → reset on power-cycle/reflash; restore toggles to a neutral state after a smoke.

## 9 · KEY FILES & GATE COMMANDS
- Oracles: `scripts/regression-harness/golden/oracle_serial_struct.py` (FAMILIES, MUTATIONS, `_extract_block`/`_normalize`/`_routed`) · `oracle_serial_replay.py` (snapshot/CORPUS/MUTATIONS + DRIVER stubs) · `serial_replay_host_stubs.h`.
- Gate Fα: `harness_selftest.py` (`ORACLE_MODULES`). Goldens + `MANIFEST.sha256` in `tests/golden/`.
- Source: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h` (`parse_command` ladder) · `serial/serial_cmd_handlers.{cpp,h}` (dispatchers) · `system/globals.h` (inline globals).
- Gates: `python3 scripts/regression-harness/golden/harness_selftest.py` · `python3 -m pytest tests/ -q` (562) · `python3 -m pytest tests/test_golden_master.py -q` · `pio run -e k1_hardware`.
- Read-order on session start: `progress.md` → `.claude/handoff.md` → THIS doc → `docs/architecture/firmware-modernization-program.md` → `docs/hardware/device-build-registry.md`.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-25 | agent:claude-code (CTO) | Created (supersedes handover-2026-06-25-serial-decomposition.md): structural-contract gate built + Gate-Fα-proven + exercised by queue (PR#6) and smart_director/smart_visual/edge_mixer (PR#7); response_gain (PR#5); da4258e device-smoked. Both recipes (replay-lock + structural gate), next families, scope-lock, discipline, device/flash reality incl. the script-pty flash gotcha. |
