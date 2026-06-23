---
abstract: "CTO program spec for the SpectraSynq K1 firmware modernization: Arduino-sketch/header-soup -> modular framework-agnostic C++ core on an ESP-IDF+CMake platform (arduino-esp32 as component), executed as autonomous behavior-preserving lanes. The load-bearing half is the FAIL-PROOF HARNESS (golden-master oracle + anti-gaming gates + harness self-test). Read before scoping or launching any migration lane. Status: RATIFIED 2026-06-23 (Captain) — Phase F (harness) executing; structural lanes gated on Gate Fα."
---

# Firmware Modernization Program (ADR + Execution Spec)

**Status:** **RATIFIED 2026-06-23 by Captain** ("Full Specced, Full Send"). Phase F (harness) is executing; structural lanes (Phase A+) remain gated on **Gate Fα** (harness self-test proven).
**Owner:** Engineering (autonomous lanes) · **Decision authority:** Captain.
**Governing principle (Captain, 2026-06-23):** *With an autonomous multi-lane refactor, the harness IS the product. Scope and harness must be flawless up front, or we reinforce failures at scale.*
**Generic methodology:** this program is the K1 instantiation of the project-agnostic **`autonomous-agentic-build`** skill (`~/.claude/skills/autonomous-agentic-build/` — harness-first doctrine + fill-in `handoff-template.md`, hardened v2). Reuse it for any other long-running autonomous build; this doc is its concrete fill-in.

---

## 1. Decision

**Target architecture:** a modular, multi-translation-unit C++ codebase with a **framework-agnostic DSP/render core** and **thin HAL seams**, built on an **ESP-IDF + CMake** platform with **`arduino-esp32` as a managed component** (FastLED / Wire / USB-CDC keep working unchanged), strangler-figging Arduino out of the core over time.

**Why this destination (not "keep Arduino", not "big-bang IDF"):**
- ESP-IDF + CMake unlocks what a *retail* product needs and Arduino-framework hides: **secure boot, flash encryption, OTA, component model, fine-grained RTOS/power** (the audit flagged secure-boot/OTA absence as a retail gap).
- `arduino-esp32`-as-component means **no big-bang**: every Arduino API keeps working on day one; we shed dependencies from the *core* incrementally, never in one risky cut.
- A framework-agnostic core is the **product-family enabler** (K1 / Tab5 / Emotiscope share one tested DSP core) and the thing that makes the IDF move a *contained swap* rather than a rewrite.

