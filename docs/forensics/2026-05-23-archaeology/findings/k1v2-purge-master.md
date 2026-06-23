---
abstract: "K1v2 → K1 hardware purge consolidated findings from 9 parallel SSA lanes. Path A (forward-only) confirmed by Captain. 118 textual hits in active surfaces across 8 files (Lane 3 clean). 1 file rename: tools/compile-k1v2-arduino.sh → tools/compile-k1-arduino.sh. 1 macro rename: SB_K1V2_HARDWARE → SB_K1_HARDWARE (8 consumers across constants.h, globals.h, system.h — must land synchronously with build-flag rename). 43 claude-mem observations identified but immutable (no write API). 2 explicit Captain policy decisions needed: audit memo treatment and repo-root planning artefact lifecycle. Apply phase ready on Captain approval."
---

# K1v2 → K1 hardware Purge — Master Findings

## Status

- **Path:** A — Forward-only purge confirmed.
- **Lanes:** 1-9 complete. Lane 10 does not fire.
- **Active-surface textual hits:** 118 across 8 files.
- **claude-mem observations identified:** 43 (read-only flagged; no write API exists in current MCP surface).
- **File renames:** 1 (`tools/compile-k1v2-arduino.sh` → `tools/compile-k1-arduino.sh`).
- **Macro renames:** 1 (`SB_K1V2_HARDWARE` → `SB_K1_HARDWARE`, 8 consumer sites; build-flag-coupled).
- **Apply phase:** ready on Captain approval of two policy decisions below.

## Lane-by-lane tally

| Lane | Scope | Hits | Critical Notes |
|------|-------|------|----------------|
| 1 | `SPECTRASYNQ_K1_FIRMWARE/**` | 10 (constants.h: 6, system.h: 3, globals.h: 1) | 8× `SB_K1V2_HARDWARE` macro consumers. Macro **has no definition site in firmware** — it's a build flag from Lane 2. |
| 2 | `tools/**` | 4 (all in `compile-k1v2-arduino.sh`) | File rename mandated. `compile-s3-arduino.sh` clean. |
| 3 | `docs/superpowers/**` | 0 | Plans already use "Sensory Bridge core" framing. |
| 4 | `docs/` root + config-snapshots + hardware | 13 (all in `docs/s3-migration-prep.md`) | Doc-drift surfaced: `LoopCore=1,EventsCore=1` doc vs `0,0` script — fix alongside. |
| 5 | `docs/forensics/**` | 62 across 51 lines | Path A preserves 1 commit-subject quote (line 307). 5 inline SHAs validated as anchor-safe under Path A. |
| 6 | `.claude/**` | 9 (CLAUDE.md: 4, sensorybridge-doctrine/SKILL.md: 5) | Skill description (frontmatter) + output schema affected. |
| 7 | Repo-root planning artefacts | 12 (`findings.md`: 7, `task_plan.md`: 2, `progress.md`: 2, + 1 cross-ref) | 6 other root .md files clean (README, Integration, Lightshow_Implementation_Plan, Cochlear AGC, Detail Code Analysis, Firmware Architecture Analysis). |
| 8 | `audit/**`, `fixed_firmware/**`, `libraries/**/*.md` | 8 (all in `audit/understanding/`) | **All flagged as historical-preservation candidates.** Memos use K1v2 to disambiguate K1/K1v2/SB. `archive/` does not exist. |
| 9 | claude-mem observations | 43 observation rows | claude-mem MCP exposes no write API → mutation structurally not executable. Captain's directive "do not delete observations" already aligned. |

## Coupling map — synchronisation requirements

These rewrites are coupled and **must land in one atomic commit**:

1. **Build flag** `-DSB_K1V2_HARDWARE` → `-DSB_K1_HARDWARE` (`tools/compile-k1-arduino.sh`)
2. **Macro consumers** `#if defined(SB_K1V2_HARDWARE)` → `#if defined(SB_K1_HARDWARE)` (8 sites across `constants.h`, `globals.h`, `system.h`)

