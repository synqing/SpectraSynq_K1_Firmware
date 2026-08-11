#include "ble_midi_transport.h"
#include "k1_ble_midi_map.h"
#include "k1_deck_identity_v1.h"
#include "k1_deck_state_v1.h"
#include "deck_state_rx.h"

#include <cstring>
#include <cmath>
#include <atomic>

#if defined(CONFIG_ESP_HOSTED_ENABLE_BT_NIMBLE) && defined(CONFIG_NIMBLE_ENABLED) && __has_include(<host/ble_gap.h>)
#define TAB5_BLE_GATT_AVAILABLE 1
#else
#define TAB5_BLE_GATT_AVAILABLE 0
#endif

// Captain HCI-path diagnosis (2026-08-07): gated verbose INIT/version/HCI
// probes. Default off — enable with -DTAB5_HCI_PATH_DIAG=1.
#ifndef TAB5_HCI_PATH_DIAG
#define TAB5_HCI_PATH_DIAG 0
#endif
#ifndef TAB5_BLE_VERBOSE_DIAG
#define TAB5_BLE_VERBOSE_DIAG 0
#endif
#ifndef TAB5_PRODUCTION_BUILD
#define TAB5_PRODUCTION_BUILD 0
#endif

#if TAB5_PRODUCTION_BUILD && (TAB5_HCI_PATH_DIAG || TAB5_BLE_VERBOSE_DIAG)
#error "Production Tab5 build cannot enable HCI or per-value diagnostics"
#endif

#if TAB5_BLE_GATT_AVAILABLE
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <host/ble_gap.h>
#include <host/ble_att.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>
#include "esp32-hal-hosted.h"
#include "esp_log.h"
#include <Wire.h>

// Avoid #include "esp_hosted.h" — that header #errors without the full
 // CONFIG_SLAVE_IDF_TARGET_* set seen by the prebuilt component Kconfig.
typedef struct {
  uint32_t major1;
  uint32_t minor1;
  uint32_t patch1;
} esp_hosted_coprocessor_fwver_t;

// Arduino P4 hosted headers omit a clean public "transport up" API; these
// symbols live in libespressif__esp_hosted and match transport_drv.h / api.
extern "C" {
#if !defined(TAB5_HOSTED_AB_VERSION)
int esp_hosted_connect_to_slave(void);
#endif
uint8_t is_transport_tx_ready(void);
int esp_hosted_get_coprocessor_fwversion(esp_hosted_coprocessor_fwver_t *ver_info);
void print_capabilities(uint32_t cap);
}

extern "C" {
void h0_wire_log_counters(const char *where);
}

#include "esp_hosted_interface.h"

// Tab5 P4↔C6 SDIO map (m5stack_tab5 / Espressif #127). Must override
// BOARD_SDIO_ESP_HOSTED_* from esp32-p4-evboard variant (18/19/14/…/54)
// before hostedInit — CONFIG_ESP_SDIO_PIN_* alone is ignored when
// BOARD_HAS_SDIO_ESP_HOSTED is set (esp32-hal-hosted.c).
static constexpr int8_t kTab5SdioClk = 12;
static constexpr int8_t kTab5SdioCmd = 13;
static constexpr int8_t kTab5SdioD0 = 11;
static constexpr int8_t kTab5SdioD1 = 10;
static constexpr int8_t kTab5SdioD2 = 9;
static constexpr int8_t kTab5SdioD3 = 8;
static constexpr int8_t kTab5SdioRst = 15;

#if TAB5_HCI_PATH_DIAG
// Raise noisy hosted tags for one boot of INIT/capability forensics.
static void hci_path_raise_hosted_logs(void)
{
  esp_log_level_set("H_SDIO_DRV", ESP_LOG_DEBUG);
  esp_log_level_set("sdio_wrapper", ESP_LOG_DEBUG);
  esp_log_level_set("transport", ESP_LOG_DEBUG);
  esp_log_level_set("RPC_WRAP", ESP_LOG_INFO);
  esp_log_level_set("rpc_core", ESP_LOG_INFO);
  esp_log_level_set("vhci_drv", ESP_LOG_DEBUG);
  esp_log_level_set("h0_wire", ESP_LOG_INFO);
  esp_log_level_set("NimBLE", ESP_LOG_INFO);
  Serial.println("[hci-diag] raised H_SDIO_DRV/transport/RPC_WRAP/vhci_drv/h0_wire log levels");
  /* Evaluated macros from headers linked into this binary (Gate H0). */
  Serial.printf("[h0] ABI ESP_SERIAL_IF=%d ESP_HCI_IF=%d ESP_INVALID_IF=%d\n",
                static_cast<int>(ESP_SERIAL_IF), static_cast<int>(ESP_HCI_IF),
                static_cast<int>(ESP_INVALID_IF));
  static_assert(ESP_SERIAL_IF == 3, "ESP_SERIAL_IF must be 3");
  static_assert(ESP_HCI_IF == 4, "ESP_HCI_IF must be 4");
}

// M5 Tab5: PI4IOE @0x44 P0 = WLAN_PWR_EN (M5Unified Power_Class + m5stack_tab5.c).
// Read via Wire (already started by M5.begin) — avoid pulling M5Unified here.
static void hci_path_log_wlan_pwr(void)
{
  // Prefer the inited Wire used by M5 on Tab5 (SDA/SCL already configured).
  Wire.beginTransmission(0x44);
  Wire.write(static_cast<uint8_t>(0x05));  // PI4IO_REG_OUT_SET
  const uint8_t wr = Wire.endTransmission(false);
  const uint8_t n = Wire.requestFrom(static_cast<uint8_t>(0x44), static_cast<uint8_t>(1));
  const int out_set = (n >= 1) ? Wire.read() : -1;

  Wire.beginTransmission(0x44);
  Wire.write(static_cast<uint8_t>(0x03));  // PI4IO_REG_IO_DIR
  const uint8_t wr2 = Wire.endTransmission(false);
  const uint8_t n2 = Wire.requestFrom(static_cast<uint8_t>(0x44), static_cast<uint8_t>(1));
  const int io_dir = (n2 >= 1) ? Wire.read() : -1;

  if (out_set < 0 || wr != 0 || wr2 != 0) {
    Serial.printf(
        "[hci-diag] PI4IOE1(0x44) read FAILED wr=%u/%u n=%u/%u "
        "(WLAN_PWR_EN unknown — I2C path)\n",
        wr, wr2, n, n2);
    return;
  }
  const bool wlan_pwr = (out_set & 0x01) != 0;
  Serial.printf(
      "[hci-diag] PI4IOE1(0x44) OUT_SET=0x%02X IO_DIR=0x%02X WLAN_PWR_EN(P0)=%s\n",
      out_set, io_dir < 0 ? 0 : io_dir, wlan_pwr ? "HIGH" : "LOW");
}

