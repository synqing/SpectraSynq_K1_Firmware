#pragma once

// K1 Founders' Edition board support. K1_FE_BOARD_V1 enables this module.
// K1_FE_BOARD_GX selects the 5 V K1-FE-Gx PCB with the routed ADC test header.
// The legacy profile retains STUSB4500 detection and its 20 V power policy.
// Select the matching build environment; Gx has no automatic board-ID device.

#if defined(K1_FE_BOARD_GX) && !defined(K1_FE_BOARD_V1)
#error "K1_FE_BOARD_GX requires K1_FE_BOARD_V1"
#endif
#if defined(K1_FE_BOARD_GX) && (defined(K1_FE_BENCH_B489_V1) || defined(K1_ST25_PROBE_V1))
#error "The Gx PCB pin map cannot share a build with the B489 loom or ST25 probe"
#endif

#ifdef K1_FE_BOARD_V1

#include <stdint.h>

#ifdef K1_FE_BOARD_GX
// PCB net -> ESP32-S3 GPIO, not module land number. This is the common map
// consumed by board startup, PCM1808 I2S1 and the PDM microphone on I2S0.
// RN_C1 stays fitted: PCM1808 is the 48 kHz BCLK/LRCK master.
// The external ADC shares these clocks but has its own ADC_DOUT input.
// PCM1808 stays 48 kHz master; the existing 48 -> 12.8 kHz path is unchanged.
#define K1_FE_I2C_SDA_PIN 2          // I2C_SDA, fitted R_B10 2.2k pull-up
#define K1_FE_I2C_SCL_PIN 1          // I2C_SCL, fitted R_B11 2.2k pull-up
#define K1_FE_HEARTBEAT_PIN 8
#define K1_FE_POWER_PERMIT_PIN 39    // current-limit selection, fitted 100k pull-down
#define K1_FE_VBUS_PG_PIN 40  // protected 5 V eFuse PG, open-drain + 10k pull-up
#define K1_FE_LED_OE_A_PIN 38  // LED_PG_A is TXU0102 active-high OE, 10k pull-up
#define K1_FE_LED_OE_B_PIN 6  // LED_PG_B is TXU0102 active-high OE, 10k pull-up
#define K1_FE_JACK_DET_PIN 42
#define K1_FE_CC1_SENSE_PIN 4  // ADC1_CH3 through R_PWR2 100k; input only
#define K1_FE_CC2_SENSE_PIN 5  // ADC1_CH4 through R_PWR59 100k; input only
#define K1_FE_ADC_SHDNZ_PIN 46  // header pin 8; keep low until the companion is qualified
#define K1_PCM1808_BCLK_PIN 47  // PCM_BCK; header pin 10; input from PCM1808
#define K1_PCM1808_LRCK_PIN 14  // PCM_LRCK; header pin 6; input from PCM1808
#define K1_PCM1808_DIN_PIN 21  // PCM_DOUT; independent of external ADC data
#define K1_FE_ADC_DOUT_PIN 45       // header pin 9; input; boot strap until reset ends
#define K1_PCM1808_NFC_CS_HOLD_PIN (-1)
#define K1_PDM_CLK_PIN 48            // MIC_CLK -> existing R_M5
#define K1_PDM_DIN_PIN 41  // MIC_DATA
#define K1_FE_NAV_RIGHT_PIN 3
#define K1_FE_NAV_PRESS_PIN 9
#define K1_FE_NAV_LEFT_PIN 10
#define K1_FE_USER3_N_PIN 11
#define K1_FE_USER1_N_PIN 12
#define K1_FE_USER2_N_PIN 13
#define K1_FE_SERVICE_TX_PIN 43
#define K1_FE_SERVICE_RX_PIN 44
#define K1_FE_BOOT_PIN 0
// GPIO7 is unused. GPIO35-37 remain reserved by N16R8 PSRAM.
// GPIO45/46 are boot straps: software cannot prove their reset-time levels.
// Do not enable an external ADC before its power/reset/harness is qualified.
#else  // legacy STUSB4500 FE profile

