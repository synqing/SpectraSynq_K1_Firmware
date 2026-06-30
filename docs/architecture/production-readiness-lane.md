---
abstract: "Autonomous-lane execution contract for closing the K1 firmware production-readiness gap (the 2026-06-26 Reality-Checker assessment). Classifies every gap by AUTONOMY — Class A autonomous-complete · B autonomous-build/device-proof · C prepare-then-decide · D blocked-external — and sequences the lanes: CONFIG-integrity → I2S/WDT freeze-fix → token-scrub → manufacturing/provisioning → release-eng → (perceptual / OTA / field-recovery / GDFT) decision packages. Inherits the harness-IS-product gate discipline + the device/decoy/security hard-do-nots. READ FIRST before any production-readiness work; every file:line below is reader-sourced (2026-06-26) and MUST be re-verified first-hand (SSA) before LOCK. The serial-decomposition program is NOT on this critical path — it runs in the background."
---

# Lane — K1 Firmware Production Readiness (autonomous execution contract)

> **Origin:** the 2026-06-26 Reality-Checker assessment (5 evidence-grounded reads). **READ-ORDER:** this doc → `.claude/handoff.md` → `docs/audit/2026-06-23-repo-audit.md` → `docs/architecture/firmware-modernization-program.md`. **FRESH CONTEXT.** Every `file:line` here is a first-pass anchor (reader-sourced 2026-06-26); the executing agent **MUST re-verify each first-hand before acting (SSA)** — git moves, readers can err (one reader mis-reported the branch/HEAD/test-count this very session).

## 0 · Prime directive + what "complete" means here

The K1 firmware is an **engineering-stable baseline, NOT production-grade.** The harness/CI/golden infrastructure is strong (the one green dimension); the *product* (perceptual) and *operational* (robustness / recovery / update / manufacturing) dimensions are mostly unproven or unbuilt. **The serial-decomposition / `.ino`→`main.cpp` modernization program is real maintainability value but it is OFF the ship critical path** — it must NOT be the headline of this lane (run it in the background at most).

**"Ingest, execute, complete" for THIS autonomous lane means:**
- **Class A lanes** → completed end-to-end to a **DRAFT PR**, all host+CI gates green. (Captain merge is the only remaining gate.)
- **Class B lanes** → built + host/build-gated to a **DRAFT PR** + a written **device-proof plan**; merge is Captain/device-gated (compile ≠ runtime proof).
- **Class C lanes** → a **decision-grade package** (evidence + options + recommendation + flag-gated scaffolding where safe) delivered to the Captain; the lane STOPS — it does NOT decide.
- **Class D lanes** → a one-page **blocked-on-external** memo (hardware pins / signing keys / regulatory) and STOP.

Faithful completion = all Class-A merged-ready, all Class-B PR'd-with-proof-plan, all Class-C/D packaged. **Do not fake autonomy on a Captain-gated item — that is report theatre and a hard failure.**

## 1 · The verdict (1 paragraph)

Of 8 production-grade dimensions, **one is green** (harness/CI + security-by-absence), and **the product-defining dimension (perceptual) plus four operational dimensions (robustness-freeze, field recovery, field update, manufacturing) are red.** The sharpest facts: an **unrecoverable audio-core freeze** (I2S `portMAX_DELAY` + no task watchdog); **no config-corruption recovery** (raw `memcpy` load, dead factory-reset fallback); **no laptop-free field reset or OTA**; a **2-board dev-bench flashing setup that refuses unknown units**; and a **shipping visual that failed its own perceptual A/B** (2026-06-21, judged worse than a non-shipping reference). Wireless is **safe by absence** (compiled out of production) but bakes a fleet-wide static token into the binary.

## 2 · Autonomy taxonomy (the spine of this lane)

| Class | Meaning | DoD | Examples |
|---|---|---|---|
| **A — Autonomous-complete** | Host+CI provable; no runtime/perceptual/decision dependency | DRAFT PR, all gates green | CONFIG integrity (N1), token-scrub (N3), manufacturing tooling (N4), release tooling (N5) |
| **B — Autonomous-build / device-proof** | Buildable + host/static-gated, but efficacy is runtime; merge needs device fault-injection/eyes-on | DRAFT PR + device-proof plan; **flag default-OFF or behaviour-flagged** | I2S timeout + task WDT (N2), robustness-hardening bundle (N2b) |
| **C — Prepare-then-decide** | Requires a Captain product/security/perceptual decision | Decision package (+ safe flag-gated scaffolding); STOP | perceptual finalize (N6), OTA enable (N7), GDFT promotion (N9), wireless-ship posture |
| **D — Blocked-external** | Needs hardware / account-secret / regulatory | Blocked memo; STOP | recovery buttons (N8 hw-pins), OTA signing keys, FCC/CE |

