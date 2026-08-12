---
abstract: "Handover for the K1 Unit 2 IM69D silence-gate lane as of 2026-08-12. Branch fix/im69d-rms-gate-and-gain-20260811 (14 commits, pushed, unmerged). Unit 2 and bench are on DIFFERENT builds — Unit 2 lacks the null-guard crash fix and must be reflashed first. Three tasks open: the bench-vs-Unit2 transfer test, eyes-on, and the merge. Read this, then SESSION_CANON_2026-08-12_device_evidence_integrity.md, then run the preflight."
---

# Handover — IM69D silence gate, Unit 2

**Date:** 2026-08-12 · **Branch:** `fix/im69d-rms-gate-and-gain-20260811` · 14 commits, pushed, **unmerged**
**Worktree:** `.worktrees/im69d_gate_fix` · **Base:** `55ae1d5` (origin/main has since moved)

---

## Read in this order. It is short on purpose.

1. **This file** — state and next actions.
2. `docs/canon/SESSION_CANON_2026-08-12_device_evidence_integrity.md` — HF-29…HF-40 and *why*.
   Non-optional: it is the difference between a measurement and a plausible number.
3. `docs/forensics/unit2-joint-silence-predictions-2026-08-11.md` — the measured distributions
   and the P1–P5 results.
4. `docs/canon/SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md` (on `main`, not this
   branch) + the `k1-vj-session-discipline` skill — HF-1…HF-13 and the joint-gate design.

Then, before touching anything:

```
bash scripts/agent/k1-session-preflight.sh K1_SILENCE_JOINT_LEVEL_SSL_FRAC K1_SILENCE_PEAKINESS_BREAK
```

---

## FIRST ACTION — the two devices are NOT on the same build

| Device | Chip | Port | Running | Gap |
|---|---|---|---|---|
| **Unit 2** | `0C54FC00` | `cu.usbmodem1101` | `3a6098a` (frac 2.5) | **Lacks the null-guard crash fix `5703a895`** |
| **Bench K1v2** | `B489A500` | `cu.usbmodem12201` | `5703a895` | Has it. **Calibration is stale/unknown.** |

Unit 2 has not crashed because it has never entered safe mode — but it carries the same latent
`StoreProhibited` boot-loop that took the bench down. **Reflash Unit 2 before measuring it:**

```
bash scripts/agent/k1-flash-verified.sh k1_unit2_im69d_right --port /dev/cu.usbmodem1101
```

Its calibration (`SSL=136`, learned under `4d54f34`) stays valid — same gain, same slot, same
pins. Only re-calibrate if you change gain, mic identity or pin map (HF-40).

Also on the bench: `cu.usbmodem12401` is a **Tab5**, not a K1. `cu.usbmodem1401` is the main K1
(`F887A500`). Neither belongs to this lane.

---

## What this lane established (do not re-derive — five things already were)

- **RMS cannot separate music from a room's noise floor, in any gain domain.** Music's median
  `rms_raw` is *lower* than a quiet room's (0.0027 vs 0.0072). Measured `rms_raw` never exceeded
  0.0386 against an EXIT threshold of 0.08 at any volume — **the legacy RMS Schmitt never fires.**
- **The 16→8→4 gain ladder was aimed at a dead symbol.** `threshold_loud_break = SSL × 1.20` has
  zero read sites and was later deleted. Gain was halved twice to move a number that did nothing.
- **Crest AND level, both required.** 42% of quiet frames clear the peakiness threshold unaided;
  silence still holds 100% because the level term rejects them. Neither axis alone works.
- **`SSL` is subtractive *and* a divisor floor** — `drive = clamp0(peak − SSL) / max(follower, SSL)`.
  Below SSL is annihilated, not attenuated.
- **The joint fraction is derived per unit/room, never inherited.** Canon's 1.25 (bench) does not
  transfer to Unit 2, where it is **2.5**.

Current verified behaviour on Unit 2 (`3a6098a`, SSL=136): quiet **100% silence, `silent_scale`
0.00**; music **0% silence, 1.00** at volume 40; still wakes at volume 30. P1/P2/P3/P5 all pass.

---

## Open task 1 — the transfer test (Captain's standing question)

**The question:** bench and Unit 2 run *identical* AP code, gain and cadence. They differ only in
LED count (160 vs 206), capsule (LEFT vs RIGHT) and PDM pins (14/13 vs 39/38). So why is the
derived fraction different (1.25 bench vs 2.5 Unit 2)? Captain's position is that it should
transfer, and the evidence leans his way: Unit 2's quiet is *peakier* (2.08 vs canon 1.24) and its
music *less* peaky (2.41 vs 3.17) — a signature that reads as room and source, not silicon.

**Procedure** (both devices are already staged for it):
1. Reflash Unit 2 (above) so both are on the same SHA.
2. Calibrate the bench under `5703a895` in a witness-verified silent room. Room is quiet by
   standing Captain authority; **verify it with the witness mic anyway** — that is the point of
   the gate (HF-36).
3. Run identical legs on both: quiet 45 s, music vol 40, music vol 55. Witness **during** each
   music leg, and re-resolve the ffmpeg audio index each run (HF-37).
