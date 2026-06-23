# Active Session Handoff — SpectraSynq K1 Firmware

**Updated:** 2026-06-23 · **Repo:** `/Users/spectrasynq/SpectraSynq_K1_Firmware` (origin `github.com/synqing/SpectraSynq_K1_Firmware`, branch `main`) · **CI:** green.
Read order: this file → `docs/architecture/firmware-modernization-program.md` (blueprint) → `docs/audit/2026-06-23-repo-audit.md` (audit). Old repo `SensoryBridge-main 9` = untouched archival backstop.

---

## ⏩ CURRENT ACTIVE LANE → Phase A · Lane 1: **GDFT decomposition (GDFT-first)**

Captain-ratified re-sequencing (2026-06-23): Phase A leads with **GDFT**, NOT `.ino`/serial_menu. GDFT is the keystone — root of the audio pipeline, the **only gap in the behavior-lock net**, and it carries the open **Critical int32-overflow bug**. Do it first; it needs a fresh context window (hardest, highest-stakes lane).

### The lane (one move, triple win)
1. **Decompose** `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h` (458 lines, single-includer header-soup) → a clean `gdft.cpp/.h` TU with explicit I/O: in = sample buffer + config; out = the ~12 spectral arrays it owns (`magnitudes*`, `novelty*`, `noise_samples`, `notes`, `frequencies`). Only **2 `CONFIG.*` refs**, **~30 Arduino/HAL touchpoints** behind a thin shim. **Behavior-preserving.**
2. **Golden-lock it** — the REAL spectrum oracle (the one the fan-out could only *replicate*). Fills the safety-net gap. Register in `ORACLE_MODULES`.
3. **Promote the overflow fix** — `K1_GDFT_INT64_*` flags (device-validated, NOT in `[env:k1_hardware]`). Now host-deterministic + golden-verifiable. Closes audit **Critical #1**.

### Reference spec (gift from the fan-out)
The spectrum agent's **replica** (a self-contained C++ driver reproducing the GDFT arithmetic verbatim with firmware line refs) is in the OLD repo:
`/Users/spectrasynq/SensoryBridge-main 9/scripts/regression-harness/golden/oracle_spectrum_novelty.py`.
Use it as the extraction's **correctness target**. It is NOT a valid oracle (locks a replica, not firmware) — the lane's job is to make the **real** `GDFT.h` host-compilable so the oracle locks firmware.

---

## ✅ DONE this session — Phase F (the fail-proof harness)
- Forked clean SpectraSynq repo (GPL-3.0 + Nishijima attribution preserved); README/NOTICE/CHANGELOG rebranded; litter excluded.
- **CI** (`.github/workflows/ci.yml`): pytest + golden gate + Gate Fα + `pio run -e k1_hardware`, green on Ubuntu.
- **Golden-master oracle harness** (`scripts/regression-harness/golden/`): self-describing oracles export `NAME`, `capture(firmware_root=None)`, `MUTATIONS`; registered in `ORACLE_MODULES` (`harness_selftest.py`). Gate = `tests/test_golden_master.py` (golden reproduce, float tol 1e-3) + `tests/test_harness_selftest.py` (**Gate Fα** mutation proof). `oracle_hostcompile.py` = shared host-compile substrate. Goldens + `MANIFEST.sha256` in `tests/golden/`.
- **4 oracles PROVEN + registered + CI-green:** `onset_beat`, `chord`, `smart_director`, `render` (each deterministic, golden frozen, 4/4 mutations caught against real firmware).

## ⏸️ Deferred (tracked)
- **tempo** oracle: built + Gate-Fα-proven on mac (4/4, 6400-rec dense trace); 1 discrete field flips cross-platform on CI. Committed, NOT in `ORACLE_MODULES`. Re-enable after coarsening the trace / excluding the boundary field.
- **semantic_state** oracle: REMOVED — stubs the producer (4-rec, sub-detectors not exercised via central tester; agent's own verify claimed 4/4, unreconciled). Reference in old repo. Needs proper central-harness integration if revived.
- **Audit backlog:** `docs/audit/2026-06-23-repo-audit.md` — GDFT overflow (Critical #1, closed by this lane), I2S Core-0 `portMAX_DELAY` timeout, `serial_menu` god-header decomposition, wireless security pre-ship (open AP + shared token), `.ino`→`main.cpp`.

## ⛔ NON-NEGOTIABLE DISCIPLINE (Captain-enshrined)
- **The harness IS the product.** No structural refactor merges without: `pio run -e k1_hardware` green **and** all registered goldens reproduce **and** Gate Fα proven **and** CI green.
- **Behavior-preserving by construction.** The golden master is the contract; a number changing = behavior changed = human-approved ticket only. The 4 existing goldens must stay byte/numerically identical through the GDFT lane.
- **Never register a blind/replica/stub oracle** — false confidence is worse than none.
- **Re-verify against REAL firmware**; never trust an agent's claim without re-running it yourself.
- Commit small + green; push; confirm CI green before moving on.

## Recent commits (main)
`0aab572` defer tempo (cross-platform) · `4294fef` float tol 1e-3 · `34ddbf6` 5-tap broaden (re-verified) · `d520e72` multi-oracle registry · earlier: Phase F harness + Gate Fα + CI + fork.
