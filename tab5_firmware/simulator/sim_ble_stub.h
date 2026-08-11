#pragma once
/** Simulator-only handles onto the BleMidiTransport stub + fake-transport log. */

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Pretend a BLE central is attached, so the LINK lamp and RSSI read live. */
void sim_ble_set_linked(bool linked);
bool sim_ble_is_linked(void);

/** Echo every send*() call to stdout. Off by default: continuous controls TX at 30 Hz. */
void sim_ble_set_verbose(bool verbose);

/** Fake peripheral-side RSSI reported while linked. */
void sim_ble_set_rssi(int8_t dbm);

/** Count of send*() calls accepted since launch — cheap sanity signal. */
uint32_t sim_ble_tx_count(void);

/** Clear the deterministic TX frame ring. */
void sim_ble_frame_log_clear(void);

/** Number of captured frames since last clear (capped by ring size). */
uint32_t sim_ble_frame_log_count(void);

/**
 * Dump captured frames as JSON Lines to path.
 * Returns false on I/O failure. Empty log still writes a valid empty array file.
 */
bool sim_ble_dump_frames_json(const char* path);

/**
 * When set, the next matching mapped send for `path` returns false (fail-closed tests).
 * Pass nullptr to clear. Exact string match on the map path.
 */
void sim_ble_fail_next_path(const char* path);

/** Apply a named deterministic fixture (link/rssi/seed counts). Unknown → false. */
bool sim_ble_apply_fixture(const char* name);

#ifdef __cplusplus
}
#endif
