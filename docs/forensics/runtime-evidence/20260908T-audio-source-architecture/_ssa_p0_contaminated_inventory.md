---
abstract: "P0 inventory of 2026-09-07 PCM1808/ST25 bring-up artefacts after Captain correction: background music continued during stimulus evaluation. VALID = clock/DMA/SRC/soak err-short-clip/ST25 identity. CONTAMINATED = any stimulus-dependent signal characterisation (L/R, amplitude, snapshots). FR/THD/crosstalk/Line-vs-MIC were never written as conclusions."
task: P0-CONTAMINATED-INVENTORY
date: 2026-09-08
source_tree: docs/forensics/runtime-evidence/20260907T-pcm1808-st25-bringup/
captain_correction: "During a prior stimulus evaluation, normal music continued while the test stimulus played."
stamp_valid: KEEP_AS_DIGITAL_PROOF
stamp_contaminated: CONTAMINATED_BACKGROUND_PLAYBACK / INADMISSIBLE_FOR_SIGNAL_CHARACTERISATION
default_verdict: NOT_VERIFIED for any L/R, FR, THD, amplitude, crosstalk, or Line-vs-MIC claim
do_not_delete: 20260907 evidence retained; this file labels only
---

# P0 — 2026-09-07 PCM1808 artefact inventory (contaminated background playback)

**Captain correction (2026-09-08):** a stimulus evaluation ran while ordinary music kept playing. That mix is not a controlled analogue source. Do not delete the 20260907 pack.

**Rule used here:** digital clocks, DMA cadence, SRC block-count invariant, soak `err`/`short`/`clip` (as those counters were then defined), USB/chip identity, and ST25 SPI identity do not need a known analogue stimulus. RMS, L/R deltas, snapshots, min/max, and any “did afplay move the level” comparison do.

**Not found in this pack (so they are not proven, not disproven):** dedicated FR, THD, crosstalk, or Line-vs-MIC reports. No sibling 2026-09-07 log outside this directory named those claims. Absence ≠ a clean measurement.

Root for quotes: `/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/forensics/runtime-evidence/20260907T-pcm1808-st25-bringup/`

---

## Table 1 — VALID (keep; not analogue characterisation)

