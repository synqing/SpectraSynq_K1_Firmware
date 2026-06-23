# Active Session Handoff — SpectraSynq K1 Firmware

**Updated:** 2026-06-23 · **Repo:** `/Users/spectrasynq/SpectraSynq_K1_Firmware` (origin `github.com/synqing/SpectraSynq_K1_Firmware`, branch `main`) · **CI:** green.
Read order: this file → `docs/architecture/firmware-modernization-program.md` (blueprint) → `docs/audit/2026-06-23-repo-audit.md` (audit). Old repo `SensoryBridge-main 9` = untouched archival backstop.

---

## ⏩ CURRENT ACTIVE LANE → Phase A · Lane 1: **GDFT decomposition (GDFT-first)**

> **STATUS 2026-06-23 — S1 + S1.5 COMPLETE & independently verified-green.** `k1_gdft_core.cpp/.h` extracted (statement-identical to `GDFT.h@HEAD`, `diff -w -B` empty); `GDFT.h` now a shim; `oracle_gdft` registered + golden frozen; Gate Fα PROVEN (int64-magnitude mutation CAUGHT); `pio -e k1_hardware` green (RAM 33.4% / Flash 9.9%); full `pytest tests/` 562 passed. **NEXT = S2** (flip `K1_GDFT_INT64_MAGNITUDE_V1`+`_RECURRENCE_V1` ON) — owes **3 device gates**: MabuTrace Core-0 margin · prod-env AGC-scale · eyes-on on registry device. Footguns: `build_src_filter` is an ALLOWLIST (every new `k1_*.cpp` needs an entry; `director/`+`control/` still `sb_*`-only) · dead `audio/audio_transfer.h` has duplicate goertzel lines (delete in cleanup) · oracle locks `process_GDFT` given reconstructed coeffs/tilt, NOT the precompute (true-center needs its own lock).

Captain-ratified re-sequencing (2026-06-23): Phase A leads with **GDFT**, NOT `.ino`/serial_menu. GDFT is the keystone — root of the audio pipeline, the **only gap in the behavior-lock net**, and it carries the open **Critical int32-overflow bug**. Do it first; it needs a fresh context window (hardest, highest-stakes lane).

### ⚑ SCOPED — full extraction contract: [`docs/architecture/gdft-decomposition-lane.md`](../docs/architecture/gdft-decomposition-lane.md) (authority for this lane; read it first)
Synthesised from 3 load-bearing agents (gdft-surface, gdft-replica-spec, gdft-int64-forensics) + first-hand `GDFT.h` read, doctrine-gated 2026-06-23.

### The lane (one move, triple win)
1. **Decompose** `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h` → `audio/k1_gdft_core.cpp/.h` (K1 naming, matches `K1_GDFT_*` flags). **Behavior-preserving** (verbatim arithmetic, extern-globals; explicit-I/O is deferred S3 polish). KEY: the **device noise-cal FSM (GDFT.h:196-266) is EXCLUDED** from the core TU — it has zero spectral coupling in `k1_hardware` (`SB_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED=0`), stays in a thin `GDFT.h` wrapper. Keep `int32_t magnitudes[]` (storage is part of the overflow surface).
2. **Golden-lock** `oracle_gdft.py` (mirror `oracle_chord.py`): driver = replica trace **+ sustained 440 Hz @ amp 16000 ≥10 frames** (else blind to the int64 fix); emit `mag_i32[0..79]` + `spec` + `nov`; DEFINES pin the **buggy int32 baseline**. Register in `ORACLE_MODULES`.
3. **Promote the int64 PAIR** — `K1_GDFT_INT64_MAGNITUDE_V1` **+** `K1_GDFT_INT64_RECURRENCE_V1` together (coupled; magnitude alone proven insufficient on device). **HOLD** `K1_GDFT_TRUE_CENTER_V1` (eyes-on FAIL) and `K1_SPECTRAL_WINDOW_V1` OFF. S2 production-flip owes 3 device gates: MabuTrace Core-0 margin, prod-env AGC-scale, eyes-on. Closes audit **Critical #1**.

Blast radius: the 4 existing host goldens drive detectors with synthetic snapshots — they never call `process_GDFT`, so S1/S2 cannot move them on host (only the new `gdft` golden moves). Reference replica (correctness target, NOT a valid oracle): old repo `scripts/regression-harness/golden/oracle_spectrum_novelty.py`.

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
