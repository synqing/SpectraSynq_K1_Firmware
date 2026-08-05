# Strategic staging & commit plan — 2026-08-05

**Branch:** `lane/dual-sync-phase0` (ahead of origin by 6)  
**HEAD:** `5d5e9e4`  
**Lane authority:** `docs/hardware/im69d130-vs-main-k1-eval-2026-08-05.md`  
**Owner:** SpectraSynq CTO (Captain decision authority, 2026-08-05)

---

## CTO decisions (LOCKED)

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | **REJECT** staged `MAX_CURRENT_MA` 1500→2500 | Documented supply is 5V/2A. FastLED ceiling is a brightness *allowance*; raising it above the PSU invites brownout. Revisit only with updated PSU/docs. |
| D2 | **Ship Wave −1 + Wave 1 immediately** | Repo-truth FAIL blocks every agent session. Authority frontmatter + pointers + gitignore first. |
| D3 | **Wave 2 next (Mode 32)** | Orphan `.cpp` + static test without stash wiring is incomplete product. Restore Mode 32 paths surgically from `stash@{0}`; do not `stash pop`. |
| D4 | **Wave 3 after Wave 2** | IM69D env is the active lane's firmware substrate; keep separate from Mode 32 so a revert is clean. |
| D5 | **Wave 4 (STM FFT512) after Wave 3** | Dev-only, flag-gated; never on production `k1_hardware` default flags. |
| D6 | **HOLD Wave 5** (serial_menu delete / edgemixer rename) | −3k LOC mixed into stash; requires intentional review on its own commit/PR. |
| D7 | **Never commit** ble_midi / knob_build binaries / agent-local state | gitignore enforced. Archive outside this repo if retention needed. |
| D8 | **Do not bulk-commit** `.codex/skills/thinking-*` | Install script only if needed later; 30 skill dirs are noise on this lane. |
| D9 | **Defer** pixelblaze, K7180 media, OTA public PEM, dual-sync artefact dump | Dead or research-only; not on the critical path of the IM69D / Mode 32 lane. |
| D10 | **Keep `stash@{0}`** until Waves 2–4 pathwise extract; then drop residue | Wholesale pop would mix D6 HOLD into product waves. |

---

## Executive verdict

The dirty tree looks huge (~124 untracked roots, ~450MB artifacts) but **almost none of it should enter one commit**. Real product work is split across:

1. **Already staged:** 1-line `MAX_CURRENT_MA` 1500→2500  
2. **Parked in `stash@{0}`:** Mode 32 + IM69D env + STM FFT512 bench + serial/edgemixer churn (mixed; must be split)  
3. **Untracked companions:** effect `.cpp`, static tests, today’s hardware docs  
4. **Ignore / never-commit:** agent local state, build binaries, design-media dumps  
5. **Optional later:** text-only evidence packs, pixelblaze research, thinking-skill trees  

**Do not** `git add .` or restore the full stash into one commit.

---

## Current inventory (truth at plan time)

| Bucket | State | Size / count | Action |
|--------|--------|--------------|--------|
| Staged | `globals_config.cpp` only (`MAX_CURRENT_MA` 2500) | 1 hunk | Commit as **Wave 0** (or unstage if you want it with power docs) |
| `stash@{0}` | `temp: clear dirty tree for max_current_ma commit` | 27 paths, +614/−3290 | **Restore surgically by path**, never wholesale |
| Untracked firmware | `light_mode_waveform_hybrid_k1.cpp`, `k1_stm_fft512_bench.{h,cpp}` | ~26KB | Commit with matching wiring from stash |
| Untracked tests | `test_waveform_hybrid_k1_static.py`, `test_im69d_env_static.py` | 209 lines | With Mode 32 / IM69D waves |
| Untracked docs (today) | `docs/hardware/im69d130-*.md`, `m32-*.md`, `waveform-hybrid-*.md` | 10 files | Docs waves after code gates |
| Artifacts | esp. `ble_midi_71` 388MB, IM73D packs, K7180 DS | ~450MB+ | **Do not commit binaries**; ignore or archive |
| Agent local | `.claude-flow/`, `.ok/`, `.entire/`, `.claude/*.json`, `.devin/*local*` | small | **gitignore** |
| Skills trees | `.codex/skills/thinking-*`, design skills | many | Optional tool-overlay commit, or ignore |
| Public PEM | `k1_ota_signing_PUBLIC.pem` | 625B | Allowed by policy; separate deliberate commit |
| Root scratch | `findings.md`, `AGENTS.md.bak.*`, `.mcp.json.bak.*` | tiny | Delete or ignore |

