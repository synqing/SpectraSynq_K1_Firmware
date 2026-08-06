# IM69D130 Dual-Mic Bring-up — State of Play & Phased Recovery Plan (2026-08-06)

> **Status:** orientation document. Written from an orchestrator re-verification pass on
> 2026-08-06. Every claim below is either marked **[VERIFIED]** (re-run against the live
> checkouts on this date) or **[UNVERIFIED]** (carried forward from earlier prose, not
> re-confirmed). Do not treat unverified lines as licence to act.
>
> **Prior authority:** [`docs/hardware/im69d130-dual-mic-eval-design-2026-08-05.md`](./im69d130-dual-mic-eval-design-2026-08-05.md)
> remains the design authority for Goals B and C. This document only records *where the
> work physically is* and *how to get it somewhere safe*.
>
> **No flash, no erase, no serial-write without explicit Captain approval.** Nothing in
> this plan authorises touching a device.

---

## 1. Ground truth (verified 2026-08-06)

### 1.1 Main checkout

`/Users/spectrasynq/SpectraSynq_K1_Firmware`

| Fact | Value | State |
|---|---|---|
| Branch | `feat/ap-advice-phase0-im69d-gain8` | [VERIFIED] |
| HEAD | `db300db` | [VERIFIED] |
| Working tree | dirty — ~14 modified plus untracked BLE/deck docs | [VERIFIED] |
| `.git/index.lock` | **PRESENT**, 0 bytes, Aug 6 20:37 | [VERIFIED] |
| Worktrees registered | 22 | [VERIFIED] |
| Stashes | `stash@{0}` this branch · `stash@{1}` p2-e2e · `stash@{2}` ws2816 ambient-drift | [VERIFIED] |

The zero-byte `index.lock` blocks **all git write operations in main** (`add`, `commit`,
`stash`, `checkout`). Plain file writes into the working tree still succeed. It is a
stale lock from an interrupted process, not a running git operation — but confirm no git
process is live before removing it (§3, P0.4).

### 1.2 vj-lane worktree — the thing at risk

`/private/tmp/claude-501/-Users-spectrasynq-SpectraSynq-K1-Firmware/d02156cf-f33e-4d37-a6e6-cec9fd00f850/scratchpad/vj-lane`

| Fact | Value | State |
|---|---|---|
| Branch | `lane/k1-vj-ble-deck8` | [VERIFIED] |
| HEAD | `0ceddeb` | [VERIFIED] |
| Uncommitted | 4 files, **+82 / −10** | [VERIFIED] |
| `origin/lane/k1-vj-ble-deck8` | **DOES NOT EXIST** | [VERIFIED] |

Uncommitted, tracked:

- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h` (+30 / −3)
- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h` (+10 / −0)
- `SPECTRASYNQ_K1_FIRMWARE/system/constants.h` (+33 / −7)
- `platformio.ini` (+9 / −0)

Uncommitted, untracked (build and serial logs — **do not commit unless Captain asks**):
`ap_full.log`, `b1.log`, `b2.log`, `baseline_build.log`, `bld.log`, `bld2.log`,
`boot_banner.log`, `control_readback.log`, `g1.log`, `postfix_readback.log`,
`pytest.log`, `readback.log`, `secondary_check.log`, `upload.log`.

What the four dirty files actually carry [VERIFIED by diff read]:

1. **`K1_MIC_IM69D_INPUT_GAIN 8.0f`** — reverting the 2026-08-05 halving to G=4. The
   rationale recorded in the diff: the G=4 step was justified by `threshold_loud_break`,
   a value assigned once and never read; SSL floor margin is 2.2× at G=8 vs 1.47× at G=4.
2. **Noise-cal admission corridor** — `NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW 1400.0f` and
   `NOISE_CAL_SSL_MAX_VALID_RAW 1540U`, with the boundary argument that the comparison is
   strict (`>`) so 1400 × 1.10 = 1540 still accepts. `PHASE_B_MAX` deliberately left at
   base; the ratio gate `NOISE_CAL_SSL_MAX_P90_TO_P50_RATIO` (2.50) is flagged as the
   only gain-invariant guard and marked *not to be widened*.
3. **Silence PEAKINESS discriminator** — `K1_SILENCE_PEAK_WIN 64` (~0.48 s at 133 Hz) and
   `K1_SILENCE_PEAKINESS_BREAK 2.10f`, a peak-to-mean ratio that may only *break* silence,
   never cause it. Backed by bench measurement (quiet 1.24 vs music 3.17) and by the
   finding that music's median RMS is *lower* than the room floor's, so no level
   threshold can work. Also adds `pky=%.2f` to the `[AP]` telemetry line.
