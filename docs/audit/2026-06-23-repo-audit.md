---
abstract: "Principal-level technical audit of the SensoryBridge K1 ESP32-S3 firmware (HEAD 44c3e7a, branch feat/gdft-corrected-arithmetic-perf-gate, 2026-06-23). Health grade C+: a B+/A- DSP engine wrapped in a not-yet-production-trustworthy shipping artifact + scaffolding. Read for: the prioritized fix plan (Milestones 0-3), the Critical/High findings table with file:line evidence, and the open product questions. Analysis only — no code was modified."
---

# SensoryBridge K1 — Repository Audit (2026-06-23)

**Auditor:** principal-engineer audit pass (orchestrated, 5 specialist agents + orchestrator re-verification of all decision-critical claims).
**Target:** HEAD `44c3e7a`, branch `feat/gdft-corrected-arithmetic-perf-gate`.
**Scope:** whole repo; depth concentrated on the core 20% (audio DSP, render path, control/serial, network, build/test). **Lighter review:** the 201 forensic docs, the `effects/framework/*` graft internals, and the `k1_ap_frontend_probe_matrix_*` env matrix were sampled, not read exhaustively.
**Constraint honored:** no code modified. Every finding cites a file:line that was actually opened/verified.

---

## 1. Executive Summary

**Overall health grade: C+** — the DSP/firmware engine is genuinely strong (B+/A-), but the *shipped artifact* and the *scaffolding around it* are not yet production-trustworthy, and that gap is the story. The core engineering shows real rigor: a compile-time-enforced cross-core split (`.ino:111-113` `#error`), a torn-read-safe `portMUX` snapshot pattern, a wireless input parser that is hardened beyond typical hobby firmware (length/NUL/duplicate-key rejection, per-client monotonic replay protection), per-constant calibration provenance in the DSP, and a device-identity upload guard. Against that, three classes of problem drag the grade down. **(1) Correctness defects ship by default:** the integer Goertzel overflow that silently zeros spectral bins under loud audio is fixed *on this very branch and device-validated* but is absent from the `k1_hardware` build (`platformio.ini` — 0 occurrences of `K1_GDFT_INT64_*`), and the Core-0 audio read blocks on `portMAX_DELAY` with no timeout/recovery (`i2s_audio.h:285`). **(2) The quality scaffolding is not enforced:** there is no CI, the "load-bearing" pre-commit gate is *not installed in this clone* (`hooksPath` = default), and the headline DSP-accuracy metrics depend on local-only audio files, so "host gate GREEN" is true only on one machine. **(3) Process/onboarding debt is severe:** the README is the wrong product's (ESP32-S2 upstream Sensory Bridge), doc "current state" claims are stale and self-contradicting (test count cited as 427 vs. real 586; five different host-gate pass counts across the nav chain), and the working tree carries 203 MB of half-committed `_scratch/` and 3.0 GB / 54 git worktrees of orphaned agent state. **Top risks:** a Kickstarter-bound binary that degrades its core spectral engine on loud music; an unenforced quality gate making every "green" claim unverifiable by a second party; and a wireless control plane (open AP + repo-public shared token) that provides no real access control the moment it ships. **Top opportunities:** promote the already-validated GDFT fix; stand up a 1-file CI + install the gate that already exists; and finish the half-built `serial_menu.h` table migration to kill the 6,191-line ODR-landmine god-header. None of the top fixes are large; the leverage is high because the underlying engineering is sound.

---

## 2. Repo Map

**Purpose.** Real-time audio-reactive lighting firmware for **K1**, a dual-channel edge-lit Light-Guide-Plate hardware product (pre-production, Kickstarter-bound). Translates music → visual via Goertzel spectral analysis (80 bins → 24 perceptual bands @ 133 Hz), beat/onset/chord detection, and a dual-core render pipeline targeting <50 ms audio-to-LED.

**Stack.** C++17 · Arduino framework on **ESP32-S3-DevKitC-1-N16R8** · **PlatformIO** (pioarduino 54.03.20 ≡ arduino-esp32 3.2.0 / ESP-IDF 5.4.1) · FastLED 3.10.3 (RMT5 DMA) · I2S audio · host-side **pytest** regression harness (Python). Vendored libs: FixedPoints, M5ROTATE8; optional WebSockets (wireless) + MabuTrace (trace).

**Maturity.** Mature-but-churning **R&D firmware for a real product** — not a prototype, not a stable release. Currently deep in a GDFT-arithmetic forensic lane. "Device eyes-on" is the declared final gate.

**Scale.** 136 firmware source files / ~42,300 LOC · 74 pytest files / 586 tests · ~700 project markdown docs (320 under `docs/`, 201 of them in `docs/forensics/`) · 40 PlatformIO build environments.