static void hci_path_log_c6_version(void)
{
  esp_hosted_coprocessor_fwver_t ver = {};
  const int rc = esp_hosted_get_coprocessor_fwversion(&ver);
  if (rc != 0) {
    Serial.printf(
        "[hci-diag] esp_hosted_get_coprocessor_fwversion FAILED rc=%d "
        "(RPC/version exchange did not complete)\n",
        rc);
    return;
  }
  Serial.printf("[hci-diag] C6 coprocessor fwversion %lu.%lu.%lu (rc=0)\n",
                static_cast<unsigned long>(ver.major1),
                static_cast<unsigned long>(ver.minor1),
                static_cast<unsigned long>(ver.patch1));
}

// Capability bitmap: H0 wraps process_capabilities — dump counters/cap here.
static void hci_path_log_capabilities(void)
{
  Serial.println(
      "[hci-diag] capability bitmap: expect h0_wire process_capabilities "
      "bitmap=0x… (wrapped) plus hosted print_capabilities feature lines.");
  (void)&print_capabilities;
  h0_wire_log_counters("post_transport_ready");
}
#endif  // TAB5_HCI_PATH_DIAG

// Wait for ESP-Hosted SDIO (P4↔C6) before BLEDevice::init → NimBLE HCI Reset.
// Without this, HCI CMD fires at transport_up(0) → H_SDIO_DRV tx fail + BLE_HS_EUNKNOWN.
static bool wait_hosted_sdio_ready(uint32_t timeout_ms)
{
#if TAB5_HCI_PATH_DIAG
  hci_path_raise_hosted_logs();
  hci_path_log_wlan_pwr();
#endif

  // Pins MUST be set before any hostedInit / hostedInitBLE / BLEDevice::init.
  if (!hostedSetPins(kTab5SdioClk, kTab5SdioCmd, kTab5SdioD0, kTab5SdioD1,
                     kTab5SdioD2, kTab5SdioD3, kTab5SdioRst)) {
    Serial.println("[ble-midi] hostedSetPins FAILED (Tab5 SDIO map)");
    return false;
  }
  Serial.printf(
      "[ble-midi] SDIO pins Tab5 clk=%d cmd=%d d0=%d d1=%d d2=%d d3=%d rst=%d\n",
      static_cast<int>(kTab5SdioClk), static_cast<int>(kTab5SdioCmd),
      static_cast<int>(kTab5SdioD0), static_cast<int>(kTab5SdioD1),
      static_cast<int>(kTab5SdioD2), static_cast<int>(kTab5SdioD3),
      static_cast<int>(kTab5SdioRst));

  if (!hostedInitBLE()) {
    Serial.println("[ble-midi] hostedInitBLE FAILED (SDIO/ESP-Hosted)");
    return false;
  }
#if !defined(TAB5_HOSTED_AB_VERSION)
  // 2.0.13 API only — absent on ESP-Hosted 1.4.x (A/B env).
  (void)esp_hosted_connect_to_slave();
#else
  Serial.println("[ble-midi] AB 1.4.x: skip esp_hosted_connect_to_slave (not in API)");
#endif

  const uint32_t start = millis();
  while ((millis() - start) < timeout_ms) {
    if (is_transport_tx_ready()) {
      Serial.printf("[ble-midi] SDIO transport TX ready after %lu ms\n",
                    static_cast<unsigned long>(millis() - start));
#if TAB5_HCI_PATH_DIAG
      hci_path_log_c6_version();
      hci_path_log_capabilities();
      hci_path_log_wlan_pwr();
#endif
      return true;
    }
    delay(50);
  }
  Serial.printf(
      "[ble-midi] FAIL: SDIO transport_up still 0 after %lu ms "
      "(C6 not speaking HCI over ESP-Hosted — check C6 FW / power)\n",
      static_cast<unsigned long>(timeout_ms));
#if TAB5_HCI_PATH_DIAG
  hci_path_log_c6_version();
  hci_path_log_wlan_pwr();
#endif
  return false;
}
#endif