**Why now (Captain's call):** doing the foundation now derisks the downstream launch instead of racing the clock post-launch. Accepted.

**Pacing:** by **gates, not dates**. Agent-hours are cheap; the two true constraints are (a) the **behavior oracle** and (b) **on-device eyes-on** checkpoints that autonomy cannot self-certify.

---

## 2. The current reality (grounding — verified in-repo)

| Axis | State |
|------|-------|
| Build system | PlatformIO / pioarduino — already modern (arduino-cli retired 2026-05-24). |
| HAL / drivers | Substantially IDF-native already: audio uses the IDF v5 I2S driver (`audio/i2s_audio.h:285` `i2s_channel_read`); LED uses FastLED's IDF RMT5 backend. |
| Framework glue | `framework = arduino` — `setup()/loop()`, `Wire`, USB-CDC boot flags, FastLED. |
| **Source architecture (the debt)** | **Single-`.ino` TU + header-soup.** 43 compiled `.cpp` (audio/director/control `sb_*`, 29 `light_mode_*`, globals/Palettes/render_params) + the `.ino`; **everything else is header-defined functions included into the one `.ino` TU** — `serial_menu.h` (6191 LOC) is an ODR landmine that only links because exactly one TU includes it. |
| Oracle seed (good news) | **10 replay harnesses already compile real firmware `.cpp` on host (`clang++ -std=c++17`) and assert numeric outputs** (`scripts/regression-harness/*_replay.py`). The behavior-oracle keystone is half-built. |
| Gaps | No `pio test -e native`; no frozen golden-master; no CI; fixtures thin/local-dependent. |

**Implication:** CI/CD and extensibility are blocked by the *source architecture*, **not** by Arduino. The build and HAL are already most of the way modern.

---

## 3. The fail-proof harness (load-bearing — built and PROVEN before any structural lane)

The autonomous loop's only job is to flow code through this harness. If the harness is weak, autonomy mass-produces plausible-but-broken work. So the harness is built first and must **prove** it is fail-proof.

### 3.1 The Oracle — golden-master behavior equivalence
- **Deterministic input battery** (committed, checksummed): synthetic click-trains at known BPMs, sine sweeps, chord stimuli, silence, AGC/loud-stress, and a few short real-music control clips. Seeds already present (`build/audio-semantic-metrics/control-fixtures/`, `tests/fixtures/`).
- **Taps:** for each input, capture the *current known-good* firmware's outputs at every pipeline stage — GDFT spectrum, novelty, onset events, tempo/beat/phase/confidence, chord/chroma, `AudioSemanticState`, and per-frame LED render buffers.
- **Golden master:** freeze those outputs once, from the pre-migration baseline. **Immutable, checksummed, owned outside the autonomous loop.**
- **Equivalence rule:** every step reproduces the golden master **bit-exact** on integer/fixed-point paths; within a **documented per-tap epsilon** on float paths. Default bit-exact wherever achievable. *If the golden master changes, behavior changed* — which requires an explicit human-approved "behavior-change" ticket, never an autonomous edit.

### 3.2 The Gate (per unit — binary, all required)
1. `pio run -e k1_hardware` compiles (platform lanes: IDF build too).
2. Golden master reproduced within tolerance at **every** tap.
3. Full host suite green; **zero tests deleted or newly skipped** vs baseline; **coverage floor not reduced**.
4. **No harness/oracle/golden file modified** by the unit.
5. render/DSP-touching units are flagged into the **device eyes-on queue**.

### 3.3 Anti-gaming (designed against the exact failure mode: "reinforcing failures")
- **Oracle immutability:** golden masters + harness scripts are checksummed; any diff by a structural lane = automatic FAIL. You cannot pass by weakening the test.
- **Test-deletion/skip detector + coverage floor:** a structural lane cannot reduce test count, IDs, or core coverage.
- **Harness self-test (mutation testing) — the proof of "fail-proof":** before any structural lane runs, inject a battery of deliberate behavior changes (flip a sign, perturb a constant, drop a clamp) and **prove the harness catches every one** (golden master diverges). A harness that misses an injected regression is not trusted. Re-run on a schedule.
- **Rollback-on-red:** a unit that can't reach green is **reverted, never merged**; stuck units escalate to a human queue. Autonomy structurally cannot merge red → cannot reinforce failure.

### 3.4 What autonomy CANNOT self-certify (human + hardware)
The oracle catches numeric regressions. **Perceptual correctness** — Strobe Law, colour clarity, motion memory, dual-channel feel — needs Captain + hardware at phase boundaries. These are explicit, scheduled checkpoints, not optional.

---

## 4. Scope decomposition (the lanes — a dependency DAG)

Each unit is small, independently revertible, and gated by §3. `→` = hard dependency.

**Phase F — Foundation (the harness; must be green + self-test-proven before Phase A):**
- **L0 · CI + hermetic build** — GitHub Actions: `pio run -e k1_hardware` + full pytest + the 10 replay harnesses, on every push. Green becomes machine-verifiable off Captain's machine.
- **L1 · Native test env + Oracle** — formalize the clang++ replay into `pio test -e native`; build + freeze the golden master (§3.1); implement anti-gaming guards (§3.3); **pass the harness self-test.**
- **GATE Fα (Captain + me):** harness self-test demonstrably catches injected regressions. *No structural lane runs until this passes.*

**Phase A — Architecture (strangler-fig; behavior-preserving; gated by L1):**
- **L2 · `.ino` → `main.cpp`** — remove sketch preprocessing; still `framework = arduino`.
- **L3 · God-header decomposition** — header-soup → `.cpp/.h` TU pairs, one unit each, ordered by leverage/risk: `serial_menu` (already half-migrated via the `serial_cmd_table.def` X-macro) → `led_utilities` → `i2s_audio` → `GDFT` → `system` → `audio_transfer` → `encoders` → remainder. Each unit: extract → clean interface → host unit test → golden master unchanged → green.
- **L4 · Framework-agnostic `core/`** — lift the pure DSP (Goertzel/onset/tempo/chord) into a `core/` library with **HAL seams** (I2S/LED/serial/I2C/time as interfaces). The product-family + IDF-enabling boundary.
- **GATE Aβ (device eyes-on):** perceptual parity confirmed on hardware after Phase A.

**Phase P — Platform (only after the core is framework-agnostic):**
- **L5 · IDF + CMake build** — introduce the CMake/IDF project with `arduino-esp32` as a component; **dual-build** (PIO-arduino AND IDF) in CI until byte/behavior parity is proven, then cut over.
- **L6 · Retail platform features** — secure boot, flash encryption, OTA (NEW capability — separately specced + validated, not behavior-preserving).
- **L7 · (optional/eventual)** — shed the Arduino component from the core where it pays.
- **GATE Pγ (device + Captain):** secure-boot/OTA validated on hardware.

**Parallelism:** lanes that don't touch the same files run concurrently; the DAG enforces order. Phase A units are highly parallel (one per header/module).

---

## 5. Autonomous execution model

- Maps to a multi-lane orchestration (Workflow): each unit = one agent working to the §3.2 gate, looping build→test→iterate until green or stuck; stuck → revert + human queue.
- Interleaves with the open audit backlog: the GDFT-overflow fix and I2S-timeout (audit Criticals) are **behavior-CHANGING** and ride a separate ticketed track with their own golden-master update + device A/B — they are *not* folded into behavior-preserving refactor units.
- Each unit is one atomic commit on a lane branch; the harness is the merge gate.

---

## 6. What needs Captain

1. **Ratify or redline this blueprint** (target = IDF+CMake-with-arduino-component; harness-first; gate structure).
2. **Gate Fα sign-off:** I build L0+L1 and *demonstrate* the harness rejects injected regressions — you confirm before structural lanes open.
3. **Device eyes-on at Gate Aβ and Gate Pγ** (perceptual + secure-boot/OTA) — the checkpoints autonomy cannot self-certify.

---

## 7. Pre-mortem (what would make this fail, and the guard)

| Failure | Guard |
|---------|-------|
| Autonomy mass-produces plausible-but-broken code | Golden-master oracle + harness self-test (§3) — proven before any lane runs |
| Agents "pass" by weakening/deleting tests | Oracle immutability + test-deletion detector + coverage floor (§3.3) |
| A refactor silently changes the delicately-tuned DSP | Bit-exact equivalence on fixed-point taps + device eyes-on gates |
| Big-bang IDF cut breaks everything | `arduino-esp32`-as-component + dual-build parity before cutover (L5) |
| Refactor entangled with the launch-critical DSP fixes | Behavior-CHANGING fixes ride a separate ticketed track, never a refactor unit (§5) |
| Forensic/perceptual knowledge lost | Behavior-preserving by construction; golden master is the contract |

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-23 | agent:claude-code (CTO) | Created DRAFT: firmware modernization program + fail-proof harness spec. Awaiting Captain ratification (Gate Fα precedes all structural lanes). |
| 2026-06-23 | captain | RATIFIED ("Full Specced, Full Send, Take No Prisoners"). Phase F execution authorized. Structural lanes remain gated on Gate Fα. |
| 2026-06-24 | agent:claude-code | Added cross-ref: generic methodology canonised as the `autonomous-agentic-build` skill (hardened v2 after adversarial teardown). This program = its K1 instantiation. |
