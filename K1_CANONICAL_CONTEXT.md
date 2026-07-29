# K1 Canonical Context — READ FIRST

_Auto-deployed 2026-07-15 across all K1 project folders. Every line is one mistake an agent won't repeat. If this file and a local doc disagree on the facts below, this file is authoritative for canonical identity; the repo's own `AGENTS.md`/handoff wins for that repo's current lane status._

## 1. Canonical identity (prevents the "which K1?" / wrong-repo error)
- **The product firmware is `/Users/spectrasynq/SpectraSynq_K1_Firmware`.** This is the ONLY shipping firmware lineage.
- **If you are reading this in any other folder, you are in a variant, experiment, or support repo — NOT the product.** Do not assume a variant (`K1.reinvented`, `K1.Genesis`, `K1.Lightwave*`, `K1.node*`, `PRISM.k1`, `K1.esp32s3*`, the many `K1.*` experiments, etc.) is canonical.
- **DEAD lineage:** `Workspace_Management/Software/Lightwave-Ledstrip/firmware-v3` — pre-pivot; good analyzers excluded from its build, downbeat is a fake mod-4 counter. Do not read, index, or edit it. clangd + QMD were repointed to the canonical repo on 2026-07-13.

## 2. Production hardware
- **Microphone = IM73D122 (PDM), canonical as of 2026-07-15.** `k1_prod_im73d` is the shipping env. **SPH0645 is legacy.** Every measurement taken before 2026-07-15 is on SPH hardware = a *legacy* baseline; re-base on IM73D before trusting it.
- MCU: ESP32-S3 (canonical firmware). Dual-core: Core 0 hard-real-time audio, Core 1 render.

## 3. Audio-DSP ground truth (don't re-derive committed work)
- **Onset** (log-spectral-flux + median-adaptive + per-band) and **chord/chroma** (semitone fold, 98.4% conf) **WORK** and are committed. Do not rewrite.
- **Tempo winner-selection is the one open gap.** The harmonic-comb ACF salience + log-Gaussian tactus prior (centre 88, σ0.75) + parabolic sub-lag are **committed**; the tactus prior sits on a documented robustness plateau — **do not re-tune it.**
- **Device gate CLOSED (2026-07-15, IM73D):** six 126–135 BPM EDM tracks → Acc1 100%, octave-error 0%, lock-fraction ~44–47%. Device novelty is *cleaner* for tempo than host-clean. **Open lane:** lock-occupancy on *human-phrased* 120–140 material (pop/funk/hip-hop). Frame budget fits (p95 6.9 ms vs 7.5 ms).
- Automatable loop for this gap: `SpectraSynq_K1_Firmware/scripts/loop/` (tempo_loop.py + program.md) — host-replay only; device stays hardware-gated.

## 4. Memory corrections (false facts to stop repeating)
- **`BeatTracker.cpp` is DEAD CODE, not "corrupted by parallel agents."** Intact (~375 lines); `update()` is never called. Correct this claim wherever it recurs in older docs.

## 5. Credentials & accounts (prevents the auth dead-ends)
- **The X (Twitter) API and xAI/Grok are different products.** An `xai-…` key NEVER authenticates the X API — that needs an `AAAA…` X Developer **Bearer Token**.
- The working X account/token/credit live in **`~/Agent-Reach`** (handle `@qaz1880`, app `32515044`) — see `~/X_API_PROJECT_POINTER.md`.
- `~/Agent-Reach` is **git local-only (no remote)** — back it up; it holds credentials + the KOL pipeline + the Hawley dossier.

## 6. Installed agent capability (use it)
- **`thinking-toolkit`** — 24 reasoning skills + an auto-router (second-order, pre-mortem, inversion, red-team, first-principles, TRIZ, Bayesian, debiasing, Cynefin, systems, OODA, theory-of-constraints, reversibility, expected-value, steel-manning…).
- **`context-engineering`** — `context-stack` (load global→AGENTS.md→memory→files→state→success-criteria before acting) + `loop-engineering` (verifier-gated agentic loops).
- Reference: the Context Engineering Playbook (War Room `03-Knowledge/AI-Infrastructure`).

## 7. Working discipline
- **Load context before acting** (context-stack): read this file + the repo's `AGENTS.md`/handoff + memory first. On-disk handoff beats memory for current lane status.
- **Cost-gate any live API run** (X API is pay-per-use; write objective + spend cap + stop rule first).
- **British English** in comments/docs (centre, colour, initialise).

## 8. Lineage traps (2026-07-29 session canon — do not re-discover)

Full oracle: **`docs/agent/K1_LINEAGE_AGENT_ORACLE.md`** (mirror of Lightwave `instructions/k1-lineage-agent-oracle.md`).

| Trap | Rule |
|------|------|
| "Latest build" ambiguity | Three answers: (A) product env `k1_hardware`, (B) `git log origin/main`, (C) on-device via `read_mac` + registry + `:build` |
| Wrong repo | `Lightwave-Ledstrip/firmware-v3` is **dead donor** — read-only for WB-4 harvest; **this repo** is the only shipping lineage |
| USB port ≠ device | Always `esptool read_mac` before flash (main `F887A500`, bench `B489A500`) |
| Framework paste | Never paste `RenderContext`/`ControlBus`/actor model — port via `light_mode_*` + `K1AudioContext` |
| Rejected migrations | No invented families (2026-07-10), no waveform-scroll clones, binned gems 30/31/33, blocked `0x0E06`/`0x1B04` |

**Preflight (Lightwave monorepo):** `Lightwave-Ledstrip/tools/k1-lineage-preflight.sh`  
**Preflight (this repo):** `bash scripts/agent/session-bootstrap.sh`

---
_Reversible: this file was added, not merged into your existing docs. Delete `K1_CANONICAL_CONTEXT.md` to remove it. Generated by the SpectraSynq context-engineering deployment, 2026-07-15. §8 added 2026-07-29._
