# Handover set — 2 September 2026 (revised after reading the DualMCU repo)

Standalone briefs for CLI coding agents (Claude Code / Codex). Each is complete on its own: open the agent in the project folder and paste one brief as its first message.

**Project folder (all briefs):** `/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-K1-DualMCU-Firmware`
**Read-only oracle (never edited):** `/Users/spectrasynq/SpectraSynq_K1_Firmware`
**Repo state when written:** HEAD `553b6be`, branch `lane/k1-dm-100-dither-truth-table`; K1-DM-000/005/010/040/060/080 PASSING, 020/030/050/070/090 BLOCKED, 100 FAILING.

| # | Brief | Status | Needs hardware | Depends on |
|---|---|---|---|---|
| A | Harness restructure | **Withdrawn** — the 24 Aug audit repairs landed 27 Aug (commit `f2f19a1`, K1-DM-080 PASSING). See the stub. | — | — |
| B | 24 kHz / 180 goldens from the legacy oracle + Emotiscope tempo-field oracle | Live | No | — |
| C | Descriptor table extends `core/control/control_catalogue` → generated map + schema blob | Live | No | — |
| D | SysEx schema transport library under `contract/` | Live | No | C's blob format (or synthetic stand-in) |

**Corrections made after reading the repo (2 Sep, evening):**
- A withdrawn: composition root `rt1062_production`, post-link gates, artefact hashing (`harness/generate_release_manifest.py`), 35 connected-runtime mutations and positive-control injections already exist and are evidenced in `docs/evidence/k1-dm-080-software-trust-f2f19a1.md`.
- C corrected: control authority is the RT1062 (`AGENTS.md`, `HARNESS_RULES.md` rule 11). The earlier draft put the table on the S3 side — wrong. The S3 only carries a build-time generated schema blob.
- B corrected: the 12.8 kHz port and parity vectors already exist in-repo (`core/audio/`, `test/fixtures/*.golden.jsonl`, `native_*_parity` environments). B no longer rebuilds them; it adds the 24 kHz differential and the Emotiscope oracle.
- Documentation for wire formats goes in `contract/` (repo convention), not `docs/protocol/` (does not exist here).

**Common rules already inside each brief:** run `.claude/harness/init.sh` first; the brief names the active feature-list item; behaviour changes enter `docs/plans/deferred-upgrade-register.md` before code; no hardware; no new guard macros or timing scaffolding; British English; stop report in the repo's format.

Suggested launch order: C and B in parallel → D.
