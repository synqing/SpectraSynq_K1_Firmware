# Bench K1 Full-Erase Recovery

## Verdict

[FACT] `RECOVERED` on 2026-07-13 AWST. The bench K1 at USB serial
`B4:3A:45:A5:89:B4`, chip `B489A500`, and explicit ports
`/dev/tty.usbmodem1401` / `/dev/cu.usbmodem1401` was fully erased and flashed
with the current K1 firmware.

[FACT] The deployed environment is `k1_bench_im73d`: production audio-semantic
flags, bench GPIO `4/5` mapping, physical IM73D microphone path, and no BLE or
probe instrumentation.

[FACT] Git HEAD at build time was
`b02fc165e28d5310f8d94d5c9a2acfa0875dc435` on a dirty working tree. Embedded
build provenance reads `git=b02fc16 epoch=1783934884 env=k1_bench_im73d`.

[FACT] Deployed upload-build firmware SHA-256 was
`3ed9ecd6025335ae3839d90fda6c1d80a2e3fe632c1a12d9927322b6544d14fe`.

## Exact Rerun Commands

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
bash scripts/agent/pio-build.sh k1_bench_im73d
shasum -a 256 .pio/build/k1_bench_im73d/firmware.bin .pio/build/k1_bench_im73d/firmware.elf
~/.platformio/penv/bin/python scripts/platformio/k1_upload_guard.py \
  --env k1_bench_im73d \
  --upload-port /dev/tty.usbmodem1401
~/.platformio/penv/bin/python \
  ~/.platformio/packages/tool-esptoolpy/esptool.py \
  --chip esp32s3 \
  --port /dev/tty.usbmodem1401 \
  erase_flash
~/.platformio/penv/bin/pio run \
  -e k1_bench_im73d \
  -t upload \
  --upload-port /dev/tty.usbmodem1401
```

## Validation

[FACT] Full-chip erase identified MAC `b4:3a:45:a5:89:b4` and reported
`Chip erase completed successfully in 4.8s`.

[FACT] Upload guard independently accepted the same MAC/chip for
`k1_bench_im73d`. Bootloader, partition table, boot app, and firmware sections
all reported `Hash of data verified`; upload exited successfully.

[FACT] Readback in `bench_k1_full_erase_recovery_readback.log` proves:

- [FACT] `BUILD: version=40103 git=b02fc16 epoch=1783934884 env=k1_bench_im73d`.
- [FACT] chip ID `B489A500`.
- [FACT] `CONFIG.SAMPLE_RATE: 12800` and `CONFIG.SAMPLES_PER_CHUNK: 96`.
- [FACT] live `[AP]` frames with changing tempo and onset fields.
- [FACT] no panic, abort, watchdog, backtrace, or reboot-loop marker was observed.

[FACT] The full erase removed prior persisted calibration. Readback reports
`CAL_SOURCE: default_invalid`, `CAL_VALID: 0`, and `CAL_PROFILE_LOADED: 0`.

[INFERENCE] Firmware recovery is complete, but subsequent audio truth-number
captures require a deliberate quiet-room noise calibration first. No calibration
was run during this recovery because room silence was not established.