**Architecture sketch (audio → light):**
```
I2S mic (12.8 kHz DMA, Core 0)
  → Goertzel GDFT (133 Hz frames, 96-sample chunks)   audio/GDFT.h, audio/i2s_audio.h
  → novelty / onset / chord / tempo (PLL flywheel)     audio/sb_tempo.cpp, sb_onset_beat.cpp, sb_musical_saliency.cpp
  → AudioSemanticState / SBAudioSnapshot (volatile + portMUX publish)   audio/sb_audio_snapshot.*
  → Smart Director / Beat-aware Director (mode routing)   director/sb_smart_director.cpp, beat_aware_director.cpp
  → effect render (Core 1, ~100 FPS)   effects/light_mode_*.cpp  (+ gated effects/framework/*)
  → led_utilities.h composition → FastLED RMT5 → dual-channel LGP
```

**Key directories (one line each):**
| Dir | Role |
|-----|------|
| `SPECTRASYNQ_K1_FIRMWARE/audio/` | DSP: Goertzel, onset, tempo, chord, snapshot publish (Core 0 hard-RT) |
| `SPECTRASYNQ_K1_FIRMWARE/visual/` | render math, palettes, `led_utilities.h` composition |
| `SPECTRASYNQ_K1_FIRMWARE/effects/` | 29 legacy `light_mode_*.cpp` + gated `framework/*` (registry/zone/transition) |
| `SPECTRASYNQ_K1_FIRMWARE/director/` | mode routing, beat-aware selection |
| `SPECTRASYNQ_K1_FIRMWARE/control/` | `sb_k1_control_facade.cpp` — typed/validated command surface |
| `SPECTRASYNQ_K1_FIRMWARE/serial/` | `serial_menu.h` (6,191-line USB-CDC command parser) |
| `SPECTRASYNQ_K1_FIRMWARE/network/` | `sb_k1_wireless.cpp` — AP-only WebSocket control bridge (off by default) |
| `SPECTRASYNQ_K1_FIRMWARE/system/` | `globals.h` (288 globals), config, constants |
| `SPECTRASYNQ_K1_FIRMWARE/diag/` | VPAB capture, motion lab, harnesses (instrumentation-boundary fenced) |
| `tests/` | 74 pytest files: 33 static, replay, gates |
| `scripts/` | PIO pre-scripts (src includes, upload guard), regression harness, git hooks |
| `docs/` | 320 md; `docs/forensics/` = 201; spec-index / handover / device registry |

**Surprises (verified):**
- The **README is for a different product** (upstream ESP32-S2 Sensory Bridge) — `README.md` links `connornishijima/SensoryBridge`, says "ESP32-S2 / Arduino IDE / $50 assembled"; 0 mentions of K1/S3/PlatformIO.
- **40 build environments**, ~30 of them disposable probe-matrix variants, all living permanently in the canonical `platformio.ini`.
- The **fix for the bug the current branch is named after is not in the production build** (`K1_GDFT_INT64_*` / `TRUE_CENTER`: 0 occurrences in `[env:k1_hardware]`).
- **3.0 GB `.claude/` + 54 git worktrees** of orphaned agent state shadow the tree (and pollute repo-wide greps with stale copies).

---

## 3. Audit Report

Severity calibrated to *"consumer hardware product approaching production/Kickstarter."* Each finding: what · where (file:line) · consequence · **FACT** (verifiable) or **JUDGMENT** (auditor read). Findings consolidated across the 5 dimension passes; orchestrator independently re-verified every Critical/High.

### 3.1 Architecture & Design

**[High] God-header `serial_menu.h` (6,191 lines) is an ODR landmine held together by single-TU accident**
~125 non-`inline` function definitions at file scope; included by exactly one TU (`.ino:39`). The hazard is even documented in-tree (`visual/lightshow_modes.h:11-15`). The day a 2nd `.cpp` includes it → ~125 multiple-definition link errors. It also makes the command parser un-unit-testable (which is why pytest can validate DSP but not the parser). **FACT.**

**[High] `parse_command` is a single ~2,293-line / ~768-cyclomatic function** (`serial/serial_menu.h:3373-5665`) — a `strcmp` ladder of 131+ arms. Command precedence is positional, so a misplaced `else` silently shadows commands; effectively unreviewable and untestable as a unit. A table-driven migration is *started* (`serial_cmd_table.def` X-macro at `:3276`) but most arms remain. **FACT.**

**[High] 288 flat mutable globals in one header + cross-layer `CONFIG` writes** (`system/globals.h`; 18 writer files including the layering violation `effects/light_mode_kaleidoscope.cpp` mutating persisted `CONFIG` directly). No encapsulation, no typed-setter chokepoint; a render-path/effect bug can corrupt flash-backed config. **FACT.**

**[High] Half-migrated parallel effect architecture.** 29 live `light_mode_*.cpp` vs. a fully-gated `effects/framework/*` (EffectRegistry/ZoneComposer/TransitionEngine) whose 5 native effects are dark/broken and OFF in production (`K1_EFFECT_FRAMEWORK_V1`/`_REGISTRY_V1` defined only in non-shippable probe envs, `platformio.ini:633,661`). Gating discipline is genuinely clean (production binary byte-unchanged), so this is *decision/carrying debt*, not a runtime hazard — but it is two authoring models + a 35-row registry that must be hand-synced to the 30-mode enum. **FACT (state) / JUDGMENT (disposition).**