namespace {

static constexpr uint8_t kNrpnParamMsb = 99;
static constexpr uint8_t kNrpnParamLsb = 98;
static constexpr uint8_t kNrpnDataMsb = 6;
static constexpr uint8_t kNrpnDataLsb = 38;

static bool gInitialised = false;
static uint32_t gLastStatusLogMs = 0;

#if TAB5_BLE_GATT_AVAILABLE
static BLEServer* gServer = nullptr;
static BLECharacteristic* gMidiCharacteristic = nullptr;
static BLECharacteristic* gIdentityCharacteristic = nullptr;
static BLECharacteristic* gStateCharacteristic = nullptr;
static bool gConnected = false;
static uint16_t gConnHandle = BLE_HS_CONN_HANDLE_NONE;
static uint8_t gIdentityWire[K1_DECK_IDENTITY_V1_SIZE] = {};

// NimBLE callbacks run on Core 0. loopTask is the sole owner of connection
// lifecycle, confirmed Deck state, recovery, cached RSSI and every LVGL call.
// Link events have an independent static queue, so state bursts cannot hide a
// disconnect. Callback work is bounded copy-only: no String, log, HCI or BLE
// lifecycle call is permitted.
static constexpr UBaseType_t kLinkQueueCapacity = 4;
static constexpr UBaseType_t kPayloadQueueCapacity = 12;
static constexpr uint8_t kPayloadDrainLimit = 8;
static constexpr uint32_t kPayloadDrainBudgetUs = 1000;

enum class LinkEventType : uint8_t { Connected = 0, Disconnected };
enum class PayloadEventType : uint8_t { Midi = 0, State };

struct LinkEvent {
  LinkEventType type;
  uint16_t conn_handle;
  uint32_t ingress_generation;
};

struct PayloadEvent {
  PayloadEventType type;
  uint16_t conn_handle;
  uint32_t ingress_generation;
  uint16_t data_len;
  uint8_t data[K1_DECK_STATE_MAX_PACKET];
};

static QueueHandle_t gLinkQueue = nullptr;
static StaticQueue_t gLinkQueueStruct;
static uint8_t gLinkQueueStorage[kLinkQueueCapacity * sizeof(LinkEvent)];
static QueueHandle_t gPayloadQueue = nullptr;
static StaticQueue_t gPayloadQueueStruct;
static uint8_t gPayloadQueueStorage[kPayloadQueueCapacity * sizeof(PayloadEvent)];
static std::atomic<uint32_t> gIngressDrops{0};
static std::atomic<bool> gIngressLoss{false};
static std::atomic<uint16_t> gIngressHandle{BLE_HS_CONN_HANDLE_NONE};
static std::atomic<uint32_t> gIngressGeneration{0};
static uint32_t gPayloadQueueHwm = 0;
static uint32_t gConnectionGeneration = 0;
static uint32_t gDuplicateConnects = 0;
static uint32_t gStalePayloads = 0;
static constexpr uint32_t kRecoveryDisconnectDeadlineMs = 2500;
static bool gRecoveryInFlight = false;
static uint32_t gRecoveryDeadlineMs = 0;
static bool gAdvertisingPending = false;
static uint8_t gAdvertisingBackoffStep = 0;
static uint32_t gNextAdvertisingMs = 0;

static void start_advertising();
static void reset_rssi_state(uint32_t now);
static bool time_reached(uint32_t now, uint32_t deadline);

static void note_ingress_loss()
{
  gIngressDrops.fetch_add(1, std::memory_order_relaxed);
  gIngressLoss.store(true, std::memory_order_release);
}

static bool enqueue_link_event(LinkEventType type, uint16_t conn_handle)
{
  // Preserve the newest controller-side handle even if the bounded queue is
  // full, so loop-owned recovery can still terminate an otherwise orphaned
  // connection. This atomic hint is not application connection authority.
  if (type == LinkEventType::Connected) {
    const uint16_t prior =
        gIngressHandle.exchange(conn_handle, std::memory_order_acq_rel);
    if (prior != conn_handle) {
      gIngressGeneration.fetch_add(1, std::memory_order_acq_rel);
    }
  } else {
    gIngressHandle.store(BLE_HS_CONN_HANDLE_NONE, std::memory_order_release);
  }
  if (!gLinkQueue) {
    note_ingress_loss();
    return false;
  }
  LinkEvent event = {
      type, conn_handle, gIngressGeneration.load(std::memory_order_acquire)};
  if (xQueueSend(gLinkQueue, &event, 0) != pdTRUE) {
    note_ingress_loss();
    return false;
  }
  return true;
}

static bool enqueue_payload_event(PayloadEventType type,
                                  const uint8_t* data,
                                  size_t len)
{
  if (!gPayloadQueue || !data || len == 0 || len > K1_DECK_STATE_MAX_PACKET) {
    note_ingress_loss();
    return false;
  }
  PayloadEvent event = {};
  event.type = type;
  event.conn_handle = gIngressHandle.load(std::memory_order_acquire);
  event.ingress_generation =
      gIngressGeneration.load(std::memory_order_acquire);
  event.data_len = static_cast<uint16_t>(len);
  memcpy(event.data, data, len);
  if (xQueueSend(gPayloadQueue, &event, 0) != pdTRUE) {
    note_ingress_loss();
    return false;
  }
  return true;
}

static uint32_t advertising_backoff_ms()
{
  static constexpr uint16_t kBackoff[] = {250, 500, 1000, 2000, 4000};
  const uint8_t index = gAdvertisingBackoffStep < 5 ? gAdvertisingBackoffStep : 4;
  if (gAdvertisingBackoffStep < 4) ++gAdvertisingBackoffStep;
  return kBackoff[index];
}

static void schedule_advertising(uint32_t now)
{
  gAdvertisingPending = true;
  gNextAdvertisingMs = now + advertising_backoff_ms();
}

static void purge_payload_queue()
{
  if (gPayloadQueue) xQueueReset(gPayloadQueue);
}

static void apply_connected(uint16_t conn_handle, uint32_t ingress_generation)
{
  if (conn_handle == BLE_HS_CONN_HANDLE_NONE || ingress_generation == 0) return;
  if (gConnected && gConnHandle == conn_handle &&
      gConnectionGeneration == ingress_generation) {
    ++gDuplicateConnects;
    return;
  }
  if (gConnected) {
    note_ingress_loss();
    return;
  }
  gConnected = true;
  gConnHandle = conn_handle;
  gIngressHandle.store(conn_handle, std::memory_order_release);
  gConnectionGeneration = ingress_generation;
  gRecoveryInFlight = false;
  gRecoveryDeadlineMs = 0;
  gAdvertisingPending = false;
  gAdvertisingBackoffStep = 0;
  reset_rssi_state(millis());
  deck_state_rx_on_identity_hint();
  Serial.printf("[ble-midi] central connected conn=%u generation=%lu\n",
                static_cast<unsigned>(gConnHandle),
                static_cast<unsigned long>(gConnectionGeneration));
}

static void apply_disconnected(const char* reason)
{
  const uint16_t old_handle = gConnHandle;
  const bool had_link = gConnected || old_handle != BLE_HS_CONN_HANDLE_NONE;
  const bool was_recovery = gRecoveryInFlight;
  gConnected = false;
  gConnHandle = BLE_HS_CONN_HANDLE_NONE;
  gIngressHandle.store(BLE_HS_CONN_HANDLE_NONE, std::memory_order_release);
  purge_payload_queue();
  reset_rssi_state(millis());
  if (had_link || was_recovery) deck_state_rx_on_disconnect();
  gRecoveryInFlight = false;
  gRecoveryDeadlineMs = 0;
  if (!gAdvertisingPending) schedule_advertising(millis());
  if (had_link || was_recovery) {
    Serial.printf("[ble-midi] central disconnected conn=%u reason=%s\n",
                  static_cast<unsigned>(old_handle), reason ? reason : "GAP");
  }
}

static void begin_controlled_recovery(const char* reason)
{
  if (gRecoveryInFlight) return;
  gRecoveryInFlight = true;
  deck_state_rx_clear_recovery_request();
  purge_payload_queue();
  const uint16_t recovery_handle =
      gConnected ? gConnHandle
                 : gIngressHandle.load(std::memory_order_acquire);
  if (gServer && recovery_handle != BLE_HS_CONN_HANDLE_NONE) {
    const int rc = gServer->disconnect(recovery_handle);
    Serial.printf("[ble-midi] recovery disconnect reason=%s rc=%d generation=%lu\n",
                  reason ? reason : "desynchronised", rc,
                  static_cast<unsigned long>(gConnectionGeneration));
    if (rc == 0) {
      gRecoveryDeadlineMs = millis() + kRecoveryDisconnectDeadlineMs;
      return;
    }
  }
  apply_disconnected(reason);
}

static void maintain_recovery(uint32_t now)
{
  if (!gRecoveryInFlight || gRecoveryDeadlineMs == 0 ||
      !time_reached(now, gRecoveryDeadlineMs)) {
    return;
  }
  // A missing GAP callback must not wedge lifecycle ownership forever. Make one
  // final controller disconnect request, then fail closed locally and re-enter
  // the bounded advertising backoff path.
  if (gConnected && gServer && gConnHandle != BLE_HS_CONN_HANDLE_NONE) {
    (void)gServer->disconnect(gConnHandle);
  }
  apply_disconnected("RECOVERY_TIMEOUT");
}

static void drain_host_events()
{
  if (!gLinkQueue || !gPayloadQueue) return;
  LinkEvent link = {};
  while (xQueueReceive(gLinkQueue, &link, 0) == pdTRUE) {
    if (link.type == LinkEventType::Connected) {
      apply_connected(link.conn_handle, link.ingress_generation);
    } else {
      apply_disconnected("GAP");
    }
  }

  const uint32_t depth = uxQueueMessagesWaiting(gPayloadQueue);
  if (depth > gPayloadQueueHwm) gPayloadQueueHwm = depth;
  const uint32_t start_us = micros();
  PayloadEvent event = {};
  uint8_t drained = 0;
  while (drained < kPayloadDrainLimit &&
         static_cast<uint32_t>(micros() - start_us) < kPayloadDrainBudgetUs &&
         xQueueReceive(gPayloadQueue, &event, 0) == pdTRUE) {
    ++drained;
    if (!gConnected || event.ingress_generation != gConnectionGeneration ||
        event.conn_handle != gConnHandle) {
      ++gStalePayloads;
      continue;
    }
    if (event.type == PayloadEventType::State) {
      deck_state_rx_on_packet(event.data, event.data_len);
    }
#if TAB5_BLE_VERBOSE_DIAG
    else {
      Serial.printf("[ble-midi] loop-owned MIDI RX len=%u\n",
                    static_cast<unsigned>(event.data_len));
    }
#endif
  }

  if (gIngressLoss.exchange(false, std::memory_order_acq_rel)) {
    deck_state_rx_on_ingress_loss("transport_queue");
  }
  deck_state_rx_tick(millis());
  if (deck_state_rx_recovery_required()) {
    begin_controlled_recovery("state_desynchronised");
  }
}

// Arduino BLE exposes Read RSSI as a synchronous NimBLE HCI call with an
// internal two-second timeout. A single static maintenance worker contains that
// wait; loopTask never blocks on HCI and remains the sole state-machine owner.
static constexpr uint32_t kRssiIntervalMs = 2000;
static constexpr uint32_t kRssiDeadlineMs = 2200;
static constexpr UBaseType_t kRssiQueueCapacity = 1;
static constexpr uint32_t kRssiWorkerStackWords = 3072;

struct RssiRequest {
  uint16_t conn_handle;
  uint32_t generation;
  uint32_t request_id;
};

struct RssiCompletion {
  uint16_t conn_handle;
  uint32_t generation;
  uint32_t request_id;
  int rc;
  int8_t rssi;
};

static QueueHandle_t gRssiRequestQueue = nullptr;
static StaticQueue_t gRssiRequestQueueStruct;
static uint8_t gRssiRequestQueueStorage[kRssiQueueCapacity * sizeof(RssiRequest)];
static QueueHandle_t gRssiCompletionQueue = nullptr;
static StaticQueue_t gRssiCompletionQueueStruct;
static uint8_t gRssiCompletionQueueStorage[
    kRssiQueueCapacity * sizeof(RssiCompletion)];
static StaticTask_t gRssiWorkerTaskStruct;
static StackType_t gRssiWorkerStack[kRssiWorkerStackWords];
static TaskHandle_t gRssiWorkerTask = nullptr;
static std::atomic<bool> gRssiWorkerBusy{false};
static bool gRssiInFlight = false;
static bool gRssiTimedOut = false;
static bool gCachedRssiValid = false;
static int8_t gCachedRssi = 0;
static uint8_t gRssiTransientFailures = 0;
static uint32_t gRssiNextDueMs = 0;
static uint32_t gRssiDeadlineAtMs = 0;
static uint32_t gRssiRequestId = 0;
static uint32_t gRssiTimeouts = 0;
static uint32_t gRssiStaleCompletions = 0;

static bool time_reached(uint32_t now, uint32_t deadline)
{
  return static_cast<int32_t>(now - deadline) >= 0;
}

static void rssi_worker(void*)
{
  RssiRequest request = {};
  for (;;) {
    if (xQueueReceive(gRssiRequestQueue, &request, portMAX_DELAY) != pdTRUE) {
      continue;
    }
    RssiCompletion completion = {};
    completion.conn_handle = request.conn_handle;
    completion.generation = request.generation;
    completion.request_id = request.request_id;
    gRssiWorkerBusy.store(true, std::memory_order_release);
    completion.rc = ble_gap_conn_rssi(request.conn_handle, &completion.rssi);
    gRssiWorkerBusy.store(false, std::memory_order_release);
    (void)xQueueOverwrite(gRssiCompletionQueue, &completion);
  }
}

static uint32_t rssi_backoff_ms()
{
  if (gRssiTransientFailures < 5) ++gRssiTransientFailures;
  uint32_t delay_ms = 2000UL << (gRssiTransientFailures - 1);
  if (delay_ms > 30000UL) delay_ms = 30000UL;
  return delay_ms;
}

static bool rssi_is_transient(int rc)
{
#ifdef BLE_HS_ETIMEOUT
  if (rc == BLE_HS_ETIMEOUT) return true;
#endif
#ifdef BLE_HS_EBUSY
  if (rc == BLE_HS_EBUSY) return true;
#endif
#ifdef BLE_HS_ENOMEM
  if (rc == BLE_HS_ENOMEM) return true;
#endif
#ifdef BLE_HS_EAGAIN
  if (rc == BLE_HS_EAGAIN) return true;
#endif
  return false;
}

static bool rssi_is_disconnected(int rc)
{
#ifdef BLE_HS_ENOTCONN
  return rc == BLE_HS_ENOTCONN;
#else
  (void)rc;
  return false;
#endif
}

static void reset_rssi_state(uint32_t now)
{
  gRssiInFlight = false;
  gRssiTimedOut = false;
  gCachedRssiValid = false;
  gRssiTransientFailures = 0;
  gRssiNextDueMs = now + kRssiIntervalMs;
  if (gRssiRequestQueue) xQueueReset(gRssiRequestQueue);
  if (gRssiCompletionQueue) xQueueReset(gRssiCompletionQueue);
}

static void maintain_rssi(uint32_t now)
{
  RssiCompletion completion = {};
  while (gRssiCompletionQueue &&
         xQueueReceive(gRssiCompletionQueue, &completion, 0) == pdTRUE) {
    if (!gRssiInFlight || completion.request_id != gRssiRequestId ||
        completion.generation != gConnectionGeneration ||
        completion.conn_handle != gConnHandle) {
      ++gRssiStaleCompletions;
      continue;
    }
    gRssiInFlight = false;
    const bool was_timed_out = gRssiTimedOut;
    gRssiTimedOut = false;
    if (was_timed_out) {
      gRssiNextDueMs = now + rssi_backoff_ms();
      continue;
    }
    if (completion.rc == 0) {
      gCachedRssi = completion.rssi;
      gCachedRssiValid = true;
      gRssiTransientFailures = 0;
      gRssiNextDueMs = now + kRssiIntervalMs;
      continue;
    }
    gCachedRssiValid = false;
    if (completion.rc == BLE_HS_HCI_ERR(BLE_ERR_UNK_CONN_ID)) {
      deck_state_rx_on_ingress_loss("rssi_unknown_handle");
      begin_controlled_recovery("RSSI_UNKNOWN_HANDLE");
    } else if (rssi_is_disconnected(completion.rc)) {
      deck_state_rx_on_ingress_loss("rssi_disconnected");
      begin_controlled_recovery("RSSI_DISCONNECTED");
    } else if (rssi_is_transient(completion.rc)) {
      gRssiNextDueMs = now + rssi_backoff_ms();
    } else {
      deck_state_rx_on_ingress_loss("rssi_fatal");
      begin_controlled_recovery("RSSI_FATAL");
    }
  }

  if (gRssiInFlight && !gRssiTimedOut && time_reached(now, gRssiDeadlineAtMs)) {
    // The worker remains the one operation in flight. No replacement request is
    // issued until its late completion arrives, so a wedged controller cannot
    // create a task, queue or HCI storm.
    gRssiTimedOut = true;
    gCachedRssiValid = false;
    ++gRssiTimeouts;
  }
  if (!gConnected || gRecoveryInFlight || gRssiInFlight ||
      gRssiWorkerBusy.load(std::memory_order_acquire) ||
      !time_reached(now, gRssiNextDueMs) || !gRssiRequestQueue) {
    return;
  }
  RssiRequest request = {};
  request.conn_handle = gConnHandle;
  request.generation = gConnectionGeneration;
  request.request_id = ++gRssiRequestId;
  if (xQueueSend(gRssiRequestQueue, &request, 0) == pdTRUE) {
    gRssiInFlight = true;
    gRssiTimedOut = false;
    gRssiDeadlineAtMs = now + kRssiDeadlineMs;
  } else {
    gRssiNextDueMs = now + rssi_backoff_ms();
  }
}

static void refresh_identity_wire()
{
  K1DeckIdentityV1 id = {};
  k1_deck_identity_build_bench(&id);
  (void)k1_deck_identity_encode(&id, gIdentityWire, sizeof(gIdentityWire));
  if (gIdentityCharacteristic) {
    gIdentityCharacteristic->setValue(gIdentityWire, sizeof(gIdentityWire));
  }
}

static void start_advertising()
{
  BLEAdvertising* advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(BleMidiTransport::kServiceUuid);
  advertising->addServiceUUID(K1_DECK_IDENTITY_SERVICE_UUID);
  advertising->addServiceUUID(K1_DECK_STATE_SERVICE_UUID);
  // Scan response carries the complete local name "K1 Tab5" so K1 can match
  // by name if the 128-bit MIDI UUID does not fit in the primary ADV PDU.
  advertising->setScanResponse(true);
  advertising->setName("K1 Tab5");
  // Prefer 15–30 ms connection interval (12–24 × 1.25 ms) for Deck16 latency.
  // Prior silicon negotiated ~50 ms (40 units); PPCP was unset (0x00).
  advertising->setMinPreferred(0x0C);
  advertising->setMaxPreferred(0x18);
  BLEDevice::startAdvertising();
}

class MidiServerCallbacks final : public BLEServerCallbacks {
public:
  void onConnect(BLEServer* server) override
  {
    /* The pinned Arduino 3.3.1 wrapper invokes this immediately before the
     * descriptor overload. Enqueue only from the overload that carries the
     * controller-authoritative handle so one link consumes one queue slot. */
    (void)server;
  }

