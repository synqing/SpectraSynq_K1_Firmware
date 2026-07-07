---
abstract: "Codex end-to-end resume brief (2026-07-06, superseded notes through 2026-07-07) for the IM73D productionization lane. Phase-1 productionization firmware shipped (k1_prod_im73d main/prod build path — byte-identical-OFF, upload-guard mapped to main K1). R1 knob persistence is closed. R4 DSR_16S controlled-audio eval is closed and rejected; keep DSR_8S. The original main-K1 physical-swap blocker is superseded: bench K1 carries IM73D on the ratified mic pin map and Captain confirms both K1s are identical hardware. Existing envs encode the intended LED map: k1_bench_im73d = 4/5, k1_prod_im73d = 6/7. What remains is selected-env device proof, Captain eyes-on, and final default-env flip. This brief carries read-order, device-identity table (MAC-only), done-ledger, task queue, byte-identity discipline, and hard rules."
---

# IM73D productionization — Codex end-to-end resume brief (2026-07-06)

**You are Codex, resuming the SpectraSynq K1 firmware.** Everything that can be done autonomously in firmware is DONE and gated. What is left is mostly **hardware/perceptual checkpoints that only Captain can clear** plus **one owed autonomous device capture**. Your job: execute the remaining ordered queue, escalate the hardware checkpoints as decision-grade asks (do not perform them yourself — they need Captain's hands / eyes / verbal silence-go), and do NOT re-litigate anything in the "closed — do not reopen" list.

> **2026-07-07 supersession:** R1 is closed. R4 controlled-audio DSR testing has
> now been performed on the bench IM73D using radio-free firmware and speaker
> playback. **DSR_16S is rejected; keep `DSR_8S`.** Bench uploaded back to
> `k1_bench_im73d @ 9d14463` after the test and is now runtime-proven by
> 2026-07-07 read-only `:build`/`:dump` recovery (`CAL_SOURCE: persisted_profile`,
> `CAL_VALID: 1`, `CONFIG.CHROMA: 0.100000`). Authority:
> `docs/hardware/im73d-dsr16-controlled-audio-evidence-2026-07-06.md` and
> `artifacts/im73d_recovery_2026-07-07/readonly_build_dump_20260707.json`.
>
> **2026-07-07 R2/R3 correction:** the original main-K1 physical-swap blocker is
> superseded. The bench K1 already carries IM73D on the ratified PDM pin map
> (`clk13/din12/LR14`), and Captain confirms both K1s are identical hardware.
> Existing envs encode LED-map choice: `k1_bench_im73d` = GPIO `4/5`,
> `k1_prod_im73d` = GPIO `6/7`. A 2026-07-07 bench flash of `k1_prod_im73d`
> made both LED channels dark because that was the wrong env for the restored
> bench configuration, not because the hardware differs.

---

## 0 · Read order (Codex-native)

1. `AGENT_OS.md` — canonical agent manual (session bootstrap, source-of-truth hierarchy, safety gates).
2. **This file** — the resume work order.
3. `docs/hardware/im73d122-productionization-handover-2026-07-03.md` — the productionization lane authority. **§10 = audit + Captain D1/D2 decision; §11 = the autonomous-execution outcomes (UA shipped, MicFrontend decision, byte-oracle finding, DSR recipe, flip red-team).** This is your deep context.
4. `docs/hardware/im73d-productionization-execution-plan-2026-07-06.md` — the gated DAG + unit status table.
5. `docs/hardware/device-build-registry.md` — the deployed-state table (**canonical device↔env↔build truth; update AFTER every device-proof, never after mere upload**).
6. `docs/spec-index.md` — lane authority. `progress.md` — rolling status (top entry = 2026-07-06).
7. Memories: `im73d-production-decision`, `k1-byte-identity-oracle`, `cal-silence-gate-never-waived`, `k1-serial-colon-command-surface`, `k1-im73d-ble-demo-build`, `im73d-pdm-snr-modes`.

**Verify live before trusting any prose:** `git rev-parse --abbrev-ref HEAD` (= `lane/im73d-pdm-eval`), `git log --oneline -8`, and match devices by **MAC**, never port.

---

## 1 · Live state at handover

- **Branch / HEAD:** `lane/im73d-pdm-eval @ 855c4a2`. Tree clean.
- **Both lanes consolidated:** `lane/palette-vibrancy-v1` is merged in (`55c536b`); vibrancy shipped + eyes-on PASSED on the main K1.
- **Host gate GREEN:** pytest **629 passed / 1 skipped**; `k1_hardware` + `k1_prod_im73d` build clean. Later corrective guard tests restored `k1_prod_im73d` as the main/prod IM73D env, guard-mapped to the main K1 MAC, after the bench wrong-env LED-dark incident.
- **The pre-commit hook is authoritative** (firmware tier = pytest + `pio run -e k1_hardware`); it runs on every commit. Docs-only commits skip the build.

### Device identity — MAC ONLY (ports scramble daily; at handover: main=`usbmodem1101`, bench=`usbmodem101`)

| Unit | Chip | USB serial (MAC) | Runs (proven) | Never do |
|---|---|---|---|---|
| **Main K1** (production) | `F887A500` | `B4:3A:45:A5:87:F8` | `k1_hardware @ ae5d90a` (SPH0645; vibrancy, eyes-on PASSED) | `k1_prod_im73d` is the main/prod IM73D env; flash only if Captain wants this unit configured for IM73D |
| **Bench K1** | `B489A500` | `B4:3A:45:A5:89:B4` | `k1_bench_im73d_ble @ 79d7fda` (BLE demo; IM73D on GPIO 13/12/14; `cal_source=persisted_profile`) | Do NOT measure mic SNR on a BLE build |

`pio device list` → match `SER=` before ANY open/flash. The upload guard is the last line of defence, not the first.

---

## 2 · Done-ledger (do NOT redo — all committed on `lane/im73d-pdm-eval`)

| Commit | What | Proof |
|---|---|---|
| `55c536b` | Merge `lane/palette-vibrancy-v1` → consolidation | pytest 629, byte-identical (3 stable sections) |
| `32bc384` | Vibrancy forensic doc (`docs/forensics/2026-07-02-palette-vibrancy-colour-collapse.md`) | numbers preserved |
| `741a40f`,`a82c1d9` | Productionization §10 audit + Captain D1/D2 decision | code-verified |
| `5628df5` | Execution plan (harness-first DAG U0–UF) | — |
| **`4b95e60`** | **UA — `k1_prod_im73d` production build path** | pytest 629; byte-identical-OFF; guard-mapped to main K1 |
| **`d1ecc10`** | **UC — `mic_stable_byte_gate.sh`** (trustworthy 3-section oracle + references + static test) | non-flaky check confirmed |
| `6bfc702` | §11 outcomes: MicFrontend decision, DSR recipe, flip red-team | — |
| `58928a1` | `progress.md` session entry | — |
| `855c4a2` | Test-precision fix (production-pin test now mutation-proven) | adversarial-review finding |

**Key state you inherit:**
- `[env:k1_prod_im73d]` = main/prod LED GPIO map (`6/7`) + `-DK1_MIC_IM73D_PDM_V1` at mic pins **clk13/din12/LR14**. It is guard-mapped to the main K1 MAC. The bench IM73D counterpart remains `[env:k1_bench_im73d]` (`4/5`).
- Byte-identity oracle = `scripts/regression-harness/mic_stable_byte_gate.sh` (hashes only the 3 reproducible sections `.dram0.data`/`.iram0.text`/`.iram0.vectors`). The old `registry_byte_gate.sh` (5 sections) is **flaky** — see memory `k1-byte-identity-oracle`.

---

## 3 · CLOSED — do NOT reopen

- **Mic selection.** IM73D122 IS the K1 production mic (Captain-ratified 2026-07-03).
- **Production pin map.** Identical bench-proven `clk13/din12/LR14` (Captain D1, 2026-07-06). No PCB rev pending.
- **MicFrontend runtime abstraction.** REJECTED with evidence (un-byte-verifiable in a non-reproducible build + Core-0 cost + doctrine). Compile-time selection retained; the 6-interface seam map is in handover §11.2. Do not build runtime mic dispatch.
- **Gain `g=16` / DSR_8S.** Stay. `g=16` silence-cals near the top of the widened window; DSR_16S is a reserved +2 dB lever, not enabled (task R4).
- **Vibrancy.** Shipped + eyes-on PASSED; never re-point the palette engine at post-gate `chromagram_smooth`.

---

## 4 · REMAINING work — ordered end-to-end queue

Two tracks. **Track A** is autonomous (do it). **Track B** is Captain-gated hardware/perceptual (prepare + escalate decision-grade; do NOT perform yourself).

### R1 (Track A, autonomous, small) — knob-persistence device capture
**Why:** the un-freeze code (`e2b62b5`) ships on the bench (`79d7fda ⊇ e2b62b5`) but the isolated "set knob → `:reset` → survived" proof was never recorded (handover §11.7). Host + adjacent-proven; this closes the last Phase-1.1 device gap.
**Do NOT run it on the current BLE demo build** — `save_config_delayed`'s LittleFS write can defer under BLE heap pressure → a non-persist result would be inconclusive. Run on **radio-free `k1_bench_im73d`**.
**Procedure (bench `B489A500` only; identity by MAC; DTR/RTS LOW before pyserial open):**
1. Guard-verify + flash the bench to radio-free `k1_bench_im73d`:
   `pio run -e k1_bench_im73d -t upload --upload-port <verified B489A500 port>`
   (this replaces the BLE demo state — note it in the registry; the demo can be reflashed later).
2. Passive read `:build` → confirm `env=k1_bench_im73d`. Confirm `cal_source=persisted_profile` survived (regression check).
3. Set a knob via a **colon-prefixed** command, e.g. `:chroma=0.150` (echo-verify `PRIMARY pcm: chroma=0.150`). Wait ≥5 s (`save_config_delayed`).
4. `:reset` → after reboot, `:dump` (or `;`) → confirm `chroma=0.150` survived (the `/CONFIG_PDM_*.BIN` persisted).
5. Restore the knob (`:chroma=0.100`), update `device-build-registry.md` deployed-state row.
**No cal firing** — no Captain silence-go needed for this. If the bench is unreachable, document as still-owed and move on.

### R2 (SUPERSEDED 2026-07-07) — main-K1 SPH0645 → IM73D physical swap
This is no longer a mic/PDM proof blocker. Bench K1 carries IM73D on the
ratified `clk13/din12/LR14` PDM pin map, and Captain confirms both K1s are
identical hardware. Main-K1 conversion is optional product-unit work, not the
current proof blocker.

### R3 (corrected 2026-07-07) — device-prove the selected existing env
Do **not** invent new env names or a canonical-map proof. Use the existing env
that matches the configured unit:

1. `k1_bench_im73d` = IM73D PDM `13/12/14`, bench-reference LED GPIO `4/5`.
2. `k1_prod_im73d` = IM73D PDM `13/12/14`, main/prod LED GPIO `6/7`.

Correct proof path: Captain chooses the intended env for the unit, the upload
guard verifies the matching K1 MAC, then device proof + Captain eyes-on decide
whether it can progress toward a default flip.

Then run the **flip checklist** (handover §11.5): `dump_raw` int16 sane → gain
re-characterise on the sealed unit → **Captain silence-go recal only if
explicitly authorised** → `stream_agc` all 4 gains < 10 after 10 s → Captain
eyes-on. Byte-gate stays green for the flag-OFF SPH path throughout.

### R4 (CLOSED 2026-07-06) — DSR_16S +2 dB evaluation
Controlled speaker playback was made available and the DSR16 measurement was
run on radio-free `k1_bench_im73d` / `k1_bench_im73d_dsr16`, not on the BLE
build. Verdict: **reject DSR16 and keep `DSR_8S`**. DSR16 raised the quiet raw
RMS floor and reduced music raw-RMS-over-quiet response at volumes 45/60/75.
Do not add a DSR16 flag or default flip from the current evidence. Reopen only
if a later sealed-unit measurement shows repeatable signal/noise benefit without
raw rail risk. Authority:
`docs/hardware/im73d-dsr16-controlled-audio-evidence-2026-07-06.md`.

### R5 (Track B, final) — `k1_hardware` default-env flip
Only after R3 + R4 + eyes-on. Captain call. Strangler-fig: `k1_prod_im73d` is the dual-run env; the default flips last. Full 7-step checklist in handover §11.5.

### Phase 2/3 (later, Captain-sequenced)
Phase 2: BOM/supply diligence (IM73D122 / Infineon), per-unit factory-cal UX, SPH0645 autopsy on the main K1 (DC ≈ −5722). Phase 3: presence-hysteresis for quiet-music partial gating (acoustically intrinsic — NOT threshold surgery), PDM-domain sweep of other SSL consumers. Details in handover §5.

---

## 5 · Corrected R2/R3 gate

> **State:** IM73D productionization firmware is complete and gated; `k1_prod_im73d` builds clean and is guard-mapped to the main K1 MAC.
> **Corrected proof target:** bench K1 `B489A500` / USB MAC `B4:3A:45:A5:89:B4` proves the IM73D PDM mic path on pins `13/12/14`. Captain confirms both K1s are identical hardware.
> **Decision no longer required:** main-K1 SPH0645→IM73D swap is optional for mic proof.
> **Next mechanical step:** use the existing env that matches the intended unit configuration (`k1_bench_im73d` for `4/5`, `k1_prod_im73d` for `6/7`), then device-prove + eyes-on.

---

## 6 · Hard rules / gotchas (each cost a prior session — non-negotiable)

1. **Serial `:` prefix is LAW.** Bare bytes are live HOTKEYS (a bare-command spray once mutated live knobs). Typed commands need `:` (`serial_menu.h`). Read-only: `;` status, `:build`, `:dump`, `:vp_status`, `:stream_agc`. Only sanctioned bare keys: `N`,`Y` — and ONLY after Captain's verbal silence-go.
2. **`start_noise_cal` is NEVER auto-fired.** Captain-verbal silence-go only ("unrestricted use" does NOT waive it — that was a logged violation). Wait for "resume" before assuming normal acoustics.
3. **Identity = USB MAC, never port names.** Ports scramble daily (bench has been on 12201/1101/101; main on 1401/2101/1101). Every flash/erase/serial-write verifies MAC first. DTR/RTS held LOW before any pyserial `open()`; rapid open/close can wedge download mode → power-cycle recovers.
4. **"Bench K1 firmware" = `k1_bench_im73d_ble` ALWAYS** (Captain 2026-07-06). `k1_custom` = the 224-LED wall build, flashed ONLY on an explicit "custom" instruction. For **SNR/mic measurement** use radio-free `k1_bench_im73d` (never a BLE build — Core-0 radio perturbs audio).
5. **Byte-identity: use `mic_stable_byte_gate.sh`** (3 reproducible sections). `registry_byte_gate.sh` (5 sections) is flaky — `.flash.text`/`.flash.rodata` churn every build via `K1_BUILD_EPOCH`. A `registry_byte_gate` "mismatch" is NOT a regression by itself (memory `k1-byte-identity-oracle`).
6. **Concurrent sessions share this worktree.** `git status --short` before staging; never commit with foreign staged files; verify the commit stat matches your intent (a prior session was bitten twice by index races).
7. **British spelling, zero tolerance** (a PostToolUse hook hard-blocks American spellings in written files): behaviour, characterise, formalise, analyse, colour, centre. (Real US product/API names are exempt via the file marker.)
8. **AP/VP acceptance gates are ratio-based and blind to absolute amplitude** — a dead/garbage mic front-end can green every numeric test. Device `dump_raw` non-zero + eyes-on is mandatory, never optional, for any mic-path device proof.
9. **Registry discipline:** update `device-build-registry.md` AFTER device-proof (`:build` = env+git on the device), not after upload. Cursor's PlatformIO extension holds serial ports (Errno 16, no visible lsof holder) → have Captain close it. The `rtk`/`tee` wrapper truncates long output → redirect to a file + grep, trust exit codes + on-silicon `:build`.
10. **No K718 work** (Captain, 2026-07-06) until directed otherwise.

---

## 7 · Commands quick-reference

```bash
# host gate (what the pre-commit hook runs for firmware)
python3 -m pytest tests/ -q
pio run -e k1_hardware

# byte-identity (trustworthy oracle — 3 stable sections)
bash scripts/regression-harness/mic_stable_byte_gate.sh            # check all
bash scripts/regression-harness/mic_stable_byte_gate.sh k1_hardware # one env
bash scripts/regression-harness/mic_stable_byte_gate.sh --update   # re-record on intentional change

# main/prod IM73D build path (LED 6/7; guard-mapped to main K1)
pio run -e k1_prod_im73d

# upload guard CLI re-check (identity by MAC)
python3 scripts/platformio/k1_upload_guard.py --env <env> --upload-port <port>

# device identity (MAC in hwid; NEVER trust port name)
pio device list
```

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-06 | agent:claude-code (Fable) | Created: Codex end-to-end resume brief after autonomous Phase-1 IM73D productionization (UA/UC shipped, lanes consolidated). Carries device table, done-ledger, ordered remaining queue (R1–R5 + Phase 2/3), escalation template, and the hard-rule set. |
