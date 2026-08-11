#include "deck_state_rx.h"
#include "deck_state.h"
#include "deck_latency.h"
#include "deck_ui_internal.h"
#include "k1_deck_identity_v1.h"
#include "k1_deck_state_v1.h"
#include "k1_ble_midi_map.h"

#include <Arduino.h>
#include <string.h>

namespace {

DeckLinkPhase gPhase = DECK_LINK_DISCONNECTED;
uint32_t gSessionGeneration = 0;
uint32_t gRevision = 0;
uint32_t gSnapshotCrcFail = 0;
uint32_t gMapMismatch = 0;
uint32_t gRevisionGaps = 0;
uint32_t gSnapshotCountFail = 0;
uint32_t gStaleRevisions = 0;
bool gSnapshotOpen = false;
uint16_t gSnapshotItems = 0;
uint16_t gSnapshotExpected = 0;
uint32_t gSnapshotCrcAcc = 0xFFFFFFFFu;

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

bool digests_match(const K1DeckStateHello& hello) {
  uint8_t md5[16] = {};
  uint8_t sha[32] = {};
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
  // Host map header string must agree with locked MD5.
  if (strcmp(K1_BLE_MIDI_REGISTRY_MD5, K1_DECK_IDENTITY_REGISTRY_MD5_HEX) != 0) {
    return false;
  }
  return true;
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
  // Authority confirm: ACCEPTED/CLAMPED only. REJECTED must not promote pending.
  if (v.map_index >= K1_BLE_MIDI_CONTROL_COUNT) {
    return;
  }
  if (v.status != K1_DECK_STATE_ST_ACCEPTED &&
      v.status != K1_DECK_STATE_ST_CLAMPED) {
    Serial.printf("DECK_MAP_REJ: map=%u status=%u val=%ld\n",
                  static_cast<unsigned>(v.map_index),
                  static_cast<unsigned>(v.status),
                  static_cast<long>(v.value_i32));
    return;
  }
  const K1BleMidiEntry& e = kK1BleMidiMap[v.map_index];
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
  Serial.printf("DECK_MAP_CONF: path=%s map=%u status=%u val=%ld layout=%u\n",
                e.path,
                static_cast<unsigned>(v.map_index),
                static_cast<unsigned>(v.status),
                static_cast<long>(v.value_i32),
                layout_updated ? 1U : 0U);
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
      if (!digests_match(hello)) {
        ++gMapMismatch;
        gPhase = DECK_LINK_DISCONNECTED;
        return;
      }
      if (gSessionGeneration != 0 && hello.session_generation != gSessionGeneration) {
        // New session generation: clear any stale pending so no uncommanded TX on ARMED.
        gRevision = 0;
        deck_state_clear_pending_all();
        Serial.println("[deck_rx] hello: new generation, pending cleared");
      }
      gSessionGeneration = hello.session_generation;
      gPhase = DECK_LINK_STATE_SYNCING;
      gSnapshotOpen = false;
      break;
    }
    case K1_DECK_STATE_REC_SNAPSHOT_BEGIN: {
      if (gPhase < DECK_LINK_STATE_SYNCING) {
        return;
      }
      gSnapshotOpen = true;
      gSnapshotItems = 0;
      gSnapshotExpected = 0;
      gSnapshotCrcAcc = 0xFFFFFFFFu;
      gPhase = DECK_LINK_STATE_SYNCING;
      break;
    }
    case K1_DECK_STATE_REC_STATE_ITEM: {
      if (!gSnapshotOpen) {
        return;
      }
      K1DeckStateValue value = {};
      if (k1_deck_state_decode_value_payload(rec.payload, rec.payload_len, &value) !=
          K1_DECK_STATE_OK) {
        return;
      }
      apply_value(value);
      gSnapshotCrcAcc = crc_update(gSnapshotCrcAcc, rec.payload, rec.payload_len);
      ++gSnapshotItems;
      if (rec.revision > gRevision) {
        gRevision = rec.revision;
      }
      break;
    }
    case K1_DECK_STATE_REC_SNAPSHOT_END: {
      if (!gSnapshotOpen || rec.payload_len < 6) {
        ++gSnapshotCountFail;
        gSnapshotOpen = false;
        return;
      }
      const uint16_t count = static_cast<uint16_t>(rec.payload[0] | (rec.payload[1] << 8));
      const uint32_t crc = static_cast<uint32_t>(rec.payload[2]) |
                           (static_cast<uint32_t>(rec.payload[3]) << 8) |
                           (static_cast<uint32_t>(rec.payload[4]) << 16) |
                           (static_cast<uint32_t>(rec.payload[5]) << 24);
      gSnapshotExpected = count;
      gSnapshotOpen = false;
      const uint32_t final_crc = gSnapshotCrcAcc ^ 0xFFFFFFFFu;
      if (count != gSnapshotItems) {
        ++gSnapshotCountFail;
        return;
      }
      if (crc != final_crc) {
        ++gSnapshotCrcFail;
        return;
      }
      deck_state_clear_confirmed_stale();
      gPhase = DECK_LINK_ARMED;
      if (rec.revision > gRevision) {
        gRevision = rec.revision;
      }
      break;
    }
    case K1_DECK_STATE_REC_DELTA_BATCH: {
      if (gPhase < DECK_LINK_ARMED && gPhase != DECK_LINK_STATE_SYNCING) {
        return;
      }
      if (rec.revision + 1 < gRevision) {
        ++gStaleRevisions;
        return;
      }
      if (rec.revision > gRevision + 1) {
        ++gRevisionGaps;
        // Gap: mark stale but still apply this DELTA so conf/T2 evidence is not
        // lost, and return to ARMED/LIVE. Full image heal remains via SNAPSHOT.
        deck_state_mark_confirmed_stale();
        Serial.printf("DECK_MAP_GAP: rev=%lu local=%lu — apply+keep armed\n",
                      static_cast<unsigned long>(rec.revision),
                      static_cast<unsigned long>(gRevision));
      }
      // DELTA may carry one or more concatenated state_value payloads.
      size_t off = 0;
      while (off + K1_DECK_STATE_VALUE_PAYLOAD_SIZE <= rec.payload_len) {
        K1DeckStateValue value = {};
        if (k1_deck_state_decode_value_payload(rec.payload + off,
                                               K1_DECK_STATE_VALUE_PAYLOAD_SIZE,
                                               &value) != K1_DECK_STATE_OK) {
          break;
        }
        apply_value(value);
        off += K1_DECK_STATE_VALUE_PAYLOAD_SIZE;
      }
      gRevision = rec.revision;
      gPhase = DECK_LINK_LIVE;
      break;
    }
    case K1_DECK_STATE_REC_HEALTH:
    default:
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
  gSnapshotOpen = false;
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
  gSnapshotOpen = false;
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
  static uint8_t s_reasm[K1_DECK_STATE_MAX_PACKET];
  static size_t s_reasm_len = 0;
  if (len >= 4 && data[0] == 'K' && data[1] == '1' && data[2] == 'D' &&
      data[3] == 'S') {
    s_reasm_len = 0;  // start of a new framed packet
  }
  if (s_reasm_len + len > sizeof(s_reasm)) {
    s_reasm_len = 0;
    return;
  }
  memcpy(s_reasm + s_reasm_len, data, len);
  s_reasm_len += len;

