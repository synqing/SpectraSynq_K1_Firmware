---
abstract: "Handover for the next K1-FE-SHOW lead (session 6), written 12 Nov 2026 ~06:20 AWST at the end of session 5. AFE2 stages 1–4 are built, judged, committed, pushed and running on the Main RPL (fe/k1-afe2-s4 9ff2addf). Stage 4 (one spectrum gain, four-band AGC deleted) was chosen by the Captain on camera. Read this whole, then the plan (docs/plans/AFE2-PLAN-2026-11-10.md, sections 4 and 6), before touching anything."
---

# Handover — K1-FE-SHOW lead, session 5 → session 6 (12 Nov 2026, ~06:20 AWST)

Facts below were checked in session 5 unless marked **[UNVERIFIED]**. Use `/usr/bin/git`. British English. AWST.
Supersedes `HANDOVER-K1-FE-SHOW-2026-11-11-S5.md` (same folder; still the reference for the commands in its §6).
Paths written `audio-forensics/…`, `m2-emu/…`, `fw-candidates/…` are under `_scratch/k1-fe-show-m2_20261110/` on branch `lane/k1-fe-show-m2`; `s5/…` is `_scratch/20261111-k1-fe-show-s5/` on the same lane.

## 1. Objective and authority
Destination: 100 paid K1 Founders' Edition units shipped. This lane finishes AFE2 (the K1 audio front-end rebuild) and merges it into the release lane for `fe-1.0.0`. Authority: the Captain's order of 10 Nov 2026 ~23:15 (verbatim in the plan §0); 11 Nov "continue as planned"; 12 Nov "Keep it, what's next then?!" (stage 4). The plan (`docs/plans/AFE2-PLAN-2026-11-10.md`) is the execution plan: never shorten it; record progress in its §6 and changelog.
Escalate only for: device identity mismatch; a calibration need; contradicting a Captain ruling; a product choice with no default.

