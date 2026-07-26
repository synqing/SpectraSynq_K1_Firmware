// SPDX-License-Identifier: GPL-3.0-only
// Copyright 2026 SpectraSynq
//
// k1_sync_link — dual-K1 sync transport probe (Phase 0, unit P0.4, NON-SHIPPABLE).
//
// Compiled ONLY in the k1_sync_probe_* envs under -DSB_K1_SYNC_PROBE; the
// radio-isolation guard (scripts/ble_midi/guard_k1_radio_isolation.py) fails any
// production artefact carrying this TU's symbols, UUIDs, or the "K1-SyncLink"
// name — so the shipping firmware stays radio-clean.
//
// Roles are fixed per env: -DK1_SYNC_ROLE_LEADER (main K1, also runs the K718
// BLE Remoted central) / -DK1_SYNC_ROLE_FOLLOWER (bench K1). The link carries a
// 33.3 Hz timestamped dummy-replay stream (leader -> follower NOTIFY) plus an
// RTT clock-sync exchange, and is instrumented by a wired GPIO cross-trigger.
//
// Everything this TU emits over serial matches the grammar in
// artifacts/k1_dual_sync_eval_2026-07-08/probe-log-contract.md §2, which the
// host oracle (scripts/dual_sync_probe/) parses into the four Phase-0 gate
// numbers. Compile ≠ runtime proof: on-silicon behaviour is P0.5.
//
// Hard rules honoured here: never arms calibration, never writes calibration
// state, never persists config; the one added FreeRTOS task is pinned to Core 1
// at priority 1; no mutex on the audio path; no heap allocation in the
// steady-state poll/ISR; the ISR is IRAM_ATTR, allocation-free, no Serial.
#ifdef SB_K1_SYNC_PROBE

#include "k1_sync_link.h"

#include <Arduino.h>
#include <NimBLEDevice.h>
#include <esp_heap_caps.h>
#include <esp_timer.h>

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

// Render-rate EMA maintained by the LED task (system/globals.h); read-only here.
extern float LED_FPS;

#if defined(K1_SYNC_ROLE_LEADER) && defined(SB_K1_BLE_REMOTED)
// The leader env also compiles the BLE Remoted central; dial-link state feeds the
// health line's dial_linked field.
bool sb_k1_ble_remoted_is_linked();
#endif

