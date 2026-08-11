#pragma once
/**
 * tab5_build.h
 * Build-time feature gates and serial log helpers.
 *
 * The current Tab5 control transport is BLE MIDI.
 */
#include <Arduino.h>

// Simple log prefixes for transition logs
#define LOG_NET(tag, fmt, ...)   do { Serial.printf("[net] " tag " " fmt "\n", ##__VA_ARGS__); } while (0)
#define LOG_MIDI(tag, fmt, ...)  do { Serial.printf("[ble-midi] " tag " " fmt "\n", ##__VA_ARGS__); } while (0)
#define LOG_UI(tag, fmt, ...)    do { Serial.printf("[ui ] " tag " " fmt "\n", ##__VA_ARGS__); } while (0)
#define LOG_HW(tag, fmt, ...)    do { Serial.printf("[hw ] " tag " " fmt "\n", ##__VA_ARGS__); } while (0)
