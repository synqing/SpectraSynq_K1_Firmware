---
abstract: "Canon from the 2026-08-11/12 Unit 2 AP recovery. THE LAW: on a shared bench, a measurement is worthless unless the build answering the port is pinned before AND after it. Every failure this session was a verification gap, not a knowledge gap — the answers already existed in canon, in unmerged commits, and in a forensics doc six days old. Encodes HF-29..HF-40, the failure taxonomy with evidence, and the machinery (k1_device_identity_guard.py, k1-flash-verified.sh, k1-session-preflight.sh) that makes each one mechanical rather than remembered."
---

# Session Canon — 2026-08-12: Device Evidence Integrity

**Companion to** `SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md` (joint silence gate)
and the `k1-vj-session-discipline` skill. That canon says *what* the gate should be. This one
says *how to know your measurement of it is real*.

---

## THE LAW

> **On a shared bench, a number is not evidence. A number plus a pinned build identity is
> evidence. Everything else is a plausible value of unknown provenance — which is worse than
> no value, because it gets acted on.**

Corollary, and the thing that actually cost this session:

> **Every failure below was a verification gap, not a knowledge gap.** The gain revert existed
> (`395116f`). The peakiness gate existed (`248ec79`). "RMS cannot separate music from this
> room's noise floor" was written down on 2026-08-06 in `FINDING-rms-cannot-separate.md`. The
> joint composition was canon on 2026-08-07. The crash fix existed (`622997b3`). **None of it
> was merged, and all of it was re-derived the hard way.** Doctrine-as-prose does not hold:
> `HF-3` ("prefer SSL-relative over absolute magic numbers") was read by the agent and violated
> within the hour. Only a mechanical gate holds.

---

## HARD FAIL additions — HF-29 … HF-40

Copy and mark these before any K1 device session. HF-1…HF-28 live in the 08-07 / 08-09 canons.

- [ ] **HF-29 Identity before AND after.** Assert the build answering the port with
      `scripts/regression-harness/k1_device_identity_guard.py` immediately before a measurement
      and again after any event that could reboot it (calibration, flash, reconnect). A single
      pre-check is insufficient: a concurrent session can reflash mid-run.
- [ ] **HF-30 Flash only via `scripts/agent/k1-flash-verified.sh`.** Never bare
      `pio run --target upload`. The harness refuses a dirty tree, pins identity after the
      write, and emits the registry deployed-state line.
- [ ] **HF-31 Deployed state is part of the flash.** If the registry row was not updated, the
      flash is not finished. Twelve flashes in one prior lane recorded zero.
- [ ] **HF-32 Search before deriving.** Before deriving any constant, threshold or fix, grep
      **all branches** for it: `git log --all -S '<symbol>'`. On this repo the answer has
      existed unmerged five times out of five.
- [ ] **HF-33 Branch from current `origin/main`.** A branch off a stale base silently omits
      crash fixes. This session boot-looped a bench device because the branch predated
      `622997b3`.
- [ ] **HF-34 Verify BOTH directions.** A silence gate must be shown to wake on music **and**
      go dark in quiet, in the same run. Either alone is satisfiable by a broken gate: a floor
      set impossibly high passes the quiet test and fails music; zero does the reverse. This
      session produced both failure modes, in that order, each looking like success.
- [ ] **HF-35 Sweep the operating range.** A threshold derived at one playback volume is not
      derived. `frac=4.0` from volume 70 cleared **2 frames of 26** at volume 40 — surviving on
      the dwell latch alone. The sweep corrected it to 2.5.
- [ ] **HF-36 Witness DURING, not before.** The acoustic path must be measured concurrently
      with the stimulus by an independent microphone. Witnessing silence beforehand and
      assuming playback worked voided a full music leg (the Bose had disconnected; playback
      went to laptop speakers).
- [ ] **HF-37 Re-resolve device indices every run.** `ffmpeg -f avfoundation` audio indices
      shift when Bluetooth devices connect or drop. A hardcoded `:1` silently pointed at the
      speaker's own microphone and produced a flat 1.3 dB reading during loud music.
- [ ] **HF-38 Guards need their own negative control.** A guard is code and carries bugs. This
      session's acoustic-path guard read `music > quiet - 10` where dB requires `+ 10`; it
      aborted a valid leg. Inverted, the same error accepts a starved path silently. Test that
      a guard REJECTS a known-bad input, not only that it accepts a good one.
- [ ] **HF-39 "multiple access on port" means STOP.** pyserial's
      `device disconnected or multiple access on port` is the only warning you get that another
      process owns the device. Reading only the first half of that sentence cost forty minutes
      of contaminated evidence.
- [ ] **HF-40 A calibration belongs to the build that learned it.** SSL and DC_OFFSET are
      meaningless across a gain change, a mic-identity change or a pin-map change. Re-learn
      after any of them, under the firmware that will use it, with identity pinned either side.

---

## Failure taxonomy — what happened, and the mechanical fix