namespace k1_sync {
namespace {

#if defined(K1_SYNC_ROLE_LEADER) && defined(SB_K1_BLE_REMOTED)
static_assert(CONFIG_BT_NIMBLE_MAX_CONNECTIONS >= 2,
              "dual-role sync leader requires at least two BLE connections");
#endif

// ── Wired GPIO cross-trigger pins ───────────────────────────────────────────
// Provably unused on BOTH K1 pinmaps — see probe-log-contract.md §1.3 (the audit
// cites constants.h line-by-line). Same numbers on both devboards (identical
// hardware). Wiring: leader15→follower16, follower15→leader16, common GND.
constexpr int kTrigOutPin = 15;
constexpr int kTrigInPin = 16;
constexpr uint32_t kTrigPulseUs = 1000;      // 1 ms high pulse
constexpr uint32_t kTrigPeriodUs = 2000000;  // 0.5 Hz cadence (leader-driven)

// ── Stream / clock timing ───────────────────────────────────────────────────
constexpr uint32_t kStreamPeriodUs = 30000;  // 33.3 Hz notify cadence
constexpr uint32_t kRecordsPerPacket = 2;    // two batched dummy-replay records
constexpr uint32_t kClockMaintPeriodUs = 1000000;  // 1 Hz maintenance ping
constexpr uint32_t kClockRetryUs = 500000;   // bounded retry for a lost burst write/response
constexpr uint32_t kClockBurstSamples = 16;  // RTT burst at link-up / recovery
constexpr uint32_t kHealthPeriodUs = 1000000;  // 1 Hz health line
constexpr uint32_t kNegotiationSettleUs = 250000;  // allow async requests to complete
constexpr uint32_t kNegotiationStableUs = 100000;  // two equal read-backs 100 ms apart
constexpr uint32_t kNegotiationMaxSamples = 5;

// ── BLE link parameters (f2-transport-decision.md) ──────────────────────────
constexpr uint16_t kConnIntervalUnits = 6;   // 6 × 1.25 ms = 7.5 ms CI
constexpr uint16_t kConnLatency = 0;
constexpr uint16_t kSupervisionUnits = 100;  // 100 × 10 ms = 1 s
constexpr uint16_t kSyncMtu = 247;

// ── Packet opcodes on the clock characteristic ──────────────────────────────
constexpr uint8_t kClkReq = 0x01;  // follower -> leader: {op,burst_seq,t1}
constexpr uint8_t kClkRsp = 0x02;  // leader -> follower: {op,burst_seq,t1,t2,t3}

inline uint64_t now_us() { return static_cast<uint64_t>(esp_timer_get_time()); }

// ── Lock-free single-producer/single-consumer ring for TRIG_IN edge times ───
// Producer = the IRAM ISR (writes head); consumer = poll() (writes tail). Power
// of two so the mask wraps cheaply; a full ring drops the oldest-unseen edge,
// which the oracle later sees as an incomplete round (never a corrupt one).
constexpr uint32_t kEdgeRingSize = 16;  // must be a power of two
volatile uint64_t s_edge_ring[kEdgeRingSize] = {0};
volatile uint32_t s_edge_head = 0;  // ISR writes
volatile uint32_t s_edge_tail = 0;  // poll writes

void IRAM_ATTR trig_in_isr() {
  const uint32_t head = s_edge_head;
  const uint32_t next = (head + 1) & (kEdgeRingSize - 1);
  if (next != s_edge_tail) {          // drop-on-full, never block
    s_edge_ring[head] = now_us();     // esp_timer_get_time() is IRAM-safe on S3
    s_edge_head = next;
  }
}

// Drain one captured edge time; false when the ring is empty.
bool pop_edge(uint64_t* t_us) {
  if (s_edge_tail == s_edge_head) {
    return false;
  }
  *t_us = s_edge_ring[s_edge_tail];
  s_edge_tail = (s_edge_tail + 1) & (kEdgeRingSize - 1);
  return true;
}

// ── Cross-trigger round counter ─────────────────────────────────────────────
// Leader drives the cadence and its seq; the follower echoes each received ping
// and adopts the same running counter, so seq pairs 1:1 across the wire by
// causality (no data rides the bare GPIO edge). Both counters reset on link-up
// so boot order cannot misalign them; a rare mid-run missed edge only drops a
// round. This makes the seq purely a pairing LABEL — the offset MEASUREMENT is
// the raw device-local timestamps, never the radio, never the counter.
uint32_t s_round_seq = 0;
uint64_t s_trig_out_high_us = 0;  // when the current TRIG_OUT pulse went high
bool s_trig_out_active = false;

// ── Stream + loss/dup tracking (follower) ───────────────────────────────────
struct StreamItem {
  uint32_t seq;
  uint64_t t_leader;
  uint64_t t_rx;
};
constexpr uint32_t kStreamRingSize = 64;  // power of two; > one 33 Hz burst
volatile StreamItem s_stream_ring[kStreamRingSize];
volatile uint32_t s_stream_head = 0;  // BLE-callback task writes
volatile uint32_t s_stream_tail = 0;  // poll() drains

bool s_have_last_rx_seq = false;
uint32_t s_last_rx_seq = 0;
uint32_t s_stream_loss = 0;
uint32_t s_stream_dup = 0;

// ── Injected fault state (follower apply path) ──────────────────────────────
enum Fault { kFaultOff = 0, kFaultDelay5, kFaultDelay20, kFaultDrop10 };
volatile int s_fault = kFaultOff;
uint32_t s_drop_phase = 0;  // deterministic 1-in-10 dropper

// ── Clock sync state ────────────────────────────────────────────────────────
// est_offset is the min-RTT-filtered offset (follower_local - leader_local) from
// each burst / 1 Hz maintenance sample. Inter-device DRIFT is deliberately NOT
// corrected in firmware: the follower stamps its own apply time from the local
// esp_timer, and the host oracle maps clocks from the wired cross-trigger truth,
// so the radio estimate is only ever the gate-1 quantity. Residual skew/drift
// therefore surfaces as the trend of the oracle's (est - wire_truth) series over
// the run — which is exactly how P0.3's drift-fault test detects it.
int64_t s_est_offset_us = 0;
uint32_t s_clk_rtt_us = 0;
uint32_t s_clk_samples = 0;
bool s_clk_valid = false;
int64_t s_burst_best_offset = 0;
uint32_t s_burst_best_rtt = 0xFFFFFFFFu;
uint32_t s_burst_remaining = 0;
uint32_t s_burst_seq = 0;
uint32_t s_clock_inflight_seq = 0;
bool s_clock_send_pending = false;

// ── NimBLE handles ──────────────────────────────────────────────────────────
volatile bool s_connected = false;
volatile bool s_linked = false;
volatile uint16_t s_conn_handle = 0xFFFF;
volatile uint32_t s_connection_generation = 0;
portMUX_TYPE s_state_mux = portMUX_INITIALIZER_UNLOCKED;
volatile bool s_ready_announcement = false;
volatile bool s_link_down_pending = false;
int s_link_down_reason = 0;
uint32_t s_link_down_epoch = 0;
uint32_t s_link_epoch = 0;
uint32_t s_notify_fail = 0;
uint32_t s_clock_io_fail = 0;
TaskHandle_t s_io_task = nullptr;
bool s_role_init_ok = false;

#if defined(K1_SYNC_ROLE_LEADER)
NimBLEServer* s_server = nullptr;
NimBLECharacteristic* s_stream_char = nullptr;
NimBLECharacteristic* s_clock_char = nullptr;
volatile bool s_stream_subscribed = false;
volatile bool s_clock_subscribed = false;
volatile bool s_peer_clock_ready = false;
volatile bool s_adv_restart_pending = false;
int s_adv_restart_reason = 0;
uint64_t s_adv_retry_after_us = 0;
uint64_t s_negotiation_candidate_us = 0;
#elif defined(K1_SYNC_ROLE_FOLLOWER)
NimBLEClient* s_client = nullptr;
NimBLERemoteCharacteristic* s_stream_rx = nullptr;
NimBLERemoteCharacteristic* s_clock_rx = nullptr;
volatile bool s_have_target = false;
NimBLEAddress s_target_addr;
portMUX_TYPE s_target_mux = portMUX_INITIALIZER_UNLOCKED;
struct ClockResponse {
  uint32_t generation;
  uint64_t t4_us;
  uint8_t data[29];
};
constexpr UBaseType_t kClockResponseQueueCapacity = 16;
QueueHandle_t s_clock_response_queue = nullptr;
StaticQueue_t s_clock_response_queue_struct;
uint8_t s_clock_response_queue_storage[
    kClockResponseQueueCapacity * sizeof(ClockResponse)];
uint32_t s_clock_response_drops = 0;
#endif

// ── Cadence bookkeeping ─────────────────────────────────────────────────────
uint64_t s_last_stream_us = 0;
uint64_t s_last_clock_maint_us = 0;
uint64_t s_last_clock_request_us = 0;
uint64_t s_last_health_us = 0;
uint64_t s_last_trig_us = 0;
uint32_t s_stream_tx_seq = 0;

void reset_link_state() {
  s_round_seq = 0;
  s_have_last_rx_seq = false;
  s_stream_loss = 0;
  s_stream_dup = 0;
  s_stream_tx_seq = 0;
  s_stream_head = 0;
  s_stream_tail = 0;
  s_edge_head = 0;
  s_edge_tail = 0;
  s_notify_fail = 0;
  s_clock_io_fail = 0;
  s_clk_valid = false;
  s_clk_samples = 0;
  s_burst_remaining = 0;
  s_clock_send_pending = false;
  s_clock_inflight_seq = 0;
}

struct NegotiatedSnapshot {
  uint16_t handle;
  uint16_t interval_units;
  uint16_t latency;
  uint16_t mtu;
  uint8_t phy_tx;
  uint8_t phy_rx;
};

NegotiatedSnapshot s_ready_snapshot{};
volatile bool s_ready_snapshot_valid = false;

bool same_snapshot(const NegotiatedSnapshot& lhs,
                   const NegotiatedSnapshot& rhs) {
  return lhs.handle == rhs.handle &&
         lhs.interval_units == rhs.interval_units &&
         lhs.latency == rhs.latency && lhs.mtu == rhs.mtu &&
         lhs.phy_tx == rhs.phy_tx && lhs.phy_rx == rhs.phy_rx;
}

bool valid_snapshot(const NegotiatedSnapshot& snapshot) {
  return snapshot.handle != 0xFFFF &&
         snapshot.interval_units == kConnIntervalUnits &&
         snapshot.latency == kConnLatency && snapshot.mtu == kSyncMtu &&
         snapshot.phy_tx == BLE_GAP_LE_PHY_2M &&
         snapshot.phy_rx == BLE_GAP_LE_PHY_2M;
}

#if defined(K1_SYNC_ROLE_LEADER)
NegotiatedSnapshot s_negotiation_candidate{};
uint32_t s_negotiation_candidate_generation = 0;
#endif

void link_lifecycle_service() {
  portENTER_CRITICAL(&s_state_mux);
  const bool emit = s_link_down_pending && !s_ready_announcement;
  const int reason = s_link_down_reason;
  const uint32_t epoch = s_link_down_epoch;
  if (emit) {
    s_link_down_pending = false;
  }
  portEXIT_CRITICAL(&s_state_mux);
  if (!emit) {
    return;
  }
#if defined(K1_SYNC_ROLE_LEADER)
  constexpr const char* kRole = "leader";
#else
  constexpr const char* kRole = "follower";
#endif
  Serial.printf("[k1_sync] link down role=%s epoch=%u reason=%d\n", kRole,
                (unsigned)epoch, reason);
}

// ── GPIO cross-trigger ──────────────────────────────────────────────────────
void trig_out_pulse(uint32_t seq) {
  digitalWrite(kTrigOutPin, HIGH);
  s_trig_out_high_us = now_us();
  s_trig_out_active = true;
  Serial.printf("[sync_oracle] trig_out seq=%u t_us=%llu\n",
                (unsigned)seq, (unsigned long long)s_trig_out_high_us);
}

void trig_service() {
  // Lower the pulse once its 1 ms width has elapsed (non-blocking).
  if (s_trig_out_active && (now_us() - s_trig_out_high_us) >= kTrigPulseUs) {
    digitalWrite(kTrigOutPin, LOW);
    s_trig_out_active = false;
  }

  // Drain captured incoming edges.
  uint64_t edge_us;
  while (pop_edge(&edge_us)) {
#if defined(K1_SYNC_ROLE_LEADER)
    // Leader: incoming edge is the follower's echo — log against the round we
    // last sent. Do not re-echo.
    Serial.printf("[sync_oracle] trig_in seq=%u t_us=%llu\n",
                  (unsigned)s_round_seq, (unsigned long long)edge_us);
#elif defined(K1_SYNC_ROLE_FOLLOWER)
    // Follower: incoming edge is the leader's ping — advance the shared counter,
    // log trig_in, then echo it back on our TRIG_OUT so the leader can close the
    // round in the reverse direction.
    ++s_round_seq;
    Serial.printf("[sync_oracle] trig_in seq=%u t_us=%llu\n",
                  (unsigned)s_round_seq, (unsigned long long)edge_us);
    trig_out_pulse(s_round_seq);
#endif
  }

#if defined(K1_SYNC_ROLE_LEADER)
  // Leader owns the 0.5 Hz cadence (only while linked, so the follower's ISR is
  // armed and cannot miss the first ping).
  if (s_linked && (now_us() - s_last_trig_us) >= kTrigPeriodUs) {
    s_last_trig_us = now_us();
    ++s_round_seq;
    trig_out_pulse(s_round_seq);
  }
#endif
}

// ── Clock-sync helpers ──────────────────────────────────────────────────────
void begin_clock_burst() {
  s_burst_remaining = kClockBurstSamples;
  s_burst_best_rtt = 0xFFFFFFFFu;
}

#if defined(K1_SYNC_ROLE_FOLLOWER)
bool send_clock_request() {
  portENTER_CRITICAL(&s_state_mux);
  NimBLERemoteCharacteristic* const clock = s_clock_rx;
  const bool usable = s_connected && s_linked && clock != nullptr;
  portEXIT_CRITICAL(&s_state_mux);
  if (!usable) {
    return false;
  }
  ++s_burst_seq;
  uint8_t pkt[13];
  pkt[0] = kClkReq;
  const uint32_t bs = s_burst_seq;
  s_clock_inflight_seq = bs;
  memcpy(&pkt[1], &bs, sizeof(bs));
  const uint64_t t1 = now_us();
  memcpy(&pkt[5], &t1, sizeof(t1));
  s_last_clock_request_us = t1;
  if (!clock->writeValue(pkt, sizeof(pkt), false)) {
    portENTER_CRITICAL(&s_state_mux);
    ++s_clock_io_fail;
    const uint32_t fail_count = s_clock_io_fail;
    portEXIT_CRITICAL(&s_state_mux);
    Serial.printf("[k1_sync_diag] clock_write_fail count=%u\n",
                  (unsigned)fail_count);
    return false;
  }
  return true;
}

void ingest_clock_response(const uint8_t* data, size_t len, uint64_t t4,
                           uint32_t generation) {
  if (len < 29 || data[0] != kClkRsp) {
    return;
  }
  portENTER_CRITICAL(&s_state_mux);
  const bool current =
      s_connected && s_connection_generation == generation;
  portEXIT_CRITICAL(&s_state_mux);
  if (!current) {
    return;
  }
  uint32_t response_seq = 0;
  uint64_t t1, t2, t3;
  memcpy(&response_seq, &data[1], sizeof(response_seq));
  if (response_seq != s_clock_inflight_seq) {
    Serial.printf(
        "[k1_sync_diag] clock_stale_response got=%u expected=%u\n",
        (unsigned)response_seq, (unsigned)s_clock_inflight_seq);
    return;
  }
  memcpy(&t1, &data[5], sizeof(t1));
  memcpy(&t2, &data[13], sizeof(t2));
  memcpy(&t3, &data[21], sizeof(t3));
  // offset = follower_local - leader_local ; rtt = round-trip minus server span.
  const int64_t offset = (static_cast<int64_t>(t1 - t2) + static_cast<int64_t>(t4 - t3)) / 2;
  const int64_t rtt = static_cast<int64_t>(t4 - t1) - static_cast<int64_t>(t3 - t2);
  const uint32_t rtt_u = rtt < 0 ? 0 : static_cast<uint32_t>(rtt);
  if (rtt_u < s_burst_best_rtt) {   // min-filter: least-queued sample wins
    s_burst_best_rtt = rtt_u;
    s_burst_best_offset = offset;
  }
  if (s_burst_remaining > 0) {
    --s_burst_remaining;
    if (s_burst_remaining == 0) {
      // Burst complete: publish min-RTT offset + update the affine skew term.
      portENTER_CRITICAL(&s_state_mux);
      s_est_offset_us = s_burst_best_offset;
      s_clk_rtt_us = s_burst_best_rtt;
      s_clk_samples = kClockBurstSamples;
      s_clk_valid = true;
      portEXIT_CRITICAL(&s_state_mux);
    } else {
      s_clock_send_pending = true;  // Core-1 I/O task owns every transmission
    }
  } else {
    // 1 Hz maintenance sample: min-filter this single round-trip and track skew.
    portENTER_CRITICAL(&s_state_mux);
    if (rtt_u <= s_clk_rtt_us || !s_clk_valid) {
      s_est_offset_us = offset;
      s_clk_rtt_us = rtt_u;
    }
    s_clk_samples = 1;
    s_clk_valid = true;
    portEXIT_CRITICAL(&s_state_mux);
  }
}
#endif  // FOLLOWER

// ── NimBLE callbacks ─────────────────────────────────────────────────────────
#if defined(K1_SYNC_ROLE_LEADER)
bool read_server_snapshot(uint16_t handle, NegotiatedSnapshot* snapshot) {
  if (!s_server || !snapshot || handle == 0xFFFF) {
    return false;
  }
  const NimBLEConnInfo info = s_server->getPeerInfoByHandle(handle);
  uint8_t tx_phy = 0;
  uint8_t rx_phy = 0;
  if (!s_server->getPhy(handle, &tx_phy, &rx_phy)) {
    return false;
  }
  *snapshot = {
      info.getConnHandle(), info.getConnInterval(), info.getConnLatency(),
      info.getMTU(), tx_phy, rx_phy,
  };
  return valid_snapshot(*snapshot);
}

void log_server_actual(const char* source, NimBLEConnInfo& info) {
  uint8_t tx_phy = 0;
  uint8_t rx_phy = 0;
  const bool phy_ok =
      s_server && s_server->getPhy(info.getConnHandle(), &tx_phy, &rx_phy);
  Serial.printf(
      "[k1_sync_diag] link_actual role=leader source=%s handle=%u mtu=%u "
      "interval_units=%u latency=%u timeout_units=%u phy_ok=%u tx_phy=%u rx_phy=%u\n",
      source, (unsigned)info.getConnHandle(), (unsigned)info.getMTU(),
      (unsigned)info.getConnInterval(), (unsigned)info.getConnLatency(),
      (unsigned)info.getConnTimeout(), phy_ok ? 1U : 0U, (unsigned)tx_phy,
      (unsigned)rx_phy);
}

void mark_leader_ready(const NegotiatedSnapshot& snapshot,
                       uint32_t generation) {
  portENTER_CRITICAL(&s_state_mux);
  const bool publish =
      !s_linked && s_connected &&
      s_connection_generation == generation &&
      s_conn_handle == snapshot.handle && s_stream_subscribed &&
      s_clock_subscribed && s_peer_clock_ready;
  if (publish) {
    reset_link_state();
    ++s_link_epoch;
    s_ready_snapshot = snapshot;
    s_ready_snapshot_valid = true;
    s_ready_announcement = true;
    s_linked = true;
  }
  const uint32_t epoch = s_link_epoch;
  portEXIT_CRITICAL(&s_state_mux);
  if (!publish) {
    return;
  }
  Serial.printf("[k1_sync] link up role=leader epoch=%u handle=%u mtu=%u\n",
                (unsigned)epoch, (unsigned)snapshot.handle,
                (unsigned)snapshot.mtu);
  Serial.printf(
      "[k1_sync] negotiated role=leader epoch=%u interval_units=%u "
      "latency=%u mtu=%u phy_tx=%u phy_rx=%u\n",
      (unsigned)epoch, (unsigned)snapshot.interval_units,
      (unsigned)snapshot.latency, (unsigned)snapshot.mtu,
      (unsigned)snapshot.phy_tx, (unsigned)snapshot.phy_rx);
  portENTER_CRITICAL(&s_state_mux);
  s_ready_announcement = false;
  portEXIT_CRITICAL(&s_state_mux);
}

void leader_ready_service() {
  portENTER_CRITICAL(&s_state_mux);
  const bool eligible =
      !s_linked && s_connected && s_stream_subscribed &&
      s_clock_subscribed && s_peer_clock_ready;
  const uint16_t handle = s_conn_handle;
  const uint32_t generation = s_connection_generation;
  portEXIT_CRITICAL(&s_state_mux);
  if (!eligible) {
    s_negotiation_candidate_us = 0;
    return;
  }
  NegotiatedSnapshot current{};
  if (!read_server_snapshot(handle, &current)) {
    s_negotiation_candidate_us = 0;
    return;
  }
  const uint64_t now = now_us();
  if (s_negotiation_candidate_us == 0 ||
      s_negotiation_candidate_generation != generation ||
      !same_snapshot(current, s_negotiation_candidate)) {
    s_negotiation_candidate = current;
    s_negotiation_candidate_generation = generation;
    s_negotiation_candidate_us = now;
    return;
  }
  if ((now - s_negotiation_candidate_us) >= kNegotiationStableUs) {
    mark_leader_ready(current, generation);
  }
}

void update_leader_subscription(NimBLECharacteristic* chr,
                                NimBLEConnInfo& info, uint16_t sub_value) {
  const bool notify_enabled = (sub_value & 0x0001U) != 0;
  portENTER_CRITICAL(&s_state_mux);
  if (chr == s_stream_char) {
    s_stream_subscribed = notify_enabled;
  } else if (chr == s_clock_char) {
    s_clock_subscribed = notify_enabled;
  }
  const bool stream_subscribed = s_stream_subscribed;
  const bool clock_subscribed = s_clock_subscribed;
  if (!notify_enabled && s_linked) {
    s_link_down_pending = true;
    s_link_down_reason = -2;
    s_link_down_epoch = s_link_epoch;
    s_linked = false;
  }
  portEXIT_CRITICAL(&s_state_mux);
  Serial.printf(
      "[k1_sync_diag] subscribe role=leader handle=%u stream=%u clock=%u\n",
      (unsigned)info.getConnHandle(), stream_subscribed ? 1U : 0U,
      clock_subscribed ? 1U : 0U);
}

class StreamNotifyCB : public NimBLECharacteristicCallbacks {
  void onSubscribe(NimBLECharacteristic* chr, NimBLEConnInfo& info,
                   uint16_t sub_value) override {
    update_leader_subscription(chr, info, sub_value);
  }
};
StreamNotifyCB s_stream_notify_cb;

class ClockWriteCB : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* chr, NimBLEConnInfo& info) override {
    const uint64_t t2 = now_us();  // leader receive time (stamp ASAP)
    NimBLEAttValue v = chr->getValue();
    if (v.length() < 13 || v.data()[0] != kClkReq) {
      return;
    }
    // A valid follower clock request can only be sent after both subscribe()
    // calls returned successfully. Combined with the two CCCD callbacks, this
    // is the application-ready barrier that prevents pre-ready stream/GPIO.
    portENTER_CRITICAL(&s_state_mux);
    if (s_connected && s_conn_handle == info.getConnHandle()) {
      s_peer_clock_ready = true;
    }
    portEXIT_CRITICAL(&s_state_mux);
    uint8_t rsp[29];
    rsp[0] = kClkRsp;
    memcpy(&rsp[1], v.data() + 1, 4);   // echo burst_seq
    memcpy(&rsp[5], v.data() + 5, 8);   // echo t1
    memcpy(&rsp[13], &t2, sizeof(t2));  // t2 leader recv
    const uint64_t t3 = now_us();       // leader send time
    memcpy(&rsp[21], &t3, sizeof(t3));
    if (s_clock_char &&
        !s_clock_char->notify(rsp, sizeof(rsp), info.getConnHandle())) {
      portENTER_CRITICAL(&s_state_mux);
      ++s_clock_io_fail;
      const uint32_t fail_count = s_clock_io_fail;
      portEXIT_CRITICAL(&s_state_mux);
      Serial.printf("[k1_sync_diag] clock_notify_fail count=%u\n",
                    (unsigned)fail_count);
    }
  }

