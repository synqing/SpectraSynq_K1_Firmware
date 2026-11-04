---
abstract: "Factual debrief of the S3 (B489A500) continuation, 2026-10-14 Perth date (UTC 2026-10-13). Inherited be0a97e3 was already committed and unflashed. This continuation implemented and committed the pinned saved-app restore plus the upload-boundary segment guard (f3ee66e8). An unreviewed host test escaped to the live S3 and its recovery is recorded. Then: controlled restore, guarded deployment of the capture image, device app readback, and a dual-edge final-render capture. No microphone initialisation or DSP fix was made; the mic still reads a constant -30935."
author: agent:claude-opus-5-5 (S3 continuation executor)
date: 2026-10-14
branch: fix/b489-ws2816-reference-capture
device: B489A500 / USB B4:3A:45:A5:89:B4
---

# Debrief — B489 WS2816 reference continuation (2026-10-14)

## 0. Plain summary

At the start of this continuation, the WS2816 output and capture repair (`be0a97e3`) was already committed and had not been flashed. It was inherited, not written here. This continuation:

1. Built and committed a pinned, guarded way to put B489's original app image back (`f3ee66e8`).
2. Allowed one unreviewed host test to reach the live S3, then recorded and recovered from that.
3. Ran a controlled restore.
4. Deployed the committed capture image under guard.
5. Proved the installed bytes by reading them back from the device.
6. Captured both final WS2816 edges with valid checksums while rendering continued.

The microphone was not fixed. Every fresh read still returns −30935 on every sample. Its cause is unresolved.

Dates: the continuation ran on 2026-10-14 Perth time (+08:00). Evidence filenames and log stamps are **UTC**, so they read `2026-10-13T18…Z`–`20…Z`. Times below are UTC unless marked. Only commands and exits that appear in a retained log or transcript are quoted exactly. Command order where nothing was logged is not claimed.

## 1. Source, ownership, hardware, installed state, dirty files, model

- **Repository:** `/Users/spectrasynq/SpectraSynq_K1_Firmware`, branch `fix/b489-ws2816-reference-capture`. Start HEAD `be0a97e31ff51f65bdc5b6b0081585acdf88c32b`. End HEAD `68a95773d41485fa14cb6dd71d89393d3aa25c73`. Nothing was pushed.
- **Hardware in scope:** the S3 bench unit only. App `:dump` CHIP ID `B489A500`, USB serial and ROM MAC `B4:3A:45:A5:89:B4`. Port names seen: `/dev/cu.usbmodem11301`, then `/dev/cu.usbmodem11401` (s05/s06). The port name is advisory; identity is the USB serial.
- **Not touched by this S3 executor:** Titan, E2 Lite, their broker, camera, player and processes were never read or operated by this executor. This is not a claim that the wider continuation did no Titan work: the parent team completed the Titan BOOM capture before Titan and E2 Lite were transferred to the other team. The parent reports that Titan work in its own answer.
- **Dirty files preserved untouched throughout:** `/Users/spectrasynq/SpectraSynq_K1_Firmware/.claude/skills/claude-mem-router/SKILL.md` (modified), `/Users/spectrasynq/SpectraSynq_K1_Firmware/Claude outputs/` and `/Users/spectrasynq/SpectraSynq_K1_Firmware/tools/k1live/` (untracked). None of them was staged in any commit.
- **Installed state at start** (from the inherited records and the pre-restore read `s01-prerestore`): `eff9bf47` / `k1_bench_im69d_led150` / epoch `1789046479`.
- **Installed state at end:** `f3ee66e8` / `k1_b489_ws2816_reference_capture` / epoch `1791917615`, rendering. The last read was s06 at 20:46Z.
- **Model and escalation:** this executor reports provider model `claude-opus-5-5` (Opus 5.5). By the parent's opening brief, the Captain required Grok 4.7 high first and Opus 5.5 high after more than two failed executions. The native Grok author "repeatedly failed to deliver" the bounded recovery implementation, and every targeted source diff was empty at handoff. That is the brief's account; this executor did not see those Grok runs. No subagents were spawned, and the model was not switched.
- **Runner and cancellation labels:** stops of processes during this continuation were parent-orchestrator actions (see §5), not Captain actions.

