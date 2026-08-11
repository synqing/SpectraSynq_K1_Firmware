# Tab5 session failures and engineering canon — 2026-08-11

Status: **load-bearing**  
Scope: Tab5 ESP32-P4 dashboard, hosted BLE state transport, LVGL ownership,
display presentation, typography, and procedural palette previews.  
Target identity: ESP32-P4 MAC `30:ed:a0:e0:c1:a0`; always pass the port
explicitly. The session port was `/dev/cu.usbmodem12401` (also reported as
`/dev/tty.usbmodem12401`). Port names are observations, not identity.

This document exists because multiple technically green changes failed the
actual product requirement. It records what happened, why it happened, what
fixed it, and the executable rule that prevents recurrence. It is not a release
claim and does not supersede the G0–G3 receipts.

## Executive laws

1. **LVGL has one owner: loopTask.** NimBLE callbacks may copy bounded records
   into queues; they may not mutate Deck state, LVGL, connection lifecycle, log
   verbosely, allocate, or execute HCI work.
2. **A green map is not the territory.** Build success, static assertions,
   deterministic maths, a simulator still, and a clean serial log prove useful
   properties. They do not prove that motion looks fluid, that type is legible,
   or that the physical panel is free of tearing. Perceptual claims require a
   current native sequence and final eyes-on confirmation on the named device.
3. **Present complete frames.** Production uses one full logical RGB565 frame,
   PPA rotation into a hidden DSI framebuffer, two distinct panel framebuffers,
   and VSYNC retirement before reuse. Partial scanout is forbidden.
4. **Preserve native RGB565 byte order.** LVGL, PPA, and the DSI framebuffer use
   native little-endian RGB565; `operation.byte_swap` is `false`.
5. **Size text from glyph metrics and worst-case content.** Berkeley Mono 55 is
   33 px per cell; `100%` needs 132 px before inset. Nominal font size is not
   rendered width or optical height.
6. **Palette previews share one motion field.** Primary and Secondary may use
   different palette LUTs, but they consume the same coordinate and light field
   for the same pixel and frame. Independent phases are forbidden.
7. **Water-like motion is a two-dimensional topology, not a translated strip.**
   The field needs curved cross-height flow, bounded non-folding deformation,
   smooth non-periodic velocity evolution, subpixel sampling, and visible but
   restrained caustic modulation.
8. **Palette colour stops must be integrated.** Subpixel interpolation alone
   does not remove narrow hard bands. Prefilter the circular palette in
   approximate linear light before spatial sampling.
9. **Callbacks, queues, snapshots, and deltas fail closed.** Loss, oversize,
   timeout, corruption, revision gaps, ambiguous statuses, or generation
   discontinuity retain last-known-good state and require a complete resnapshot.
10. **Never claim `fixed`, `fluid`, `organic`, `smooth`, `best`, or `production`
    beyond the evidence actually observed.**

## Incident and resolution inventory

