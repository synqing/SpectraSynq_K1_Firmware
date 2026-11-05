================================================================================
K1 S3 FOLLOW-UP BRIEF — CLOSE THE LANE (supersedes the previous brief)
Repo: /Users/spectrasynq/SpectraSynq_K1_Firmware   Branch: lane/k1-fe-release
HEAD: 19992ad7   Bench: B489, /dev/cu.usbmodem101
Normal env: k1_fe_bench_b489   Diagnostic env: k1_fe_bench_b489_trace_dev
Scratch (only one): _scratch/s3-repair-20261105/   (continue in it, subdir followup/)
British English. Explain every abbreviation once. Times in Perth (AWST).
================================================================================

0. RULES (unchanged from the previous brief, restated because they bind)
0.1 DO NOT STOP until section 8 is complete. The only permitted stops:
    B489 unreachable after one retry; a truly irreversible change needing
    Captain approval. A failed gate, failed capture, rejected candidate,
    missing file or any question of method is NEVER a reason to stop.
0.2 Three different approaches per item, then mark it OPENith evidence
    and move on. Never ask the Captain a technical question.
0.3 No new tooling. Timing sections in product code are allowed.
0.4 No sleep or blocking waits over the bridge. nohup + poll.
0.5 PASS only from exit codes against a baseline produced by a different
    build. Never grep for PASS. Never hand-write PASS.
0.6 Timing numbers carry env, sha, MHz, flags file, silicon/host.
0.7 One commit per completed item. No push. Receipts + gates.json entry
    per item.
0.8 Cadence authority: contract.json vp_contract.admission (p99 ≤ 8,333,
    mean ≤ 8,333, ≤ 1 consecutive miss, recovery ≤ 2). Effect ceiling
    2,000 µs per effect call.
0.9 Performance-only byte gate: ±1 per RGB8 byte, identical lit-pixel
    masks, ≤ 0.1 % bytes differing. Corrections use their own expected
    result written before the fix.
0.10 Do not edit k1_tempo.cpp, k1_onset_beat.cpp, novelty, AGC, GDFT, or
    saved calibration constants.
0.11 ORCHESTRATOR owns B489 and the branch. Workers (section 7) never
    vice or lane/k1-fe-release.

1. NEW RULE — SAME-CONDITIONS CAPTURES (this is why the last campaign's
   before/after numbers are worthless)
1.1 Every before/after timing comparison in this lane uses ONE capture
    recipe, frozen in followup/capture-recipe.json before any capture:
    env k1_fe_bench_b489_trace_dev; the SAME fixed audio clip from the same
    start offset, played through the same route at the same volume;
    secondary mode fixed at 18 for every run; same look settings; same
    capture duration; the mode under test as primary. Record the recipe's
    sha256 in every receipt.
1.2 "Before" = commit 9f3eb18e built with the identical flags file, captured
    under 1.1 in THIS session. Do not reuse the 5 Nov numbers as "before".
1.3 A number captured under any other conditions is not evidence in this
    lane. Discard it.

2. REGRESSION TRIAGE (sequential, before anything else)
2.1 Mode 27 (Tempo Comet Anticipate) was dark for its whole 28-mode window.
    Capture mode 27 under 1.1 on HEAD anon 9f3eb18e. If HEAD is dark and
    9f3eb18e is lit → regression. Bisect across 83c44797 (tempo consumer
    flag moved to bench env), 9a5e08a8/62d93cca/742b5aeb (presence floor),
    d143c3ac (silence drain). Fix the cause. Expected result: mode 27 lit
    frames under music within 10 % of 9f3eb18e's count, dark on quiet.
    If both are dark, mode 27 was already dark; record that and move on.
2.2 "Rendered VU modes are disabled." Establish exactly what that means:
    which modes, by which commit, by which flag or code path. If any
    session commit disabled a shipping mode, undo it and re-verify VU
    (mode 5) and VU Dot (mode 9) under the nine-window line test and one
    mic capture: quiet dark, music lit. If they were disabled before this
    lane, record the commit that did it and leave it.
2.3 Commit: `fix(fe): restore tempo comet anticipate / VU rendering` as
    applicable.

3. RIVER LOOKUP — KEEP OR REVERT (data decides, same conditions)
3.1 Build A = HEAD. Build B = HEAD with 36607a8f, 10d8 and 7cf8a315
    reverted (git revert, keep the reverts on a temp branch until decided).
3.2 Capture modes 14, 15, 19, 28, 29 under 1.1 on A and on B. One capture
    each, all five modes in sequence per build.
3.3 Decision rule: keep the lookup only if every one of the five is faster
    on A than on B by more than the run-to-run noise (measure noise by
    capturing B twice; noise = the larger of the two |diff|s per mode).
    Otherwise commit the reverts to the lane. No partial keeps.
3.4 Commit: `perf(s3): retain river hue lookup (measured)` or
    `revert(s3): river hue lookup slower under same-conditions capture`.

4. FULL HOST SUITE (close the open gate)
4.1 nohup python3 -m pytest tests -q > followup/host-suite.log 2>&1 &
    then poll. Required: 0 failed. If anything fails, fix it (test or
    code, whichever is wrong, with the reason written), rerun. Up to three
    runs.
4.2 Receipt with exit code and counts.

5. EFFECT CEILINGS — STOP OPTIMISING, PRODUCE THE DECISION PACK
   Nine micro-optisation attempts moved these effects by ±5 %. That
   approach is closed. The remaining choice is design vs ceiling, and the
   Captain decides by LOOKING, so the deliverable is visual and measured.
