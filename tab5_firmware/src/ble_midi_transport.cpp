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

#if TAB5_BLE_GATT_AVAILABLE
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <host/ble_gap.h>
#include <host/ble_att.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
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

// NimBLE callbacks run on Core 0. Deck state and every LVGL mutation are owned
// by loopTask on Core 1, so callbacks may only enqueue compact transport events.
// Reserve two slots for link transitions so a snapshot burst cannot hide a
// disconnect behind state chunks.
static constexpr UBaseType_t kHostEventQueueCapacity = 12;
static constexpr UBaseType_t kHostEventReservedLinkSlots = 2;

enum class HostEventType : uint8_t {
  Connected = 0,
  Disconnected,
  StateChunk,
};

struct HostEvent {
  HostEventType type;
  uint16_t conn_handle;
  uint16_t data_len;
  uint8_t data[K1_DECK_STATE_MAX_PACKET];
};

static QueueHandle_t gHostEventQueue = nullptr;
static StaticQueue_t gHostEventQueueStruct;
static uint8_t gHostEventQueueStorage[
    kHostEventQueueCapacity * sizeof(HostEvent)];
static std::atomic<uint32_t> gHostEventDrops{0};

static bool enqueue_host_event(HostEventType type,
                               uint16_t conn_handle,
                               const uint8_t* data = nullptr,
                               size_t len = 0)
{
  if (!gHostEventQueue || len > K1_DECK_STATE_MAX_PACKET ||
      (len > 0 && data == nullptr)) {
    gHostEventDrops.fetch_add(1, std::memory_order_relaxed);
    return false;
  }
  if (type == HostEventType::StateChunk &&
      uxQueueSpacesAvailable(gHostEventQueue) <= kHostEventReservedLinkSlots) {
    gHostEventDrops.fetch_add(1, std::memory_order_relaxed);
    return false;
  }

  HostEvent event = {};
  event.type = type;
  event.conn_handle = conn_handle;
  event.data_len = static_cast<uint16_t>(len);
  if (len > 0) memcpy(event.data, data, len);
  if (xQueueSend(gHostEventQueue, &event, 0) != pdTRUE) {
    gHostEventDrops.fetch_add(1, std::memory_order_relaxed);
    return false;
  }
  return true;
}

static void apply_connected(uint16_t conn_handle)
{
  if (conn_handle == BLE_HS_CONN_HANDLE_NONE) return;
  if (gConnected && gConnHandle == conn_handle) return;
  gConnected = true;
  gConnHandle = conn_handle;
  deck_state_rx_on_identity_hint();
  Serial.printf("[ble-midi] central connected conn=%u\n",
                static_cast<unsigned>(gConnHandle));
}

static void apply_disconnected(const char* reason)
{
  if (!gConnected && gConnHandle == BLE_HS_CONN_HANDLE_NONE) return;
  const uint16_t old_handle = gConnHandle;
  gConnected = false;
  gConnHandle = BLE_HS_CONN_HANDLE_NONE;
  deck_state_rx_on_disconnect();
  Serial.printf("[ble-midi] central disconnected conn=%u reason=%s\n",
                static_cast<unsigned>(old_handle), reason ? reason : "GAP");
}

static void drain_host_events()
{
  if (!gHostEventQueue) return;
  HostEvent event = {};
  while (xQueueReceive(gHostEventQueue, &event, 0) == pdTRUE) {
    switch (event.type) {
      case HostEventType::Connected:
        apply_connected(event.conn_handle);
        break;
      case HostEventType::Disconnected:
        apply_disconnected("GAP");
        break;
      case HostEventType::StateChunk:
        deck_state_rx_on_packet(event.data, event.data_len);
        break;
    }
  }

  const uint32_t drops = gHostEventDrops.exchange(0, std::memory_order_relaxed);
  if (drops > 0) {
    Serial.printf("[ble-midi] host event queue drops=%lu\n",
                  static_cast<unsigned long>(drops));
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
    const uint16_t handle = server ? server->getConnId() : BLE_HS_CONN_HANDLE_NONE;
    (void)enqueue_host_event(HostEventType::Connected, handle);
  }

  void onConnect(BLEServer* server, ble_gap_conn_desc* desc) override
  {
    const uint16_t handle = desc ? desc->conn_handle
                                 : (server ? server->getConnId()
                                           : BLE_HS_CONN_HANDLE_NONE);
    (void)enqueue_host_event(HostEventType::Connected, handle);
  }

  void onDisconnect(BLEServer* server) override
  {
    (void)enqueue_host_event(HostEventType::Disconnected,
                             BLE_HS_CONN_HANDLE_NONE);
    if (server) server->startAdvertising();
  }
};

class MidiCharacteristicCallbacks final : public BLECharacteristicCallbacks {
public:
  void onWrite(BLECharacteristic* characteristic) override
  {
    if (!characteristic) return;
    const String value = characteristic->getValue();
    Serial.printf("[ble-midi] rx %u bytes", static_cast<unsigned>(value.length()));
    for (size_t i = 0; i < value.length(); ++i) {
      Serial.printf(" %02X", static_cast<uint8_t>(value[i]));
    }
    Serial.println();
  }
};

class StateCharacteristicCallbacks final : public BLECharacteristicCallbacks {
public:
  void onWrite(BLECharacteristic* characteristic) override
  {
    if (!characteristic) return;
    const String value = characteristic->getValue();
    (void)enqueue_host_event(
        HostEventType::StateChunk,
        BLE_HS_CONN_HANDLE_NONE,
        reinterpret_cast<const uint8_t*>(value.c_str()),
        static_cast<size_t>(value.length()));
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
  Serial.printf("[ble-midi] %s", label);
  for (size_t i = 0; i < len; ++i) {
    Serial.printf(" %02X", data[i]);
  }
  Serial.println();
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

  gHostEventQueue = xQueueCreateStatic(kHostEventQueueCapacity,
                                       sizeof(HostEvent),
                                       gHostEventQueueStorage,
                                       &gHostEventQueueStruct);
  if (!gHostEventQueue) {
    Serial.println("[ble-midi] host event queue creation FAILED");
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
  if (now - gLastStatusLogMs >= 30000UL) {
    gLastStatusLogMs = now;
#if TAB5_BLE_GATT_AVAILABLE
    Serial.printf("[ble-midi] status=advertising connected=%s\n", gConnected ? "yes" : "no");
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
  if (!gConnected || gConnHandle == BLE_HS_CONN_HANDLE_NONE) return false;
  int8_t rssi = 0;
  const int rc = ble_gap_conn_rssi(gConnHandle, &rssi);
  if (rc != 0) {
    if (rc == BLE_HS_HCI_ERR(BLE_ERR_UNK_CONN_ID)) {
      apply_disconnected("RSSI_UNKNOWN_HANDLE");
      if (gServer) gServer->startAdvertising();
    }
    return false;
  }
  *out_dbm = rssi;
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