**[Medium] Copy-paste effect variants by policy.** `light_mode_dense_forge_chord.cpp` is a near-verbatim copy of `light_mode_dense_forge.cpp` (287 lines each; the copy's header states the "never modify originals; new behaviour = new file" Captain policy). Also `ember`/`ember_v2`, `tempo_comet`/`_anticipate`. A bug fix or the Strobe-Law invariant must be applied in N bodies that will diverge. Deliberate tradeoff, but unbounded. **FACT/JUDGMENT.**

**[Medium] Production loop and tempo core are shredded by interleaved instrumentation** (`.ino:1035-1076`; `sb_tempo.cpp:1338-1416` six `sb_dbg_stage_*` sandwiches in `sb_tempo_update`; `led_utilities.h:889-1072` `show_leds` = 184 lines / 36 branches / ~9 jobs). Real algorithm lines run ~1:1 with `#if ENABLE_*` probe blocks — directly against the project's own Developer Instrumentation Boundary doctrine. **FACT/JUDGMENT.**

### 3.2 Code Quality

**[High] Inconsistent/missing bounds-checking on serial-parsed input reaches *persisted* CONFIG.** Most setters clamp via `constrain()`, but `serial_menu.h:4585` writes `CONFIG.SENSITIVITY = atof(...)` unclamped; `:4939/:4984/:5004` hand-roll clamps instead of `constrain`; `:5576` `atoi(command_buf + 15)` reads one byte past the 14-char `"SECONDARY_MODE"` literal; `:3422-3441` fixed 32/94-byte buffers silently truncate (a 33-char unknown command can alias a shorter valid prefix). Per-arm discipline ⇒ inevitable gaps; malformed values reach flash. **FACT.**

**[High] Unguarded float→int LED indexing on fixed 160-element buffers in the per-frame render path.** `visual/led_utilities.h:277-295` (`lerp_led_16`) and `:868-887` (`scale_to_strip`) dereference `index_right = index_whole + 1` up to index 161 on 160-element buffers, with no clamp — while the sibling `:257-275` (`lerp_led_NEW`) *does* guard, proving inconsistent application. Underflow-prone `shift_leds_*` size math at `:1202-1209`. Silent memory corruption at the top of the LED range, not a clean crash. **FACT.**

**[Medium] `try/catch(...){}` with a dead success flag in the render path** (`led_utilities.h:976-981`) — C++ exceptions in an ESP32 render loop are heavyweight/non-deterministic and the empty catch swallows failures silently. **FACT.**

**[Medium] Compile-flag sprawl.** Repo-wide ~19 feature flags; `audio/sb_tempo.cpp` alone is gated by 36 flags / 159 preprocessor directives, with v1 *and* v2 paths both compiled-from-source (~22-25% of its 1,615 lines is dead/probe/legacy). `sb_tempo_reset()` must manually re-zero 60+ statics across four `#ifdef` blocks — one missed field is a latent stale-state bug. (Contrast `sb_onset_beat.cpp`: 1 flag, ~19 statics — proof the team *can* write clean gated DSP.) **FACT.**

### 3.3 Performance & Real-Time Safety

**[High] Core-0 I2S read blocks on `portMAX_DELAY` with no timeout/watchdog escape** (`audio/i2s_audio.h:285`). The DMA fill is the audio frame clock (nominal ~7.5 ms wait), but any DMA stall parks the hard-RT core forever; `bytes_read` is discarded unless `ENABLE_AP_FRONTEND_DEBUG`. No graceful-degrade path — contradicts the project's own "never block Core 0" doctrine. **FACT.**

**[High] Integer Goertzel overflow ships in the production default and silently zeros spectral bins under loud audio.** The int32 magnitude path (`q*q` overflows ~int32 at q≈160k → negative → clamped to 0) and the int32 recurrence multiply (`coeff_q14 * (int32_t)q1` overflows at q1≈67k) live in `audio/GDFT.h:132-163` `#else` fallback. The fixes (`K1_GDFT_INT64_MAGNITUDE_V1`, `K1_GDFT_INT64_RECURRENCE_V1`) are device-proven (git `68ff630`, `fcbcad1`, `926ed40` — "device A/B PASSES") **but absent from `[env:k1_hardware]`** (orchestrator-verified: 0 occurrences). Degrades the spectral engine every effect/onset/chord/tempo consumer depends on, exactly when it matters (loud music). *Note:* the sibling `K1_GDFT_TRUE_CENTER_V1` failed eyes-on (HEAD `44c3e7a`) — the overflow fix must be promoted **separately** from true-center. **FACT.**

**[High] Full ACF recomputed every novelty emit (44.44 Hz) on Core 0, with no measured production headroom.** `sb_tempo.cpp:1358-1368` sets `sb_acf_refresh_now` every emit by default (`SB_TEMPO_ACF_REFRESH_DECIMATION 1U`); `sb_compute_acf_salience()` (`:643`) does 512×~200 MAC + 96-bin comb scoring on the audio core. Device measurement at 16 kHz/120 shows cadence collapse 133→123 Hz + WDT into `sb_tempo.cpp:529` (`docs/forensics/2026-06-15-16k120-ap-stage-profile-verdict.md`). Production 12.8k/96 is *assumed* survivable (validated by absence-of-overrun, not a headroom number). The amortized path (`sb_compute_acf_salience_spread`, `:651-683`) exists in probe envs but isn't in production. First failure point as the AP pipeline grows. **FACT (measurement) / JUDGMENT (production headroom).**

**[Medium] ~427-byte `SBAudioSnapshot` copied under `portENTER_CRITICAL` at 133 Hz, no `sizeof` gate** (`audio/sb_audio_snapshot.cpp:105-115`; struct `:57-84`, `spectrum[80]`=320 B dominates, grows with each additive V2 flag). Works today; a scalability trap — every new `#ifdef` field silently lengthens the cross-core critical section. A prior strobe-reboot was tied to a similar large-struct stack copy. **FACT.**

**[Medium] Cross-core `led_thread_halt` read as a plain (non-`volatile`) `bool` on the production path.** `system/globals.h:378-382` makes it `volatile` only under `K1_EFFECT_FRAMEWORK_V1`; the production `#else` is a plain `bool`, read at `.ino:1026` on Core 1 while Core 0 may write it. Under `-O3` the compiler may cache it in a register → late/missed halt. Genuine memory-model hole on the exact path that ships. **FACT (decl) / JUDGMENT (likelihood).**

**[Medium] No end-to-end `<50 ms` latency measurement exists.** VPAB captures render-side `render_us`/`frame_us`/`show_us` only (`diag/vpab_capture.h:24-58`); no audio-to-LED trace in `docs/`. The customer-facing "<50 ms" claim has a defensible arithmetic lower bound (~17.5 ms) but no captured evidence. **FACT (no measurement) / JUDGMENT (promise risk).**

### 3.4 Security & Config

**[High — latent until wireless ships] Open AP + repo-public shared static control token = no real access control.** `network/sb_k1_wireless.cpp:20` `K1_AP_PASSWORD = ""` (open, unencrypted AP, fixed SSID `"LightwaveOS-AP"` `:19`); auth is one compile-time `strcmp` against `K1_CONTROL_TOKEN`, defaulting to `"k1-tab5"` and baked into every unit (`:37` + `platformio.ini:68`). The token is in this public repo and in the binary, sent in cleartext over an open AP → anyone in RF range can read it and drive any K1. Wireless is **OFF by default** (`default_envs = k1_hardware` does not define `SB_K1_WIRELESS_ENABLED`), so this is the model that *will* ship, not a live exposure. Fix before enabling for backers: non-empty WPA2 + per-device token derived from `ESP.getEfuseMac()` (already read in `utilities.h:25`). **FACT.**

**[Medium] License-of-record contradiction: `LICENSE` = GPL-3.0, but `CLAUDE.md` says MIT.** GPL-3.0 imposes copyleft/source-availability obligations on a shipped binary — must be reconciled before distribution. Compounded: the GPL-3.0 MabuTrace dep (`platformio.ini:243`) is excluded from production *only by env discipline* — airtight by construction, but **no automated gate** fails the build if it leaks into `k1_hardware`. **FACT / JUDGMENT.**

**[Medium] Floating `^` version on the one network-facing dependency.** `links2004/WebSockets@^2.4.0` (`platformio.ini:213`) resolves to any `2.x` at build time, vs. exact-pinned FastLED (`@3.10.3`). Non-reproducible builds for the untrusted-input WS parser; pin it exactly. **FACT.**

**[Low] No secure-boot / flash-encryption** (`platformio.ini` has no `CONFIG_SECURE_BOOT`/`CONFIG_FLASH_ENCRYPTION`) — firmware can be USB-dumped (exposing the static token) and replaced. Upload guard (`scripts/platformio/k1_upload_guard.py`) genuinely verifies USB-serial/chip-ID identity and hard-`SystemExit`s on mismatch — but it's a build-host convenience, not field anti-tamper. **FACT/JUDGMENT.**

**[Low] `-O3 -ffast-math` globally** (`platformio.ini:78-79`) — not a vuln, but `-ffast-math` lets the compiler assume finiteness and may elide the `isfinite()`/`strtof` guards the wireless float parser relies on (`sb_k1_wireless.cpp:251-263`); downstream values are `constrain()`-clamped, so low. **FACT/JUDGMENT.**

*Verified strengths here (do not "fix"): WS input is genuinely hardened (length/NUL/duplicate-key rejection `:633-648`, per-client monotonic replay protection `:398-419`, control allowlist `:711`); the serial path is physically gated (USB-CDC) and consistently bounds-checked at its parse sites; no real secrets are committed (`wifi_credentials.ini` is untracked, only an empty-password `.template`).*

### 3.5 Testing, DevEx & CI

**[Critical] Zero CI automation.** No `.github/workflows`, no `.gitlab-ci`, nothing (orchestrator-verified). Every "host gate GREEN" claim is local-machine-only; a second dev / fresh clone / remote runner cannot reproduce it. For a launch that needs external trust in the quality claim, this is the single biggest scaffolding gap. **FACT.**

**[Critical] The "load-bearing" pre-commit gate is not installed in this clone.** `git config core.hooksPath` = default `.git/hooks`; no `pre-commit` there (only `.sample`). `scripts/hooks/install.sh` must be run per-clone and wasn't — so the tiered pytest+`pio run` gate is silently non-operational on the canonical dev machine. **FACT.**

**[High] Headline DSP-accuracy metrics are not reproducible offline.** Fixture manifest (`scripts/regression-harness/fixtures/k1_av_regression_fixtures.template.json`) points at `~/Downloads/*.mp3` and `PENDING_CAPTAIN_TRACK_PATH`; `tests/fixtures/` has no audio. So `Acc1/Acc2`, tempo-confidence 0.620, density 97.2% are *documentation, not running tests* — a fresh `pytest tests/` verifies infra, not the product claims. **FACT.**

**[High] ~33 `*_static.py` tests include source-text grep checks, not behavior** (`tests/test_k1_av_regression_static.py` — `assertIn("vTaskDelay(1);", source)` etc.). They pass even if the code is dead/misplaced and false-fail on benign refactors; useful as spelling-regression guards but must not be counted as behavioral coverage. **FACT.**

**[High] Replay tests are opaque subprocess delegates** — `assertIn("ONSET_BEAT_REPLAY_OK cases=7", stdout)` (`tests/test_onset_beat_replay.py:16`, same shape in director/semantic/chord replays). On failure pytest prints an undifferentiated blob — no per-case ID, no diff, no metric; and the hardcoded `cases=N` silently breaks if a case is added. (The *underlying* harness compiles real `.cpp` and asserts numerics — that architecture is a strength; the pytest surface throws the diagnostics away.) **FACT.**

**[Medium] No Python lint/format/deps config.** No `ruff`/`black`/`pyproject.toml`/`.pre-commit-config.yaml` at root, no `requirements.txt` — 74 test files + ~80 harness scripts drift unchecked, and a new dev has no reproducible setup. **FACT.**

**[Medium] 40 build environments create target confusion** — only ~5 are shippable/reference; ~30 are probe-matrix variants with no deprecation/archival policy, permanently in the canonical build file. **FACT/JUDGMENT.**

### 3.6 Documentation & Repo Hygiene

**[Critical] README is the wrong product's README** (upstream ESP32-S2 Sensory Bridge). `README.md` links `connornishijima/SensoryBridge`, says "ESP32-S2 / Arduino IDE / $50 assembled"; **0** mentions of K1, S3, PlatformIO, `pio run`, or pytest (orchestrator-verified). No engineer can build K1 from it; the real build truth lives only in agent-facing `CLAUDE.md`. **FACT.**

**[High] Stale, self-contradicting "current state."** `CLAUDE.md` cites "427 tests / 54 files" in 8 places; real = **586 tests / 74 files** (orchestrator-verified). The nav chain (`progress.md`→`.claude/handoff.md`→`docs/spec-index.md`) — the declared on-disk source of truth — quotes **five different** host-gate pass counts (309/310/427/458/550) and points at HEADs (`88a1bc3`/`f0c6808`) that aren't the live HEAD (`44c3e7a`). The truth-navigation system is itself untrustworthy. **FACT.**

**[High] Workspace litter at scale.** `_scratch/` = **203 MB, 72 files tracked in git** (and several untracked dirs in every `git status`); `.claude/` = **3.0 GB with 54 git worktrees** of orphaned agent state (whose stale `config_types.h` copies pollute repo-wide greps); `docs/forensics/` = **201 docs / 63 dated folders**, near-zero curation; **no root `CHANGELOG.md`** despite mandated changelog discipline. The repo violates its own hygiene doctrine. **FACT.**

**[Medium] `<50 ms` latency is doc-only** (customer-facing, in the abstract) with no in-repo measurement; "133 Hz" *is* arithmetically backed (12800/96, `config_types.h:37,41`). **FACT.**

*Correction to a subagent claim (orchestrator-verified):* `.gitignore` is **not** "effectively empty" — it is **95 lines and thoughtfully written** (ignores `.pio` build output, `.claude/worktrees/`, caches, `task_plan.md`, etc.). The real, narrower gap: **`_scratch/` and `.codex-subagent/` are not ignored**, so 72 scratch files are tracked and `.codex-subagent/` litters the tree.

---

## 4. Strengths (preserve — do not "refactor away")

- **Cross-core architecture is correct and compile-enforced.** `.ino:111-113` `#error`s if AP+render share a core; `portMUX` whole-struct snapshot (`sb_audio_snapshot.cpp:105-116`) is torn-read-safe by construction; consistent across snapshot/onset/tempo publishers.
- **`control/sb_k1_control_facade.cpp:33-80` is the model the serial parser should follow** — typed, validated (`needs_number_range`, structured error codes, `strlcpy` throughout).
- **Wireless input parsing is hardened beyond typical ESP32 firmware** — length/NUL/duplicate-key rejection, per-client monotonic replay protection, control allowlist.
- **DSP constants carry calibration-script + corpus provenance** (`sb_tempo.cpp:240-264, 343-373`); the mode enum documents *why* IDs are append-only/NVS-persisted (`config_types.h:137-144`).
- **Instrumentation-boundary discipline is real and test-enforced** — `tests/test_dev_instrumentation_boundary.py` parses `platformio.ini` inheritance and forbids MabuTrace/trace tokens in production envs; framework graft is provably byte-zero in production.
- **The best tests compile real firmware `.cpp` at host and assert numerics** (`scripts/regression-harness/onset_beat_replay.py`, `test_beat_aware_director_static.py`, `test_rate_consistency.py` rate-domain alpha derivation) — the right approach for embedded DSP.
- **Render path is heap-clean** (no per-frame `malloc`/`String`/`vector`); **upload guard genuinely verifies device identity** and hard-blocks cross-flashing.
- **`platformio.ini` build provenance is excellent** — every non-obvious flag dated + justified, with explicit REVERT instructions.

---

## 5. Improvement Strategy

Five themes explain ~90% of the findings.

**Theme A — Validated fixes aren't promoted; the shipped binary lags the proven one.**
*Target state:* the production `k1_hardware` binary is the best-validated arithmetic the team has produced. *Principle:* "device-validated" must converge to "shipping." The GDFT overflow fix and the ACF amortization both exist and are proven in branches/probe envs; the gap is a promotion + single device A/B, not new work.

**Theme B — Quality is asserted, not enforced or reproducible.**
*Target state:* a second party (CI, a fresh clone, a backer-facing claim) can reproduce every "green." *Principle:* a gate that isn't installed and metrics that need one person's `~/Downloads` are theatre. Install the existing gate, add 1-file CI, and commit deterministic synthetic fixtures so the headline DSP metrics run anywhere.

**Theme C — Accreted state masquerades as canonical.**
*Target state:* one trustworthy README, one generated test count, one synced nav chain, a gitignored scratch space. *Principle:* the project already *documents* "one canonical file per topic" and "ground copy in implemented behavior" — apply its own doctrine to itself. The wrong-product README and 5-way-contradictory counts are curation lapses, not structural inability (the mode-enum doc proves docs *can* be kept true).

**Theme D — A few god-files concentrate the risk.**
*Target state:* `serial_menu.h` becomes a table-driven `.cpp` TU; `CONFIG` writes go through a typed setter chokepoint; the dual effect-framework fork is resolved (finish or excise). *Principle:* the 6,191-line parser is simultaneously the #1 untestable surface *and* where unclamped values reach flash — fixing it is the highest leverage-per-hour structural move, and it's half-built already.

**Explicitly NOT recommending (effort vs. payoff / maturity):**
- A full audio/visual rewrite, an HAL abstraction layer, or de-`#ifdef`-ing the whole DSP — the engine works; churn risk outweighs payoff pre-launch.
- Enterprise observability/secure-boot/OTA infrastructure now — secure-boot *should* be on the pre-ship checklist, but it's a launch-gate decision, not a refactor.
- Mass-renaming `sb_`→`k1_` (Captain standing order forbids it) or "fixing" the copy-paste-variant policy (Captain-ratified) — surface as a tradeoff, don't override.
- Deleting the 201 forensic docs — archive/index them; they're institutional memory.

**Definition of done (measurable):**
1. CI runs `pytest -k "not device"` + `pio run -e k1_hardware` on every push; red CI blocks merge.
2. Pre-commit gate installed and verified active (`core.hooksPath` set).
3. Zero Critical findings open; the GDFT overflow fix in `k1_hardware` (device A/B re-confirmed) or an explicit written decision why not.
4. README builds K1 from scratch with no other doc; test count generated, not hand-typed; nav chain == HEAD.
5. `_scratch/` + `.codex-subagent/` gitignored; 72 tracked scratch files removed from the index.
6. WebSockets exact-pinned; LICENSE reconciled; MabuTrace-absence is a hard release gate.

---

## 6. Task Plan

### Quick wins (high impact · S effort · do immediately)
| # | Task | Effort | Why now |
|---|------|--------|---------|
| QW1 | `./scripts/hooks/install.sh` + verify `core.hooksPath` set; document in README | S | The gate already exists and is simply off. |
| QW2 | Add `_scratch/`, `.codex-subagent/` to `.gitignore`; `git rm -r --cached` the 72 tracked scratch files | S | Stops the bleed; 203 MB + noise out of `git status`. |
| QW3 | Exact-pin `links2004/WebSockets@2.4.x` (drop `^`) in `platformio.ini:213` | S | Reproducible builds for the one network-facing dep. |
| QW4 | Reconcile LICENSE: decide GPL-3.0 vs MIT; make `LICENSE` and `CLAUDE.md` agree | S (decision) | Copyleft obligation must be settled before distribution. |
| QW5 | Add `sizeof(SBAudioSnapshot)`/`AudioSemanticState` `static_assert` size ceilings | S | Catches the spinlock/stack-copy regression class at compile time. |
| QW6 | Regenerate the test count (`pytest --co -q`) and fix the 8 stale `427/54` citations | S | One number, repeated wrong 8×; trivially correct. |

### Milestone 0 — Safety net (before any refactor)
| ID | Task | Files/areas | Acceptance | Effort | Change-risk | Deps |
|----|------|-------------|------------|--------|-------------|------|
| M0.1 | **CI pipeline** (GitHub Actions): `pytest -k "not device"` + `pio run -e k1_hardware` on push/PR | `.github/workflows/ci.yml` (new) | Green required to merge; red blocks | M | Low | — |
| M0.2 | Install + enforce pre-commit gate; add `requirements.txt` for harness | `scripts/hooks/`, repo root | `core.hooksPath` set; fresh clone instructions work | S | Low | — |
| M0.3 | **Deterministic synthetic golden fixtures** (tone/beat trains at known BPM) so onset/beat/chord metrics run with no proprietary audio | `tests/fixtures/`, `scripts/regression-harness/` | `pytest tests/` reproduces ≥1 headline metric offline in CI | L | Low | M0.1 |
| M0.4 | Python lint/format: `ruff` + `pyproject.toml`; wire into CI + pre-commit | repo root | CI fails on lint; format enforced | S | Low | M0.1 |

### Milestone 1 — Critical correctness & security
| ID | Task | Files/areas | Acceptance | Effort | Change-risk | Deps |
|----|------|-------------|------------|--------|-------------|------|
| M1.1 | **Promote GDFT int64 overflow fix to `k1_hardware`** (magnitude+recurrence ONLY; exclude true-center which failed eyes-on); re-confirm device A/B on 12201 | `platformio.ini`, `audio/GDFT.h` | Loud-tone A/B shows no bin-zeroing; eyes-on PASS; flags in prod env | M | **Med** (DSP path) | M0.1, device |
| M1.2 | **I2S read timeout + recovery** — replace `portMAX_DELAY` with bounded timeout + short-read handling + WDT-safe degrade | `audio/i2s_audio.h:285` | Injected DMA stall → recovers, logs, no freeze | M | **Med** (hard-RT) | M0.3 |
| M1.3 | Fix unguarded LED-index OOB in render path (`lerp_led_16`, `scale_to_strip`, `shift_leds_*`) | `visual/led_utilities.h:277,868,1202` | Clamped indices; fuzz over offset range no OOB | S | Low | M0.3 |
| M1.4 | **Pre-wireless security pack** (gate before backers): non-empty WPA2 default + per-device token from `getEfuseMac()`; exact-pin WS | `network/sb_k1_wireless.cpp:20,37`, `platformio.ini` | Open-AP + shared-token removed; per-unit secret; surfaced via pairing | M | Low (off by default) | QW3 |
| M1.5 | **MabuTrace-absence release gate** (CI fails if trace symbols/flags in `k1_hardware` binary) | CI, `scripts/` | Build fails on leak | S | Low | M0.1 |

### Milestone 2 — High-leverage structural
| ID | Task | Files/areas | Acceptance | Effort | Change-risk | Deps |
|----|------|-------------|------------|--------|-------------|------|
| M2.1 | **`serial_menu.h` decomposition** — finish the `serial_cmd_table.def` migration into a real `serial_menu.cpp` TU; kills ODR landmine + makes parser host-testable + closes bounds-check gaps via one validated setter path | `serial/serial_menu.*`, `.ino:39` | Parser in `.cpp`; host unit tests for ≥20 commands; ODR-safe (2nd include compiles) | XL | **Med** | M0.1, M0.3 |
| M2.2 | **Typed `CONFIG` setter chokepoint**; remove direct cross-layer writes (esp. `light_mode_kaleidoscope.cpp`) | `system/globals*.h`, 18 writers | All clamps in one place; no effect-layer CONFIG writes | L | Med | M2.1 |
| M2.3 | **Resolve effect-framework fork** — decide finish-migration vs excise probe envs; document the call | `effects/framework/*`, `platformio.ini` | One authoring model of record; registry sync automated or removed | L | Low | — |
| M2.4 | **Rewrite README** from verified build truth (S3-N16R8, `pio run -e k1_hardware`, upload guard, pytest) | `README.md` | New engineer builds + flashes from README alone | M | Low | — |
| M2.5 | Promote ACF amortization (`*_spread`) to production after device cadence A/B | `audio/sb_tempo.cpp`, `platformio.ini` | 12.8k/96 measured headroom > target; eyes-on PASS | M | Med | M1.1 |

### Milestone 3 — Quality & polish
| ID | Task | Acceptance | Effort | Risk |
|----|------|------------|--------|------|
| M3.1 | Prune/archive the ~30 probe-matrix envs; keep ~7 documented; CLAUDE.md env table == reality | `platformio.ini` ≤ ~10 envs | M | Low |
| M3.2 | Replay-test diagnostics: emit structured JSON, assert per-case in pytest | per-case failure messages | M | Low |
| M3.3 | `conftest.py` shared fixtures (kill the duplicated `importlib` boilerplate in 12+ files) | one fixture, no dup | S | Low |
| M3.4 | Stand up root `CHANGELOG.md` (`[Unreleased]`); re-sync nav chain to HEAD as a release step | exists + current | S | Low |
| M3.5 | Worktree/`.claude` cleanup: prune 54 stale worktrees / 3 GB | `git worktree prune`; size down | S | Low |
| M3.6 | Scope `-ffast-math` off the DSP TUs (or document the accepted risk per-file) | DSP builds strict-FP or documented | M | Med |

### Top-3 task implementation sketches

**M1.1 — Promote the GDFT int64 overflow fix (highest correctness ROI).**
Approach: the fix is *already written and device-validated*; this is promotion, not authoring. Steps: (1) In `[env:k1_hardware]` add `-DK1_GDFT_INT64_MAGNITUDE_V1` and `-DK1_GDFT_INT64_RECURRENCE_V1` **only** — do **not** add `K1_GDFT_TRUE_CENTER_V1` (HEAD `44c3e7a` records it failing eyes-on; keep it isolated). (2) `pio run -e k1_hardware` + host gate green. (3) Device A/B on bench 12201 (`k1_bench_reference`, chip `B489A500` — per device registry, never cross-flash to 1401): loud sustained tone, confirm no bin-zeroing vs. baseline. (4) Captain eyes-on on real music. **Gotchas:** int64 multiply cost on Xtensa is non-trivial in the hottest loop — verify AP cadence didn't regress (reuse the stage-profiler env); keep the `#else` int32 path intact as revertible; this interacts with M2.5 (ACF budget) so measure cadence *after* both.

**M0.1+M0.3 — CI + synthetic golden fixtures (unlocks trustworthy "green").**
Approach: minimal Actions workflow on `ubuntu-latest`: install Python+pytest+`platformio`+`clang++`, run `pytest tests/ -k "not device"`, then `pio run -e k1_hardware`. Separately, generate deterministic WAVs in Python (sine/click trains at fixed BPMs, fixed seed) committed under `tests/fixtures/synth/`, and add a replay case asserting onset/beat counts within tolerance — closing the "metrics need `~/Downloads`" gap. **Gotchas:** the real-`.cpp` replay tests need `clang++` on the runner (install it, don't let them silently skip — a skipped test is not a passed test); pin the PlatformIO platform in CI to the same pioarduino release; keep proprietary audio out of git (synthetic only).

**M2.1 — `serial_menu.h` decomposition (highest structural leverage).**
Approach: the `serial_cmd_table.def` X-macro (`:3276`) is the seam — finish moving the 131 `strcmp` arms into table entries, then move the bodies into a new `serial_menu.cpp` (add to `build_src_filter`), leaving a thin header. Route every numeric setter through *one* validated `apply_config_value(field, raw, min, max)` so bounds-checking is structural, not per-arm. **Gotchas:** this is the ODR-landmine file — do it behind a flag and prove a second TU can include the header before flipping; preserve exact command spelling/precedence (the static tests + device muscle-memory depend on it); land in small table-by-section commits, each host-green, so the gate (now installed via M0.2) catches regressions; do M0.3 first so you have behavioral coverage of the parser before you move it.

---

## 7. Open Questions (need a human/product decision)

1. **GDFT promotion scope:** confirm M1.1 ships magnitude+recurrence overflow fixes **without** true-center (which failed eyes-on at HEAD) — i.e. is "fix the overflow, defer true-center" the intended split?
2. **Effect-framework fork (M2.3):** finish the `effects/framework/*` migration, or excise it and standardize on parameterized legacy effects? This is a strategic fork with materially different downstream cost.
3. **Wireless launch posture (M1.4):** will the K1 ship with wireless enabled for backers? If yes, the open-AP + shared-token model must change first; if no/later, M1.4 is deferrable.
4. **License of record:** is K1 firmware MIT or GPL-3.0? The `LICENSE` file and `CLAUDE.md` disagree, and the answer changes distribution obligations.
5. **`<50 ms` latency claim:** is this a measured product promise (needs a MabuTrace audio-to-LED capture) or should the customer-facing copy be softened until measured?
6. **Forensic-doc retention:** archive the 201 `docs/forensics/` docs to a separate history store, or keep in-tree? Affects clone size and "find current truth" navigability.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-23 | agent:claude-code (orchestrated audit) | Created: full 4-phase repo audit (map, evidence-based findings, strategy, milestone task plan). All Critical/High claims orchestrator-verified against source. |
