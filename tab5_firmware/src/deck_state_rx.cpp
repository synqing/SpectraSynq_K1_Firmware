#include "deck_state_rx.h"
#include "deck_state.h"
#include "deck_latency.h"
#include "deck_ui_internal.h"
#include "deck_claim.h"
#include "k1_deck_identity_v1.h"
#include "k1_deck_state_v1.h"
#include "k1_claim_adv_v1.h"
#include "k1_ble_midi_map.h"

#include <Arduino.h>
#include <string.h>

#ifndef TAB5_BLE_VERBOSE_DIAG
#define TAB5_BLE_VERBOSE_DIAG 0
#endif

namespace {

static_assert(K1_BLE_MIDI_CONTROL_COUNT == 68,
              "Deck-state staging is sized for the canonical 68-control map");

constexpr char kCanonicalRegistryMd5[] = "9b5db3fbb17438367adeaceb541db03b";
constexpr uint8_t kRequiredSnapshotMembers = 18;

DeckLinkPhase gPhase = DECK_LINK_DISCONNECTED;
uint32_t gSessionGeneration = 0;
uint32_t gCommittedGeneration = 0;
uint32_t gRevision = 0;
uint32_t gSnapshotCrcFail = 0;
uint32_t gMapMismatch = 0;
uint32_t gRevisionGaps = 0;
uint32_t gSnapshotCountFail = 0;
uint32_t gStaleRevisions = 0;
DeckStateRxCounters gCounters = {};
bool gDesynchronised = false;
bool gRecoveryRequired = false;
bool gRequireNewGeneration = false;
bool gHelloAdmitted = false;
bool gSequenceValid = false;
uint16_t gLastSequence = 0;
bool gSnapshotOpen = false;
uint16_t gSnapshotItems = 0;
uint16_t gSnapshotExpected = 0;
uint32_t gSnapshotCrcAcc = 0xFFFFFFFFu;
uint32_t gSnapshotRevision = 0;
uint32_t gTransactionTouchedMs = 0;
K1DeckStateValue gSnapshotStage[K1_BLE_MIDI_CONTROL_COUNT] = {};
bool gSnapshotSeen[K1_BLE_MIDI_CONTROL_COUNT] = {};
K1DeckStateValue gDeltaStage[K1_BLE_MIDI_CONTROL_COUNT] = {};
uint8_t gReassembly[K1_DECK_STATE_MAX_PACKET] = {};
size_t gReassemblyLen = 0;
uint32_t gReassemblyTouchedMs = 0;

uint32_t crc_update(uint32_t crc, const uint8_t* data, size_t len) {
  for (size_t i = 0; i < len; ++i) {
    crc ^= data[i];
    for (int b = 0; b < 8; ++b) {
      const uint32_t mask = static_cast<uint32_t>(-(static_cast<int32_t>(crc & 1u)));
      crc = (crc >> 1) ^ (0xEDB88320u & mask);
    }
  }
  return crc;
}

bool exact_compatibility_hello(const K1DeckStateHello& hello) {
  uint8_t md5[16] = {};
  uint8_t sha[32] = {};
  const uint8_t deck_id[16] = K1_DECK_IDENTITY_BENCH_DECK_ID_INIT;
  if (k1_deck_identity_parse_hex(K1_DECK_IDENTITY_REGISTRY_MD5_HEX, md5, 16) != 0) {
    return false;
  }
  if (k1_deck_identity_parse_hex(K1_DECK_IDENTITY_LAYOUT_SHA256_HEX, sha, 32) != 0) {
    return false;
  }
  if (memcmp(hello.ble_midi_registry_md5, md5, 16) != 0) {
    return false;
  }
  if (memcmp(hello.deck16_layout_sha256, sha, 32) != 0) {
    return false;
  }
  if (hello.protocol_min != K1_DECK_STATE_VERSION ||
      hello.protocol_max != K1_DECK_STATE_VERSION ||
      (hello.flags != 0 &&
       hello.flags != K1_DECK_STATE_HELLO_FLAG_K1_UNIT_ID) ||
      hello.session_generation == 0 ||
      memcmp(hello.deck_id, deck_id, sizeof(deck_id)) != 0 ||
      hello.short_id != K1_DECK_IDENTITY_BENCH_SHORT_ID) {
    return false;
  }
  /*
   * The generated control map and the identity wire contract share the same
   * canonical registry digest. Reject a binary assembled from divergent maps.
   */
  if (strcmp(K1_BLE_MIDI_REGISTRY_MD5, kCanonicalRegistryMd5) != 0) {
    return false;
  }
  return true;
}

uint8_t expected_value_type(const K1BleMidiEntry& entry) {
  switch (entry.type) {
    case K1MIDI_PC: return K1_DECK_STATE_VT_PROGRAM;
    case K1MIDI_CC14: return K1_DECK_STATE_VT_CC14;
    case K1MIDI_CC7_BOOL: return K1_DECK_STATE_VT_BOOL;
    case K1MIDI_CC7_ENUM: return K1_DECK_STATE_VT_ENUM;
    case K1MIDI_NRPN: return K1_DECK_STATE_VT_NRPN;
    default: return 0;
  }
}

bool value_in_range(const K1BleMidiEntry& entry, const K1DeckStateValue& value) {
  switch (entry.type) {
    case K1MIDI_CC7_BOOL:
      return value.value_i32 == 0 || value.value_i32 == 1;
    case K1MIDI_CC14:
      return value.value_i32 >= 0 && value.value_i32 <= 16383;
    case K1MIDI_CC7_ENUM:
    case K1MIDI_PC:
      return value.value_i32 >= 0 && value.value_i32 <= 127;
    case K1MIDI_NRPN:
      if (entry.text_count > 0) {
        return value.value_i32 >= 0 && value.value_i32 < entry.text_count;
      }
      return value.value_i32 >= 0 && value.value_i32 <= 16383;
    default:
      return false;
  }
}

bool validate_value(const K1DeckStateValue& value, bool snapshot) {
  if (value.map_index >= K1_BLE_MIDI_CONTROL_COUNT) {
    ++gCounters.invalid_members;
    Serial.printf("[deck_state_rx] invalid member map=%u type=%u status=%u value=%ld snapshot=%u reason=map\n",
                  static_cast<unsigned>(value.map_index),
                  static_cast<unsigned>(value.value_type),
                  static_cast<unsigned>(value.status),
                  static_cast<long>(value.value_i32), snapshot ? 1U : 0U);
    return false;
  }
  const K1BleMidiEntry& entry = kK1BleMidiMap[value.map_index];
  if (value.value_type != expected_value_type(entry) ||
      value.status > K1_DECK_STATE_ST_UNAVAILABLE ||
      (snapshot && value.status != K1_DECK_STATE_ST_ACCEPTED &&
       value.status != K1_DECK_STATE_ST_CLAMPED) ||
      !value_in_range(entry, value)) {
    ++gCounters.invalid_members;
    Serial.printf("[deck_state_rx] invalid member path=%s map=%u type=%u expected=%u status=%u value=%ld snapshot=%u\n",
                  entry.path, static_cast<unsigned>(value.map_index),
                  static_cast<unsigned>(value.value_type),
                  static_cast<unsigned>(expected_value_type(entry)),
                  static_cast<unsigned>(value.status),
                  static_cast<long>(value.value_i32), snapshot ? 1U : 0U);
    return false;
  }
  return true;
}

bool is_required_snapshot_member(uint16_t index) {
  static const char* const required[] = {
      "primary.mode",       "primary.palette",      "primary.photons",
      "primary.mood",       "primary.chroma",       "primary.saturation",
      "primary.prism_count", "secondary.mode",      "secondary.palette",
      "secondary.enabled",  "secondary.photons",    "secondary.mood",
      "secondary.chroma",   "secondary.saturation", "edge.enabled",
      "director.enabled",   "scene.smart",          "vp.profile",
  };
  for (const char* path : required) {
    if (strcmp(kK1BleMidiMap[index].path, path) == 0) {
      return true;
    }
  }
  return false;
}

bool required_snapshot_members_present() {
  uint8_t found = 0;
  for (uint16_t i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
    if (is_required_snapshot_member(i)) {
      if (!gSnapshotSeen[i]) {
        return false;
      }
      ++found;
    }
  }
  return found == kRequiredSnapshotMembers;
}

void clear_transaction() {
  gSnapshotOpen = false;
  gSnapshotItems = 0;
  gSnapshotExpected = 0;
  gSnapshotCrcAcc = 0xFFFFFFFFu;
  gSnapshotRevision = 0;
  memset(gSnapshotSeen, 0, sizeof(gSnapshotSeen));
}

void request_recovery() {
  if (!gRecoveryRequired) {
    ++gCounters.recovery_requests;
  }
  gRecoveryRequired = true;
}

void fail_closed(bool snapshot_reject, bool delta_reject) {
  if (snapshot_reject) ++gCounters.snapshot_rejects;
  if (delta_reject) ++gCounters.delta_rejects;
  clear_transaction();
  gHelloAdmitted = false;
  gDesynchronised = true;
  request_recovery();
  deck_state_mark_confirmed_stale();
  gPhase = gSessionGeneration != 0 ? DECK_LINK_STATE_SYNCING
                                   : DECK_LINK_DISCONNECTED;
}

// Inverse of K1 encode_number_i32 for CC14:
//   v14 = round((value - vmin) / (vmax - vmin) * 16383)
float decode_number_f(const K1BleMidiEntry& e, int32_t value_i32) {
  if (e.type == K1MIDI_CC14) {
    const float lo = e.vmin;
    const float hi = (e.vmax > e.vmin) ? e.vmax : (e.vmin + 1.0f);
    float n = static_cast<float>(value_i32) / 16383.0f;
    if (n < 0.0f) n = 0.0f;
    if (n > 1.0f) n = 1.0f;
    return lo + n * (hi - lo);
  }
  return static_cast<float>(value_i32);
}

void apply_value(const K1DeckStateValue& v) {
  if (v.map_index >= K1_BLE_MIDI_CONTROL_COUNT) {
    return;
  }
  const K1BleMidiEntry& e = kK1BleMidiMap[v.map_index];
  // Snapshot values are authoritative. All non-ACCEPTED deltas are rejected
  // before this point because v1 carries no request correlation ID.
  if (v.status != K1_DECK_STATE_ST_ACCEPTED &&
      v.status != K1_DECK_STATE_ST_CLAMPED) return;
  DeckControlId id = DECK_CTRL_COUNT;
  bool layout_updated = false;
  if (strcmp(e.path, "primary.photons") == 0) {
    id = DECK_CTRL_PRIMARY_PHOTONS;
    deck_state_apply_confirmed_f(id, decode_number_f(e, v.value_i32));
    layout_updated = true;
  } else if (strcmp(e.path, "secondary.photons") == 0) {
    id = DECK_CTRL_SECONDARY_PHOTONS;
    deck_state_apply_confirmed_f(id, decode_number_f(e, v.value_i32));
    layout_updated = true;
  } else if (strcmp(e.path, "primary.mood") == 0) {
    id = DECK_CTRL_PRIMARY_MOOD;
    deck_state_apply_confirmed_f(id, decode_number_f(e, v.value_i32));
    layout_updated = true;
  } else if (strcmp(e.path, "secondary.mood") == 0) {
    id = DECK_CTRL_SECONDARY_MOOD;
    deck_state_apply_confirmed_f(id, decode_number_f(e, v.value_i32));
    layout_updated = true;
  } else if (strcmp(e.path, "primary.chroma") == 0) {
    id = DECK_CTRL_PRIMARY_CHROMA;
    deck_state_apply_confirmed_f(id, decode_number_f(e, v.value_i32));
    layout_updated = true;
  } else if (strcmp(e.path, "primary.saturation") == 0) {
    id = DECK_CTRL_PRIMARY_SATURATION;
    deck_state_apply_confirmed_f(id, decode_number_f(e, v.value_i32));
    layout_updated = true;
  } else if (strcmp(e.path, "primary.prism_count") == 0) {
    id = DECK_CTRL_PRIMARY_PRISM_COUNT;
    deck_state_apply_confirmed_f(id, decode_number_f(e, v.value_i32));
    layout_updated = true;
  } else if (strcmp(e.path, "secondary.chroma") == 0) {
    id = DECK_CTRL_SECONDARY_CHROMA;
    deck_state_apply_confirmed_f(id, decode_number_f(e, v.value_i32));
    layout_updated = true;
  } else if (strcmp(e.path, "secondary.saturation") == 0) {
    id = DECK_CTRL_SECONDARY_SATURATION;
    deck_state_apply_confirmed_f(id, decode_number_f(e, v.value_i32));
    layout_updated = true;
  } else if (strcmp(e.path, "primary.mode") == 0) {
    id = DECK_CTRL_PRIMARY_MODE;
    deck_state_apply_confirmed_u8(id, static_cast<uint8_t>(v.value_i32 & 0xFF));
    layout_updated = true;
  } else if (strcmp(e.path, "secondary.mode") == 0) {
    id = DECK_CTRL_SECONDARY_MODE;
    deck_state_apply_confirmed_u8(id, static_cast<uint8_t>(v.value_i32 & 0xFF));
    layout_updated = true;
  } else if (strcmp(e.path, "primary.palette") == 0) {
    id = DECK_CTRL_PRIMARY_PALETTE;
    deck_state_apply_confirmed_u8(id, static_cast<uint8_t>(v.value_i32 & 0xFF));
    layout_updated = true;
  } else if (strcmp(e.path, "secondary.palette") == 0) {
    id = DECK_CTRL_SECONDARY_PALETTE;
    deck_state_apply_confirmed_u8(id, static_cast<uint8_t>(v.value_i32 & 0xFF));
    layout_updated = true;
  } else if (strcmp(e.path, "secondary.enabled") == 0) {
    id = DECK_CTRL_SECONDARY_ENABLED;
    deck_state_apply_confirmed_u8(id, v.value_i32 ? 1 : 0);
    layout_updated = true;
  } else {
    // Full 71-map: confirmed authority for non-layout paths (no DeckControlId slot).
    deck_state_bump_confirmed();
    /* Soft-key lamps + sheet bool reconcile from SNAPSHOT/DELTA (not local TX). */
    if (strcmp(e.path, "edge.enabled") == 0) {
      deck_ui_set_key_lamp(DECK_SHEET_EDGE, v.value_i32 != 0);
      deck_ui_sheets_apply_bool(e.path, v.value_i32 != 0);
    } else if (strcmp(e.path, "director.enabled") == 0) {
      deck_ui_set_key_lamp(DECK_SHEET_DIRECTOR, v.value_i32 != 0);
      deck_ui_sheets_apply_bool(e.path, v.value_i32 != 0);
    } else if (strcmp(e.path, "director.assist") == 0) {
      deck_ui_sheets_apply_bool(e.path, v.value_i32 != 0);
    } else if (strcmp(e.path, "director.autonomy") == 0) {
      deck_ui_sheets_apply_bool(e.path, v.value_i32 != 0);
    } else if (strcmp(e.path, "scene.smart") == 0) {
      deck_ui_set_key_lamp(DECK_SHEET_SMART, v.value_i32 != 0);
    } else if (strcmp(e.path, "vp.profile") == 0) {
      deck_ui_set_key_lamp(DECK_SHEET_RENDER, v.value_i32 != 0);
    }
  }
  deck_latency_note_t2(id, v.map_index, v.value_i32);
#if TAB5_BLE_VERBOSE_DIAG
  Serial.printf("DECK_MAP_CONF: path=%s map=%u status=%u val=%ld layout=%u\n",
                e.path,
                static_cast<unsigned>(v.map_index),
                static_cast<unsigned>(v.status),
                static_cast<long>(v.value_i32),
                layout_updated ? 1U : 0U);
#else
  (void)layout_updated;
#endif
}

void handle_record(const K1DeckStateRecordView& rec) {
  switch (rec.type) {
    case K1_DECK_STATE_REC_HELLO: {
      K1DeckStateHello hello = {};
      if (k1_deck_state_decode_hello_payload(rec.payload, rec.payload_len, &hello) !=
          K1_DECK_STATE_OK) {
        gPhase = DECK_LINK_DISCONNECTED;
        return;
      }
      if (!exact_compatibility_hello(hello) || rec.flags != 0) {
        ++gMapMismatch;
        gPhase = DECK_LINK_DISCONNECTED;
        gSequenceValid = false;
        return;
      }
      /* Post-connect unit proof (C1 property / SURVIVORS kill #2). */
      deck_claim_clear_proven_unit();
      if ((hello.flags & K1_DECK_STATE_HELLO_FLAG_K1_UNIT_ID) != 0) {
        if (rec.payload_len <
            K1_DECK_STATE_HELLO_PAYLOAD_SIZE + K1_DECK_STATE_HELLO_UNIT_ID_EXT_LEN) {
          ++gMapMismatch;
          gPhase = DECK_LINK_DISCONNECTED;
          return;
        }
        const uint32_t unit = k1_claim_adv_v1_read_be32(
            rec.payload + K1_DECK_STATE_HELLO_PAYLOAD_SIZE);
        deck_claim_set_proven_unit(unit);
        Serial.printf("[deck_state_rx] HELLO unit_proof=%08X\n",
                      (unsigned)unit);
      }
      if (gRequireNewGeneration && hello.session_generation == gSessionGeneration) {
        ++gCounters.decode_errors;
        fail_closed(false, false);
        return;
      }
      clear_transaction();
      if (hello.session_generation != gSessionGeneration) {
        deck_state_clear_pending_all();
      }
      gSessionGeneration = hello.session_generation;
      gRequireNewGeneration = false;
      gHelloAdmitted = true;
      gDesynchronised = true;
      deck_state_mark_confirmed_stale();
      gPhase = DECK_LINK_STATE_SYNCING;
      break;
    }
    case K1_DECK_STATE_REC_SNAPSHOT_BEGIN: {
      if (gPhase != DECK_LINK_STATE_SYNCING || !gHelloAdmitted || gSnapshotOpen ||
          rec.flags != 0 || rec.payload_len != 0) {
        fail_closed(true, false);
        return;
      }
      if (gCommittedGeneration == gSessionGeneration &&
          static_cast<int32_t>(rec.revision - gRevision) < 0) {
        ++gStaleRevisions;
        fail_closed(true, false);
        return;
      }
      gSnapshotOpen = true;
      gSnapshotItems = 0;
      gSnapshotExpected = 0;
      gSnapshotCrcAcc = 0xFFFFFFFFu;
      gSnapshotRevision = rec.revision;
      gTransactionTouchedMs = millis();
      memset(gSnapshotSeen, 0, sizeof(gSnapshotSeen));
      gPhase = DECK_LINK_STATE_SYNCING;
      break;
    }
    case K1_DECK_STATE_REC_STATE_ITEM: {
      if (!gSnapshotOpen || rec.flags != 0 ||
          rec.revision != gSnapshotRevision ||
          rec.payload_len != K1_DECK_STATE_VALUE_PAYLOAD_SIZE) {
        fail_closed(true, false);
        return;
      }
      K1DeckStateValue value = {};
      if (k1_deck_state_decode_value_payload(rec.payload, rec.payload_len, &value) !=
          K1_DECK_STATE_OK) {
        ++gCounters.decode_errors;
        fail_closed(true, false);
        return;
      }
      if (!validate_value(value, true)) {
        fail_closed(true, false);
        return;
      }
      if (gSnapshotSeen[value.map_index]) {
        ++gCounters.duplicate_members;
        fail_closed(true, false);
        return;
      }
      if (gSnapshotItems >= K1_BLE_MIDI_CONTROL_COUNT) {
        ++gSnapshotCountFail;
        fail_closed(true, false);
        return;
      }
      gSnapshotStage[value.map_index] = value;
      gSnapshotSeen[value.map_index] = true;
      gSnapshotCrcAcc = crc_update(gSnapshotCrcAcc, rec.payload, rec.payload_len);
      ++gSnapshotItems;
      gTransactionTouchedMs = millis();
      break;
    }
    case K1_DECK_STATE_REC_SNAPSHOT_END: {
      if (!gSnapshotOpen || rec.flags != 0 || rec.payload_len != 6 ||
          rec.revision != gSnapshotRevision) {
        ++gSnapshotCountFail;
        fail_closed(true, false);
        return;
      }
      const uint16_t count = static_cast<uint16_t>(rec.payload[0] | (rec.payload[1] << 8));
      const uint32_t crc = static_cast<uint32_t>(rec.payload[2]) |
                           (static_cast<uint32_t>(rec.payload[3]) << 8) |
                           (static_cast<uint32_t>(rec.payload[4]) << 16) |
                           (static_cast<uint32_t>(rec.payload[5]) << 24);
      gSnapshotExpected = count;
      const uint32_t final_crc = gSnapshotCrcAcc ^ 0xFFFFFFFFu;
      if (count != gSnapshotItems || count > K1_BLE_MIDI_CONTROL_COUNT ||
          !required_snapshot_members_present()) {
        ++gSnapshotCountFail;
        fail_closed(true, false);
        return;
      }
      if (crc != final_crc) {
        ++gSnapshotCrcFail;
        fail_closed(true, false);
        return;
      }
      /* First mutation point: the complete snapshot is now validated. */
      for (uint16_t i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
        if (gSnapshotSeen[i]) apply_value(gSnapshotStage[i]);
      }
      gRevision = gSnapshotRevision;
      gCommittedGeneration = gSessionGeneration;
      clear_transaction();
      deck_state_clear_confirmed_stale();
      /* Claim unit proof must match before ARMED TX (kill #3). */
      const uint8_t claim_mode = deck_claim_mode();
      const uint32_t proven = deck_claim_proven_unit();
      if (proven == 0) {
        Serial.println("[deck_state_rx] ARMED blocked: missing unit proof");
        fail_closed(true, false);
        return;
      }
      if (claim_mode == K1_CLAIM_MODE_UNIT &&
          proven != deck_claim_active_unit()) {
        Serial.printf("[deck_state_rx] ARMED blocked: proven=%08X claim=%08X\n",
                      (unsigned)proven, (unsigned)deck_claim_active_unit());
        fail_closed(true, false);
        return;
      }
      if (claim_mode == K1_CLAIM_MODE_NONE) {
        Serial.println("[deck_state_rx] ARMED blocked: claim NONE");
        fail_closed(true, false);
        return;
      }
      gPhase = DECK_LINK_ARMED;
      gDesynchronised = false;
      gRecoveryRequired = false;
      ++gCounters.snapshot_commits;
      break;
    }
    case K1_DECK_STATE_REC_DELTA_BATCH: {
      if (gDesynchronised || gCommittedGeneration != gSessionGeneration ||
          (gPhase != DECK_LINK_ARMED && gPhase != DECK_LINK_LIVE)) {
        fail_closed(false, true);
        return;
      }
      if (rec.flags != 0 || rec.payload_len == 0 ||
          (rec.payload_len % K1_DECK_STATE_VALUE_PAYLOAD_SIZE) != 0) {
        fail_closed(false, true);
        return;
      }
      const size_t value_count = rec.payload_len / K1_DECK_STATE_VALUE_PAYLOAD_SIZE;
      if (value_count > K1_BLE_MIDI_CONTROL_COUNT) {
        fail_closed(false, true);
        return;
      }
      const int32_t revision_delta = static_cast<int32_t>(rec.revision - gRevision);
      if (revision_delta <= 0) {
        ++gStaleRevisions;
        ++gCounters.delta_rejects;
        return;
      }
      if (rec.revision != static_cast<uint32_t>(gRevision + 1u)) {
        ++gRevisionGaps;
        fail_closed(false, true);
        return;
      }
      bool seen[K1_BLE_MIDI_CONTROL_COUNT] = {};
      size_t off = 0;
      size_t staged = 0;
      while (off < rec.payload_len) {
        K1DeckStateValue value = {};
        if (k1_deck_state_decode_value_payload(rec.payload + off,
                                               K1_DECK_STATE_VALUE_PAYLOAD_SIZE,
                                               &value) != K1_DECK_STATE_OK) {
          ++gCounters.decode_errors;
          fail_closed(false, true);
          return;
        }
        if (!validate_value(value, false)) {
          fail_closed(false, true);
          return;
        }
        /* Protocol v1 has no request ID. Applying a delayed CLAMPED result
         * could erase a newer pending request, and UNAVAILABLE has no
         * authoritative value. Resynchronise instead of guessing. */
        if (value.status != K1_DECK_STATE_ST_ACCEPTED) {
          fail_closed(false, true);
          return;
        }
        if (seen[value.map_index]) {
          ++gCounters.duplicate_members;
          fail_closed(false, true);
          return;
        }
        seen[value.map_index] = true;
        gDeltaStage[staged++] = value;
        off += K1_DECK_STATE_VALUE_PAYLOAD_SIZE;
      }
      /* First mutation point: the complete delta batch is now validated. */
      for (size_t i = 0; i < staged; ++i) apply_value(gDeltaStage[i]);
      gRevision = rec.revision;
      gPhase = DECK_LINK_LIVE;
      ++gCounters.delta_commits;
      break;
    }
    case K1_DECK_STATE_REC_HEALTH:
      if (gSnapshotOpen) fail_closed(true, false);
      break;
    default:
      ++gCounters.decode_errors;
      fail_closed(gSnapshotOpen, false);
      break;
  }
}

}  // namespace

