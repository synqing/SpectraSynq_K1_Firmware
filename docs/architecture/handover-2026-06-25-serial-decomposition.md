---
abstract: "Detailed agent handover (2026-06-25) for the SpectraSynq K1 de-Arduino modernization, serial_menu.h strangler-fig decomposition lane. Current state: main=1d5b111, GDFT + serial S0–S4.1 + AP-diag + VP-tuning + vivid all merged & (live ones) device-validated. Encodes the PROVEN lock-then-extract recipe, the global-write vs function-call BIFURCATION, the next phases (response_gain → vp_profile → the function-call BULK via a structural-contract gate), and every load-bearing gate/discipline/device fact. Read this + .claude/handoff.md before touching anything."
---

# Handover — K1 serial_menu.h decomposition (2026-06-25)

> **You are the SpectraSynq CTO-agent continuing a de-Arduino modernization.** Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware`. The goal is a decomposed, extensible firmware **without regressing the musical light-show** (perceptual product = sacred; behaviour-preservation = the floor). Method = **strangler-fig: extract god-header handlers into clean TUs behind golden/replay behavior-locks, proven safe at every step.** The verification HARNESS IS THE PRODUCT.

## 0 · TL;DR — where we are
- **`main` = `1d5b111`** (CI-green). Active branch **`feat/serial-decomposition`** (fresh off main, even 0/0).
- Shipped to `main`, all host+CI+golden-proven and the **production-LIVE extractions device-runtime-proven on the main K1 (`F887A500`)**:
  - **GDFT** god-header → `k1_gdft_core.cpp` + golden-locked spectrum oracle.
  - **serial_menu.h decomposition** (6191 → **4450 lines**): 30 CONFIG setters (23 pure + 7 reboot), 11 gated AP-diag commands, **17 VP-tuning handlers**, **4 vivid handlers**.
- The decomposition is mid-flight. **The next agent continues it with the PROVEN recipe (§2), respecting the bifurcation (§3) and the discipline (§4).**

## 1 · What is on `main` (the program so far)
| Lane | What | Verification | PR |
|---|---|---|---|
| GDFT | `GDFT.h` god-header → `audio/k1_gdft_core.cpp` (statement-identical); int64 overflow fix flags **default-OFF** | golden `oracle_gdft.py` + Gate Fα; device soak | PR #1 |
| serial S0–S4.1 | 30 CONFIG setters → `serial_cmd_dispatch_pure_setter()` (23) + `serial_cmd_dispatch_reboot_setter()` (7) in `serial/serial_cmd_handlers.cpp` | `oracle_serial_replay.py` (capture-triple: echo text + CONFIG delta + side-effect flags) | PR #1/#2 |
| AP-diag | 11 gated diagnostics cmds (`ap_frontend_debug`/`nov_*`/`apcad_*`) → `serial_diag_ap_dispatch()` in `serial/k1_ap_capture_telemetry.cpp` | **production byte-identical** (gated-out under `ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG`) | PR #2 |
| **VP-tuning** | 17 `VP_FIX`/`VP_BLOOM`/`VP_WAVEFORM` handlers → `serial_cmd_dispatch_vp_tuning()` | EXTENDED replay lock (17 VP globals + 2 Fα mut.); golden reproduces; **device functional PASS** | PR #3 |
| **vivid** | 4 handlers → `serial_cmd_dispatch_vivid()` (single `#ifdef SB_VIVID_PRECOMP_V1` gate) | EXTENDED replay lock (3 `VP_VIVID_*` + 2 Fα mut.); golden reproduces; **device functional PASS** | PR #4 |

**Harness (the product):** golden-master oracles registered in `harness_selftest.py::ORACLE_MODULES` = `onset_beat, chord, smart_director, render, gdft, serial_replay` (each deterministic, golden frozen, mutation-proven). `tempo` deferred (cross-platform field); `semantic_state` removed (was a stub). pytest = **562 passed / 1 skipped / 67 subtests**.