4. **`-fno-finite-math-only`** in `platformio.ini`, ordered after `-ffast-math`. The diff
   comment claims 93 `isfinite`/`isnan`/`isinf` call sites across 42 files were being
   folded to constants and thus deleted from the binary.

Committed tip chain (local only): `c9c459b` → `e4a1288` → `7034362` → `f670ffc` →
`eaa4492` → `0ceddeb`. [VERIFIED]

### 1.3 Forensics directory — also at risk

`/private/tmp/claude-501/-Users-spectrasynq-SpectraSynq-K1-Firmware/d02156cf-f33e-4d37-a6e6-cec9fd00f850/scratchpad/im69d-forensics`

12 files [VERIFIED]: `FINDING-rms-cannot-separate.md`, `FINDING-stashed-cadence.md`,
`ambient_rms_20s.log`, `music_capture_45s.log`, `music_pky_capture.log`,
`orchestrator-verified-core.md`, `ssa1-constants.md`, `ssa2-cadence.md`,
`ssa3-timeline.md`, `ssa4-redteam-VERIFIED.md`, `w1-calgates.md`, `w4-w6-drafts.md`.

This directory is **not** inside any git worktree. It has no version control at all.

### 1.4 What is good

- The audio-stack reasoning is written down *in the code*, not only in chat. The four
  dirty files carry their own measured justification and revert instructions.
- The forensics pack is substantial and includes a red-team pass marked VERIFIED.
- Stage 1 mono bring-up is functionally done. [UNVERIFIED on this date — carried forward]
- No device has been flashed with any of this.

### 1.5 The two fires

1. **NO_REMOTE_LANE.** `origin/lane/k1-vj-ble-deck8` does not exist. Six commits plus 82
   uncommitted lines of measured audio work exist on exactly one filesystem, under
   `/private/tmp`. A reboot, a tmp reaper, or a `git worktree prune` loses all of it.
2. **INDEX_LOCK in main.** Main cannot accept a git write. Any recovery that routes
   through main is blocked until the lock is cleared.

---

## 2. Map–territory deltas

Corrections to earlier prose. These matter because acting on the stale map wastes the
Phase 0 window.

| Earlier claim | Verified reality | Consequence |
|---|---|---|
| "The lane just needs pushing" | **`origin/lane/k1-vj-ble-deck8` does not exist.** Nothing has ever been pushed. | Strictly worse than "behind remote". There is no remote copy to fall back on. First push must create the branch. |
| "The PEAKINESS gate is in main" | **Absent.** A repo-wide search for `PEAKINESS` and `fno-finite-math-only` in main returns nothing. The only `peakiness` hits are unrelated lowercase comments in `k1_musical_saliency.cpp` and `k1_audio_snapshot.cpp`. | The gate is **uncommitted, in the lane worktree only**. Do not assume main protects anything. |
| "The forensics are safe" | **Also under `/private/tmp`**, and not in any git worktree. | Both the worktree *and* the forensics share one reboot-loss failure mode. Phase 0 must preserve both. |
| "Main is clean enough to work in" | Main is dirty (~14 modified) **and** git-locked. | Main cannot be the staging ground. Preserve from the lane outward. |
| "The dirty main files are part of this lane" | They are **BLE/deck documents — a separate workstream**. | Do not sweep them into an audio-stack commit. See §5. |

---

## 3. Phase 0 — PRESERVE

**Objective:** get every byte of unique work onto a durable, addressable surface before
anything else is attempted. No refactoring, no cleanup, no rebasing, no squashing.

**Precondition:** nothing here requires main's git. Do P0.1–P0.3 *before* touching the
lock.

### P0.1 — Push the lane branch to origin (creates the branch)

```
cd /private/tmp/claude-501/-Users-spectrasynq-SpectraSynq-K1-Firmware/d02156cf-f33e-4d37-a6e6-cec9fd00f850/scratchpad/vj-lane
git push -u origin lane/k1-vj-ble-deck8
```

This publishes the six committed commits through `0ceddeb`. It does **not** save the 82
uncommitted lines — that is P0.2. Do this first anyway: it is one command and it removes
the worst of the exposure.

### P0.2 — Commit the four dirty tracked files, then push

Four atomic commits, in this order. Tracked files only — **stage by explicit path, never
`git add -A`**, or the fourteen log files come with it.

```
git add SPECTRASYNQ_K1_FIRMWARE/system/constants.h
git commit -m "fix(audio): revert IM69D input gain to 8.0f on SSL floor margin"

git add SPECTRASYNQ_K1_FIRMWARE/system/constants.h
git commit -m "fix(cal): pin the IM69D noise-cal admission corridor at G=8"

git add SPECTRASYNQ_K1_FIRMWARE/system/globals.h SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h
git commit -m "feat(audio): add gain-invariant peakiness break to the silence gate"

git add platformio.ini
git commit -m "fix(build): stop -ffast-math folding away every isfinite guard"
```

