# K1-FE-SHOW-M1 — prepared-show physical proof on the shipping K1 (P0 → P2)

Issued 9 Nov 2026 (AWST) by the Operations Manager (Claude) on Captain's instruction. Source plan: `PLAN-K1-PRISM-2026-11-09.md` in this folder (Captain's execution brief). This brief re-targets its P0–P2 from the parked PRISM lane to the shipping FE firmware. Reasons are in `COURSE-2026-11-02.md` changelog (9 Nov).

## Why here and not PRISM (facts found 9 Nov)
- SpectraSynq-PRISM is PARKED by the programme course until the FE board is ordered (G4, 23 Nov).
- PRISM/K1-S3's only qualified device is an Emotiscope v1.1, 128 px (`K1-S3/docs/deployments/current.json`). Not a dual-edge K1. No dual-edge K1 has ever been flashed from that lane.
- No `ShowBundle`, `Prim8`, `Trinity` or `stem_features` code exists in PRISM. That lineage lives in `~/Workspace_Management/Software/Trinity` (analysis, 16 Aug), `~/Workspace_Management/Software/SpectraSynq-Instrument-Spine` (host spine, 16 Aug) and the deprecated donor `Lightwave-Ledstrip` (ShowBundle consumer). The compiler the spine calls (`PRISM.studio/tools/trinity_compile_showbundle_v0_2.js`) no longer exists at that path.
- This repository (`~/SpectraSynq_K1_Firmware`, `lane/k1-fe-release`) is the FE product firmware: real dual-edge 2×160 geometry, Captain-approved `tools/esp_emulator/k1_lightshow_acceptance.json` (schema k1-lightshow-acceptance/1, 5 Nov), an ESP32-S3 emulator that replays real PCM through the real pipeline and captures native A/B frames (`tools/esp_emulator/README.md`, `player.py`), and a typed serial command surface (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_cmd_table.def`, e.g. `set_mode`).
- Therefore the smallest honest M1 is: Mac transport plays the original recording → timestamped cue list → existing typed serial commands → the resident FE build on the real K1 → both edges. No firmware change is the default.

## Milestone
M1 = one 60–90 s real-music passage, hand-authored cue list, both real edges, repeatable three times, measured timing with stated uncertainty, pause/seek survived, live baseline restored. Nothing else. Analysis quality, Studio, PRISM contract migration are OUT.

## Read order (all read-only unless named as a write target)
1. `~/K1_Launch_Planning/00-Governance/COURSE-2026-11-02.md` (authority; this task is listed in its changelog, 9 Nov)
2. `AGENTS.md`, `CLAUDE.md`, `K1_CANONICAL_CONTEXT.md`, `docs/agent/AGENT_EXECUTION_STANDARD.md`, `docs/process/SPECTRASYNQ-GIT-DOCTRINE.md`, `docs/process/SPECTRASYNQ-HOUSEKEEPING-DOCTRINE.md`
3. `PLAN-K1-PRISM-2026-11-09.md` (this folder) — sections 1, 4, 6 (P0–P2), 7 (A01–A09, A14–A15), 10
4. `tools/esp_emulator/README.md`, `k1_lightshow_acceptance.json`, `player.py`, `emu_capture.py`, `run.py`
5. `SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_cmd_table.def`, `serial_cmd_handlers.{h,cpp}`, `serial_typed_dispatch.cpp`
6. `docs/protocol/k1-ble-midi-map.json`, `k1-ws-controls-registry.yaml` (control names/ranges only; BLE is not the show transport)
7. Lineage, read-only, for contract vocabulary only: `~/Workspace_Management/Software/SpectraSynq-Instrument-Spine/docs/spec/ONE_INSTRUMENT.md`, `docs/GOLDEN_PATH.md`; `~/Workspace_Management/Software/Trinity/analysis/STEM_PACK_CONTRACT.md`

## Execution order and swarm plan
Branch: `lane/k1-fe-show-m1` from `lane/k1-fe-release`. Work in `_scratch/k1-fe-show-m1_20261109/`. One writer per file set. Launch lanes A, B, C as parallel subagents; D runs after A–C report.

### Lane A — P0 baseline and compatibility (desk, no device mutation)
- A1 Identity record: repo HEAD, dirty files, platformio env for `k1_fe`, emulator tool lock, toolchain versions. If a K1 is attached on USB: read back `build`/identity over serial only. No flash. Unknown stays unknown.
- A2 Control-path compatibility table (accepted today / adapter needed / unsupported) for: typed serial commands, BLE-MIDI CC map, emulator scenario injection. Columns: command, parameters, range, edge addressability (top/bottom/both), acknowledgement form, persistence side effect, measured round-trip.
- A3 HARD CHECK: does `set_mode` / palette / photons via serial trigger `save_config_delayed` (flash write) on every call? Find a non-persisting path (`k1_queue_set_mode_enabled`, session-only setters) or state plainly that none exists. Cues must never cause flash writes.
- A4 Measure serial command→ack latency distribution on the emulator (and on hardware in Lane D): ≥200 commands, report p50/p95/max in ms.
- A5 Asset inventory: locate Captain's approved reference tracks and prior capture assets (search `~/K1_Optical_Captures`, `evidence/`, `_scratch/`, `~/Music`; memory names BOOM and Dopex). Record exact file sha256, sample rate, channel layout, duration. The banned `song-0` fixture is never used. If no approved asset is found, select one locally stored lossless track and label it "UNAPPROVED — comparison only".
- A6 Rollback material: confirm a retained known-good image/config for the resident build (`~/K1_Rollback_Images`, `evidence/`), its sha256 and the documented restore route. Do not overwrite anything.
- Output: `A-P0-baseline.md` with the tables above; every row FACT (observed) or UNKNOWN.

### Lane B — P1 minimal cue contract and fixtures
- B1 `cue_list_v0.schema.json`: asset identity (sha256 of original file, decoded sample rate, sample count, channels); timeline in samples at asset rate plus ONE exact conversion to microseconds; `epoch_id`; cue = {`t_sample`, `edge`∈{top,bottom,both}, `command` (must exist in Lane A's accepted table), `args`, `cue_id`}; stable ordering rule for equal times; version. No 0–1 ranges without named units.
- B2 Precedence rules written down: firmware power limit always wins; manual serial/BLE changes during a show are recorded as overrides; overrides release on next cue for that control.
- B3 Fixtures (verifier-owned, host-only): constant, ramp, single event, simultaneous top+bottom event, silence section, invalid value, unknown command, backward seek, forward seek, epoch change. Each has an expected rejection or expected command stream.
- B4 Validator: `validate_cue_list.py` rejects malformed lists without emitting any command; tests prove each fixture's expected outcome.
- Output: schema, fixtures, validator, pytest.

### Lane C — P2 host player and emulator proof
- C1 `show_player.py`: plays the original recording through CoreAudio (`sounddevice` or equivalent) at the Mac's CURRENT volume — never change system volume; stop any previous playback first. Uses the stream's reported output time/latency as the programme clock. Schedules cues from audio position, not wall-clock sleeps. Supports pause, resume, seek (new epoch; cancels queued cues). Emits typed serial commands; logs scheduled time, send time, ack time per cue (µs, monotonic).
- C2 Emulator run: feed the identical PCM to the emulator (`run.py` scenario), apply the same cue list through its injection path, capture native A/B frames. Verify each cue's application hop against its scheduled sample time. Repeat three times from a known initial state; native frame payloads must be byte-identical across runs (A05) or the difference is explained.
- C3 Hand-author the cue list for the chosen 60–90 s passage: one clear transition, independent top/bottom roles, approved palette, admitted modes only (Waveform Hybrid K1 / Snapwave family). No new effects. Keep it to ≤40 cues.
- Output: player, emulator run directories (`result.json`, `report.html`), three-run comparison, cue list.

### Lane D — P2 on the real K1 (one bench session)
Precondition: Lanes A–C PASS; Captain has the K1 on USB with the resident FE build; identity read-back matches A1. If identity mismatches: STOP and report. No flash without Captain's explicit word.
- D1 Capture live baseline first: 60 s of music into the mic, both edges photographed/filmed, serial telemetry saved.
- D2 Run the show three times from the same initial state. Keep: scheduled/sent/ack times, serial log, 50 fps Sony footage (gross alignment and geometry only).
- D3 Pause/resume once; one backward and one forward seek, one at a point with a visible trail. Old-epoch cues must not fire.
- D4 Timing gate A06 (p95 ≤25 ms, max ≤50 ms) is certifiable ONLY with a common-clock audio+light sensor capture (uncertainty ≤5 ms). First check `~/K1_Optical_Captures` and bench notes for an existing rig. If none: report A06 as BLOCKED with the 50 fps footage as coarse evidence (±20 ms). Do not buy anything; do not claim sub-frame timing from video.
- D5 Restore live baseline; confirm music drives both edges as in D1. Restoration result recorded.
- Output: `D-P2-receipt.md` per the plan's section 10 evidence record.

## Hard rules
- No firmware source change in this task. If M1 is impossible without one (Lane A3 finds no non-persisting control path, or no edge-addressable control), stop and report the exact mechanism — that is a FW-lead change request, not your job.
- No flash, reset or erase of any board unless identity read-back mismatches AND Captain says so.
- Gates start NOT RUN. Record PASS / FAIL / BLOCKED / NOT RUN distinctly. Never upgrade a self-report. A gate you have never seen go red is not a gate: each validator must be shown failing on a planted bad input.
- Never raise Mac volume. Never leave playback running.
- Git doctrine: lane branch, no commit to main, commit on the lane at session end with CHANGELOG entry; housekeeping two-zone rule; one backup file max; nothing on Desktop/Downloads.
- No new dashboard, orchestrator or project umbrella. Reuse `report.py`/`player.py` outputs.
- British English. Explain every abbreviation on first use in anything Captain reads.
- Long jobs run detached; poll, never block.

## Escalate (stop and write it up) only on
- Device identity mismatch; resident build unknown.
- No non-persisting, edge-addressable control path (A3).
- Emulator build fails on the current checkout after one diagnosed retry.
- No track asset locatable at all.
Everything else: decide, label the assumption, continue to the end.

## Handback (problems first)
What works · what fails · what is blocked · decisions genuinely needing Captain · next executable task. Then links: cue list, player, emulator runs, serial logs, footage, restoration result, rollback material. Preserve failed candidates with reasons.