  void onSubscribe(NimBLECharacteristic* chr, NimBLEConnInfo& info,
                   uint16_t sub_value) override {
    update_leader_subscription(chr, info, sub_value);
  }
};
ClockWriteCB s_clock_write_cb;

class ServerCB : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer* server, NimBLEConnInfo& info) override {
    portENTER_CRITICAL(&s_state_mux);
    ++s_connection_generation;
    s_connected = true;
    s_linked = false;
    s_ready_snapshot_valid = false;
    s_conn_handle = info.getConnHandle();
    s_stream_subscribed = false;
    s_clock_subscribed = false;
    s_peer_clock_ready = false;
    portEXIT_CRITICAL(&s_state_mux);
    Serial.printf("[k1_sync_diag] connected role=leader handle=%u\n",
                  (unsigned)s_conn_handle);
    log_server_actual("connect", info);
    server->updateConnParams(s_conn_handle, kConnIntervalUnits, kConnIntervalUnits,
                             kConnLatency, kSupervisionUnits);
    const bool phy_requested = server->updatePhy(
        s_conn_handle, BLE_GAP_LE_PHY_2M_MASK, BLE_GAP_LE_PHY_2M_MASK, 0);
    server->setDataLen(s_conn_handle, 251);
    Serial.printf(
        "[k1_sync_diag] link_request role=leader conn_params=issued "
        "phy=%s dle=issued\n",
        phy_requested ? "accepted" : "rejected");
    Serial.println(
        "[k1_sync_diag] dle role=leader requested_octets=251 negotiated=UNMEASURED");
  }

  void onDisconnect(NimBLEServer*, NimBLEConnInfo&, int reason) override {
    portENTER_CRITICAL(&s_state_mux);
    const bool was_linked = s_linked;
    if (was_linked) {
      s_link_down_pending = true;
      s_link_down_reason = reason;
      s_link_down_epoch = s_link_epoch;
    }
    ++s_connection_generation;
    s_connected = false;
    s_linked = false;
    s_ready_snapshot_valid = false;
    s_stream_subscribed = false;
    s_clock_subscribed = false;
    s_peer_clock_ready = false;
    s_adv_restart_pending = true;
    s_adv_restart_reason = reason;
    s_conn_handle = 0xFFFF;
    portEXIT_CRITICAL(&s_state_mux);
    if (!was_linked) {
      Serial.printf(
          "[k1_sync_diag] physical_down role=leader reason=%d before_ready=1\n",
          reason);
    }
  }

  void onMTUChange(uint16_t mtu, NimBLEConnInfo& info) override {
    Serial.printf("[k1_sync_diag] mtu_actual role=leader mtu=%u\n",
                  (unsigned)mtu);
    log_server_actual("mtu", info);
  }

  void onConnParamsUpdate(NimBLEConnInfo& info) override {
    log_server_actual("conn_params", info);
  }

  void onPhyUpdate(NimBLEConnInfo& info, uint8_t tx_phy,
                   uint8_t rx_phy) override {
    Serial.printf(
        "[k1_sync_diag] phy_actual role=leader handle=%u tx_phy=%u rx_phy=%u\n",
        (unsigned)info.getConnHandle(), (unsigned)tx_phy, (unsigned)rx_phy);
    log_server_actual("phy", info);
  }
};
ServerCB s_server_cb;