  void onConnect(BLEServer* server, ble_gap_conn_desc* desc) override
  {
    const uint16_t handle = desc ? desc->conn_handle
                                 : (server ? server->getConnId()
                                           : BLE_HS_CONN_HANDLE_NONE);
    (void)enqueue_link_event(LinkEventType::Connected, handle);
  }

  void onDisconnect(BLEServer* server) override
  {
    (void)server;
    (void)enqueue_link_event(LinkEventType::Disconnected,
                             BLE_HS_CONN_HANDLE_NONE);
  }
};

class MidiCharacteristicCallbacks final : public BLECharacteristicCallbacks {
public:
  void onWrite(BLECharacteristic* characteristic) override
  {
    if (!characteristic) return;
    if (characteristic->getLength() == 0) return;
    (void)enqueue_payload_event(PayloadEventType::Midi,
                                characteristic->getData(),
                                characteristic->getLength());
  }
};

class StateCharacteristicCallbacks final : public BLECharacteristicCallbacks {
public:
  void onWrite(BLECharacteristic* characteristic) override
  {
    if (!characteristic) return;
    (void)enqueue_payload_event(PayloadEventType::State,
                                characteristic->getData(),
                                characteristic->getLength());
  }
};

static void wrap_ble_midi_packet(const uint8_t* midi, size_t len, uint8_t* out, size_t* outLen)
{
  const uint16_t timestamp = static_cast<uint16_t>(millis() & 0x1FFF);
  out[0] = static_cast<uint8_t>(0x80 | ((timestamp >> 7) & 0x3F));
  out[1] = static_cast<uint8_t>(0x80 | (timestamp & 0x7F));
  memcpy(out + 2, midi, len);
  *outLen = len + 2;
}
#endif

static void log_packet(const char* label, const uint8_t* data, size_t len)
{
#if TAB5_BLE_VERBOSE_DIAG
  Serial.printf("[ble-midi] %s", label);
  for (size_t i = 0; i < len; ++i) {
    Serial.printf(" %02X", data[i]);
  }
  Serial.println();
#else
  (void)label;
  (void)data;
  (void)len;
#endif
}

// BLE-MIDI header (2) + up to 4 tightly packed CC messages (12) = 14.
// K1 decoder walks status+data without inter-message timestamps, so pack
// consecutive MIDI status messages only (no 0x80 ts bytes between them).
static constexpr size_t kBleMidiMaxMidiBytes = 12;
static constexpr size_t kBleMidiMaxPacket = 2 + kBleMidiMaxMidiBytes;

static void send_midi_message(const char* label, const uint8_t* midi, size_t len)
{
  if (!gInitialised || !midi || len == 0) return;

#if TAB5_BLE_GATT_AVAILABLE
  if (gMidiCharacteristic && gConnected && len <= kBleMidiMaxMidiBytes) {
    uint8_t packet[kBleMidiMaxPacket] = {};
    size_t packetLen = 0;
    wrap_ble_midi_packet(midi, len, packet, &packetLen);
    gMidiCharacteristic->setValue(packet, packetLen);
    gMidiCharacteristic->notify();
    log_packet(label, packet, packetLen);
    return;
  }
#endif

  log_packet(label, midi, len);
}

static const K1BleMidiEntry* find_entry(const char* path)
{
  if (!path) return nullptr;
  for (size_t i = 0; i < K1_BLE_MIDI_CONTROL_COUNT; ++i) {
    if (strcmp(kK1BleMidiMap[i].path, path) == 0) {
      return &kK1BleMidiMap[i];
    }
  }
  return nullptr;
}

static float clampf(float v, float lo, float hi)
{
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

static uint16_t encode_cc14(const K1BleMidiEntry& entry, float value)
{
  const float lo = entry.vmin;
  const float hi = (entry.vmax > entry.vmin) ? entry.vmax : (entry.vmin + 1.0f);
  const float clamped = clampf(value, lo, hi);
  const float norm = (clamped - lo) / (hi - lo);
  const long n = lroundf(norm * 16383.0f);
  if (n < 0) return 0;
  if (n > 16383) return 16383;
  return static_cast<uint16_t>(n);
}

} // namespace

namespace BleMidiTransport {

void init()
{
  gInitialised = true;
  gLastStatusLogMs = millis();
#if TAB5_BLE_GATT_AVAILABLE
  // Gate NimBLE behind SDIO readiness. SoftAP/STA stay off — only the radio pipe.
  if (!wait_hosted_sdio_ready(8000U)) {
    Serial.println("[ble-midi] bearer=pending (SDIO not up); skipping BLEDevice::init");
    return;
  }

  gLinkQueue = xQueueCreateStatic(kLinkQueueCapacity, sizeof(LinkEvent),
                                  gLinkQueueStorage, &gLinkQueueStruct);
  gPayloadQueue = xQueueCreateStatic(kPayloadQueueCapacity, sizeof(PayloadEvent),
                                     gPayloadQueueStorage, &gPayloadQueueStruct);
  gRssiRequestQueue = xQueueCreateStatic(
      kRssiQueueCapacity, sizeof(RssiRequest), gRssiRequestQueueStorage,
      &gRssiRequestQueueStruct);
  gRssiCompletionQueue = xQueueCreateStatic(
      kRssiQueueCapacity, sizeof(RssiCompletion), gRssiCompletionQueueStorage,
      &gRssiCompletionQueueStruct);
  if (!gLinkQueue || !gPayloadQueue || !gRssiRequestQueue ||
      !gRssiCompletionQueue) {
    Serial.println("[ble-midi] static transport queue creation FAILED");
    return;
  }
  gRssiWorkerTask = xTaskCreateStaticPinnedToCore(
      rssi_worker, "tab5_rssi", kRssiWorkerStackWords, nullptr, 1,
      gRssiWorkerStack, &gRssiWorkerTaskStruct, tskNO_AFFINITY);
  if (!gRssiWorkerTask) {
    Serial.println("[ble-midi] static RSSI worker creation FAILED");
    return;
  }

  BLEDevice::init("K1 Tab5");
  gServer = BLEDevice::createServer();
  gServer->setCallbacks(new MidiServerCallbacks());

  BLEService* service = gServer->createService(kServiceUuid);
  gMidiCharacteristic = service->createCharacteristic(
    kCharacteristicUuid,
    BLECharacteristic::PROPERTY_READ |
      BLECharacteristic::PROPERTY_WRITE |
      BLECharacteristic::PROPERTY_WRITE_NR |
      BLECharacteristic::PROPERTY_NOTIFY
  );
  gMidiCharacteristic->setCallbacks(new MidiCharacteristicCallbacks());
  service->start();

  // Deck16 identity_v1 (read-only). K1 must admit this peer before MIDI subscribe.
  BLEService* identityService = gServer->createService(K1_DECK_IDENTITY_SERVICE_UUID);
  gIdentityCharacteristic = identityService->createCharacteristic(
    K1_DECK_IDENTITY_V1_UUID,
    BLECharacteristic::PROPERTY_READ
  );
  refresh_identity_wire();
  identityService->start();

  BLEService* stateService = gServer->createService(K1_DECK_STATE_SERVICE_UUID);
  gStateCharacteristic = stateService->createCharacteristic(
    K1_STATE_V1_RX_UUID,
    BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR
  );
  gStateCharacteristic->setCallbacks(new StateCharacteristicCallbacks());
  stateService->start();

  start_advertising();

  Serial.printf(
      "[ble-midi] GATT advertising service=%s characteristic=%s map_md5=%s "
      "identity=%s state=%s deck_id=DECK16-BENCH-01\n",
      kServiceUuid,
      kCharacteristicUuid,
      K1_BLE_MIDI_REGISTRY_MD5,
      K1_DECK_IDENTITY_SERVICE_UUID,
      K1_DECK_STATE_SERVICE_UUID);
#if TAB5_HCI_PATH_DIAG
  h0_wire_log_counters("post_advertising_start");
#endif
#else
  Serial.printf("[ble-midi] protocol ready service=%s characteristic=%s map_md5=%s\n",
                kServiceUuid,
                kCharacteristicUuid,
                K1_BLE_MIDI_REGISTRY_MD5);
  Serial.println("[ble-midi] bearer=pending-p4-c6-ble-host; Wi-Fi SoftAP disabled");
#if !defined(CONFIG_ESP_HOSTED_ENABLE_BT_NIMBLE)
  Serial.println("[ble-midi] gate=missing CONFIG_ESP_HOSTED_ENABLE_BT_NIMBLE");
#endif
#if !defined(CONFIG_NIMBLE_ENABLED)
  Serial.println("[ble-midi] gate=missing CONFIG_NIMBLE_ENABLED");
#endif
#if !__has_include(<host/ble_gap.h>)
  Serial.println("[ble-midi] gate=missing host/ble_gap.h");
#endif
#endif
}

void tick()
{
#if TAB5_BLE_GATT_AVAILABLE
  drain_host_events();
#endif
  const uint32_t now = millis();
#if TAB5_BLE_GATT_AVAILABLE
  maintain_recovery(now);
  if (gAdvertisingPending && time_reached(now, gNextAdvertisingMs)) {
    gAdvertisingPending = false;
    BLEDevice::startAdvertising();
  }
  maintain_rssi(now);
#endif
  if (now - gLastStatusLogMs >= 30000UL) {
    gLastStatusLogMs = now;
#if TAB5_BLE_GATT_AVAILABLE
    Serial.printf(
        "[ble-midi] status connected=%s generation=%lu drops=%lu hwm=%lu "
        "stale_payloads=%lu duplicate_connects=%lu rssi_timeouts=%lu "
        "rssi_stale=%lu\n",
        gConnected ? "yes" : "no",
        static_cast<unsigned long>(gConnectionGeneration),
        static_cast<unsigned long>(gIngressDrops.load(std::memory_order_relaxed)),
        static_cast<unsigned long>(gPayloadQueueHwm),
        static_cast<unsigned long>(gStalePayloads),
        static_cast<unsigned long>(gDuplicateConnects),
        static_cast<unsigned long>(gRssiTimeouts),
        static_cast<unsigned long>(gRssiStaleCompletions));
#else
    Serial.println("[ble-midi] status=protocol-ready bearer=pending");
#endif
  }
}

bool ready()
{
#if TAB5_BLE_GATT_AVAILABLE
  return gInitialised && gMidiCharacteristic != nullptr;
#else
  return gInitialised;
#endif
}

bool connected()
{
#if TAB5_BLE_GATT_AVAILABLE
  return gConnected;
#else
  return false;
#endif
}

bool gattAvailable()
{
  return TAB5_BLE_GATT_AVAILABLE != 0;
}

bool connectionRssi(int8_t* out_dbm)
{
  if (!out_dbm) return false;
  *out_dbm = 0;
#if TAB5_BLE_GATT_AVAILABLE
  // UI reads the loop-owned cache only. HCI acquisition happens at most once
  // every two seconds in the bounded maintenance state machine.
  if (!gConnected || !gCachedRssiValid) return false;
  *out_dbm = gCachedRssi;
  return true;
#else
  return false;
#endif
}

uint8_t unitToMidi7(float value)
{
  value = clampf(value, 0.0f, 1.0f);
  return static_cast<uint8_t>(lroundf(value * 127.0f));
}

uint16_t unitToMidi14(float value)
{
  value = clampf(value, 0.0f, 1.0f);
  return static_cast<uint16_t>(lroundf(value * 16383.0f));
}

void sendProgramChange(uint8_t channel, uint8_t program)
{
  channel &= 0x0F;
  if (program > 127) program = 127;
  const uint8_t midi[] = { static_cast<uint8_t>(0xC0 | channel), program };
  char label[48];
  snprintf(label, sizeof(label), "tx PC ch=%u", static_cast<unsigned>(channel + 1));
  send_midi_message(label, midi, sizeof(midi));
}

void sendControlChange(uint8_t channel, uint8_t controller, uint8_t value)
{
  channel &= 0x0F;
  if (controller > 127) controller = 127;
  if (value > 127) value = 127;
  const uint8_t midi[] = {
    static_cast<uint8_t>(0xB0 | channel),
    controller,
    value,
  };
  char label[56];
  snprintf(label, sizeof(label), "tx CC ch=%u cc=%u",
           static_cast<unsigned>(channel + 1),
           static_cast<unsigned>(controller));
  send_midi_message(label, midi, sizeof(midi));
}

void sendControlChange14(uint8_t channel, uint8_t cc_msb, uint8_t cc_lsb, uint16_t value14)
{
  // Single notify: MSB+LSB must share one BLE-MIDI packet so K1's 50 ms
  // CC14 pair window cannot expire between halves under connection-interval jitter.
  channel &= 0x0F;
  if (cc_msb > 127) cc_msb = 127;
  if (cc_lsb > 127) cc_lsb = 127;
  if (value14 > 0x3FFF) value14 = 0x3FFF;
  const uint8_t midi[] = {
    static_cast<uint8_t>(0xB0 | channel),
    cc_msb,
    static_cast<uint8_t>((value14 >> 7) & 0x7F),
    static_cast<uint8_t>(0xB0 | channel),
    cc_lsb,
    static_cast<uint8_t>(value14 & 0x7F),
  };
  char label[64];
  snprintf(label, sizeof(label), "tx CC14 ch=%u msb=%u lsb=%u",
           static_cast<unsigned>(channel + 1),
           static_cast<unsigned>(cc_msb),
           static_cast<unsigned>(cc_lsb));
  send_midi_message(label, midi, sizeof(midi));
}

void sendNrpn(uint8_t channel, uint16_t param, uint16_t data14)
{
  // Single notify: full NRPN select+data in one packet (avoids partial NRPN state).
  channel &= 0x0F;
  if (param > 0x3FFF) param = 0x3FFF;
  if (data14 > 0x3FFF) data14 = 0x3FFF;
  const uint8_t midi[] = {
    static_cast<uint8_t>(0xB0 | channel), kNrpnParamMsb,
    static_cast<uint8_t>((param >> 7) & 0x7F),
    static_cast<uint8_t>(0xB0 | channel), kNrpnParamLsb,
    static_cast<uint8_t>(param & 0x7F),
    static_cast<uint8_t>(0xB0 | channel), kNrpnDataMsb,
    static_cast<uint8_t>((data14 >> 7) & 0x7F),
    static_cast<uint8_t>(0xB0 | channel), kNrpnDataLsb,
    static_cast<uint8_t>(data14 & 0x7F),
  };
  char label[56];
  snprintf(label, sizeof(label), "tx NRPN ch=%u param=%u",
           static_cast<unsigned>(channel + 1),
           static_cast<unsigned>(param));
  send_midi_message(label, midi, sizeof(midi));
}

void sendPitchBend(uint8_t channel, uint16_t value14)
{
  channel &= 0x0F;
  if (value14 > 0x3FFF) value14 = 0x3FFF;
  const uint8_t midi[] = {
    static_cast<uint8_t>(0xE0 | channel),
    static_cast<uint8_t>(value14 & 0x7F),
    static_cast<uint8_t>((value14 >> 7) & 0x7F),
  };
  char label[48];
  snprintf(label, sizeof(label), "tx PB ch=%u", static_cast<unsigned>(channel + 1));
  send_midi_message(label, midi, sizeof(midi));
}

bool sendMappedNumber(const char* path, float value)
{
  const K1BleMidiEntry* entry = find_entry(path);
  if (!entry) {
    Serial.printf("[ble-midi] unknown map path=%s\n", path ? path : "(null)");
    return false;
  }

  switch (entry->type) {
    case K1MIDI_CC14:
      sendControlChange14(entry->channel, entry->cc_msb, entry->cc_lsb, encode_cc14(*entry, value));
      return true;
    case K1MIDI_CC7_BOOL:
      sendControlChange(entry->channel, entry->cc_msb, value >= 0.5f ? 127 : 0);
      return true;
    case K1MIDI_CC7_ENUM:
      sendControlChange(entry->channel, entry->cc_msb, unitToMidi7(clampf(value, 0.0f, 1.0f)));
      return true;
    case K1MIDI_NRPN:
      sendNrpn(entry->channel, entry->nrpn_param, unitToMidi14(clampf(value, 0.0f, 1.0f)));
      return true;
    case K1MIDI_PC:
      sendProgramChange(entry->channel, unitToMidi7(clampf(value, 0.0f, 1.0f)));
      return true;
    default:
      return false;
  }
}

bool sendMappedBool(const char* path, bool value)
{
  const K1BleMidiEntry* entry = find_entry(path);
  if (!entry || entry->type != K1MIDI_CC7_BOOL) {
    Serial.printf("[ble-midi] bool map miss path=%s\n", path ? path : "(null)");
    return false;
  }
  sendControlChange(entry->channel, entry->cc_msb, value ? 127 : 0);
  return true;
}

bool sendMappedEnum(const char* path, uint8_t index)
{
  const K1BleMidiEntry* entry = find_entry(path);
  if (!entry || entry->type != K1MIDI_CC7_ENUM) {
    Serial.printf("[ble-midi] enum map miss path=%s\n", path ? path : "(null)");
    return false;
  }
  if (index > 127) index = 127;
  sendControlChange(entry->channel, entry->cc_msb, index);
  return true;
}

bool sendMappedProgram(const char* path, uint8_t program)
{
  const K1BleMidiEntry* entry = find_entry(path);
  if (!entry || entry->type != K1MIDI_PC) {
    Serial.printf("[ble-midi] pc map miss path=%s\n", path ? path : "(null)");
    return false;
  }
  sendProgramChange(entry->channel, program);
  return true;
}

bool sendMappedText(const char* path, uint8_t local_index)
{
  const K1BleMidiEntry* entry = find_entry(path);
  if (!entry || entry->type != K1MIDI_NRPN) {
    Serial.printf("[ble-midi] text map miss path=%s\n", path ? path : "(null)");
    return false;
  }
  if (entry->text_count == 0) {
    /* Command pulse — data14 unused / zero. */
    sendNrpn(entry->channel, entry->nrpn_param, 0);
    return true;
  }
  if (local_index >= entry->text_count) local_index = static_cast<uint8_t>(entry->text_count - 1);
  sendNrpn(entry->channel, entry->nrpn_param, local_index);
  return true;
}

void sendPrimaryMode(uint8_t program)
{
  sendMappedProgram("primary.mode", program);
}

void sendPrimaryPhotons(float unit01)
{
  sendMappedNumber("primary.photons", unit01);
}

void sendPrimaryMood(float unit01)
{
  sendMappedNumber("primary.mood", unit01);
}

void sendPrimaryPalette(uint8_t paletteIndex)
{
  sendMappedEnum("primary.palette", paletteIndex);
}

void sendSecondaryMode(uint8_t program)
{
  sendMappedProgram("secondary.mode", program);
}

void sendSecondaryPhotons(float unit01)
{
  sendMappedNumber("secondary.photons", unit01);
}

void sendSecondaryMood(float unit01)
{
  sendMappedNumber("secondary.mood", unit01);
}

void sendSecondaryPalette(uint8_t paletteIndex)
{
  sendMappedEnum("secondary.palette", paletteIndex);
}

bool sendCalArm()
{
  return sendMappedNumber("calibration.noise.arm", 1.0f);
}

bool sendCalConfirm()
{
  return sendMappedNumber("calibration.noise.confirm", 1.0f);
}

bool sendCalClear()
{
  // data14=0 → text "CONFIRM" (K1 facade requires it for clear).
  return sendMappedNumber("calibration.noise.clear", 0.0f);
}

bool disconnectCentral()
{
#if TAB5_BLE_GATT_AVAILABLE
  if (!gServer || gConnHandle == BLE_HS_CONN_HANDLE_NONE) {
    Serial.println("[ble-midi] disconnect: no central");
    return false;
  }
  const int rc = gServer->disconnect(gConnHandle);
  Serial.printf("[ble-midi] disconnect rc=%d conn=%u\n", rc,
                static_cast<unsigned>(gConnHandle));
  return rc == 0;
#else
  return false;
#endif
}

bool setIdentityFault(const char* mode)
{
#if TAB5_BLE_GATT_AVAILABLE
  if (!mode) mode = "ok";
  K1DeckIdentityV1 id = {};
  k1_deck_identity_build_bench(&id);
  if (strcmp(mode, "md5") == 0) {
    id.ble_midi_registry_md5[0] ^= 0xA5;
  } else if (strcmp(mode, "product") == 0) {
    id.product_id = 0xDEAD;
  } else if (strcmp(mode, "short") == 0) {
    // Encode then truncate characteristic value to force length reject.
    (void)k1_deck_identity_encode(&id, gIdentityWire, sizeof(gIdentityWire));
    if (gIdentityCharacteristic) {
      gIdentityCharacteristic->setValue(gIdentityWire, 8);
    }
    Serial.println("[ble-midi] identity_fault=short (8-byte)");
    (void)disconnectCentral();
    return true;
  } else if (strcmp(mode, "ok") != 0) {
    Serial.printf("[ble-midi] identity_fault unknown mode=%s\n", mode);
    return false;
  }
  (void)k1_deck_identity_encode(&id, gIdentityWire, sizeof(gIdentityWire));
  if (gIdentityCharacteristic) {
    gIdentityCharacteristic->setValue(gIdentityWire, sizeof(gIdentityWire));
  }
  Serial.printf("[ble-midi] identity_fault=%s applied\n", mode);
  (void)disconnectCentral();
  return true;
#else
  (void)mode;
  return false;
#endif
}

void dumpConnPerf()
{
#if TAB5_BLE_GATT_AVAILABLE
  if (!gConnected || gConnHandle == BLE_HS_CONN_HANDLE_NONE) {
    Serial.println("TAB5_PERF: connected=0");
    return;
  }
  struct ble_gap_conn_desc desc = {};
  const int rc = ble_gap_conn_find(gConnHandle, &desc);
  if (rc != 0) {
    Serial.printf("TAB5_PERF: connected=1 conn_find_rc=%d\n", rc);
    return;
  }
  const uint16_t mtu = ble_att_mtu(gConnHandle);
  Serial.printf(
      "TAB5_PERF: connected=1 mtu=%u interval_units=%u latency=%u "
      "timeout_units=%u\n",
      static_cast<unsigned>(mtu),
      static_cast<unsigned>(desc.conn_itvl),
      static_cast<unsigned>(desc.conn_latency),
      static_cast<unsigned>(desc.supervision_timeout));
#else
  Serial.println("TAB5_PERF: gatt_unavailable");
#endif
}

} // namespace BleMidiTransport