| # | Failure | Evidence | Mechanical fix |
|---|---|---|---|
| 1 | Concurrent session reflashed the device mid-measurement, twice | 40 min of calibration + distributions taken against `k1_custom_silicon_closure @ 622997b` (gain 4.0f, pins 13/12, no gate); later `1c647e79 / k1_custom` | `k1_device_identity_guard.py` — caught the second occurrence in one call |
| 2 | Deployed state never recorded | 12 flashes, zero registry updates; registry claimed a firmware that was not on the device | `k1-flash-verified.sh` emits the row as flash output |
| 3 | Existing fixes re-derived from scratch | `395116f`, `248ec79`, `FINDING-rms-cannot-separate.md`, canon 08-07, `622997b3` — all unmerged, all rediscovered | HF-32 + preflight `git log --all -S` sweep |
| 4 | One-directional verification | Peakiness alone: music woke, quiet false-woke 92.6% of frames. Absolute floor: quiet went dark, music stopped waking | HF-34 + paired predictions P1/P2 written **before** the run |
| 5 | Single-point derivation | `frac=4.0` at volume 70 only; 2/26 frames at volume 40 | HF-35 volume sweep |
| 6 | Absolute magic number where a ratio was required | `K1_SILENCE_PEAK_MIN_RAW = 500.0f` survived exactly one recalibration | HF-3 (08-07) — now with a worked counter-example |
| 7 | Acoustic path assumed, not measured | Bose disconnected; "music" played to laptop speakers; K1 `max_raw` 548 vs 5051 | HF-36 witness during |
| 8 | Witness pointed at the wrong device | BT reconnect shifted ffmpeg index; `:1` became the speaker's mic | HF-37 re-resolve indices |
| 9 | Guard with an inverted comparison | `music > quiet - 10` | HF-38 negative control |
| 10 | Stale branch base omitted a crash fix | Bench boot-looped: `StoreProhibited`, `rst:0xc` ×27, safe-mode null LED buffers | HF-33 + preflight base check |
| 11 | Second-hand facts asserted as verified | "IM73D misflash is back" — asserted from an agent's env chain; that worktree had retargeted to IM69D | Read the file, quote file:line |
| 12 | Subagents returning idle without delivering | 3 of 6 agents signalled available with no result; one never delivered until chased | Chase once, then own it — orchestration doctrine already covers this |

---

## Machinery now in the repo

| Path | Enforces |
|---|---|
| `scripts/regression-harness/k1_device_identity_guard.py` | HF-29, HF-39. Refuses to proceed unless git/env/epoch match. Tests assert it **rejects** the real foreign `BUILD:` line, plus an anti-tautology case. |
| `scripts/agent/k1-flash-verified.sh` | HF-30, HF-31. Dirty-tree refusal → build → pre-identity → flash → post-identity (exit 3 on mismatch) → registry row. |
| `scripts/agent/k1-session-preflight.sh` | HF-32, HF-33. Stale-base check against `origin/main`; unmerged-work sweep for the symbols about to be touched. |
| `tests/test_k1_serial_safety.py` | 64 of 152 typed serial commands are destructive-and-persisting with query-shaped names (`led_count`, `sample_rate`, `mirror_enabled`, `silence_enter`). Drift-guarded allowlist. |

---

## Findings that are product truth, not process

1. **RMS cannot separate music from a room's noise floor, in any gain domain.** Measured:
   music median `rms_raw` 0.0027 vs quiet room 0.0072 — music's median is *lower*. No level
   threshold on that statistic separates them. Three successive gain cuts (16→8→4) each traded
   one failure for the other and neither stayed fixed.
2. **The gain ladder was aimed at a dead symbol.** `threshold_loud_break = SSL × 1.20` has
   **zero read sites**; it gated nothing and was later deleted. Gain was halved twice to move a
   number that did nothing.
3. **Crest and level are complementary and BOTH are required.** Measured on Unit 2: 42% of
   quiet frames cleared the peakiness threshold unaided, and silence still held 100% because
   the level term rejected every one. Peakiness alone false-wakes; level alone cannot tell
   music from a transient.
4. **`SSL` is a subtractive term AND a divisor floor** (`i2s_audio.h:702`, `:708`, `:719`,
   `:735`): `drive = clamp0(peak − SSL) / max(follower, SSL)`. Everything below SSL is
   annihilated, not attenuated.
5. **The joint fraction is per-unit/per-room and must be derived, not inherited.** Canon's 1.25
   (bench `B489A500`) does not transfer to Unit 2. Whether that is environmental or hardware is
   **still open** — bench and Unit 2 run identical AP code, gain and cadence, differing only in
   LED count (160 vs 206), capsule (LEFT vs RIGHT) and PDM pins. Candidate mechanisms in order
   of suspicion: **LED current coupling into the mic supply rail** (206 px is ~29% more current
   on the noisiest rail), capsule sensitivity, trace routing.

---

## Still open

- The bench-vs-Unit-2 transfer test (item 5 above). Both devices are now on matching builds;
  the bench needs a calibration under its own firmware, then the same quiet/music legs.
- Eyes-on. Every result in this lane is telemetry. Nobody has looked at the lamp.
- The canon amendment to `SESSION_CANON_2026-08-07` (frac is per-unit) lands when this branch
  merges — that file postdates this branch's base.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-12 | agent:claude-code | Created. Encodes HF-29…HF-40, the twelve-failure taxonomy with evidence, the machinery that makes each mechanical, and the five product-truth findings from the 2026-08-11/12 Unit 2 AP recovery. |
