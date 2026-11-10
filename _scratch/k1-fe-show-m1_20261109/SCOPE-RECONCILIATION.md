Abstract: how the 9 Nov 2026 PRISM (the Captain's music-to-lightshow programme) assignment fits the 2 Nov 2026 freeze. Records the conflict, the bounded exception, who is affected, the risks to Founders' Edition (FE) delivery, and the two decisions only the Captain can make. Scope only; no results from other lanes are claimed.

Citation key: COURSE = `~/K1_Launch_Planning/00-Governance/COURSE-2026-11-02.md`. OPS = `team/OPERATIONS.md`. FW = `team/LEAD-FW-FE-RELEASE.md`. REV2 = `BRIEF-K1-FE-SHOW-M1-REV2.md`. REV1 = `BRIEF-K1-FE-SHOW-M1.md`. PLAN = `PLAN-K1-PRISM-2026-11-09.md`.

## 1. What each document says

The 2 Nov freeze (COURSE):
- Destination: "100 paid K1 Founders' Edition units in customers' hands. Nothing after that (Kickstarter, PRISM platform, dual-MCU, Titan) is worked on until it is done, except where explicitly listed as 'allowed in parallel'." (COURSE:11-12)
- FE firmware is the shipping S3 build; "PRISM-Core / K1-S3 pattern-language work does not gate shipping and is parked until the FE board is ordered." (COURSE:18-19)
- Parked list includes "SpectraSynq-PRISM (until FE board ordered)". (COURSE:29)
- "One hardware lane at a time." (COURSE:49)
- "No new agent tooling, hooks, skills, memory systems or governance programmes until G7. Maintenance only." (COURSE:50)
- "FE board ORDERED" gate G4 is Sun 23 Nov. (COURSE:40)

The 9 Nov PRISM assignment (PLAN):
- One loop: import a recording, prepare it, generate a show, edit it, play it in time on both K1 edges, save it, reopen it. (PLAN:5)
- Phases P0 to P9. The first milestone is a repeatable physical demonstration. (PLAN:7, PLAN:116-118)
- Needs a physical device owner and real-edge evidence; "host results cannot close its physical gate". (PLAN:120)
- Says it does not itself authorise firmware changes, flashes or purchases. (PLAN:129)

## 2. Where they conflict

- Direct conflict on timing. The freeze parks PRISM work until G4 (23 Nov). The 9 Nov assignment asks for it now. (COURSE:19, 29 versus PLAN:5)
- Direct conflict on Captain time. The freeze says one hardware lane. The assignment needs a physical session on a real K1. (COURSE:49 versus PLAN:120)
- The 18:45 entry allowed "no firmware source change, no flash". The 19:30 entry loosens this to "FE firmware source changes only via FW-lead change request". Both are in the same file; the later one governs. (COURSE:72 versus COURSE:73)
- Parking is a scheduling instruction, not a technical finding. The separate facts are:
  - The only qualified device in the PRISM firmware lane is an Emotiscope v1.1 (128 px), not a dual-edge K1. (REV1:8)
  - The compiler is present at `.g5r-clean/PRISM.studio`, not gone. (COURSE:73; REV2:8)
- Smaller tension, flagged for the Operations Manager. Host-player work (REV2:31, Lane C5, audio-clock pacing) could count as "new agent tooling" under COURSE:50. REV2 limits it to a change made only if measurement shows drift. The course file does not say whether that fits "maintenance only".
- Smaller tension. The FW charter says "Do not touch the AP/VP maths, sample rate, bins, calibration or effects. This is a board-support release, not a firmware upgrade." (FW:38) REV2 says a gap found in the authored-input path goes to the FW lead as a change request, "do not shrink the product requirement". (REV2:43) A request that touches effects would collide with the FW charter.

## 3. The bounded exception, as the 19:30 entry grants it (COURSE:73)

Allowed:
- Host-side PRISM work by agents: compiler and Spine reconciliation, Trinity gates, emulator proof.
- ONE Captain bench session, for T2 (prepared-Prim8-stream proof on the real K1). This is M1.

Stays parked:
- The PRISM / K1-S3 firmware lane.
- All hardware lanes.
- P3 onward (analysis, Studio) until G4. (COURSE:72)

Firmware rule:
- FE firmware source changes go only through a FW-lead change request.
- Agents do not edit FE firmware directly under this exception.

## 4. Owners affected

- FW lead: receives change requests. Their in-flight work is untouched. The shared working tree on `lane/k1-fe-release` holds their staged edits (`light_mode_waveform_hybrid_k1.cpp`, `globals.h`). This task did not touch them. They use the same bench device B489A500 for FE bench proof and flash it (FW:45-47).
- Build lead: unaffected. No enclosure, cover or order work is touched. (OPS:21; COURSE:70)
- HW lead: unaffected. Stays off; the board work is Captain-led. (COURSE:71)
- Commerce, Compliance and Demand leads: unaffected. Demand gains content material as a side effect. (COURSE:72)
- Operations Manager: owns this exception and the two decisions below.

## 5. Effect on FE delivery

- None to G2, G3 or G4 if Captain time stays at one bench session. Host-side work uses agent time only. (COURSE:38-40)
- Second-order risks:
  - A change request lands in the FW lead's queue before G4. It competes with the `k1_fe` env and G5 kit work (FW:19-28). Reversible: the FW lead can defer it, and M1 can report PARTIAL.
  - The M1 bench session collides with FW-lead flashes of B489A500. The resident build can change between sessions, so REV2:33 (identity and PRSM-path read-back) could fail on a build that lacks the authored path. Reversible: one reflash restores it, and the device registry records each flash.
  - T3 (M2, the creator loop) pulls Captain attention before G4. The Captain is hand-routing the board (COURSE:71). Reversible while only planned; not reversible once Captain hours are spent.
  - Precedent risk. A bounded exception can grow into the parked lane. Reversible if each addition is logged against COURSE:73.

## 6. Decisions only the Captain can make

**DECIDED by the Captain, 10 Nov 2026 ~16:20 AWST (K1-FE-SHOW lead session 2, asked once with recommendations):**
- (c) Firmware fixes: **"All fixes now"** (recommendation was phase 1 only). The FW lead implements every item of `CHANGE-REQUESTS-FW-LEAD.md` rev 2 except priority 3 (richer harmonic colour stays a Captain decision after the colour diagnosis). Delivered as a dated session brief in `~/K1_Launch_Planning/00-Governance/team/LEAD-FW-FE-RELEASE.md`; FW lead launched 10 Nov 16:18 AWST (`team/logs/FW-20261110-1618.log`). Nothing is flashed by the FW lead.
- (d) PRISM tools: **"Yes, all of it"** (recommendation excluded per-section editing). Agents fix the PRISM.studio, Spine and Trinity defects on branches in their own repos with their own tests, including per-section editing (later phase). `organs.lock.json` is never repinned without the Captain or the Spine owner.
- (e) Bench unit: **Main RPL, flash go** (as recommended). Once a fixed candidate passes G1–G4 and the Lane B oracle, the lead may flash the Main RPL (`9087A500`, USB `B4:3A:45:A5:87:90`) with a capture-enabled test build carrying that unit's pin map. The Captain still plugs it in; B489 stays with the FW lead for the FE bench proof.

**DECIDED by the Captain, 9 Nov 2026 ~20:50 AWST (in the lead session, against the agents' recommendations below):**
- (a) M1 bench session: **tonight** (before G4). It ran 9 Nov 20:57–21:45 AWST on B489A500; no flash. Receipt: `lane-d/D-P2-receipt.md`.
- (b) T3 (M2, creator loop): **yes, host-side only**, before G4. No hardware or firmware change. Not started by this task; it is the next executable task.
- Audio route for the bench: both conditions (silent room + music on the Bose speaker at current volume).

The original proposal text is kept below as history.

PROPOSAL — NOT APPROVED (superseded by the decisions above).

(a) M1 bench session: before or after G4 (Sun 23 Nov)?
- Option 1: before G4.
- Option 2: after G4 (from Mon 24 Nov).
- Agents recommend option 2. Reasons:
  - The Captain is the G3 bottleneck while hand-routing (COURSE:71).
  - G3 is due Wed 19 Nov and G4 Sun 23 Nov, so only about four days of slack.
  - Agents can finish the emulator proof and the stream first, so the later session is short.
  - The session moves cleanly to any day after G4; its cost does not change.
  - It also avoids the B489A500 flash collision with the FW lead before G4.
- Reversible: yes. The date can move either way.

(b) Does T3 (M2, creator loop) start before G4?
- Option 1: no.
- Option 2: yes, host-side only.
- Agents recommend option 1. Reasons:
  - COURSE:72 keeps P3 onward parked until G4.
  - T3 needs Captain judgement on shows.
  - The freeze names PRISM platform work as the thing that waits (COURSE:11-12).
  - REV2:16 already requires M1 to leave T3 unobstructed, so nothing is lost by waiting.
- Reversible: yes, until Captain hours are spent.

## Conflicts found between the course file and the brief

- None that block. The brief (REV2:40) states the exception as the 19:30 entry does.
- One wording drift. REV1:6 says PRISM is parked "until the FE board is ordered (G4, 23 Nov)", which matches COURSE:29; REV1 is superseded by REV2.
- The two tensions in section 2 (host-player tooling versus COURSE:50; change requests versus FW:38) are not resolved by either document.

2026-11-09 AWST — Lane E created this record from the course file, charters, REV2 brief and PLAN; no other file written.
2026-11-09 21:50 AWST — lead: recorded the Captain's decisions (bench tonight; M2 host-side yes; both audio conditions). The course file itself was not edited (Operations Manager owns it); add a course changelog line from this section.
2026-11-10 16:25 AWST — lead (session 2): recorded the Captain's decisions (c) all firmware fixes now, (d) all PRISM tool fixes, (e) Main RPL bench unit with flash go after the gates pass. Course file not edited; proposed course line for the Operations Manager: "2026-11-10 16:20 AWST — Captain: FW lead implements the K1-FE-SHOW change requests rev 2 (except priority 3); agents may fix PRISM.studio/Spine/Trinity on branches; Main RPL is the M1 bench unit with a flash go once fixes pass the emulator gates."
