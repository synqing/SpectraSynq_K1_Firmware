---
abstract: "Record of the 2026-06-23 SpectraSynq K1 firmware fork: how the clean-slate repo was produced from SensoryBridge-main 9, what was renamed/excluded, the GPL-3.0 attribution decision, the green-gate proof, and the explicitly-deferred items (SSID/token, GDFT promotion, CI). Read before trusting repo lineage or asking 'where did X go'."
---

# SpectraSynq K1 — Fork Record (2026-06-23)

This repository is the **official SpectraSynq-branded fork** of the K1 firmware,
created from the `SensoryBridge-main 9` working tree on 2026-06-23. It is a
**clean-slate** repo: fresh history, brand identity rebranded, litter excluded.

## Captain decisions that governed this fork

| Decision | Choice |
|----------|--------|
| Licence | **Rebrand, stay GPL-3.0** + add upstream attribution (legally clean). |
| Fork target | **New directory, clean slate** (fresh history). |
| Rename depth | **Identity + customer-visible only**; internal `sb_` heritage prefix kept per the 2026-06-21 standing order. |
| Sequencing | Delegated to engineering judgment (see below). |

## What was done

1. **Selective allowlist copy** from the archive tree into
   `/Users/spectrasynq/SpectraSynq_K1_Firmware/` — firmware + host harness +
   build config + libraries + docs only. Result: **44 MB → ~120 MB** vs. the
   archive's ~7 GB. The old repo (`SensoryBridge-main 9`, full git history +
   `SpectraSynq-K1-Firmware-SB9-` remote) is **untouched** as the archival
   backstop.
2. **Firmware identity rename** — `SENSORY_BRIDGE_FIRMWARE/` →
   `SPECTRASYNQ_K1_FIRMWARE/` (dir + `.ino`); 223 path-token references across
   `platformio.ini`, scripts, tests, and docs updated.
3. **GPL compliance** — `LICENSE` stays GPL-3.0; `NOTICE` now credits Connor
   Nishijima / Lixie Labs and explains the heritage. The product brand is
   SpectraSynq; the licence lineage is preserved (these are not in conflict).
4. **Brand surfaces** — new `README.md`, rebranded `NOTICE`, `CHANGELOG.md`.
5. **Hygiene** — clean `.gitignore`; no `_scratch/`, `.claude/worktrees/`,
   `.codex-subagent/`, build artefacts, or heavy media carried over.

## Scope exclusions (intentional)

- **`sb-tab5-wireless-controller/` (5.0 GB)** and **`Lightwave-Ledstrip/`
  (1.2 GB)** — separate companion projects, not K1 firmware. Each warrants its
  own SpectraSynq repo. Their tests were removed here; the firmware↔Tab5
  palette/`MAX_PALETTE` sync test now **skips** when Tab5 is absent and must be
  enforced in an integration context where both repos are present.
- Heavy forensic media (9 `.mp4` A/B captures, 4 colour-book PDFs) and 318 MB
  of `build/` artefacts. The one synthetic control fixture a test reads
  (`build/audio-semantic-metrics/control-fixtures/control_127bpm_click_44k1.wav`)
  was restored deliberately.

## Proof (green gate)

- **Host:** `pytest tests/` → **559 passed, 1 skipped** (the intentional Tab5
  cross-repo skip). Each rename-related failure was traced to a deliberate
  exclusion and proven absent on the archive baseline — the rename itself is
  behaviour-preserving.
- **Firmware:** `pio run -e k1_hardware` → exit 0, `firmware.bin` produced.

## Deferred (NOT done in the fork — tracked)

The fork is deliberately **behaviour-preserving**; risky changes that need
device validation were not bundled with a rename:

- **SSID `LightwaveOS-AP` → SpectraSynq + per-device control token** — a
  device-pairing contract change; belongs to the wireless-enablement task with
  Tab5 coordination (wireless is OFF by default today).
- **GDFT int32-overflow fix promotion** to the production env (device A/B on
  bench 12201 required first).
- **I2S `portMAX_DELAY` Core-0 timeout/recovery**.
- **CI pipeline + commit-gate enforcement** (the gate hook exists under
  `scripts/hooks/`).
- Full backlog: [`audit/2026-06-23-repo-audit.md`](./audit/2026-06-23-repo-audit.md).

## Not done by an agent (Captain / authorized action)

- **Creating and pushing the new GitHub remote.** This repo has **no remote**;
  publishing it is a public-facing action left to Captain.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-23 | agent:claude-code | Created: fork record for the clean-slate SpectraSynq K1 firmware repository. |