| File | Quote | Why VALID |
|---|---|---|
| `PCMCLK_RECEIPT.txt` | `[PCMCLK] lrck_hz=47985.9` / `bclk_hz=3069048.5` / `ratio=63.957` / `mode=48K_MASTER_I2S24` / `gate=PASS` | PCNT digital clock gate on GPIO14/13. Independent of what analogue audio was playing. **Do not relabel this PASS.** |
| `PCMCLK_RECEIPT.txt` | `[PCMRATE] frames=48000 us=1000043 hz=47997.9 gate=PASS` then `[PCM_RATE_PROOF] PASS` | DMA frame count vs wall time. Digital cadence, not RMS. |
| `PCMCLK_RECEIPT.txt` | `[PCMING] source=pcm1808 canonical_hz=12800 hop=96` and `RUNTIME_TIMING_GUARD: timing_ok=1 sample_rate=12800 samples_per_chunk=96` | Firmware hop contract after SRC, not analogue FR. |
| `PCMCLK_RECEIPT.txt` | `60s soak … dma_hz=46782 err=0 short=0 clip=0 PASS_STREAM=1` and `10 min soak: dma_hz=46823.5 tspan=596.95s err=0 short=0 clip=0 n=299 PASS_STREAM=1` | Stream-health slice only (DMA + those three counters as then defined). RMS in the same soaks is **not** this row. |
| `pcmclk-reset.txt` | `[PCMCLK] lrck_hz=47985.9` … `gate=PASS` then `[PCMRATE] … hz=47997.9 gate=PASS` / `[PCM_RATE_PROOF] PASS` | Live boot reprint of the same clock/rate gate. |
| `pcmclk-boot.txt` | `[PCMRS] in=971280 out=259008 blocks=2698 invariant=PASS` (and every later `invariant=PASS`) | SRC 4/15 block-count invariant. Integer in/out, not signal quality. |
| `pcmclk-reset.txt` | `[PCMRS] in=37440 out=9984 blocks=104 invariant=PASS` (and later `invariant=PASS`) | Same SRC invariant after USB reset. |
| `PCM-R1-SOAK-60s.txt` | `frames_live0=6510240 frames_live1=9321840 delta=2811600 tspan=60.1 dma_hz=46782` / `sum_err=0 sum_short=0 sum_clip=0` / `PASS_STREAM=1` | 60 s soak stream health. Live window note (`t=2.1..62.2`, stale burst would fake 60 kHz) is also digital-cadence hygiene, keep. |
| `PCM-SOAK-10MIN.txt` | `delta=27951120 tspan=596.95 dma_hz=46823.5` / `sum_err=0 sum_short=0 sum_clip=0` / `PASS_STREAM=1` | 10 min soak stream health. `mean_rmsL`/`mean_rmsR` on the same line are **not** this row. |
| `ST25ID_RECEIPT.txt` | `[ST25ID] hex=0x31 irq=0 pins=sclk7 mosi6 miso5 cs4` then `gate=PASS family=ST25R3916B` | SPI register 0x7F identity. Not audio. First boot `gate=FAIL reason=UNEXPECTED_IDENTITY` on `a66273c9` is also valid history of the classifier. |
| `ST25ID-boot-pass.txt` | `[ST25ID] hex=0x31 … gate=PASS family=ST25R3916B` | Silicon boot witness for identity PASS @ `605b855e`. Ignore `[AP]` lines in this file (Table 2). |
| `ST25ID-boot.txt` | `[ST25ID] hex=0x31 … gate=FAIL reason=UNEXPECTED_IDENTITY` | Silicon boot witness for the pre-classifier-fix FAIL. Ignore `[AP]` lines. |
| `IDENTITY.txt` | `chip_id=9087A500` / `git=acaecaa8` / `env=k1_main_rpl_im69d` / `usb_serial=B4:3A:45:A5:87:90` | Pre-probe product identity on usbmodem1101. |
| `TARGET_IDENTITY.txt` | `usb_serial=B4:3A:45:A5:87:90` / `port=/dev/cu.usbmodem1101` | USB target lock. |
| `RESTORE_DUMP.sha256` | `1e2744256eaaaf170f18600f5daafc39bc33bce1521bd1067f92f48a6a3a3a8e  restore-pre-pcm-probe-0x0-2MB.bin` | Product restore dump digest. |
| `live-dump-preflight.txt` | `BUILD: version=40103 git=acaecaa8 epoch=1788173468 env=k1_main_rpl_im69d` / `CHIP ID: 9087A500` / `CAL_SOURCE: persisted_profile` / `CAL_VALID: 1` | Pre-PCM `:dump` identity + cal inherit. `[AP]` RMS in the same file is **not** this row. |
| `PREFLIGHT.md` | I2S1 free; candidate PCM 13/14/10 ACCEPT; candidate NFC 7/6/5/4/2 ACCEPT on this env only | Pin/peripheral census before analogue work. Not a signal claim. |
| `docs/handover/HANDOVER_2026-09-07_PCM1808_ST25R3916B_BRINGUP.md` | changelog: `PCMCLK gate=PASS 47.986 kHz / ratio 63.957, DMA 47.998 kHz, hop 12800/96` and `ST25 identity PASS … hex=0x31 family=ST25R3916B` | Repeats digital PASSes. The same changelog’s “Analog L/R map not proven” is Table 2. |
| `docs/hardware/device-build-registry.md` (2026-09-07 rows) | `[PCMCLK] lrck_hz=47985.9 bclk_hz=3069048.5 ratio=63.957 gate=PASS` then `[PCM_RATE_PROOF] PASS` hop 12800/96; 10 min soak `dma_hz=46823.5 err=0`; ST25 `hex=0x31 gate=PASS` | Registry restates digital PASSes. No FR/THD/L/R characterisation in those rows. |
| `BASE_HEAD.txt` / `BASE_STATUS.txt` / `BASE_TEST_FAILURES.txt` / `NEW_TEST_FAILURES.txt` | git `657c8322` freeze; BLE-iPhone pytest dirt | Session hygiene, not analogue. |
| `leftover-ble-iphone-platformio.ini.patch` | BLE-iPhone env aside | Unrelated leftover. Not PCM signal. |
| `restore-bin-inventory.txt` | webflash/worktree bins `match_factory=False` | Restore-path warning. Not analogue. |

---

## Table 2 — CONTAMINATED / INADMISSIBLE_FOR_SIGNAL_CHARACTERISATION

Stamp: `CONTAMINATED_BACKGROUND_PLAYBACK`. Keep the files. Do not use them as L/R map, FR, THD, amplitude, crosstalk, Line-vs-MIC, or “stimulus did/did not couple.”

