# SSA RT Audit - MAS-RT-AUDIT-20260710

## Scope

Read-only audit of the current dirty checkout on branch `lane/dual-sync-phase0`.
I inspected the uncommitted mic auto-sense implementation and only the adjacent
firmware/build/test surfaces needed to answer the hazard question. I did not
flash, monitor serial, run PlatformIO, or modify production/test files.

Evidence file written as the only intentional write in this pass.

## Commands Run

- `sed -n '1,220p' /Users/spectrasynq/.agents/skills/code-review/SKILL.md`
- `sed -n '1,220p' /Users/spectrasynq/.codex/skills/spectrasynq-audio-pipeline/SKILL.md`
- `rg -n "mic auto|auto-sense|auto sense|k1_mic|dual-sync|MAS-RT-AUDIT|upload guard|k1_upload_guard|device-build-registry" /Users/spectrasynq/.codex/memories/MEMORY.md`
- `sed -n '1,220p' AGENT_OS.md`
- `sed -n '1,220p' .claude/CLAUDE.md`
- `sed -n '1,220p' docs/spec-index.md`
- `sed -n '1,180p' progress.md`
- `sed -n '1,160p' .claude/handoff.md`
- `command rg --files | command rg '(^|/)codebase-map\.md$|(^|/)fsm-reference\.md$|(^|/)firmware-v3/docs/reference/'`
- `sed -n '1,180p' docs/protocol/k1-ws-contract.yaml`
- `sed -n '1,180p' docs/protocol/k1-rest-contract.yaml`
- `git status --short`
- `git rev-parse --abbrev-ref HEAD`
- `git diff --stat`
- `git diff --name-only`
- `git diff -- SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h platformio.ini scripts/agent/pio-build.sh scripts/platformio/k1_upload_guard.py tests/test_audio_telemetry_schema_static.py tests/test_im73d_audio_eval_harness.py tests/test_k1_upload_guard.py`
- `git ls-files --others --exclude-standard SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h tests/test_mic_auto_sense_static.py`
- `nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h`
- `nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp`
- `nl -ba tests/test_mic_auto_sense_static.py`
- `nl -ba SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino | sed -n '600,910p'`
- `nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '1,910p'`
- `nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals.h | sed -n '110,205p'`
- `nl -ba platformio.ini | sed -n '30,560p'`
- `nl -ba scripts/agent/pio-build.sh | sed -n '1,90p'`
- `nl -ba scripts/platformio/k1_upload_guard.py | sed -n '60,105p'`
- `command rg -n "k1_mic_auto_sense_|K1_MIC_AUTO|mas_" SPECTRASYNQ_K1_FIRMWARE tests platformio.ini scripts docs`
- `command rg -n "^\\[env:k1_|extends =|build_src_filter =|K1_MIC_AUTO_SENSE_V1|k1_bench_im73d_mic_auto_shadow|k1_prod_im73d" platformio.ini`
- `command rg -n "K1_MIC_AUTO_REASON_STALE_I2S|i2s_read_status|bytes_read|K1_MIC_AUTO_REASON_NONFINITE|isfinite" SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h platformio.ini`
- `git diff --check`

Not run: `bash scripts/agent/session-bootstrap.sh`, because the script itself
states it writes `.devin/last-bootstrap.json` and calls `repo-truth.sh`, which
writes `.devin/repo-truth-report.json`; the SSA scope allowed only read-only
work plus this evidence file. Not run: pytest/PlatformIO/device commands,
because they create build/cache/device side effects outside this read-only audit.

## Findings

### F1 - Runtime telemetry integrity hazard: stale I2S is not detectable by MAS

Status: `CONTRADICTORY`.

The MAS API advertises `K1_MIC_AUTO_REASON_STALE_I2S` in
`SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h:13-21`, but the new
implementation never consumes `i2s_read_status`, `bytes_read`, or the AP debug
read-status surface. The only `STALE_I2S` hit is the enum declaration; the MAS
update code only checks IM73D raw globals, conditioned peak, calibration, loud
guard fields, and non-finite values
(`SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp:30-101`).

This matters because the existing bounded-read guard explicitly zero-fills on
I2S timeout or short read:
`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:324-344`. In the normal non-debug
path, `i2s_read_status` and `bytes_read` are then discarded
(`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:352-359`). The raw IM73D metrics are
computed from the possibly zero-filled buffer immediately afterwards
(`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:362-379`), and MAS copies those
globals without fault provenance
(`SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp:41-49`).

Result: a DMA/read fault can look like a quiet, calibrated, headroom-safe
telemetry frame rather than `K1_MIC_AUTO_REASON_STALE_I2S`. Because
`k1_mic_auto_sense_applied_scale()` is fixed at `1.0f`, this is not a current
auto-gain behaviour change. It is still a runtime hazard if MAS telemetry is
used as proof of mic health or as a later controller input.

### F2 - Non-finite guard is suspect under the inherited build flags

Status: `NOT_VERIFIED`.