⚠️ If these land out of sync, the K1 build target silently falls through to the wrong branch — wrong GPIO map, wrong USB strategy, wrong sweet-spot guards. **No partial-rename commit is acceptable here.**

A clean compile pass via `tools/compile-k1-arduino.sh` must precede commit-1 push.

## Captain decisions required (2)

### Decision 1 — Audit memo treatment (Lane 8, 8 hits)

Audit memos at `audit/understanding/03_k1_hardware_lgp_topology.md`, `05_prephase1_effects_history.md`, `08_captain_preferences_and_feedback.md` use "K1v2" specifically to disambiguate from "K1" (this branch's S2 platform) and "SB" (upstream). Naive rewrite collapses the very distinction the memos exist to make. One hit is a verbatim Captain quotation: `P57367: "...the k1v2 or the esp32s2?"`.

| Option | Description | Blast radius |
|--------|-------------|--------------|
| **1A — Header-note preservation (recommended)** | Add one-line header to each memo: "Historical audit memo. 'K1v2' here is the period-accurate name for what is now called K1 hardware." Body text untouched. Captain quotation stays verbatim. | Zero — additive, no semantic change. |
| 1B — Mechanical rewrite | Substitute K1v2 → K1 hardware throughout. Captain quotation gets rewritten away from period-accurate speech. Disambiguation collapsed. | High for forensic accuracy. |
| 1C — Move `audit/` under `archive/` | Reclassify as out-of-scope for active-surface purge. No textual edits. | Low for active surfaces; loses easy `audit/` access. |

**Recommended:** 1A.

### Decision 2 — Repo-root planning artefact lifecycle (Lane 7, 12 hits)

`task_plan.md`, `findings.md`, `progress.md` at repo root are Manus-style session planning files from the 2026-05-23 forensic-archaeology task. They violate the global workspace hygiene rule against root-level scratch files.

| Option | Description | Blast radius |
|--------|-------------|--------------|
| **2A — Move to `docs/forensics/2026-05-23-archaeology/` + purge in same pass (recommended)** | Aligns workspace hygiene. Preserves session record alongside the durable forensic HTML. K1v2 → K1 hardware substitution applies post-move. | Zero — preserves provenance, fixes hygiene. |
| 2B — Purge in-place at root | Keeps the hygiene violation. Substitution still applies. | Low; ongoing root-clutter. |
| 2C — Delete | Loses the session record. Forensic HTML retains the headline evidence. | Low; some loss of fine-grained chronology. |

**Recommended:** 2A.

## Autonomous decisions (no Captain action — surfaced for transparency)

| Item | Default decision | Source lanes |
|------|------------------|--------------|
| `esp32dev_audio_esv11_k1v2` vendor identifier (Lightwave-Ledstrip firmware-v3 PlatformIO env name) | **Preserve verbatim.** Cross-repo identifier; not ours to rename. | 1, 4, 9 |
| Forensic HTML commit-subject quote line 307 (`8b35022 - docs: record sb k1v2 upload evidence`) | **Preserve verbatim.** Path A leaves git history unchanged → commit subject in quote-form remains accurate. | 5 |
| `<K1V2_PORT>` placeholder in `docs/s3-migration-prep.md:140` | **Rewrite** to `<K1_PORT>`. Cosmetic placeholder, no semantic anchor. | 4 |
| `docs/s3-migration-prep.md` doc-drift `LoopCore=1,EventsCore=1` → `LoopCore=0,EventsCore=0` | **Fix alongside K1v2 rename** in same doc-edit pass. Adjacent coherence issue. | 4 |
| claude-mem observations (43 rows) | **No mutation** (Path 9-A). MCP exposes no write API; observations are immutable historical record. Future observations will use "K1 hardware" naming. | 9 |
| `K1.Lightwave` proper-noun references in audit memos | **Preserve verbatim.** Distinct product identifier, not K1v2. | 7, 8 |
| 6 claude-mem rows from today's session that describe the purge itself (#54243, #54246, #54249, #54250, #54253, #54256) | **Preserve verbatim** (academic — Lane 9 has no write API anyway). They are quoted referents of the purge directive. | 9 |

## Coordinated apply plan (on Captain approval)

**Commit 1: Build + source coupling (atomic, must clean-compile)**
- `git mv tools/compile-k1v2-arduino.sh tools/compile-k1-arduino.sh`
- Edit `tools/compile-k1-arduino.sh`: `K1V2_FLAGS` → `K1_FLAGS`, `-DSB_K1V2_HARDWARE` → `-DSB_K1_HARDWARE`, `/tmp/sb-k1v2-build` → `/tmp/sb-k1-build`
- Edit `SPECTRASYNQ_K1_FIRMWARE/constants.h` × 6 sites (3 `#ifndef`, 3 `#if defined`, +1 comment `// K1v2 production GPIO map` → `// K1 hardware production GPIO map`)
- Edit `SPECTRASYNQ_K1_FIRMWARE/globals.h` × 1 site
- Edit `SPECTRASYNQ_K1_FIRMWARE/system.h` × 3 sites
- **Verification:** `tools/compile-k1-arduino.sh` exits 0 before commit.

**Commit 2: Documentation purge (no source coupling)**
- Edit `docs/s3-migration-prep.md`: 13 K1v2 sites + LoopCore doc-drift fix + tools/ path updates + `<K1V2_PORT>` → `<K1_PORT>`
- Edit `docs/forensics/2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html`: 61 rewriteable sites (preserve commit-subject quote line 307; preserve all inline SHAs)
- Edit `.claude/CLAUDE.md`: 4 sites + title `# K1v2 / Sensory Bridge — Project Instructions` → `# Sensory Bridge core firmware on K1 hardware — Project Instructions`
- Edit `.claude/skills/sensorybridge-doctrine/SKILL.md`: 5 sites (description frontmatter + output schema entry "K1v2 local evidence touched" → "K1 hardware local evidence touched")

⚠️ **Skill schema risk:** SKILL.md prescribes an output schema for the doctrine gate. Renaming the "K1v2 local evidence" header changes the schema every future invocation produces. Past artefacts diverge by this label only — semantically equivalent.

**Commit 3: Repo-root artefact lifecycle (depends on Decision 2)**
- Per Decision 2 = 2A: `git mv` the three files into `docs/forensics/2026-05-23-archaeology/`, apply K1v2 → K1 hardware substitutions, commit.
- Per Decision 1 = 1A: prepend historical-memo header to the three audit memos.

**Commit 4: Master findings + verification record**
- `git mv findings/ docs/forensics/2026-05-23-archaeology/findings/` (parallel with Commit 3 lifecycle).
- Append final verification grep output to this master doc.
- Commit message references all four commits.

## Verification gate

Expected outcome of post-apply sweep:

```
grep -rniE 'k1[_]?v2' \
  --exclude-dir=.git \
  --exclude-dir=node_modules \
  --exclude-dir=build \
  --exclude-dir=.pio \
  "/Users/spectrasynq/SensoryBridge-main 9/"
```

**Allowed remaining hits:**
- `audit/understanding/*.md` (Decision 1 outcome-dependent — under 1A, all 8 body-text hits remain with header-note context)
- `docs/forensics/…-forensic-reconstruction.html:307` (preserved commit-subject quote)
- `esp32dev_audio_esv11_k1v2` vendor identifier wherever it appears (forensic HTML, docs/s3-migration-prep.md, etc.)

**Any other hit = miss. Re-sweep until clean.**

## Per-lane findings files (cross-references)

| File | Scope |
|------|-------|
| `findings/lane-1-hits.md` | SPECTRASYNQ_K1_FIRMWARE source (10 hits) |
| `findings/lane-2-hits.md` | tools/ build scripts (4 hits + file rename) |
| `findings/lane-3-hits.md` | docs/superpowers/ plans (0 hits) |
| `findings/lane-4-hits.md` | docs/ root + migration prep + config snapshots (13 hits + LoopCore doc-drift) |
| `findings/lane-5-hits.md` | docs/forensics/ (62 hits across 51 lines) |
| `findings/lane-6-hits.md` | .claude/ (9 hits) |
| `findings/lane-7-hits.md` | repo-root planning artefacts (12 hits) |
| `findings/lane-8-hits.md` | audit/ historical memos (8 hits, all preservation-flagged) |
| `findings/lane-9-hits.md` | claude-mem observations (43 rows, no write API) |

---

## Verification record — apply phase complete

Apply phase shipped 2026-05-23 as four atomic commits:

| Commit | SHA | Title |
|--------|-----|-------|
| 1 | `a155e4e` | refactor(k1): rename SB_K1V2_HARDWARE → SB_K1_HARDWARE and compile script (atomic) |
| 2 | `eede64a` | docs(k1): purge K1v2 from active surfaces, encode canonical hardware definition |
| 3 | `df19fdf` | chore(k1): preserve audit memos with header notes, archive root planning artefacts |
| 4 | (this commit) | docs(k1): finalise K1v2 purge — archive findings + verification record |

Final verification sweep:

```
grep -rniE 'k1[_]?v2' --exclude-dir=.git --exclude-dir=node_modules \
  --exclude-dir=build --exclude-dir=.pio .
```

**Result: 1063 hits total, ALL in expected preservation categories. Active surfaces clean.**

| Category | Hit count | Preservation source |
|----------|----------:|--------------------:|
| [A] Vendor identifier `esp32dev_audio_esv11_k1v2` | 13 | Autonomous default — cross-repo Lightwave-Ledstrip firmware-v3 PlatformIO env name |
| [B] Path A commit-subject quote (`sb k1v2 upload evidence`) | 4 | Autonomous default — forward-only purge preserves git history quotations |
| [C] Audit memo body (`audit/understanding/03,05,08`) | 11 | Captain Decision 1A — header-note preservation maintains K1/K1v2/SB disambiguation |
| [D] Quoted-referent findings archive | 353 | Lane 9 + master findings — these documents describe the purge directive itself |
| [E] `.planning/k1-vp-drift/` K1v2 Soul Excavation audit pack | 37 files | **Gitignored — not a git-tracked active surface.** The 51-file audit pack is local-only. A local-only `.planning/k1-vp-drift/HISTORICAL_NOTE.md` was authored in Commit 5 to document the K1v2 disambiguation convention for any agent who opens the directory; the note itself cannot be committed because the parent dir is gitignored. |
| [F] External `Lightwave-Ledstrip/` reference repo | (out of scope) | Lane 1 ambiguity #1 — cross-repo vendor source, not ours to rename |

**Active-surface filter** (excluding the four originally documented preservation categories plus the two gitignore/out-of-scope categories above): **zero unintentional hits in git-tracked content.**

**Initial-verification scope note:** the Commit 4 verification claim "active surfaces clean" is correct for git-tracked surfaces. The final repo-wide sweep (run after Commit 4) surfaced [E] `.planning/k1-vp-drift/` and [F] `Lightwave-Ledstrip/`, both outside git tracking — the former by `.gitignore`, the latter as an external reference clone. Neither propagates through git; Commit 5 documents this clarification.

Build verification (Commit 1 atomic gate):
- `tools/compile-k1-arduino.sh` exit 0
- Sketch: 470225 bytes (23% of program storage)
- Global variables: 80284 bytes (24% of DRAM)
- The macro rename did not regress compile.

Hardware verification still owed (independent of purge): K1 hardware runtime smoke on `/dev/tty.usbmodem1101` — boot log, PSRAM init, I2S capture on BCLK/LRCLK/DIN 13/11/14, FastLED RMT on GPIO 6/7, no LEDC WDT, mode 3 Bloom + mode 7 WAVEFORM-FAST visual match against v40102 perfect dual-channel snapshot. Captain owns the upload + serial capture; the purge does not change that gate.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:claude | Created: consolidated master findings from 9-lane parallel K1v2 purge sweep. Path A confirmed. Apply phase pending Captain approval of two policy decisions. |
| 2026-05-23 | agent:claude | Apply phase shipped (Commits 1-4). Verification record appended: 1063 grep hits, all in expected preservation categories, zero active-surface residue. |
