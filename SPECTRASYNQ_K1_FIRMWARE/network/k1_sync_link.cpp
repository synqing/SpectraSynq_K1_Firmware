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
#include "freertos/task.h"

// Render-rate EMA maintained by the LED task (system/globals.h); read-only here.
extern float LED_FPS;

#if defined(K1_SYNC_ROLE_LEADER)
// The leader env also compiles the BLE Remoted central; dial-link state feeds the
// health line's dial_linked field.
bool sb_k1_ble_remoted_is_linked();
#endif

namespace k1_sync {
namespace {

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
constexpr uint32_t kClockBurstSamples = 16;  // RTT burst at link-up / recovery
constexpr uint32_t kHealthPeriodUs = 1000000;  // 1 Hz health line

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

// ── NimBLE handles ──────────────────────────────────────────────────────────
volatile bool s_linked = false;
volatile uint16_t s_conn_handle = 0xFFFF;

#if defined(K1_SYNC_ROLE_LEADER)
NimBLEServer* s_server = nullptr;
NimBLECharacteristic* s_stream_char = nullptr;
NimBLECharacteristic* s_clock_char = nullptr;
#elif defined(K1_SYNC_ROLE_FOLLOWER)
NimBLEClient* s_client = nullptr;
NimBLERemoteCharacteristic* s_stream_rx = nullptr;
NimBLERemoteCharacteristic* s_clock_rx = nullptr;
volatile bool s_have_target = false;
volatile bool s_scanning = false;
NimBLEAddress s_target_addr;
portMUX_TYPE s_target_mux = portMUX_INITIALIZER_UNLOCKED;
TaskHandle_t s_scan_task = nullptr;
#endif

// ── Cadence bookkeeping ─────────────────────────────────────────────────────
uint64_t s_last_stream_us = 0;
uint64_t s_last_clock_maint_us = 0;
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
  s_clk_valid = false;
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
void send_clock_request() {
  if (!s_clock_rx) {
    return;
  }
  ++s_burst_seq;
  uint8_t pkt[13];
  pkt[0] = kClkReq;
  const uint32_t bs = s_burst_seq;
  memcpy(&pkt[1], &bs, sizeof(bs));
  const uint64_t t1 = now_us();
  memcpy(&pkt[5], &t1, sizeof(t1));
  s_clock_rx->writeValue(pkt, sizeof(pkt), false);
}

void ingest_clock_response(const uint8_t* data, size_t len) {
  if (len < 29 || data[0] != kClkRsp) {
    return;
  }
  const uint64_t t4 = now_us();
  uint64_t t1, t2, t3;
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
      s_est_offset_us = s_burst_best_offset;
      s_clk_rtt_us = s_burst_best_rtt;
      s_clk_samples = kClockBurstSamples;
      s_clk_valid = true;
    } else {
      send_clock_request();  // continue the burst
    }
  } else {
    // 1 Hz maintenance sample: min-filter this single round-trip and track skew.
    if (rtt_u <= s_clk_rtt_us || !s_clk_valid) {
      s_est_offset_us = offset;
      s_clk_rtt_us = rtt_u;
    }
    s_clk_samples = 1;
    s_clk_valid = true;
  }
}
#endif  // FOLLOWER

// ── NimBLE callbacks ─────────────────────────────────────────────────────────
#if defined(K1_SYNC_ROLE_LEADER)
class ClockWriteCB : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* chr, NimBLEConnInfo& info) override {
    const uint64_t t2 = now_us();  // leader receive time (stamp ASAP)
    NimBLEAttValue v = chr->getValue();
    if (v.length() < 13 || v.data()[0] != kClkReq) {
      return;
    }
    uint8_t rsp[29];
    rsp[0] = kClkRsp;
    memcpy(&rsp[1], v.data() + 1, 4);   // echo burst_seq
    memcpy(&rsp[5], v.data() + 5, 8);   // echo t1
    memcpy(&rsp[13], &t2, sizeof(t2));  // t2 leader recv
    const uint64_t t3 = now_us();       // leader send time
    memcpy(&rsp[21], &t3, sizeof(t3));
    if (s_clock_char) {
      s_clock_char->notify(rsp, sizeof(rsp), info.getConnHandle());
    }
  }
};
ClockWriteCB s_clock_write_cb;

