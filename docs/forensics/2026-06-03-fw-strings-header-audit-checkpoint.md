---
abstract: "Read-only checkpoint for the fw_strings.h removal/folding audit. Establishes current source truth, provenance of the strings.h POSIX shadow, symbol usage, and initial refactor options before parallel SSA synthesis."
---

# fw_strings.h Header Audit Checkpoint

| Field | Value |
|---|---|
| Date | 2026-06-03 |
| Worktree | `/Users/spectrasynq/SensoryBridge-main 9` |
| Branch / HEAD | `feat/gdft-harness` / `75f0f3a` |
| Scope | Read-only architecture/refactor audit of `SPECTRASYNQ_K1_FIRMWARE/serial/fw_strings.h` |
| Files edited by this checkpoint | This document only |

## Gate / Source-Truth Notes

- [FACT] `AGENTS.md` says `.claude/CLAUDE.md` is canonical if the two diverge, and requires source-cited evidence plus write-to-disk checkpoints for multi-step analytical tasks.
- [FACT] `.claude/CLAUDE.md` and `.claude/skills/sensorybridge-doctrine/SKILL.md` were read for this audit. The doctrine gate makes architecture subordinate to musical/perceptual behaviour.
- [FACT] `.claude/skills/k1-firmware-change-gate/SKILL.md` was read. This is not an implementation pass, so no firmware edits, uploads, serial actions, or runtime claims are made here.
- [FACT] The AGENTS-mandated docs `firmware-v3/docs/reference/codebase-map.md`, `firmware-v3/docs/reference/fsm-reference.md`, `docs/protocol/k1-ws-contract.yaml`, and `docs/protocol/k1-rest-contract.yaml` do not exist at those root paths in this checkout. Moved/reference equivalents exist under `Lightwave-Ledstrip/` and were read after this checkpoint's initial source pass.
- [FACT] The AGENTS-referenced `/Users/spectrasynq/.agents/skills/perception-first-engineering/SKILL.md` was not present on disk. The audit still applies the stated question from AGENTS: "What is this doing, and does it need to exist in this form?"

## Current Source Truth

- [FACT] `SPECTRASYNQ_K1_FIRMWARE/serial/fw_strings.h` defines:
  - `SB_PASS` as `"PASS"` at line 10.
  - `SB_FAIL` as `"FAIL ###################"` at line 11.
  - `inline char notes_chromatic[12]` at line 23.
  - `inline char sharps[12]` at line 24.
- [FACT] `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:14-18` includes `fw_strings.h` and states that `globals.h` is now the universal hub preserving symbol availability after the old POSIX-shadow path was removed.
- [FACT] `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:78` also includes `fw_strings.h` directly before `globals.h`.
- [FACT] Current live source uses `SB_PASS` / `SB_FAIL` at:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:67,115,119`
  - `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:135`
  - `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:360`
  - `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:994,1865`
- [FACT] `rg` found no live source use of `notes_chromatic` or `sharps` outside their definitions in `fw_strings.h`.

## Provenance

- [FACT] `git log --follow -- SPECTRASYNQ_K1_FIRMWARE/serial/fw_strings.h` traces the file through:
  - `de4fc48` adding `SPECTRASYNQ_K1_FIRMWARE/strings.h`
  - `2cbeea9` renaming bare `PASS` / `FAIL` macros to `SB_PASS` / `SB_FAIL`
  - `ecbab24` marking `notes_chromatic` / `sharps` inline after the multi-TU POSIX-shadow defect surfaced
  - `75f0f3a` renaming `strings.h` to `serial/fw_strings.h` and explicitly including it via `system/globals.h`
- [FACT] `docs/k1-refactor-2026-05/spike2/VERDICT.md:91-98` records `strings.h` shadowing POSIX `<strings.h>` as a real ODR defect when the build gained a second translation unit.
- [FACT] `docs/forensics/2026-05-24-codex-review-checkpoint-1.md:62-76` records the arduino-esp32 3.2.0 / IDF 5.4.1 `FAIL` enum collision and the byte-preserving `PASS` / `FAIL` to `SB_PASS` / `SB_FAIL` rename.
- [FACT] `platformio.ini:40-55` and `scripts/platformio/k1_src_includes.py` show the current grouped-subfolder build, with subdirs added to `CPPPATH`.

## First-Principles Cut

Mechanism:
- Four globally available printing/note-label symbols are transported through a serial-named header and then re-exported by `globals.h`.

End-user perceived output:
- The only live end-user-visible output found in source is boot/status text bytes: `PASS` and `FAIL ###################`.
- No live perceptual audio/visual surface currently depends on `notes_chromatic` / `sharps` by source usage search.

Collapse points:
- Removing or moving `SB_PASS` / `SB_FAIL` without preserving includes breaks audio, serial, filesystem, and LED init prints.
- Reintroducing a file named `strings.h` risks POSIX shadowing again.
- Moving these names into a fat header can deepen the existing `globals.h` coupling if done carelessly.

Initial decision:
- The old file name `strings.h` definitely needed to die.
- The current standalone `fw_strings.h` does not appear to carry enough domain responsibility to deserve independent long-term ownership.
- The live contract that must survive is the exact serial output bytes for `SB_PASS` / `SB_FAIL`, not the current header boundary.

## Initial Options

1. Keep `fw_strings.h`.
   - Lowest immediate risk.
   - Leaves a tiny, serial-adjacent header whose only live payload is two status string macros plus two apparently-unused note arrays.

2. Fold `SB_PASS` / `SB_FAIL` into `system/constants.h` or a slim status constants header.
   - Better ownership than `globals.h` because these are constants, not mutable globals.
   - Needs include verification because current users receive them through `globals.h` / `.ino` include order.

3. Fold directly into `system/globals.h`.
   - Lowest code churn if `globals.h` is the universal hub anyway.
   - Architecturally poor: it makes a global-state header own serial response constants and reinforces the fat-header pattern the refactor is trying to unwind.

4. Fold into `serial/serial_menu.h`.
   - Wrong scope: `SB_PASS` / `SB_FAIL` are used by audio, persistence, and visual initialisation, not only the serial menu.

5. Delete `notes_chromatic` / `sharps`.
   - Plausible if source search remains clean, but must be verified against generated docs/harnesses and a clean build.

## Verification Required Before Any Implementation Claim

- `rg -n "SB_PASS|SB_FAIL|notes_chromatic|sharps|fw_strings|strings\\.h"` after edits.
- Host tests that cover status/harness assumptions: `pytest tests/` and the regression harness self-tests named by current repo gate.
- Firmware build gate: `pio run -e k1_hardware` and `pio run -e k1_bench_reference`.
- No serial/flash/runtime proof is required for a pure constant relocation unless status text bytes or startup sequencing are intentionally changed. If bytes change, runtime serial smoke becomes required.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-03 | codex | Created read-only checkpoint before final SSA synthesis. |