**Critical orphan:** on-disk working tree has **zero** `WAVEFORM_HYBRID_K1` wiring in enum/dispatch. The untracked effect file + static test expect Mode 32. Wiring lives in **`stash@{0}`**. Committing the `.cpp` alone will not build / will fail the static gate.

---

## Hard exclusions (never stage)

```
.claude-flow/
.ok/
.entire/
.claude/proven-config.json
.claude/.proven-config-version
.claude/launch.json
.claude/settings.json          # local agent config
.devin/config.local.json       # already ignored
.devin/last-bootstrap.json
.devin/repo-truth-report.json
.devin/k1-session-target.json
.devin/delegations.json        # unless intentionally shared
*.bin *.elf *.map              # under artifacts/**/knob_build*
artifacts/ble_midi_71_20260628/   # 388MB build+capture dump
artifacts/K7180-Design-System/reference/**.{png,html}  # media-heavy
AGENTS.md.bak.*
.mcp.json.bak.*
findings.md                    # root scratch; dual-sync findings belong under artifacts/
```

**gitignore hygiene (recommended Wave −1, docs-only):**

```gitignore
.claude-flow/
.ok/
.entire/
evidence/
*.bak.*
.mcp.json.bak.*
# Optional if artifacts stay local forever:
# artifacts/ble_midi_71_20260628/
# artifacts/**/knob_build/
# artifacts/**/*.bin
```

---

## Pre-flight gates (before any firmware commit)

1. Fix **repo-truth** for active authority (frontmatter):
   - Add `status: active`
   - Add `branch: lane/dual-sync-phase0` (or the branch Captain names)
   - Update `progress.md` + `AGENT_OS.md` pointers to the authority path
2. Confirm `stash@{0}` still exists before popping anything.
3. Prefer **pathwise restore** over `git stash pop`:
   ```bash
   git checkout stash@{0} -- <paths...>
   ```
4. After each firmware wave: `pytest` + `bash scripts/agent/pio-build.sh k1_hardware` (and `k1_bench_im69d` when that env lands).
5. Do **not** flash / upload as part of commit waves.

---

## Recommended commit waves

### Wave −1 — Hygiene (docs/meta only, optional first)

**Intent:** stop agent/local noise from polluting `git status`.

| Stage | Notes |
|-------|--------|
| `.gitignore` updates | patterns above |
| (optional) delete root bak files | no commit needed if deleted |

**Message sketch:** `chore: ignore agent-local state and bak scratch`

---

### Wave 0 — Power ceiling (already staged)

**Stage (already):**
- `SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp` (`MAX_CURRENT_MA` 1500→2500)

**Do not mix with Mode 32 / IM69D.** Same hunk is also inside `stash@{0}` — after Wave 0, when restoring stash paths, **skip** re-applying `globals_config.cpp` or resolve to keep 2500 once.

**Gate:** docs-only adjacent? No — firmware default → pytest + `pio-build.sh k1_hardware`.

**Message sketch:**
```
fix(power): raise default MAX_CURRENT_MA to 2500 for 5V/~2.5A PSU headroom
```

**Captain decision needed:** is 2500 the intended global default for all envs, or bench-only? If unsure, **unstage** and park until decided.

---

### Wave 1 — Repo-truth / lane authority repair

**Stage:**
- `docs/hardware/im69d130-vs-main-k1-eval-2026-08-05.md` (frontmatter only)
- `progress.md` (active authority reference)
- `AGENT_OS.md` (active authority reference)
- companion untracked IM69D docs (optional same wave or Wave 1b):
  - `docs/hardware/im69d130-ap-telemetry-read-2026-08-05.md`
  - `docs/hardware/im69d130-board-wiring-from-eda-2026-08-05.md`
  - `docs/hardware/im69d130-dual-mic-eval-design-2026-08-05.md`
  - `docs/hardware/im69d130-env-implement-receipt-2026-08-05.md`
  - `docs/hardware/im69d130-gain-retune-2026-08-05.md`
  - `docs/hardware/im69d130-specialist-check-2026-08-05.md`