## 2. Inherited firmware patch `be0a97e31ff51f65bdc5b6b0081585acdf88c32b` (not implemented here)

Commit message: "fix: restore B489 WS2816 output and dual-edge capture". It was already committed, and unflashed, when this continuation started. Mechanisms, from that commit's diff, which was inspected and not rewritten:

- **Four DINs and the 2×160 / 80-per-DIN split:** `constants.h`. The B489 env takes the `K1_MAIN_RPL_PINMAP_V1 || K1_B489_WS2816_V1` branch: `LED_DATA_PIN 15`, `LED_CLOCK_PIN 16` (primary DIN-A/DIN-B), `SECONDARY_LED_DATA_PIN 17`, `SECONDARY_LED_CLOCK_PIN 18`. The PDM pins are overridden to CLK 14 / DATA 13, with an `#error` that keeps DSR16S and mono RIGHT. `led_utilities.h` (+143) keeps both DIN halves in WS2816 format for every reverse setting, 80 pixels per DIN, 160 per optical edge. `globals.h`, `globals_config.cpp`, `config_types.h` and `system.h` carry the B489 profile and `LED_COUNT 160`.
- **WS2816 16-bit final capture:** `k1_render_trace.cpp/.h`. The bounded rtrace stores **both** final packed edge buffers in one record (2000 frames × 1920 B), stride 6 per pixel. The wire order `G_hi G_lo R_hi R_lo B_hi B_lo` is dumped as R16 G16 B16 with a header CRC. The decoder `score_rtrace_occupancy.py` gains the 2-edge format.
- **Legacy power compatibility:** `visual/k1_b489_legacy_power.h` (+77). It preserves the pinned FastLED 3.10.3 estimator decision on the logical post-look frames of both edges, applied while packing, never by scaling the packed carriers. Its own header labels it "a compatibility envelope, NOT measured WS2816 milliamps".
- **Raw observation-only telemetry:** `audio/i2s_audio.h` (+12) records `b489_i2s_read_sequence`, last status, bytes, expected bytes and raw min/max. `serial/serial_menu.cpp` (+17) prints `LED_PROFILE`, `MIC_PROFILE` and `MIC_LAST_READ` in `:dump`. Observation only; there is no acquisition change.
- **Env:** `platformio.ini` `[env:k1_b489_ws2816_reference_capture]`, which extends `k1_bench_im69d` and adds `-DK1_B489_WS2816_V1 -DK1_WS2816_LEVER2_V1 -DK1_LOOK_LIB_V1 -DK1_COLOUR_LAB_V1 -DK1_RMT_ALLOC_ON_VP_CORE_V1=1 -DK1_RENDER_TRACE_V1`. The mic flags are inherited from the base env: `[env:k1_bench_im69d]` starts at **platformio.ini line 529**, with `-DK1_MIC_IM69D_SLOT_RIGHT` at **line 550**, at f3ee66e8 (corrected by the independent reviewer; see §11).

All 32 inherited changed files (absolute paths):

```
/Users/spectrasynq/SpectraSynq_K1_Firmware/.claude/handoff.md
/Users/spectrasynq/SpectraSynq_K1_Firmware/AGENT_OS.md
/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h
/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp
/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/system/config_types.h
/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/system/constants.h
/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/system/globals.h
/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp
/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/system/system.h
/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/visual/k1_b489_legacy_power.h
/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/visual/k1_render_trace.cpp
/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/visual/k1_render_trace.h
/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h
/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/handover/HANDOVER_2026-10-13_B489_WS2816_REFERENCE.md
/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/spec-index.md
/Users/spectrasynq/SpectraSynq_K1_Firmware/platformio.ini
/Users/spectrasynq/SpectraSynq_K1_Firmware/progress.md
/Users/spectrasynq/SpectraSynq_K1_Firmware/scripts/agent/pio-build.sh
/Users/spectrasynq/SpectraSynq_K1_Firmware/scripts/platformio/k1_device_identities.json
/Users/spectrasynq/SpectraSynq_K1_Firmware/scripts/regression-harness/golden/oracle_gdft.py
/Users/spectrasynq/SpectraSynq_K1_Firmware/scripts/regression-harness/golden/oracle_render.py
/Users/spectrasynq/SpectraSynq_K1_Firmware/scripts/regression-harness/golden/oracle_serial_replay.py
/Users/spectrasynq/SpectraSynq_K1_Firmware/scripts/regression-harness/render_replay.py
/Users/spectrasynq/SpectraSynq_K1_Firmware/scripts/regression-harness/score_rtrace_occupancy.py
/Users/spectrasynq/SpectraSynq_K1_Firmware/tests/test_b489_legacy_power_host.cpp
/Users/spectrasynq/SpectraSynq_K1_Firmware/tests/test_b489_legacy_power_host.py
/Users/spectrasynq/SpectraSynq_K1_Firmware/tests/test_k1_upload_guard.py
/Users/spectrasynq/SpectraSynq_K1_Firmware/tests/test_main_rpl_env_static.py
/Users/spectrasynq/SpectraSynq_K1_Firmware/tests/test_render_trace_static.py
/Users/spectrasynq/SpectraSynq_K1_Firmware/tests/test_rtrace_capture_host.py
/Users/spectrasynq/SpectraSynq_K1_Firmware/tests/test_rtrace_occupancy_host.py
/Users/spectrasynq/SpectraSynq_K1_Firmware/tests/test_serial_menu_odr_static.py
```