void deck_state_rx_init(void) {
  gPhase = DECK_LINK_DISCONNECTED;
  gSessionGeneration = 0;
  gRevision = 0;
  gSnapshotCrcFail = 0;
  gMapMismatch = 0;
  gRevisionGaps = 0;
  gSnapshotCountFail = 0;
  gStaleRevisions = 0;
  memset(&gCounters, 0, sizeof(gCounters));
  gCommittedGeneration = 0;
  gDesynchronised = false;
  gRecoveryRequired = false;
  gRequireNewGeneration = false;
  gHelloAdmitted = false;
  gSequenceValid = false;
  gReassemblyLen = 0;
  clear_transaction();
}

static const char* phase_name(DeckLinkPhase p) {
  switch (p) {
    case DECK_LINK_DISCONNECTED: return "DISCONNECTED";
    case DECK_LINK_CONNECTED_UNAUTHORISED: return "CONNECTED_UNAUTHORISED";
    case DECK_LINK_IDENTITY_ACCEPTED: return "IDENTITY_ACCEPTED";
    case DECK_LINK_STATE_SYNCING: return "STATE_SYNCING";
    case DECK_LINK_ARMED: return "ARMED";
    case DECK_LINK_LIVE: return "LIVE";
    default: return "UNKNOWN";
  }
}