## 2. Live state (12 Nov ~06:15)
| Item | State |
|---|---|
| Main RPL `9087A500`, USB `B4:3A:45:A5:87:90`, `/dev/cu.usbmodem11301` | `k1_main_rpl_show_bench` @ **`9ff2addf`** (`fe/k1-afe2-s4`), epoch `1794434462`, mode **32** (the Captain's choice, with CHROMA 0.20, MOOD 0.85, PRISM_COUNT 1.50, which he set at the plate on 12 Nov before flash 12). Restore images (not committed): `s5/bench/flash-s4c/` (`df435671`, sha256 `f46579bd…82e4`), `s5/bench/flash-s4acc/` (`27810f69`, sha256 `66b39b67…f5af`). |
| Branches (all pushed) | `fe/k1-afe2-s4` **`7381f540`** (registry) ← `9ff2addf` (line-in fix) ← `b3e70b74` (S4 acceptance) ← `d685c032` ← `27810f69` (candidate) ← `31bae23f` (`fe/k1-afe2-s3` tip: explainer moved to `docs/architecture/k1-audio-front-end-afe2.html`) ← `714277c8`. `wip/k1-afe2-s4` = `b3e70b74` (history only). Lanes: `lane/k1-fe-show-m2` (documents, evidence, tools), `lane/k1-fe-show-m1` `cb2b0798` (bench tools: `:k1_afe_spec`, `set_mode` 14/21 allowed). |
| Release lane | `lane/k1-fe-release` @ `8b202f46`: AFE2 **not** merged. |
| Shared checkout `~/SpectraSynq_K1_Firmware` | on `mcpp/next-phase-fixes` with other sessions' uncommitted files. Never checkout/stash/add/commit there. Session 5 did not touch it. |
| Explainer | `docs/architecture/k1-audio-front-end-afe2.html` (on `fe/k1-afe2-s3` and later); published https://claude.ai/artifact/NUPD343KnvpNrfJ67z3E3y v6 (stages 1–3). Builder: `audio-forensics/design/build_explainer2.py --export <export> --out <docs path>`. The Captain called the scratch location wrong; documents live in `docs/`. |
| Camera | Sony a7S III (ILCE-7SM3) on USB, PC Remote (PTP), movie Manual f/4 1/100 s fixed ISO, Daylight WB, framed on the plate. It **dropped off USB at ~05:50** (auto power-off **[UNVERIFIED]**): the Captain must wake it before the next filmed run. |
| Background jobs | none; nothing playing. |

## 3. Done in session 5
| Task | Result | Evidence |
|---|---|---|
| T2 (S3 hot input) | input side identical S2 vs S3 on 3,600 hops × 3 modes; gdft_trim 1.000 on S3 | `s5/t2/t2-compare.txt` |
| T1 (Captain at the plate) | verbatim: "Honestly if there are any differences in visual performance, it's not something I can distingush immediately." (he compared at full section level, where on = off by design). Defaults unchanged. | plan §6 |
| T5 explainer | stages 2–3 added, v6 published; file moved into docs | above |
| **S4** | Attempt 1 (anchor / section) and attempt 2 (section + fixed treble tilt ×3.16) failed the pre-registered rule (tracking/contrast level with the AGC, not up) → STOP applied. Candidate flashed with a switch; bench + **camera A/B** (4 modes); the Captain chose **section** ("Keep it"). Accepted, four-band AGC deleted, line-in fallback fix, flashed (flash 13), measured. Self-adjusting stages 4 → 3. | plan §6 rows "S4 …"; `s5/s4/`, `s5/camera/compose/` |

## 4. Rules that bind (each paid for)
All of the S5 handover §4, plus:
- **Camera:** macOS `ptpcamerad` claims the camera exclusively and ignores SIGTERM; `s5/tools/cam_capture.py` SIGKILLs it by PID right before `gphoto2` (it respawns). Never change camera settings. Lock nothing yourself; if the exposure mode is not movie Manual, ask the Captain.
- **Serial port:** the Captain's Cursor serial monitor holds the port when open; `lsof` needs the sandbox off to see it. Ask him to close it; never kill another app.
- **Emulator boot epoch:** cases with `epoch=boot_monotonic` (e.g. `startup-sqr`) shift when boot code changes (adding a serial command moved it 112 ms). Prove behaviour with a declared-epoch copy before calling it a regression.
- **Pre-register acceptance rules** in plan §6 before running an A/B; score with a script (`audio-forensics/emu/score_s4.py` pattern).

## 5. Outstanding tasks, in order
Each: purpose → method → acceptance → failure → STOP. Repair authority: fix and re-run without asking.

**Q (open questions to the Captain, asked 12 Nov ~05:30, unanswered):** (1) Cut S5 (clipping only at venue volume) and S6 (VU modes) from `fe-1.0.0`? Lead's recommendation: yes, ship without them, do them after. (2) Is any line source cabled to the bench K1's loose PCM1808 module? Do not proceed on S5/S6 order or line-in measurement assumptions until answered; S7 code work below does not wait.

**Captain ruling 12 Nov ~21:50 (verbatim): "Captain, for the moment, let's leave the Aux jack out of this development phase".** S7's line-in part below is deferred; line-in ships on the broadband fallback (as before AFE2). Q2 is closed by this ruling; T7 no longer waits for line-in.

**S7 — line-in gets the meter; ritual; dead code.** Purpose and acceptance: plan §4 AFE2-S7. Facts found: the FE jack path (`audio/i2s_audio.h` `#if K1_PCM1808_LINE_SWITCH` branch, `pcm_hop[96]` → `k1_audio_commit_canonical_frame`) never reaches the meter; since `9ff2addf` line-in hops use the broadband AGC fallback and brightness factor 1.0 (`k1_afe2_metered`). Method: a second meter state for line-in (`k1_afe2_line`) fed from `pcm_hop` (no ×21.6, no SENSITIVITY on that path, so its K and floors differ from the microphone's: **measure** them on line audio, never scale by inference); stage 1/4 read the active source's meter; then delete the broadband fallback (last trace of the old AGC). Emulator cannot replay PCM1808 capture: measurement needs the FE board or the bench K1's PCM1808 module with a cabled source. STOP: FE board identity not confirmed (plan S7).

**S5, S6: skipped for `fe-1.0.0`** (Captain, 12 Nov: "Stage 5: Skip"; S6 "Skip it then" after the lead corrected its own claim that S6 fixes mode 32). Stage 1 is on for the FE (`b204f792`, "Yes turn it on"); release lane `24edfb59`. AFE2's software for `fe-1.0.0` is complete; what remains is hardware (T7).

**S8** — picture for the Captain only (mode 22 dark stretches). Note: the S4 camera stills show mode 22 dark at 1:42 with the old AGC and lit with S4.

**T6 — merge into `lane/k1-fe-release` — DONE 12 Nov ~22:00.** `lane/k1-fe-release` `0aa48f64` (FW lead's local receipt commit on the show fixes `c949151c`) → **`88f096ea`** (merge with `fe/k1-afe2-s4` `6ac7bd31`), pushed (origin was `024389b4`). The FW lead's 12 Nov receipt (finding 6) expected this merge. The release side added documents only (0 files outside `docs/`), so the firmware equals `fe/k1-afe2-s4`'s code `9ff2addf`, judged there; no re-run was needed. Still to do: update the skill text listing the deleted silence constants (S5 handover "Known open items").

**Q3 (asked 12 Nov ~22:00): stage 1 on the FE build.** `k1_fe` extends `k1_main_rpl_im69d`, which does not set `K1_AFE2_DEFAULT_ON`, so on the FE the stage-1 output-brightness exposure is measured but **not applied**; the Captain's approved camera A/B had it applied (bench env). Without it, spectral modes on the FE get no section dynamics at all (stage 4 leaves the section level to stage 1). Lead's recommendation: add `-DK1_AFE2_DEFAULT_ON=1` to `[env:k1_fe]` so the FE shows what the Captain approved. One-line change; then pytest, `k1_fe` build, G1–G4 (`fe` profile) and the release lane.

**Critical path note (FW lead receipt 12 Nov, not this lane's work):** the Captain's FE board is K1-FE-S31-G01 with an **ESP32-S31**, not the S3 the course names (Captain ruling 10 Nov 17:00). The FE firmware compiles for the S31 only with patches; the S31 port (FastLED patch, pin map, BLE library, pre-release toolchain, web flasher) is the FW lead's lane and needs the Operations Manager to update the course first. AFE2 needs nothing extra for the S31 beyond the microphone proof on a real S31.

**T7 — FE board, A06, A18, `fe-1.0.0`**: FE board flash only with identity confirmed (S31 port first, FW lead). Line-in measurement no longer required (Captain ruling above). A06 timing (iPhone 240 fps clap, one Captain action), A18 musical value with the Captain. Tagging is a publication step: confirm with the Captain.

## 6. Commands that work
S5 handover §6 holds export, commit, merge, pytest, builds, emulator, gates, flash, registry commands. New in session 5 (all in `s5/tools/`, on `lane/k1-fe-show-m2`):
- `mkexport.sh <name> <sha>`: export + private git dir + library caches (`cp -c`).
- `commit_export.sh <export> <parent> <branch> <msg file> [create]`: private-index commit; prints the stat; **read it** (an export missing a file the parent has deletes it).
- `make_probe_scenario.py <export>`: guard scenario on the probe env (per-hop G lines incl. stage-4 fields: mean magnitude, S, A, M, gain, band means).
- `audio-forensics/emu/make_scenario_s4.py <export>` (after `make_scenario_tracks.py`): five tracks × three levels × modes 14/21/22/32; `analyse_s4.py --export --run --out [--cal]`; `score_s4.py <variant> <agc json> <variant json>`.
- `bench_ab.sh <name> <cmd…>` (LISTEN_S=110) + `bench_s4.py <out.json> <run dirs…>` (light %, loud ÷ breakdown, movement, hue bins, silent music lines; reproduces session 4's numbers exactly).
- Camera: `cam_ab.sh <name> <cmd…>` (camera + Loreen −10 dB), `cam_compose.py` (side-by-side video with audio, brightness chart, stills; frames timed to the song by the player's DAC trace).

## 7. Ship path
1. On silicon now: Main RPL runs AFE2 stages 1–4 (`9ff2addf`), bench build only. In source: `fe/k1-afe2-s4` (pushed).
2. Next agent: S7 (line-in meter, needs a line source on hardware); S5/S6 per the Captain's answer; T6 merge into `lane/k1-fe-release` and judge; T7 FE board flash.
3. Captain: answer Q1/Q2; wake the camera when a filmed run is needed; A06 and A18 at the end.
4. Shipped = `fe-1.0.0` tagged on an FE board passing every M1 check, recorded in `docs/hardware/device-build-registry.md`.

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-12 | agent:claude (K1-FE-SHOW lead, session 5) | Created at the end of session 5, in `docs/handover/K1-FE-SHOW/` (the plan moved to `docs/plans/`, earlier handovers to this folder; the Captain ruled that finished documents do not live in `_scratch`). |