## 3. Implemented here: `f3ee66e88ee91c4805b1ebd12f393c934bae9c3b` (helper, guard, tests)

Commit: "feat(upload): pinned B489 saved-app restore and upload-boundary segment check". The four files, with their approved and committed SHA-256:

```
/Users/spectrasynq/SpectraSynq_K1_Firmware/scripts/platformio/k1_upload_guard.py       57f292c20932e11499ea63cbdeeb7992bb24901dbc25fc4453566b4e982f6ca9
/Users/spectrasynq/SpectraSynq_K1_Firmware/scripts/agent/k1-flash-verified.sh          d899949a8049682b47f69d8f4476cd27071338c49dfb187486869e7c8228c0e4
/Users/spectrasynq/SpectraSynq_K1_Firmware/tests/test_k1_saved_app_restore.py          6066a98b7087e94d38121afac22ea6f2f68636ffc6df9152d56b87f2fd83a6eb
/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/handover/HANDOVER_2026-10-13_B489_WS2816_REFERENCE.md  (additive sections)
```

**Pinned profile** `SAVED_APP_PROFILES["b489-original-app0-20261013"]` in `k1_upload_guard.py`:

| Field | Value |
|---|---|
| Image | `_scratch/b489-ws2816-reference-20261013/original-app-app0.bin` |
| SHA-256 | `3d3b929e71b0d1ddc471f64f263a30c85aa38fc5a6c261dcef6087f376f9c226` |
| Size | 6553600 |
| Descriptor ELF | `7edb88488c521da72d1d6bbeef3b1bfa24b6cacb134323560ebbfe6d87aaf104` |
| Slot / offset | 0 / `0x10000` |
| Expected app | `eff9bf47` / `k1_bench_im69d_led150` |
| Expected chip / USB | `B489A500` / `B4:3A:45:A5:89:B4` |
| Guard env | `k1_b489_ws2816_reference_capture` |
| otadata | `0xE000`, 8192 B, `f94c5d78…` |
| Partition table | `0x8000`, 3072 B, `bd0f7954…` |
| Bootloader | 20208 B, `12c9a10f…` |

**Restore flow** (`run_saved_app_restore`):

1. Every declared value must equal the pin, and fixtures cannot authorise a real write.
2. Image SHA, size, magic `0xE9` and descriptor ELF are checked.
3. The port is located by USB serial, then `validate_upload_target`, then `check_port_free` (lsof exit 1 with empty output means free; an owner, stderr or a missing lsof refuses).
4. `:build` is read as preflight evidence only, never as admission.
5. `await_device` (at most 20 polls of 0.5 s) runs before **every** esptool session. It accepts port drift with the same serial; it refuses a duplicate serial, a swapped serial or an owner.
6. ROM `read_mac`. The chip id is derived from the MAC and labelled as not an independent register read.
7. Live otadata and partition reads, then `plan_saved_app_restore`, which reproduces the bootloader slot choice through `esp_rom_crc32_le(UINT32_MAX, seq)`.
8. The image is staged privately and re-hashed, the source is re-hashed, and ROM identity is read again.
9. One `write_flash --flash_mode keep --flash_freq keep --flash_size keep 0x10000 <staged>`.
10. Full readback of hash and ELF, plus an otadata-unchanged check, then `:build` identity.