void begin_leader() {
  s_role_init_ok = false;
  const bool init_ok =
      NimBLEDevice::isInitialized() || NimBLEDevice::init(kSyncDeviceName);
  const bool mtu_pref_ok = init_ok && NimBLEDevice::setMTU(kSyncMtu);
  Serial.printf(
      "[k1_sync_diag] init role=leader ok=%u mtu_pref_ok=%u\n",
      init_ok ? 1U : 0U, mtu_pref_ok ? 1U : 0U);
  if (!init_ok || !mtu_pref_ok) {
    return;
  }
  s_server = NimBLEDevice::createServer();
  if (!s_server) {
    Serial.println("[k1_sync_diag] init role=leader server_ok=0");
    return;
  }
  s_server->setCallbacks(&s_server_cb, false);
  NimBLEService* svc = s_server->createService(kSyncServiceUuid);
  if (!svc) {
    Serial.println("[k1_sync_diag] init role=leader service_ok=0");
    return;
  }
  s_stream_char = svc->createCharacteristic(
      kSyncStreamCharUuid, NIMBLE_PROPERTY::NOTIFY | NIMBLE_PROPERTY::READ);
  s_clock_char = svc->createCharacteristic(
      kSyncClockCharUuid,
      NIMBLE_PROPERTY::NOTIFY | NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR);
  if (!s_stream_char || !s_clock_char) {
    Serial.println("[k1_sync_diag] init role=leader characteristics_ok=0");
    return;
  }
  s_stream_char->setCallbacks(&s_stream_notify_cb);
  s_clock_char->setCallbacks(&s_clock_write_cb);
  NimBLEAdvertising* adv = NimBLEDevice::getAdvertising();
  if (!adv) {
    Serial.println("[k1_sync_diag] init role=leader advertising_ok=0");
    return;
  }
  adv->enableScanResponse(true);
  const bool uuid_ok = adv->addServiceUUID(kSyncServiceUuid);
  const bool name_ok = adv->setName(kSyncDeviceName);
  const bool start_ok = adv->start();
  const bool active = adv->isAdvertising();
  Serial.printf(
      "[k1_sync_diag] adv scan_rsp_configured=1 uuid=%u name=%u start=%u active=%u\n",
      uuid_ok ? 1U : 0U, name_ok ? 1U : 0U, start_ok ? 1U : 0U,
      active ? 1U : 0U);
  s_role_init_ok = uuid_ok && name_ok && start_ok && active;
  Serial.println("[k1_sync] begin role=leader");
}