| # | Observed failure | Root cause / failed assumption | Resolution | Durable prevention / proof |
|---|---|---|---|---|
| 1 | `BLE_ERR_UNK_CONN_ID` repeated every ~0.5 s | `05 14 02 00 00` was HCI Read RSSI (`0x1405`) for handle `0x0000`; status `0x02` meant the controller no longer owned that connection. Handle zero itself is legal. | Cache RSSI; one bounded operation in flight; classify invalid handle and recover through the loop-owned state machine. | `test_tab5_g2_transport_static.py`; G2/G3 receipts. A prompt Command Complete proves the exchange, not connection health. |
| 2 | IDLE0 watchdog named `nimble_host` | The RSSI spam was downstream smoke. The captured PC/RA symbolised to `lv_inv_area`; LVGL's assertion self-loop was entered because a NimBLE `onWrite` path changed widgets while loopTask rendered. | Callbacks enqueue bounded payload/link records only. loopTask drains and performs Deck/LVGL mutation. | G1 M1 mutants; G3 100-cycle silicon proof. Re-symbolise against the exact flashed ELF whenever image identity differs. |
| 3 | Host state remained connected while the controller rejected handle zero | The wedged host could not run disconnect cleanup; `gConnected`/`gConnHandle` were also an unsynchronised cross-core pair. | One loop-owned connection state machine with handle + generation; callback events are tagged and deduplicated. | G1 M2/M7; G2 transport tests; G3 zero stale RSSI completions. |
| 4 | Initial G0 source closure passed, then reopened | A clean build did not prove complete authority. `docs/protocol/k1-deck-state-v1.md` was absent and Tab5 carried a 68-control/old digest while K1 authority had 71 controls/new digest. | Track the protocol document; regenerate and checksum JSON, K1 header, Tab5 header, identity, and generator parity; rerun disposable empty-cache builds. | G0 reopen notice; G1 M9. Buildability is not protocol compatibility. |
| 5 | A G1 positive oracle risked becoming theatre | Current firmware initially violated the intended rules, so testing only an independent fixture could not claim source conformance. | Use the fixture to prove every mutant is detectable, then rerun unchanged oracles against hardened production source in G2. | 35/35 M1–M9 mutants killed; G1 claim boundary. |
| 6 | Queue loss could silently continue | Drop/oversize counters alone do not preserve state consistency. | Any relevant loss sets a desynchronised latch, preserves last-known-good state, and blocks deltas until a complete valid snapshot commits. | G1 M3; transaction harness; G2 receipt. Queue depth is capacity tuning, not correctness. |
| 7 | Snapshot and delta members could apply before transaction validation | Incremental mutation exposed partial state when END/CRC/count/member checks later failed. | Bounded static staging; validate the entire transaction before the first confirmed-state or LVGL mutation; commit once from loopTask. | G1 M4–M6; `deck_state_rx_transaction_harness.cpp`. |
| 8 | Valid HELLO/SNAPSHOT could be lost at connect | `apply_connected()` purged the payload queue while link events were drained before payloads. | Do not purge valid queued payloads; exact-match handle and ingress generation. | G2 code review regression. Ordering must be tested, not inferred from queue presence. |
| 9 | CLAMPED/REJECTED could leave or erase pending state incorrectly | Protocol v1 has no request correlation ID; value equality cannot distinguish delayed A from identical newer B (ABA). | All non-ACCEPTED statuses fail closed before mutation or revision advance and require resnapshot. | G2 code review; ACCEPTED/REJECTED/CLAMPED harness cases. |
| 10 | Verbose production diagnostics remained possible | A diagnostic build flag existed but call sites were unconditional or convention-controlled. | Compile-time production invariant rejects HCI or per-value diagnostics. | G1 M8; production build. Release safety must not depend on memory. |
| 11 | Work targeted or reasoned from the wrong lane/baseline | The active checkout, global lane metadata, and live image were not always the same thing. | Freeze a Tab5-specific worktree/baseline; state branch, HEAD, dirty state, device identity, and claim boundary before edits or flash. | G0 receipt and nested `tab5_firmware/AGENTS.md`. |
| 12 | Agent treated the Tab5 as unavailable despite USB presence | Port recollection and stale skill examples displaced live enumeration and identity. | Enumerate every time; verify P4 chip + exact MAC through `flash_tab5_p4.sh --verify-only`; never infer absence from a remembered port. | Identity guard refuses wrong targets before write. Session port: `usbmodem12401`. |
| 13 | Full brightness displayed as `00%` | The leading `1` in `100%` was clipped: a 104 px label could not hold four 33 px Berkeley Mono cells. | Width 144 px, right-aligned, with 8 px inset. | `test_full_scale_percent_value_cannot_clip_its_leading_digit`; commit `e48d65c`. |
| 14 | Bottom-row page changes redrew in visible staggered pieces | Partial LVGL flushes were copied/rotated into the visible panel while it was scanning out. More generic heap alone would not fix presentation semantics. | Full logical frame in PSRAM; PPA rotate complete frame; submit hidden DSI buffer; swap only at VSYNC; wait before buffer reuse. | `test_tab5_render_pipeline_static.py`; commit `e48d65c`; silicon eyes-on. |
| 15 | Screen colours appeared inverted/corrupted | PPA byte-swapped RGB565 even though source and destination were already native-endian. | `operation.byte_swap = false`. | Static contract; commit `3062da5`. |
| 16 | Palette preview was static | The product path did not update the swatch pixels at bounded animation cadence. | 16 ms animation cadence with 50 ms dt clamp and static buffers. | Commit `95d422b`; current render static test. |
| 17 | First “organic” motion still looked like the old implementation | Easing and randomised speed were applied to a one-dimensional translated strip. The dynamics changed; the perceptual topology did not. | Replace translation with a sampled spatial field. | This is the session's principal map–territory failure. Commit `b0c2cde` is historical evidence, not the final design. |
| 18 | Primary and Secondary moved out of phase | Separate state made adjacent views disagree about the same implied flow. | One shared `PaletteFlowState` and one shared per-frame field; both palette consumers sample identical coordinates and lighting. | Current `palette_flow` harness and integration static test. Commit `0a07e73` aligned phase but remained one-dimensional. |
| 19 | Shared motion still looked rigid and predictable | Alignment alone retained evenly spaced horizontal waves and a visible conveyor-belt character. | Three bounded travelling modes, independently eased velocity channels, cross-height phase offsets, non-folding Jacobian, 2D field, and caustic light modulation. | `palette_flow_harness.cpp`: deterministic pairing, >500 changing samples over a 10-minute jitter soak, 2D row difference, Jacobian >0.60, meaningful light range. |
| 20 | Colour bands remained harsh after the 2D field | Sampling blended positions but not palette stop energy; adjacent narrow stops still formed hard stripes. | Circular 11-tap triangular prefilter using squared-channel accumulation as an approximate linear-light integration, then subpixel LUT sampling. | `test_palette_preview_uses_one_shared_subpixel_spatial_field`; screenshot `flow_2d_blended_1900.png`. |
| 21 | Rotating `PRIMARY/SECONDARY PALETTE` 90° appeared to reclaim space but did not fit | Measured title widths (about 191/217 px) exceeded the 147 px widget height; rotation would overrun or force illegible shrinkage. | Keep horizontal titles and spend the space on 36 px visual swatches. | Optical measurement pack under `_scratch/tab5_palette_flow_20260811/`. |
| 22 | Font choice risked becoming taste-by-chat | Available faces were not compared by role, optical size, density, or brand behaviour. | Auditioned 180 intentional candidate files. Keep Countach Bold Italic for hero indices only and Berkeley Mono for all words, controls, state, and instrument values. | `deck_type.h`; `font_inventory.json`; role ladder receipt. The selected inventory identifies both Countach and Berkeley Mono source assets as TRIAL. Both remain bench-only until embedded commercial licences or replacements exist. |
| 23 | Progress devolved into busy-work loops | After direct perceptual rejection, effort drifted toward more explanations, tests, and small parameter changes instead of changing what the user could see. | OODA re-entry: observe the current physical/native result, name the perceptual defect, choose the smallest mechanism-level change capable of falsifying it, act, and re-observe before claiming success. | Required by the motion skill and nested agent contract. More proof is valuable only when it can falsify the current claim. |
| 24 | G3 receipt declared the lane closed beyond its durable evidence | The 100-cycle reconnect proof was strong, but the originally approved dense fault soak and 45–60-minute ordinary production soak were not completed; only identity-MD5 fault recovery is durably recorded. | Corrected the receipt to distinguish `WDT_RSSI_RECONNECT_REPAIR=PASS` from `FULL_G3_FAULT_AND_ORDINARY_SOAK=NOT_VERIFIED`. | Acceptance thresholds are immutable once execution begins. Missing rows produce PARTIAL/NOT_VERIFIED, never retroactive closure. |
| 25 | A final P4 rebuild intermittently resolved the wrong shared framework package | The mutable global PlatformIO package cache had been replaced with Arduino 3.2.0 metadata while this project pins the official 3.3.1 archive. The checksum guard correctly refused to patch it. | Rebuilt with a dedicated empty `PLATFORMIO_CORE_DIR`; the isolated resolver fetched 3.3.1, passed every overlay checksum, and produced the final binary. | Release/source-closure builds must use an explicit task-owned PlatformIO core. A shared cache is an optimisation, never authority. |

