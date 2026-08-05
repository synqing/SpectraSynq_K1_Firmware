---
abstract: "Red-team-hardened evaluation + plan for dual-K1 sync. Product shape: M1 = twin sync (full 22-mode roster, ships first, ~20–40 ms budget) → M2 = widened 320-px seam-centred display (contingent on day-zero physical seam trial + measured budget). Sync engine = timestamped replay (render-what-you-send delay line), leader authority, per-path control contract (calibration NEVER mirrored). Transport decided by Phase-0 bake-off with a 4-number gate. Captain forks F1–F5 inside. v1.0, survived 4-lens red team (3 KILLs consumed)."
---

# Dual-K1 Sync — Evaluation & Implementation Plan (v1.0, red-team-hardened)

Lane: `artifacts/k1_dual_sync_eval_2026-07-08/` · Evidence: [`findings.md`](./findings.md), `findings/` (9 research + 4 red-team files) · Red team: perceptual FLAWED→fixed, timing/engineering/doctrine SOUND_WITH_FIXES → all KILL/MAJOR fixes consumed below. Orchestrator re-ran every decisive claim (ledger in findings.md).

## 0 · Doctrine gate (sensorybridge-doctrine)
1. **Rules engaged:** perceptual impact over architecture; independent dual-channel behaviour protected (no re-unifying one device's two channels, `K1BufferView.h:5-11`); motion canon *modulate velocity, never jump*; compile ≠ runtime proof; instrumentation never ships; MabuTrace mandatory for timing-causality claims; cal silence gate never waived.
2. **Local evidence:** `findings/` (13 files), orchestrator re-runs (BLE role, canvas geometry, half-canvas render, facade cal paths, BT core pinning, device registry, radio-free prod, UF2).
3. **North-star impact:** M1 twin sync is a pure perceptual win (two rooms/sides of a room beating as one, all 22 modes). M2 widened is a bigger moment with real regression risk (seam quality, mode character change) — hence gated on physical evidence before firmware.
4. **Re-test triggers crossed:** VP geometry (M2), timing (radio near Core 0), AP consumer surface. Requires apparent-motion re-test, transport probe, interference A/B closure.
5. **Runtime proof:** two-device bench eyes-on; measured clock-offset/lateness numbers; MabuTrace Core-0 evidence; day-zero seam photo.
6. **Minimal edit plan:** §7.  7. **Non-goals:** §9.

## 1 · What "sync" actually is — corrected

Three verified facts shape the feature, one of which corrects the draft:

1. **All 22 enabled modes are centre-mirrored, and effects render ONLY the upper half** `[80..159]` of the 160-px canvas; `mirror_image_downwards()` fills `[0..79]` (✓ re-run: ember zeroes the lower half and writes only `HALF+k`). Consequence — there are exactly **two honest widening mechanisms**, and the draft's "2× detail with zero geometry work" conflated them:
   - **v-a Windowed stretch:** window + flip the existing 80-px arm across 160 LEDs at the `scale_to_strip` resample seam (zero effect edits, proven parametric by the 160→224 k1_custom path). Honest statement: **same information, 2× larger, half the pixel density, ~2× physical velocity** — "one bigger picture", not "more detail".
   - **v-b Native 160-px arm:** per-effect origin/extent/fade rework (HALF→NR basis change across all 22 modes; BLOOM alone has three verified change sites). Real 2× unique detail, real per-effect cost, full perceptual retune pass.
2. **Identical inputs is a replay contract, not a stream.** A leader that renders fresh local 133 Hz state while the follower renders delayed decimated packets violates its own premise (up to ~22.5 ms systematic mismatch — 2.25× the seam budget — from PLL quantisation + staleness alone). The fix is **render-what-you-send**: the leader renders through the *same timestamp-indexed delay line of decimated snapshots it streams*; both devices render snapshot T−D at leader-clock time T. Transport latency then vanishes from the seam — it only bounds D against the leader's <50 ms budget (D ≤ ~30 ms after mic 7.5 + AP ~2 + frame 5.4 + WS2812 wire-out 4.8 ms).
3. **The seam is governed by clock error, not transport p95.** With replay, the two numbers that matter are (i) inter-device clock-offset error and (ii) packet lateness beyond D. Sub-10 ms clock sync is a solved problem (two-way RTT exchange at pairing; µs-class over ESP-NOW; 1 Hz maintenance beacons suffice — S3 crystal drift ≤40 µs/s).

**Also corrected/absorbed:** the follower's palette hue comes from the VP-side chromagram derived from its OWN mic (`make_smooth_chromagram` reads the AP spectrum every frame — the Palette Vibrancy V1 path), so the stream must carry quantised pre-gate chroma (+12 B) and the follower needs an injection mux for VP-read AP globals; the feature subset is recomputed over **render-pipeline** consumers, not effect consumers only. WAVEFORM_HYBRID (raw waveform history) is out of any widened v1 roster. Census tally corrected: 15 class-A / 7 class-B per the census table.

## 2 · Product shape — twins first, widened second (restructured per red team)

**M1 — Twin sync (the shippable core).** Both units render identical centre-mirrored displays from the leader's replayed state: **all 22 modes, every beat-locked showpiece, zero geometry work, no physical-seam exposure**, and the timing bar relaxes from ~10 ms displacement to event-simultaneity (~20–40 ms) — a 2–4× easier transport target. This is the "two K1s beat as one" product, and every line of M1 (protocol, replay, clock, control contract, pairing, persistence) is a prerequisite of M2 anyway. Nothing is throwaway.

**M2 — Widened display (the showpiece, contingent).** Seam-centred geometry (F4 mockup), starting with mechanism **v-a** to prove seam physics cheaply; **v-b** is the quality upgrade if M2 survives eyes-on. M2 proceeds only if: the **day-zero physical seam trial** (below) doesn't kill it; the measured seam budget is achievable; and the roster story is acceptable (v1 widened roster ≈ 8 stateless modes, **no beat-locked mode** — Captain must see this stated plainly). Paired-mode cycling clamps to the widened roster; widen↔unwiden transitions are slewed cross-fades, never jumps.

**Day-zero kill test (before any sync firmware):** same build on both bench-capable units, static colour + simple pattern, butt the two enclosures together, fixed-exposure photos/video. Answers: true bezel gap in LED-pitch units, LGP edge behaviour, panel-to-panel brightness/colour batch variance (which **no firmware fixes**), and whether "one surface" is physically credible. Cost ≈ an hour; it can kill M2 before a single phase is paid for. F4's HTML mockup decides **geometry semantics only** — seam *quality* is decided on this photo.

## 3 · Sync engine architecture (M1 core, M2 inherits)

- **Roles:** leader = audio + control + clock authority. Role + side persisted in a dedicated LittleFS magic+version file (never a `struct conf` field — CFG_FALLBACK wipe); **factory_reset explicitly deletes it** (red-team: it would silently survive the enumerated delete list today). Pairing = explicit one-time ritual; auto-resync thereafter; MAC tie-break.
- **Replay stream (leader → follower), all records leader-clock timestamped:**
  - Decimated snapshot subset recomputed over render-pipeline consumers (incl. 12-B pre-gate chroma), quantised; **33.3 Hz packets carrying two snapshots each** (≥20 ms spacing — keeps ESP-NOW out of its documented <20 ms buffering-collapse regime and halves BLE event count).
  - Edge events (beat_tick, onsets, drop-cut) with event-ids **and timestamps**; follower re-anchors **back-dated** (`tick_time + n·period`), discards ticks older than half a beat; dead-reckoning is gap-fill only.
  - Clock: two-way RTT burst at pairing and on link recovery; 1 Hz maintenance beacon; forward-only slew. Achieved offset error is a **measured Phase-0 gate number**.
  - Follower renders from streamed values through the same quantisation the leader rendered through (render-what-you-send closes the SQ15x16-vs-u8 mismatch).
- **Control contract — a 71-row per-path policy table, not "the facade as-is":** classes = mirror / side-transform (`primary.mirror`, `reverse_order`, presets) / leader-only / **blocked** (`calibration.*` — NEVER mirrored; the cal silence gate is never waived and a mirrored cal-confirm would fire the follower's cal un-gated). Adopted runtime scalars (AGC envelope, hue phase, brightness) are **RAM-only-adopt**; persisted cal-derived CONFIG fields (DC_OFFSET, SWEET_SPOT_*, noise_samples) are **never-adopt** — the host harness asserts sync application never triggers `save_config_delayed` on them (this is the 2026-05-24 SWEET_SPOT poisoning incident, prevented by architecture). Follower-local inputs (buttons/encoders/serial) while paired: forward-to-leader or blocked — never applied locally. Mode/param changes carry **apply-at timestamps** so cross-fades commit on the same beat on both units; follower SmartDirector auto-rotation suppressed. K718 dial binds the **leader only**.
- **Failure stance:** link loss → coast ≤ ~2 s on flywheel + last snapshot → slewed cross-fade to own-mic independent mode (restoring own AGC/cal), never blackout, never jump; rejoin → RTT re-sync, slewed re-entry; defined acquisition display while the delay line fills. Leader loss = follower becomes a normal solo K1.
- **Core placement, honestly:** the BT controller and WiFi driver tasks are framework-pinned to **Core 0** (✓ re-run: `CONFIG_BT_CTRL_PINNED_TO_CORE=0`, `CONFIG_ESP_WIFI_TASK_PINNED_TO_CORE_0=y`) — only the NimBLE host + sync task can move to Core 1. So Core-0 radio work is *minimised and measured*, not "clean": bounded by the Phase-0 gate under worst-case duty (stream + K718 dial linked). Render side is protected too: `led_thread` runs at idle+1 and RMT refill can starve — FPS floor and LED-glitch checks are gate criteria.

## 4 · Transport — bake-off with a corrected gate

Candidates (framing symmetrised per red team: **neither is UF2-ratified; both sit under F1**. UF2 ratified BLE-MIDI as the K718 *control* surface, not BLE-anything for a new K1↔K1 stream; ESP-NOW re-enables the esp_wifi driver UF2 dropped):
- **A: BLE custom GATT**, NimBLE dual-role (central to K718 + peripheral to follower). **A′ fallback: Bluedroid** (external benchmark: 14.6 ms vs NimBLE 45 ms median notify — if the 3× penalty reproduces on K1, A fails for a stack reason).
- **B: ESP-NOW broadcast** at 33.3 Hz batched packets; raw `esp_now_send()` distinguished from the esp-now component wrapper (the collapse report is against the component).
- WiFi softAP+WS: fallback only; product-deprecated (UF2), jitter-hostile.

**Phase-0 gate = four measured numbers** (replaces the draft's wrong "transport p95 ≤ seam budget"):
1. Clock-offset error ≤ measured seam budget (M2) / ≤ 20 ms (M1);
2. p99.9 packet lateness ≤ D (delay-line depth);
3. Leader end-to-end ≤ 50 ms **with D included** (D ≤ ~30 ms);
4. Render-side health: FPS floor p95 under full stream + dial load, zero WS2812 latch glitches, internal-heap `min_ever` watermark above the documented transient-dip abort line.

## 5 · Captain decision forks (accept/reject; defaults stated)
| # | Fork | Default if no override |
|---|------|------------------------|
| F1 | **RATIFIED 2026-07-08:** scheduling non-issue (dev parallel to crowdfunding) — Phase 0 green-lit. Radio choice = merit-driven. Captain's minimum standard: **~8 ms perceived-lag/seam budget + small margin** (supersedes the provisional ≤10 ms; clock-offset gate tightens to ≤~4 ms). WiFi must prove AP absorption + reliability; BLE carries the K718 100%-uptime field prior. | — decided (framework) |
| F2 | **RATIFIED 2026-07-08: BLE-family custom GATT** (see f2-transport-decision.md). Phase 0 narrows to verifying BLE against the four gate numbers + dial-link uptime under stream load. Contingencies: ESP-NOW (tier 1, paper) → 2nd MCU radio co-processor, ESP32-S3 or C5 (tier 2, Captain-added). | — decided |
| F3 | Widening scope: primary pair only vs both channels (EdgeMixer) | Primary-only for M2 v1 |
| F4 | ~~Widened geometry semantics~~ **RATIFIED 2026-07-08: seam-centred (Option 1), Captain eyes-on via hosted mockup.** Seam *quality* still gated on the day-zero photo. | — decided |
| F5 | **RATIFIED 2026-07-08:** full authority to silence/remove dev-blocking gates with documented reasons; 1401 flashing authorised. Recorded interpretation: identity guards get envs REGISTERED (updated, not deleted — they prevent wrong-target flashes); cal silence gate stands (not dev-blocking). Restore-baseline for 1401 still recorded before each probe flash. | — decided |

## 6 · Pre-mortem (updated, top kill-risks)
1. **Physical seam is ugly regardless of firmware** (bezel gap, LED batch bins, LGP edge) → day-zero photo kills M2 for an hour's cost, M1 unaffected.
2. **Clock/lateness physics fail the gate** → M1 still ships on the looser budget; M2 parks with numbers on record.
3. **Core-0 regression / heap dip** (BT controller immovable; 2026-07-05 crash precedent) → gate criterion 4; MabuTrace evidence; interference A/B closure before any production flip.
4. **Widened roster disappoints** (~8 stateless modes, no beat-locked showpiece in M2 v1) → stated plainly at F4/M2 go-no-go; v-b + Phase-3 determinism is the expansion path.
5. **Guard blind spot:** the radio-isolation guard's token list is BLE-Remoted-specific — a sync TU (especially ESP-NOW) would be invisible to it → guard token extension ships **with the first sync source**, not at Phase 4; the dirty `k1_upload_guard.py` edit is committed before any env work.

## 7 · Phased plan (all bench-class until F1; every phase gated + committable)
- **Phase 0 — Kill tests & physics** (needs F5 for anything touching 1401):
  0a. Day-zero physical seam trial (zero firmware, photos, ~1 h).
  0b. Commit the guard re-block; extend radio-isolation guard tokens; register two pin-map-specific probe envs (bench GPIO 4/5 + IM73D vs main 6/7 + SPH — mic confound stated) in guard + registry.
  0c. Transport bake-off (A, A′, B) measuring the four gate numbers; wired GPIO cross-trigger between units as the sub-µs timing reference; seam-crossing stimulus added to k1_motion_probe; interference A/B closure attempt.
  **Gate:** four numbers green for at least one transport → M1 proceeds; seam-budget number + photo decide M2's fate.
- **Phase 1 — Sync engine, host-first:** versioned wire protocol (replay contract), control policy table (71 rows, harness-asserted), adoption classes (harness-asserted no-cal-persistence), role/pairing/persistence + factory-reset semantics, link supervision. Host harness = **two processes** (firmware globals are inline — one process cannot host two instances) replaying one capture, asserting convergence, loss, rejoin. **Gate:** host green + bench link soak.
- **Phase 2 — M1 twin sync on devices:** replay rendering, AGC/hue adoption, apply-at mode changes, acquisition/fallback UX. **Gate:** two-device eyes-on — beat simultaneity across all 22 modes, character parity vs solo baseline.
- **Phase 3 — M2 widened (contingent):** v-a windowed stretch + flip + BLOOM/river special cases, roster clamp, widen↔unwiden slew, per-mode speed/character retune (explicit scope line), F3 executed. **Gate:** eyes-on — seam continuity AND per-mode character parity. v-b native-arm upgrade only after v-a survives.
- **Phase 4 — Productionisation (requires F1):** radio stance flip, guards/registry/docs/OTA, re-read the Tier-0 launch docs in the landing-page workspace (`LAUNCH_LOCKS.yaml` lives there, not in this repo), Captain sign-off.

## 8 · Red-team ledger (consumption)
| Lens | Verdict | KILLs | Disposition |
|---|---|---|---|
| Perceptual | FLAWED | 1 (mechanism conflation) | ✓ re-run confirmed (ember half-canvas); §1 rewritten, product reshaped M1→M2, day-zero trial added, roster honesty in §2/§6 |
| Timing | SOUND_WITH_FIXES | 2 (identical-inputs violation; wrong Phase-0 gate) | Replay contract §3; 4-number gate §4; 33 Hz batching; RTT clock sync; back-dated re-anchor; Core-0 honesty (✓ re-run sdkconfig) |
| Engineering | SOUND_WITH_FIXES | 0 | Control policy table (✓ re-run cal paths in facade); chroma/injection-mux; device reality → F5 (✓ re-run registry); guard timing → Phase 0b; role-file reset semantics |
| Doctrine | SOUND_WITH_FIXES | 0 | Cal never-adopt classes; UF2 framing symmetrised; launch-lock referent corrected; F1 includes scheduling; 1401 authorisation = F5 |

Full attack lists: `findings/redteam-*.md`.

## 9 · Non-goals
No canvas widening (`NUM_FREQS` coupling). No pixel streaming. No re-unification of one device's two channels. No >2-device mesh. No production radio change without F1. No 1401 flash without F5. No Tab5/K718 protocol breakage. No implementation in this lane (Captain scope decision 2026-07-08).

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code | Created — DRAFT v0.1 evaluation + phased plan from 9-SSA evidence base. |
| 2026-07-08 | agent:claude-code | v1.0 — consumed 4-lens red team (3 KILLs, 13 MAJORs): corrected mechanism story (v-a/v-b), restructured to M1 twins → M2 widened, replay contract, 4-number Phase-0 gate, control policy table, day-zero seam trial, forks F1–F5. All decisive claims orchestrator re-run. |