void leader_stream_service() {
  portENTER_CRITICAL(&s_state_mux);
  const bool linked = s_linked;
  const uint16_t handle = s_conn_handle;
  const uint32_t generation = s_connection_generation;
  portEXIT_CRITICAL(&s_state_mux);
  if (!linked || !s_stream_char) {
    return;
  }
  if ((now_us() - s_last_stream_us) < kStreamPeriodUs) {
    return;
  }
  s_last_stream_us = now_us();
  uint8_t pkt[kRecordsPerPacket * 12];
  for (uint32_t i = 0; i < kRecordsPerPacket; ++i) {
    const uint32_t seq = ++s_stream_tx_seq;
    const uint64_t t_leader = now_us();
    memcpy(&pkt[i * 12], &seq, 4);
    memcpy(&pkt[i * 12 + 4], &t_leader, 8);
    Serial.printf("[k1_sync] tx seq=%u t_leader_us=%llu\n",
                  (unsigned)seq, (unsigned long long)t_leader);
  }
  portENTER_CRITICAL(&s_state_mux);
  const bool current =
      s_linked && s_connection_generation == generation &&
      s_conn_handle == handle;
  portEXIT_CRITICAL(&s_state_mux);
  if (!current) {
    return;
  }
  if (!s_stream_char->notify(pkt, sizeof(pkt), handle)) {
    ++s_notify_fail;
    Serial.printf("[k1_sync_diag] stream_notify_fail count=%u\n",
                  (unsigned)s_notify_fail);
  }
}
#endif  // LEADER

#if defined(K1_SYNC_ROLE_FOLLOWER)
void on_stream_notify(NimBLERemoteCharacteristic*, uint8_t* data, size_t len, bool) {
  const uint64_t t_rx = now_us();
  const size_t records = len / 12;
  for (size_t i = 0; i < records; ++i) {
    uint32_t seq;
    uint64_t t_leader;
    memcpy(&seq, &data[i * 12], 4);
    memcpy(&t_leader, &data[i * 12 + 4], 8);
    const uint32_t head = s_stream_head;
    const uint32_t next = (head + 1) & (kStreamRingSize - 1);
    if (next != s_stream_tail) {
      s_stream_ring[head].seq = seq;
      s_stream_ring[head].t_leader = t_leader;
      s_stream_ring[head].t_rx = t_rx;
      s_stream_head = next;
    }
  }
}

void on_clock_notify(NimBLERemoteCharacteristic*, uint8_t* data, size_t len,
                     bool) {
  if (!s_clock_response_queue || data == nullptr || len < 29) {
    return;
  }
  ClockResponse response{};
  response.t4_us = now_us();
  portENTER_CRITICAL(&s_state_mux);
  response.generation = s_connection_generation;
  portEXIT_CRITICAL(&s_state_mux);
  memcpy(response.data, data, sizeof(response.data));
  if (xQueueSend(s_clock_response_queue, &response, 0) != pdTRUE) {
    portENTER_CRITICAL(&s_state_mux);
    ++s_clock_response_drops;
    portEXIT_CRITICAL(&s_state_mux);
  }
}

class ScanCB : public NimBLEScanCallbacks {
  void consider(const NimBLEAdvertisedDevice* dev) {
    if (dev == nullptr || s_have_target || s_connected) {
      return;
    }
    if (!dev->haveServiceUUID() ||
        !dev->isAdvertisingService(NimBLEUUID(kSyncServiceUuid))) {
      return;
    }
    portENTER_CRITICAL(&s_target_mux);
    if (!s_have_target) {
      s_target_addr = dev->getAddress();
      s_have_target = true;
    }
    portEXIT_CRITICAL(&s_target_mux);
    const bool stopped = NimBLEDevice::getScan()->stop();
    Serial.printf(
        "[k1_sync_diag] discovered uuid=1 name_match=%u scan_stop=%u\n",
        dev->getName() == kSyncDeviceName ? 1U : 0U, stopped ? 1U : 0U);
  }

  void onDiscovered(const NimBLEAdvertisedDevice* dev) override {
    consider(dev);
  }

  void onResult(const NimBLEAdvertisedDevice* dev) override { consider(dev); }
};
ScanCB s_scan_cb;

