# K1-FE-SHOW-M1 — REVISION 2 (9 Nov 2026, 19:30 AWST)

Supersedes `BRIEF-K1-FE-SHOW-M1.md` (Rev 1, retained as history). Rev 1's hardware target, safety rules, lane structure and swarm plan stand. Rev 1's **objective and transport were wrong** and are corrected here after an independent review was verified against source.

## What changed and why (Correction Protocol)
| Rev 1 said | Verified fact (9 Nov, 19:15) | Consequence |
|---|---|---|
| The PRISM.studio compiler no longer exists | `~/Workspace_Management/Software/.g5r-clean/PRISM.studio` exists with `tools/trinity_compile_showbundle_v0_3.js`, `src/vm.js`, `src/playback.js`, `src/cdc.js`, `tools/intent_cdc_stream.js`. Spine `organs.local.json` points there; `tools/instrument.mjs:150` calls v0.3. Working tree 07eb822; lock `cc00556d`. Its `.git` has an alternates pointer to the deleted `PRISM.studio/.git/objects` → `git` reports `bad object HEAD`. | Compiler PRESENT. Identity unverifiable until re-cloned at `cc00556d` from `synqing/PRISM.studio` and diffed against the local tree. Do not silently repin. |
| M1 = timed `set_mode`-style serial commands over the live analyser | FE firmware already has an authored-input path: 34-byte PRSM frame {version, hz, seq, t_us, 8× Prim8 u16} (`audio/k1_prsm.h`) → `serial_menu.cpp:4155–4160` → `k1_authored_on_frame` → snapshot fields vu_level/peak/spectral_energy (pressure), novelty (impact), low/mid/high energy (mass/momentum/texture), silence; replaces the live snapshot while fresh (`.ino:1144–1158`); zeroes chroma (`.ino:1565–1567`); 50 ms freshness → RECOVERY → STANDALONE (live fallback designed in); seq gap >3 → ACQUIRE (seek handling). No per-edge feature split; device ignores `t_us` for scheduling (uses arrival time). | M1 = **prepared Prim8 stream driving the renderer**, not preset switching. Rev 1's cue player is demoted to an optional transport smoke test (T1). |
| Objective = a timed FE demonstration | Captain's programme = PRISM offline music-to-lightshow workflow (prepare → generate → edit → execute → save/reopen/replay). FE is the execution target, not a replacement for the programme. | Three tests kept distinct (below). Results are reported per test; T1 never stands in for T2 or T3. |
| Parking framed as a technical consequence | Parking is a scheduling instruction (course 2 Nov). The Emotiscope finding and compiler location are separate facts. | Scope reconciliation stated plainly in the course changelog (19:30 entry): bounded host-side exception; PRISM/K1-S3 firmware lane and all hardware lanes stay parked; FE firmware source changes only via FW lead change request. |

## Three tests — never conflated
- **T1 Transport smoke** (optional, ≤1 h): timed config changes over live analysis. Proves serial path and Mac clock only.
- **T2 Prepared-input proof = M1**: a frozen Prim8/authored stream changes the intended renderer output on both real edges, repeatably, in time with the original recording; seek and stream-loss behave; live baseline restored. Includes a rejected-input case (bad hz, bad magic, seq discontinuity) proving the change comes from the authored consumer, not live audio.
- **T3 Creator loop = M2**: generate (Trinity), edit, save, reopen, replay. Not in this task; the task must leave T3 unobstructed.