5.1 Per-section cost table (one capture per effect under 1.1, trace_dev,
    with sub-scopes covering ≥ 90 % of the effect body): for each of
    modes 14, 15, 19, 21, 24, 28, 29 list every section, its max and p99
    µs, and its share of the total. followup/effect-cost-table.json.
5.2 For each of the seven, implement ONE cheaper design variant behind a
    bench-only compile flag (K1_BENCH_FX_LITE_<MODE>=1 in the trace_dev
    env only; product env untouched). The variant must keep the effect's
    identity (same movement direction, same colour source, same beat or
    spectrum driver) and may reduce: pixel-pass count, per-pixel trig,
    history blend passes, sprite width, update rate of a slow-changing
    term. Target ≤ 1,800 µs measured. Three variants maximum per effect;
    keep the fastest that stses a visual sanity rule you state
    (e.g. "dot still travels", "river still scrolls", "chord colour still
    tracks").
5.3 Measure each variant under 1.1. Record max and p99 effect µs, cadence
    four numbers, and the byte-diff size vs the stock effect (this is a
    design change, so no ±1 gate; the diff size is informational).
5.4 VISUAL PACK (this is what the Captain reads): for each effect, a
    contact sheet PNG built from the captured RGB8 frames of stock vs
    variant on the identical clip window: 24 evenly spaced frames each,
    rendered as 160-pixel horizontal strips, stock on top, variant below,
    with the frame timestamp and the measured µs printed beside each row.
    Use the existing frame-to-PNG path that produced
    device-reciprocal-frames.png on 5 Nov; do not write a new renderer.
    Output: followup/visual/<mode>-stock-vs-lite.png (seven files) and one
    index PNG tiling all seven.
5.5 CEILING OPTION, numerically: for each effect, state the smallest ceiling
    in µs that STOCK effect passes at p99 under 1.1, and whether the
    frame still meets 8,333 at p99 with that effect plus secondary 18.
    followup/ceiling-option.json. No recommendation to change the contract
    is to be written into any authority doc; this is a numbers table.
5.6 Nothing from 5.2 is merged into the product env. The variants stay
    behind the bench flag on the lane branch. Commit:
    `bench(s3): lite effect variants and visual decision pack`.

6. FINAL
6.1 Flash normal env k1_fe_bench_b489 at the final commit. Confirm with the
    `build` handshake.
6.2 One 28-mode capture on the normal build (existing all-mode function).
    Mode 27 and the VU modes must be lit under music.
6.3 Restore every saved setting, look, calibration 108/57, microphone/auto,
    AP (audio-processing) streaming state and the audio route; verify with
    the settings-dump comparison; exit code in the receipt.
6.4 Update README.md and docs/hardware/device-build-registry.md with the
    same-conditions numbers, replacing the 19992ad7 table. Commit:
    `docs(fe): same-conditions results and effect decision pack`.
6.5 No push.

7. SWARM (parallel where the device is not needed)
7.1 Orchestrator: sections 1, 2, 3, 4-launch, 6, all device captures, all
    merges. Workers in git worktrees branched from HEAD, one scratch subdir
    each, capture requests via followup/queue/<stream>-<n>.json serviced by
    the orchestrator in this priority: triage (2) → river A/B (3) →
    variant captures (5) → final (6).
7.2 Streams, launched after section 2 is settled:
    - R  river A/B revert branch preparation and, after 3.4, river variants
         (14, 15, 19, 28, 29). Files: the five river effects + their helper.
    - F  forge variants (21, 24). Files: the two forge effects.
    - V  visual pack builder (5.4) — host only; consumes captured frame
         files as they land; no device.
    - C  cost tables and ceiling-option json (5.1, 5.5) — host-side
         analysis of trace exports as they land; no device.
    - H  host suon 4) — host only, from the start, in the main
         checkout but never committing.
    File ownership is exclusive. Nobody but the orchestrator edits
    platformio.ini, the acceptance file, the contract fixture, README or
    the registry doc.
7.3 Each worker ends with followup/sw-<stream>/REPORT.md in the section-8
    format scoped to its stream. The orchestrator opens every worker's
    receipts, diffs and PNGs itself before using them. A worker that stops
    without a REPORT.md is relaunched once; twice → stream OPEN, lane
    continues.

8. FINAL REPORT (one report, at the end, plain English, bullets, fewest
   words; no interim reports)
8.1 Changed artefacts: path + one line + commit sha.
8.2 Gates: gate · command · exit code · receipt path, failures and OPEN
    items included.
8.3 Measured numbers: capture recipe sha; for each of the seven effects:
    stock µs (same-conditions before), stock µs on final HEAD, best lite
    variant µs, cadence four numbers; river A vs B table with no    path unchanged confirmation; full suite counts.
8.4 Not verified: every OPEN item with its three approaches and evidence.
8.5 Decisions for the Captain, exactly two, each with the file to open:
    (a) per effect: ship stock, ship lite variant, or redesign later —
        open followup/visual/index.png;
    (b) whether the 2,000 µs per-effect ceiling is amended for named
        effects — open followup/ceiling-option.json.
    Nothing else. No method questions. Under-claim.
================================================================================

$global-skill-router $thinking-toolkit:thinking-router $thinking-toolkit:thinking-red-team $thinking-second-order $context-engineering-corpus:context-engineering-router $context-engineering:context-stack $spectrasynq-workflow $orchestrator-briefing-discipline $codex-subagents $ssa-management $ssa-management