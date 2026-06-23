---
abstract: "Thorough narrative handover for the SpectraSynq K1 firmware modernization (Phase A, de-Arduino). Explains WHY (de-Arduino without regressing the perceptual product), HOW (strangler-fig + golden-master behavior-locks + lock-then-extract + delegate-and-re-verify), and WHAT (current validated state on branch feat/gdft-decomposition). Includes the harness architecture, a Cynefin-classified remaining-work roadmap, the red-team failure list, the device discipline, the recurring cross-TU edges, and the OODA operating model for the next agent. Read .claude/handoff.md FIRST for the live pointer; this brief is the deep context behind it."
---

# SpectraSynq K1 Modernization — Handover Brief

**Date:** 2026-06-24 · **Branch:** `feat/gdft-decomposition` (HEAD `0c35a5f`, 14 commits, PR #1, CI-green) · **Baseline:** `main` (pre-modernization).
**Live pointer (read first, every session):** [`.claude/handoff.md`](../../.claude/handoff.md). This brief is the *why/how* narrative behind that pointer; it changes slowly. `handoff.md` changes per slice.

> **One sentence:** We are de-Arduino-ing the K1 firmware — pulling god-headers out of an Arduino `.ino`/header-soup monolith into clean translation units — *behind golden-master behavior-locks that are themselves proven to catch regressions*, so the perceptual product never regresses, and we have validated the whole approach end-to-end on real hardware with a Captain eyes-on PASS.

---

## 1 · The WHY (this governs every decision — internalize it)

### 1.1 The product is the light-show, not the code
The K1 is an audio-reactive lighting instrument: a microphone → Goertzel spectral analysis (GDFT) → onset/beat/chord/tempo detection → dual-channel edge-lit LGP plate. Its **perceptual quality** — how musically alive and visually captivating the plate is — **is the north star** (`sensorybridge-doctrine`). Architecture is *subordinate* to that. A change that makes the code cleaner but the show worse is a **regression**, full stop.

### 1.2 Why modernize at all
The firmware is inherited Sensory Bridge code (Connor Nishijima / Lixie Labs, GPL-3.0). It **works and looks good**, but it is an Arduino `.ino` + header-soup monolith:
- 6000+-line god-headers (`GDFT.h`, `serial_menu.h`) `#include`d into a single `.ino` translation unit.
- Nothing host-compiles in isolation → no fast host tests, no real CI, no characterization safety net.
- Fragile build (`build_src_filter` allowlists, `.ino`→`.ino.cpp` generation), no module boundaries, no path to ESP-IDF/CMake.

For the SpectraSynq launch trajectory (K1 → FE → Kickstarter → mass adoption), that architecture cannot carry the weight: it is not extensible, not CI/CD-able, not safe to evolve at speed. **Phase A's goal is to de-Arduino it** — clean TUs, host-testability, CI/CD, a path to ESP-IDF — *without regressing the perceptual product*.

### 1.3 The sacred constraint: behavior-preservation
Faithful reproduction of the working firmware's behavior is the **FLOOR**. "Cleaner but different" is failure. Every refactor in this program is **behavior-preserving by construction**, and we *prove* it, we don't assert it.

### 1.4 The Captain's hard precondition (why the harness came first)
The Captain stated three times: the job must be **flawlessly scoped with a fail-proof harness BEFORE autonomous operation** — otherwise autonomous agents "just reinforce failures." That is *why* the very first phase (Phase F) built the golden-master harness and **proved the harness itself catches regressions (Gate Fα)** before a single line of production code was moved. A behavior-lock you haven't proven is blind is worse than no lock — it manufactures false confidence. This principle recurs everywhere below.

---

## 2 · The HOW (the method — repeatable, follow it exactly)

This is the engine of the whole program. It is five interlocking ideas.

### 2.1 Strangler-fig + golden-master characterization (Michael Feathers)
You cannot safely refactor untested legacy code. So before moving code, **freeze its current observable behavior as a "golden"** (a recorded output), then require any refactor to **reproduce that golden byte-for-byte**. The monolith is strangled incrementally: each god-header chunk is pulled into a clean TU while the golden guarantees behavior is unchanged. We never rewrite; we **relocate verbatim**.

### 2.2 The host-compile oracle (how a golden is produced)
The genius/pain of this codebase is that nothing host-compiles. So an "oracle" **compiles the REAL firmware `.cpp` on the host** (g++/clang, `-O0 -fno-fast-math` for determinism) against a *minimal* Arduino/HAL stub surface, drives it with a **deterministic input trace**, and captures the resulting numeric/behavioral state as **JSONL**. That frozen capture is the golden. Substrate:
- `scripts/regression-harness/golden/oracle_hostcompile.py` — the shared host-compile substrate (Arduino/portMUX stub, include-path wiring).
- `scripts/regression-harness/stubs/` — the stub family (recording `USBSerial`, FreeRTOS shims, etc.).
- `tests/golden/*.golden.jsonl` — the frozen goldens; `tests/golden/MANIFEST.sha256` — anti-gaming checksums.

### 2.3 Gate Fα — the lock must prove it isn't blind
A golden that doesn't notice a real regression is a **false-confidence lock — worse than none.** So every oracle ships **mutations**: deliberate edits to the *real firmware* (a clamp bound, a misrouted write, a shift constant, an int64 flag) that **must** make the golden diverge. `scripts/regression-harness/golden/harness_selftest.py` applies each mutation to a firmware *copy* and asserts divergence. If a mutation slips through, the oracle is blind and the self-test FAILS. This is **Gate Fα**, and it is non-negotiable: *prove the lock catches regressions before you trust it to gate an extraction.* (We caught a self-blind serial mutation this way and fixed the anchor, not the mutation.)

`ORACLE_MODULES` in `harness_selftest.py` is the single registry; `tests/test_golden_master.py` (reproduce + MANIFEST integrity) and `tests/test_harness_selftest.py` (Gate Fα) both consume it. Registered oracles: `onset_beat`, `chord`, `smart_director`, `render`, `gdft`, `serial_replay`. (`tempo` deferred — cross-platform discrete-field flip; `semantic_state`/`spectrum` rejected as stub/replica — they'd lock a copy, not firmware.)

### 2.4 Lock-then-extract (the core loop — repeat per group)
**Never extract code the golden does not cover.** The loop:
1. **Lock (extend coverage first):** if the target group isn't in a golden, extend the oracle's input corpus to cover it, freeze the (now larger) golden, and add **≥2 mutations** proving the new coverage isn't blind. This *legitimately* re-freezes the golden — coverage expansion ≠ gaming, and the firing mutations are the proof it's honest.
2. **Extract (verbatim, gated):** lift the group's bodies **statement-identically** into a clean TU, dispatched via one call from the old site. The gate is: the golden **REPRODUCES byte-for-byte, untouched.** *That identity IS the behavior-preservation proof.* If the golden doesn't reproduce, you changed behavior — fix the extraction, **never** the golden.

The asymmetry matters: a **lock step** edits the golden+MANIFEST (legit, proven by mutations); an **extract step** must leave golden+MANIFEST **untouched** (any golden edit during an extraction is gaming — the MANIFEST integrity test catches it, but don't even try).

### 2.5 Delegate-and-re-verify (the SSA model — the discipline that saved us repeatedly)
Heavy reading, scoping, and extraction are delegated to **fresh-context sub-agents** with tight contracts (conserves the orchestrator's context; gives each task a full window). **But a sub-agent produces prose, not proof** — it is fluent and confident even when wrong. So the **orchestrator personally re-runs the decisive artifact** before any commit: re-run `harness_selftest.py` (Gate Fα), re-run full `pytest tests/`, re-run `pio run -e k1_hardware`, and confirm `git diff` shows the golden+MANIFEST are *not* in an extraction's changeset. This single discipline caught, across this session: a **false flag claim** (an agent said `K1_LOUD_GUARD_V1` was OFF in `k1_hardware`; `platformio.ini` said ON), **10 hidden static-test failures** (an agent's narrow proof ran a subset, not full pytest), a **+160 B production-link leak** (a gated-out `.cpp` emitted a global ctor; caught by byte-comparing the production build), a **self-blind mutation**, and a **phantom "6 includers"** (a substring grep matched a comment, not an `#include`). **None reached a commit. Never skip the re-run.**

### 2.6 Device validation (when host-green is enough, and when it isn't)
- **Behavior-PRESERVING refactors** (everything done so far): host-green (golden + pytest + build) closes intermediate steps; **device-runtime-proof + Captain eyes-on** before merge-to-production. *We have now done this for the whole branch.*
- **Behavior-CHANGING work** (int64 promotion, the I2S timeout fix, timing changes): **always** needs device A/B + Captain eyes-on. Host can't see IRAM placement, Core-0 timing margin, `-ffast-math` float drift on xtensa, or the LEDs.
- **Bayesian update:** before 2026-06-24, "host-green ⇒ device-correct" was an *unproven prior*. The device soak + eyes-on PASS **updated it to a strong prior** — so the next agent can lean on the golden for intermediate extractions, but must still device-validate before promoting anything to the production baseline.

---

## 3 · The WHAT (current validated state — all committed + pushed, CI-green)

### 3.1 The validation chain (the headline)
The whole modernization refactor is validated through the strongest chain available: **host-green → CI-green (Ubuntu cross-platform) → golden-locked → device-runtime soak (75 s, 0 crashes, AP pipeline alive) → Captain eyes-on PASS (2026-06-24, "no visual drift/corruption/faults").** The branch is **mergeable**.

### 3.2 GDFT lane (audit Critical #1)
- `audio/GDFT.h` (the 458-line spectral god-header) → `audio/k1_gdft_core.cpp/.h` — `process_GDFT()` + `calculate_novelty()` lifted **statement-identically** (verified by `diff -w -B` AND exact diff; `IRAM_ATTR` preserved, function-statics preserved). `GDFT.h` is now a thin shim.
- Spectrum oracle `oracle_gdft.py` golden-locks the real transform (driver includes a sustained 16000-amp tone so the int32 overflow is *observable*; emits `spec[80]` + `mag_i32[80]` + novelty). **Red-teamed** (contract §8): exact-diff statement identity, golden reproducibility, 80/80-bin coverage; residual limits documented (single-point trace, coeff-precompute not locked, host≠device float). Gate Fα proves it catches **both** int64 halves.
- The int32→int64 **overflow fix** (`K1_GDFT_INT64_MAGNITUDE_V1` + `K1_GDFT_INT64_RECURRENCE_V1`) is host-deterministic and golden-verifiable but **DEFAULT-OFF**. **S2 (promoting it) is on HOLD** — the Captain eyes-on'd it on the bench (2026-06-21, bundled with `K1_GDFT_TRUE_CENTER_V1`) and judged it *"device-proven capability with no product value"* (the real perceptual issue, "louder→dimmer," is a pre-existing broadband AGC clamp, not this lane). Revisit only as **int64-ALONE** isolation if the Captain wants — host-char shows int64-alone *stabilizes* the resonant bin that currently flickers `38201↔0` (contract §9).
- Contract + red-team + S2 char: [`gdft-decomposition-lane.md`](./gdft-decomposition-lane.md). Dependency inventory: [`gdft-surface-inventory.md`](./gdft-surface-inventory.md).

### 3.3 serial_menu lane (the de-Arduino constraint, in progress)
`serial_menu.h`: **6191 → 4676 lines.** Three chunks extracted, each behind the behavior-lock:
- `serial/k1_ap_capture_telemetry.{h,cpp}` (S1) — AP capture/soak telemetry; **production-gated-OFF** (`ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG`), so the production build was **byte-identical** after extraction.
- `serial/serial_tx.{h,cpp}` + `serial/serial_parse_helpers.{h,cpp}` (S2) — leaf utilities (tx/echo helpers, `vp_parse_bool/float`, clamp/wrap). Production-ON; +20 B benign out-of-lining.
- `serial/serial_cmd_handlers.{h,cpp}` (S4 + S4.1) — **23 pure CONFIG setters** + **7 reboot-bearing setters**, in two dispatchers (`serial_cmd_dispatch_pure_setter`, `serial_cmd_dispatch_reboot_setter`).
- The behavior-lock: `oracle_serial_replay.py` drives the **real** `parse_command` over a deterministic corpus, capturing the **triple** per command — emitted serial text (recording `USBSerial`) + CONFIG field deltas + side-effect flags (`save_config`/`save_config_delayed`/`reboot`/`bad_command`). **8 mutations across all 4 channels**, all caught. Lock design: [`serial-menu-s3-replay-lock-design.md`](./serial-menu-s3-replay-lock-design.md). Seam-map + sequence: [`serial-menu-decomposition-scope.md`](./serial-menu-decomposition-scope.md).
- Host-compile note: the serial oracle uses the **render-oracle compile machinery** (it pulls full `globals.h`), with a **recording** `USBSerial` stub (the emitted text IS part of the golden) and no-op `save_config`/`reboot` recorders (`reboot()` sets a flag + returns — control flow identical, process never exits).

### 3.4 Device + registry
Main K1 `F887A500` on `/dev/cu.usbmodem1101` runs the refactor build (`39466fc`, `k1_hardware`, int64 OFF). 75 s soak: **82 `[AP]` lines (~1.1 Hz), 0 crash markers, 0 reboots**, AP pipeline fully alive (`bpm` 62–120, onset/bass toggling, `agc_gain` 1.6–2.4, `cal_valid=1`). Eyes-on PASS. Registry updated: [`../hardware/device-build-registry.md`](../hardware/device-build-registry.md).

### 3.5 Numbers to expect (sanity baselines)
- `pio run -e k1_hardware` → **RAM 109408 B, Flash 648490 B** (post-S4.1). RAM is stable across all serial extractions; a small Flash delta from out-of-lining is normal.
- `pytest tests/` → **562 passed, 1 skipped, 67 subtests** (the 1 skip is a pre-existing device-gated test).
- `harness_selftest.py` → `GATE_F-alpha: PROVEN` (6 oracles; serial_replay has 8 mutations, gdft has 6).

---

## 4 · Remaining work (Cynefin-classified — match the approach to the domain)

| Work | Cynefin | Approach |
|---|---|---|
| **Merge `feat/gdft-decomposition` → `main`** | **Clear** | Validated; **Captain's promotion call** (do NOT merge to `main` autonomously — it's the production baseline). Highest leverage: makes the modernization the baseline. Recommend first. |
| **serial S5: subsystem-coupled handler families** | **Complicated** | Known lock-then-extract technique, but each family couples to a subsystem. *Probe its host-compile surface first* — some drag FastLED/`led_utilities`/`vpab_capture` and ODR-clash the stubs. Mirror-under-drift-pin (like the S3.0 stubs) or exclude + report. |
| **`set_mode` async slice** | **Complex** | `set_mode` is **NOT** a synchronous setter: it queues a transition; the real `CONFIG.LIGHTSHOW_MODE` write happens later in `led_utilities.h:1517`, echoes a dense index, and couples to the effect registry. **Do not lock a synchronous round-trip** — model the async path, or it freezes wrong behavior. Probe → sense → respond. |
| **`apply_chroma_profile` pair** (`set_chroma_profile` + `bass_mode`) | **Complicated** | They reboot **conditionally** on `apply_chroma_profile()` (an inline in `led_utilities.h` that drags FastLED). The S3.1 stub returns `false` always → would lock `reboot:false` = opposite of production = blind. Needs the real fn host-compiled or mirrored-under-drift-pin **before** locking. |
| **I2S Core-0 `portMAX_DELAY` timeout** | **Complicated** | A real reliability bug (Core-0 audio read can hang). Behavior-CHANGING → own lane, device A/B + eyes-on. |
| **Wireless security** (open AP + shared token) | **Complicated** | Pre-ship hardening. Behavior-changing → device-gated lane. |
| **`.ino` → `main.cpp` + ESP-IDF/CMake** | **Complex** | The constraint endgame (the actual de-Arduino destination). Do *after* the god-headers are extracted (the build-system migration is de-risked by smaller TUs). The `build_src_filter` allowlist footgun is a preview of its hazards. |
| **MabuTrace Core-0 timing margin** | **Complicated** | Owed before *any* non-behavior-preserving default-flip (int64, timing). Trace-dev build, non-shippable. |

---

## 5 · Red-team — what will make the next agent fail (guard against each)

1. **Trusting a delegate's "golden reproduces" without re-running Gate Fα yourself.** Gaming/blindness slips through. *Always* re-run `harness_selftest.py` + confirm `git diff --stat` shows golden+MANIFEST **absent** from an extraction's changeset.
2. **Editing the golden to "make it pass."** Forbidden. The MANIFEST integrity test catches it — but don't even try. Fix the extraction, not the golden.
3. **Extracting a handler you assumed pure that's actually coupled** (the `set_mode` trap). First-hand recon before extracting; exclude + report if coupled. The lock only protects what it *covers*.
4. **Flashing the wrong silicon.** Ports scramble across re-enumeration. **Identity is the chip ID** (`F887A500` = main K1; `B489A500` = bench), **never the port label.** Verify by USB serial / the upload guard before *every* write. `1401`/`12201` in `platformio.ini` are stale port pins — pass `--upload-port` explicitly.
5. **Auto-firing `:start_noise_cal`.** Forbidden. It assumes silence; needs the Captain's verbal silence confirmation. Poisoning calibration with music-during-cal is a STOP-and-rollback incident.
6. **A new `serial/*.cpp` or `k1_*.cpp` silently not compiled.** `build_src_filter` is an **allowlist**, not a glob — add an explicit entry (`serial/*.cpp` is in; new dirs need adding). A missing entry → "undefined reference" link error.
7. **`pytest tests/` returning "No tests collected" in some shells.** A known environment quirk (a matcher intercepts the bare invocation). Run via the venv python with an explicit `-o cache_dir=/tmp/...` if it bites; verify you actually ran 562 tests.
8. **Accumulating gated experiments without deciding them** (the *Growth-and-Underinvestment* archetype). `K1_GDFT_TRUE_CENTER_V1`, `K1_SPECTRAL_WINDOW_V1`, the int64 pair are all default-OFF. **Golden-lock-then-DECIDE** each flag (promote or kill with a reason); don't pile up default-OFF debt that rots.
9. **The recurring cross-TU edges** (these *will* recur on every extraction): (a) a `static` referenced by code that stays behind → widen to `extern` (linkage-only, statements identical); (b) a guard-less impl-header (e.g. `i2s_audio.h`) needed by the new TU → factor its types/constants into a guarded `sb_*_types.h` shared by both, don't double-include the impl-header; (c) put the `#if` gate **before** `#include "globals.h"` in a gated `.cpp` so it preprocesses to *nothing* in production (else a global ctor leaks — byte-compare the production build, don't eyeball); (d) **never move/compile code referencing `FIRMWARE_VERSION`** — it's a `.ino` `#define`, invisible to a separate TU (`init_serial`/`dump_info` stay put).
10. **Treating compile/upload as runtime proof.** It isn't. Behavior-changing work needs serial/timing/eyes-on evidence (sensorybridge-doctrine). MabuTrace is the *mandatory* tool for timing/causality claims — scalar diagnostics quantify a symptom but don't close causal attribution.

---

## 6 · Operating model (your per-slice OODA loop)

- **OBSERVE:** read `.claude/handoff.md` → the relevant contract/scope doc → recent `git log`. Confirm the baselines in §3.5.
- **ORIENT:** pick the next group the golden can cover with a *tractable* lock-extension. **Start from the means already built** (Effectuation): the harness, the stubs, the delegate model, the recurring-edges knowledge — don't invent a grand new plan; compose the next slice from what exists.
- **DECIDE:** a single lock-then-extract directive for one fresh-context delegate, with the discipline (§2.4, §2.5) baked into the contract.
- **ACT:** dispatch → **re-verify the decisive artifacts yourself** → commit small + green → push → confirm CI.

**Cadence:** commit at every green checkpoint, not end-of-session. Small, frequent, green. **Conserve your own context** by delegating heavy work and keeping only the verdict — when you near your context limit, *land a clean validated milestone and hand off*; do not start a slice you can't shepherd to proof (best output ≠ most output).

---

## 7 · Key files index (orientation map)

**Doctrine / state (read first):** `.claude/handoff.md` · `.claude/CLAUDE.md` · `CLAUDE.md` · `docs/architecture/firmware-modernization-program.md` · `docs/audit/2026-06-23-repo-audit.md`.
**GDFT lane:** `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.{cpp,h}` · `audio/GDFT.h` (shim) · `scripts/regression-harness/golden/oracle_gdft.py` · `docs/architecture/gdft-decomposition-lane.md` · `gdft-surface-inventory.md`.
**serial lane:** `SPECTRASYNQ_K1_FIRMWARE/serial/{serial_menu.h, serial_cmd_handlers.*, serial_tx.*, serial_parse_helpers.*, k1_ap_capture_telemetry.*}` · `scripts/regression-harness/golden/{oracle_serial_replay.py, serial_replay_host_stubs.h}` · `docs/architecture/serial-menu-decomposition-scope.md` · `serial-menu-s3-replay-lock-design.md`.
**Harness:** `scripts/regression-harness/golden/{oracle_hostcompile.py, harness_selftest.py}` · `scripts/regression-harness/stubs/` · `tests/golden/{*.golden.jsonl, MANIFEST.sha256}` · `tests/{test_golden_master.py, test_harness_selftest.py}` · `.github/workflows/ci.yml`.
**Device:** `docs/hardware/device-build-registry.md` · `scripts/platformio/k1_upload_guard.py` · `platformio.ini`.

---

## 8 · The non-negotiables (pin these to the wall)

1. **Behavior-preservation is sacred.** The golden reproducing *is* the proof. If it doesn't reproduce, you changed behavior — fix the extraction, never the golden.
2. **Lock-then-extract.** Never extract code a proven golden doesn't cover.
3. **The lock must prove it isn't blind** (Gate Fα) before you trust it.
4. **Re-verify every subagent claim yourself** — re-run the decisive artifact. Prose is not proof.
5. **Statement-identity** for extractions (verbatim lift, no reflow).
6. **Run the FULL `pytest tests/`**, not a subset.
7. **Identity-by-chip-ID before any flash.** Never auto-fire `noise_cal`. 75 s soak after every flash.
8. **Merge to `main` is the Captain's call.** Promotion is never autonomous.
9. **Commit small + green, push, confirm CI.** Never commit unverified.
10. **The perceptual product is the north star.** Architecture serves the show.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-24 | agent:claude-code | Created — comprehensive narrative handover for the K1 modernization (Phase A). Captures the WHY (de-Arduino without perceptual regression), the HOW (strangler-fig + golden-master + Gate Fα + lock-then-extract + delegate-and-re-verify + device validation), the WHAT (validated state on feat/gdft-decomposition, 14 commits, eyes-on PASS), the harness architecture, a Cynefin-classified remaining-work roadmap, the red-team failure list, the recurring cross-TU edges, the device discipline, and the OODA operating model. Companion to the live pointer .claude/handoff.md. |