Every esptool session ends with `--after hard_reset`; `_esptool` refuses any other value and refuses `--erase-all`, `-e`, `erase_region`, `erase_flash` and `--encrypt`. Exit codes: 0 verified · 1 write attempted, not verified (`write_attempted` is set immediately before the writer) · 2 refused, writer never invoked · 3 readback or app mismatch · 4 bytes verified, app silent. `--plan-only` needs all three fixtures and runs no device tool.

**Forward upload boundary:** `_guard_upload_action`, the existing PlatformIO upload pre-action, runs for `k1_b489_ws2816_reference_capture` only. After the identity check it reads `FLASH_EXTRA_IMAGES` (the exact pairs `espressif32/builder/main.py:1932-1933` appends to `write-flash`). It requires that 0x0, 0x8000 and 0xe000 equal the bootloader, partition and otadata pins and that nothing else is sent, and it prints each selected file. Other envs keep their earlier behaviour. The helper `k1-flash-verified.sh` gained an early `--restore-saved-app` branch that `exec`s the guard and never calls `pio run`.

## 4. Host test escape to the live S3, recovery, confinement, reviews

**Escape: evidence versus inference.**
- An early, unconfined version of the test file ran a 9-mutant sweep over the shared guard file (`/tmp/k1_guard_orig.py` backup). The sweep began at 18:18:56Z.
- Mutant `fixture-real-allowed` removed the fixture refusal, so `test_helper_refuses_fixtures_for_a_real_write` ran the real restore path. Its fake port `/dev/cu.usbmodem99999` was not enumerated, and the code picked the real B489 by serial.
- That pytest ran 121.64 s and was killed by its own 120 s subprocess timeout. **All esptool stdout, and the write's return code, were lost.** The shared guard file was restored byte-identical afterwards (`cmp`).
- Facts: the escaped temp dir `$TMPDIR/k1-restore-se_7n9zx` holds `otadata.bin` (written 18:19:02, `f94c5d78…`), `partition.bin` (18:19:03, `bd0f7954…`) and staged `app0.bin` (18:19:03, `3d3b929e…`), with no `readback.bin`. The kernel USB log has seven port-close times: 18:19:00.471, 01.960, 02.557, 03.103, 04.467, 46.677 and 18:20:58.863.
- Inference only, from code order and file times: those sessions were `:build`, `read_mac`, the otadata read, the partition read, `read_mac`, one about-42-second `write_flash` of the pinned image at `0x10000`, and a readback killed mid-read. That `write_flash` completed is **inferred, not observed**. That code used `--after no_reset`, so no reset ran.
- **Observed afterwards:** `:build` silent ("never answered ':build' within 4.0s").
  - 18:23:09Z: a read-only `read_flash 0x10000 6553600 --after hard_reset` returned esptool rc 0 with readback SHA `3d3b929e…`, equal to the pin.
  - 18:24:41Z: `IDENTITY OK: git=eff9bf47 env=k1_bench_im69d_led150 epoch=1789046479`.
  - Not re-read after the escape: otadata, NVS, the partition table, the bootloader.
- Evidence: `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/b489-ws2816-reference-20261013/resume-20261014/incident-20261014-test-escape/`, containing `kernel-usb-portclose-021850-022500.log`, `escaped-tempdir-listing.txt`, copies of `otadata.bin` and `partition.bin`, and `mutation-run-output.txt`. Also in `resume-20261014/`: `incident-readonly-check.log` and `incident-readonly-check.esptool.log`.

**Confinement repair:** the tests now trap at the OS and subprocess boundary.
- In-process: `subprocess.Popen` is allow-listed, `open` / `os.open` of `/dev/cu.*` and `/dev/tty.*` are blocked, and pyserial is stubbed.
- In child processes: a `sitecustomize` on PYTHONPATH blocks every `Popen` and `/dev` open, with fake `serial`, PATH shims and an empty HOME.
- Every hit is recorded and asserted empty. `ConfinementTest` deletes the admission checks at test level and proves the traps still stop the identity guard, `read_mac` and `write_flash`, in-process and in a child.
- All test port names are fake (`/dev/cu.usbmodemK1TESTFAKE*`).

