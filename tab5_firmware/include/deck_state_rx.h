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

/** Bounded health surface retained in production (no per-value logging). */
typedef struct {
  uint32_t snapshot_commits;
  uint32_t delta_commits;
  uint32_t snapshot_rejects;
  uint32_t delta_rejects;
  uint32_t packet_crc_fail;
  uint32_t packet_sequence_fail;
  uint32_t decode_errors;
  uint32_t duplicate_members;
  uint32_t invalid_members;
  uint32_t ingress_losses;
  uint32_t incomplete_timeouts;
  uint32_t recovery_requests;
} DeckStateRxCounters;

/** Maximum quiet interval allowed for an incomplete packet or snapshot. */
#define DECK_STATE_RX_INCOMPLETE_TIMEOUT_MS 1500u

void deck_state_rx_init(void);
void deck_state_rx_on_disconnect(void);
void deck_state_rx_on_identity_hint(void);  /* optional; Tab5 peripheral side */

/** Feed one GATT write payload from K1 (K1DS packet). */
void deck_state_rx_on_packet(const uint8_t* data, size_t len);

/**
 * Loop-owned loss/recovery hooks. Any relevant ingress loss fails closed and
 * preserves the last committed values while disarming further deltas.
 */
void deck_state_rx_on_ingress_loss(const char* reason);
void deck_state_rx_tick(uint32_t now_ms);
bool deck_state_rx_desynchronised(void);
bool deck_state_rx_recovery_required(void);
void deck_state_rx_clear_recovery_request(void);

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
void deck_state_rx_counters(DeckStateRxCounters* out);

/** One-line proof dump: phase/armed/revision/counters. */
void deck_state_rx_dump_status(void);

#ifdef __cplusplus
}
#endif
