---
status: active
branch: fix/b489-ws2816-reference-capture
---
# B489 reference repair — Captain mandate, 13 October 2026

Titan must continue autonomous music. Root is the sole live-device owner.

Captain's instructions, retained verbatim:

> Okay so we have an Esp32s3 (original reference firmware + hardware) on usbmodem11301, which we are able to extract the exact ledstrip data at the point of rendering that we should be comparing to what is being output by the Titan for use as a comparison to what the "reference" system is doing

> Captain, identify the current S3 firmware build and make the necessary changes to the firmware to fix the led discrepency + current failure to extract the pixel capture command/output lane

> and take note of the LED protocol assignement on the S3, it should match the Titan's ws2816

> the ws2816 lane uses 2 data lines per channel instead of 1 data line for the regular ws2812 lane

Root asked whether B489 had lower DIN-A/B GPIO15/16, upper DIN-A/B GPIO17/18, microphone DATA8/CLK9, with 80 LEDs per DIN half. Captain corrected:

> Negative, the current microphone gpios are Data 13, CLK 14, the data lines for the leds are acceptable

## Bound starting point and purpose

Live chip B489A500, USB B4:3A:45:A5:89:B4, port /dev/cu.usbmodem11301;
firmware 40103 / source eff9bf47d9ae5a4d8a2101f1d7173b61ec970dc0,
epoch 1789046479, environment k1_bench_im69d_led150, app ELF SHA256
7edb88488c521da72d1d6bbeef3b1bfa24b6cacb134323560ebbfe6d87aaf104.
Readback reported 150 pixels, WS2812 output branch GPIO39/40, primary Hybrid K1,
secondary Waveform Fast / Naberius Gold. rtrace and VPAB commands rejected.
Raw input remained near full scale; that is a separate unresolved input observation,
not evidence of useful music response. Serial DTR false caused a USB reset;
DTR true / RTS false subsequently retained the same boot nonce.

Work on the installed source revision in this existing repository, not newer
96e6839's unrelated firmware changes. Original branch wip/emotiscope-perf and
all historical assignments remain preserved. The pre-existing modified memory
skill is restored byte-for-byte and additionally backed up in the named stash;
Claude outputs are untouched. Recovery/binding evidence:
_scratch/b489-ws2816-reference-20261013/.

## Bounded implementation and proof

1. Preserve the original flash and settings. No erase, calibration, unrelated
   hardware lane or changes to Titan firmware/configuration.
2. Add the target-specific WS2816 profile: two 160-pixel optical edges, four 80-pixel
   DIN outputs 15/16/17/18; keep IM69D DATA13 / CLK14. Reuse proven 48-bit packing;
   do not transmit bare RGB8 or apply byte scaling after packing.
3. Extend existing bounded rtrace to both final packed edge buffers at one
   render instant. Keep pixel count, channel depth, order, sequence, timestamp
   and CRC explicit. No new capture framework or renderer. Keep normal music
   independent of diagnostic start/stop/dump. No synthetic rainbow stimulus.
4. Exercise existing production packing/decoder/identity checks; reject wrong
   device, bad geometry, truncated or corrupt trace. Build exact source and
   install through the existing identity guard and verified-flash route.
5. Read back installed source/env/app ELF/config and capture both edges with
   verified transport integrity. Confirm continued operation after capture.
   Trace identity is not optical or musical acceptance; invalid microphone
   input blocks corresponding musical claims until corrected and verified.

On failed build/identity/recovery prerequisite, stop dependent writes and keep
independent source work. On candidate runtime/output fault, restore the bound
original image through the same guarded route. Preserve failed evidence.
Aesthetic parity requires equivalent effects/settings/input boundaries and the
assembled-plate comparison from the original Titan suite; this repair does not
replace or shorten that assignment.

Relevant doctrine: preserve independent effect/history behaviour and existing
palette identity; isolate output-format changes; do not infer runtime proof from
compilation. Re-test triggers are output packing/topology and diagnostic capture.
The existing PCM1808/ST25 lane below this checkpoint remains historical and is
not resumed by this task.

## Current verification — 13 October 2026

Captain asked whether DATA13 / CLK14 and the dual IM69D130 lane are properly
configured. The live source/env binding and captured boot log confirm PDM RIGHT
mono, not simultaneous two-microphone capture. The source defines DATA13 and
CLK14, PCM 12,800 Hz / 16 bits / DSR16S, with SELECT hardware-strapped. RIGHT is
recorded as physical IM1 / SELECT HIGH. GPIO12 is not driven as SELECT. The
existing stereo environment reads both slots for measurement; it is not the
installed environment. Software configuration does not independently prove the
physical wire termination or microphone power.