**Reviews and checks.**
- Independent code review in `/tmp/prism-b489-code-review-20261014.md.result`:
  - r1: guard `e06ee897`, helper `be5cd859`, verdict NOT READY, with B1 (failures after the write reported as "chip not written") and B2 (port re-enumeration).
  - r2: the source is APPROVED: guard `57f292c2…`, helper `d899949a…`.
  - r3: the test condition is CLEARED for tests `6066a98b…`.
- Fixes made between them: `write_attempted`, `await_device`, logging of requested-port drift and of the derived chip id, the upload-boundary segment check, a fixed forbidden-argument test, and confined post-write-failure tests.
- Focused run `confined-tests-r3.log`: **77 passed** (44 in `test_k1_saved_app_restore.py`).
- One planted mutant, on an isolated **copy** (`/tmp/k1-restore-mutant-copy.7sRD6K`) under the child sandbox, deleting the fixture refusal (`planted-mutant-run.log`, then `-r2.log`). The expected test went **RED**. After the in-process tripwire was made to record its hits, two tests went RED. The canary stayed green, and no real subprocess or serial access happened.
- Frozen hashes: `frozen-source-r2.sha256`. Patch: `review-diff-r2.patch`.

## 5. Commit gate (f3ee66e8)

- **The original gate was authoritative.** Per the parent's process record: git PID 46580, hook 46581, pytest 46616. Its log is `deploy-20261014/commit-gate.log`: `1801 passed, 15 skipped in 287.02s`, `k1_hardware SUCCESS 00:00:20.745`, `COMMIT_EXIT=0`. It landed `f3ee66e8`.
- `k1_hardware` is the gate's compile check, **not** the B489 capture build or install.
- **Process error by this executor:** a filtered process listing wrongly showed no gate running, and a duplicate gate was started (`commit-gate-r2.log`, PID 68297 / pytest 68334). The **parent orchestrator stopped only that duplicate**. It was not the Captain, and it was not a test failure. Its `COMMIT_EXIT=1` is that cancellation, and it landed nothing.
- Later docs commits through the docs tier, each with exit 0: `ffdc7e218c3f74e69733b3548c763e67e1e844e5`, `3714c206a348de0c4da06f733bcee0a16166d8e5` and `68a95773d41485fa14cb6dd71d89393d3aa25c73`.

## 6. Controlled saved-app restore (18:52Z)

Exact invocation (the contract command, logged in `deploy-20261014/restore.{stdout,stderr,exit}`): `bash scripts/agent/k1-flash-verified.sh --restore-saved-app --port /dev/cu.usbmodem11301 --image _scratch/b489-ws2816-reference-20261013/original-app-app0.bin --sha256 3d3b929e71b0d1ddc471f64f263a30c85aa38fc5a6c261dcef6087f376f9c226 --size 6553600 --slot 0 --offset 0x10000 --expect-git eff9bf47 --expect-env k1_bench_im69d_led150 --expect-chip B489A500 --expect-usb-serial B4:3A:45:A5:89:B4`.

**`RESTORE_EXIT=0`** at 2026-10-13T18:52:38Z, with stderr empty. The log shows:
- the USB guard verified B489;
- app before: `eff9bf47`;
- ROM MAC matched, with the chip id derived from it;
- the plan: one write at `0x10000`;
- after the write: readback SHA `3d3b929e…` and ELF `7edb8848…`, otadata unchanged, and `RESTORED AND VERIFIED: git=eff9bf47 env=k1_bench_im69d_led150 chip B489A500`.

Pre- versus post-restore `:dump` (`s01-prerestore`, `s02-postrestore`): **33 CONFIG/BUILD/CHIP lines identical**.

**Scope:** app0 only. Bootloader, NVS, SPIFFS, coredump and app1 bytes were not read. This is **not** a full-flash restoration claim.

## 7. Capture build, guarded deployment, installed identity (18:50–18:59Z)

