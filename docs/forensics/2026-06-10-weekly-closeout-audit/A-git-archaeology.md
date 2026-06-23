---
abstract: "Git archaeology closeout audit 2026-06-10. Landing state of all work units from the last 7 days (2026-06-03 to 2026-06-10). Branch: wip/audio-saliency-recovery, 208 commits ahead of main, NOT merged. 20 modified tracked files + 35 untracked files uncommitted."
---

# Git Archaeology — Closeout Audit 2026-06-10

Generated: 2026-06-10
Repo: `/Users/spectrasynq/SensoryBridge-main 9`
Current branch: `wip/audio-saliency-recovery`
Ahead/behind main: **208 ahead, 0 behind**

---

## Work Units — Landing State Table

| WORK UNIT | Commits (first↔last) | Branch | Merged to main? | Uncommitted residue? | Subsystems touched |
|---|---|---|---|---|---|
| **Audio Semantic Forward-Graft (v2 DSP)** | `69d7321`…`4e96e30` (2026-06-03–06-05) | wip/audio-saliency-recovery | NO | No tracked residue | `SPECTRASYNQ_K1_FIRMWARE/audio/` (sb_tempo, sb_onset_beat, sb_chord_saliency, sb_musical_saliency, sb_audio_snapshot), `platformio.ini`, `tests/`, `docs/forensics/tempo_tracking_refactor/` |
| **VME L1 Waveform Memory Primitives** | `797ca82`…`0f8be64` (2026-06-08) | wip/audio-saliency-recovery (park/vme-l1-waveform-20260608 has one doc-only commit `23522a3`) | NO | No tracked residue | `SPECTRASYNQ_K1_FIRMWARE/effects/` (waveform, waveform_fast, waveform_tempo), `visual/led_utilities.h` (modified in working tree), `visual/lightshow_modes.h`, `tests/test_waveform_memory_l1_static.py`, `docs/forensics/vme_l1/` |
| **VP Motion Lab (VPML) host harness + firmware diag** | `88a1bc3` (2026-06-09, HEAD commit) | wip/audio-saliency-recovery | NO | YES — 20 modified tracked files + 17 untracked runtime-evidence files + 6 new scripts + 3 new tests | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h`, `visual/led_utilities.h`, `serial/serial_menu.h`, `scripts/regression-harness/vpml_live_runner.py`, `vpml_run_console.py` + new: `vpml_compiler.py`, `vpml_workbench.py`, `vpml_run_console_server.py`, `docs/forensics/vp_motion_lab/`, `docs/forensics/runtime-evidence/` |
| **Tab5 Wireless Controller + K1 WebSocket Protocol v2** | `b613de5`…`a80e888` (2026-06-09, 30 commits) | wip/audio-saliency-recovery | NO | YES — `sb-tab5-wireless-controller/` (5 files modified + 1 new `LightComposerUI_pages.cpp`), `tools/tab5_k1_dashboard_harness.py`, `tests/test_sb_tab5_wireless_controller_static.py`, `tests/test_tab5_dashboard_harness.py` | `sb-tab5-wireless-controller/` (main.cpp, LightComposerUI.cpp/.h, Tab5SerialHarness.cpp, platformio.ini), K1 firmware: `SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp`, `control/sb_wireless_control.cpp`, `platformio.ini`, `tools/`, `tests/`, `docs/forensics/sb-tab5-control/` |
| **K1 Upload Guard hardening** | `2ff26a1`, `f6116ea` (2026-06-09) | wip/audio-saliency-recovery | NO | YES — `scripts/platformio/k1_upload_guard.py` (1 line modified), `tests/test_k1_upload_guard.py` (1 line modified) | `scripts/platformio/k1_upload_guard.py`, `tests/test_k1_upload_guard.py` |
| **VE-Auto-Loop / LGP optics / bloom harness** | `6bdaa9e`…`fdd152c` (2026-06-03–06-04, on feat/gdft-harness in VE-Auto-Loop worktree) | feat/gdft-harness (worktree at `/Users/spectrasynq/SensoryBridge-ve-auto-loop`) | NO | Not visible in main tree working-tree status | `scripts/regression-harness/loop.py`, `lgp_optics.py`, `spaces/lgp_real_*.py`, `tests/test_loop.py` |
| **Perceptual Bloom effect (light_mode_perceptual_bloom)** | `a77b3c6` (2026-06-04) | wip/perceptual-bloom | NO | None visible in main tree | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_perceptual_bloom.cpp`, `config_types.h`, `system.h`, `visual/channel_effect_state.h`, `visual/lightshow_modes.h` |
| **Musical Saliency (sb_musical_saliency RC-1/RC-4)** | `aef74f4`, `cd94fd7` (2026-06-04) | wip/audio-saliency-recovery | NO | No tracked residue | `SPECTRASYNQ_K1_FIRMWARE/audio/sb_musical_saliency.cpp/.h`, `docs/forensics/`, `scripts/regression-harness/musical_saliency_benchmark.py`, `novelty_from_wav.py` |
| **Speckit toolchain install** | `19e0bb4` (2026-06-03) | wip/audio-saliency-recovery | NO | No tracked residue | `.agents/skills/speckit-*`, `.claude/skills/speckit-*`, `.specify/` |
| **Commit gate + tiered pre-commit hook** | `138a7c9` (2026-06-03) | wip/audio-saliency-recovery | NO | `613a79c` adds Tab5 tier (already committed) | `scripts/hooks/pre-commit`, `scripts/hooks/install.sh`, `docs/git/commit-gate.md` |

