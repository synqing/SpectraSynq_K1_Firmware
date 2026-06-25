---
abstract: "Lane contract for the GATED / side-effect-bearing serial families (set_mode + secondary_mode + beat_director) — the last serial_menu.h tranche before .ino→main.cpp. Captain-ratified higher bar (2026-06-26). KEY DECISION: these are STRUCTURAL-GATE families (oracle_serial_struct.py, proven on queue/smart/edge/preset), NOT replay-lock — a verbatim lift is behaviour-preserving by construction, so the async/deferred CONFIG.LIGHTSHOW_MODE write is sidestepped, NOT modelled (modelling it in replay would be a blind-lock trap). Encodes per-handler classification, gating shapes (set_mode/secondary_mode = internal #ifdef → ungated dispatcher; beat_director = fully #ifdef K1_EFFECT_FRAMEWORK_V1, production-OFF → gate-matched dispatcher), the recommended split, the structural mutation teeth that satisfy the Captain's required regressions, the draft-PR merge-safety rule, and stop conditions. FRESH CONTEXT ONLY; re-verify every classification first-hand (SSA)."
---

# Lane — Gated / side-effect-bearing serial families (set_mode · secondary_mode · beat_director)

> **Predecessors shipped:** preset (PR #8), secondary_* pure setters + the mutation-anchor guard (PR #9). **main = `3317fa1`.** This is the **last serial_menu.h tranche** before the `.ino`→`main.cpp` keystone. Read `.claude/handoff.md` and `docs/architecture/firmware-modernization-program.md` first. **FRESH CONTEXT ONLY** (Captain) — do not start this in a context already loaded with another family.

## 0 · Posture (Captain-ratified, 2026-06-26)
- These handlers cross into **mode routing + persistence side-effects** (deferred CONFIG write, `save_config_delayed`, effect-registry calls). **Higher bar than pure setters.** Treat as a NEW family, not "secondary_* part 2."
- **Merge safety — DRAFT PR.** There is **no auto-merge automation** in this repo (only `.github/workflows/ci.yml`; PR auto-merge is not configured — verified 2026-06-26: PR #9's `autoMergeRequest` was `null`, merged by the `synqing` account = the Captain, manually). The risk is therefore a **premature manual merge before review**, not a runaway bot. **HARD RULE for this lane:** open the PR as a **DRAFT** and mark it "Ready for review" ONLY after every local gate passes AND the branch is final. GitHub blocks merging a draft, so it cannot land before review regardless of who clicks. Title-prefix the PR `[DRAFT — side-effect-bearing, do not merge until reviewed]`.
- **No device flash. No facade/vp_profile. No CHROMA / LayerSense / AP-evidence-lab / native render code. No broad serial_menu rewrite.**

## 1 · THE KEY DECISION — STRUCTURAL gate, NOT a new async-modelling replay oracle
The Captain's instruction said "the replay oracle must cover async CONFIG write / deferred-save semantics." **The right tool is the opposite: do NOT replay-lock these, and do NOT model the async write.** Reasoning (TRIZ #13 the-other-way-round + #22 blessing-in-disguise):

- `set_mode` / `secondary_mode` queue `mode_transition_queued` / `mode_destination` **synchronously**, but the **real `CONFIG.LIGHTSHOW_MODE` write is DEFERRED** to `led_utilities.h`'s transition FSM. `oracle_serial_replay.py` already **EXCLUDES `set_mode` for exactly this reason** — a synchronous capture would freeze the WRONG behaviour (`CONFIG.LIGHTSHOW_MODE` unchanged at capture time). Building a replay model of the deferred write = a **new blind-lock surface** = the precise trap the discipline forbids ("never register a blind/replica/stub oracle").
- A **verbatim lift** is behaviour-preserving **BY CONSTRUCTION**: statement-identity + dispatch-routing-preservation. The **structural-contract gate** (`oracle_serial_struct.py`, PROVEN on queue/smart_director/smart_visual/edge_mixer/preset) pins exactly that, **without observing behaviour**. The deferred write lives in `led_utilities.h`, which this lane **does not touch**, so it fires identically before and after the lift. The async semantics are **irrelevant** to the proof.

**Conclusion:** register each handler as a `serial_struct` FAMILY and lift verbatim. The existing gate stack already gives triple coverage: **structural** (statement-identity + routing, pure parse) · **compile/link** (the replay oracle host-compiles `serial_cmd_handlers.cpp` in `MODULE_CPPS`, and `pio -e k1_hardware`) · **mutation teeth** (Gate Fα). No new oracle. This is the "stronger gate" the Captain wants — delivered by the proven structural mechanism + the mandatory classification, not by fragile async modelling.

### Captain's required teeth → structural mechanism (all satisfiable, no async model)
| Captain's required regression | Structural tooth that catches it |
|---|---|
| mode-routing sever caught | `command_type`-rename mutation (`strcmp(command_type,"set_mode")`→`..._MUT`) → body null + unreachable |
| async-write / deferred-save sever caught | **body mutation** dropping/altering `save_config_delayed();` or `mode_destination = …;` → statement-identity divergence |
| secondary_mode path sever caught | per-family `command_type`-rename + call-site-sever teeth (as for queue/smart/edge) |
| beat_director command sever caught (if included) | `command_type`-rename on `"beat_director"` + call-site-sever |
| tempo_stream straddle covered / OOS | beat_director's gate-match is the straddle control (§3); declare tempo_stream OUT OF SCOPE explicitly |

## 2 · Per-handler first-pass classification (RE-VERIFY FIRST-HAND — SSA)
> First-pass only (2026-06-26 read). The fresh session **must** re-classify each handler first-hand before LOCK; do not trust these line numbers or claims blind.

| handler | serial_menu.h | class | side-effects | gating |
|---|---|---|---|---|
| `set_mode` | ~2948 | function-call + global-write (mixed) | `mode_transition_queued`/`mode_destination` (sync); **`save_config_delayed()`**; **deferred** `CONFIG.LIGHTSHOW_MODE` (led_utilities.h FSM); `k1::effects::framework::registry_*`, `light_mode_next_enabled`, `serial_print_mode_line` | **internal** `#ifdef K1_EFFECT_REGISTRY_V1` (handler always present) |
| `secondary_mode` | ~3329 (now inline; deferred from PR #9) | function-call + global-write (mixed) | `SECONDARY_LIGHTSHOW_MODE`, `ENABLE_SECONDARY_LEDS` (sync); registry_*, `light_mode_next_enabled`, `serial_print_mode_line` | **internal** `#ifdef K1_EFFECT_REGISTRY_V1` |
| `beat_director` | ~3093 | function-call | `bad_director_set_enabled(value)` (subsystem toggle); `serial_print_beat_director_status()`; `vp_parse_bool` | **WHOLE else-if WRAPPED** in `#ifdef K1_EFFECT_FRAMEWORK_V1` |

`K1_EFFECT_FRAMEWORK_V1` is **NOT defined in shipping `k1_hardware`** (platformio.ini:608) — it lives in a separate framework env; `K1_EFFECT_REGISTRY_V1` requires it (platformio.ini:640). So in the production build: `set_mode`/`secondary_mode` compile the `#else` (`light_mode_next_enabled`) branch and **are present**; `beat_director` is **compiled OUT** (production-byte-identical, like the probe families).

## 3 · Gating shape & the straddle hazard — and the recommended SPLIT
- **`set_mode` + `secondary_mode`**: the `#ifdef K1_EFFECT_REGISTRY_V1` is **internal** to the body → the handler is always present → **UNGATED dispatcher**; the internal `#ifdef` rides verbatim with the lifted body (exactly the secondary_mode/secondary_* pattern). serial_menu.h-local helpers they call (`serial_print_mode_line`, `serial_mode_name`) are external-linkage → forward-declare in handlers.cpp (proven pattern). registry fns come from the effects-framework header; if its `.cpp` is NOT in the replay-oracle `MODULE_CPPS`, apply the ORACLE-LINK rule (guaranteed-external driver stub, never `static inline`).
- **`beat_director`**: the **entire** `else if` is behind `#ifdef K1_EFFECT_FRAMEWORK_V1` and is production-OFF. Its dispatcher **decl + def + call-site must ALL be `#ifdef K1_EFFECT_FRAMEWORK_V1`** (gate-matched). A single-flag handler under a different/combined gate is the **tempo_stream straddle scar** (it once broke `k1_tempo_probe`). `bad_director_set_enabled`/`serial_print_beat_director_status` are themselves framework-gated → they only exist where the flag is defined, so the gated dispatcher links only in the framework env.
- **RECOMMENDED SPLIT (Captain: "split it smaller"):**
  1. **Increment A** — `set_mode` + `secondary_mode` (shared internal-`#ifdef K1_EFFECT_REGISTRY_V1` + registry surface; ungated dispatcher). Same recipe, two commands, one family.
  2. **Increment B** — `beat_director` (fully-gated `#ifdef K1_EFFECT_FRAMEWORK_V1`, production-OFF, gate-matched dispatcher). Treat like a probe family: each affected env (the framework/registry envs) must build byte-identical, plus `k1_hardware` byte-identical (it compiles the handler out either way).
  Do **not** mix A and B in one increment — different gates, different production-presence.

## 4 · Process (per increment, unchanged discipline)
- **LOCK commit**: add the family to `oracle_serial_struct.py` `FAMILIES`; regen `serial_struct.golden.jsonl` under the ORIGINAL inline handlers (clean append); add ≥1 **body** mutation (incl. a `save_config_delayed`/`mode_destination` drop = the deferred-save tooth) + ≥1 `command_type`-rename mutation. **oracle + golden + MANIFEST only; ZERO source.** Gate Fα PROVEN.
- **EXTRACT commit**: verbatim lift into `serial_cmd_dispatch_<family>()` (`if(false){}` opener; `else if` chain; `else { return false; }`; `return true;`); ungated call-site for A, **gate-matched** call-site for B; add the routing call-site-sever tooth. **Source + tooth only; golden UNTOUCHED.** (For the structural oracle the sever tooth is the pure-parse `_SEVERED` rename — fine; it does NOT compile in the harness. Do NOT confuse with the replay oracle, where a sever must be compile-safe `false &&`.)
- **Re-verify yourself** (do NOT trust an agent's claim): struct golden reproduces byte-for-byte; statement-identity `diff -w -B` empty; Gate Fα PROVEN; **`test_mutation_anchor_uniqueness_static.py` GREEN** (the PR #9 guard — every anchor count==1, dispatcher comments use the `"<name>"` placeholder); full `pytest tests/`; `pio run -e k1_hardware` (and the framework/registry envs for B); `git status` (zero golden in EXTRACT). Static-test fallout (greps of serial_menu.h for the moved handler) → re-point to handlers.cpp, preserve the invariant (amend-broken-gates).

## 5 · Stop conditions (Captain + lane)
- golden changes during EXTRACT · mutation tooth weakened/missed · a handler crosses a save/reboot/subsystem boundary **not in its classification** · a single-flag handler would land under a different/combined gate (straddle) · tempo_stream ambiguity unresolved · branch/HEAD truth ambiguous · the lift is not byte-for-byte verbatim (statement-identity fails) → STOP at the exact surface, diagnose only that.

## 6 · Do-NOT-touch (Captain scope lock)
facade · vp_profile/vp_all · CHROMA · LayerSense · AP-evidence-lab · effect native render code · device flashing · `secondary_status` (read-only — its own gate if ever extracted) · the `secondary_status` carve-out (serial_menu.h:1457) & `strncmp(command_type,"secondary_",10)` prefix-router (1460) in `serial_command_marks_manual_visual_control` (manual-owner audit — NOT handlers).

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-26 | agent:claude-code (CTO) | Created after PR #9 (secondary_* shipped). Captain ratified a higher bar for the gated/side-effect family + flagged merge safety. KEY refinement: structural gate (not async-modelling replay) — TRIZ #13/#22, the async write is sidestepped by a verbatim lift; the replay-async path would be a blind-lock trap. First-pass classification + gating shapes (set_mode/secondary_mode internal #ifdef → ungated; beat_director fully #ifdef K1_EFFECT_FRAMEWORK_V1 production-OFF → gate-matched); recommended A/B split; structural teeth mapping the Captain's required regressions; draft-PR merge-safety rule (no repo auto-merge automation — PR #9 was a manual merge). |