- **Initial capture build of inherited `be0a97e3`: built, NOT installed.** This was recorded in this continuation lane before this executor started.
  - Records: `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/b489-ws2816-reference-20261013/resume-20261014/build-committed.log` and `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/b489-ws2816-reference-20261013/resume-20261014/build-identity.json`, recorded 2026-10-13T17:26:41Z.
  - Env `k1_b489_ws2816_reference_capture` at HEAD `be0a97e31ff51f65bdc5b6b0081585acdf88c32b`, clean firmware tree, `SUCCESS 20.20s`, RAM 127680 B, app flash 730414 B.
  - `firmware.bin` 730816 B, SHA `c2ab0880253be2e598c4519d3638c71c9c6936d2a0f68a910f689a2359a4b27b`; `firmware.elf` `bd0dd0cdb62b1f3710b651d883c3813ec4095da28559a89131513a58af7cadc3`; provenance epoch `1791912339`. Its `installed` field reads "NOT UPLOADED".
- **Why flashing waited.** A hashed full backup already existed (`original-flash-921600.bin`, `25ecc4ad…`, and `original-app-app0.bin`, `3d3b929e…`). But no supported exact procedure existed to restore that saved app image if the candidate failed. The checkpoint held the flash until one did.
  - An uploader attempt at 17:42:35Z (`/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/b489-ws2816-reference-20261013/resume-20261014/flash-verified-raw.txt`) was stopped by the parent during its build stage: no "Flashing" stage, recorded `FLASH_EXIT:143`. Its `WRAPPER_EXIT:0` was a wrapper false positive. Nothing was written.
  - A later rebuild changed the local binary's metadata. That initial `c2ab0880…` image was never installed.
- **Final image, built AND installed:** the post-commit `f3ee66e8` build and deploy below. Only the `f3ee66e8` artefact (`5fbf34ef…`) is the installed identity.

- **Host prebuild** (`prebuild-capture.log`): `k1_b489_ws2816_reference_capture SUCCESS`.
- **Forward deploy:** `bash scripts/agent/k1-flash-verified.sh k1_b489_ws2816_reference_capture --port /dev/cu.usbmodem11301` (`forward.{stdout,stderr,exit}`) gave **`FORWARD_EXIT=0`** at 18:54:16Z from HEAD `f3ee66e8`.
  - BEFORE-FLASH identity: `eff9bf47`.
  - The pre-action printed `0x0 bootloader: .pio/build/k1_b489_ws2816_reference_capture/bootloader.bin sha256 12c9a10f… = pin`, the matching 0x8000 `partitions.bin` line (`bd0f7954…`) and 0xe000 `…/framework-arduinoespressif32@src-6738aaddd9fb901216d5f60e093380b6/tools/partitions/boot_app0.bin` (`f94c5d78…`).
  - esptool reported "Hash of data verified" for all four segments; the app was 730816 B.
  - After the flash: `IDENTITY OK: git=f3ee66e8 env=k1_b489_ws2816_reference_capture epoch=1791917615`.
- **Installed artefact** (`installed-artifacts.txt`): `firmware.bin` `5fbf34efaed1fe3db20485ee63560a369d6e460e92fca283df0bb7f55f97369b` (730816 B), with descriptor ELF `b3c12ee16bbc1234bb151dc484b645fb7c4d7a5a196f4c6439f470f02cf771a8`, equal to the `firmware.elf` SHA. The earlier `c2ab0880…` and `539ff8e0…` builds are not the installed identity.
- **Device readback** (read-only, 18:59:43Z, `installed_app_readback.py`, which uses only the existing guard functions): **730816 B read at `0x10000`**, SHA `5fbf34ef…`, magic `0xE9`, ELF `b3c12ee1…`, **byte-identical to the local artefact**. `READBACK_EXIT=0`; the session ended in a hard reset. Afterwards `:build` read the same build, env and epoch, the config was unchanged, and rendering continued (`s04-post-readback`).

## 8. Paired dual-edge final-render capture (s03)