## 2 · THE PROVEN RECIPE — lock-then-extract a GLOBAL-WRITE live family
This is the loop that shipped VP-tuning and vivid. Mirror it exactly. Reference impls: `serial_cmd_dispatch_vp_tuning` / `serial_cmd_dispatch_vivid` + the matching commits `1b2a45c`+`05fb9d2` (VP) / `ac325b3`+`6794cf7` (vivid).

**PHASE A — extend the lock (handlers STAY inline; test-infra only):**
1. In `oracle_serial_replay.py`'s host-driver C++ string, `snapshot(FieldSnap* out)` (ends `return n;` ~L433): append `out[n++] = {"GLOBAL_NAME",(double)GLOBAL_NAME};` for each global the family writes. FieldSnap array is sized ≥64 — confirm it holds the new count.
2. Add CORPUS entries (Python `CORPUS` list ~L177): one representative per handler **+ clamp-boundary cases** (the boundary entries are what make the lock catch clamp regressions).
3. Add ≥2 Gate-Fα MUTATIONS (follow the existing structure): a **write-misroute** (point the handler at the wrong global → field-routing divergence) and a **clamp-shift** (change a clamp bound → CONFIG-delta divergence on a boundary corpus entry).
4. Regenerate the golden via the project regen path (do **NOT** hand-edit the golden), then `python3 scripts/regression-harness/golden/harness_selftest.py` → Gate Fα must report the new mutations CAUGHT. Confirm the golden's new entries have **non-empty config_delta** and that a clamped input recorded the **clamped** value (= ORIGINAL behaviour). **STOP if A fails — a blind/empty lock is worse than none.**

**PHASE B — extract (only after A green):**
5. Lift the handler bodies **VERBATIM** out of `serial_menu.h`'s `parse_command()` ladder into `bool serial_cmd_dispatch_<family>(const char* command_type, char* command_data)` in `serial_cmd_handlers.cpp` (`if(false){}` opener, `else if` chain, `return true` iff handled else `false`). Forward-declare any helpers it calls (pattern: `vp_set_flag_command` / `serial_set_vivid_level` already done). Declare the fn in `serial_cmd_handlers.h`.
6. Replace the inline branches in `parse_command` with ONE `else if (serial_cmd_dispatch_<family>(...)) { }` at the SAME ladder position. **GATE-MATCH: if the family was under `#ifdef X`, then decl + def + call-site ALL get `#ifdef X` (single gate). A handler under flag X must NOT become reachable under a different gate** — that straddle broke `k1_tempo_probe` once (see §4).
7. The golden must now **REPRODUCE byte-for-byte** (you did NOT regen in B). If it doesn't → the extraction changed behaviour → fix the EXTRACTION, never the golden.

**COMMITS = two, anti-gaming:** commit FILES_A (oracle + golden + MANIFEST) as the **lock** commit; commit FILES_B (serial_menu.h + serial_cmd_handlers.{cpp,h} + any re-pointed static test) as the **extract** commit. The extract commit must touch **zero golden** (git-prove it) — that proves the golden was frozen under the original handlers and the extraction reproduced it untouched.