## Canonical architecture

### BLE and state

```text
NimBLE callback (Core 0)
  -> bounded copy to link/payload queue, tagged with handle + generation
  -> return

loopTask (Core 1)
  -> drain link events
  -> drain exact-generation payloads
  -> stage and validate complete transaction
  -> one confirmed-state commit
  -> LVGL mutation
  -> bounded connection/RSSI recovery state machine
```

Forbidden in callbacks: `String`, heap allocation, per-value logging, Deck/UI
mutation, advertising/lifecycle work, synchronous HCI, or unbounded retries.

### Display presentation

```text
LVGL renders complete 1280x720 logical RGB565 frame in PSRAM
  -> PPA rotates complete frame into hidden 720x1280 DSI framebuffer
  -> panel submits hidden buffer
  -> VSYNC retires it
  -> front/back pointers swap; old front is not reused early
```

The P4's PPA is used for rotation. It does not make partial-frame scanout atomic,
choose colour endianness, or remove the need for two panel framebuffers.

### Palette preview motion

```text
one shared `PaletteFlowState`, dt-clamped
  -> smooth random target velocities
  -> 2D non-folding coordinate field + light field
  -> circular linear-light palette prefilter
  -> Primary LUT and Secondary LUT sample the same coordinate/light cell
  -> update static RGB565 buffers at bounded cadence
```