## Lanes (parallel subagents A–C now; D after; E host-side in parallel, no bench time)
### Lane A — P0 baseline (as Rev 1) PLUS
- A7 Authored-path consumer map: for each admitted FE effect (Waveform Hybrid K1, Snapwave, others in the acceptance set) list which snapshot fields it reads (vu/novelty/low/mid/high/silence/chroma). State plainly which effects become palette-only hue under authored mode and whether that is acceptable under THE LAW (colour disciplined, hue tracks harmony/energy).
- A8 Confirm the PRSM path is compiled into the `k1_fe` product env and into the resident device image (build flags, then device read-back in Lane D). Source presence ≠ deployment.
- A9 Record the authored-mode timing facts: 120 Hz nominal, 50 ms freshness, seq gap 3, host-side drift-corrected `setTimeout` scheduling (`playback.js`), device uses arrival time. State the implication: alignment accuracy is the host's responsibility.
### Lane B — P1 contract (as Rev 1) PLUS
- B5 Reconcile timebases: Trinity contract "times in seconds" → ShowBundle/VM `t_us` → PRSM `t_us` (ignored on device) → device hop (7.5 ms). One explicit conversion table; A02 ≤1 sample rounding check.
- B6 Map Rev 1's cue-list fields onto the EXISTING ShowBundle 0.3 schema and K1CT PARAM_SET; a new schema only for a proven gap, versioned.
### Lane C — P2 emulator proof, re-targeted to T2
- C1 Re-clone `synqing/PRISM.studio` at `cc00556d` into `_scratch/.../prism-studio-locked/` (read-only); diff against `.g5r-clean/PRISM.studio` working tree 07eb822; report the mismatch. Do not change `organs.lock.json`.
- C2 Run the Spine golden path (`docs/GOLDEN_PATH.md`, `tools/g5_clean_verify.sh`) host-only against today's checkouts. Record PASS/FAIL with the compile manifest and Intent Trace hash. Fix nothing in Trinity/PRISM.studio; report.
- C3 Hand-author (or compile from an existing Trinity fixture contract) a 60–90 s Prim8 stream for the chosen passage. Frozen bytes, sha256.
- C4 Emulator: determine whether PRSM frames can be injected at hop coordinates through the scenario command blob (`parse_command()` path, README §Coordinates). If yes: fixed PCM + fixed start state, run baseline (live) vs authored stream vs rejected-input stream; native A/B frames must differ for authored and NOT differ for rejected. Three repeats byte-identical. If no: state the exact gap; do not fake it with a host render.
- C5 Host player: use `src/playback.js` as the base. Add audio-clock pacing (CoreAudio stream time with reported output latency) in place of wall-clock `setTimeout` ONLY if measurement shows wall-clock drift exceeds budget; otherwise measure and report. Never change Mac volume; stop prior playback.
### Lane D — real K1 (one bench session; preconditions as Rev 1)
- D0 Identity read-back; confirm PRSM path present in the resident build (A8). Mismatch → STOP.
- D1 Live baseline capture (as Rev 1).
- D2 T2 three runs: PRSM stream + original audio from the Mac; record seq/t_us sent, device state transitions (STANDALONE→ACQUIRE→AUTHORED), footage of both edges.
- D3 Seek (seq gap) forward and backward; stream stop → observe RECOVERY→STANDALONE within the 50 ms + tick budget; no blackout, no stale replay.
- D4 Timing: A06 fine gate BLOCKED unless a common-clock audio+light capture exists (check `~/K1_Optical_Captures`, bench). 50 fps footage = coarse only. Report M1 as PARTIAL if A06 is blocked — not complete.
- D5 Restore live baseline; record result.
### Lane E — scope reconciliation record (desk)
- E1 Write `SCOPE-RECONCILIATION.md`: earlier freeze (2 Nov) vs new PRISM assignment (9 Nov); bounded exception (host-side PRISM work by agents; one bench session; no hardware lanes; no FE source change without FW lead); owners affected (FW lead, Build lead unaffected); effect on FE delivery (none to G2–G4 if Captain time stays at one session). Decisions genuinely Captain's: (a) whether M1 bench session happens before or after G4; (b) whether T3 (M2) starts before G4.

## Hard rules, escalation, handback — as Rev 1, plus
- If the authored path cannot drive an admitted effect acceptably (A7) or cannot be injected into the emulator (C4), report the smallest adapter or firmware change as a change request to the FW lead. Do not shrink the product requirement to fit existing interfaces.
- Emulator timing is lockstep and does not model hardware scheduling (README §64–74, 148–151). Never promote it to physical latency evidence.
- `photons`/palette serial commands call `save_config_delayed()` (`serial_cmd_handlers.cpp:120–123, 185–188`); PRSM frames do not. T1, if run, must prove it causes no flash writes.