void log_client_actual(const char* source, NimBLEClient* client) {
  if (!client || !client->isConnected()) {
    Serial.printf(
        "[k1_sync_diag] link_actual role=follower source=%s connected=0\n",
        source);
    return;
  }
  const NimBLEConnInfo info = client->getConnInfo();
  uint8_t tx_phy = 0;
  uint8_t rx_phy = 0;
  const bool phy_ok = client->getPhy(&tx_phy, &rx_phy);
  Serial.printf(
      "[k1_sync_diag] link_actual role=follower source=%s handle=%u mtu=%u "
      "interval_units=%u latency=%u timeout_units=%u phy_ok=%u tx_phy=%u rx_phy=%u\n",
      source, (unsigned)info.getConnHandle(), (unsigned)info.getMTU(),
      (unsigned)info.getConnInterval(), (unsigned)info.getConnLatency(),
      (unsigned)info.getConnTimeout(), phy_ok ? 1U : 0U, (unsigned)tx_phy,
      (unsigned)rx_phy);
}

class ClientCB : public NimBLEClientCallbacks {
  void onConnect(NimBLEClient* client) override {
    portENTER_CRITICAL(&s_state_mux);
    ++s_connection_generation;
    s_connected = true;
    s_linked = false;
    s_ready_snapshot_valid = false;
    s_conn_handle = client->getConnHandle();
    portEXIT_CRITICAL(&s_state_mux);
    Serial.printf("[k1_sync_diag] connected role=follower handle=%u\n",
                  (unsigned)s_conn_handle);
    log_client_actual("connect", client);
    const bool conn_params_requested = client->updateConnParams(
        kConnIntervalUnits, kConnIntervalUnits, kConnLatency,
        kSupervisionUnits);
    const bool phy_requested = client->updatePhy(
        BLE_GAP_LE_PHY_2M_MASK, BLE_GAP_LE_PHY_2M_MASK, 0);
    const bool dle_requested = client->setDataLen(251);
    Serial.printf(
        "[k1_sync_diag] link_request role=follower conn_params=%s "
        "phy=%s dle=%s\n",
        conn_params_requested ? "accepted" : "rejected",
        phy_requested ? "accepted" : "rejected",
        dle_requested ? "accepted" : "rejected");
    Serial.println(
        "[k1_sync_diag] dle role=follower requested_octets=251 negotiated=UNMEASURED");
  }

  void onDisconnect(NimBLEClient*, int reason) override {
    portENTER_CRITICAL(&s_state_mux);
    const bool was_linked = s_linked;
    if (was_linked) {
      s_link_down_pending = true;
      s_link_down_reason = reason;
      s_link_down_epoch = s_link_epoch;
    }
    ++s_connection_generation;
    s_connected = false;
    s_linked = false;
    s_ready_snapshot_valid = false;
    s_stream_rx = nullptr;
    s_clock_rx = nullptr;
    s_conn_handle = 0xFFFF;
    portEXIT_CRITICAL(&s_state_mux);
    portENTER_CRITICAL(&s_target_mux);
    s_have_target = false;
    portEXIT_CRITICAL(&s_target_mux);
    if (!was_linked) {
      Serial.printf(
          "[k1_sync_diag] physical_down role=follower reason=%d before_ready=1\n",
          reason);
    }
  }

  void onConnectFail(NimBLEClient* client, int reason) override {
    portENTER_CRITICAL(&s_state_mux);
    ++s_connection_generation;
    s_connected = false;
    s_linked = false;
    s_ready_snapshot_valid = false;
    portEXIT_CRITICAL(&s_state_mux);
    portENTER_CRITICAL(&s_target_mux);
    s_have_target = false;
    portEXIT_CRITICAL(&s_target_mux);
    Serial.printf(
        "[k1_sync_diag] connect_fail role=follower reason=%d last_error=%d\n",
        reason, client ? client->getLastError() : reason);
  }

  void onMTUChange(NimBLEClient* client, uint16_t mtu) override {
    Serial.printf("[k1_sync_diag] mtu_actual role=follower mtu=%u\n",
                  (unsigned)mtu);
    log_client_actual("mtu", client);
  }

  void onPhyUpdate(NimBLEClient* client, uint8_t tx_phy,
                   uint8_t rx_phy) override {
    Serial.printf(
        "[k1_sync_diag] phy_actual role=follower tx_phy=%u rx_phy=%u\n",
        (unsigned)tx_phy, (unsigned)rx_phy);
    log_client_actual("phy", client);
  }
};
ClientCB s_client_cb;

bool connection_is_current(uint32_t generation) {
  portENTER_CRITICAL(&s_state_mux);
  const bool current =
      s_connected && s_connection_generation == generation;
  portEXIT_CRITICAL(&s_state_mux);
  return current && s_client && s_client->isConnected();
}

bool read_client_snapshot(NimBLEClient* client, NegotiatedSnapshot* snapshot) {
  if (!client || !snapshot || !client->isConnected()) {
    return false;
  }
  const NimBLEConnInfo info = client->getConnInfo();
  uint8_t tx_phy = 0;
  uint8_t rx_phy = 0;
  if (!client->getPhy(&tx_phy, &rx_phy)) {
    return false;
  }
  *snapshot = {
      info.getConnHandle(), info.getConnInterval(), info.getConnLatency(),
      info.getMTU(), tx_phy, rx_phy,
  };
  return valid_snapshot(*snapshot);
}

bool read_stable_client_snapshot(uint32_t generation,
                                 NegotiatedSnapshot* settled) {
  vTaskDelay(pdMS_TO_TICKS(kNegotiationSettleUs / 1000U));
  NegotiatedSnapshot previous{};
  bool have_previous = false;
  for (uint32_t sample = 0; sample < kNegotiationMaxSamples; ++sample) {
    if (!connection_is_current(generation)) {
      return false;
    }
    NegotiatedSnapshot current{};
    if (read_client_snapshot(s_client, &current)) {
      if (have_previous && same_snapshot(previous, current)) {
        *settled = current;
        return true;
      }
      previous = current;
      have_previous = true;
    }
    vTaskDelay(pdMS_TO_TICKS(kNegotiationStableUs / 1000U));
  }
  return false;
}

bool disconnect_after_failure(const char* step) {
  const int last_error = s_client ? s_client->getLastError() : 0;
  Serial.printf(
      "[k1_sync_diag] subscribe_fail role=follower step=%s last_error=%d\n",
      step, last_error);
  if (s_client && s_client->isConnected()) {
    s_client->disconnect();
  }
  return false;
}