`:rtrace_arm=2,25`, `:rtrace_status=1`, `:rtrace_dump=1` (`s03-capture.{raw,txt,steps.jsonl}`):
- Header: `[RTRACE-BEGIN frames=11 every=25 px=160 fmt=rgb16hex bpp=16 edges=2 crc32=0f564f2e]` … `[RTRACE-END]`.
- The committed decoder (`s03-rtrace-receipt.json`) reports `crc_verified true`, **22 edge planes**, **3520 px**, dropped 0, verdict `PASS_TRUE16`.
- Raw-byte check (`s03-structure-check.txt`): 11 records with frame indices 0–10, monotonic ms 167–170 apart, each record holding both edges from one instant at exactly 160 px × 12 hex. The checker first reported False, because its charset was uppercase-only while the firmware emits lowercase hex. That was corrected in the file.
- Packed wire order is GRB (`G_hi G_lo R_hi R_lo B_hi B_lo`), dumped as R16 G16 B16.
- Rendering continued: SYSTEM_FPS about 134–139, LED_FPS about 147–149, before, during and after.
- This is **transport and submitted-data proof only**, not optical, artistic or musical evidence. Content was sparse (mode 32; edge-0 198 non-zero px, edge-1 22; `unique_g=1`).

## 9. Microphone: fresh raw data, recovered init, comparison

- **Fresh raw is constant at −30935** (int16 `0x8729`) on every read:
  - s03 (session start 18:54:44Z, from steps-file epoch 1791917684.56): sequence 5454 → 8751 → 9156 → 9560.
  - s04 (18:59Z): sequence 1762.
  - **s05** `s05-live-audio-recheck-20261013T203433Z` on `/dev/cu.usbmodem11401`: sequence 11460 / 11729 / 12001, at epoch 1791923675.91 / 677.93 / 679.97.
  - **s06** `s06-live-audio-recheck-20261013T204623Z` on `/dev/cu.usbmodem11401`: sequence 106078 / 106348 / 106618, at epoch 1791924387.60 / 389.63 / 391.66.
  - All reads: status 0, 192 of 192 bytes, raw_min = raw_max = −30935. The AP lines show `raw_i16_abs_peak=30935 raw_i16_rms=30935.0 raw_i16_near_pct=1.000`.
  - The same constant was already present on `eff9bf47` before any flash (`_scratch/b489-ws2816-reference-20261013/raw-input-observation.json`), so it is not a regression of the candidate.
- **The recovered working init** is **`fa164732`** (2026-08-12), env `k1_bench_im69d_micb`, proven on this B489 (`docs/forensics/im69d-stage1b-stage2-2026-08-12/stage1b-receipt.md`, with the 2026-08-15 G1 correction). The G1 doc commit `39f75731` is documentary. The sequence, in `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h` `init_i2s`:
  1. `i2s_new_channel` (RX master).
  2. `I2S_PDM_RX_CLK_DEFAULT_CONFIG(12800)` and `I2S_PDM_RX_SLOT_DEFAULT_CONFIG(16BIT, MONO)`, with `clk=14`, `din=13` (PCB3 bench branch of `system/constants.h`) and `clk_inv=0`.
  3. `dn_sample_mode=I2S_PDM_DSR_16S`.
  4. `slot_mask=I2S_PDM_SLOT_RIGHT`.
  5. `i2s_channel_init_pdm_rx_mode`.
  6. `i2s_channel_enable`.
- **Comparison:** installed `f3ee66e8` compiles the same calls and values; this is unchanged, inspected code. No missing or different init step was found in source. This is **not** an exoneration of the whole pipeline: equal init functions cannot rule out other startup or runtime activity or driver state. The cause is unresolved.

## 10. Boot banner attempt, rejected proposal, withdrawn inference

- **Boot banner:** no existing capture held `INIT I2S (channel)`, `I2S PDM RX INIT` or `I2S ENABLE`. The existing procedure (`scripts/regression-harness/k1_audio_visual_regression.py::capture_boot_guard`) reboots with `:reset`, and `k1_serial_safety.assert_safe_to_send(':reset')` refused it: `'reset' is NOT read-only: carries CMD_DISRUPTIVE`. **No device command was sent.** Because the shell chained the steps with `&&`, **the USB enumeration in that attempt did not run** after the refusal; only `lsof` on the hard-coded 11301 nodes ran, with rc 1 and no output. The checkpoint line that said identity was "enumerated" in that step is wrong and is corrected here. This shows only that this one existing route was refused. It is not proof that every reset route is forbidden.
- **Stereo-diagnostic reflash proposal: REJECTED** by the parent under current scope (no stereo bring-up or blind slots; it would also move the LEDs to 4/5). It was not run.
- **"Static GPIO13 data" inference: withdrawn** as a finding. It is a hypothesis only, not a pin, translator or hardware diagnosis.

