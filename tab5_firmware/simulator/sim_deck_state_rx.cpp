/**
 * Native-SDL stub for deck_state_rx — keeps MAIN TX paths exercisable without
 * a live K1 SNAPSHOT/HELLO session. Device builds use src/deck_state_rx.cpp.
 *
 * Default: ARMED (linked demo). Pass --unarmed to sim for gated chrome stills.
 */

#include "deck_state_rx.h"

#include <stdlib.h>
#include <string.h>

namespace {
DeckLinkPhase gPhase = DECK_LINK_ARMED;
}

extern "C" {

void sim_deck_state_rx_set_phase(DeckLinkPhase phase)
{
  gPhase = phase;
}

void deck_state_rx_init(void)
{
  const char* env = getenv("DECK_SIM_PHASE");
  if (env && (!strcmp(env, "DISCONNECTED") || !strcmp(env, "unarmed"))) {
    gPhase = DECK_LINK_DISCONNECTED;
  }
}

void deck_state_rx_on_disconnect(void) { gPhase = DECK_LINK_DISCONNECTED; }
void deck_state_rx_on_identity_hint(void)
{
  if (gPhase == DECK_LINK_DISCONNECTED) gPhase = DECK_LINK_IDENTITY_ACCEPTED;
}
void deck_state_rx_on_packet(const uint8_t* /*data*/, size_t /*len*/) {}

DeckLinkPhase deck_state_rx_phase(void) { return gPhase; }
bool deck_state_rx_armed(void)
{
  return gPhase == DECK_LINK_ARMED || gPhase == DECK_LINK_LIVE;
}
bool deck_state_rx_live(void) { return gPhase == DECK_LINK_LIVE; }
uint32_t deck_state_rx_session_generation(void) { return 1; }
uint32_t deck_state_rx_revision(void) { return 1; }
uint32_t deck_state_rx_snapshot_crc_fail(void) { return 0; }
uint32_t deck_state_rx_snapshot_count_fail(void) { return 0; }
uint32_t deck_state_rx_map_mismatch(void) { return 0; }
uint32_t deck_state_rx_revision_gaps(void) { return 0; }
uint32_t deck_state_rx_stale_revisions(void) { return 0; }
void deck_state_rx_dump_status(void) {}

}  /* extern "C" */