Randomness is used to schedule smooth target changes, not to inject per-frame
jitter. “Unpredictable” means non-repeating evolution with continuous velocity,
not noise.

## Two-rail acceptance contract

### Rail A — mechanical safety

- no heap or `String` in callbacks or palette/render hot paths;
- deterministic bounded dt and one-in-flight maintenance work;
- non-folding field and static memory bounds;
- complete-frame PPA/VSYNC presentation;
- native RGB565 order;
- full transaction validation before mutation;
- identity-first explicit-port flash;
- host tests, P4 production build, serial stability, memory stability.

### Rail B — perceptual territory

- inspect at least three frames from one continuous native run, not three
  separately seeded launches;
- inspect the physical Tab5 for motion continuity, synchronisation, banding,
  tearing, colour, clipping, and interaction transitions;
- compare before/after at the same state and elapsed time;
- Captain's direct eyes-on rejection reopens the gate even when Rail A is green;
- record the exact image/ELF/commit/dirty-state boundary.

Rail A can block a release. It cannot pass Rail B.

## Remaining risks — not silently closed

- The current field Jacobian is about `0.614`; it passes the `>0.60` non-folding
  threshold with limited margin. Do not increase deformation without measuring
  the new bound and re-observing the result.
- The blended LUT now has functional uniform-preservation, circular-wrap,
  symmetry, and 11-tap-support tests. It still needs representative high-contrast
  palette anchor-tolerance criteria derived from on-glass review.
- No durable high-frame-rate video or counters for PPA duration,
  `lv_timer_handler` duration, VSYNC waits, missed frames, or presenter faults
  exist for the current dirty palette workload.
- The G3 100-cycle evidence applies to `87d4091`; it predates the atomic
  presenter, endian correction, and palette work.
- The M5GFX double-buffer overlay and current uncommitted palette files were
  introduced after the original G0 source-closure proof. Re-run clean-clone G0
  before a new release claim.
- A clean build is not deterministic binary proof: absolute build paths changed
  ELF/app/bootloader hashes in G0 while source/build reproducibility still
  passed.
- The shared global PlatformIO package cache is mutable across projects. The
  final validation caught it carrying Arduino 3.2.0 metadata. Use an explicit
  isolated `PLATFORMIO_CORE_DIR` for release proof and trust the checksum guard.
- Both selected source inventories are marked TRIAL (`Countach` and `Berkeley
  Mono Trial Regular`) and remain bench-only until embedded commercial licences
  or replacements exist.

## Required adversarial mutants

The palette-motion gate must kill these failure classes for the intended reason:

1. vertical frequencies set to zero (collapses to 1D);
2. vertical effect technically nonzero but below the minimum visible displacement;
3. light modulation set to zero (no caustic depth);
4. independent Primary/Secondary motion state;
5. integer widget translation replacing subpixel field sampling;
6. circular linear-light prefilter removed (hard palette stops);
7. heap allocation introduced in the hot path.

The existing G1 mutation gate remains authority for M1–M9 transport/state/source
failure classes. A mutant that did not actually change the specimen is invalid;
a test that fails every mutant for the same unrelated reason is not evidence.

## Model synthesis: how to reason next time

- **Model selection/router:** classify this work as diagnostic + systems +
  perceptual evaluation. “Animation implementation” alone is too narrow.
- **Systems:** the dominant feedback loop was *green metric → premature claim →
  Captain rejects territory → parameter tweak → another premature claim*.
  Break it by requiring re-observation before the claim.
- **Map–territory:** source, metrics, maths, screenshots, and receipts are maps.
  The physical panel in motion is the territory.
- **Archetypes:** avoid *Fixes That Fail* (easing a bad topology), *Shifting the
  Burden* (tests replacing perception), and *Escalation* (more process after a
  visible rejection instead of a visible fix).
- **OODA:** Observe current motion; Orient to the exact complaint; Decide the
  smallest topology-level correction; Act; re-Observe. Never stop at Act/build.