#ifndef K1_FE_LED_ENABLE_PIN
#define K1_FE_LED_ENABLE_PIN 1     // out, 100k pull-down R_PWR59: LED buck + both bank eFuses
#endif
#ifndef K1_FE_POWER_PERMIT_PIN
#define K1_FE_POWER_PERMIT_PIN 2   // out, 100k pull-down R_PWR35: main eFuse 3.53 A step
#endif
#ifndef K1_FE_HEARTBEAT_PIN
#define K1_FE_HEARTBEAT_PIN 5      // out, status LED D_S9 via R_S9
#endif
#ifndef K1_FE_LED_PG_A_PIN
#define K1_FE_LED_PG_A_PIN 6       // in, 10k pull-up R_PWR27
#endif
#ifndef K1_FE_LED_PG_B_PIN
#define K1_FE_LED_PG_B_PIN 7       // in, 10k pull-up R_PWR33
#endif
#ifndef K1_FE_INPUT_20V_PG_PIN
#define K1_FE_INPUT_20V_PG_PIN 38  // in, 10k pull-up R_PWR15; high = input >= 18 V
#endif
#ifndef K1_FE_PD_FAULT_N_PIN
#define K1_FE_PD_FAULT_N_PIN 39    // in, 10k pull-up R_PWR2; low = STUSB4500 fault
#endif
#ifndef K1_FE_JACK_DET_PIN
#define K1_FE_JACK_DET_PIN 40      // in, 150k R_B52 network; high = plug in (OI-06)
#endif
#ifndef K1_FE_PD_SDA_PIN
#define K1_FE_PD_SDA_PIN 41        // STUSB4500 SDA, 2.2k pull-up R_B10
#endif
#ifndef K1_FE_PD_SCL_PIN
#define K1_FE_PD_SCL_PIN 42        // STUSB4500 SCL, 2.2k pull-up R_B11
#endif
#ifndef K1_FE_STUSB4500_ADDR
#define K1_FE_STUSB4500_ADDR 0x28  // ADDR0/ADDR1 low (R3 power-connections.json "I2C0x28")
#endif

#endif  // K1_FE_BOARD_GX

// Initialize the selected physical profile. Call once from init_system(),
// after k1_pcm1808_begin(). Gx keeps the external ADC shut down until its
// configuration driver is provided, and leaves LED OEs at their fitted defaults.
void k1_fe_board_begin();

// Core 0 housekeeping: jack debounce and profile-specific power/status reads;
// prints only on state changes.
void k1_fe_board_poll(uint32_t t_now_ms);

// Render task (Core 1), once per frame: 1 Hz heartbeat. A stalled renderer
// stops the blink.
void k1_fe_heartbeat_tick(int64_t now_us);

// Called by acquire_sample_chunk() at the top of every hop. Latches and
// returns true when the PCM1808 line-in owns this hop. hold_mic (noise
// calibration running) keeps the microphone so calibration never learns line-in.
bool k1_fe_audio_line_hop_begin(bool hold_mic);

// The value latched by the last k1_fe_audio_line_hop_begin().
bool k1_fe_audio_line_active();

#ifdef K1_FE_BOARD_GX
// One atomic request token covers both LED edges. The low 16 bits are the
// estimated LED allowance; the high bits identify a particular request.
uint32_t k1_fe_gx_power_budget_snapshot();
uint16_t k1_fe_gx_led_budget_ma(uint32_t token, uint32_t requested_ma);
void k1_fe_gx_frame_submitted(uint32_t token);
#endif

// Serial: fe_status, audio_src=auto|mic|line. PD commands are legacy-profile only.
bool k1_fe_board_dispatch(const char *command_type, char *command_data);

#endif  // K1_FE_BOARD_V1
