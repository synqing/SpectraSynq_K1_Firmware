# Lane C: what a port of `k1_fe` and `k1_fe_emu` must supply

Worktree `/Users/spectrasynq/SpectraSynq_K1_Firmware-s31`, head `fcdefec5`, 15 Nov 2026. Read-only: no repo file edited, no build run.
Baseline: HEAD content, as built at 09:26 AWST. At 09:46 another lane edited `audio/i2s_audio.h` and `system/k1_platform.h` in this worktree (uncommitted: adds `K1_PLATFORM_S31` and an ESP-IDF 6.1 `#error` at i2s_audio.h:95-99). That edit is not reflected below; the line numbers for those two files are HEAD's.
Machine-readable twin: `inventory.json` (same folder). Every `file:line` is relative to `SPECTRASYNQ_K1_FIRMWARE/` unless it starts `platformio.ini`.

How the evidence was made (so it can be trusted or re-run):
- File list: `build_src_filter` evaluated independently over the source tree gives 78 files per env; `.pio/build/{k1_fe,k1_fe_emu}/src` holds exactly the same 78 objects (0 differences, both envs).
- Calls: I rebuilt the xtensa g++ command line from the pioarduino flag files plus the env's `build_flags`, and checked it against the build's own `.d` dependency files: the header set matched for 78/78 TUs in each env. I then ran `-E` and scanned only the preprocessed project lines, so every call below is in ACTIVE code (disabled `#if` branches and comments cannot appear). Link-level facts come from `nm` on every object, the link maps and `firmware.elf`.
- `file:line` is the line the preprocessor emitted the statement at (first line of a multi-line macro use); spot-checked against raw source.

## 1. Files, flags, settings

### 1.1 Source selection (identical for both envs; the emulator is selected by `-D` flags, not files)
- Filter chain in order: `k1_hardware` (platformio.ini:44) then `k1_main_rpl_im69d` adds `+<director/k1_edgemixer.cpp>`, then `k1_fe` adds `+<audio/k1_pcm1808_input.cpp>` `+<system/k1_fe_board.cpp>`. `k1_fe_emu` adds nothing.
- 78 TUs: `.ino` 1, audio 18, control 6, director 5, effects 31, persistence 1, serial 7, system 4, visual 5. Full list with per-file API counts is `files[]` in the JSON.
- Compiled but empty (0 bytes after preprocessing), so they need no port work in that env:
  - `k1_fe`: audio/k1_emu_fixture.cpp, audio/k1_stereo_probe.cpp, audio/k1_stm.cpp, audio/k1_stm_fft512_bench.cpp, serial/k1_ap_capture_telemetry.cpp, serial/k1_scheduling_trace_telemetry.cpp, visual/k1_i2s_emit.cpp, visual/k1_render_trace.cpp (70 live TUs).
  - `k1_fe_emu`: the same list minus audio/k1_emu_fixture.cpp and visual/k1_render_trace.cpp, which go live (72 live TUs).