## 11. Independent review corrections applied

From `/tmp/prism-b489-init-independent-review-20261014.result.md` (r1), corrections the reviewer made in its own review: −30935 as int16 is **`0x8729`**, not `0x8749`, and the `platformio.ini` citation is **line 529** (`[env:k1_bench_im69d]` start) and **550** (`SLOT_RIGHT`), not 303 (which is in `[env:k1_main_rpl_im69d]`). This debrief uses the corrected values.

## 12. Paths: code, tests, helpers, evidence, documents

**Implemented here (new or changed):** the four `f3ee66e8` files in §3, plus the evidence-only helpers (not repo code) `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/b489-ws2816-reference-20261013/resume-20261014/deploy-20261014/s3_session.py` and `…/deploy-20261014/installed_app_readback.py`.

**Inspected and unchanged in this continuation:**
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h`
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/system/constants.h`
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/visual/k1_render_trace.cpp`
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp`
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/audio/audio_transfer.h` (not included anywhere)
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/platformio.ini`
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/scripts/regression-harness/k1_device_identity_guard.py`
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/scripts/regression-harness/k1_serial_safety.py`
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/scripts/regression-harness/score_rtrace_occupancy.py`
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/scripts/platformio/k1_device_identities.json`

**Existing tests run in the gate set:** `tests/test_k1_upload_guard.py`, `tests/test_k1_upload_guard_identity_static.py`, `tests/test_k1_device_identity_guard.py`.

**Evidence** (full absolute directories):
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/b489-ws2816-reference-20261013/`: `original-flash-921600.bin` (16 MiB, `25ecc4ad…`), `original-app-app0.bin`, `raw-input-observation.json`.
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/b489-ws2816-reference-20261013/resume-20261014/`: `CHECKPOINT.md`, `recovery-contract.md`, `build-committed.log`, `build-identity.json`, `flash-verified-raw.txt`, `incident-readonly-check.log`, `incident-readonly-check.esptool.log`.
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/b489-ws2816-reference-20261013/resume-20261014/incident-20261014-test-escape/`: incident logs, `confined-tests-r1/r2/r3.log`, `planted-mutant-run*.log`, `review-diff*.patch`, `frozen-source-r2.sha256`.
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/b489-ws2816-reference-20261013/resume-20261014/deploy-20261014/`:
  - gate logs: `commit-gate*.log`, `docs-commit*.log`;
  - restore and deploy: `restore.*`, `prebuild-capture.log`, `forward.*`, `installed-artifacts.txt`;
  - sessions s01–s06: `.raw`, `.txt`, `.steps.jsonl`;
  - capture: `s03-rtrace-receipt.json`, `s03-structure-check.txt`;
  - readback: `installed-app-readback*`.

**Documents:**
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/handover/HANDOVER_2026-10-13_B489_WS2816_REFERENCE.md` (additive sections)
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/hardware/device-build-registry.md` (§2 current B489 row and changelog)
- `/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/hardware/im69d130-dual-mic-learnings-2026-08-13.md`, `…/im69d130-board-wiring-from-eda-2026-08-05.md`, `docs/forensics/G1_AP_INPUT_SLOT_RATIFICATION_2026-08-15.md` (read only)

**Review files** (outside the repo): `/tmp/prism-b489-recovery-independent-review-20261014.md`, `/tmp/prism-b489-code-review-20261014.md.result`, `/tmp/prism-b489-init-independent-review-20261014.result.md`.

## 13. Unfinished

- **S3 audio:** the raw input is constant at −30935. The cause is unresolved, so there is **no valid musical reference** and no music-reactive claim. Optical and music parity remain TBD.
- **Device:** B489 is left on capture image `f3ee66e8`, which can be returned to `eff9bf47` with the reviewed restore.
- **Titan:** owned by the other team, not touched here; the parent covers the Titan work.
- **Governance:** `workflow_verify` refused this project ("outside configured workspace"). `workflow_gate` returned can-stop with no task ledger bound, which is not a completion certificate.

## 14. Records and reads

Every value above was taken from the retained logs, transcripts, commits and diffs named here. The parent's root reads and reviews are independent of this document. Publishing this debrief does not show that any other agent or memory system has read it.