---

## Uncommitted Working-Tree State

### Modified tracked files (20 files, none staged)

```
SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h         (283 lines net diff)
SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h          (1 line)
SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h        (118 lines net diff)
docs/forensics/vp_motion_lab/latest-vpml-evidence-page.html  (334 lines net diff)
docs/forensics/vp_motion_lab/latest-vpml-evidence-page.json  (12960 lines net diff — large evidence update)
platformio.ini                                        (12 lines)
sb-tab5-wireless-controller/platformio.ini            (1 line)
sb-tab5-wireless-controller/src/harness/Tab5SerialHarness.cpp (99 lines)
sb-tab5-wireless-controller/src/main.cpp              (8 lines)
sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp (78 lines)
sb-tab5-wireless-controller/src/ui/LightComposerUI.h  (85 lines)
scripts/platformio/k1_upload_guard.py                 (1 line)
scripts/regression-harness/vpml_live_runner.py        (151 lines)
scripts/regression-harness/vpml_run_console.py        (286 lines)
tests/test_k1_upload_guard.py                         (1 line)
tests/test_sb_tab5_wireless_controller_static.py      (68 lines)
tests/test_tab5_dashboard_harness.py                  (10 lines)
tests/test_vpml_live_runner.py                        (24 lines)
tests/test_vpml_run_console.py                        (130 lines)
tools/tab5_k1_dashboard_harness.py                    (15 lines)
```

Nothing is staged (`git diff --stat --cached` returned empty).

### Untracked files (35 items), grouped by directory

| Count | Directory / File |
|-------|-----------------|
| 17 | `docs/forensics/runtime-evidence/` — VPML session evidence files (frame-gate.json, frames.log, raw.log, vpml-summary.json, session-error.json) from 4 capture sessions: 20260609T214319, T214857, T220729, T232714 |
| 6 | `scripts/regression-harness/` — new scripts: `high_bin_alias_audit.py`, `k1_paired_snappiness_capture.py`, `sample_rate_32k_migration_model.py`, `vpml_compiler.py`, `vpml_run_console_server.py`, `vpml_workbench.py` |
| 3 | `tests/` — `test_k1_paired_snappiness_capture.py`, `test_vpml_run_console_server.py`, `test_vpml_run_console_server_smoke.py` |
| 1 | `tools/` — `sph0645_phase01_dump_raw.py` |
| 1 | `sb-tab5-wireless-controller/src/ui/` — `LightComposerUI_pages.cpp` |
| 1 | `docs/forensics/sb-tab5-control/` — `2026-06-09-tab5-k1-control-hub-mockup.html` |
| 1 | `docs/forensics/vp_motion_lab/ssa/` (directory) |
| 1 | `evidence/tab5-k1-dashboard-harness/20260609-215950/` (directory) |
| 1 | `evidence/ssa/v3-sketch-20260609/` (directory) |
| 1 | `evidence/sample-rate-lanes/` (directory) |
| 1 | `tab5_mockup_full.png` (root-level, workspace hygiene: should move to `docs/forensics/sb-tab5-control/` or `docs/`) |
| 1 | `.claude/hooks/.summonaikit-task-contract.txt` |

**Total: 20 modified tracked + 35 untracked = 55 items with uncommitted work**

---

## Stash List

```
stash@{0}: On refactor/main: wip-claudemd
```

One stash on `refactor/main` (CLAUDE.md work in progress), unrelated to current wip branch activity.

---

## Branch State Summary

### Branches NOT merged to main (relevant active ones)
- `wip/audio-saliency-recovery` ← **current** — 208 commits ahead of main, 0 behind
- `feat/gdft-harness` — VE-Auto-Loop worktree (`/Users/spectrasynq/SensoryBridge-ve-auto-loop`), ahead of origin by 14
- `wip/perceptual-bloom` — perceptual_bloom effect, not merged
- `park/vme-l1-waveform-20260608` — 1 doc-only commit, not merged
- `wf/effect-*` (13 branches) — individual beat-reactive effect candidates from agent fleet, not merged
- Many others (backup/*, spike/*, sandbox/*, worktree-agent-*, worktree-wf_*)

### Branches merged to main
- `main` itself, plus 14 `worktree-*` branches (internal worktree tracking branches, not real feature work)

### Ahead/Behind main
```
wip/audio-saliency-recovery: 208 ahead, 0 behind
```

---

## Key Command to Confirm Headline

```bash
git -C "/Users/spectrasynq/SensoryBridge-main 9" rev-list --left-right --count main...HEAD
# Returns: 0	208
```

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-10 | agent:claude-code | Created: git archaeology closeout audit for last 7 days of work |
