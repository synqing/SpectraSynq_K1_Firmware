# I2S/LCD_CAM RPL flash — brick and unbrick (`9087A500`, 2026-08-20)

**What happened:** Captain ordered the bench I2S experiment off (blue intro, dead secondary) and the same driver onto the RPL. `k1-flash-verified.sh k1_main_rpl_i2sled_probe` wrote the app at `0x10000` (esptool hash verified) then failed identity. Serial from ROM:

```
E (138) esp_image: Checksum failed. Calculated 0x5f read 0x8e
E (138) boot: OTA app partition slot 0 is not bootable
E (139) esp_image: image at 0x650000 has invalid magic byte
E (145) boot: OTA app partition slot 1 is not bootable
E (150) boot: No bootable app partitions in the partition table
```

Hard loop (`RTC_SW_SYS_RST`). App never started, so this is **not** an I2S runtime crash — the bootloader would not accept the image / found no bootable slot.

**Unbrick:** MAC confirmed `b4:3a:45:a5:87:90` via esptool. App-only rewrite of `k1_main_rpl_im69d` was not enough to get `:build`. Rewrote bootloader `0x0` + partitions `0x8000` + `boot_app0` `0xe000` + app `0x10000`. NVS at `0x9000` not erased.

**Now:** `IDENTITY OK: git=d276fd68 env=k1_main_rpl_im69d epoch=1787175949`. Dump `SYSTEM_FPS: 139.29` `LED_FPS: 146.02` `CAL_VALID: 1`.

**Park:** `k1_bench_im69d_i2sled_probe` and `k1_main_rpl_i2sled_probe` stay in source as NON-SHIPPABLE. Do not flash either without a new named GO. Bench is already back on `k1_bench_im69d` (LED_FPS 202.09).
