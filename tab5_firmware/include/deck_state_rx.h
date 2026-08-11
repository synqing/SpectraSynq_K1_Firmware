#pragma once

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
  DECK_LINK_DISCONNECTED = 0,
  DECK_LINK_CONNECTED_UNAUTHORISED,
  DECK_LINK_IDENTITY_ACCEPTED,
  DECK_LINK_STATE_SYNCING,
  DECK_LINK_ARMED,
  DECK_LINK_LIVE,
} DeckLinkPhase;

void deck_state_rx_init(void);
void deck_state_rx_on_disconnect(void);
void deck_state_rx_on_identity_hint(void);  /* optional; Tab5 peripheral side */

/** Feed one GATT write payload from K1 (K1DS packet). */
void deck_state_rx_on_packet(const uint8_t* data, size_t len);

DeckLinkPhase deck_state_rx_phase(void);
bool deck_state_rx_armed(void);
bool deck_state_rx_live(void);

uint32_t deck_state_rx_session_generation(void);
uint32_t deck_state_rx_revision(void);
uint32_t deck_state_rx_snapshot_crc_fail(void);
uint32_t deck_state_rx_snapshot_count_fail(void);
uint32_t deck_state_rx_map_mismatch(void);
uint32_t deck_state_rx_revision_gaps(void);
uint32_t deck_state_rx_stale_revisions(void);

/** One-line proof dump: phase/armed/revision/counters. */
void deck_state_rx_dump_status(void);

#ifdef __cplusplus
}
#endif