bool connect_and_subscribe() {
  NimBLEAddress addr;
  portENTER_CRITICAL(&s_target_mux);
  addr = s_target_addr;
  portEXIT_CRITICAL(&s_target_mux);
  if (!s_client) {
    s_client = NimBLEDevice::createClient();
    if (!s_client) {
      Serial.println(
          "[k1_sync_diag] connect_setup_fail role=follower step=create_client");
      return false;
    }
    s_client->setClientCallbacks(&s_client_cb, false);
    s_client->setConnectionParams(kConnIntervalUnits, kConnIntervalUnits,
                                  kConnLatency, kSupervisionUnits);
  }
  // Preserve discovered attribute objects across reconnects so a callback/task
  // overlap cannot free a locally snapshotted characteristic pointer.
  if (!s_client->connect(addr, false)) {
    Serial.printf(
        "[k1_sync_diag] connect_call_fail role=follower last_error=%d\n",
        s_client->getLastError());
    return false;
  }
  const uint32_t generation = s_connection_generation;
  if (!connection_is_current(generation)) {
    return disconnect_after_failure("connection_generation");
  }
  NimBLERemoteService* svc = s_client->getService(kSyncServiceUuid);
  if (!svc) {
    return disconnect_after_failure("service");
  }
  NimBLERemoteCharacteristic* stream =
      svc->getCharacteristic(kSyncStreamCharUuid);
  NimBLERemoteCharacteristic* clock =
      svc->getCharacteristic(kSyncClockCharUuid);
  if (!stream) {
    return disconnect_after_failure("stream_characteristic");
  }
  if (!clock) {
    return disconnect_after_failure("clock_characteristic");
  }
  if (!connection_is_current(generation) ||
      !stream->subscribe(true, on_stream_notify)) {
    return disconnect_after_failure("stream_subscribe");
  }
  if (!connection_is_current(generation) ||
      !clock->subscribe(true, on_clock_notify)) {
    return disconnect_after_failure("clock_subscribe");
  }
  NegotiatedSnapshot settled{};
  if (!read_stable_client_snapshot(generation, &settled)) {
    return disconnect_after_failure("negotiated_stability");
  }
  portENTER_CRITICAL(&s_state_mux);
  const bool publish =
      s_connected && s_connection_generation == generation;
  if (publish) {
    reset_link_state();
    begin_clock_burst();
    s_last_clock_request_us = now_us();
    s_clock_send_pending = true;
    s_stream_rx = stream;
    s_clock_rx = clock;
    s_conn_handle = settled.handle;
    ++s_link_epoch;
    s_ready_snapshot = settled;
    s_ready_snapshot_valid = true;
    s_ready_announcement = true;
    s_linked = true;
  }
  const uint32_t epoch = s_link_epoch;
  portEXIT_CRITICAL(&s_state_mux);
  if (!publish) {
    return false;
  }

  Serial.printf("[k1_sync] link up role=follower epoch=%u handle=%u mtu=%u\n",
                (unsigned)epoch, (unsigned)settled.handle,
                (unsigned)settled.mtu);
  Serial.printf(
      "[k1_sync] negotiated role=follower epoch=%u interval_units=%u "
      "latency=%u mtu=%u phy_tx=%u phy_rx=%u\n",
      (unsigned)epoch, (unsigned)settled.interval_units,
      (unsigned)settled.latency, (unsigned)settled.mtu,
      (unsigned)settled.phy_tx, (unsigned)settled.phy_rx);

  portENTER_CRITICAL(&s_state_mux);
  const bool still_current =
      s_connected && s_connection_generation == generation;
  s_ready_announcement = false;
  portEXIT_CRITICAL(&s_state_mux);
  if (!still_current) {
    return false;
  }
  log_client_actual("ready", s_client);
  return true;
}

void begin_follower() {
  s_role_init_ok = false;
  const bool init_ok =
      NimBLEDevice::isInitialized() || NimBLEDevice::init(kSyncDeviceName);
  const bool mtu_pref_ok = init_ok && NimBLEDevice::setMTU(kSyncMtu);
  s_clock_response_queue = xQueueCreateStatic(
      kClockResponseQueueCapacity, sizeof(ClockResponse),
      s_clock_response_queue_storage, &s_clock_response_queue_struct);
  const bool queue_ok = s_clock_response_queue != nullptr;
  s_role_init_ok = init_ok && mtu_pref_ok && queue_ok;
  Serial.printf(
      "[k1_sync_diag] init role=follower ok=%u mtu_pref_ok=%u queue_ok=%u\n",
      init_ok ? 1U : 0U, mtu_pref_ok ? 1U : 0U, queue_ok ? 1U : 0U);
  Serial.println("[k1_sync] begin role=follower");
}

void follower_apply_service() {
  // Drain received stream records: log rx (receipt) then apply (render consume).
  uint32_t tail = s_stream_tail;
  while (tail != s_stream_head) {
    const uint32_t seq = s_stream_ring[tail].seq;
    const uint64_t t_leader = s_stream_ring[tail].t_leader;
    const uint64_t t_rx = s_stream_ring[tail].t_rx;
    tail = (tail + 1) & (kStreamRingSize - 1);
    s_stream_tail = tail;

    // loss / dup accounting on the dense leader seq.
    if (s_have_last_rx_seq) {
      if (seq == s_last_rx_seq) {
        ++s_stream_dup;
      } else if (seq > s_last_rx_seq + 1) {
        s_stream_loss += (seq - s_last_rx_seq - 1);
      }
    }
    if (!s_have_last_rx_seq || seq > s_last_rx_seq) {
      s_last_rx_seq = seq;
      s_have_last_rx_seq = true;
    }

    Serial.printf("[k1_sync] rx seq=%u t_leader_us=%llu t_local_us=%llu\n",
                  (unsigned)seq, (unsigned long long)t_leader,
                  (unsigned long long)t_rx);

    // Injected fault: drop ~10% deterministically, or delay the apply stamp.
    if (s_fault == kFaultDrop10) {
      if ((s_drop_phase++ % 10u) == 0u) {
        continue;  // dropped before apply
      }
    }
    uint64_t t_render = now_us();
    if (s_fault == kFaultDelay5) {
      t_render += 5000;
    } else if (s_fault == kFaultDelay20) {
      t_render += 20000;
    }
    Serial.printf("[k1_sync] apply seq=%u t_render_us=%llu\n",
                  (unsigned)seq, (unsigned long long)t_render);
  }
}

void follower_clock_service() {
  portENTER_CRITICAL(&s_state_mux);
  const bool linked = s_linked && s_clock_rx != nullptr;
  portEXIT_CRITICAL(&s_state_mux);
  if (!linked) {
    return;
  }
  if (s_clock_send_pending) {
    s_clock_send_pending = false;
    send_clock_request();
    return;
  }
  if (s_burst_remaining > 0 &&
      (now_us() - s_last_clock_request_us) >= kClockRetryUs) {
    send_clock_request();
    return;
  }
  if ((now_us() - s_last_clock_maint_us) >= kClockMaintPeriodUs) {
    s_last_clock_maint_us = now_us();
    if (s_burst_remaining == 0) {  // don't collide with an in-flight burst
      send_clock_request();
    }
  }
}
#endif  // FOLLOWER

