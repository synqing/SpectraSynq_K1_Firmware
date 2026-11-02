#pragma once

// K1 Founders' Edition board support (env k1_fe only, K1_FE_BOARD_V1).
//
// Board truth: ~/Workspace_Management/Software/K1-FE-Board/FE-BOARD-BRIEF.md
// ("S3 pins") and OPEN-ITEMS.md OI-02/03/05/06/08/09/11/15/19. The board is the
// authority over these defaults.
//
// What this module owns:
//   - FE board detection: the STUSB4500 PD sink must ACK on I2C (GPIO41/42).
//     Every FE-only output (LED_ENABLE, POWER_PERMIT, heartbeat) stays an input
//     unless it does, so this image is passive on the Main RPL bench devkit,
//     where GPIO2/4-7 carry the parked ST25 NFC test board.
//   - Power policy (OI-08/OI-09): POWER_PERMIT then LED_ENABLE go high only
//     while INPUT_20V_PG is high; both drop the moment it falls. On 5 V-only
//     USB the LEDs stay dark and the serial log says why. LED_PG_A/B are read
//     back and logged.
//   - Audio source (Captain ruling 1 Sep 2026): 3.5 mm insertion (JACK_DET
//     GPIO40 high) hands AP ingress to the PCM1808 canonical path; removal
//     returns it to the IM69D130. No other automatic switching.
//   - Heartbeat LED on GPIO5 (OI-19): 1 Hz, toggled from the render task.
//   - STUSB4500 NVM tool (OI-11): `:pd_nvm_write` programs 5 V 0.5 A /
//     20 V 3 A / 20 V 5 A once, verifies by read-back, prints PASS/FAIL.

#ifdef K1_FE_BOARD_V1

#include <stdint.h>

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

// Detect the board and apply the boot power state. Call once from
// init_system(), after k1_pcm1808_begin().
void k1_fe_board_begin();

// Core 0 loop housekeeping: jack debounce and power policy. Cheap GPIO reads;
// prints only on state changes.
void k1_fe_board_poll(uint32_t t_now_ms);

// Render task (Core 1), once per frame: 1 Hz heartbeat. A stalled renderer
// stops the blink.
void k1_fe_heartbeat_tick(int64_t now_us);

// Called by acquire_sample_chunk() at the top of every hop. Latches and
// returns true when the PCM1808 line-in owns this hop.
bool k1_fe_audio_line_hop_begin();

// The value latched by the last k1_fe_audio_line_hop_begin().
bool k1_fe_audio_line_active();

// Serial: fe_status, pd_status, pd_nvm_write, audio_src=auto|mic|line.
bool k1_fe_board_dispatch(const char *command_type, char *command_data);

#endif  // K1_FE_BOARD_V1
