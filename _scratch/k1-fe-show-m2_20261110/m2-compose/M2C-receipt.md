# M2 lane C (m2-compose) receipt — 10 Nov 2026

**What happened.** The whole creator loop now runs on the real Loreen recording through PRISM, not an ad-hoc script. The steps are: composition, then the locked PRISM compiler (0.3.1, cc00556d), then ShowBundle and Intent Trace, then one authored edit, then save, reopen and recompile, then the VM, then a `.prsm` stream with its sidecar. After reopening, every hash came out the same, and so did the stream. The edit changed exactly what was predicted before the comparison was made. The stream is VALID and BENCH-ELIGIBLE. It has been handed to m2-emu. No device was touched.

## Problems first

1. **The editor cannot do this loop itself (PRISM defect, reported, not fixed).** `prism_minimal_editor/server.js` `/api/instrument/compile` calls the compiler with `--contract/--stem-features`. Compiler 0.3.1 expects `--in/--stems` and also requires `--coverage-out/--manifest-out`, so the endpoint always fails. The default `compiler_commit` is hard-coded to `e37c7da`, not the lock. Evidence: `raw/f4_editor_probe.log` (HTTP 500 with the compiler's usage error). `/api/instrument/profile` accepts only `prim8_natural_v1` and `prim8_natural_v1_1`, so an authored profile is refused (HTTP 400). `app.js` has no call to the compile endpoint. The editor's only save API (`POST /api/bundle`) saves ShowBundle edits, which a recompile overwrites. That kind of edit is excluded as authorship.
2. **The Spine CLI cannot compile an edited composition (Spine defect).** `tools/instrument.mjs` hard-codes `mapping/prim8_natural_v1.json`. `verify --project` ignores `inputs.mapping_profile_path`. `writeBuildManifest` hard-codes `compiler_version …/0.3.0`, but the compiler is 0.3.1. The tool also writes into its own `.tmp/`. My workaround is the thin driver `tools/compose.mjs`. It runs Spine `compileOnce` and `verifyFixture` with the same compiler flags, the same cwd `/tmp` and the same replay call. It imports Spine's own `evaluateCoverage`, `validateProject` and `validateProfile` read-only. All its outputs go to this folder.
3. **No section-scoped authoring exists.** `mapping_profile_v1` and compiler 0.3.1 have no per-segment scope, so the edit applies to the whole track. That is a gap against the brief's "one named section".
4. **Analysis defect seen in the edited stream (m2-analysis / Trinity allin1).** Between 18 and 30 s, 17 of 30 beats are marked as downbeats (21.48, 21.84, 22.20 s and so on). The bar-accent edit therefore keeps full-strength impact on almost every beat there. Further caveats from the lead: contract bpm 125 and 6/4 are wrong, and nothing here reads them. The raw contract fails the adapter, so the consumer contract with its 9.98 ms last-segment clamp was used. Stems are not reproducible from source, and the retained cache is the reference. [INFERENCE] The "chorus" label at 106.16 s sits on falling energy, with texture and mass near zero; see the plot.
5. **Editor binds all interfaces.** `server.listen(PORT)` passes no host. I forced 127.0.0.1 with a preload (`tools/editor_localhost_preload.mjs`), which modifies no PRISM file. Bind proof: `raw/f4_editor_bind.txt`. The server was stopped after the probe.
6. **My own prediction error.** I predicted 26,869 frames for Loreen. The VM's `ceil(223,910,023 µs × 120 / 1e6)` gives 26,870, and the stream has 26,870. My arithmetic was wrong; the chain is correct.

## Chain hops proven

| Hop | Fixture `ci_click_3s` | Real: Loreen, full track 0–223.91 s |
|---|---|---|
| Composition (Spine `instrument_project_v1` + `mapping_profile_v1`) | `projects/ci_click_3s/composition.json` | `projects/loreen/composition.json` |
| Compile ×2 (A04) + manifest integrity + coverage gate | PASS (`raw/f2_*`, `raw/f6_*`) | PASS (`raw/r2_*`, `raw/r5_*`) |
| Pre-edit result matches the Spine golden | ShowBundle 6a0678c2…, trace bcdd0c22… (= G5 expected) | n/a |
| Editor preview `/api/replay` = Intent Trace | PASS: sha bcdd0c22… (`raw/f4_editor_probe.log`) | not run |
| Edit, save, reopen, recompile: identical | PASS (`raw/f7_reopen_verify.log`) | PASS (`raw/r7_loreen_reopen_verify.log`) |
| VM → `.prsm` frames byte-equal to PRISM `cdc.js makePrsmPacket` | PASS, 360 frames | PASS, 26,870 frames |
| Reopened project regenerates identical `.prsm` and sidecar | PASS (`raw/f7_reopen_stream_sha.txt`) | PASS (`raw/r8_loreen_reopen_stream_sha.txt`) |
| `validate_prim8_stream.py` (run once) | VALID | VALID |
| `audit_prsm_bytes.py --guard 30` (run once) | BENCH-ELIGIBLE 360/360, 0 hotkeys | BENCH-ELIGIBLE 26870/26870, 0 hotkeys |

## Hashes (sha256)

| | ShowBundle | Intent Trace (120 Hz) | `.prsm` |
|---|---|---|---|
| Fixture pre-edit | 6a0678c2…71ba0 | bcdd0c22…ae2b8 | 81f521d7…9254 |
| Fixture post-edit = reopen | 648c052a…4e84 | 23439c6c…aeb9 | ee4577aa…55d8 |
| Loreen pre-edit | cae4fbc1…e1e1 | 9491b071…28ce | 65143215…eba1 |
| Loreen post-edit = reopen | 90855dde…801b | 8128452f…1bde | **116981ee920f9006954357293bc91ff5b2d02ddb06fff72e24de56951b5e97e3** |

The full list is in `raw/sha256_all.txt`. Inputs: consumer contract f17a0c05…e793; stem_features 9053c7ad…6052; contract schema 3d521f5d… (Trinity e271af39). Asset: mp3 a62e1f09…9b0f, decoded wav b3fafd33…1415, 44.1 kHz, 2 ch, 9,874,432 samples. Settings: passage_start_sample 0, hz 120, one epoch e0 with seq 0…26869, device_profile "none".

## The edit, and what it changed

- **Edit:** bar accent. `prim8.impact.transform.beat_amp_u16` changes from 48000 to 12000. It was made through `compose.mjs edit`, which writes a new profile `prim8_natural_v1_bar_accent` (derived_from v1 ec285a50…) and saves the composition.
- **Intent:** declared before comparing, in `raw/f5_edit_intent_DECLARED_BEFORE_COMPARE.md` and `raw/r4_loreen_edit_intent_DECLARED_BEFORE_COMPARE.md`.
- **Result for Loreen** (`projects/loreen/diff/stream_diff.json`), verdict MATCH:
  - Only impact (Prim8[1], the device's novelty input) changed: 1,582 frames in 331 windows, one per off-downbeat beat. Each window is the 40 ms after the beat.
  - The new value equals the old value × ¼, within ±1.
  - The 131 downbeat pulses are unchanged.
  - Only frame bytes 20–21 differ. Channels 0, 2, 3, 4, 5, 6 and 7 are byte-identical.
- **Fixture:** 20 frames in 4 windows, MATCH.
- **Plots** (I have looked at both): `projects/loreen/diff/stream_channels.png` (with a zoom on 106–110 s) and `projects/ci_click_3s/diff/stream_channels.png`.

## Gates and status

- Fixture loop: PASS.
- Real loop: PASS.
- Validator and audit: PASS, each run once per delivered stream.
- Trinity pytest: NOT RUN (out of scope).
- Device or emulator playback: NOT RUN here; that is m2-emu's G4.
- Mutation testing: none.
- Writes: only to this folder, plus `laneb_byte_audit_*` in the system temp folder, which lane-b's audit builds there itself.
- No git writes. No changes to the Spine, PRISM or Trinity trees.

## Ship path

- **Done:** host chain on the real track, with VALID and BENCH-ELIGIBLE stream bytes.
- **Remaining:**
  1. m2-emu plays the stream in the emulator (G4).
  2. Fix defects 1–2 so the editor and Spine CLI can run this loop themselves. That needs a PRISM or Spine owner change and was not done here.
  3. Add section-scoped mapping (3) if per-section authorship is required.
  4. Get the Captain's eyes-on of the bench playback.
- **What counts as shipped:** the emulator G4 PASS on sha 116981ee…, followed by bench playback.

## Changelog
- 2026-11-10 agent:m2-compose — created: fixture and real-track loops, tools, evidence.