The new non-finite guard is `return !isfinite(value);`
(`SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp:13-15`) and drives the
`K1_MIC_AUTO_REASON_NONFINITE` path
(`SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp:90-99`). The shadow env
inherits the base `-ffast-math` build flag through `env:k1_bench_im73d`
(`platformio.ini:83-84`, `platformio.ini:216-232`).

I did not compile or inspect Xtensa assembly in this read-only pass, so I am not
claiming the guard is definitely optimised away in this toolchain. I am flagging
it as a production-firmware risk because `-ffast-math` includes assumptions that
can make NaN/Inf checks unreliable. The orchestrator should verify this with the
actual PlatformIO/Xtensa build before treating the non-finite path as a real
fault barrier.

### F3 - Production flag-off containment appears sound from source inspection

Status: `VERIFIED_SOURCE_ONLY`.

The base build filter includes `+<audio/k1_*.cpp>` but explicitly subtracts
`-<audio/k1_mic_auto_sense.cpp>` (`platformio.ini:44`). The only inspected env
that re-adds the source and defines the feature flag is the new
`k1_bench_im73d_mic_auto_shadow` env
(`platformio.ini:222-232`). `k1_bench_im73d` defines only
`K1_MIC_IM73D_PDM_V1` (`platformio.ini:216-220`), and `k1_prod_im73d` likewise
defines only `K1_MIC_IM73D_PDM_V1` on top of `k1_hardware`
(`platformio.ini:252-256`).

The upload/build surfaces are bench-scoped, not production default:
`scripts/agent/pio-build.sh:22-24` adds the shadow env to the compile wrapper
allowlist only, and `scripts/platformio/k1_upload_guard.py:76-99` maps it to
the bench K1 target tuple.

No `K1_MIC_AUTO_SENSE_V1` or `k1_mic_auto_*` hits were found in REST/WS control
surfaces; direct firmware hits are confined to the new files, `i2s_audio.h`,
`.ino`, tests, scripts, and planning artefacts.

### F4 - Current implementation does not apply auto-scale or persist/calibrate

Status: `VERIFIED_SOURCE_ONLY`.

`k1_mic_auto_sense_applied_scale()` returns `1.0f`
(`SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp:108-110`), and the flag-off
header stub also returns `1.0f`
(`SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h:72-74`). The acquisition path
still computes effective sensitivity as `CONFIG.SENSITIVITY * k1_loud_input_trim`
when loud guard is enabled
(`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:118-120`) and applies that value in
the per-sample loop (`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:420-436`).

The auto-sense source has no `save_config`, `LittleFS`, `Preferences`, NVS,
`start_noise_cal`, `sb_noise_cal_*`, heap allocation, or serial output. Its
per-frame update is O(1) aside from copying one POD telemetry struct
(`SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp:30-101`). The only new
serial emission is appended to the existing 1 Hz AP stream under
`K1_MIC_AUTO_SENSE_V1`
(`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:800-840`).

### F5 - Current direct usage is same-core, but the accessor is not cross-core safe

Status: `WATCH`.

The AP loop runs on core 0 by build flag (`platformio.ini:63-68`), while the LED
task is pinned to `SB_LED_TASK_CORE` and checked as a different core in setup
(`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:711-717`). The current MAS
write happens in `loop()` after GDFT and loud guard
(`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:780-885`). The current
MAS read for AP telemetry happens in `i2s_audio.h` inside the same loop path
(`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:800-840`).

Therefore I did not find a current cross-core reader. But
`k1_mic_auto_sense_read()` returns a multi-field struct by value from an
unprotected static global
(`SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp:10-11`,
`SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp:101-105`). If render/core-1
code later reads this surface, it will need a sequence counter, critical section,
or single-writer snapshot protocol; otherwise torn mixed-frame telemetry is
possible.

## Required Re-run Command

Most important static refutation:

```bash
command rg -n "K1_MIC_AUTO_REASON_STALE_I2S|i2s_read_status|bytes_read|K1_MIC_AUTO_REASON_NONFINITE|isfinite|-ffast-math|K1_MIC_AUTO_SENSE_V1" SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h platformio.ini
```

Production containment/build sanity the orchestrator should run outside this
read-only audit:

```bash
python3 -m pytest tests/test_mic_auto_sense_static.py tests/test_audio_telemetry_schema_static.py tests/test_im73d_audio_eval_harness.py tests/test_k1_upload_guard.py -q && bash scripts/agent/pio-build.sh k1_hardware && bash scripts/agent/pio-build.sh k1_bench_im73d && bash scripts/agent/pio-build.sh k1_bench_im73d_mic_auto_shadow
```

If the non-finite guard is to remain a safety claim, also inspect the generated
Xtensa code for `k1_mic_auto_nonfinite()` or replace it with a guard proven
under the repo's `-ffast-math` configuration.

## Verdict

The current diff does not appear to leak auto-sense into production flag-off
firmware and does not currently apply gain, persist config, trigger calibration,
or add heap/blocking work to the per-sample path. However, the MAS telemetry is
not runtime-sound as a health/fault surface because stale I2S/read failures are
not propagated into the state machine, despite an advertised stale-I2S reason.
Treat safety as contradicted for runtime telemetry trust, and source-verified
only for production flag containment.
