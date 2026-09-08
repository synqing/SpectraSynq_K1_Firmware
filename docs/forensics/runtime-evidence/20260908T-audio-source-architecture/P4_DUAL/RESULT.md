---
abstract: "P4 dual-capture on Main RPL a08dc10e / k1_main_rpl_pcm1808_shadow. IM69 remains the AP source. PCM shadow runs at 48 kHz with ovf=0 and ring-drop=0 during the epoch. Dump is refused while armed and only serialised after freeze. Electrical AUX path proven. Acoustic/room path did not couple on this bench — alignment stopped at that physical-routing gate. Shadow AP cost is ~0.16 ms p99 versus MIC-only."
---

# P4 dual capture — 2026-09-08

Silicon: Main RPL chip `9087A500`, USB `B4:3A:45:A5:87:90`, `/dev/cu.usbmodem1101`.
`IDENTITY OK: git=a08dc10e env=k1_main_rpl_pcm1808_shadow epoch=1788847940`.
Flashed with `k1-flash-verified.sh`. Product restore remains `k1_main_rpl_im69d` @ `acaecaa8`.

## What is true now

The microphone still owns the analysis pipeline. Line-In runs beside it as a shadow recorder: 48 kHz in, 48 kHz consumed, no overflows, no ring drops while we are measuring. The huge hex dump happens only after that window is frozen. Asking for a dump while the window is still filling is refused.

Mac → AUX → PCM1808 is real (peak ~161 k vs quiet ~19 k on slot 0, physical RIGHT). The IM69 did not hear MacBook speakers, the DELL monitor, or the Multi-Output device above its quiet floor (peak 26–41 vs quiet 34). Same-source alignment was therefore not run. That is a bench routing/placement stop, not a firmware failure.

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

**Physical-routing gate:** this Mac cannot currently put the same programme into both the AUX jack and a speaker the IM69 can hear. Alignment/drift is not scored from a fake pair.

Volume 56 on headphones is bench hygiene, not a firmware constant.

## Cost (4 s quiet)

| Leg | hop mean | p95 | p99 | max | notes |
|---|---:|---:|---:|---:|---|
| MIC + PCM shadow | 5635 | 6390 | 6507 | 7712 | ovf=0 drop=0 fill_ok |
| MIC only (I2S1 paused) | 5583 | 6297 | 6345 | 8168 | ovf_epoch=16 is the pause, not AP loss |

Shadow − MIC-only: +52 µs mean, +162 µs p99. Not material on K1's 8 ms hop.

## P4 close status

Not closed. Instrument, electrical branch, epoch cleanliness, dump-after-freeze, and CPU cost are on silicon. Alignment/drift wait on a speaker (or splitter) that the IM69 actually hears.

## Ship path

1. Already on silicon: `k1_main_rpl_pcm1808_shadow` @ `a08dc10e`.
2. Captain: put a speaker the IM69 can hear on the same programme as the AUX cable (or confirm a Multi-Output that includes that speaker).
3. Agent: rerun the jittered transient pair, then lag + drift.
4. Then P5 Line vs IM69 comparison. Conditioner and LEFT/RIGHT/MID stay unfrozen until P6.
5. Product restore is still `k1_main_rpl_im69d` @ `acaecaa8` (P12). This probe is not that.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | agent:grok | P4 shadow dual-capture silicon result; alignment stopped at acoustic routing gate. |