| File | Quote | Why CONTAMINATED |
|---|---|---|
| `PCMCLK_RECEIPT.txt` | `NOT YET PROVEN: physical L/R DMA slot map (Mac afplay on Multi-Output Device did not move PCM RMS vs baseline; analog path to PCM1808 not confirmed)` | This **is** a stimulus-dependent L/R + amplitude claim. Background music would hold RMS high and hide (or fake) an afplay delta. The map remains unproven; the “did not move” measurement is **inadmissible**, not a hardware FAIL. |
| `docs/handover/HANDOVER_2026-09-07_PCM1808_ST25R3916B_BRINGUP.md` | `Analog L/R map not proven.` | Status “not proven” is still the right *outcome*, but it rests on the contaminated afplay/RMS attempt. Do not treat it as a clean negative coupling test. |
| `PCM-R1-SOAK-60s.txt` | `t=2.1 frames=6510240 rmsL=48597 rmsR=52106 …` through `t=62.2 … rmsL=33752 rmsR=43181` | Amplitude and L vs R levels during a soak that was not a quiet, exclusive stimulus. Inadmissible for L/R, amplitude, crosstalk. `err`/`short`/`clip`/`dma_hz` stay Table 1. |
| `PCM-SOAK-10MIN.txt` | `mean_rmsL=36392 mean_rmsR=35626` and per-row `rmsL`/`rmsR` (e.g. `t=312.4 … rmsL=58523 rmsR=58033`) | Same: mean/peak amplitude and L≈R are not a crosstalk or stereo-map proof under mixed music+stimulus. |
| `pcmclk-boot.txt` | `[PCMRAW] … rmsL=73645 rmsR=75428 minL=-302243 maxL=279846 minR=-310178 maxR=279774 clip=0` | PCMRAW RMS/min/max are analogue amplitude. `clip=0` on those lines is Table 1 (counter as then defined); the RMS/min/max are Table 2. |
| `pcmclk-reset.txt` | `[PCMRAW] frames=37440 … rmsL=32085 rmsR=45587 minL=-144933 maxL=138624 minR=-168118 maxR=146922` | Post-reset amplitude and L≠R. Cannot map slots or estimate imbalance with mixed playback. |
| `pcmclk-reset.txt` | `[PCMSNAP] frames=2048 bytes=12288 dump=hex24le` then `0 4CABFF 798400` … | Raw stereo samples. Any FR, L/R, THD, or waveform read from this dump is mixed-source. |
| `ST25ID-boot-pass.txt` | `[AP] SSL=157 … rms_raw=0.0170 … raw_i16_rms=30.7` (and following `[AP]` rows) | IM69 PDM telemetry after ST25 flash, while music was in the room. Inadmissible as Line-vs-MIC or mic amplitude. Identity lines stay Table 1. |
| `ST25ID-boot.txt` | same class `[AP] … rms_raw=… raw_i16_rms=…` | Same MIC-path contamination. |
| `live-dump-preflight.txt` | `[AP] SSL=157 … rms_raw=0.0014` / `raw_i16_rms=6.9` (and siblings) | Pre-PCM IM69 `:dump` levels. Not a Line-vs-MIC control unless the room was proven quiet; this session’s music correction makes that unproven. Identity/cal lines stay Table 1. |

### Claims **not present** as artefacts (do not invent a PASS or FAIL)

| Claim class | Found in 20260907 pack? | Disposition |
|---|---|---|
| Frequency response | No FR plot, tone table, or bin-vs-Hz write-up | `NOT_VERIFIED` — never measured cleanly |
| THD | No THD number | `NOT_VERIFIED` |
| Crosstalk (explicit) | No isolation dB; only simultaneous `rmsL`/`rmsR` | Those RMS pairs are Table 2, not a crosstalk test |
| Line vs MIC (explicit) | No A/B write-up | Do not infer from PCMRAW vs `[AP]` under mixed playback |

### Sibling search (same day, outside the 20260907 dir)

Searched `docs/handover/`, `docs/spec-index.md`, `docs/hardware/device-build-registry.md`, `progress.md`, `CHANGELOG.md`, `scripts/agent/post-session-report.md`, `_scratch/` for 2026-09-07 + `PCM RMS` / `afplay` / `Multi-Output` / stimulus L/R.

Hits that **repeat** the Table 1/2 material: handover changelog, registry 2026-09-07 rows, spec-index pointer. No extra FR/THD/crosstalk/Line-vs-MIC log from that day.

---

## Split rule for mixed files (do not delete)

A file can be VALID on one axis and CONTAMINATED on another. Example: `PCM-SOAK-10MIN.txt` **keeps** `dma_hz=46823.5 err=0 short=0 clip=0`; **discards** `mean_rmsL=36392` for characterisation.

`PCMCLK_RECEIPT.txt` clock/rate/soak-health **stays** the lane’s digital proof. Only the afplay L/R paragraph is withdrawn as a measurement.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | agent:grok SSA P0-CONTAMINATED-INVENTORY | Created VALID vs CONTAMINATED tables from 20260907 pack + same-day siblings. Did not modify 20260907. |
