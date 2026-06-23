---
abstract: "CANONICAL device↔env↔build registry for the two K1 units. 1401 (chip F887A500) flashes ONLY env k1_hardware; 12201 (chip B489A500) flashes ONLY env k1_bench_reference — different GPIO maps, cross-flashing bricks output. Records currently-deployed commits, eyes-on anchor commits, flash discipline, serial gotchas, and non-shippable env rules. Verify against live git/device before trusting the deployed-state table; update the table on every flash."
---

# K1 Device ↔ Build Registry (canonical)

**This file is the single source of truth for which firmware build belongs on
which physical device.** Future agents: read this BEFORE any flash, erase,
serial-write, or "which build is that device running?" reasoning. If reality
disagrees with this file, reality wins — then fix this file.

Companion docs: pin-level hardware truth in
[`k1-hardware-definition.md`](./k1-hardware-definition.md); routing authority
in [`../spec-index.md`](../spec-index.md).

## 1. The two devices (identity is NON-NEGOTIABLE before any write)

| Device | Role | Chip ID | Port (typical) | **ONLY permitted env** |
|---|---|---|---|---|
| **1401** | Main K1 (Captain's primary) | `F887A500` | `/dev/cu.usbmodem1401` / currently `/dev/cu.usbmodem1101` | `k1_hardware` |
| **12201** | Bench K1v2 | `B489A500` | `/dev/cu.usbmodem12201` / currently `/dev/cu.usbmodem12401` | `k1_bench_reference` |

- The two envs differ by **GPIO map**, not just flags. `k1_hardware` on 12201
  (or vice versa) produces dead/garbled output. There is no "same binary on
  both" — a build deployed "to both devices" means the SAME COMMIT built twice,
  once per env.
- `scripts/platformio/k1_upload_guard.py` verifies USB MAC/chip ID on upload,
  but do not lean on it as the only check: confirm port + identity first
  (`ls /dev/cu.usbmodem*`, `:chip_id` over serial if ambiguous).
- Port numbers can drift across USB re-enumeration. Identity = chip ID, never
  the port name.
- **Never flash any device without Captain's per-device instruction**
  (standing rule, 2026-06-11; origin: unauthorized 1401 rollback).
  > **Standing authorization (2026-06-19, Captain):** full ownership of the
  > K1↔Tab5 feature-development phase granted — autonomous flash/test on the
  > **main K1 (`F887A500`)** and **Tab5 (ESP32-P4)** is pre-approved *for this
  > phase only*, no per-action approval needed. Identity-by-chip-ID still
  > mandatory before every write. Does not extend to other devices.

### 2026-06-19 live identity verification (esptool `flash_id`, all 4 enumerated ports)

Ports are badly scrambled vs the typical map; verified by chip type + MAC:

| Port (now) | Chip | Base MAC | Identity → env |
|---|---|---|---|
| `/dev/cu.usbmodem1101` | ESP32-S3 | `b4:3a:45:a5:87:f8` (= chip `F887A500`) | **main K1** → `k1_hardware` |
| `/dev/cu.usbmodem12401` | ESP32-S3 | `b4:3a:45:a5:89:b4` (= chip `B489A500`) | **bench K1v2** → `k1_bench_reference` |
| `/dev/cu.usbmodem12201` | ESP32-S3 | `b4:3a:45:a5:89:b4` (= chip `B489A500`) | **bench K1v2** → `k1_bench_reference` (⚠ **re-scrambled 2026-06-21**: this port was the Tab5 P4 on 2026-06-19; chip-ID is truth, verify every session) |
| `/dev/cu.usbmodem1401` | ESP32-S3 | `fc:01:2c:da:2b:38` | **⚠ UNREGISTERED 4th S3** — not in this registry; do not flash without Captain ID |

- **`platformio.ini` port pins are now WRONG vs reality:** `k1_hardware`
  pins `upload_port=/dev/tty.usbmodem1401` (now the unregistered S3) and
  `k1_bench_reference` pins `12201` (now the **Tab5 P4**). Always pass
  `--upload-port` explicitly by verified identity; the upload guard (MAC) is the
  backstop, not the first check.

- **2026-06-21 (live re-scramble + GDFT centre A/B):** `12201` re-enumerated as
  the **bench K1 `B489A500`** (verified `b4:3a:45:a5:89:b4`). Added a dev-only
  env **`k1_bench_reference_harness`** (= `k1_bench_reference` GPIO map +
  `-DENABLE_GDFT_HARNESS=1`), registered in `k1_upload_guard.py` under the bench
  target so it flashes ONLY to `B489A500`. Flashed it, ran the deterministic
  synthetic GDFT probe, then **restored `k1_bench_reference`** (harness gone,
  functionally verified). Device evidence: 440 Hz (A4) → bin 26 (B4 label),
  415.3 Hz (G#4) → bin 24 (A4 label), 2509/2754 Hz → bin 78 (above-Nyquist
  alias) — rounded-k centre offset is product-visible.
- Main K1 currently runs the TEMPORARY `k1_effect_registry` eyes-on build
  (branch `feat/effect-registry-rewire` @ `1864899`, incl. R5 dense gap-free
  numbering), per §2 — not clean production. Supersedes the earlier
  `k1_effect_framework` (`c9d2578`) temporary flash. Restore baseline `72cb650`
  (`k1_hardware`) after the eyes-on verdict.

## 2. Deployed state (UPDATE ON EVERY FLASH)

| Device | Commit | Build/env | Why | Since |
|---|---|---|---|---|
| 12201 (bench K1, `B489A500`) | `fcbcad1` (branch `feat/gdft-int64-recurrence-ab`) | **Net deployed = shippable `k1_bench_reference`** (RESTORED). 4-leg A/B: `k1_bench_reference_harness` flashed with A=all-OFF, B=`-DK1_GDFT_INT64_MAGNITUDE_V1=1`, C=`+ -DK1_GDFT_INT64_RECURRENCE_V1=1`, D=`+ -DK1_GDFT_TRUE_CENTER_V1=1`, then restored. Identity guard-verified `B489A500` before every flash. | **GDFT int32 overflow CHAIN fully resolved + true-centre VINDICATED.** Two int32 overflow sites: (1) magnitude `q2²+q1²-(mult>>14)·q2`; (2) recurrence `coeff_q14*(int32_t)q1` (overflows at q1>~67k). **Leg A** = the collapse (440: bin24/25=0.00). **Leg B** (magnitude only) = clamps gone but magnitudes overflow-inflated (~6500) because the recurrence still grows q erratically; rounded-k offset persists. **Leg C** (magnitude+recurrence, rounded-k) = magnitudes drop to **~245, matching the bit-faithful host replica to <1%** (host 248/245/245 vs device 247.8/245.4/244.6); `q0ovf=0`. **Leg D** (magnitude+recurrence+true-centre) = **ACCEPTANCE PASS: 415.3→bin23, 440→bin24, 466.16→bin25**, each a clean dominant winner, mags 252/249/247, `q0ovf=0`. **q-state never overflows int32** (`q0ovf=0` every probe; max\|q0\|~1.6e5 ≪ INT32_MAX) — the bug was the multiply WIDTH, not q range; no wider-q pass needed. The prior "true-centre broken / confirmed-negative / scalloping" framings were ALL the two fixed-point overflows. All three flags remain **default-OFF** pending perf/MabuTrace + magnitude-scale(~20×)/AGC review + Captain eyes-on before any flip. Raw captures: `docs/forensics/runtime-evidence/2026-06-21-gdft-overflow-telemetry/rec_{A,B,C,D}.txt` + `int64-recurrence-ab-README.md`. Restore proof: `:gdft_probe=440` returns nothing; guard re-verified post-restore. | 2026-06-21 ~09:40 AWST |
| 12201 (bench K1, `B489A500`) | `15fab24` (branch `feat/gdft-true-center-ab`) | **Net deployed = shippable `k1_bench_reference`** (RESTORED). During the session: `k1_bench_reference_harness` flashed OFF (`-DK1_GDFT_TRUE_CENTER_V1=0`) then ON (`=1`) to `/dev/cu.usbmodem12201`; identity verified by upload guard (serial `B4:3A:45:A5:89:B4` = chip `B489A500`) before each write. | **K1_GDFT_TRUE_CENTER_V1 device A/B (synthetic GDFT harness, no mic).** OFF leg reproduced legacy rounded-k (440 Hz→bin 26, 415.3→bin 24). ON leg: 440→bin 24, but 415.3→bin 26 (mag 53), 405/410/466 sweep losing to alias bin 78. **ROOT CAUSE PROVEN via GDFTP5 top-5/neighbour telemetry (2026-06-21, harness commit on `feat/gdft-true-center-ab`):** the int32 magnitude `magnitudes[i]=q2²+q1²−(mult>>14)·q2` OVERFLOWS at sustained resonance (undamped resonator grows q≈160k over the block; q²≈2.6e10 wraps int32 → negative → the `if(<0)…=0` clamp ZEROES the bin). Neighbour magnitudes read **exactly 0.00** for the near-resonance bins (e.g. ON 415.3: bin22/23/24 = 0.00; OFF 440: bin24/25 = 0.00) — that clamp is the only explanation. **Present in BOTH OFF (production rounded-k) and ON** — true-centre is NOT independently worse; it only shifts WHICH input tones hit the knife-edge. bin 23 is GENUINELY zero on-device (overflow), not "losing"; bin 78 only wins when the near bins collapse first. Device coeff_q14 + block_size matched the host replica exactly, so the host's disagreement was purely its inability to bit-reproduce the wrap. **The A/B argmax is contaminated by this pre-existing overflow → true-centre's merit is not cleanly testable until the overflow is addressed.** **[RESOLVED 2026-06-21 — see the recurrence-A/B row above: the overflow was a CHAIN of two int32 sites (magnitude + recurrence multiply); with `K1_GDFT_INT64_MAGNITUDE_V1=1` AND `K1_GDFT_INT64_RECURRENCE_V1=1`, true-centre PASSES on hardware (415.3→bin23, 440→bin24, 466.16→bin25). True-centre was never broken — it was masked by the overflows.]** Flag stays default-OFF. Raw captures: `docs/forensics/runtime-evidence/2026-06-21-gdft-overflow-telemetry/capture_{OFF,ON}.txt`. **Restore proof:** `:gdft_probe=440` returns no GDFTP line (harness gone); guard re-verified identity post-restore. Raw probe logs: `_scratch/gdft-12201/`. | 2026-06-21 ~07:55 AWST |
| 1401 (main K1, `F887A500`) | `7bbb0b8` (eyes-on, TEMPORARY) | `k1_effect_registry` (= `k1_hardware` GPIO map + `-DK1_EFFECT_FRAMEWORK_V1 -DK1_EFFECT_REGISTRY_V1` + 5 native effects) uploaded to `/dev/cu.usbmodem2101`; identity verified live by esptool `read_mac` → `b4:3a:45:a5:87:f8` = chip `F887A500` AND by the upload guard before write | **TEMPORARY device eyes-on flash of the registration-architecture rewire (R1–R4, branch `feat/effect-registry-rewire`).** Single `EffectEntry[]` registry replaces the archaic per-effect edit scatter; all consumers (dispatch/name/enable/cycle/director/NVS-sanitize) are registry lookups; registry build is additive + flag-gated, BeatAwareDirector defaults OFF so boot is production-identical until `beat_director=on`. **Host gates before upload (all re-run by orchestrator):** pytest `518 passed` (+61 subtests); `pio run -e k1_hardware` = `649,486 B` baseline byte-identical (loadable-section fingerprint `3073aec…`, `registry_byte_gate.sh` PASS); `pio run -e k1_effect_registry` links clean (`679,238 B`); `framework-safety-gate.sh` exit 0 (CL-1/CL-2). **Post-flash device proof:** boot `K1_EFFECT_REGISTRY_V1 boot self-check: PASS` (registry healthy → registry render path, not legacy fallback), `:chip_id` = `F887A500`, `SYSTEM INIT COMPLETE`, `RUNTIME_TIMING_GUARD timing_ok=1 sample_rate=12800 samples_per_chunk=96`, AP live (`bpm` detect, `lock=1` seen), `cal_valid=1`. 5 natives registered + named on-device (ords 30–34: Beat Pulse Resonant / LGP Harmonic Tide / LGP Beat Prism / LGP Flux Rift / LGP Transient Lattice; all `enabled=true, director_ok=true`). **CL-1 ack-barrier DEVICE-PROVEN:** `:slot_save=4` (LittleFS `/PRESETS_V1.BIN` write) fired mid-render with framework active → 0 crash markers, AP cadence continuous (no freeze), `SLOT 4 SAVED`. **75 s pre-eyes-on soak:** `ap_lines=75 (~1.0 Hz)`, 0 extra boots, 0 crash markers; director autonomously reached native mode 30 (Beat Pulse Resonant). **Production baseline to RESTORE after eyes-on:** `72cb650` (`k1_hardware`) via `pio run -e k1_hardware -t upload --upload-port <verified F887A500 port>`. **Eyes-on verdict: PENDING Captain visual review.** NOT timing-proven (MabuTrace Core-1 frame-budget pass still owed before any registry-as-default flip). Test artifact: preset slot 4 now holds `CHROMA CONSTELLATION` (was EMPTY; slots 1–3 = Captain's WAVEFORM presets, untouched). | 2026-06-20 AWST |
| 1401 | `c9d2578` (eyes-on, superseded) | `k1_effect_framework` (= `k1_hardware` GPIO map + `-DK1_EFFECT_FRAMEWORK_V1`) uploaded to `/dev/cu.usbmodem1101`; identity verified live (`:chip_id` → `F887A500`) AND by the upload guard before write | **TEMPORARY device eyes-on flash of the P1–P6 effect-framework + beat-aware director (branch `feat/effect-framework-v3-graft`).** Flag-on build; the framework is additive and the BeatAwareDirector defaults OFF, so boot behaviour is identical to production until `beat_director=on` is sent over serial. Host gate before upload: `pytest 523 passed`, `pio run -e k1_effect_framework` + `pio run -e k1_hardware` (649,486 B == baseline) both green. Upload exit 0; post-flash proof: `:chip_id` = `F887A500`, audio pipeline live (tempo detect `bpm≈94`), `cal_valid=1` (NVS/calibration survived app-partition flash), `beat_director`/`serial_print_beat_director_status` confirmed present in flashed `firmware.elf`. **Production baseline to RESTORE after eyes-on:** prior deployed `72cb650` (`k1_hardware`) — reflash via `pio run -e k1_hardware -t upload --upload-port /dev/cu.usbmodem1101`. **Eyes-on verdict: PASS** (Captain, 2026-06-19) — `beat_director=on` on the plate: "everything looks good". First device validation of the effect-framework + beat-aware director. NOT yet timing-proven (MabuTrace Core-1 frame-budget pass still owed) and crash-safety (gate-0 CL-1/CL-2) is source-reasoned not device-proven; both required before any production default-flip. | 2026-06-19 AWST |
| 12201 | `5b329b3` | `k1_bench_reference` built/uploaded from clean worktree `_scratch/restore-clean-head-5b329b3` to `/dev/cu.usbmodem12401` (chip `B489A500`) | Clean committed-head restore after a dirty VP-probe experiment was flashed and failed to emit VPO rows. Restore proof: identity matched, `sample_rate=12800`, `samples_per_chunk=96`, `CAL_SOURCE=config`, `CAL_VALID=1`, AP rows=13, `failure=null`, zero crash-marker matches. Evidence: `docs/forensics/runtime-evidence/20260615T-clean-head-restore-after-vp-probe/20260615T225138-snappiness-manifest.json` and `20260615T225138-snappiness-bench-12201.log`. | 2026-06-15 ~22:52 AWST |

> 2026-06-14 flash note: the 2026-06-11 firmware-swap comparison is no longer
> the deployed 1401 state. Upload to 1401 returned success from PlatformIO on
> `/dev/cu.usbmodem1101`, then the same main identity re-enumerated as
> `/dev/cu.usbmodem12201`. Post-flash checks on `/dev/cu.usbmodem12201` verified
> `:chip_id` = `F887A500`, `:version` = `40103`, `CONFIG.SAMPLE_RATE` = `12800`,
> `CONFIG.SAMPLES_PER_CHUNK` = `96`, and a 75 s AP soak with 88 `[AP]` lines and
> zero crash markers.

**Build fingerprints over serial (115200):** pre-forward-graft builds
(≤ dd2902f) print the SHORT `[AP]` line (no `bpm=`/`onset=` section);
post-graft builds print the long v2 form. `:version` answers `40103` on both
lineages — version number does NOT discriminate; use the `[AP]` shape or git
flash records.

## 2.1 Sample-rate research status (not a deployed-state change)

- Current production timing remains `12800 / 96 / decim=3` until a candidate
  tuple passes live acquisition, AP/VP, calibration, and eyes-on gates.
- Known unresolved hardware risk: with 32-bit stereo I2S slots, 12.8 kHz implies
  BCLK `819.2 kHz`, below the SPH0645 normal-mode minimum reported in the
  sample-rate consultant findings. This is a research risk, not proof that the
  currently deployed firmware is broken.
- Known DSP hygiene issue at the production default `NOTE_OFFSET=12`: bins
  `71..79` target frequencies above the 6.4 kHz Nyquist limit. Firmware changes
  that consume musical state should clamp those bins out unless the active sample
  rate and note offset make them valid.
- Do not promote `16000/*` or `32000/*` by compile/upload success. Promotion
  requires matched calibration provenance and runtime evidence, not just a green
  PlatformIO build.
- `k1_sample_rate_32k_spike` is explicitly build-only at `50063f4`: the upload
  guard blocks it even on the correct main identity until the hardware/runtime
  gate is deliberately reopened.
- Sample-rate probe envs now remove inherited production tuple macros before
  declaring candidate timing. This prevents false builds where a matrix env name
  says one tuple but the inherited compile flags still build another tuple.
- Live `16000/120/d3` AP0/VP1 probe result on main K1: **NO-GO as run**. The
  binary booted with `RUNTIME_TIMING_GUARD timing_ok=1` and the expected
  `sample_rate=16000`, `samples_per_chunk=120`, `tempo_decim=3`, `ap_core=0`,
  `vp_core=1`, but repeatedly hit task watchdog resets on CPU0/`loopTask`
  before APCAD rows were captured. Evidence:
  `docs/forensics/2026-06-15-16k120-live-probe-verdict.md` and
  `docs/forensics/runtime-evidence/20260615T0920-sample-rate-16k120-probe/`.
  Main was restored to `k1_hardware` immediately afterwards; paired restore
  proof is `docs/forensics/runtime-evidence/20260615T092202-snappiness-manifest.json`.
- Follow-up acquisition-isolation probe on the same tuple narrowed the blocker:
  `k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acq_probe` captured `2000`
  rows at `16000/120`, AP core `0`, VP core `1`, with `i2s_status=0` for every
  row, `bytes_mismatch_count=0`, `frame_gap_count=0`, and
  `APCAD_CAPTURE_DONE,count=2000,dropped=0`. The first acquisition-only run hit
  WDT while dumping the APCAD serial buffer; addr2line resolved it to
  `HWCDC::write` / `Print::printFloat` inside `ap_cad_capture_dump()`. The dump
  now yields every 16 rows and the superseding capture has zero crash-marker
  matches. Verdict: 16 kHz acquisition is not the current blocker; full AP DSP
  compute/yield budget is. Evidence:
  `docs/forensics/2026-06-15-16k120-acquisition-isolation-verdict.md` and
  `docs/forensics/runtime-evidence/20260615T0937-sample-rate-16k120-acq-probe-yield/`.
  Main was restored to production afterwards; paired restore proof is
  `docs/forensics/runtime-evidence/20260615T093738-snappiness-manifest.json`.
- AP stage profiling then narrowed the full-AP 16 kHz blocker further:
  acquisition, GDFT, novelty, snapshot, onset, and saliency stage probes held
  declared AP cadence with clean I2S, while `stage_tempo` dropped to
  `123.149 Hz` AP / `41.044 Hz` accepted novelty with `i2s_status=0`,
  `bytes_mismatch_count=0`, and no crash markers. Verdict: the first hard
  `16000/120/d3` full-AP blocker is `sb_tempo_update()` / ACF update cost.
  Evidence: `docs/forensics/2026-06-15-16k120-ap-stage-profile-verdict.md`.
- ACF follow-up narrowed the blocker again. The ACF-d8 probe recovered mean
  cadence but left heavy refresh frames; the ACF spread-16 probe reduced
  `tempo_acf_elapsed_us` p95 to `1028 us` while holding AP `133.340 Hz` and
  novelty `44.447 Hz` with clean I2S and zero crash markers, but still failed
  the full AP p95 contract (`total_ap_loop_elapsed_us` p95 `9591 us` vs
  `7500 us`). Evidence:
  `docs/forensics/2026-06-15-16k120-acf-spread16-probe-verdict.md` and
  `docs/forensics/runtime-evidence/20260615T1149-sample-rate-16k120-tempo-acf-spread16/`.
- The next active-budget probe split ACF work more finely and added
  `active_ap_work_elapsed_us = total_ap_loop_elapsed_us - i2s_read_elapsed_us`
  to the APCAD summary so I2S wait time is not confused with CPU work. Spread12
  still failed emitted active-work p95 (`7528 us`) with `27` emitted rows over
  `7500 us`. Spread8 is the first live `16000/120/d3` stage-tempo probe whose
  active AP CPU work clears the 7.5 ms period: AP `133.353 Hz`, novelty
  `44.449 Hz`, clean I2S, zero frame gaps, zero timestamp regressions,
  `tempo_acf_elapsed_us` p95 `524 us`, active-work p95 `7050.75 us`, emitted
  active-work p95 `7213.8 us`, active max `7451 us`, and `0` active/emitted rows
  over `7500 us`. Verdict: this is a real research pass for the stage-tempo
  active-work gate, not production promotion. `16000/120/d3` still needs longer
  AP+VP, matched calibration, corpus, and eyes-on evidence. Evidence:
  `docs/forensics/2026-06-15-16k120-acf-spread8-active-budget-verdict.md`,
  `docs/forensics/runtime-evidence/20260615T1214-sample-rate-16k120-tempo-acf-spread12/`,
  and `docs/forensics/runtime-evidence/20260615T1218-sample-rate-16k120-tempo-acf-spread8/`.
- Extended spread8 runtime proof then held the same active-work gate for the
  longest no-drop APCAD window currently supported by the firmware buffer:
  17 s at `16000/120/d3`, `2267/2304` rows, `dropped=0`, AP `133.325 Hz`,
  novelty `44.448 Hz`, clean I2S, zero frame gaps, zero timestamp regressions,
  `tempo_acf_elapsed_us` p95 `540.4 us`, active-work p95 `6940 us`, emitted
  active-work p95 `7133 us`, active max `7407 us`, and `0` active/emitted rows
  over `7500 us`. A 75 s mixed AP/VP soak also ran with main on spread8 and
  bench on production (`failure=null`, expected `timing_parity=false`, both
  AP/VP rows `79/79`, zero crash markers). Verdict: better runtime evidence,
  still no promotion. Evidence:
  `docs/forensics/2026-06-15-16k120-spread8-extended-runtime-verdict.md`,
  `docs/forensics/runtime-evidence/20260615T123733-sample-rate-16k120-tempo-acf-spread8-17s/`,
  and `docs/forensics/runtime-evidence/20260615T123849-sample-rate-16k120-spread8-apvp-75s/`.
- Full-AP spread8 then passed the same active-work gate without the stage stop:
  17 s at `16000/120/d3`, `2267/2304` rows, `dropped=0`, AP `133.341 Hz`,
  novelty `44.444 Hz`, clean I2S, zero frame gaps, zero timestamp regressions,
  `tempo_acf_elapsed_us` p95 `549.8 us`, active-work p95 `6932.7 us`, emitted
  active-work p95 `7121.2 us`, active max `7474 us`, and `0` active/emitted
  rows over `7500 us`. A 75 s mixed AP/VP soak also ran with main on full-AP
  spread8 and bench on production (`failure=null`, expected
  `timing_parity=false`, both AP/VP rows `79/79`, zero crash markers). Verdict:
  full-AP runtime viability is now proven for this probe window, but production
  promotion still requires matched calibration, corpus, and eyes-on evidence.
  Evidence:
  `docs/forensics/2026-06-15-16k120-full-ap-spread8-runtime-verdict.md`,
  `docs/forensics/runtime-evidence/20260615T124922-sample-rate-16k120-full-ap-acf-spread8-17s/`,
  and `docs/forensics/runtime-evidence/20260615T125136-sample-rate-16k120-full-ap-spread8-apvp-75s/`.
- Full-AP spread4 plus compact APCAD real-corpus soaks improved the test
  substrate but did **not** promote `16000/120/d3`. Eighteen P4 references ran
  cleanly with AP `133.332..133.337 Hz`, novelty `44.444..44.445 Hz`,
  active-work p95 `7040..7168 us`, active-work max `7369..7458 us`, and zero
  I2S/byte/core/frame/timestamp faults. The high-risk Ziggy lane still produced
  one emitted active-work over-budget row (`active_max=7779 us`,
  `active_over_7500_count=1`, `emitted_active_over_7500_count=1`). Verdict:
  spread4 remains research-only; keep production on `12800/96/d3` and
  investigate the remaining tempo active-work spike before retesting the
  risk-set. Evidence:
  `docs/forensics/2026-06-15-16k120-spread4-real-corpus-verdict.md`,
  `docs/forensics/runtime-evidence/20260615T145158-k1-real-music-corpus/`,
  `docs/forensics/runtime-evidence/20260615T154939-k1-real-music-corpus/`,
  and `docs/forensics/runtime-evidence/20260615T142351-k1-real-music-corpus/`.
- Post-16k-gate production evidence is now clean on both registered K1s at
  `12800/96/d3` with measured calibration. Captain had confirmed the room was
  quiet before the paired noise-cal pass. Main (`F887A500` on current
  `/dev/cu.usbmodem12201`) accepted `CAL_SOURCE=measured`, `CAL_VALID=1`,
  `CAL_PROFILE_LOADED=1`, `DC=-4688`, `SSL=421`; bench (`B489A500` on current
  `/dev/cu.usbmodem12401`) accepted `CAL_SOURCE=measured`, `CAL_VALID=1`,
  `CAL_PROFILE_LOADED=1`, `DC=-812`, `SSL=424`. The follow-up 75 s production
  soak passed with timing parity and AP/VP rows on both devices. Real-corpus
  SubFocus 120 s split lanes then passed AP-only (`142/143` AP rows) and
  VP-only (`147/145` VP rows) with zero crash-marker matches. The split lanes
  are deliberate: main's USB serial stream can delay long status/dump output
  enough to bury later stream toggles, so the helper now supports
  `--stream-surface both|ap|vp|none` and uses a quiet pre-capture path. This is
  software-observable production evidence, not physical BCLK proof. Captain
  then reported both devices looked alright, closing the product eyes-on gate
  for the current production baseline. Evidence:
  `docs/forensics/2026-06-15-post-16k-gate-calibration-and-vp-evidence.md`,
  `docs/forensics/runtime-evidence/20260615T195749-paired-noise-cal-post-16k-gate/`,
  `docs/forensics/runtime-evidence/20260615T-post-16k-gate-paired-production-soak/`,
  `docs/forensics/runtime-evidence/20260615T-post-cal-real-corpus-subfocus-paired-ap-only/`,
  and
  `docs/forensics/runtime-evidence/20260615T-post-cal-real-corpus-subfocus-paired-vp-only/`.

## 3. Branch and anchor truth (2026-06-11)

- **Live lineage:** `rescue/1401-head-minus-killset` — all 2026-06-11 work
  (kill-set revert, p90 noise-cal, modes 24–29, palette-crush + held-hue fixes,
  HD sampling, drop-cut, attack snap, pairing presets, wireless A/B bench,
  effects queue + slots). `wip/audio-saliency-recovery` is parked at `300dd6e`;
  `main` is older. Merge/promotion is an OPEN Captain decision — never rebase
  or reset these without his word.
- **Eyes-on anchors (for bisects/regressions):**
  - `a5ce32e` — last Captain eyes-on PASS on 1401 ("effects back to normal", 06-07)
  - `9eb3cee` — waveform-tempo-v1 deep anchor (mode 18 kept, 7.9/10)
  - `dd2902f` — bench/snappy-reference-telemetry tip = 9eb3cee + one telemetry
    commit; the Captain-declared-safe REFERENCE build (pre-forward-graft,
    pre-SPL). This is what "the old firmware" means in 2026-06-11 comparisons.
  - tag `k1-rescue-baseline-20260611` (@3147010) — rescue-lane rollback point
  - `f23e438` — preserved Codex dirty tree (salvage source; never deploy)

## 4. Environment rules

| Env | Shippable? | Notes |
|---|---|---|
| `k1_hardware` | YES (production) | 1401 only. Wireless **compile-gated OFF** (`SB_K1_WIRELESS_ENABLED` undefined) — measured A/B FAIL: onsets −33%, mic level −17.6% with radio on (evidence `docs/forensics/runtime-evidence/wireless-ab/20260611`, commit 099ebc6). Do not re-enable without a Captain decision. |
| `k1_bench_reference` | YES | 12201 only. Same DSP/flags as k1_hardware, bench GPIO map. |
| `k1_hardware_harness`, `k1_wireless_ab_probe`, `*_trace_dev`, `*_probe`, `*_motion_lab` | **NO — non-shippable** | Env names MUST carry a non-shippable marker (`harness/probe/trace_dev/motion_lab`) — statically enforced. `k1_wireless_ab_probe` is the ONLY wireless-enabled build; Tab5 can connect only when a device runs it (with the measured AP cost above). |

## 5. Flash + serial discipline (the known traps)

1. **Cursor grabs the ports.** A Cursor extension-host auto-opens
   `/dev/tty.usbmodem*` and respawns after kill. Before flashing:
   `lsof /dev/tty.usbmodem* /dev/cu.usbmodem*` → `kill <PID>` → retry.
2. **`.pio/build/<env>` corrupts recurrently** (concurrent processes;
   `.sconsign313.dblite: No such file or directory` or garbled dep files).
   Fix: `rm -rf .pio/build/<env>` and rebuild. Never "fix" source for this.
3. **Opening a serial port DTR-resets the device** (pyserial/macOS, even with
   dtr/rts cleared post-open). Every probe reboots the unit — wait for
   `SYSTEM INIT COMPLETE` before sending commands; expect `rst:0x15
   (USB_UART_CHIP_RESET)` in the banner (it is NOT a crash marker).
4. **Line commands need the `:` prefix** (`:secondary_mode=3`,
   `:slot_list`). Bare bytes are single-character HOTKEYS — an unprefixed
   command string fires ~16 random hotkeys (2026-06-11 incident; RAM-only
   damage, cleared by reset).
5. **Wireless-enabled builds boot slow** (WiFi AP bring-up): allow ~30 s
   before identity probes, not the usual ~10 s.
6. **75 s serial soak before Captain eyes-on** (count boots, scan crash
   markers, confirm 1 Hz `[AP]` cadence) — mandatory after every flash.
7. Calibration: `start_noise_cal` NEVER auto-fired; Captain confirms silence
   verbally. Persisted SSL/DC are per-device NVS — they survive reflashes, so
   a device can run new firmware with an old cal value.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-21 | captain+agent:claude-code | Captain eyes-on A/B of corrected GDFT arithmetic + true-center on 12201 (LGP plate, music). VERDICT: does NOT pass — A (legacy) ≈ B (corrected+tc), B slightly worse-but-negligible; "louder→dimmer" inverse present in BOTH legs = pre-existing broadband AGC clamp (not this lane); both worse than the effect-framework reference on 2101. All 3 flags stay default-OFF, NOT promoted; corrected arithmetic = device-proven capability with no product value. No MabuTrace (gate), no tuning. Device left on shippable A. See `docs/forensics/.../eyes-on-verdict.md`. |
| 2026-06-21 | agent:claude-code | Logged the `K1_GDFT_INT64_RECURRENCE_V1` 4-leg device A/B on 12201 (`B489A500`). Resolved the GDFT int32 overflow CHAIN (magnitude + recurrence-multiply): leg C magnitudes match the host replica to <1% (q0ovf=0); leg D PASSES true-centre acceptance (415.3→bin23, 440→bin24, 466.16→bin25). True-centre VINDICATED — it was masked by the overflows, never broken. Marked the prior `15fab24` row's "not testable" conclusion as RESOLVED. q-state needs no widening. All flags stay default-OFF. Net deployed = shippable. |
| 2026-06-21 | agent:claude-code | Logged the `K1_GDFT_TRUE_CENTER_V1` device A/B on bench 12201 (`B489A500`): harness OFF→ON flashed then RESTORED to shippable `k1_bench_reference` (`:gdft_probe` returns nothing; identity guard-verified before each write and post-restore). Result: 440→bin 24 but 415.3→bin 26 (mag 53). **Root cause PROVEN by a second pass with GDFTP5 top-5/neighbour telemetry**: int32 overflow in the production Goertzel magnitude formula at sustained resonance → near-resonance bins clamp to exactly 0.00 (ON 415.3: bin22/23/24=0; OFF 440: bin24/25=0). Present in BOTH OFF and ON (not true-centre-specific); contaminates the A/B argmax. Earlier "scalloping/confirmed-negative" framing RETRACTED; "host contradicts" RESOLVED (host couldn't bit-reproduce the wrap). Net deployed state unchanged = shippable. |
| 2026-06-20 | agent:claude-code | Recorded TEMPORARY eyes-on flash of `k1_effect_registry` (`7bbb0b8`, registration-architecture rewire R1–R4) to main K1 `F887A500` on `/dev/cu.usbmodem2101` (identity verified by esptool `read_mac`); logged host-gate green set, boot registry self-check PASS, on-device native registration (ords 30–34), CL-1 ack-barrier device-proof via mid-render `slot_save`, and 75 s clean soak. Eyes-on verdict pending Captain; baseline `72cb650` restore owed after. |
| 2026-06-19 | agent:claude-code | Recorded Captain standing authorization for the K1↔Tab5 phase and the live esptool identity map of all 4 enumerated ports: main K1 on `1101`, bench on `12401`, **Tab5 (ESP32-P4) on `12201`**, and an **unregistered 4th ESP32-S3 on `1401`**; flagged that platformio port pins now point at the wrong silicon |
| 2026-06-15 | agent:codex | Closed current production eyes-on gate after Captain reported both devices looked alright on the post-16k measured-calibration baseline |
| 2026-06-15 | agent:codex | Recorded post-16k-gate measured calibration plus production AP/VP and real-corpus split AP/VP evidence for both registered K1s; documented the serial-stream harness split and remaining physical BCLK/eyes-on gates |
| 2026-06-15 | agent:codex | Recorded full-AP spread4 real-corpus compact-soak verdict: eighteen clean P4 references, one Ziggy emitted active-work over-budget spike, production restored to `12800/96/d3`; spread4 remains research-only |
| 2026-06-15 | agent:codex | Recorded full-AP spread8 runtime proof and production restore after flashing exact commit `ea12acd` to both registered K1 identities |
| 2026-06-15 | agent:codex | Recorded spread8 extended runtime proof and production restore after flashing exact commit `f7fe864` to both registered K1 identities |
| 2026-06-15 | agent:codex | Updated deployed-state rows after flashing exact commit `c89e576` to both registered K1 identities; recorded ACF spread8 active-budget pass, paired 75 s production proof, and the remaining non-promotion gates |
| 2026-06-15 | agent:codex | Updated deployed-state rows after flashing exact commit `401599e` to both registered K1 identities; recorded ACF spread-16 probe verdict and paired 75 s production proof with timing parity and zero crash-marker matches |
| 2026-06-15 | agent:codex | Flashed committed `6d5b476` AP-stage-profiler source to both registered production envs and recorded paired 75 s timing-parity proof with zero crash-marker matches |
| 2026-06-15 | agent:codex | Recorded 16 kHz AP stage profiling: tempo ACF/update is the first hard full-AP blocker after acquisition/GDFT/novelty/snapshot/onset/saliency all held clean stage probes |
| 2026-06-15 | agent:codex | Flashed committed `533003a` to both registered K1 identities after the acquisition-isolation probe landed, then recorded paired 75 s proof with production timing parity and zero crash-marker matches |
| 2026-06-15 | agent:codex | Added 16 kHz acquisition-isolation result: isolated `16000/120/d3` I2S/APCAD capture is clean after serial-dump yielding, so the remaining 16 kHz blocker is full AP DSP compute/yield budget, not I2S byte integrity |
| 2026-06-15 | agent:codex | Recorded live `16000/120/d3` AP0/VP1 probe as NO-GO as run due repeated task-watchdog resets before APCAD rows, then restored main to production and recorded paired restore proof |
| 2026-06-15 | agent:codex | Updated deployed-state rows after flashing exact commit `50063f4` to both registered K1 identities; recorded paired 75 s proof with response-profile dump visibility and 32 kHz upload guard now present on-device |
| 2026-06-15 | agent:codex | Promoted the response profile into firmware source commit `5f69377`, flashed main with compiled `response_gain=3.0` and bench with `response_gain=1.0`, and recorded paired 75 s post-flash proof |
| 2026-06-15 | agent:codex | Restored both registered K1s from non-shippable AP front-end probe firmware to shippable production envs at firmware source commit `1329dff`, recorded paired post-restore proof, and linked buffered APCAD tempo-lock verdict |
| 2026-06-15 | agent:codex | Updated deployed-state rows after flashing committed `a9fb4ca` runtime response-gain probe firmware to both registered K1 identities, recording post-flash soak evidence, and explicitly restoring both units to `response_gain=1.0` |
| 2026-06-15 | agent:codex | Recorded Captain-confirmed quiet-room noise calibration and post-cal no-music baseline for both registered K1 identities: main remained high-DC (`-4698`), bench measured low-DC (`-828`) |
| 2026-06-15 | agent:codex | Updated deployed-state rows after flashing committed `a995ff6` Nyquist-safe musical-bin gate firmware to both registered K1 identities and recording paired 75 s soak evidence |
| 2026-06-15 | agent:codex | Updated deployed-state rows after flashing exact committed `03b7cdf` phase 3/4/5 runtime-controls firmware to both registered K1 identities and recording phase345 proof plus paired 75 s soak evidence |
| 2026-06-15 | agent:codex | Added sample-rate research status note: keep production on 12800/96/d3, track SPH0645 BCLK risk, and require Nyquist-safe musical consumers before tuple promotion |
| 2026-06-15 | agent:codex | Updated deployed-state rows after flashing exact committed `074a2b3` to both registered K1 identities and recording paired post-flash soak evidence |
| 2026-06-15 | agent:codex | Updated deployed-state rows after flashing the noise-calibration repair working tree to both registered K1 identities and recording post-flash/post-cal runtime evidence |
| 2026-06-11 | agent:claude-code | Created at Captain's request: canonical device↔env↔build registry after the firmware-swap comparison; folds in flash/serial discipline learned 2026-06-10/11 |
