# K1-FE-SHOW-M1 Rev 2 — Lane B: P1 contract, timebase, fixtures and validator

**Abstract:** Maps the prepared-input path (Trinity contract → PRISM ShowBundle 0.3 / virtual machine (VM) → 34-byte PRSM frame → K1 FE firmware) onto one explicit timebase, defines the prepared Prim8 stream artefact (frozen frames plus a `k1-prim8-stream/0` sidecar), and ships a host-only validator proven on 28 fixtures and cross-checked against the real firmware parser. Main finding: one corrupt frame on the wire can make the device fire hotkeys (noise-calibration arm, preset save) and swallow the rest of the stream, so the host validator is a safety gate, not a convenience.

Sources read at: firmware commit `407fdf6f503f92441f1d529276de017495f20ef3` (PRSM files identical to the working tree; snapshot and sha256 in `oracle/fw_407fdf6f/SHA256SUMS`); PRISM.studio working tree `~/Workspace_Management/Software/.g5r-clean/PRISM.studio` (git metadata broken, files read directly; identity vs lock `cc00556d` is Lane C1's job); Spine `organs.lock.json`; Trinity `analysis/`.

## Problems first

1. **Corrupt bytes reach hotkeys and command mode on the device (safety).** In `check_serial` a byte goes to the PRSM scanner only while it continues a `PRSM` hunt (`k1_prsm.cpp:54-71`). Any frame with broken magic, or the tail of a truncated frame, falls through to `:` command mode and the immediate-hotkey dispatcher (`serial_menu.cpp` check_serial ~4123-4210; hotkey set 1730-1825). Measured on the real parser with a replica of the demux: the `bad_magic` fixture (one bad frame among 24) leaks 87 bytes, fires `N` (arm noise calibration) six times and `)` (preset slot 10 **save**) once, enters command mode six times, sends five garbage strings to `parse_command`, and the device accepts only 5 of the 23 valid frames. The cause is ordinary Prim8 values: 20000 = bytes `20 4E` (space, `N`), 15000 = `98 3A` (`:`). Evidence: `raw/device_leak_report.json`, `raw/oracle_c_output.json`.
2. **No checksum in PRSM v1.** A frame cut short mid-stream merges with the next frame's header: the device accepts a corrupted frame (seq 10, impact 21072, mass 19795, momentum 30721, texture 18976 — bytes of `PRSM`) and then desynchronises (`truncated_mid_stream`: 11 accepted, 50 leaked bytes, `N` ×4). An end-of-stream truncation leaves 20 bytes in the scanner that will merge with the next stream's first frame (`scanner_fill_at_eof` = 20).
3. **PRISM `playback.js` sends K1CT PARAM_SET frames that FE firmware cannot parse.** `playback.js:67-72, 228-240, 281-299` emits K1CT frames (`cdc.js:61-91`, magic `K1CT`) whenever `device_profile != "none"` and `param_curves` exist (the golden v0.3 bundle has both: `fixtures/golden_bundle_v0.3.json:6,35-43`). FE firmware has no K1CT parser (`git grep K1CT` over firmware: none). Those bytes become hotkeys (`K`, `1` = preset slot load, `T`, …). T2 must stream with `device_profile: "none"` or with a Prim8-only streamer.
4. **Host hz range is wider than the device's.** `intent_cdc_stream.js:37` and `vm.js:297` allow 1..1000; `cdc.js:28` masks `hz & 0xff`. The device accepts 30..240 (`k1_authored_source.cpp:28`). The validator rejects outside 30..240 and any frame hz different from the sidecar hz.
5. **Stale numbers in host code:** `playback.js:210-212` says "the K1's 250ms freshness timeout"; FE firmware is 50 ms (`k1_authored_source.h:16`). `playback.js:87-89,132-134` computes `Math.ceil(Number(BigInt(t)*hz/1e6))` — BigInt division truncates first, so this is floor, not "first tick at or after"; `play(t)` can start one tick early. Read-only; reported, not changed.

## B5 — timebase reconciliation

Master axis: **asset sample index n at the asset rate R** (sample 0 = first decoded sample of `audio/track.wav`; Trinity "every timestamp is seconds from t=0.0 of audio/track.wav", `STEM_PACK_CONTRACT.md:19`).

| # | Layer | Unit / representation | Conversion (exact rule) | Source |
|---|---|---|---|---|
| 0 | Asset (decoded track.wav) | integer sample n at R (e.g. 44100, 48000) | — | stem pack `sample_rate_hz`, `sha256_track_wav` (`STEM_PACK_CONTRACT.md:72-75`); contract `track.sample_rate` (`contract_schema.json:27-31`) |
| 1 | Trinity contract | float seconds (`beats`, `downbeats`, `segments.start/end`, `track.duration_sec`) | — (n/R as float64) | `contract_schema.json:22-25,56,64,105`; lock note "times in seconds" (`organs.lock.json:10`) |
| 2 | Adapter boundary (the ONLY seconds→µs site) | integer µs | `secondsToUs(s) = Math.round(s*1e6)` (round half toward +∞) | `trinity_contract_adapter_v1.js:44-49` |
| 2b | Stem-feature frames | integer µs on the feature-fps grid | `frameToUs(i,fps) = Math.round(i*1e6/fps)` | `mapping_transforms_v1.js:11-12` |
| 3 | ShowBundle 0.3 | integer µs, `timebase.unit = "us"`, curve points `{t_us, v_u16}` | equal-time points: sort by t_us, **last one wins** (stable sort, input order) | `showbundle_v0.3.schema.json:11-20,117-124`; `vm.js:118-127` |
| 4 | VM tick (stream rate hz, nominal **120**) | tick i | `t_us(i) = (i*1_000_000 + floor(hz/2)) // hz`; count = `ceil(duration_us*hz/1e6)` | `vm.js:132-145`; `intent_cdc_stream.js:35`; Spine `instrument.mjs:190` (`--hz 120`) |
| 5 | PRSM frame | `t_us` u64 LE @10 = ShowBundle µs (origin = asset sample 0); `seq` u32 @6 = frame counter from 0 at each `play()`; seek keeps seq contiguous | `seq` resets at `play()`, continues across `seek()` | `cdc.js:24-39`; `playback.js:91-92,119,154,265` |
| 6 | Host send time | wall clock `performance.now()`, drift-corrected `setTimeout` | target = wallStart + (t_us − bundleStart)/1000 ms | `playback.js:199-205`; `intent_cdc_stream.js:67-86` |
| 7 | Device arrival | `millis()` at the AP (audio) loop iteration that drains the byte | `t_us` and `seq` are stored but **not used for scheduling** | `.ino:911,959`; `k1_authored_source.cpp:48-50,63-88` |
| 8 | Device publish | once per AP loop iteration = one I2S chunk = 96 samples @ 12.8 kHz = **7.5 ms** hop; latest frame received wins | snapshot published if state is AUTHORED/ACQUIRE/DRAIN | `config_types.h:37,41`; `platformio.ini:76-77`; `.ino:1144-1158` |
| 9 | Freshness | age > 50 ms → RECOVERY (live analysis resumes in that same tick), next tick → STANDALONE | measured on real C: +50 ms AUTHORED, +51 RECOVERY, +52 STANDALONE | `k1_authored_source.cpp:90-107`; test `test_freshness_handback` |
| 10 | Render | led_thread (Core 1) reads the snapshot each frame; chroma zeroed while authored | not paced by PRSM | `.ino:1368`, `1565-1567` |

**Rounding, defined once (this lane's rule for the sample axis):**
- sample → µs: `(2·n·1e6 + R) // (2R)` (round half up). µs → sample: `(2·t·R + 1e6) // 2e6` (round half up).
- Passage start sample S → first frame tick `i0 = first i with t_us(i) ≥ sample_to_us(S)`. Frames lie on the asset-anchored VM tick grid (same grid `play()`/`seek()` use), never on a passage-relative grid.
- Equal-time ordering: ShowBundle curve points, last in input order wins (`vm.js:122-123`); tracks are summed in id order and clamped once (`vm.js:32,219-234`), so track order cannot change the value. In the stream there are no equal times: one frame per tick.

**A02 result (round-trip ≤ 1 sample):** `raw/a02_timebase.json`
- sample → µs → sample, every sample, 0–90 s and 0–10 min, at 44.1 kHz and 48 kHz (28,800,001 samples at 48 kHz/10 min): **max error 0 samples**. Reason: 1 µs is smaller than half a sample period at both rates.
- Trinity path (n/R float64 seconds → `Math.round(s·1e6)` → sample), sampled every 997th sample to 10 min plus the 24 h limit: **max error 0 samples**.
- Tick → nearest sample → µs at 120 Hz over 10 min: max 11 µs (44.1 kHz) and 0 µs (48 kHz), within half a sample (11.3 µs / 10.4 µs) as expected.
- Implication [INFERENCE]: representation rounding is negligible; alignment error lives in host send timing (row 6) and the 7.5 ms device hop (row 8), which Lane C5/D measure.

## B6 — Rev 1 cue-list fields → existing homes

| Rev 1 field | Existing home (file:line) | Gap? | Does T2 need it? |
|---|---|---|---|
| asset sha256 | Not in ShowBundle (top-level `additionalProperties: false`, `showbundle_v0.3.schema.json:7`; only `stemtrack.stem_ref` string ≤128, `:92-102`, set to the contract basename, `trinity_compile_showbundle_v0_3.js:190-196`). Exists upstream: `sha256_track_wav` (`STEM_PACK_CONTRACT.md:72`). Compile manifest hashes contract/stems/profile only (`trinity_compile_showbundle_v0_3.js:116-148`). | **GAP (confirmed)** at ShowBundle | **Yes** (A01: the stream must name the recording it was made for). Carried in the sidecar `asset.sha256`. |
| sample rate | contract `track.sample_rate` (`contract_schema.json:27-31`), stem pack `sample_rate_hz` (`:74`). Not in ShowBundle. | GAP at ShowBundle | **Yes** (A02 conversions). Sidecar `asset.sample_rate`. |
| sample count | nowhere (only `duration_sec` float, `contract_schema.json:22`) | GAP | Yes, weakly: bounds check `T_US_BEYOND_ASSET`. Sidecar `asset.sample_count`. |
| channels | stem pack `channels` (`:75`) | GAP at ShowBundle | No (informational). Sidecar `asset.channels`. |
| timeline in samples + one conversion | ShowBundle is integer µs (`schema:11-20`); one seconds→µs site (`adapter:44-49`) | partial: no sample axis | Yes: B5 rule, recorded in sidecar `timebase` (no ShowBundle change). |
| epoch_id | none. `PlaybackEngine.seek()` keeps seq contiguous and only jumps t_us (`playback.js:119,143-154`); device has no epoch, only seq-gap → ACQUIRE (`k1_authored_source.cpp:54-61,70-75`) | **GAP** | Yes, host side only (D3 seek test). Sidecar `epochs[]`. |
| cue.t_sample | curve point `t_us` (`schema:117-124`), segment `t_us` (`:51-60`) | via B5 rule | Yes (as tick t_us). |
| cue.edge (top/bottom/both) | Prim8 has no edge field (PRSM `k1_prsm.h:21-27`); ParamTree K1CT ids carry `strip_id` bits 15:12 (`ParamTree.schema.json:8-11`) but only for device-tier params of profile `k1.wavefield.v1` (USB-bridge renderer), and FE firmware has no K1CT parser | **GAP (confirmed) for FE** | **No.** T2 = one stream drives both edges. Validator returns UNSUPPORTED for per-edge requests. |
| cue.command | `param_curves` keyed by ParamTree id → K1CT PARAM_SET (`schema:41-48`; `cdc.js:61-91`; `playback.js:281-299`). Mode/palette binding per Spine is serial `set_mode` / `k1_control_apply` (`K1_AUTHORED_INGRESS_CONTRACT.md:46,64`) | GAP on FE (no K1CT consumer) | No. T2 sets mode before the show; the stream carries Prim8 only. |
| cue.args | `v_u16` (`schema:122-123`), K1CT value u32 (`cdc.js:84`) | — | Prim8 u16 only. |
| cue_id | none | GAP | No (frames are identified by tick + seq). |
| equal-time ordering | `vm.js:118-127` (last wins), `vm.js:32` (track id order) | exists | Yes, already defined. |
| version | ShowBundle `"0.3"` (`schema:10`); ParamTree `schema_version` (`:22-26`); PRSM version 1 (`k1_prsm.h:19`) | — | Sidecar adds `schema: "k1-prim8-stream/0"`. |

**New schema decision:** ShowBundle 0.3 cannot hold asset identity or epochs (closed top level). The proven gaps go into a **sidecar only**, versioned `k1-prim8-stream/0`, scoped to a frozen PRSM stream. No change to ShowBundle, VM, PRSM or firmware.

## Prepared stream artefact (T2 input)

- `<name>.prsm` — concatenated 34-byte PRSM frames, exactly the bytes to send. Layout: `'P','R','S','M'`, version 1 @4, hz u8 @5, seq u32 LE @6, t_us u64 LE @10, Prim8 u16 LE ×8 @18 (`k1_prsm.h:10-27`, `k1_prsm.cpp:22-43`, `cdc.js:24-39`).
- `<name>.prsm.json` — sidecar `k1-prim8-stream/0`: `asset {sha256, sample_rate, sample_count, channels, path_hint}`, `timebase` (rules above), `passage_start_sample`, `hz`, `frame_len`, `frame_count`, `epoch_id`, `epochs [{epoch_id, first_frame, kind, seq_start?}]`, `stream_sha256`, `prim8` (per index: name, unit "u16 linear, 65535 = full scale", device consumer, `consumed_on_device`), `edge_addressing: "none"`, optional `source` (ShowBundle/compile-manifest hashes) and `notes`.
- Prim8 on FE firmware (`k1_authored_source.cpp:31-47`): 0 pressure → vu_level, peak_scaled, spectral_energy; 1 impact → novelty; 2 mass → low_energy; 3 momentum → mid_energy; 6 texture → high_energy; **4 heat, 5 space, 7 gravity: no consumer** (validator warns). silence = Prim8[0..2] all zero. Chroma forced to zero while authored (`.ino:1565-1567`).
- Library: `prim8_stream.py` (encode/decode, tick and sample conversions, build/write/read stream, sidecar). Encoder and tick rule match PRISM `cdc.js makePrsmPacket` and `vm.js tickTimeUs` byte for byte (test `test_encoder_and_tick_match_prism_js`).
- Single events [INFERENCE]: the device publishes the latest frame per 7.5 ms hop, so two frames arriving in one hop lose the earlier one. Author impacts at least 2 frames (≥16.7 ms) wide.

## B2 — precedence

| Rule | Desired | What the device does today (407fdf6f) | CR candidate? |
|---|---|---|---|
| Power limit always wins | yes | `FastLED.setMaxPowerInVoltsAndMilliamps(5.0, CONFIG.MAX_CURRENT_MA)` at output (`led_utilities.h:1669`), independent of source; PRSM cannot change it | no |
| Authored replaces live only while fresh | yes | yes: one writer, `.ino:1144-1158`; 50 ms freshness | no |
| Entry needs an explicit ARM | Spine `K1_SOURCE_ARBITRATION.md:25-27` | **no ARM**: any valid frame enters AUTHORED (`k1_authored_source.cpp:63-88`) | **CR-1** |
| Duplicate seq dropped; gap >3 or t_us jump >50 ms = seek with effect-history reset and no lerp | Spine `:37-38,60-67` | duplicates applied; gap → ACQUIRE→AUTHORED inside the same call (no visible effect, verified on real C); t_us ignored; no history reset | **CR-2** |
| DRAIN band 25–50 ms; RECOVERY fades / one silence-clamped frame before live | Spine `:13-14,47-52,71-77` | DRAIN never entered; RECOVERY hands straight to live in the same tick, no fade | **CR-3** |
| USB disconnect → immediate RECOVERY | Spine `:58` | not implemented (50 ms timeout only) | CR-3 |
| Live darkness must not override authored pressure | Spine `:79-81` | drop-cut pinned to 1.0 in authored (`led_utilities.h:558-562`); **`silent_scale` (live-mic silence dim) is not pinned** for k1_fe (pinned only under motion probe / VPML / `K1_BLE_REMOTED`, `led_utilities.h:540-556`; `K1_BLE_REMOTED` absent from platformio.ini) [INFERENCE, needs a runtime check] | **CR-4** |
| Binary frames never reach hotkeys / command mode | implied by Spine `:27` | they do (Problems 1–2) | **CR-5**: scanner-first even in command mode, or a binary-session lock; add CRC/length to a PRSM v2 |
| Manual serial/BLE change during a show recorded as override | yes | not recorded on device; host must log what it sent. Mode/palette changes act on the renderer independently of the snapshot | host-side logging (Lane C5) |

## Validator rules (B4) — `validate_prim8_stream.py`

Exit 0 VALID, 1 INVALID, 2 UNSUPPORTED, 3 usage/IO. Prints `INVALID frame=<k|-> rule=<RULE> <detail>` (first failure only). Opens no port. Sidecar rules: SIDECAR_MISSING, SIDECAR_SCHEMA, SIDECAR_FIELD (incl. sidecar hz outside 30..240), ASSET_IDENTITY, EPOCHS. Per frame in order: device rules DEVICE_MAGIC, DEVICE_VERSION, DEVICE_HZ_RANGE; host rules HZ_MISMATCH, T_US_OFF_GRID, T_US_BEFORE_PASSAGE, T_US_BEYOND_ASSET, PASSAGE_START_TICK, SEQ_DISCONTINUITY and T_US_NOT_NEXT_TICK (unless an epoch starts at that frame), EPOCH_START_SEQ. Stream rules: TRUNCATED, FRAME_COUNT, STREAM_SHA256. Capability: EDGE_ADDRESSING_UNSUPPORTED.

Seq discontinuity: the device accepts it (state ends AUTHORED in the same call — verified, `test_seq_discontinuity_is_not_a_device_rejection`). It is therefore an **epoch/seek** question, not a rejected-input case. The host validator is the stricter gate: a seq or t_us jump is valid only where the sidecar declares an epoch.

**Rejected-input case for Lane D:** use `invalid_hz_0`, `invalid_hz_241` or `bad_version` (scanner consumes all 34 bytes; zero leaked bytes, verified). Do **not** send `bad_magic` or `truncated_mid_stream` to hardware.

## B3 — fixtures (`fixtures/`, regenerate with `make_fixtures.py`; expectations hand-declared in `fixtures/expected.json`)

24 frames at 120 Hz, test asset 48 kHz / 10 min (identity is a labelled test hash, not audio), passage start sample 1,440,017 (off-grid on purpose) → first tick 3601.

| Fixture | Host verdict (rule, frame) | Device (real C): chunks rejected / leaked bytes |
|---|---|---|
| constant, ramp, single_impact, silence_section | VALID | none / 0 |
| unconsumed_dims | VALID + warning (heat, space, gravity) | none / 0 |
| simultaneous_top_bottom | UNSUPPORTED (EDGE_ADDRESSING_UNSUPPORTED, 10) — gap, no per-edge split | accepts all 24, both edges identical |
| invalid_hz_0 / invalid_hz_241 | INVALID (DEVICE_HZ_RANGE, 5) | chunk 5 / 0 |
| bad_magic | INVALID (DEVICE_MAGIC, 5) | chunk 5 / **87, `N`×6, `)`, 5 garbage commands, 18 valid frames lost** |
| bad_version | INVALID (DEVICE_VERSION, 5) | chunk 5 / 0 |
| truncated (end) | INVALID (TRUNCATED, 23) | none / 0; 20 bytes left in scanner |
| truncated_mid_stream | INVALID (DEVICE_MAGIC, 11) | chunks 11–22 / **50, `N`×4; one corrupted frame accepted** |
| non_monotonic_t_us | INVALID (T_US_NOT_NEXT_TICK, 10) | accepts all |
| seq_discontinuity_undeclared (+10) | INVALID (SEQ_DISCONTINUITY, 12) | accepts all |
| seq_gap_2_undeclared | INVALID (SEQ_DISCONTINUITY, 12) | accepts all (gap ≤3 = "continuous") |
| seq_discontinuity_declared | VALID (epoch e1 at 12) | accepts all |
| backward_seek (10 ticks back, seq contiguous like `playback.js`) | VALID (declared) | accepts all |
| backward_seek_undeclared (same bytes) | INVALID (T_US_NOT_NEXT_TICK, 12) | accepts all |
| forward_seek (+10 s, seq +100) | VALID (declared) | accepts all |
| epoch_change (restart, seq_start 0) | VALID | accepts all |
| epoch_start_seq_wrong | INVALID (EPOCH_START_SEQ, 12) | accepts all |
| hz_mismatch (frame hz 60 vs sidecar 120) | INVALID (HZ_MISMATCH, 5) | accepts all |
| off_grid_t_us | INVALID (T_US_OFF_GRID, 7) | accepts all |
| beyond_asset | INVALID (T_US_BEYOND_ASSET, 12) | accepts all |
| before_passage | INVALID (T_US_BEFORE_PASSAGE, 0) | accepts all |
| stream_sha_mismatch | INVALID (STREAM_SHA256, -) | accepts all |
| missing_sidecar | INVALID (SIDECAR_MISSING, -) | accepts all |
| bad_asset_identity | INVALID (ASSET_IDENTITY, -) | accepts all |

## Gate results

| Gate | Status | Evidence |
|---|---|---|
| Validator verdict = declared expectation, all 28 fixtures | **PASS** | `raw/pytest_run1.txt` |
| Validator CLI goes red on bad inputs (exit 1/2 with rule and frame), green on good (exit 0) — real negative inputs, run once | **PASS** | same run, `test_validator_cli_exit_code` ×28 |
| Differential oracle, chunk level (magic, version, hz): real firmware C vs independent Python model vs validator | **PASS** (28/28 agree) | `test_diff_chunk_level_device_rules`; `raw/oracle_c_output.json` |
| Differential oracle, byte scanner events and check_serial demux | **PASS** (28/28 agree) | `test_diff_byte_scanner`, `test_diff_check_serial_demux`. Note: the demux in `device_oracle.cpp` replicates `serial_menu.cpp` control flow (scanner itself is real firmware code) |
| Host stricter than device (every device reject caught by host) | **PASS** | `test_host_is_stricter_than_device` |
| Valid streams leak zero bytes to hotkeys/command mode | **PASS** | `test_device_byte_leak_report`; `raw/device_leak_report.json` |
| A02 rounding ≤1 sample | **PASS** — max 0 samples | `raw/a02_timebase.json` |
| Encoder / tick grid identical to PRISM `cdc.js` / `vm.js` | **PASS** | `test_encoder_and_tick_match_prism_js` (node v26.5.0, read-only import) |
| Freshness handback 50/51/52 ms | **PASS** | `test_freshness_handback` |

pytest: **149 passed, 0 failed** in one run (python3 3.14 host with pytest 8.4.2; validator CLI under python3.13 as required). Nothing installed.

## Resident build identity (bench K1 runs ed0aa984)

`serial_menu.cpp`, `serial_menu.h`, `k1_prsm.{h,cpp}`, `k1_authored_source.{h,cpp}` and `visual/led_utilities.h` have **identical git blobs** at `407fdf6f` and `ed0aa984` (`git diff --stat 407fdf6f ed0aa984 -- <files>` empty; blob e.g. `serial_menu.cpp` = `e99b8fb4`). The `.ino` (+30 lines) and `config_types.h` (+17 lines) differ by insertions only, none touching PRSM, authored, `check_serial`, sample rate or chunk size; `platformio.ini` at ed0aa984 still sets 12800 Hz / 96 samples. The oracle therefore applies to the resident build. Test: `test_resident_build_ed0aa984_has_identical_prsm_path`.

## Partial-frame hazard and the safe resync preamble

**Hazard (lead's hypothesis — confirmed, with one correction).** Measured with the real scanner, a stale partial buffer of fill f followed by a valid stream (`raw/preamble_proof.json`, `without_preamble`):
- f = 1..3 (partial magic): **no hazard.** The next frame's `P` breaks the partial magic and is re-hunted (`k1_prsm.cpp:63-67`); all 24 frames accepted.
- f = 4: the next frame's `P` lands in the version byte → FRAME_BAD; that frame is lost and its last 4 bytes fall through.
- f = 5..33: **not FRAME_BAD** — the merged buffer usually parses as **FRAME_OK** (stale header; at f = 5 the hz byte is `P` = 80, which is in range). A corrupted frame is accepted, then the real frame's last f bytes fall through to the dispatcher.
- From about f = 10 upward the fall-through bytes include Prim8/t_us bytes that are hotkeys or `:`. Worst case (f = 33): 32 hotkey bytes and 7 command-mode entries; the device accepts 1 of 24 frames. 60 of 68 tested start states are unsafe.
- Device already in `:` command mode: every byte is swallowed (722 of 816), 0 frames accepted, garbage lines executed every 127 bytes.

**Preamble:** `RESYNC_PREAMBLE = b"\n" + b"\x00" * 63` (64 bytes = one full USB packet, `prim8_stream.py`; first proven at 34 bytes, widened to 64 so it keeps the guarded frame writes below packet-aligned, proof re-run). Send it as one write before the first frame of every session and every epoch.
- `\n` (LF): outside command mode it is skipped by `check_serial` (CR/LF `continue`); inside command mode it ends the line (`serial_menu.cpp` check_serial command branch).
- `0x00` (NUL): not `P`, not `:`, not CR/LF, and not in `serial_hotkey_is_immediate()` (`serial_menu.cpp:1730-1825`), so at fill 0 it is ignored. From f = 4..33 at most 30 bytes finish the stale buffer; the scanner consumes every one.
- Proof (real scanner + demux replica + hotkey classifier): **all 68 start states** (fill 0..33 × two stale contents) → 0 hotkey bytes, 0 command-mode entries, 24/24 frames, final fill 0. **All 36 command-mode states** (pending 0/1/20/126 × fill 0,1,3,4,5,6,18,20,33) → same. Evidence: `raw/preamble_proof_run.txt`, `raw/preamble_proof.json`, tests `test_preamble_*`.
- No-op bytes at the dispatcher: every value outside the immediate set below and outside `P`, `:`, CR, LF. NUL (0x00) is the chosen filler. Immediate set (actionable): ``g G u y m - = _ + space h ; N Y [ ] 0-9 ! @ # $ % ^ & * ( ) \ U i I o O p P j J k K l L q Q w W e E r R t T , . / a s S d f``, plus build-conditional `z Z v`.

**Residual risks the preamble cannot remove (firmware CR, folded into CR-5):**
1. **A command line already pending is executed.** Command mode has no abort byte: CR/LF runs `parse_command(command_buf)` when the buffer is non-empty, and 127 bytes runs it regardless. `parse_command` (`serial_menu.cpp:2876+`) dispatches any exact command name or `name=value` setter and otherwise reports a bad command. A stray partial line such as `set_mode=1` would therefore run. Only reachable if an earlier writer left `:`+text without a newline; our streams never do (audit gate).
2. **One stale frame can complete as a valid frame** (f ≥ 6 with a valid stale header): it carries stale bytes plus `0x0A` and zeros, e.g. f = 20 → Prim8 `[30000, 10, 0, 0, 0, 0, 0, 0]`. The first real frame replaces it in the same burst; no hotkey or command effect.
3. A `:look_load` binary transfer in progress (`K1_LOOK_LIB_V1` branch at the top of check_serial) would absorb the preamble as look data. Only reachable after an explicit `:look_load` command.

**CR-5 (smallest firmware change, revised):** (a) in check_serial's command branch, treat one byte (0x18 CAN or 0x1B ESC) as "clear `command_buf`, leave command mode, execute nothing"; (b) reset the PRSM scanner when fill > 0 and no byte has arrived for ≥ 20 ms (frames arrive as 34-byte bursts, 8.3 ms apart); (c) PRSM v2 with length + CRC. (a) plus (b) makes a session start safe without any preamble assumption.

## Byte audit gate — `audit_prsm_bytes.py`

Feeds preamble + whole `.prsm` through `oracle/byte_audit.cpp` (real `k1_prsm.cpp` + `k1_authored_source.cpp`, demux replica, injectable start state). Exit 0 BENCH-ELIGIBLE only if: zero actionable hotkey bytes, zero `:` entries, zero bytes swallowed or lines executed by command mode, every stream byte consumed by the scanner, every stream frame accepted, and final fill 0. `--allow-rejected-frames` is for the deliberate rejected-input case: frames may be rejected, but the hotkey and command-mode rules still apply. Exit 1 not eligible (prints counts and first positions), 3 usage.

Run once (`raw/audit_fixtures_run.txt`, `raw/audit_rejected_and_cemu_run.txt`):
- constant, ramp, single_impact, silence_section, unconsumed_dims, seq_discontinuity_declared, backward_seek, forward_seek, epoch_change → **exit 0**.
- bad_magic → **exit 1**: 26 hotkeys, 6 `:` entries, 550 bytes swallowed, 5 lines executed, 5/24 frames.
- truncated_mid_stream → exit 1 (17 hotkeys, 4 entries).
- truncated → exit 1 (fill 20 left).
- bad_version and invalid_hz_0 → exit 1 as shows; with `--allow-rejected-frames` → exit 0 (also invalid_hz_241) — safe rejected-input cases.
- **Lane C-emu stream** `lane-c-emu/stream/loreen_75_155_120hz.prsm` (read-only, sha256 `ea4b8f45…55af`): audit **exit 0**, 9600/9600 frames, 0 hotkeys; validator **VALID**.

Additional gate rows: preamble proof **PASS** (68 + 36 states); byte audit red on bad_magic / green on good fixtures **PASS**; resident-build identity **PASS**. Full suite re-run once after these additions: **160 passed** (`raw/pytest_run2.txt`).

## USB packet-loss exposure (bench stream)

**Model.** USB-Serial-JTAG RX copies each ≤64-byte packet into `rx_queue`; when the queue is full the interrupt routine stops and the rest of that packet is lost (lead-verified, arduino-esp32 `HWCDC.cpp:116-127`; this lane did not re-read it). The host has already had the packet acknowledged, so it never resends. A loss event (k, i) keeps the first i bytes of packet k; later packets arrive intact. Each event runs through the real scanner and mapper plus the check_serial demux replica until resync (`oracle/loss_exposure.cpp`). Outcomes are classified by `oracle/analyze_loss.py` from the hotkey handler (`serial_menu.cpp:1998-2260`) and the helpers it calls:

| Byte(s) | Effect | Persists? | Source |
|---|---|---|---|
| `N` | arms noise calibration for 5 s; no disarm except expiry or a `Y` while not armed | — | `k1_noise_cal_arm.cpp:21-26`, `.h:5` |
| `N` … `Y` within 5 s | **calibration queued** (CRITICAL) | config poisoned by cal during music | `k1_noise_cal_arm.cpp:32-42` |
| `S` | `k1_show_state_save()` | **yes** (LittleFS + `save_config`) | `serial_menu.cpp:2231-2246`; `k1_show_state.cpp:254+` |
| `! @ # $ % ^ & * ( )` | preset slot 1–10 save | **yes** (LittleFS) | `serial_menu.cpp:2078-2107`, `1561-1572`; `k1_effect_queue.cpp:360` |
| `1`–`9`, `0` | preset slot load → `apply_preset_live` | **yes** (primary: `save_config_delayed`) | `serial_menu.cpp:2064-2077`, `1541+`; `k1_effect_queue.cpp:133-141` |
| `q Q w W` | SQUARE_ITER / SENSITIVITY ± | **yes** (`save_config_delayed`) | `serial_menu.cpp:2152-2175` |
| `i I o O p j J k K l L` | photons/chroma/mood/saturation/prism/base-coat ± | **yes** when the primary channel is targeted | `serial_menu.cpp:2116-2151`, `1470-1479` |
| `/` | palette-mode toggle | **yes** | `serial_menu.cpp:2218-2220`, `1510+` |
| `[ ] , . \ U` | queued mode/palette change, commit, queue mode | visible; persistence not verified | `serial_menu.cpp:2020-2025, 2108-2115, 2212-2217` |
| `e E r R t T`, `g G = - + _ u y m`, space | visual tuning (RAM), edge mixer, target channel | no | `serial_menu.cpp:2003-2055, 2176-2211` |
| `a s d f` | serial stream toggles (device starts or stops streaming text) | no | `serial_menu.cpp:2221-2256` |
| `:` + bytes | command line; executes when CR/LF arrives or at 127 bytes | depends on the command | check_serial; `parse_command` `serial_menu.cpp:2876+` |

**Result — bench stream `lane-c-emu/stream/loreen_75_155_120hz.prsm`** (sha256 `ea4b8f45…55af`, 9600 frames, seq 9000–18599, t_us 75.000–154.992 s), one frame per 34-byte packet (no guard), 326,366 events (`raw/loss_exposure_cemu_guard0.json`):
- clean: 38,396; dirty: 287,970. All events resync within 64 packets.
- **CAL_QUEUED (critical): 110 events.** `N` armed only: 6,308. `Y` without `N`: 6,651 (dangerous if an independent earlier loss in the previous 5 s produced an `N`).
- **PERSIST: 178,135 events**; most frequent leaked byte is `S` (26,550).
- Command mode entered: 8,476. Command lines executed: 30, all `h`/`H` (help, `serial_cmd_table.def:41-42`, harmless); 8,811 lines end in "Bad command".
- Garbage frame accepted: 278,371. Mode/palette change: 44,045.
- **Worst event:** (k = 415, i = 33) — leaks `R S $ k N _ 3 h l Y p`: show-state save, preset-slot-4 save, prism +, noise cal armed then **queued**, slot-3 load. Persisting or critical events occur for every i from 4 to 33; at i = 32 and 33 they occur for 9,599 of 9,599 frames, because the leaked tail starts with the magic `R S`.
- Rejected-input variants (`bad_version`, `invalid_hz_0`, `invalid_hz_241`): the same classes appear without the guard (`raw/loss_exposure_rejected_variants.txt`).

## Payload shaping — refuted

Shaping Prim8 values cannot remove the persisting outcomes. Byte origin in the bench stream (`raw/loss_byte_origin_cemu.txt`):
- **Magic `R S` (frame bytes 1–2):** present in all 9,600 frames. `S` is the persistent show-state save. Nudging cannot change it.
- **seq:** persisting keys in 5,527 frames; `N` 38, `Y` 38, `:` 293. Its low byte runs through all 256 values every 256 frames, so no choice of starting seq avoids them.
- **t_us** (fixed by the contract): persisting keys in 3,422 frames; `N` 67, `Y` 68, `:` 78.
- **Prim8:** 6,453 / 233 / 254 / 239 (persist / N / Y / colon).

No shaped stream was emitted.

**Host-side fix that does work — per-frame guard.** Write every frame as one 64-byte write: 30 NUL bytes, then the 34-byte frame (`prim8_stream.FRAME_GUARD_BYTES`, `wire_packets()`). Send `RESYNC_PREAMBLE` (64 bytes) first.
- Why it works: if a packet's tail is lost, the next packet's 30 NULs finish any stale partial frame (fill 4..33 needs at most 30 bytes; fill 1..3 resets) before a frame byte arrives. Lone NULs are no-ops at the dispatcher.
- Every write is exactly 64 bytes, so any packing of whole writes into USB packets stays aligned.
- Exhaustive single-loss run, same bench stream, 614,336 events (`raw/loss_exposure_cemu_guard30.json`): **0 hotkey bytes, 0 command-mode entries, 0 commands**. The only effect is 249,394 events in which one stale frame (old bytes plus zeros) is accepted and then replaced by the real frame in the same packet.
- **Any sequence of losses:** induction step checked for every start fill 0..33 (two stale contents) × every 10th packet × every kept prefix 0..64: **4,243,200 runs, 0 leaks** (`raw/loss_step_cemu_guard30.json`). Without the guard: 1,065,526 of 2,284,800 runs leak.
- `audit_prsm_bytes.py --guard 30` on the bench stream: exit 0 (`raw/audit_guard30_run.txt`). The validator result is unchanged (VALID, stream bytes not altered).
- Costs and assumptions:
  1. 7,680 B/s instead of 4,080 B/s. The device drain cap of 128 B per 7.5 ms hop (17 kB/s) still covers it.
  2. The stall a 256-byte queue can absorb (Lane A figure, not re-checked) drops from about 63 ms to about 33 ms. Overflow now only loses frames, and the 50 ms freshness rule hands back to live.
  3. **[INFERENCE]** The macOS CDC driver turns each 64-byte write into one full packet, and never splits a write across packets at a non-64 boundary. This is standard bulk-transfer behaviour but was not measured. It is the one assumption the bench should check; the watchdog below is the backstop.
- Still recommended as firmware change CR-5 (the real fix): command-mode abort byte, scanner idle reset, CRC.

## Host-side device-output watchdog (spec)

The player must read the K1's text output on the same port during the show (`playback.js` never reads it). Matching is a prefix match on each line. Sources are at 407fdf6f, identical at ed0aa984.

| Device line (prefix) | Meaning | Source | Host reaction |
|---|---|---|---|
| `NOISE_CAL: armed` | leaked `N` | `k1_noise_cal_arm.cpp:25` | **STOP all writes at once for ≥ 5.5 s** (window 5000 ms, `k1_noise_cal_arm.h:5`) so no leaked `Y` can land. Then resume with `RESYNC_PREAMBLE` and a new epoch. Never send `Y`. |
| `NOISE_CAL: queued` | `N` then `Y` leaked: **calibration during music** | `:41` | STOP the show. Raise CRITICAL. Calibration policy applies: do not continue; Captain re-calibrates under confirmed silence (rollback). |
| `NOISE_CAL: not armed` | leaked `Y` | `:35` | STOP for ≥ 5.5 s (a later `N` + `Y` pair is possible); log. |
| `SHOW_STATE_SAVED` | leaked `S`: show state written to flash | `serial_menu.cpp:2233` (`:2645` is the `:save_show` command) | STOP. Flag persisted state as polluted. Restore through the Lane A6 rollback route after the session. |
| `SLOT ` … ` SAVED` / ` SAVE FAILED` | preset slot overwritten | `serial_menu.cpp:1563-1571` | STOP; flag the slot as polluted. |
| `SLOT ` … ` -> ` / ` EMPTY` / `QUEUE: ARMED SLOT` | preset load (primary saves config) | `:1528-1557` | STOP; flag config. |
| `HOTKEY ` | photons/chroma/mood/saturation/prism/base coat changed (saved if primary) | `:1407,1415` | STOP; flag config. |
| `CONFIG.SQUARE_ITER: ` / `CONFIG.SENSITIVITY: ` | saved setting changed | `:2155-2173` | STOP; flag config. |
| `PALETTE_MODE: ` / `SECONDARY_PALETTE_MODE: ` | palette mode toggled (saved) | `:1514,1518` | STOP; flag config. |
| `QUEUE: ARMED`, `COMMIT`, `QUEUE MODE`, `QUEUE: nothing armed` | mode/palette queue touched | `:1446,1500,1576-1595` | STOP; check mode with a typed status query before resuming. |
| `SECONDARY_CONTROL: ` | target channel flipped | `:2005` | STOP; flag (changes what later keys persist). |
| `EDGE_` | edge mixer changed (RAM) | `:315-428` | STOP; reset after the session. |
| `VP_WAVEFORM_SHIFT_RATE: `, `VP_BLOOM_SHIFT_SCALE: `, `VP_BLOOM_ALPHA: ` | visual tuning changed (RAM) | `:2179-2209` | STOP; reset after the session. |
| `AP_STREAM: `, `VP_STREAM: `, `STREAM_AGC_DEBUG: `, `STREAMS: ` | device text streaming toggled | `:2223-2254` | STOP; send the matching typed off command after the session. |
| `K1 HOTKEYS`, `K1 HOTKEY STATUS` | leaked `h` / `;` (help or status) | `:1600,1675` | STOP (proves leakage); harmless by itself. |
| `Bad command: ` | leaked `:` line executed | `serial_tx.cpp:52` | STOP; the device may still be in command mode, so resume only with `RESYNC_PREAMBLE`. |
| any other unexpected line during the show | unknown | — | STOP and log. |

Rules: any match ⇒ stop writing within one frame period (8.3 ms), keep stopped ≥ 5.5 s, never send `Y`, `N` or any `:` command automatically, record the line with host monotonic time and the last seq sent, resume only after the preamble and a new epoch. The watchdog is a backstop. The guard plus preamble are the primary prevention.

Gates for this section: exhaustive loss run **PASS** (no guard: exposure measured; guard: 0 hotkeys); induction step **PASS** (0 leaks in 4,243,200 runs); shaping **REFUTED** (no stream emitted); suite run once after these additions: **163 passed** (`raw/pytest_run3.txt`).

## Files
`oracle/loss_exposure.cpp`, `oracle/analyze_loss.py`, `audit_prsm_bytes.py`, `oracle/byte_audit.cpp`, `oracle/prove_preamble.py`, `prim8_stream.py`, `validate_prim8_stream.py`, `make_fixtures.py`, `test_validate_prim8_stream.py`, `fixtures/` (28 streams + sidecars + `expected.json`), `oracle/device_oracle.cpp`, `oracle/py_device_model.py`, `oracle/fw_407fdf6f/` (firmware snapshot + `SHA256SUMS` + hotkey excerpt), `raw/`.

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-09 | agent:claude (Lane B) | Added: exhaustive USB packet-loss exposure on the bench stream (110 calibration-queued, 178,135 persisting events unguarded), payload shaping refuted (magic `RS` + seq + t_us), 30-NUL per-frame guard (0 hotkeys over 614,336 events; induction 0/4,243,200), preamble widened to 64 B, device-output watchdog spec; 163 tests pass. |
| 2026-11-09 | agent:claude (Lane B) | Added: resident-build identity (ed0aa984 PRSM/serial blobs identical), partial-frame hazard confirmed (f 4..33; f 1..3 self-resync), resync preamble `\n`+33×NUL proven for 68 scanner + 36 command-mode states, CR-5 revised (abort byte, scanner idle reset, CRC), `audit_prsm_bytes.py` gate; C-emu stream eligible; 160 tests pass. |
| 2026-11-09 | agent:claude (Lane B) | Created: B5 timebase table, B6 field map, `k1-prim8-stream/0` sidecar, precedence with CR-1..CR-5, 28 fixtures, validator, differential oracle against firmware 407fdf6f; 149 tests pass. |