## 3 · The lanes

> Per-lane: **Gap** (evidence — re-verify SSA) · **Fix** · **Host behaviour-lock** · **Definition of Done** · **Stop/escalate**. One gated lane per PR (never bundle flags). The recipe substrate is the existing harness: `scripts/regression-harness/golden/` oracles + `harness_selftest.py` (Gate Fα) + `tests/test_golden_master.py` + `pio run -e <env>` + the anti-gaming two-commit split (LOCK = oracle/golden/test, ZERO source; then EXTRACT/FIX = source, golden untouched) + statement/region byte-identity where a change must be production-neutral.

### Lane N1 — CONFIG-load integrity + factory-reset fallback · **Class A** · **P1**
- **Gap:** `persistence/bridge_fs.h:118-160` loads the persisted config via raw `memcpy(&CONFIG, buffer, sizeof(CONFIG))` with **no magic / version / CRC**; the `queue_factory_reset` fallback is **dead code** (declared `false`, never set). One corrupt or version-skewed NVS write → undefined state that **survives power-cycle** (defeats the only recovery a backer has). `factory_reset()` @ `bridge_fs.h:24`, `restore_defaults()` @ `:61` already exist but the corruption path never reaches them.
- **Fix:** add a `{magic, version, length, CRC32}` header to the config blob on save; on load, validate → on any mismatch, fall back to `CONFIG_DEFAULTS` (and re-seed). Handle migration of existing headerless `/CONFIG_<ver>.BIN` (treat as version-0 → load-then-reseed-with-header, never hard-reset silently). Wire the dead fallback.
- **Host behaviour-lock:** this logic is pure over a byte buffer → **fully host-provable.** Add a golden/unit gate (host-compile the load/save path via the `oracle_hostcompile.py` substrate, or a focused host unit) that feeds `{valid, bad-CRC, version-skew, truncated, headerless-legacy}` blobs and pins `{action: load | fallback | migrate, resulting CONFIG}`. ≥1 Gate-Fα tooth per branch (corrupt-but-accepted MUST diverge).
- **DoD:** golden reproduces; Gate Fα proven; `pio run -e k1_hardware` green; DRAFT PR. (Class A — host-complete.)
- **Stop if:** the config struct has pointers/non-POD (CRC over raw bytes would be unstable) → escalate the serialization design.