4. Compare `max_raw` distributions **as multiples of each device's own SSL**.

**Interpretation, decided in advance so it cannot be rationalised afterwards:**
- Distributions match → the fraction transfers, the "per-unit" framing is wrong, and the canon
  amendment should say *per-room*, not per-unit. Fix the canon and this branch's comment.
- They do not match → the delta is real. Candidate mechanisms, in order of suspicion:
  **(a) LED current coupling into the mic supply** — 206 px is ~29% more current on the noisiest
  rail, which raises the noise floor, raises SSL and shifts every ratio; **(b)** capsule-to-capsule
  sensitivity; **(c)** PDM trace routing. Discriminate (a) by re-running Unit 2 with
  `LED_COUNT_VALUE` temporarily at 160 — same silicon, same capsule, different current.

That last test is the cheap decisive one and nobody has run it.

---

## Open task 2 — eyes-on

**Every result in this lane is telemetry. Nobody has looked at the lamp.** Per the Sensory Bridge
doctrine, architecture is not success if visual impact regresses. Unit 2 is flashed, calibrated and
waking correctly; this needs Captain's eyes and 30 seconds, and it is the only genuine product
gate remaining.

---

## Open task 3 — merge

- Branch is **based on `55ae1d5`; `origin/main` has moved** (at least to `1c647e79`). Rebase or
  merge forward before the PR — and re-read the incoming commits for further crash/safety fixes
  (that is exactly how `622997b3` was missed and boot-looped the bench).
- **`docs/hardware/device-build-registry.md` will conflict.** This branch edits it; the main
  checkout has an uncommitted edit to the same file from another lane. Resolve deliberately.
- The registry deployed-state row for Unit 2 is currently marked **CONTESTED** — update it to the
  real state once Unit 2 is reflashed. `k1-flash-verified.sh` prints the row for you.
- The `SESSION_CANON_2026-08-07` amendment (fraction is derived, not inherited) is written in the
  2026-08-12 canon and must be appended to the 08-07 file **at merge** — that file postdates this
  branch's base and is not here.
- Same for `.claude/skills/k1-vj-session-discipline/SKILL.md`: the companion pointer text is in
  the 08-12 canon, ready to append.

---

## Traps that have already cost time

| Trap | What happens |
|---|---|
| **Concurrent sessions flash these devices** | Happened twice on 2026-08-11. **16 worktrees** can build and flash. Always pin identity before *and* after a measurement. |
| **Serial needs DTR asserted** | Without it the port returns **zero bytes** and looks like a dead device. Never set `dtr=False` — that is a hardware reset on USB-Serial-JTAG. |
| **`"multiple access on port"`** | pyserial's only warning that another process owns the device. Reading just the first half of that sentence cost 40 minutes. |
| **64 of 152 typed serial commands are destructive** | `led_count`, `sample_rate`, `mirror_enabled`, `silence_enter` all *look* like getters and are persisted setters that reboot. Check `serial_typed_cmd_table.def` flags, or use `tests/test_k1_serial_safety.py`'s allowlist. |
| **Noise cal is `N` then `Y`**, not `:start_noise_cal` | The typed command is disabled and prints guidance. Captain-verbal-gated always; verify the room with the witness mic regardless. |
| **ffmpeg audio indices shift** | Bluetooth connect/disconnect renumbers them. A hardcoded `:1` silently pointed at the speaker's own mic and read flat during loud music. Re-resolve by name every run. |
| **The Bose auto-sleeps** | `blueutil` is denied Bluetooth permission on this host, so it cannot be woken programmatically. It needs a button press. Laptop speakers cannot substitute — they deliver ~5× too little SPL to the K1. |
| **Subagents go idle without reporting** | 3 of 6 did this. Chase once, then own the task yourself. |

---

## Timeline, compressed

**Before this session:** IM69D gain cut 16→8→4 (`1ae9d4a`, 5 Aug) to stop the plate false-waking;
G=8 revert (`395116f`) and peakiness gate (`248ec79`) authored on `lane/k1-vj-ble-deck8` and
**never merged**; `FINDING-rms-cannot-separate.md` written 6 Aug; joint composition canonised
7 Aug; Unit 2 left as a documented **IM73D misflash** under a flash freeze. A prior session then
spent ~4.5 h and 815 tool calls on Unit 2 producing **zero commits** and two watchdog reboots.

**This session:** proved the AP hears music (tempo lock to within 1 BPM); found the misflash and
the dead-symbol gain ladder; salvaged ~40 lines from a 68-file abandoned tree; landed the G=8
revert, peakiness gate, Unit 2 profile and `-fno-finite-math-only`; recalibrated under correct
firmware; derived the joint fraction, found it wrong under a volume sweep, re-derived it; got
contaminated twice by concurrent sessions and built the identity guard that caught the second;
boot-looped the bench on a stale-base crash bug and cherry-picked the fix; retired three abandoned
worktrees; canonised the lot.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-12 | agent:claude-code | Created at lane close-out. Records device build divergence (Unit 2 lacks the crash fix), the three open tasks with pre-decided interpretation criteria, the trap table, and the compressed timeline. |