**Gate:** `bash scripts/agent/repo-truth.sh` → PASS (docs class; no pio required if docs-only).

**Message sketch:**
```
docs(lane): activate IM69D130 eval authority and attach supporting receipts
```

---

### Wave 2 — Mode 32 Waveform Hybrid K1 (product slice)

**Restore from stash (paths only):**
- `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h`
- `SPECTRASYNQ_K1_FIRMWARE/system/system.h`
- `SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h`
- `SPECTRASYNQ_K1_FIRMWARE/visual/channel_effect_state.h`
- `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectRegistry.cpp`
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` — **careful:** stash also contains edgemixer rename + STM bench hooks; prefer a **partial apply** or hand-port Mode 32 hunks only
- Boot-palette macros in `config_types.h` if Captain wants them with Mode 32 (or split Wave 2b)

**Add untracked:**
- `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid_k1.cpp`
- `tests/test_waveform_hybrid_k1_static.py`
- docs: `docs/hardware/m32-*.md`, `docs/hardware/waveform-hybrid-k1-all-builds-2026-08-05.md`

**Exclude from this wave:** `k1_edgemixer` rename, `serial_menu.cpp` deletion, IM69D env, STM FFT512, dual-sync artifact edits.

**Gate:** `pytest tests/test_waveform_hybrid_k1_static.py` + full pytest + `pio-build.sh k1_hardware`.

**Message sketch:**
```
feat(effects): add Mode 32 WAVEFORM_HYBRID_K1 on all builds

Tombstone IDs 30/31 keep ordinal 32 stable. Static gate requires common-path
dispatch (no mic-env ifdef).
```

**Risk:** `.ino` restore may pull unrelated edgemixer/STM diffs. Treat `.ino` as **manual hunk selection**.

---

### Wave 3 — IM69D bench env + mic path

**Restore from stash (expected cohort):**
- `platformio.ini` (`[env:k1_bench_im69d]` + flags)
- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h`
- `SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.cpp`
- `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.cpp`
- `SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h`
- `SPECTRASYNQ_K1_FIRMWARE/system/constants.h`
- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h`
- `scripts/agent/pio-build.sh`
- `scripts/platformio/k1_upload_guard.py`
- `tests/test_k1_upload_guard.py`

**Add untracked:**
- `tests/test_im69d_env_static.py`

**Gate:** `pytest tests/test_im69d_env_static.py tests/test_k1_upload_guard.py` + `pio-build.sh k1_bench_im69d` (and ensure `k1_hardware` still builds).

**Message sketch:**
```
feat(audio): add k1_bench_im69d env and IM69D PDM mic path

Isolated from IM73D flags; cal namespace /cal_profile_im69d.bin. Never cross-flash
im73d builds onto CLK=14/DATA=13 wiring.
```

---

### Wave 4 — STM FFT512 bench (dev-only)

**Restore / add:**
- `SPECTRASYNQ_K1_FIRMWARE/audio/k1_stm_fft512_bench.{h,cpp}` (untracked)
- matching `#ifdef K1_STM_FFT512_BENCH` hooks from stash (`.ino`, `platformio.ini` flag on a **non-ship** env only)
- scripts: `scripts/regression-harness/compile_stm_host.sh`, `stm_*.py`, `run_fft512_bench_eval.py`, `device_stm_telem_soak.py`
- text artifacts only: `artifacts/stm-track-b/**/*.md`, selected `*.json` under `gate_b_spike` (no binaries)

**Gate:** host scripts compile; firmware build only for the bench env that sets the flag. Confirm production `k1_hardware` has flag **off**.

**Message sketch:**
```
feat(bench): add STM FFT512 microbench path behind K1_STM_FFT512_BENCH
```

---

### Wave 5 — Serial / edgemixer structural (HIGH RISK — separate review)

**Stash paths (do not mix with Mode 32):**
- `director/k1_edgemixer.cpp` + `.ino` include rename `sb_edgemixer_lite` → `k1_edgemixer`
- `serial/serial_menu.cpp` **deleted** (−large)
- `serial/serial_cmd_handlers.{h,cpp}`, `serial/serial_menu.h`
- `persistence/bridge_fs.h`

**Action:** review diff size (−3290 lines dominated here). Confirm intentional before staging. May deserve its own branch.