class ServerCB : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer* server, NimBLEConnInfo& info) override {
    s_conn_handle = info.getConnHandle();
    s_linked = true;
    reset_link_state();
    server->updateConnParams(s_conn_handle, kConnIntervalUnits, kConnIntervalUnits,
                             kConnLatency, kSupervisionUnits);
    server->updatePhy(s_conn_handle, BLE_GAP_LE_PHY_2M_MASK, BLE_GAP_LE_PHY_2M_MASK, 0);
    Serial.printf("[k1_sync] link up role=leader handle=%u mtu=%u\n",
                  (unsigned)s_conn_handle, (unsigned)server->getPeerMTU(s_conn_handle));
    // keep advertising so the link can be re-established after a drop
    NimBLEDevice::getAdvertising()->start();
  }
  void onDisconnect(NimBLEServer*, NimBLEConnInfo&, int) override {
    s_linked = false;
    s_conn_handle = 0xFFFF;
    NimBLEDevice::getAdvertising()->start();
    Serial.println("[k1_sync] link down role=leader");
  }
  void onMTUChange(uint16_t mtu, NimBLEConnInfo&) override {
    Serial.printf("[k1_sync] mtu granted=%u\n", (unsigned)mtu);
  }
};
ServerCB s_server_cb;

void begin_leader() {
  // NimBLE is already initialised by sb_k1_ble_remoted_begin() on this env; only
  // init if (defensively) it is not, and never re-init.
  if (!NimBLEDevice::isInitialized()) {
    NimBLEDevice::init(kSyncDeviceName);
  }
  NimBLEDevice::setMTU(kSyncMtu);
  s_server = NimBLEDevice::createServer();
  s_server->setCallbacks(&s_server_cb, false);
  NimBLEService* svc = s_server->createService(kSyncServiceUuid);
  s_stream_char = svc->createCharacteristic(
      kSyncStreamCharUuid, NIMBLE_PROPERTY::NOTIFY | NIMBLE_PROPERTY::READ);
  s_clock_char = svc->createCharacteristic(
      kSyncClockCharUuid,
      NIMBLE_PROPERTY::NOTIFY | NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR);
  s_clock_char->setCallbacks(&s_clock_write_cb);
  svc->start();
  NimBLEAdvertising* adv = NimBLEDevice::getAdvertising();
  adv->addServiceUUID(kSyncServiceUuid);
  adv->setName(kSyncDeviceName);
  adv->start();
  Serial.printf("[k1_sync] begin role=leader adv=%s\n", kSyncDeviceName);
}

