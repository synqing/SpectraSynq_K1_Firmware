# I2S direct Yves probe — FAIL / parked (9087A500)

**Silicon now:** `BUILD: version=40103 git=d276fd68 epoch=1787175949 env=k1_main_rpl_im69d`  
**Dump:** `CHIP ID: 9087A500` `SYSTEM_FPS: 136.89` `LED_FPS: 144.48` `CAL_VALID: 1`  
**Close stamp:** that identity on 9087A500. Do not flash `k1_main_rpl_i2sled_probe` again without a new named GO.

## What happened

Source for the direct Yves driver is on the branch (`293490b4`, flag-gated,
RPL probe env only). Host gate passed (1426 tests, production + probe PIO
builds, probe `image_info` Checksum `0xcc (valid)`).

On silicon the probe app was **ROM-rejected**:

```
E (138) esp_image: Checksum failed. Calculated <varies> read 0xcc
E (139) boot: OTA app partition slot 0 is not bootable
E (150) boot: No bootable app partitions in the partition table
```

esptool `write_flash` + `verify_flash` both reported hash/digest OK. That is
**not** bootable. Same class of brick as the earlier wrapper-I2S flash
(`docs/forensics/runtime-evidence/20260820T-i2sled-rpl-brick/RESULT.md`).

A later restore write left the **proven** image in the same loop
(`Calculated 0xfa read 0x94` — `0x94` is the staged `d276fd68` footer).
Full-chain rewrite with `--flash_size keep` + `--after watchdog_reset`
(not RTS `hard_reset`, which straps `boot:0x0 DOWNLOAD`) brought the app back.

## Do not

- Flash `k1_main_rpl_i2sled_probe` again
- Use `--after hard_reset` on this USB-JTAG S3 (leaves DOWNLOAD)
- Treat esptool verify as a boot gate
- Tune Yves T0H / clock — the app never stayed up

## Remaining ship path

1. **Already on silicon / in source:** production RMT look `k1_main_rpl_im69d`
   @ `d276fd68` is running. Direct-driver source stays flag-gated in
   `293490b4`; production code path is unchanged.
2. **Agent:** host-only diagnosis of why ROM XOR ≠ stored checksum on the
   probe `.bin` (and why a keep-flash once printed `INIT_LEDS: PASS` before
   a false-positive restore). No device write.
3. **Captain:** named GO if a new probe image is ever offered.
4. **Shipped for this lane:** the restore identity above. I2S/LCD_CAM eval
   stays PARKED until that GO.