Commits 1 and 2 both touch `constants.h`. Split them with `git add -p`, or accept a
single combined commit if the interactive split is not clean — **preservation beats
commit hygiene here**. If splitting stalls for more than a couple of minutes, commit
`constants.h` once with the first message and note the merge in the body.

Then:

```
git push
```

> The pre-commit gate normally demands pytest plus a build for firmware changes. These
> are preservation commits on a local-only, non-shippable lane branch, not a promotion.
> If the gate blocks, escalate to Captain rather than bypassing silently — record the
> decision either way.

### P0.3 — Get the forensics pack out of `/tmp`

The 12 files have no version control. Copy them to a durable location under the repo
(suggested: `docs/forensics/im69d130-bringup-2026-08-06/`) in the lane worktree, then:

```
git add docs/forensics/im69d130-bringup-2026-08-06
git commit -m "docs(forensics): preserve the IM69D bring-up evidence pack"
git push
```

The three `.log` captures (`ambient_rms_20s.log`, `music_capture_45s.log`,
`music_pky_capture.log`) are the raw measurement substrate behind every threshold in
P0.2 — they are evidence, not build noise, and should be kept. The fourteen build/serial
logs in the worktree root are build noise and should **not** be committed.

### P0.4 — Clear the stale `index.lock` in main

Only after P0.1–P0.3 are pushed.

```
ps aux | grep -i "[g]it" # confirm no live git process
ls -la /Users/spectrasynq/SpectraSynq_K1_Firmware/.git/index.lock
rm /Users/spectrasynq/SpectraSynq_K1_Firmware/.git/index.lock
cd /Users/spectrasynq/SpectraSynq_K1_Firmware && git status
```

A zero-byte lock with a timestamp of 20:37 and no owning process is stale. If any git
process *is* live, stop and report — do not remove the lock underneath it.

### Phase 0 exit criteria

- [ ] `git ls-remote --heads origin lane/k1-vj-ble-deck8` returns a SHA.
- [ ] `git status --porcelain` in the lane shows no modified **tracked** files.
- [ ] The 12 forensics files exist under a committed, pushed path inside the repo.
- [ ] `git status` in main succeeds.
- [ ] Nothing was flashed. Nothing was rebased. No log files were committed.

---

## 4. Phases 1–5

Each phase is gated on the previous one's exit criteria. Do not run them concurrently.

### Phase 1 — Prove

Establish that the preserved lane still builds and that the four changes behave as their
comments claim.

- Build the relevant env via `bash scripts/agent/pio-build.sh <env>` (the wrapper rejects
  upload/monitor tokens).
- Run the host gate: `pytest tests/`.
- Confirm `-fno-finite-math-only` actually restores the guards: verify at least one
  previously-folded `isfinite` site now generates a real test in the disassembly. The
  "93 call sites across 42 files" figure is **[UNVERIFIED]** — it comes from the diff
  comment and has not been independently recounted.
- The peakiness measurements (quiet 1.24, music 3.17) are **[UNVERIFIED]** here; they
  originate in the forensics pack and were not re-derived in this pass.

**Exit:** build green, pytest green, at least one guard-restoration observation recorded.

### Phase 2 — Freeze the corridor

Lock the admission corridor so later work cannot silently drift it.

- Add a static ratchet test asserting `TRUSTED_P90 = 1400`, `MAX_VALID = 1540`,
  `PEAKINESS_BREAK = 2.10f`, `PEAK_WIN = 64`, and `INPUT_GAIN = 8.0f`, each with a
  pointer to the measurement that set it.
- Explicitly assert that `NOISE_CAL_SSL_MAX_P90_TO_P50_RATIO` is unchanged at 2.50 — the
  diff comments name it the only gain-invariant guard and mark it not-to-be-widened.
- Note that `0ceddeb` already claims a static ratchet for the 2026-08-06 defect classes;
  check for overlap before adding a second one.

**Exit:** a failing-if-drifted test exists and passes.

### Phase 3 — Remediation

Pay the debts the preservation commits deliberately deferred.

- **Perf gate owed on `-fno-finite-math-only`.** Re-enabling NaN/Inf awareness is not
  free on the Core-0 hot path. Measure and record the audio-frame cost against the
  133 Hz budget before this flag goes anywhere near a shippable env. This is a hard
  obligation, not a nice-to-have.
- Reconcile the peakiness path with the existing lowercase `peakiness` logic in
  `k1_musical_saliency.cpp` / `k1_audio_snapshot.cpp` — confirm they are genuinely
  unrelated and not two competing notions of the same thing.