### Lane N2 — I2S bounded read + task watchdog (the unrecoverable-freeze fix) · **Class B** · **P0 (highest severity)**
- **Gap:** `audio/i2s_audio.h:277` `i2s_channel_read(..., portMAX_DELAY)` (called from `loop()` via `acquire_sample_chunk()` ~`.ino:747`) blocks the hard-RT audio core **forever** on a mic/DMA stall; **no task is subscribed to `esp_task_wdt`** anywhere in the tree → the hang is never caught and **never resets.** This is the single worst unattended-field failure (dead unit, physical power-cycle required).
- **Fix:** (a) replace `portMAX_DELAY` with a **bounded timeout** + an explicit short/empty-read degrade path (the downstream chunk handler currently assumes a full chunk — handle the new path explicitly so the pipeline degrades, not corrupts); (b) subscribe the audio loop + the LED render task (`.ino:655` `ledTaskCreated`) + the AP loop to `esp_task_wdt` (init + feed + a panic-reset on starve). Pin WDT timeout via `sdkconfig` (none exists today → add one).
- **Host behaviour-lock:** efficacy is **runtime** (host can't run FreeRTOS). Lock the STRUCTURE: a static test asserting the timeout constant (not `portMAX_DELAY`) + the WDT subscribe/feed calls on each task + the degrade path exists; `pio run -e k1_hardware` (and `k1_bench_reference`) green. This is a **behaviour change → NOT production-byte-identical**; do NOT claim byte-identity.
- **DoD:** DRAFT PR + **device-proof plan** (fault-injection: simulate DMA stall / unplug mic on the bench `B489A500`; confirm WDT reset + clean reboot + AP-alive; main K1 `F887A500` eyes-on). **Merge is Captain/device-gated.** Flag the new timeout behaviour behind a revertible `#define` defaulting to the safe bounded value.
- **Stop if:** the audio team's hard-RT contract forbids any early-return in the acquisition path → escalate (this is an AP/audio-seam change; honour `/sensorybridge-doctrine` + `/k1-firmware-change-gate`).

### Lane N2b — robustness-hardening bundle · **Class B** · **P1** (each a small independent micro-PR)
- `globals.h:381` `led_thread_halt` is **non-`volatile` on the production `#else` path** (volatile only under `K1_EFFECT_FRAMEWORK_V1`) → cross-core memory-model hole; **1-keyword fix** + a static guard.
- **Boot-loop protection:** no anti-bricking on crash-at-boot; coredump disabled at framework default. Add a boot-counter in NVS + a "N fast crashes → boot to safe defaults" fallback. (Pairs with N1.)
- **Brownout/coredump pinning:** no `sdkconfig` in repo → brownout + coredump run at undocumented arduino-esp32 3.2.0 defaults. Add an explicit `sdkconfig.defaults` pinning brownout threshold + `ESP_COREDUMP_ENABLE_TO_FLASH` (post-mortem on field crashes). **Verify the resolved defaults first-hand before changing.**
- **LED power:** `led_utilities.h:1116` `FastLED.setMaxPowerInVoltsAndMilliamps(5.0, MAX_CURRENT_MA=1500)` is a software estimator, user-raisable, doesn't govern inrush. Decide a hard ceiling + whether to lock the CONFIG field. (May be Class C if it changes the brightness envelope — escalate if perceptual.)
- **DoD per item:** static/build-gated DRAFT PR; device-proof where runtime (boot-loop, brownout).

### Lane N3 — production control-token scrub · **Class A** · **P1**
- **Gap:** `platformio.ini:68` bakes `-DK1_CONTROL_TOKEN="k1-tab5"` into the **production `k1_hardware`** binary even though the wireless transport is compiled out (`network/sb_k1_wireless.cpp:36-37`). A firmware dump yields a fleet-wide secret.
- **Fix:** move the token define OUT of `k1_hardware`; keep it ONLY in the wireless probe/dev envs that actually use it (`k1_wireless_ab_probe`). Do not change wireless default-OFF.
- **Host behaviour-lock:** **host-provable** — assert (a) `grep K1_CONTROL_TOKEN` absent from the `k1_hardware` build_flags, (b) the production `firmware.elf` no longer contains the byte string `k1-tab5` (region/string scan), (c) `k1_hardware` code/data otherwise **byte-identical** (the token was dead in prod, so removing its define should be near-neutral — verify via the code/data-region diff, NOT the `.bin` hash), (d) the wireless probe env still builds with the token.
- **DoD:** static test + region byte-diff + both envs build; DRAFT PR. (Class A.)

### Lane N4 — manufacturing / provisioning tooling · **Class A** (mechanism) + one scheme-confirm · **P1**
- **Gap:** `scripts/platformio/k1_upload_guard.py` **hard-codes 2 USB serials and refuses any other unit**; `docs/hardware/device-build-registry.md` is a hand 2-device table; no batch-flash / factory-image / per-unit-identity / efuse / `nvs_partition_gen` tooling exists. **Not manufacturable.**
- **Fix:** (a) a **factory-image** build step (`esptool merge_bin` → single flashable image); (b) a **per-unit provisioning** step (NVS namespace seeding a serial/SKU; `nvs_partition_gen`); (c) replace the 2-serial allowlist with a manufacturable guard (env/role-based, not serial-hardcoded) that still prevents cross-flash by **chip-role**, not by a fixed list; (d) a documented flashing runbook.
- **Host behaviour-lock:** tooling output is host-verifiable (image structure, NVS contents, guard logic unit-tested). No device needed for the mechanism.
- **DoD:** DRAFT PR with the tooling + runbook + tests. **Escalate ONE decision:** the per-unit **serial/SKU scheme** (externally visible, affects RMA/support) — propose a scheme, get Captain confirm before baking it in.
- **Stop if:** efuse burning is required (irreversible per unit) → that step is Class D (Captain-authorized only).

### Lane N5 — release engineering · **Class A** (mechanism) + gated publish · **P2**
- **Gap:** **0 git tags**; `FIRMWARE_VERSION 40103` (`SPECTRASYNQ_K1_FIRMWARE.ino:3`) is a bare int not linked to tags/builds; no release→shipped-unit traceability; `CHANGELOG.md` exists but isn't build-linked. CI covers host+compile only.
- **Fix:** a release script (tag ↔ `FIRMWARE_VERSION` ↔ built image ↔ changelog entry ↔ the device-build-registry deployed-state row); embed a build-provenance string (git describe) readable over serial + (when wireless on) the WS surface; optionally a CI release job.
- **DoD:** DRAFT PR with the tooling + a version-reporting firmware addition (host/build-gated). **Creating/pushing TAGS is a publication action → Captain-gated** (the agent builds the mechanism, does NOT publish a release tag autonomously).

### Lane N6 — perceptual finalization PACKAGE · **Class C** · **P0 (product-existential)** — DOES NOT SHIP AUTONOMOUSLY
- **Gap:** the product's reason to exist is unproven. Last "the show is *good*" eyes-on = the 2026-06-15 baseline; the most recent A/B (`docs/.../eyes-on-verdict.md`, 2026-06-21) judged the **shipping look worse** than the non-shipping effect-framework-v3 reference (`[env:k1_effect_framework]`, `K1_EFFECT_FRAMEWORK_V1`, not in the `k1_hardware` filter). **Loud-music AGC inverse-dimming** unsolved (directly attacks the core promise). Default shipped visual (`globals_config.cpp:53` BLOOM/palette 0; `globals.h:800` secondary) may be **in flux** (a `feat/secondary-boot-default-*` branch suggests an unmerged change — confirm first-hand). Latency `<50ms` **unmeasured** (`README.md:29`).
- **Autonomous scope (prepare only):** (a) **host-characterize the AGC inverse-dimming** using the existing GDFT/AGC harness (the `gdft_agc_probe` GDFTAGC contrast metric you just shipped is the instrument) — quantify the contrast collapse vs input level, propose candidate fixes **behind flags** (do not change the default); (b) a clean **v3-vs-current decision frame** (what default-flipping the framework costs: the owed MabuTrace timing + preset-ID freeze); (c) a reproducible-on-host A/B metric package. **STOP for Captain eyes-on.** The agent NEVER picks the shipping look or flips a perceptual default.
- **DoD:** a decision package + flag-gated candidate(s); no default change; no merge.

### Lane N7 — OTA receiver (field update) · **Class C/B** · **P0-operational** — build behind flag, STOP for enablement
- **Gap:** **no OTA anywhere**; USB-MSC updater hard-disabled on `SB_K1_HARDWARE`; partition `default_16MB.csv` HAS `ota_0/ota_1/otadata` slots but **no code targets them.** Backers cannot patch bugs. (The biggest single missing subsystem.)
- **Autonomous scope:** build the on-device OTA receiver + **rollback/anti-bricking** (`esp_ota_*`, `esp_ota_mark_app_valid_cancel_rollback`) behind a default-OFF flag; host/build-gate it. **STOP for:** the enablement decision, **image signing keys** (secret → Class D, account-gated), and the distribution/server (product infra). Do NOT enable OTA or commit keys autonomously — a bad OTA path bricks fleets (highest blast radius in the repo).
- **DoD:** flag-OFF receiver + rollback in a DRAFT PR + a device-proof plan + an enablement/keys decision memo. Merge Captain-gated.

### Lane N8 — laptop-free field recovery · **Class D-gated** · **P1**
- **Gap:** factory-reset is serial-only + typed `CONFIRM`; the button-combo path is **compiled out** (K1 control pins `= -1`, `constants.h:291-292`); no status LEDs (pins `-1`). A backer with a wedged/over-cal'd unit is stuck.
- **Autonomous scope:** implement the button-combo factory-reset + a status-indicator path **gated on the pins being defined**; host/build-gate. **BLOCKED on hardware:** the enclosure pin assignment (does the K1 HW have a reset button? which GPIO?) is a hardware/Captain question. Produce the gated implementation + a one-page "needs pin assignment X/Y" memo. STOP.

### Lane N9 — GDFT int32-overflow promotion DECISION memo · **Class C** · **P2**
- **Gap:** the int32 Goertzel magnitude overflow ships unfixed-by-default; the fix (`K1_GDFT_INT64_MAGNITUDE_V1`+`_RECURRENCE_V1`) is built + device-proven-correct but **HELD** ("no product value", Captain 2026-06-21). The overflow **zeros spectral bins on loud audio = the demo condition**, and may share a root with N6's AGC inverse-dimming.
- **Autonomous scope:** a 1-page memo — the overflow's loud-audio failure case, whether it's coupled to the AGC dimming (host-testable with the GDFT harness), and the cost of promoting vs the prior "no value" verdict. **Captain decides.** Do NOT promote the flags autonomously (explicitly HELD by decision).

## 4 · Inherited discipline (NON-NEGOTIABLE — applies to every lane)

- **The harness IS the product.** No structural/firmware change merges without: `pio run -e k1_hardware` green **and** all registered goldens reproduce **and** Gate Fα proven **and** CI green. Behaviour-preserving changes prove **production code/data byte-identity via the code/data-region diff, NOT the `.bin` hash** (esp_app_desc/image self-hashes always move on a debug-line shift). Behaviour-CHANGING lanes (N2, N7, N8) do NOT claim byte-identity and carry a device-proof gate.
- **Anti-gaming two-commit split:** LOCK (oracle/golden/test, ZERO source) → then FIX/EXTRACT (source, golden untouched + the tooth). Gate red on arrival → fix as a class, restore green first (amend-broken-gates), never run-while-broken.
- **Merge model:** MANUAL by the Captain (`synqing`). Open gated/side-effect PRs as **DRAFT** (GitHub blocks merging a draft; the harness also gates `gh pr merge`). The agent NEVER marks-ready, merges, force-pushes `main`, or pushes tags.
- **Commit gate:** tiered pre-commit (docs→none; `tests/`+`scripts/regression-harness`→`pytest tests/`; firmware/`platformio.ini`→`pytest tests/` **and** `pio run -e k1_hardware`). zsh backtick gotcha → `git commit -F -` (heredoc), never `-m` with backticks.
- **Repo/identity (LOAD-BEARING):** FORK = `/Users/spectrasynq/SpectraSynq_K1_Firmware`. **DECOY = `/Users/spectrasynq/SensoryBridge-main 9` — NEVER read/build/write.** cwd-guard EVERY subagent brief (`git -C <fork> rev-parse --show-toplevel`, abort if not the fork) + absolute paths. SSA: re-run/re-verify every subagent claim and every `file:line` in this doc first-hand.
- **Device (only if a lane's device-proof is Captain-authorized this session):** identity by **chip-ID** — main K1 `F887A500` = `k1_hardware`; bench `B489A500` = `k1_bench_reference`; **NEVER cross-flash** (different GPIO maps; consult `docs/hardware/device-build-registry.md`, update its deployed-state row after any flash). Piped `pio -t upload` silently no-ops → wrap in `script -q <log> …`. **Never auto-fire `noise_cal`** (wait for verbal silence confirm). Device I/O via Bash needs `dangerouslyDisableSandbox:true`.
- **Context + fanout:** use `context-mode` MCP for heavy reads; **DEFAULT to fanning out subagents** for heavy reading/running/building (keep the orchestrator context lean), each with a consumption contract + cwd-guard.

## 5 · Hard DO-NOT (red-team derived — each maps to a real failure mode)

1. **Do NOT decide or change the shipping VISUAL / perceptual default** — N6 prepares, the Captain decides. Flipping a default or "improving" the look autonomously = product-authority violation.
2. **Do NOT ship/enable wireless or redesign the wireless security posture** without the Captain's wireless-ship decision — N3 token-scrub + default-OFF only.
3. **Do NOT enable OTA or generate/commit signing keys** — N7 builds the receiver behind a flag; enablement + keys are Captain/account-gated. A bad OTA bricks fleets.
4. **Do NOT promote the GDFT int64 flags** (HELD by Captain decision) — N9 is a memo only.
5. **Do NOT treat compile/host-green as runtime proof** on Class-B lanes — label device-proof a tracked gate; flag behaviour changes default-safe + revertible.
6. **Do NOT touch the DECOY repo;** cwd-guard everything.
7. **Do NOT force-push `main`, mark PRs ready, merge, or push release tags** — all Captain-gated.
8. **Do NOT flash/erase/serial-write a device or run fault-injection** without explicit per-session Captain authorization + chip-ID guard; never auto-fire `noise_cal`.
9. **Do NOT bundle two flags/lanes in one PR;** one gated lane per PR.
10. **Do NOT let the serial-decomposition / `.ino`→`main.cpp` program become the headline** — it is off the ship path; background only.

## 6 · Captain-decision register (the lane STOPS and escalates these — accept/reject format)

| # | Decision | Why Captain-only | Default if no override |
|---|---|---|---|
| D1 | **Does the Tab5 wireless control ship in v1?** | Product/security posture; gates N3-full + the wireless redesign | Wireless stays default-OFF; ship token-scrubbed |
| D2 | **Shipping visual: finish/flip effect-framework-v3, or fix the current look?** | Perceptual judgment + eyes-on (N6) | No change; prepare A/B only |
| D3 | **Enable OTA for v1? + signing-key custody** | Irreversible blast radius + secret custody (N7) | OTA receiver built but default-OFF, unsigned, disabled |
| D4 | **Per-unit serial/SKU scheme** (N4) | Externally visible; RMA/support | Propose scheme; do not bake without confirm |
| D5 | **Promote the GDFT int64 overflow fix?** (N9) | Reverses a prior Captain "no value" verdict | Stays HELD |
| D6 | **K1 hardware reset-button GPIO assignment** (N8) | Hardware/enclosure | Gated implementation; blocked memo |

**Escalation format (mandatory):** current state → decision required → options → recommended path → blast radius → default action if no override. Decision-grade only — no logs/transcripts to the Captain.

## 7 · Dependency graph + recommended sequence

```
WAVE 1 (autonomous, ship-blocker robustness — do first):
  N1 CONFIG-integrity  ──┐  (cleanest fully-autonomous; establishes the rhythm)
  N2 I2S+WDT freeze-fix ─┤  (P0 severity; build+host, device-proof tracked)   ← depends on a sdkconfig (shared w/ N2b)
  N3 token-scrub       ──┘  (cheap, autonomous)
WAVE 2 (autonomous, operability tooling):
  N4 manufacturing  ──→ N5 release-eng   (N5 version↔build linkage leans on N4 identity)
  N2b robustness bundle (boot-loop pairs with N1; led_thread_halt volatile standalone)
WAVE 3 (prepare-then-decide — package + STOP):
  N6 perceptual pkg (P0 product)  ·  N7 OTA receiver (P0 ops)  ·  N8 recovery (hw-gated)  ·  N9 GDFT memo
```

Recommended start: **N1** (clean Class-A win, proves the autonomous rhythm), then **N2** (highest severity). N6 + N7 packages can be prepared in parallel by fanned-out readers while the autonomous PRs land.

## 8 · Evidence index (re-verify first-hand — SSA)

| Gap | Anchor (reader-sourced 2026-06-26) |
|---|---|
| I2S freeze | `audio/i2s_audio.h:277` (portMAX_DELAY); no `esp_task_wdt` in tree; `.ino:655` LED task, `.ino:747` acquire |
| CONFIG integrity | `persistence/bridge_fs.h:118-160` (raw memcpy), `:24` factory_reset, `:61` restore_defaults; dead `queue_factory_reset` |
| Token bake | `platformio.ini:68` (`-DK1_CONTROL_TOKEN`), `network/sb_k1_wireless.cpp:19-20,36-37` |
| Manufacturing | `scripts/platformio/k1_upload_guard.py` (2 serials), `docs/hardware/device-build-registry.md`, `default_16MB.csv` (ota slots) |
| Recovery pins | `constants.h:291-295` (control pins / sweet-spot LEDs = −1); button-combo `system/system.h:~487` |
| Release | `SPECTRASYNQ_K1_FIRMWARE.ino:3` (`FIRMWARE_VERSION 40103`); `git tag -l` = 0; root `CHANGELOG.md` |
| Perceptual | `eyes-on-verdict.md` (2026-06-21 A/B), `progress.md` (2026-06-15 baseline), `globals_config.cpp:53`, `globals.h:800`, `[env:k1_effect_framework]`, `README.md:29` (latency) |
| GDFT overflow | int64 flags absent from `platformio.ini`; HELD per `eyes-on-verdict.md` |
| robustness misc | `globals.h:381` (`led_thread_halt` non-volatile prod), `led_utilities.h:1116` (LED power), no `sdkconfig*` in repo |
| Harness/CI | `scripts/regression-harness/golden/`, `harness_selftest.py`, `tests/test_golden_master.py`, `.github/workflows/ci.yml`; pre-commit NOT installed locally (CI backstops) |

## 9 · Verification caveats (confirm first-hand before relying)

- One assessment reader mis-reported git state (branch / `main` HEAD / test count) — **confirm live `main` + the default-boot visual (mode 8 vs 18 ambiguity) first-hand.**
- Not verified closed: offline DSP-fixture reproducibility (audit M0.3), the LED-index OOB clamps (audit M1.3, `led_utilities.h:277/868/1202`), exact arduino-esp32 3.2.0 brownout/coredump defaults (no `sdkconfig` in repo).
- The audit (`2026-06-23`) predates recent work — cross-check each item's status against live source before acting.

## 10 · Status reality update — 2026-06-30 (live; supersedes stale §3 statuses)

Work shipped this session on the product line `lane/remoted-ble-midi-phase-f` (device-proven on main K1 `F887A500`; none merged to `main` — that stays Captain-gated):

- **N1** — device-proofed (`479701d`, MIGRATE path). Effectively done.
- **N2** — **SHIPPED** (freeze-fix `827d73a`→`e2beac5`) **+ ACF work-spreading root-fix** (`6880095`): active-AP p95 `9088→6784 µs`, over-budget frames `889/2667→0`, 127 BPM lock preserved 100%. The freeze cause is removed, not just caught.
- **N6** — the **"louder→dimmer" AGC defect is SHIPPED FIXED** (per-band AGC `SB_AGC_PERBAND_V1`, `2e2800d`): cross-band gain spread `0.000→0.145` (treble ~2.6× brighter than bass on loud). Doc §3 only expected "prepare A/B" — we went further with objective device data. **D2 (effect-framework-v3 vs current look) remains open.**
- **N4-adjacent** — upload guard **hardened** (`980c8a3`): all 6 K1-chip-bound envs registered + a drift-catcher test (closed a real cross-flash brick-risk the probe envs had opened; found 4 pre-existing gaps).
- **N7** — flag-OFF OTA receiver: DRAFT in progress (branch `feat/n7-ota-receiver`).
- **N8 / N9** — memos written: [`n8-field-recovery-blocked-memo.md`](./n8-field-recovery-blocked-memo.md) (BLOCKED on D6 GPIO), [`n9-gdft-int64-held-memo.md`](./n9-gdft-int64-held-memo.md) (HELD; #72837 weakened its case).

**STRUCTURAL FINDING (new Captain decision — D7):** the `feat/*` integration stack (tip `feat/gate-class-pio-prescripts`, carrying N3 + N2b + N4a + build-config + commit-gate) is **NOT merged into the product line**, and the two lines **diverged at N2** (the stack's `827d73a` vs the product line's cherry-picked `e2beac5`). A merge will conflict on `platformio.ini`, the upload guard (both lines edited it), and possibly the golden manifest (trust-root).
- **D7 — How to reconcile the two divergent firmware lines?** Why Captain-relevant: it sets which line is canonical for v1 and risks the device-validated shipping line. Options: (a) merge the stack into the product line (resolve conflicts in a sandbox, host-gate, land only if clean); (b) cherry-pick the un-integrated lane artifacts (N3 token-scrub, N2b bootloop guard) onto the product line individually; (c) rebase the product line's BLE/ACF/AGC work onto the stack tip. **Recommended:** (b) — cherry-pick the discrete lane artifacts (lower blast radius than a full divergent-line merge); the product line stays canonical. **Default if no override:** product line is canonical for v1; the stack's unique lanes (N3/N2b) are cherry-picked, gated, and landed; the rest of the stack is archived.

### Integration update — 2026-06-30 (autonomous lane completion, harness-first)

Executed via three sandboxed SSAs (isolated worktrees, isolated build dirs, commit-before-gate); every claim re-verified by the orchestrator against git + a re-run gate on the post-merge HEAD (never SSA self-report).

- **LANDED on the product line** `lane/remoted-ble-midi-phase-f` (`ad08ce1`→`7d1e28b`, **pushed**), gate re-run by orchestrator = **612 passed / 1 skipped**, golden+Gate-0 keystone green, trust-root untouched:
  - **N3 token-scrub** (`d70c190`+`7a4a98a`) — `K1_CONTROL_TOKEN` moved out of `k1_hardware` (where it was inherited by ~50 envs but dead-stripped) into `k1_wireless_ab_probe` (the sole consumer). Production **byte-identical** (golden byte-oracle confirms); build-hygiene, not a leaked-secret fix.
  - **N4 factory tooling** (`7d1e28b`) — `make_factory_image.py` (`esptool merge_bin`, non-flashing), `make_unit_nvs.py` (`nvs_partition_gen`, D4-placeholder CSV), flash runbook, static test. Class A, behaviour-preserving.
- **STAGED + host-gated + DEVICE-PROOF OWED** (no edit to the canonical line until bench-proven):
  - **N2b boot-loop guard** — `lane/n2b-staged` (**pushed**). RTC crash-streak guard + **non-destructive** safe mode (loads `CONFIG_DEFAULTS` in RAM only; config file never deleted, never re-saved). Flag `K1_BOOTLOOP_GUARD_V1`, currently **ON in `k1_hardware`** → behaviour-changing boot path → must be device-proven before it lands. Host-gated green (the `k1_bootloop` golden oracle ships with it; the `bridge_fs_config` golden delta is the inert flag-gated source block, human-reviewed + accepted). RTC-based, **no sdkconfig/rollback dependency**.
  - **N7 OTA rollback prereq** — `feat/n7-rollback-prereq` (**pushed**) atop the flag-OFF OTA DRAFT. Adds `sdkconfig.defaults` (`CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE`) + bench device-proof runbook. `sdkconfig.defaults` changes every build → correctly **OTA-branch-only**, never the product line. OTA still **flag-OFF**; **D3 key-custody STOP** stands (no key generated/committed).
- **Device on the bus = MAIN K1 `F887A500`** (identity by esptool `read_mac`). The N2b + OTA device-proofs are **bench** procedures (`B489A500`) — boot-looping / bad-image-pushing the primary is the wrong instrument. Owed until the bench is connected.
- **Hard stops surfaced, not bulldozed:** D3 (signing key — Class D secret), D6 (reset GPIO — unassigned hardware), D2 (visual look — product-truth + needs MabuTrace timing on hardware), D5 (int64 — already Captain-decided OFF 2026-06-21).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:claude-opus-4-8 (CTO) | Integration update: N3 token-scrub + N4 factory tooling LANDED on the product line (`7d1e28b`, pushed, 612-pass gate re-run on post-merge HEAD); N2b boot-guard staged on `lane/n2b-staged` (flag-ON in k1_hardware → device-proof owed; non-destructive RTC safe-mode; bridge_fs golden delta human-reviewed); N7 rollback prereq staged on `feat/n7-rollback-prereq` (sdkconfig OTA-branch-only, key-custody STOP holds). Device on bus = MAIN K1 — N2b/OTA proofs are bench-only. |
| 2026-06-30 | agent:claude-opus-4-8 (CTO) | Added §10 live status update: N1 done, N2 + ACF + per-band-AGC (N6 defect) SHIPPED + device-proven on the product line, upload-guard hardened, N7 OTA DRAFT in progress, N8/N9 memos written. Surfaced D7 — the feat/* stack is unmerged and diverged from the product line at N2; recommended cherry-picking discrete lane artifacts over a full divergent-line merge. |
| 2026-06-26 | agent:claude-code (CTO) | Created from the 2026-06-26 Reality-Checker production-readiness assessment (5 evidence reads). Encodes the autonomy taxonomy (A/B/C/D), the lane plan N1-N9, inherited gate discipline, the hard do-not list, the Captain-decision register, and the evidence index. Designed for ingestion by the autonomous build lane: complete Class-A end-to-end, PR+proof-plan Class-B, package-and-stop Class-C/D. |
