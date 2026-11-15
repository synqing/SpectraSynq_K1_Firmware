#pragma once

// K1-FE-S31-Gx2 carrier + Waveshare ESP32-S31-Zero: carrier net -> ESP32-S31 GPIO.
// Included from k1_fe_board.h when K1_PLATFORM_S31 (targets/esp32s31) is defined.
//
// Source of every number below (read-only, 15 Nov 2026):
//  - Carrier: the ordered board file ~/Downloads/K1-FE-S31-Gx2_black-gold-v6.epro2
//    (sha256 5769d7949f77f21c1c3fa91ca257ab5fcecef8d75bbdcb4db2cf16361c2e1452), socket J_S31
//    pad -> net (PAD_NET records). The Zero plugs into J_S31 by its 40-pin connector J2;
//    J_S31 pad n mates Zero contact n (3V3/5V/GND/USB pads line up).
//  - Zero: ESP32-S31-Zero schematic p1, J2 contact -> GPIO.
//  - Evidence and per-pin verdicts: docs/forensics/runtime-evidence/20261115-s31-port/.
//
// K1_FE_PIN_NC: the ordered carrier does not connect this net to any S31 pin (no J_S31
// pad, no copper ending on one). Firmware leaves it alone; the function needs a wire fix.

#define K1_FE_PIN_NC (-1)

#define K1_FE_I2C_SDA_PIN K1_FE_PIN_NC      // I2C_SDA reaches only J_ADC + R_B10
#define K1_FE_I2C_SCL_PIN K1_FE_PIN_NC      // I2C_SCL reaches only J_ADC + R_B11
#define K1_FE_HEARTBEAT_PIN K1_FE_PIN_NC    // HEARTBEAT has no pads on the board
#define K1_FE_POWER_PERMIT_PIN 11           // J_S31.14, R_PWR35 pull-down
#define K1_FE_VBUS_PG_PIN 17                // J_S31.26
#define K1_FE_LED_OE_A_PIN 21               // J_S31.31 LED_N_OE: U_B6 OE, R_PWR27 pull-DOWN
#define K1_FE_LED_OE_B_PIN 54               // J_S31.40 LED_S_OE: U_B7 OE, R_PWR33 pull-DOWN
#define K1_FE_JACK_DET_PIN 12               // J_S31.16
#define K1_FE_CC1_SENSE_PIN K1_FE_PIN_NC    // CC1_SENSE reaches only R_PWR2
#define K1_FE_CC2_SENSE_PIN K1_FE_PIN_NC    // CC2_SENSE reaches only R_PWR59
#define K1_FE_ADC_SHDNZ_PIN 35              // J_S31.36
#define K1_PCM1808_BCLK_PIN 19              // J_S31.30 PCM_BCK (input from PCM1808)
#define K1_PCM1808_LRCK_PIN K1_FE_PIN_NC    // PCM_LRCK reaches only J_ADC + RN_C1
#define K1_PCM1808_DIN_PIN K1_FE_PIN_NC     // PCM_DOUT reaches only RN_C1
#define K1_FE_ADC_DOUT_PIN K1_FE_PIN_NC     // ADC_DOUT reaches only J_ADC
#define K1_PCM1808_NFC_CS_HOLD_PIN (-1)
#define K1_PDM_CLK_PIN 20                   // J_S31.29 MIC_CLK (SDIO pad group, 3.3 V at reset)
#define K1_PDM_DIN_PIN 16                   // J_S31.24 MIC_DATA
#define K1_FE_NAV_RIGHT_PIN 13              // J_S31.18
#define K1_FE_NAV_PRESS_PIN 15              // J_S31.22
#define K1_FE_NAV_LEFT_PIN 8                // J_S31.8
#define K1_FE_USER3_N_PIN 14                // J_S31.20 SW_USER3_N
#define K1_FE_USER1_N_PIN K1_FE_PIN_NC      // SW_USER1_N reaches only SW_USER1 + R_CTRL4
#define K1_FE_USER2_N_PIN K1_FE_PIN_NC      // SW_USER2_N reaches only SW_USER2 + R_CTRL5
#define K1_FE_SERVICE_TX_PIN K1_FE_PIN_NC   // no service UART on the carrier socket
#define K1_FE_SERVICE_RX_PIN K1_FE_PIN_NC
#define K1_FE_BOOT_PIN 61                   // Zero BOOT button (strap); not on J_S31

// LED data, WS2816 split feeds: north P_LED_N = LED0/LED1 through U_B6, south P_LED_S =
// LED2/LED3 through U_B7. North pairs with OE_A (as the S3 Gx board), so north = primary.
// DIN-A/DIN-B order inside an edge follows the connector pin order (pin 3 then pin 4);
// UNVERIFIED until an LED bar exists (no bar board has been built).
#define K1_S31_LED_PRIMARY_DIN_A_PIN 22     // J_S31.33 LED0_MCU -> P_LED_N.3
#define K1_S31_LED_PRIMARY_DIN_B_PIN 23     // J_S31.35 LED1_MCU -> P_LED_N.4
#define K1_S31_LED_SECONDARY_DIN_A_PIN 25   // J_S31.39 LED2_MCU -> P_LED_S.3
#define K1_S31_LED_SECONDARY_DIN_B_PIN 24   // J_S31.37 LED3_MCU -> P_LED_S.4

// On the S3 Gx board the two LED buffer enables have 10k pull-ups (enabled from power-on).
// Gx2 pulls them DOWN, so the S31 firmware drives them high at board start to keep the
// same behaviour (k1_fe_board.cpp).
#define K1_S31_LED_OE_DRIVE_HIGH 1