**ORCHESTRATOR RE-VERIFY (do NOT trust the agent's "VERIFIED"):** re-run yourself — Gate Fα (the new mutations caught), golden gate (`pytest tests/test_golden_master.py`), full `pytest tests/`, `pio run -e k1_hardware`, statement-identity diff (extracted body vs `git show HEAD:...serial_menu.h`), gate-consistency grep (all 3 surfaces same `#ifdef`), and `git status` (only the expected files).

**DEVICE-VALIDATE** (§5), then **MERGE PR → TIDY** (§6).

## 3 · THE BIFURCATION (strategic — drives sequencing)
The remaining `parse_command` ladder (~66 live handlers) splits:
- **GLOBAL-WRITE handlers** — write an `inline` global in `globals.h` directly (or via a host-compilable helper that does). **Replay-lockable** via §2's extend-snapshot. **Remaining: `response_gain` (trivial, ungated), `vp_profile`/`vp_all` (multi-field via `vp_apply_profile` — CONFIRM no `save_config` in the VP_FIX path before treating as pure).**
- **FUNCTION-CALL handlers (~30, THE BULK)** — call a host-stubbed subsystem (`sb_queue_*`, `set_preset`, `sb_smart_director_*`, `sb_edgemixer_*`, `apply_chroma_profile`, `beat_aware_director`) that drags FS/LittleFS and can't host-compile → the replay is **BLIND** for them. Families: `queue_mode`/`transition_*`/`commit_quantise`, `smart_*`, `edge_*`, `preset`, `secondary_*`, `set_mode` (async), `set_chroma_profile`+`bass_mode` (conditional reboot).

**Unblocking the bulk (TRIZ-resolved, the keystone of the next phase):** a **STRUCTURAL-CONTRACT gate**, NOT a replay extension. For a **verbatim** lift, *statement-identity + dispatch-routing-preservation is behaviour-preserving BY CONSTRUCTION* (the stubbed subsystem sees an identical call, so its behaviour is irrelevant to the proof — TRIZ #13 The-Other-Way-Round + #22 Blessing-in-Disguise). So build a host test that asserts (a) each command routes to the dispatcher, (b) the lifted body is byte-identical to the original (diff-gate), and prove it fault-EVIDENT with a mutation battery (Gate-Fα-equivalent: a mis-routed/altered body must fail it). `#1 Segmentation` (stub only FS/LittleFS, compile the subsystem logic real) is held in reserve where full behavioural replay is wanted. **This single gate unblocks all ~30 function-call handlers.**

## 4 · LOAD-BEARING DISCIPLINE (non-negotiable)
- **The harness IS the product.** No structural refactor merges without: `pio run -e k1_hardware` green **AND** all registered goldens reproduce **AND** Gate Fα proven **AND** CI green.
- **Behaviour-preserving by construction.** Statement-identical lift; the golden reproducing IS the proof. A number changing = behaviour changed = human-approved ticket only.
- **Never register a blind/replica/stub oracle.** False confidence is worse than none.
- **SSA — re-run every subagent claim yourself.** This session, **3 of 4 implementation/scoping agents returned "VERIFIED" while WRONG on first contact**: one read the **wrong repo** (the decoy at `/Users/spectrasynq/SensoryBridge-main 9`), one introduced a **gate-straddle regression** (tempo_stream folded under a combined gate → broke `k1_tempo_probe`/`k1_bench_tempo_probe`). Both caught by orchestrator re-run. **Every delegation brief MUST start with a cwd-guard** (`git -C <abs> rev-parse --show-toplevel`; abort if not the fork) + absolute paths. Decision-critical claims → the orchestrator personally re-runs the decisive artifact.
- **Anti-gaming two-commit split** (lock then extract; golden NOT in the extract commit).
- **Gate-match** (the tempo_stream lesson, §2 step 6).
- **Branch flow:** per-increment branch → PR → merge (`--merge`, consistent w/ history) → `--delete-branch` → re-cut fresh `feat/serial-decomposition` off updated `main`. `main` always current + green. GitHub mergeability is async — poll until `MERGEABLE` before `gh pr merge`.
- **`compile ≠ runtime proof`**: production-LIVE extractions get a device flash + functional check (§5). Production byte-identical (gated-out) extractions are closed by the host gate alone.

## 5 · DEVICE / PORT REALITY (verify identity by CHIP-ID before ANY write)
- **Main K1 = chip `F887A500` = USB serial `B4:3A:45:A5:87:F8` = env `k1_hardware`.** Currently on **`/dev/cu.usbmodem2101`** (drifted from `1101` this session — **ports re-enumerate; chip-ID is truth**). Captain has authorized unrestricted bench use.
- **Bench K1v2 = chip `B489A500` = env `k1_bench_reference`** (DIFFERENT GPIO map — NEVER cross-flash; bricks output). Canonical pairing + deployed-state: `docs/hardware/device-build-registry.md` (read before any flash; update its table after every flash).
- **Flash:** `pio run -e k1_hardware --target upload --upload-port /dev/cu.usbmodem<PORT>` — the `k1_upload_guard.py` pre-script re-verifies chip-ID/MAC and aborts on mismatch (last line of defence, not first; `platformio.ini` port pins are STALE → always pass `--upload-port`). Verify identity yourself first (`ioreg -p IOUSB -l | grep "USB Serial Number"`).
- **Serial command protocol:** typed commands MUST be **`:`-prefixed** to reach `parse_command` (`check_serial`:~3988 enters command-mode on `:`; bare bytes route to the single-byte HOTKEY path — `v`/`m`/`f` etc. fire as hotkeys and shred an un-prefixed command). Device functional test pattern: open `cu.usbmodem<PORT>` @115200, soak ~60–75 s (scan crash markers + `[AP]` cadence), send `:<cmd>=<val>\n`, assert the echoed status. **Never auto-fire `noise_cal`** (needs verbal silence confirmation).
- **This S3 does NOT DTR-reset on port-open** → non-persistent global writes (vivid/VP tuning) persist across port open/close (reset only on power-cycle/reflash); restore defaults explicitly via the echo-confirmed command if you change them.
- **Heads-up:** Cursor IDE may hold a stale serial-monitor handle on an OLD port node (e.g. `tty.usbmodem1101`) → "Resource busy" on flash. `lsof /dev/tty.usbmodem<port>` to find it; it's the Captain's editor — surface it, don't kill it.

## 6 · NEXT PHASE (prioritised)
1. **`response_gain`** — ungated single global-write (`audio_response_gain` via `serial_clamp_float`), the cleanest next §2 recipe application. ~1 increment.
2. **`vp_profile`/`vp_all`** — global-write but multi-field via `vp_apply_profile()`; **first confirm it doesn't call `save_config` in the VP_FIX path**, then §2.
3. **THE BULK — build the structural-contract gate (§3)** and extract the ~30 function-call families under it. This is the highest-leverage move; it converts the rest of the decomposition from blocked to mechanical.
4. **Gated-out probe families** (`ap_capture`/`frame_dump`/`vp_probe`/`gdft_*`/`mp_*`) — production byte-identical (Unit-A pattern), low strategic value → do as filler; each its own gate family (gate-match).
5. **Then the spine + the `.ino → main.cpp` keystone** (the actual de-Arduino goal — behaviour-CHANGING, high-blast-radius → needs device A/B + Captain eyes-on; NOT pure-autonomous).
6. **Audit backlog (Captain-gated):** I2S Core-0 `portMAX_DELAY` timeout; wireless security (open AP + shared token — a real Kickstarter-ship vulnerability). int64 GDFT flags stay default-OFF (Captain bench eyes-on: "no product value").

## 7 · KEY FILES & GATE COMMANDS
- Oracle: `scripts/regression-harness/golden/oracle_serial_replay.py` (`snapshot()`, `CORPUS`, `MUTATIONS`).
- Gate Fα: `scripts/regression-harness/golden/harness_selftest.py`. Golden: `tests/golden/serial_replay.golden.jsonl` (+ `MANIFEST.sha256`).
- Dispatchers/decls: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.{cpp,h}`. Source ladder: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h`. Globals: `SPECTRASYNQ_K1_FIRMWARE/system/globals.h`.
- Gates: `python3 scripts/regression-harness/golden/harness_selftest.py` · `python3 -m pytest tests/ -q` (562) · `python3 -m pytest tests/test_golden_master.py -q` · `pio run -e k1_hardware`.
- Read-order on session start: `progress.md` → `.claude/handoff.md` → this doc → `docs/architecture/firmware-modernization-program.md` (the ratified blueprint, = the K1 instantiation of the `autonomous-agentic-build` skill) → `docs/hardware/device-build-registry.md`.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-25 | agent:claude-code (CTO) | Created: full handover after vivid family shipped (PR #4, host+device validated). Proven recipe, bifurcation, next phases, discipline, device/port reality. |