void deck_state_rx_on_disconnect(void) {
  gPhase = DECK_LINK_DISCONNECTED;
  clear_transaction();
  gReassemblyLen = 0;
  gSequenceValid = false;
  gDesynchronised = true;
  gRecoveryRequired = false;
  gRequireNewGeneration = gSessionGeneration != 0;
  gHelloAdmitted = false;
  deck_claim_clear_proven_unit();
  deck_state_mark_confirmed_stale();
  // No stale pending survives into a new session — operator must act after re-link.
  deck_state_clear_pending_all();
  Serial.println("[deck_rx] disconnect: pending cleared");
}

void deck_state_rx_on_identity_hint(void) {
  if (gPhase == DECK_LINK_DISCONNECTED) {
    gPhase = DECK_LINK_IDENTITY_ACCEPTED;
  }
}

void deck_state_rx_on_packet(const uint8_t* data, size_t len) {
  if (data == nullptr || len == 0) {
    return;
  }
  // ATT MTU fallback: K1 may chunk a K1DS packet across multiple writes.
  // Reassemble until header payload_len is satisfied, then parse.
  if (len >= 4 && data[0] == 'K' && data[1] == '1' && data[2] == 'D' &&
      data[3] == 'S') {
    if (gReassemblyLen != 0) {
      deck_state_rx_on_ingress_loss("new frame before prior completion");
    }
    gReassemblyLen = 0;
  }
  if (gReassemblyLen == 0 &&
      !(len >= 4 && data[0] == 'K' && data[1] == '1' && data[2] == 'D' &&
        data[3] == 'S')) {
    deck_state_rx_on_ingress_loss("orphan packet fragment");
    return;
  }
  if (gReassemblyLen + len > sizeof(gReassembly)) {
    deck_state_rx_on_ingress_loss("packet exceeds bounded reassembly");
    return;
  }
  memcpy(gReassembly + gReassemblyLen, data, len);
  gReassemblyLen += len;
  gReassemblyTouchedMs = millis();

  while (gReassemblyLen >= K1_DECK_STATE_PACKET_HEADER_SIZE) {
    if (!(gReassembly[0] == 'K' && gReassembly[1] == '1' &&
          gReassembly[2] == 'D' && gReassembly[3] == 'S')) {
      deck_state_rx_on_ingress_loss("invalid packet magic");
      return;
    }
    const uint16_t payload_len = static_cast<uint16_t>(
        gReassembly[10] | (static_cast<uint16_t>(gReassembly[11]) << 8));
    const size_t need =
        static_cast<size_t>(K1_DECK_STATE_PACKET_HEADER_SIZE) + payload_len;
    if (need > sizeof(gReassembly)) {
      deck_state_rx_on_ingress_loss("declared packet length exceeds bound");
      return;
    }
    if (gReassemblyLen < need) {
      return;  // wait for more ATT chunks
    }
    K1DeckStatePacketHeader hdr = {};
    const uint8_t* blob = nullptr;
    size_t blob_len = 0;
    const K1DeckStateStatus st =
        k1_deck_state_parse_packet(gReassembly, need, &hdr, &blob, &blob_len);
    if (st == K1_DECK_STATE_ERR_CRC) {
      ++gCounters.packet_crc_fail;
      fail_closed(gSnapshotOpen, false);
    } else if (st == K1_DECK_STATE_OK) {
      size_t cursor = 0;
      K1DeckStateRecordView rec = {};
      const bool one_record = hdr.record_count == 1 && gReassembly[5] == 0 &&
                              gReassembly[7] == 0 &&
                              k1_deck_state_next_record(blob, blob_len, &cursor, &rec) ==
                                  K1_DECK_STATE_OK &&
                              cursor == blob_len;
      if (!one_record) {
        ++gCounters.decode_errors;
        fail_closed(gSnapshotOpen, false);
      } else if (rec.type == K1_DECK_STATE_REC_HELLO) {
        /* HELLO establishes a fresh packet-sequence baseline for its session. */
        gLastSequence = hdr.sequence;
        gSequenceValid = true;
        handle_record(rec);
      } else if (!gSequenceValid ||
                 hdr.sequence != static_cast<uint16_t>(gLastSequence + 1u)) {
        ++gCounters.packet_sequence_fail;
        fail_closed(gSnapshotOpen, rec.type == K1_DECK_STATE_REC_DELTA_BATCH);
      } else {
        gLastSequence = hdr.sequence;
        handle_record(rec);
      }
    } else {
      ++gCounters.decode_errors;
      fail_closed(gSnapshotOpen, false);
    }
    // Shift any leftover bytes (start of next packet).
    const size_t remain = gReassemblyLen - need;
    if (remain > 0) {
      memmove(gReassembly, gReassembly + need, remain);
    }
    gReassemblyLen = remain;
  }
}