Two read-only raw dumps returned 32 copies of -30935 each. This establishes
constant samples in those observed blocks, not a microphone component diagnosis.
The legacy dump token `silence` is only its existing print label: no silence
condition was asserted, no calibration was performed, and no test tone played.
Evidence: `_scratch/b489-ws2816-reference-20261013/raw-input-observation.json`.
The original input must be corrected/verified before claiming a music-valid
reference comparison; LED protocol and pixel transport proof remain separate.

The complete 16 MiB flash backup is preserved at
`_scratch/b489-ws2816-reference-20261013/original-flash-921600.bin`, SHA-256
`25ecc4adb141d35186045af81991195efbefce81f0afe17968f7d0de913a6593`.
The extracted app0 has a valid image checksum/hash and ELF identity matching the
live image above. NVS/filesystem/calibration remain preserved. Readback reset the
S3 after backup; Titan was not touched. The first slow incomplete backup is
retained as incomplete evidence, not a recovery image.

The existing WS2816 path bypasses FastLED's RGB8 power estimator. The repair must
retain that legacy shared estimate using final logical RGB16 values before
packing, including both physical edges. It must not scale packed carrier bytes.
This preserves the existing code-space policy at MAX_CURRENT_MA=1913; it does
not establish a calibrated WS2816 current measurement.

Source checks before installation: the exact B489 profile builds successfully
(127,680 bytes RAM, 730,414 bytes application flash). The first build failed
on the new readback using LED_COUNT outside its scope; that readback now uses
CONFIG.LED_COUNT and the corrected build passed. Both build logs are retained.
Target guard accepts B489 and rejects the other S3. Production trace/decoder
tests reject corruption/truncation and preserve the legacy allocation/format.
The unchanged pinned FastLED 3.10.3 oracle agrees with the new native limiter;
all 16 look slots preserve existing pack output at identity scale. These are
software checks, not physical microphone, optical or measured-current proof.

The first normal commit was refused by the required host gate; no flash followed
that failed gate. Three existing host oracle compiler selectors stopped at GCC
15 and fell back to Apple Clang on this GCC 16 machine. Clang rejected the
unchanged FixedPoints in-class constexpr members. Add GCC 16 to those existing
candidate lists (GDFT, render and serial replay); do not alter DSP, goldens or the
library. Two static checks also require the new explicit diagnostic environment
and the shared Main-RPL/B489 controller guard, retaining their original
assertions. Focused AGC/trace/RPL checks then passed. The original failure log and
corrected checks are retained under the recovery evidence directory.

## Recovered custom-board context — Captain correction, 13 October 2026

Captain explicitly corrected the process and hardware identity:

> What the fucking hell is causing this fucking needless churn on the audio pipeline of the S3? Fucking deploy $claude-mem-router and extract the necessary fucking context needed instead of repeating this unnecessary self-discovery

> FUCK YOU ASSHOLE. The microphone breakout/board is our custom built dual-im69d130 design

Read-only claude-mem retrieval (observations 89377, 89645, 90659, 92150,
92704 and 92718) led back to the actual custom-board records. Current on-disk
supersession, not older observation prose, governs:

- `docs/hardware/im69d130-board-wiring-from-eda-2026-08-05.md`: custom PCB3,
  J1.3 clock to GPIO14, J1.5 data to GPIO13, shared PDM data through the board's
  translators, IM1 SELECT HIGH via R7 and IM2 SELECT LOW via R14. No host SELECT.
- `docs/forensics/G1_AP_INPUT_SLOT_RATIFICATION_2026-08-15.md`: ratified IM1 /
  board-left / SELECT HIGH -> ESP-IDF RIGHT -> stereo index 0; programme source
  is IM1. Both capsules were demonstrated alive. Mono RIGHT is deliberate and
  is NOT itself a configuration defect or a missing stereo feature.
- `docs/forensics/P0_0_AP_INPUT_QUARANTINE_MANIFEST_2026-08-15.md`: earlier
  default-slot B489 absolute-level/calibration claims require their replacement
  evidence. Do not lift old thresholds or an old request for microphone handling
  out of that history. Preserve current calibration; no new calibration occurred.

The 18 February AtomS3 observation of -30935 belongs to different hardware and
an ADAU7002 investigation. It cannot establish today's cause on custom PCB3.
Today's constant raw blocks remain a narrow observation, not a dead-microphone
verdict. The installed and candidate configurations already use ratified RIGHT.
This repair does not change acquisition settings, slots, gain, DSP, calibration
or silence policy. The added read-status fields are observation only.

The remaining host-gate failures were two more outdated GCC discovery sites
(render replay and serial ODR smoke) and a static brace scanner encountering
mutually exclusive opening braces. The native output guards now use one common
brace with the same compiled conditions. Focused affected checks passed; no
assertion or golden expectation was removed or relaxed.