- Decide the fate of the fourteen untracked build/serial logs: delete or gitignore.

**Exit:** perf number recorded; no duplicate/contradictory peakiness concept; worktree
clean of stray logs.

### Phase 4 — Untangle

Separate the two workstreams that are currently entangled across two checkouts.

- Main's ~14 dirty files plus untracked BLE/deck docs land on their own branch (see §5).
- The lane branch keeps the audio stack only.
- Audit the 22 registered worktrees; prune the dead ones. Anything under `/private/tmp`
  that holds unique work gets the P0.1–P0.3 treatment before pruning.
- Triage the three stashes: `stash@{0}` (this branch), `stash@{1}` (p2-e2e),
  `stash@{2}` (ws2816 ambient-drift). Apply, discard, or convert to branches — do not
  leave them as a third unlabelled loss surface.

**Exit:** one branch per workstream; worktree count justified; stash list empty or
each entry deliberately retained with a written reason.

### Phase 5 — Resume Goals B and C

Only now return to the original design authority,
`im69d130-dual-mic-eval-design-2026-08-05.md`.

- **Goal B** — A/B evidence, IM69D130 vs IM73D122 (design §6). Comparator metric is raw,
  pre-conditioning only.
- **Goal C** — dual-mic / stereo (design §5), including the stereo hypothesis and its
  kill criterion.
- **Clock band** — the clock-rate blocker at design §2.5 is still open and still a
  prerequisite for stereo.
- **Promotion** — the non-shippable bench env must not become shippable without the
  developer-instrumentation boundary check and the perf gate from Phase 3.

**Exit:** as defined in the eval design document, not here.

---

## 5. Workstream separation

There are **two** unrelated bodies of work in flight, in two different checkouts:

| | Main checkout | vj-lane worktree |
|---|---|---|
| Branch | `feat/ap-advice-phase0-im69d-gain8` @ `db300db` | `lane/k1-vj-ble-deck8` @ `0ceddeb` |
| Dirty content | ~14 modified + untracked **BLE / deck docs** | 4 files, **audio stack** |
| Risk | git-locked; on a normal filesystem | local-only; under `/private/tmp` |

**Do not mix them.** A commit that contains both BLE-deck documentation and the noise-cal
corridor is unreviewable and unrevertable. The temptation during Phase 0 will be to
"clean up while we're here" — resist it. Preservation commits touch the four named audio
files and the forensics pack, nothing else.

The branch name `lane/k1-vj-ble-deck8` is itself misleading: the branch now carries the
audio stack, not just the VJ/BLE deck work. Renaming is a Phase 4 concern, not a Phase 0
one — **do not rename before the branch exists on origin**.

---

## 6. Standing constraints

- **No flash, erase, or serial-write without explicit Captain approval.** Consult
  `docs/hardware/device-build-registry.md` before any device operation. 1401 (chip
  `F887A500`) takes `k1_hardware` only; 12201 (chip `B489A500`) takes
  `k1_bench_reference` only. Never cross-flash.
- **No `start_noise_cal` without confirmed silence.** Every threshold in P0.2 derives
  from calibration behaviour; a bad cal contaminates the evidence base.
- **Build only via `bash scripts/agent/pio-build.sh <env>`.**
- **Perf gate is owed on `-fno-finite-math-only`** before it reaches any shippable
  environment (Phase 3). Treat the flag as provisional until that number exists.
- **Do not widen `NOISE_CAL_SSL_MAX_P90_TO_P50_RATIO`.** It is the only gain-invariant
  guard in the corridor.
- **Do not commit build or serial logs** without an explicit request.

---

## 7. Verification record

Re-run these to confirm the state described above still holds:

```
# Lane
cd /private/tmp/claude-501/-Users-spectrasynq-SpectraSynq-K1-Firmware/d02156cf-f33e-4d37-a6e6-cec9fd00f850/scratchpad/vj-lane
git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD
git status --porcelain && git diff --shortstat
git ls-remote --heads origin lane/k1-vj-ble-deck8   # empty output = NO_REMOTE_LANE

# Forensics
ls /private/tmp/claude-501/-Users-spectrasynq-SpectraSynq-K1-Firmware/d02156cf-f33e-4d37-a6e6-cec9fd00f850/scratchpad/im69d-forensics

# Main
ls -la /Users/spectrasynq/SpectraSynq_K1_Firmware/.git/index.lock
cd /Users/spectrasynq/SpectraSynq_K1_Firmware && git rev-parse --abbrev-ref HEAD
```

Verified on 2026-08-06 by an orchestrator re-run. Items marked **[UNVERIFIED]** were not
re-derived and must be confirmed before they are relied upon.