void deck_state_rx_on_ingress_loss(const char* reason) {
  ++gCounters.ingress_losses;
  gReassemblyLen = 0;
  fail_closed(gSnapshotOpen, false);
#if TAB5_BLE_VERBOSE_DIAG
  Serial.printf("[deck_rx] ingress loss: %s\n", reason != nullptr ? reason : "unknown");
#else
  (void)reason;
#endif
}

void deck_state_rx_tick(uint32_t now_ms) {
  const bool packet_timed_out =
      gReassemblyLen != 0 &&
      static_cast<uint32_t>(now_ms - gReassemblyTouchedMs) >=
          DECK_STATE_RX_INCOMPLETE_TIMEOUT_MS;
  const bool snapshot_timed_out =
      gSnapshotOpen &&
      static_cast<uint32_t>(now_ms - gTransactionTouchedMs) >=
          DECK_STATE_RX_INCOMPLETE_TIMEOUT_MS;
  if (packet_timed_out || snapshot_timed_out) {
    ++gCounters.incomplete_timeouts;
    deck_state_rx_on_ingress_loss("incomplete transaction timeout");
  }
}

bool deck_state_rx_desynchronised(void) { return gDesynchronised; }
bool deck_state_rx_recovery_required(void) { return gRecoveryRequired; }
void deck_state_rx_clear_recovery_request(void) { gRecoveryRequired = false; }