void sync_io_task(void*) {
#if defined(K1_SYNC_ROLE_FOLLOWER)
  NimBLEScan* scan = NimBLEDevice::getScan();
  scan->setScanCallbacks(&s_scan_cb, false);
  scan->setActiveScan(true);
#endif
  for (;;) {
#if defined(K1_SYNC_ROLE_LEADER)
    portENTER_CRITICAL(&s_state_mux);
    const bool restart_pending = s_adv_restart_pending;
    const bool connected = s_connected;
    const uint32_t generation = s_connection_generation;
    const int restart_reason = s_adv_restart_reason;
    portEXIT_CRITICAL(&s_state_mux);
    if (restart_pending && !connected && now_us() >= s_adv_retry_after_us) {
      NimBLEAdvertising* adv = NimBLEDevice::getAdvertising();
      const bool started = adv && adv->start();
      const bool active = adv && adv->isAdvertising();
      Serial.printf("[k1_sync_diag] adv_restart start=%u active=%u reason=%d\n",
                    started ? 1U : 0U, active ? 1U : 0U, restart_reason);
      portENTER_CRITICAL(&s_state_mux);
      if (s_connection_generation == generation && !s_connected) {
        s_adv_restart_pending = !active;
        if (!active) {
          s_adv_retry_after_us = now_us() + 500000U;
        }
      } else if (s_connected) {
        s_adv_restart_pending = false;
      }
      portEXIT_CRITICAL(&s_state_mux);
    }
    leader_ready_service();
    leader_stream_service();
#elif defined(K1_SYNC_ROLE_FOLLOWER)
    ClockResponse response{};
    while (xQueueReceive(s_clock_response_queue, &response, 0) == pdTRUE) {
      ingest_clock_response(response.data, sizeof(response.data),
                            response.t4_us, response.generation);
    }
    static uint32_t reported_response_drops = 0;
    portENTER_CRITICAL(&s_state_mux);
    const uint32_t response_drops = s_clock_response_drops;
    portEXIT_CRITICAL(&s_state_mux);
    if (response_drops != reported_response_drops) {
      reported_response_drops = response_drops;
      Serial.printf("[k1_sync_diag] clock_response_drop count=%u\n",
                    (unsigned)reported_response_drops);
    }
    follower_clock_service();

    portENTER_CRITICAL(&s_state_mux);
    const bool linked = s_linked;
    const bool connected = s_connected;
    portEXIT_CRITICAL(&s_state_mux);
    portENTER_CRITICAL(&s_target_mux);
    const bool have_target = s_have_target;
    portEXIT_CRITICAL(&s_target_mux);
    if (!linked && !connected && !have_target && !scan->isScanning()) {
      const bool started = scan->start(0, false);
      Serial.printf("[k1_sync_diag] scan_start ok=%u active=%u\n",
                    started ? 1U : 0U, scan->isScanning() ? 1U : 0U);
      if (!started) {
        vTaskDelay(pdMS_TO_TICKS(500));
      }
    } else if (!linked && !connected && have_target &&
               !connect_and_subscribe()) {
      portENTER_CRITICAL(&s_target_mux);
      s_have_target = false;
      portEXIT_CRITICAL(&s_target_mux);
      vTaskDelay(pdMS_TO_TICKS(800));
    }
#endif
    vTaskDelay(pdMS_TO_TICKS(5));
  }
}

void health_service() {
  if ((now_us() - s_last_health_us) < kHealthPeriodUs) {
    return;
  }
  s_last_health_us = now_us();
  const uint32_t heap_min =
      (uint32_t)heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL);
#if defined(K1_SYNC_ROLE_LEADER) && defined(SB_K1_BLE_REMOTED)
  const int dial = sb_k1_ble_remoted_is_linked() ? 1 : 0;
#else
  const int dial = 0;
#endif
  // ap_p95_us: the probe harness exposes no Core-0 AP p95 surface here -> 0.
#if defined(K1_SYNC_ROLE_LEADER)
  constexpr const char* kRole = "leader";
#else
  constexpr const char* kRole = "follower";
#endif
  Serial.printf(
      "[k1_sync] health role=%s fps=%.2f heap_min=%u ap_p95_us=%u dial_linked=%d "
      "loss=%u dup=%u\n",
      kRole, LED_FPS, (unsigned)heap_min, 0u, dial,
      (unsigned)s_stream_loss, (unsigned)s_stream_dup);

#if defined(K1_SYNC_ROLE_FOLLOWER)
  portENTER_CRITICAL(&s_state_mux);
  const bool clk_valid = s_clk_valid;
  const int64_t est_offset_us = s_est_offset_us;
  const uint32_t clk_rtt_us = s_clk_rtt_us;
  const uint32_t clk_samples = s_clk_samples;
  portEXIT_CRITICAL(&s_state_mux);
  if (clk_valid) {
    Serial.printf(
        "[k1_sync] clk role=follower t_local_us=%llu est_offset_us=%lld "
        "rtt_us=%u n=%u\n",
        (unsigned long long)now_us(), (long long)est_offset_us,
        (unsigned)clk_rtt_us, (unsigned)clk_samples);
  }
#endif
}

}  // namespace

// ── Public interface ────────────────────────────────────────────────────────
void begin() {
  pinMode(kTrigOutPin, OUTPUT);
  digitalWrite(kTrigOutPin, LOW);
  pinMode(kTrigInPin, INPUT_PULLDOWN);
  attachInterrupt(digitalPinToInterrupt(kTrigInPin), trig_in_isr, RISING);
#if defined(K1_SYNC_ROLE_LEADER)
  begin_leader();
#elif defined(K1_SYNC_ROLE_FOLLOWER)
  begin_follower();
#else
#error "k1_sync_probe env must define K1_SYNC_ROLE_LEADER or K1_SYNC_ROLE_FOLLOWER"
#endif
  const BaseType_t task_result =
      s_role_init_ok
          ? xTaskCreatePinnedToCore(sync_io_task, "k1_sync_io", 4096, nullptr,
                                    1, &s_io_task, 1)
          : pdFAIL;
  Serial.printf("[k1_sync_diag] io_task role=%s ok=%u core=1\n",
#if defined(K1_SYNC_ROLE_LEADER)
                "leader",
#else
                "follower",
#endif
                task_result == pdPASS ? 1U : 0U);
}

void poll() {
  link_lifecycle_service();
#if defined(K1_SYNC_ROLE_LEADER)
  // Periodic readiness and stream-notify work are owned by sync_io_task on
  // Core 1. The connection-bound clock reply stays in NimBLE's write callback
  // so its t2/t3 timestamps describe the actual response.
#elif defined(K1_SYNC_ROLE_FOLLOWER)
  follower_apply_service();
#endif
  trig_service();
  health_service();
}

bool is_linked() { return s_linked; }

void status() {
  portENTER_CRITICAL(&s_state_mux);
  const bool ready =
      s_linked && s_ready_snapshot_valid && !s_ready_announcement;
  const uint32_t epoch = s_link_epoch;
  const NegotiatedSnapshot snapshot = s_ready_snapshot;
  portEXIT_CRITICAL(&s_state_mux);

#if defined(K1_SYNC_ROLE_LEADER)
  constexpr const char* kRole = "leader";
#else
  constexpr const char* kRole = "follower";
#endif
  Serial.printf("SYNC_STATUS: role=%s linked=%u\n", kRole, ready ? 1U : 0U);
  if (!ready) {
    return;
  }
  Serial.printf("[k1_sync] link up role=%s epoch=%u handle=%u mtu=%u\n", kRole,
                (unsigned)epoch, (unsigned)snapshot.handle,
                (unsigned)snapshot.mtu);
  Serial.printf(
      "[k1_sync] negotiated role=%s epoch=%u interval_units=%u "
      "latency=%u mtu=%u phy_tx=%u phy_rx=%u\n",
      kRole, (unsigned)epoch, (unsigned)snapshot.interval_units,
      (unsigned)snapshot.latency, (unsigned)snapshot.mtu,
      (unsigned)snapshot.phy_tx, (unsigned)snapshot.phy_rx);
}

bool set_fault(const char* mode) {
  if (mode == nullptr) {
    return false;
  }
  if (strcmp(mode, "off") == 0) {
    s_fault = kFaultOff;
  } else if (strcmp(mode, "delay5") == 0) {
    s_fault = kFaultDelay5;
  } else if (strcmp(mode, "delay20") == 0) {
    s_fault = kFaultDelay20;
  } else if (strcmp(mode, "drop10") == 0) {
    s_fault = kFaultDrop10;
  } else {
    return false;
  }
  Serial.printf("[k1_sync] fault=%s\n", mode);
  return true;
}

}  // namespace k1_sync

#endif  // SB_K1_SYNC_PROBE