  while (s_reasm_len >= K1_DECK_STATE_PACKET_HEADER_SIZE) {
    if (!(s_reasm[0] == 'K' && s_reasm[1] == '1' && s_reasm[2] == 'D' &&
          s_reasm[3] == 'S')) {
      s_reasm_len = 0;
      return;
    }
    const uint16_t payload_len = static_cast<uint16_t>(
        s_reasm[10] | (static_cast<uint16_t>(s_reasm[11]) << 8));
    const size_t need =
        static_cast<size_t>(K1_DECK_STATE_PACKET_HEADER_SIZE) + payload_len;
    if (need > sizeof(s_reasm)) {
      s_reasm_len = 0;
      return;
    }
    if (s_reasm_len < need) {
      return;  // wait for more ATT chunks
    }
    K1DeckStatePacketHeader hdr = {};
    const uint8_t* blob = nullptr;
    size_t blob_len = 0;
    const K1DeckStateStatus st =
        k1_deck_state_parse_packet(s_reasm, need, &hdr, &blob, &blob_len);
    if (st == K1_DECK_STATE_ERR_CRC) {
      ++gSnapshotCrcFail;
    } else if (st == K1_DECK_STATE_OK) {
      size_t cursor = 0;
      for (uint8_t i = 0; i < hdr.record_count; ++i) {
        K1DeckStateRecordView rec = {};
        if (k1_deck_state_next_record(blob, blob_len, &cursor, &rec) !=
            K1_DECK_STATE_OK) {
          break;
        }
        handle_record(rec);
      }
    }
    // Shift any leftover bytes (start of next packet).
    const size_t remain = s_reasm_len - need;
    if (remain > 0) {
      memmove(s_reasm, s_reasm + need, remain);
    }
    s_reasm_len = remain;
  }
}

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

void deck_state_rx_dump_status(void) {
  Serial.printf(
      "DECK_RX: phase=%s armed=%u live=%u gen=%lu rev=%lu "
      "crc_fail=%lu count_fail=%lu map_mismatch=%lu gaps=%lu stale=%lu "
      "confirmed_stale=%u snap_open=%u items=%u\n",
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
      deck_state_confirmed_stale() ? 1U : 0U,
      gSnapshotOpen ? 1U : 0U,
      static_cast<unsigned>(gSnapshotItems));
}