DeckLinkPhase deck_state_rx_phase(void) { return gPhase; }
bool deck_state_rx_armed(void) {
  return gPhase == DECK_LINK_ARMED || gPhase == DECK_LINK_LIVE;
}
bool deck_state_rx_live(void) { return gPhase == DECK_LINK_LIVE; }
uint32_t deck_state_rx_session_generation(void) { return gSessionGeneration; }
uint32_t deck_state_rx_revision(void) { return gRevision; }
uint32_t deck_state_rx_snapshot_crc_fail(void) { return gSnapshotCrcFail; }
uint32_t deck_state_rx_snapshot_count_fail(void) { return gSnapshotCountFail; }
uint32_t deck_state_rx_map_mismatch(void) { return gMapMismatch; }
uint32_t deck_state_rx_revision_gaps(void) { return gRevisionGaps; }
uint32_t deck_state_rx_stale_revisions(void) { return gStaleRevisions; }
void deck_state_rx_counters(DeckStateRxCounters* out) {
  if (out != nullptr) *out = gCounters;
}

void deck_state_rx_dump_status(void) {
  Serial.printf(
      "DECK_RX: phase=%s armed=%u live=%u gen=%lu rev=%lu "
      "crc_fail=%lu count_fail=%lu map_mismatch=%lu gaps=%lu stale=%lu "
      "desync=%u recovery=%u confirmed_stale=%u snap_open=%u items=%u "
      "snap_commit=%lu delta_commit=%lu snap_reject=%lu delta_reject=%lu "
      "seq_fail=%lu decode=%lu invalid=%lu ingress_loss=%lu timeout=%lu\n",
      phase_name(gPhase),
      deck_state_rx_armed() ? 1U : 0U,
      deck_state_rx_live() ? 1U : 0U,
      static_cast<unsigned long>(gSessionGeneration),
      static_cast<unsigned long>(gRevision),
      static_cast<unsigned long>(gSnapshotCrcFail),
      static_cast<unsigned long>(gSnapshotCountFail),
      static_cast<unsigned long>(gMapMismatch),
      static_cast<unsigned long>(gRevisionGaps),
      static_cast<unsigned long>(gStaleRevisions),
      gDesynchronised ? 1U : 0U,
      gRecoveryRequired ? 1U : 0U,
      deck_state_confirmed_stale() ? 1U : 0U,
      gSnapshotOpen ? 1U : 0U,
      static_cast<unsigned>(gSnapshotItems),
      static_cast<unsigned long>(gCounters.snapshot_commits),
      static_cast<unsigned long>(gCounters.delta_commits),
      static_cast<unsigned long>(gCounters.snapshot_rejects),
      static_cast<unsigned long>(gCounters.delta_rejects),
      static_cast<unsigned long>(gCounters.packet_sequence_fail),
      static_cast<unsigned long>(gCounters.decode_errors),
      static_cast<unsigned long>(gCounters.invalid_members),
      static_cast<unsigned long>(gCounters.ingress_losses),
      static_cast<unsigned long>(gCounters.incomplete_timeouts));
}
