---
abstract: "P4 CLOSED on Main RPL a08dc10e / k1_main_rpl_pcm1808_shadow. IM69 remains the AP source while PCM runs shadow at 48 kHz. After the lamp was moved to the MacBook speakers, Multi-Output drove the same deterministic programme into AUX and the room path. Three clean jittered-transient epochs gave positive LINE→MIC lag 5.66–7.44 ms (median 7.07 ms); coarse drift estimates 80–227 ppm (median 112 ppm). Shadow AP cost remains ~0.16 ms p99 versus MIC-only."
---

# P4 dual capture — 2026-09-08

Silicon: Main RPL chip `9087A500`, USB `B4:3A:45:A5:87:90`, `/dev/cu.usbmodem1101`.
`IDENTITY OK: git=a08dc10e env=k1_main_rpl_pcm1808_shadow epoch=1788847940`.
Flashed with `k1-flash-verified.sh`. Product restore remains `k1_main_rpl_im69d` @ `acaecaa8`.

## What is true now

The microphone still owns the analysis pipeline. Line-In runs beside it as a shadow recorder: 48 kHz in, 48 kHz consumed, no overflows, no ring drops while we are measuring. The huge hex dump happens only after that window is frozen. Asking for a dump while the window is still filling is refused.

Mac → AUX → PCM1808 is real. The earlier acoustic failure was physical placement/drive, not firmware: after Captain moved the lamp to the MacBook speakers, a full-scale guarded 997 Hz fixture at speaker volume 100 moved the raw IM69 from its ~14-count RMS floor to ~66 counts RMS (peak 432).

The existing **Multi-Output Device** then proved the required same-programme topology. A full-scale guarded 997 Hz fixture drove both paths simultaneously (PCM RMS ~1.16M counts; MIC RMS ~57 counts), with ovf=0 / ring_drop=0 / mic_err=0. The deterministic full-scale jittered-transient fixture was then captured three times for 4 s epochs, starting after its leading guard. All three epochs were clean and unambiguous.

Alignment results: positive LINE→MIC lag **5.66–7.44 ms**, median **7.07 ms**, peak correlation 0.677–0.706, peak-to-sidelobe 1.68–2.03. Coarse 2.8 s drift estimates were **80–227 ppm**, median **112 ppm**. The spread is too wide to present 112 ppm as a precision oscillator measurement; the product-relevant finding is that the two capture domains are measurably asynchronous and long paired recordings need timestamp/alignment treatment. Normal one-source AP ownership does not require locking their clocks.

Running the Line-In capture task next to the microphone costs about 50 µs on the average analysis hop and 160 µs at p99. Both stay under the 8 ms budget.

## Instrument (dump after freeze)

| Check | Result |
|---|---|
| AP source | IM69 (`[PCMPAIR-EPOCH] ap_source=im69d`, live `[AP] raw_i16_*`) |
| PCM shadow rate | `acq_hz ≈ cons_hz ≈ 48000`, `canon_hz=0` (does not feed AP) |
| Quiet 2 s pair | `fill_ok=1` ovf=0 drop=0 mic_err=0 pcm=96000 mic=25600 hops=267 |
| Dump while armed | `DUMP REFUSED` |
| No WDT/reset | still `CHIP ID: 9087A500` after the runs |

Quiet hop: mean 5600 µs, p99 6367 µs, max 7728 µs.

## Stimulus branches (2 s, 997 Hz stereo −18 dBFS)

| Route | PCM peak | MIC peak | Verdict |
|---|---:|---:|---|
| Quiet | 18948 | 34 | floor |
| External Headphones | 161305 | 27 | electrical PASS; MIC not driven |
| MacBook Pro Speakers (vol 37 then 70) | 17166–21414 | 31–41 | MIC still floor |
| DELL U2518D | 15254 | 26 | MIC still floor |
| Multi-Output Device | 169603 | 29 | electrical only |

Every branch: ovf_epoch=0, ring_drop_epoch=0, mic_err=0, buffers complete.

**Physical-routing gate CLOSED:** with the lamp at the MacBook speakers and the full-scale fixture, Multi-Output drives the same programme into AUX and the acoustic path. The low-level -18 dBFS fixture was below useful microphone SNR for this geometry; the full-scale deterministic fixture is the accepted P4 alignment stimulus.

Volume 56 on headphones is bench hygiene, not a firmware constant.

## Cost (4 s quiet)

| Leg | hop mean | p95 | p99 | max | notes |
|---|---:|---:|---:|---:|---|
| MIC + PCM shadow | 5635 | 6390 | 6507 | 7712 | ovf=0 drop=0 fill_ok |
| MIC only (I2S1 paused) | 5583 | 6297 | 6345 | 8168 | ovf_epoch=16 is the pause, not AP loss |

Shadow − MIC-only: +52 µs mean, +162 µs p99. Not material on K1's 8 ms hop.

## Same-programme alignment receipt

| Epoch | LINE→MIC lag | peak corr | PSR | coarse drift | capture |
|---|---:|---:|---:|---:|---|
| 09 | 7.44 ms | 0.689 | 1.78 | 227 ppm | clean |
| 10 | 5.66 ms | 0.677 | 1.68 | 112 ppm | clean |
| 11 | 7.07 ms | 0.706 | 2.03 | 80 ppm | clean |
| **median** | **7.07 ms** | — | — | **112 ppm** | — |

Fixture: `p4_align_transients_jittered_fullscale.wav`, SHA256 `00cc5d54142441182e98049a4da2d15849bdc8a77331a8f01bdadd30640643fc`; playback lead 1.02 s skips the 1 s guard so the 4 s device window contains active transients. `p4_align.py --selftest` PASS before scoring silicon data.

## P4 close status

**CLOSED.** Both physical capture lanes run simultaneously; IM69 remains the only AP source; PCM shadow is lossless; same-programme electrical/acoustic routing is proven; lag and coarse drift are measured; runtime cost is bounded. No source-manager or product promotion is implied.

## Ship path

1. Already on silicon: `k1_main_rpl_pcm1808_shadow` @ `a08dc10e`; P4 CLOSED.
2. Agent: proceed to P5 Line-vs-IM69 signal/AP comparison and ingress CPU accounting, then P6 conditioner + LEFT/RIGHT/MID ruling.
3. Continue P7 source manager and P8 high-rate feature value; stop for Captain before any OP2/96 kHz action.
4. Then P10 RFAL/tag, P11 coexistence, P12 restore.
5. Product-close stamp remains `IDENTITY OK: git=acaecaa8 env=k1_main_rpl_im69d` on chip `9087A500`. This shadow image is not product.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | ChatGPT/Desktop Commander | P4 CLOSED after Captain moved lamp to MacBook speakers: same-programme Multi-Output, three clean jittered-transient lag/drift epochs. |
| 2026-09-08 | agent:grok | P4 shadow dual-capture silicon result; initial alignment stopped at acoustic routing gate. |