- **Steel-man:** 1D translation was cheaper, deterministic, aligned, and easy to
  test. It was still the wrong solution because the product requirement was
  water-like spatial integration, not merely safe movement.
- **Red team:** attack the claimed perceptual mechanism, not only syntax. If a
  1D/no-blend/desynchronised mutant still passes, the gate is decorative.
- **Model combination:** system/map models choose the architecture; field maths
  and mutation tests constrain it; OODA closes the loop on the actual device.

## Rationalisations that are now forbidden

| Rationalisation | Required response |
|---|---|
| “The tests pass, so it is fluid.” | Tests prove named invariants only. Show a current continuous sequence and physical eyes-on result. |
| “It is random, therefore organic.” | Per-frame randomness is jitter. Organic motion needs continuous state and velocity. |
| “Both swatches use the same speed.” | They must consume the same coordinate/light field, not merely similar parameters. |
| “Subpixel sampling blends the palette.” | It blends sample positions; narrow stop energy still needs circular prefiltering. |
| “The P4 has an accelerator, so redraw should be smooth.” | PPA accelerates rotation. Atomic presentation still requires complete frames, hidden buffering, and VSYNC ownership. |
| “More queue depth fixes drops.” | Overflow is a synchronisation fault; latch desync and resnapshot. |
| “Handle zero is invalid.” | Handle zero is legal. Status `0x02` says that specific controller connection does not exist now. |
| “The watchdog named NimBLE, so BLE caused it.” | Symbolise the exact PC/RA. The task name identifies execution context, not root cause. |
| “The port used to be different.” | Enumerate live devices and verify chip + MAC. Never target by remembered port. |
| “A small visual nudge does not need re-observation.” | Small visual changes can be total perceptual failures. Re-observe the touched surface. |
| “One more document/test will show progress.” | Only add evidence that can kill a live hypothesis or prevent recurrence; otherwise change the product or stop. |

## Evidence and rerun index

- G0 source closure: `docs/receipts/tab5-hardening-20260811/G0_SOURCE_CLOSURE.md`
- G1 mutation proof: `docs/receipts/tab5-hardening-20260811/G1_MUTATION_RECEIPT.md`
- G2 hardening: `docs/receipts/tab5-hardening-20260811/G2_BEHAVIOURAL_HARDENING.md`
- G2 independent review: `docs/receipts/tab5-hardening-20260811/G2_CODE_REVIEW.md`
- G3 silicon proof: `docs/receipts/tab5-hardening-20260811/G3_SILICON_RELEASE_PROOF.md`
- Current optical/motion evidence:
  `tab5_firmware/_scratch/tab5_palette_flow_20260811/`
- Blended 2D screenshot SHA-256:
  `ddca3dcf5f76d59124431f8bd6db6ab6cb9fddbe0179c47b2c749897de680c8f`
- Current dirty P4 build hashes at canon capture:
  BIN `9a7e72541d4e370137298bd99919aaab70e564c90e92213d1fc0d62abc6708ac`;
  ELF `5d5ebc7745ae94b6a9528bc2300804191b77859bd9d9337846129b6d6100e959`.
- Presenter/value static tests:
  `tab5_firmware/tests/test_tab5_render_pipeline_static.py`
- Motion host harness:
  `tab5_firmware/tests/palette_flow_harness.cpp`
- Motion mutation guard:
  `tab5_firmware/scripts/tab5_palette_motion_mutation.py`

```sh
cd /Users/spectrasynq/SpectraSynq_K1_Tab5_Hardening
python3 -m pytest tab5_firmware/tests -q
pio run -d tab5_firmware -e native_sdl
pio run -d tab5_firmware -e tab5_p4
tab5_firmware/scripts/flash_tab5_p4.sh \
  --port /dev/cu.usbmodem12401 --verify-only
```

## Claim boundary at capture

- Last committed motion baseline: `0a07e73773761d3cbf373ccd967e5252173aa9b0`.
- The shared 2D field, 36 px swatches, circular prefilter, and associated tests
  were present as a dirty working-tree change when this canon was written.
- They had passed the then-current 18-test Tab5 host suite and P4 build. A live
  flash and stable short serial observation occurred during the interactive
  session, but no durable upload/serial/frame-timing receipt was written for
  this exact dirty binary. Do not promote the chat observation into release
  evidence.
- This is not a clean-commit, full G3, motion-timing, or long-duration
  production-promotion claim. Preserve the diff and repeat the two-rail gate
  after any source or binary change.