void leader_stream_service() {
  if (!s_linked || !s_stream_char) {
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
  s_stream_char->notify(pkt, sizeof(pkt), s_conn_handle);
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

void on_clock_notify(NimBLERemoteCharacteristic*, uint8_t* data, size_t len, bool) {
  ingest_clock_response(data, len);
}

class ScanCB : public NimBLEScanCallbacks {
  void onResult(const NimBLEAdvertisedDevice* dev) override {
    if (s_have_target || s_linked) {
      return;
    }
    const bool match = (dev->getName() == kSyncDeviceName) ||
                       (dev->haveServiceUUID() &&
                        dev->isAdvertisingService(NimBLEUUID(kSyncServiceUuid)));
    if (!match) {
      return;
    }
    portENTER_CRITICAL(&s_target_mux);
    s_target_addr = dev->getAddress();
    s_have_target = true;
    portEXIT_CRITICAL(&s_target_mux);
    NimBLEDevice::getScan()->stop();
    s_scanning = false;
  }
  void onScanEnd(const NimBLEScanResults&, int) override { s_scanning = false; }
};
ScanCB s_scan_cb;

class ClientCB : public NimBLEClientCallbacks {
  void onConnect(NimBLEClient* client) override {
    s_linked = true;
    s_conn_handle = client->getConnHandle();
    reset_link_state();
    client->updateConnParams(kConnIntervalUnits, kConnIntervalUnits, kConnLatency,
                             kSupervisionUnits);
    client->updatePhy(BLE_GAP_LE_PHY_2M_MASK, BLE_GAP_LE_PHY_2M_MASK, 0);
  }
  void onDisconnect(NimBLEClient*, int) override {
    s_linked = false;
    s_have_target = false;
    s_stream_rx = nullptr;
    s_clock_rx = nullptr;
  }
  void onConnectFail(NimBLEClient*, int) override {
    s_linked = false;
    s_have_target = false;
  }
};
ClientCB s_client_cb;

bool connect_and_subscribe() {
  NimBLEAddress addr;
  portENTER_CRITICAL(&s_target_mux);
  addr = s_target_addr;
  portEXIT_CRITICAL(&s_target_mux);
  if (!s_client) {
    s_client = NimBLEDevice::createClient();
    s_client->setClientCallbacks(&s_client_cb, false);
    s_client->setConnectionParams(kConnIntervalUnits, kConnIntervalUnits,
                                  kConnLatency, kSupervisionUnits);
  }
  if (!s_client->connect(addr)) {
    return false;
  }
  NimBLERemoteService* svc = s_client->getService(kSyncServiceUuid);
  if (!svc) {
    s_client->disconnect();
    return false;
  }
  s_stream_rx = svc->getCharacteristic(kSyncStreamCharUuid);
  s_clock_rx = svc->getCharacteristic(kSyncClockCharUuid);
  if (!s_stream_rx || !s_clock_rx) {
    s_client->disconnect();
    return false;
  }
  if (!s_stream_rx->subscribe(true, on_stream_notify) ||
      !s_clock_rx->subscribe(true, on_clock_notify)) {
    s_client->disconnect();
    return false;
  }
  Serial.printf("[k1_sync] link up role=follower handle=%u mtu=%u\n",
                (unsigned)s_conn_handle, (unsigned)s_client->getMTU());
  begin_clock_burst();
  send_clock_request();
  return true;
}

void scan_task(void*) {
  NimBLEScan* scan = NimBLEDevice::getScan();
  scan->setScanCallbacks(&s_scan_cb, false);
  scan->setActiveScan(true);
  for (;;) {
    if (!s_linked) {
      if (!s_have_target) {
        if (!s_scanning) {
          s_scanning = true;
          scan->start(0, false);
        }
      } else if (!connect_and_subscribe()) {
        s_have_target = false;
        vTaskDelay(pdMS_TO_TICKS(800));
      }
    }
    vTaskDelay(pdMS_TO_TICKS(150));
  }
}

void begin_follower() {
  if (!NimBLEDevice::isInitialized()) {
    NimBLEDevice::init(kSyncDeviceName);
  }
  NimBLEDevice::setMTU(kSyncMtu);
  // The scan/connect loop is the only task this TU adds: Core 1, priority 1
  // (NimBLE's own host task already owns Core 0; we stay off the audio core).
  xTaskCreatePinnedToCore(scan_task, "k1_sync_scan", 4096, nullptr, 1, &s_scan_task, 1);
  Serial.printf("[k1_sync] begin role=follower scan for %s\n", kSyncDeviceName);
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
  if (!s_linked || !s_clock_rx) {
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

void health_service() {
  if ((now_us() - s_last_health_us) < kHealthPeriodUs) {
    return;
  }
  s_last_health_us = now_us();
  const uint32_t heap_min =
      (uint32_t)heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL);
#if defined(K1_SYNC_ROLE_LEADER)
  const int dial = sb_k1_ble_remoted_is_linked() ? 1 : 0;
#else
  const int dial = 0;
#endif
  // ap_p95_us: the probe harness exposes no Core-0 AP p95 surface here -> 0.
  Serial.printf(
      "[k1_sync] health fps=%.2f heap_min=%u ap_p95_us=%u dial_linked=%d "
      "loss=%u dup=%u\n",
      LED_FPS, (unsigned)heap_min, 0u, dial, (unsigned)s_stream_loss,
      (unsigned)s_stream_dup);

  if (s_clk_valid) {
    Serial.printf("[k1_sync] clk est_offset_us=%lld rtt_us=%u n=%u\n",
                  (long long)s_est_offset_us, (unsigned)s_clk_rtt_us,
                  (unsigned)s_clk_samples);
  }
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
}

void poll() {
  trig_service();
  health_service();
#if defined(K1_SYNC_ROLE_LEADER)
  leader_stream_service();
#elif defined(K1_SYNC_ROLE_FOLLOWER)
  follower_apply_service();
  follower_clock_service();
#endif
}

bool is_linked() { return s_linked; }

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