- Not compiled (33 files in src_dir): all of diag/*, network/*, nfc/*, effects/framework/*, platform/k1_p4_led_transport.cpp, audio/k1_usb_audio_input.cpp, audio/k1_mic_auto_sense.cpp, audio/k1_audio_frame_host_shim.c, director/beat_aware_director.cpp.
- `control/k1_wireless_control.cpp` compiles to 145 bytes: three forwarders to `k1_control_*`; no WiFi/BLE API.
- `.ino`: `SPECTRASYNQ_K1_FIRMWARE.ino` (1958 lines) is converted by PlatformIO to a `.ino.cpp` and compiled as one TU; the port needs `setup()`/`loop()` under an Arduino-on-IDF `app_main`.
- 171 project files (cpp plus headers) enter the build. Much real code lives in headers: audio/i2s_audio.h (PDM I2S), visual/led_utilities.h (FastLED), system/system.h, persistence/bridge_fs.h, visual/k1_look.h, visual/k1_look_file.h, system/globals.h.

### 1.2 extra_scripts (none adds or removes a source file)
- `k1_src_includes.py`: appends CPPPATH `SPECTRASYNQ_K1_FIRMWARE/{audio,visual,effects,director,control,network,serial,system,persistence,calibration,diag,platform,nfc}` plus the `qio_opi` sdkconfig include dir.
- `k1_build_provenance.py`: adds `-DK1_BUILD_GIT_HASH="..."`, `-DK1_BUILD_EPOCH=<s>`, `-DK1_BUILD_ENV="..."`, and (k1_fe only, `custom_release_tag_prefix = fe-`) `-DK1_BUILD_TAG="..."`. The port needs a configure-time equivalent.
- `k1_upload_guard.py`: upload-time identity guard only. `k1_i2s_emit_skip_fastled_wrapper.py`: no-op here (needs `K1_LED_I2S_DIRECT_V1`, undefined).

### 1.3 Flags (plain JSON arrays are in `inventory.json` at `flags.k1_fe` and `flags.k1_fe_emu`)
- `k1_fe`: 56 items from `build_flags`. Notable: `-DARDUINO_USB_MODE=1 -DARDUINO_USB_CDC_ON_BOOT=1 -DARDUINO_RUNNING_CORE=0 -DBOARD_HAS_PSRAM -DK1_HARDWARE -DK1_LED_TASK_CORE=1 -DDEFAULT_SAMPLE_RATE=12800 -DDEFAULT_SAMPLES_PER_CHUNK=96 -O3 -ffast-math -fno-finite-math-only -Wno-narrowing -Wno-deprecated-declarations -DK1_MAIN_RPL_PINMAP_V1=1 -DK1_MIC_IM69D_PDM_V1 -DK1_MIC_IM69D_DSR_16S_V1 -DK1_MIC_IM69D_SLOT_RIGHT -DK1_WS2816_LEVER2_V1 -DK1_RMT_ALLOC_ON_VP_CORE_V1=1 -DK1_FE_BOARD_V1 -DK1_FE_BOARD_GX -DK1_PCM1808_LINE_SWITCH=1 -DK1_PCM1808_MONO_POLICY=K1_PCM1808_MONO_MID -DK1_PCM1808_CANON_TRIM_Q15=2048`. `-DK1_EDGE_PALETTE_HONOUR_V1` appears twice (harmless, inherited).
- `k1_fe_emu` = the 56 plus 7: `-DK1_RENDER_TRACE_V1 -DK1_EMU_FIXTURE -DK1_EMU_SKIP_EMIT -DK1_EMU_UART0 -DK1_EMU_FE_MIC_ONLY -DK1_EMU_ONSET_TRACE -DK1_EMU_SPECTRUM_TRACE`, plus a source-only flag `build_src_flags = -include k1_emu_clock_force.h` (macro-renames `millis`/`micros` to `k1_emu_fixture_time_ms/us`; header is audio/k1_emu_clock_force.h).
- `build_unflags` (both): `-DARDUINO_RUNNING_CORE=1` (board JSON default, replaced by `=0`).
- Framework-added flags (not in the ini; reference only, `framework_flags_reference` in the JSON): `-std=gnu++2a -fno-rtti -fexceptions`, `-mlongcalls`, `-mdisable-hardware-atomics`, `-DARDUINO=10812 -DARDUINO_ARCH_ESP32 -DESP32=ESP32 -DF_CPU=240000000L`, IDF defines. Xtensa-only items to drop for RISC-V are listed there.
- `lib_deps` (both): `fastled/FastLED@3.10.3`, `file://libraries/FixedPoints`, `file://libraries/M5ROTATE8`.
- Board settings (both): platform pioarduino 54.03.20 (arduino-esp32 3.2.0, IDF 5.4.1), `board = esp32-s3-devkitc1-n16r8`, `framework = arduino`, `board_build.arduino.memory_type = qio_opi`, `board_build.psram_type = opi`, `board_build.flash_mode = qio`, `board_build.flash_size = 16MB`, `board_upload.flash_size = 16MB`, `board_build.partitions = default_16MB.csv`, monitor 115200, upload 921600.
- Partition table in use (default_16MB.csv): nvs 0x9000/0x5000, otadata 0xe000/0x2000, app0 0x10000/0x640000, app1 (ota_1) 0x650000/0x640000, spiffs 0xc90000/0x360000 (LittleFS), coredump 0xFF0000/0x10000. The emulator reads its scenario blob from `ota_1` (audio/k1_emu_fixture.cpp:334-335).

## 2. Must-supply list, grouped

### 2.1 Arduino API (site counts are active sites; both envs unless noted)
- Console: `USBSerial` is `#define USBSerial Serial`, which resolves to `HWCDCSerial` (USB-Serial-JTAG CDC): `begin` (system/system.h:198, serial_menu.cpp:675), `setTxBufferSize(4096)` (system.h:194), `setTxTimeoutMs(20)` (:196), `flush`, `available`/`read` (serial_menu.cpp:4263-4267), `operator bool`, plus the `Print` family (`print`/`println`/`printf`: 1031 + 745 + 29 sites, 20 to 25 files; serial_menu.cpp is the bulk).
- Timing: `millis` (68 sites, 25 TUs), `micros` (.ino:935, serial_cmd_handlers.cpp:1312,1316, system.h:57,61), `delay` (5 sites), `yield` (serial_menu.cpp:691). `delayMicroseconds` (persistence/encoders.h:71,73) is compiled but absent from `firmware.elf`.
- GPIO/ADC (k1_fe_board.cpp, k1_fe only): `digitalRead` (:442,505,594,703,707), `analogReadMilliVolts` (:445-448), `analogSetPinAttenuation` (:586-587). `pinMode`/`digitalWrite` exist only in encoders.h:67-72 (`K1_HAS_ROTATE8` is 0).
- Wire: `Wire.begin(sda,scl)` k1_fe_board.cpp:592 (FE board I2C 2/1) and encoders.h:78 (rotary encoder bus, disabled). `M5ROTATE8` is constructed (.ino:120) but all its methods are removed by gc.
- Watchdog/system: `enableLoopWDT` (.ino:863), `feedLoopWDT` (.ino:930), `ESP.getEfuseMac` (utilities.h:27), `ESP.restart` (system.h:50), `Ticker` (globals.h:544; ctor/dtor in 49 TUs, `_attach_us`/`detach` in 2).
- Not used (checked): Preferences/NVS, `ledc*`, `attachInterrupt`, `SPI`, `String`, WiFi/BLE/lwip symbols.

### 2.2 FastLED 3.10.3 (RMT5 backend)
- Four controllers, all `WS2812B` timing, colour order template `RGB`, pins are compile-time template arguments: led_utilities.h:1697 `<WS2812B, LED_DATA_PIN, RGB>(ws2816_wire, 0, LED_COUNT)`, :1698 `<WS2812B, LED_CLOCK_PIN, RGB>(ws2816_wire, LED_COUNT, LED_COUNT)`, :2978 `<WS2812B, SECONDARY_LED_DATA_PIN, RGB>`, :2980 `<WS2812B, SECONDARY_LED_CLOCK_PIN, RGB>`.
- Other calls: `setCorrection` (:1700), `setTemperature` (:1701), `setDither(DISABLE_DITHER)` (:1464,1551,1702), `setBrightness` (system.h:39, led_utilities.h:1301), `setMaxPowerInMilliWatts` (:1302), `setMaxPowerInVoltsAndMilliamps(5.0, mA)` (:1754), `show` (platform/k1_led_emit.h:24, system.h:48, led_utilities.h:1465,1627), `delay` (system.h:37, led_utilities.h:1780,1786,2148). Emu only: `getBrightness`, `calculate_max_brightness_for_power_mW` (k1_emu_fixture.cpp:976,980).
- Types/maths: `CRGB`, `CHSV`, `CRGBPalette16` (36 sites, 26 effect files), `ColorFromPalette` (lightshow_modes.h:305), `blend`, `inoise16` (light_mode_kaleidoscope.cpp:101-103), `rgb2hsv_approximate` (led_utilities.h:2312,2320), `nscale8_video` (ws2816_pack.h), `hsv2rgb_rainbow`, `fl::fill_gradient_RGB`. No `FASTLED_*` configuration macro is defined anywhere (only unrelated `ENABLE_FASTLED_*` in constants.h:682,687).
- FastLED members actually linked (26): FastLED, allocator, cled_controller, colorutils, crgb, downscale, engine_events, fill, gradient, hsv2rgb, **idf5_rmt, strip_rmt, led_strip_api, led_strip_rmt_dev, led_strip_rmt_encoder**, io, json, noise, power_mgt, raster_sparse, rgbw, screenmap, str, tile2x2, upscale, xymap. Their IDF needs: `rmt_new_tx_channel rmt_transmit rmt_enable rmt_disable rmt_tx_wait_all_done rmt_new_bytes_encoder rmt_new_copy_encoder rmt_encoder_reset rmt_del_encoder rmt_del_channel`, `heap_caps_malloc/free`, `esp_log_write`, `esp_log_timestamp`. Note `K1_RMT_ALLOC_ON_VP_CORE_V1=1` (first `show()` on core 1) and `K1_WS2816_LEVER2_V1` (48-bit WS2816 packer over WS2812B timing).

### 2.3 Filesystem (LittleFS)
- `LittleFS.begin(true)` (persistence/bridge_fs.h:706), `open` (15 sites: k1_effect_queue.cpp:428,452, k1_show_state.cpp:262,280, bridge_fs.h, k1_look_file.h), `remove` (9), `mkdir` (k1_look_file.h:426), `rename` (:443), `exists` (bridge_fs.h:110), `File` read/write/seek/close/flush/size. Uses the `spiffs`-labelled partition. `fopen` appears only in a string. No SPIFFS/FFat/SD use.

### 2.4 ESP-IDF drivers and system
- `esp_driver_i2s`: `i2s_new_channel` (i2s_audio.h:337, k1_pcm1808_input.cpp:319), `i2s_channel_init_pdm_rx_mode` (i2s_audio.h:399; IM69D PDM RX, mono 16-bit, `I2S_PDM_RX_CLK_DEFAULT_CONFIG(12800)`), and k1_fe only: `i2s_channel_init_std_mode` (k1_pcm1808_input.cpp:343; I2S_NUM_1, ROLE_SLAVE, slot BOTH), `i2s_channel_enable` (i2s_audio.h:474, pcm1808:354), `i2s_channel_read` (i2s_audio.h:669, pcm1808:188,371), `i2s_channel_register_event_callback` (pcm1808:350).
- `esp_driver_pcnt` (k1_fe only): one unit, one channel, edge-increase counting (k1_pcm1808_input.cpp:263-296: `pcnt_new_unit/new_channel/set_edge_action/enable/clear_count/start/stop/get_count/disable/del_channel/del_unit`).
- `esp_driver_gpio` (k1_fe only): `gpio_config` (k1_fe_board.cpp:554,565), `gpio_set_level` (:459,558,566,677), `GPIO_MODE_*`, `GPIO_NUM_NC`.
- `esp_driver_rmt`: only via FastLED (2.2). `esp_timer_get_time` (35 sites, 4 TUs link it). `heap_caps_malloc/free/get_free_size/get_largest_free_block` with `MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT` (.ino:694; k1_look.h:416; k1_look_file.h:125,397,473; the look files fall back to `MALLOC_CAP_8BIT`, .ino:694 does not) and `MALLOC_CAP_INTERNAL` (bridge_fs.h, k1_look_file.h).
- FreeRTOS: `xTaskCreatePinnedToCore` (.ino:814 `led_task`, 8192 B, pri idle+1, core `K1_LED_TASK_CORE`=1; k1_pcm1808_input.cpp:460 `pcm_cap`, 3072 B, pri idle+2, core 0), `vTaskDelay`, `vPortYield`, `xTaskGetCurrentTaskHandle`, `xPortGetCoreID`, and `portMUX_TYPE` spinlocks (15 declarations; 42 enter + 56 exit sites over 12 files: k1_audio_frame, k1_audio_snapshot, k1_musical_saliency, k1_onset_beat, k1_tempo, k1_colour_lab, k1_command_channels, ...).
- System: `esp_random` (3), `esp_reset_reason` plus `ESP_RST_{POWERON,SW,PANIC,INT_WDT,TASK_WDT,WDT,BROWNOUT,DEEPSLEEP,EXT,SDIO,UNKNOWN}` (.ino:685,712; serial_menu.cpp:2625-2635; k1_bootloop_guard.h:84-85), `esp_task_wdt_reconfigure/add/reset/status` with `esp_task_wdt_config_t{timeout_ms, idle_core_mask=0x1, trigger_panic}` (.ino:860-863,1483-1492), `esp_app_get_description` (serial_menu.h:414), `RTC_NOINIT_ATTR` bootloop state (.ino:108), `IRAM_ATTR`/`DRAM_ATTR` sections.
- libc/libm/libgcc/libstdc++ (81 symbols, full list in JSON): `memcpy memmove memset strcmp strncmp strlen strchr strcpy strncpy strlcpy strtok_r strtof strtoll strtoull atoi atol snprintf sscanf __errno`, `exp expf pow sqrt sqrtf sin sinf cosf atan2f logf log2f floorf roundf lroundf lrintf fmaxf fminf tanhf`, soft double (`__adddf3 __muldf3 ...`), `operator new[]/delete`, `__cxa_*`, `__gxx_personality_v0`, `_Unwind_Resume`, `__stack_chk_*`, `__atomic_fetch_add_4` (7 TUs), `__atomic_exchange_1/_4`, `abort`, `malloc`.
- C++ exceptions are enabled by the framework (`-fexceptions`); `__gxx_personality_v0` and `_Unwind_Resume` are referenced.

### 2.5 k1_fe_emu extras (not in k1_fe)
- `esp_partition_find_first(ESP_PARTITION_TYPE_APP, ESP_PARTITION_SUBTYPE_APP_OTA_1)` (k1_emu_fixture.cpp:334), `esp_partition_read` (:338,376,383,433,625), `esp_crc32_le` (resolves to `esp_rom_crc32_le`), `ps_malloc` (k1_emu_fixture.cpp:713,730,737; k1_render_trace.cpp:100-104), `xTaskCreateStaticPinnedToCore` (k1_render_trace.cpp:90) with `xTaskGenericNotify`/`ulTaskGenericNotifyTake`, `Serial0.begin(115200)` (.ino:672, k1_emu_fixture.cpp:760), `Serial1.begin(115200, SERIAL_8N1, rx=7, tx=6)` (:672; trace UART), `HardwareSerial`.
- Absent in emu (hardware paths skipped): PCM1808 STD I2S, PCNT, board GPIO/ADC, `i2s_channel_enable/read`. Emu keeps FastLED/RMT linked (`addLeds` still runs; `show` is skipped by `K1_EMU_SKIP_EMIT`).

## 3. Items settled with evidence

### 3.1 diag/k1_rmt_completion_trace.cpp (Xtensa asm near line 141): NOT compiled in either env; asm is guarded
- Not selected: no `+<diag/...>` token anywhere in the filter chain; independent glob evaluation and the 78-object listing in both build dirs contain no diag/* file.
- Whole body is `#ifdef K1_SCHEDULING_TRACE_V1` (k1_rmt_completion_trace.cpp:4 to :739); that macro is set only in trace envs (platformio.ini:1442,1461,2211,2232).
- The asm is `__asm__ __volatile__("memw" ::: "memory")` at :142 inside `#if defined(__XTENSA__)` (:141); the `#else` (:143-144) is `__atomic_thread_fence(__ATOMIC_SEQ_CST)`. So it is guarded by architecture as well.
- Only serial/k1_scheduling_trace_telemetry.cpp:12 includes its header, and that TU is empty in both envs; no `k1_rmt_completion_trace_*` symbol is referenced by any object.

### 3.2 audio/i2s_audio.h IDF-5.4.1 `#error`: REACHED in both envs, and would fire on IDF 6.1.1
- audio/i2s_audio.h:90-91: `#if ESP_IDF_VERSION != ESP_IDF_VERSION_VAL(5, 4, 1)` then `#error "IM69D slot/order contract is source-frozen to the active ESP-IDF 5.4.1 driver"`.
- Nesting: `#ifdef K1_MIC_IM69D_PDM_V1` (:86), `#ifndef K1_PLATFORM_P4` (:88), `#if K1_AUDIO_SOURCE_MIC` (:89). Measured with `-dM -E` on the .ino TU for both envs: `K1_MIC_IM69D_PDM_V1`=1, `K1_PLATFORM_P4` undefined, `K1_AUDIO_SOURCE_MIC`=1, IDF version macros 5/4/1.
- i2s_audio.h is included once, from SPECTRASYNQ_K1_FIRMWARE.ino:39. Two ways past it: define `K1_PLATFORM_P4` (also pulls the P4 seam, see 4) or edit the guard after re-proving the PDM slot order. The `static_assert`s at :99-102 (`I2S_PDM_SLOT_RIGHT==1`, `LEFT==2`) also need re-checking on IDF 6.1.1.
- Other `#error` guards in the same file (:9,16,38,383,386,397) are build-contract checks, not version checks.

### 3.3 visual/k1_i2s_emit.cpp: selected and compiled, but contains no code
- Matched by `+<visual/k1_i2s_emit.cpp>` (k1_hardware filter), so `visual/k1_i2s_emit.cpp.o` exists; the whole file is `#ifdef K1_LED_I2S_DIRECT_V1` (k1_i2s_emit.cpp:4 to :127). That macro is undefined in both envs (`-dM` check) and the object is 0/0/0 bytes in both. The Yves LCD_CAM driver include (`third_party/yves/...`, :27) is never reached. The skip script is a no-op for the same reason.

### 3.4 `-Wl,--wrap=` linker wraps
- In the ini for these two envs: none (the resolved `build_flags` contain no `-Wl,`).
- From the Arduino framework (pioarduino-build.py LINKFLAGS), applied to both: `--wrap=esp_log_write`, `--wrap=esp_log_writev`, `--wrap=log_printf`, `--wrap=longjmp`. The first three are implemented in the prebuilt IDF component `libespressif__esp_diagnostics.a(esp_diagnostics_log_hook.c.obj)` (seen in the k1_fe `firmware.map`). No `__wrap_longjmp` definition appears in that map (UNVERIFIED which archive would satisfy it).
- Project wraps `--wrap=rmt_new_tx_channel` / `--wrap=rmt_transmit` exist only in the four trace envs (platformio.ini:1445-1446, 1466-1467, 2219-2220, 2240-2241); their implementation is diag/k1_rmt_completion_trace.cpp:418,455, not compiled here. No other project source defines a `__wrap_` symbol.

## 4. S3-only and Xtensa-only dependencies (what is really active)
- Not present in active code: inline asm, `xthal_*`, `XT_*`, `ccount`, register-struct access (`GPIO.`, `I2S0.`, `REG_*`), `*_ll_*`, `soc/`, `hal/`, `rom/`, `esp32s3/`, `xtensa/` includes. None of the 292 matching `#include` lines in compiled project files (libc/libstdc++ included in that count) names them; those headers enter only through Arduino.h/FreeRTOS/IDF headers. The only asm in the tree is the guarded, uncompiled line in 3.1.
- Active and chip-specific:
  - `#error` on `ESP_IDF_VERSION` (3.2) and the PDM slot `static_assert`s (i2s_audio.h:99-102).
  - Chip guard system/k1_platform.h:6-17 (`CONFIG_IDF_TARGET_ESP32S3` / `ESP32P4`): on an S31 neither macro is set, so no `#error` fires (the ADR-0007 seam passes through).
  - Section attributes: `IRAM_ATTR` (k1_gdft_core.cpp:119, k1_gdft_core.h:28, k1_pcm1808_input.cpp:149,158, utilities.h:5), `DRAM_ATTR` (globals.h:156,169), `RTC_NOINIT_ATTR` (.ino:108).
  - Software atomics (`-mdisable-hardware-atomics`): nothing to port on RISC-V.
  - HWCDC console via `ARDUINO_USB_MODE=1`, `ARDUINO_USB_CDC_ON_BOOT=1` (system.h:193-198).
  - ADC1 CC1/CC2 on GPIO4/5, octal-PSRAM knobs (`BOARD_HAS_PSRAM`, `qio_opi`), GPIO numbers up to 48 with S3 strap/reserved assumptions (k1_fe_board.h:52-53).
  - Dual-core split: loopTask core 0, `led_task` core 1, `pcm_cap` core 0, TWDT idle mask 0x1 (.ino:814,860; k1_pcm1808_input.cpp:460).
- Existing second-target precedent: `system/k1_platform.h`, `platform/k1_led_emit.h` (`K1_PLATFORM_P4`), `platform/k1_p4_led_transport.cpp` (not compiled here), and the `K1_P4_WIFI6_PINMAP_V1` pin branch (constants.h:401-452).
- Local IDF v6.1.1 `components/soc/esp32s31/include/soc/soc_caps.h` (FACT, macros only): 2 cores, `SOC_GPIO_PIN_COUNT` 62 (GPIO0..61), I2S with PDM RX (`SOC_I2S_SUPPORTS_PDM_RX` 1, HW v2, PDM2PCM on I2S0), PCNT, RMT (with DMA), USB-Serial-JTAG and USB OTG, ADC (2 units), 3 I2C, SPIRAM supported, 5 UARTs. Components `esp_driver_{i2s,pcnt,rmt,gpio,i2c,usb_serial_jtag}` exist in that IDF.

## 5. Pin definitions (single S31 pin file plug-in points)
Selection: constants.h:400-624 is an `#if/#elif` chain of pin maps; `k1_fe` resolves to the `K1_MAIN_RPL_PINMAP_V1` branch (constants.h:454-533) with `K1_MAIN_RPL_REWIRE_20261110` NOT defined (it is an `#error` with `K1_FE_BOARD_V1`, constants.h:477-478). The FE physical map is system/k1_fe_board.h:19-54 (`K1_FE_BOARD_GX` branch; the legacy STUSB4500 branch :55-91 is inactive). `K1_FE_BOARD_GX` makes constants.h defer the PDM pins to k1_fe_board.h (constants.h:495-496).

| macro | value | defined at | role |
|---|---|---|---|
| `LED_DATA_PIN` | 15 | constants.h:485 | primary strip DIN-A (FastLED template arg, led_utilities.h:1697) |
| `LED_CLOCK_PIN` | 16 | constants.h:486 | primary strip DIN-B (legacy "clock" name; second data line, :1698) |
| `SECONDARY_LED_DATA_PIN` | 17 | constants.h:487 | secondary DIN-A (:2978) |
| `SECONDARY_LED_CLOCK_PIN` | 18 | constants.h:488 | secondary DIN-B (:2980) |
| `K1_PDM_CLK_PIN` / `K1_PDM_DIN_PIN` | 48 / 41 | k1_fe_board.h:41-42 | IM69D130 PDM mic (i2s_audio.h:353-354) |
| `K1_IM69_PDM_SEL_PIN` | -1 | constants.h:513 | not driven |
| `K1_PCM1808_BCLK_PIN` / `LRCK` / `DIN` | 47 / 14 / 21 | k1_fe_board.h:36-38 | PCM1808 I2S1 slave RX (fallbacks in k1_pcm1808_input.h:11-20) |
| `K1_PCM1808_NFC_CS_HOLD_PIN` | -1 | k1_fe_board.h:40 | disabled |
| `K1_FE_ADC_DOUT_PIN` / `ADC_SHDNZ` | 45 / 46 | k1_fe_board.h:39,35 | external ADC header (S3 straps) |
| `K1_FE_I2C_SDA_PIN` / `SCL` | 2 / 1 | k1_fe_board.h:25-26 | FE board I2C (`Wire.begin`) |
| `K1_FE_HEARTBEAT_PIN` | 8 | k1_fe_board.h:27 | status LED |
| `K1_FE_POWER_PERMIT_PIN` | 39 | k1_fe_board.h:28 | current-limit select |
| `K1_FE_VBUS_PG_PIN` | 40 | k1_fe_board.h:29 | eFuse power-good |
| `K1_FE_LED_OE_A_PIN` / `OE_B` | 38 / 6 | k1_fe_board.h:30-31 | LED level-shifter OE |
| `K1_FE_JACK_DET_PIN` | 42 | k1_fe_board.h:32 | jack detect |
| `K1_FE_CC1_SENSE_PIN` / `CC2` | 4 / 5 | k1_fe_board.h:33-34 | ADC1 CC sense |
| defined, no active use | NAV R/PRESS/L 3/9/10, USER1/2/3 12/13/11, SERVICE TX/RX 43/44, BOOT 0, `RNG_SEED_PIN` 10, legacy `I2S_BCLK/LRCLK/DIN_PIN` 13/11/14 (only in the inactive std-mode branch, i2s_audio.h:455-458), `I2C_SDA/SCL_PIN` -1 | k1_fe_board.h:43-51, constants.h:467-469,521-522,533 | |
| emu only | `kClientTraceTx/Rx` 6 / 7 | k1_emu_fixture.cpp:58-59 | UART1 client trace |

`static_assert`s that a new pin file must still satisfy: k1_pcm1808_input.cpp:29-32 (PCM1808 pins distinct from PDM pins and LED lines), :247 (NFC hold not an LED line).

## 6. Things that will stop an S31 build on day one
1. `#error` at audio/i2s_audio.h:91 (IDF != 5.4.1), reached in both envs.
2. The pin tables above (GPIO48 and the S3 strap/UART/PSRAM assumptions) need an S31 map.
3. `HWCDC`, `enableLoopWDT`/`feedLoopWDT`, `Ticker`, `LittleFS`, `analogReadMilliVolts` come from arduino-esp32; their 4.0.0-RC1 forms were not read (UNVERIFIED).
4. FastLED 3.10.3 must find IDF 6.1.1 RMT (`rmt_*` calls above) and the project's `K1_RMT_ALLOC_ON_VP_CORE_V1` behaviour.
5. Sections `.iram1`/`.dram1`/`.rtc_noinit` and a LittleFS-labelled `spiffs` partition (plus `ota_1` for the emulator blob).

## 7. UNVERIFIED (not established by this lane)
- Counts of I2S controllers, PCNT units and RMT TX channels on S31 (not in `soc_caps.h`; k1_fe needs I2S0 PDM RX + I2S1 STD RX slave, 1 PCNT unit, 4 RMT TX channels).
- S31 ADC channel mapping for GPIO4/5 equivalents; S31 strap and reserved pins; S31 PSRAM configuration.
- arduino-esp32 4.0.0-RC1 API drift for the Arduino calls in 2.1 (sources not inspected); IDF 6.1.1 forms of `esp_task_wdt_reconfigure`/`esp_task_wdt_config_t`.
- Which archive would satisfy `--wrap=longjmp`.
- Reachability of encoders.h:67-78 in k1_fe: compiled into the .ino TU, `K1_HAS_ROTATE8`=0, M5ROTATE8 methods absent from the ELF; the surviving `TwoWire::begin` reference is attributed to k1_fe_board.cpp.
- The main checkout `/Users/spectrasynq/SpectraSynq_K1_Firmware/.pio/build` holds only an empty `k1_hardware/` (0 objects), so no k1_fe/k1_fe_emu objects exist there; the cross-check used this worktree's builds (09:26 AWST, 15 Nov 2026) plus the independent filter evaluation.
- PlatformIO's generated `.ino.cpp` (auto prototypes) no longer exists on disk; I prepended `#include <Arduino.h>` + `#line` instead, which reproduced the build's header set exactly. `K1_BUILD_*` values were placeholders; no project `#if` depends on them (header sets matched).