**Message sketch (only if intentional):**
```
refactor(serial): remove serial_menu.cpp; finish k1_edgemixer rename
```

---

### Wave 6 — Shelved dual-sync / WB3 text evidence (optional)

**Stage text-only:**
- `artifacts/k1_dual_sync_eval_2026-07-08/**/*.md`
- selected `*.json` contracts under `recovery/` (attestations/manifests — not firmware blobs)
- `artifacts/stm-track-b/*.md`
- `artifacts/wb4_winner_staged_2026-07-29/` if small/text

**Exclude:** recovery upload binaries, PNGs unless Captain wants them, anything >5MB without explicit approval.

**Message sketch:**
```
docs(artifacts): archive dual-sync phase0 / WB3 text evidence packs
```

---

### Wave 7 — Research / architecture docs (optional)

| Paths | Message sketch |
|-------|----------------|
| `docs/architecture/effect-decomposition/*.md` | `docs(arch): waveform-class / captivation decomposition notes` |
| `docs/research/k1_*2026-07-1*.md` | `docs(research): lightshow family + gems port notes` |
| `docs/handover/2026-07-*.md` | `docs(handover): IM73D / captivation handovers` |
| `pixelblaze/**` | `docs(research): pixelblaze K1 effect ports` — or keep local |

---

### Wave 8 — Tooling overlays (optional, low priority)

| Paths | Notes |
|-------|--------|
| `.cursor/skills/{muller,nyt,vignelli}/` | OK if team wants them tracked (gitignore already allows `.cursor/skills`) |
| `.claude/skills/k1-effects-router/` etc. | Same |
| `.codex/skills/thinking-*` + `scripts/install-thinking-skills.sh` | Large; prefer submodule/install script over 30 skill dirs if possible |
| `scripts/loop/` | Agent loop helpers — only if used |
| `k1_ota_signing_PUBLIC.pem` | Deliberate: `chore(ota): add public verify key` |
| `docs/agent-stack/` | Mostly session logs — **skip** or ignore |

---

## Explicitly do NOT commit (archive elsewhere)

| Path | Why |
|------|-----|
| `artifacts/ble_midi_71_20260628/` | 388MB binaries + device logs |
| `artifacts/im73d_*` large audio/LED proof trees | Prefer archive repo / external store |
| `artifacts/K7180-Design-System/` media | Design asset dump; not firmware truth |
| `docs/forensics/runtime-evidence/**` if media-heavy | Keep text receipts only |
| `evidence/` | Empty-ish scratch |

---

## Suggested execution order (Captain approval checklist)

```
[ ] Wave −1  gitignore hygiene
[ ] Wave 0   MAX_CURRENT_MA (or unstage / reject)
[ ] Wave 1   authority frontmatter + IM69D docs → repo-truth PASS
[ ] Wave 2   Mode 32 complete slice (stash paths + cpp + test + m32 docs)
[ ] Wave 3   IM69D env + mic + upload guard
[ ] Wave 4   STM FFT512 bench (flag-gated)
[ ] Wave 5   serial/edgemixer only after intentional review
[ ] Wave 6+  optional docs/artifacts/skills
[ ] Drop or rewrite remaining stash@{0} residue
[ ] Do not push unless Captain asks
```

---

## Already committed (do not re-stage)

Unpushed on this branch (6):

1. `1957e53` docs(agent): mirror lineage oracle; record main K1 donor flash  
2. `556ec45` docs(forensics): WB-3 STM investigation pack and VP gate  
3. `437e076` docs(wb3): dual-track bench policy and artefact scaffolds  
4. `3b59794` docs(forensics): WB-3 dual-track bench policy and artefact scaffolds  
5. `8335b7f` docs(lane): kill and shelve dual-K1 sync; route to IM69D130 mic eval  
6. `5d5e9e4` test(harness): mic A/B comparison, interrupted-run recovery, IM69D role  

---

## Commit message style to match

Recent style: conventional prefix + scope — `feat(effects):`, `docs(lane):`, `test(harness):`, `fix(power):`. Prefer **why** in body (safety / ordinal stability / never cross-flash).

---

## One-line summary for Captain

**Stage small, restore stash by path, ship Mode 32 and IM69D as separate gated waves, ignore ~450MB of artifacts and agent local state, fix authority frontmatter before claiming the lane clean.**
