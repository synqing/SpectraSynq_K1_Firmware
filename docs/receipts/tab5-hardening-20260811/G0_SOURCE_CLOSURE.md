# G0 source-closure receipt

**Gate:** G0 — Source closure  
**Result:** PASS  
**Recorded:** 2026-08-11 (Australia/Perth)  
**Frozen baseline:** `21d0e593461af468d38394b140e2477bd58bf7f3`  
**Reviewed source-closure commit:** `0f3cab432c8b17b7b049f5a7996df8ca7c1a3f86`

## Closure result

The active Tab5 P4 production and native source is committed on the isolated
`fix/tab5-hardening-20260811` branch. Production packages are resolved from
exact official release URLs or immutable revisions listed in
`tab5_firmware/toolchain-lock.json`; no project-local `vendor/`, extracted
framework, untracked source file, branch name, version range, or machine-local
absolute path is required by the project configuration.

The live WDT repair is present as the explicit callback-to-loop queue ownership
change in the imported source. NimBLE callbacks enqueue bounded records and the
loop-owned drain path performs Deck/LVGL mutation. G1 mutates this invariant
rather than treating its presence as sufficient proof.

`pioarduino`'s tool installer internally materialises some official registry
packages through PlatformIO's global package cache after fetching their pinned
archives. Those standard packages are declared by name, version, upstream URL,
archive SHA-256 where available, and installed binary/tree hashes in the lock.
No nonstandard or fragile unpublished package remains; therefore no internal
mirror exception is required for G0.

## Disposable proof A

Source clone: `/tmp/tab5_g0_clean_clone_0f3cab43`  
Empty core: `/tmp/tab5_pio_core_g0d`  
Resolved HEAD: `0f3cab432c8b17b7b049f5a7996df8ca7c1a3f86`

Commands:

```sh
PLATFORMIO_CORE_DIR=/tmp/tab5_pio_core_g0d ~/.platformio/penv/bin/pio run -d tab5_firmware -e tab5_p4
PLATFORMIO_CORE_DIR=/tmp/tab5_pio_core_g0d ~/.platformio/penv/bin/pio run -d tab5_firmware -e native_sdl
```

Results:

- `tab5_p4`: PASS; RAM 65,988 / 512,000 bytes; flash 1,311,899 / 3,145,728 bytes.
- `native_sdl`: PASS.
- `firmware.elf`: `dc71e6f28127f5eb76baa67f93a639f4165b32aeeb3b7786c46ab3aaa259ccdb`
- `firmware.bin`: `15b2081c2ea602100acc4ca0fde92b83b740c077cba65039037d215cb0f44ca0`
- `bootloader.bin`: `103843e87f92267a481ed4e59dd383c7085e2d5af9ec0e4094ca23f4d9f51b7a`
- `partitions.bin`: `aaae2888c5a6a348004b5b436f47abb25ae32e72d9003902955a998eda723edd`
- Native executable before the production recapture rebuild:
  `5afc9f21dae1e10e8c5c5a4cf2451e50c345594b81ea4a1798e22175fc0a8c6b`.

The native environment clears the alternate PlatformIO environment's build
artifacts, so production was rebuilt after the native pass to capture the four
production hashes above.

## Disposable proof B

Source clone: `/tmp/tab5_g0_clean_clone2_0f3cab43`  
Empty core: `/tmp/tab5_pio_core_g0e`  
Resolved HEAD: `0f3cab432c8b17b7b049f5a7996df8ca7c1a3f86`

Commands:

```sh
PLATFORMIO_CORE_DIR=/tmp/tab5_pio_core_g0e ~/.platformio/penv/bin/pio run -d tab5_firmware -e tab5_p4
PLATFORMIO_CORE_DIR=/tmp/tab5_pio_core_g0e ~/.platformio/penv/bin/pio run -d tab5_firmware -e native_sdl
```

Results:

- `tab5_p4`: PASS; RAM 65,988 / 512,000 bytes; flash 1,311,899 / 3,145,728 bytes.
- `native_sdl`: PASS.
- `firmware.elf`: `158d7add2470e3a788e349e4c4d1ec1a86f26b294b00de93fd0f121e8e2ea01e`
- `firmware.bin`: `fec8e3b5687e5a6ee4096983f4c7dae0d72137983a57fa3d7240ae8578aa5b96`
- `bootloader.bin`: `ae97ea279e92cb00377c945825a892321f1243117f94a14183025a08868bfe60`
- `partitions.bin`: `aaae2888c5a6a348004b5b436f47abb25ae32e72d9003902955a998eda723edd`

## Reproducibility boundary

Both independent empty-core builds resolved the same package versions, compiled
the same clean source commit, passed the same production/native targets, emitted
identical RAM/flash sizes, and produced an identical partition image. ELF,
application, and bootloader bytes are **not bit-for-bit reproducible** across
the two disposable absolute build paths. G0 therefore claims recoverable source
and build reproducibility only; it does not claim deterministic binary output.

The recurring `esp_idf_size --ng` incompatibility is a non-fatal reporting
warning from the pinned PlatformIO/platform combination. PlatformIO's own size
check still passed and reported the values above. It is tracked for later build
polish but is not source closure or firmware correctness evidence.

## Exit checks

- Clean clone at exact reviewed commit: PASS.
- Two independent empty `PLATFORMIO_CORE_DIR` production builds: PASS.
- Two independent native builds: PASS.
- Exact dependency manifest and checksums: PASS.
- No required untracked source or project-local extracted framework: PASS.
- WDT ownership repair explicitly present for G1 mutation: PASS.
- Undeclared/fragile build input: none found.

G1 may begin. A later gate may not waive this receipt or broaden its claim.
