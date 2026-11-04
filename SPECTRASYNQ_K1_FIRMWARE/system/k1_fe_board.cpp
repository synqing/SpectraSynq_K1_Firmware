#include "k1_fe_board.h"

#ifdef K1_FE_BOARD_V1

#include <Arduino.h>
#include <Wire.h>
#include <driver/gpio.h>
#include <string.h>

#include "k1_pcm1808_input.h"

#ifndef USBSerial
#define USBSerial Serial
#endif

#if !K1_PCM1808_LINE_SWITCH
#error "K1_FE_BOARD_V1 needs K1_PCM1808_LINE_SWITCH=1 (jack-selected PCM1808 line-in)"
#endif

// ── Policy timings ──────────────────────────────────────────────────────────
static const uint32_t K1_FE_PG_RISE_STABLE_MS = 250;  // INPUT_20V_PG high this long before POWER_PERMIT
static const uint32_t K1_FE_PERMIT_TO_LED_MS = 20;    // POWER_PERMIT settles before LED_ENABLE
static const uint32_t K1_FE_LED_PG_READ_MS = 150;     // eFuse + buck soft-start before LED_PG readback
static const uint32_t K1_FE_JACK_STABLE_MS = 100;     // jack contact debounce
static const uint32_t K1_FE_DARK_REMINDER_MS = 60000; // repeat the "why dark" line while 5 V-only
static const int64_t K1_FE_HEARTBEAT_HALF_US = 500000; // 1 Hz blink
static const int K1_FE_PG_DROP_LATCH_COUNT = 3;        // this many 20 V drops while lit ...
static const uint32_t K1_FE_PG_DROP_LATCH_WINDOW_MS = 10000; // ... inside this window latch the LEDs off

// ── STUSB4500 registers (ST usb-c/STUSB4500 USB_PD_defines_STUSB-GEN1S.h;
//    NVM sequence follows ST NVM_Flasher as ported by SparkFun_STUSB4500) ────
static const uint8_t STUSB_DEVICE_ID = 0x2F;
static const uint8_t STUSB_DPM_PDO_NUMB = 0x70;
static const uint8_t STUSB_DPM_SNK_PDO1 = 0x85;   // 3 x 32-bit, little-endian
static const uint8_t STUSB_RDO_STATUS = 0x91;     // 32-bit
static const uint8_t STUSB_RW_BUFFER = 0x53;
static const uint8_t STUSB_FTP_PASSWORD_REG = 0x95;
static const uint8_t STUSB_FTP_PASSWORD = 0x47;
static const uint8_t STUSB_FTP_CTRL_0 = 0x96;
static const uint8_t STUSB_FTP_CTRL_1 = 0x97;
static const uint8_t FTP_CUST_PWR = 0x80;
static const uint8_t FTP_CUST_RST_N = 0x40;
static const uint8_t FTP_CUST_REQ = 0x10;
static const uint8_t FTP_CUST_SECT = 0x07;
static const uint8_t FTP_CUST_SER = 0xF8;
static const uint8_t FTP_CUST_OPCODE = 0x07;
static const uint8_t FTP_OP_READ = 0x00;
static const uint8_t FTP_OP_WRITE_PL = 0x01;
static const uint8_t FTP_OP_WRITE_SER = 0x02;
static const uint8_t FTP_OP_ERASE_SECTOR = 0x05;
static const uint8_t FTP_OP_PROG_SECTOR = 0x06;
static const uint8_t FTP_OP_SOFT_PROG_SECTOR = 0x07;
static const uint8_t FTP_ALL_SECTORS = 0x1F;
static const int K1_FE_NVM_SECTORS = 5;
static const int K1_FE_NVM_SECTOR_BYTES = 8;
// ST factory NVM image (SparkFun_STUSB4500 write(defaultVals), decodes to
// 5 V 1.5 A / 15 V 1.5 A / 20 V 1.0 A, GPIO_CFG = error recovery). The FE image
// is this plus the PDO fields, so a write never carries forward unknown bytes.
static const uint8_t K1_FE_ST_FACTORY_NVM[5][8] = {
    {0x00, 0x00, 0xB0, 0xAA, 0x00, 0x45, 0x00, 0x00},
    {0x10, 0x40, 0x9C, 0x1C, 0xFF, 0x01, 0x3C, 0xDF},
    {0x02, 0x40, 0x0F, 0x00, 0x32, 0x00, 0xFC, 0xF1},
    {0x00, 0x19, 0x56, 0xAF, 0xF5, 0x35, 0x5F, 0x00},
    {0x00, 0x4B, 0x90, 0x21, 0x43, 0x00, 0x40, 0xFB},
};

// ── FE sink profile (OI-11; R3 power-connections.json "NVM5V0.5A /20V3A /20V5A") ─
static const uint32_t K1_FE_PD_PDO1_MA = 500;
static const uint32_t K1_FE_PD_PDO2_MA = 3000;
static const uint32_t K1_FE_PD_PDO3_MA = 5000;
static const uint32_t K1_FE_PD_PDO23_MV = 20000;
static const uint8_t K1_FE_PD_PDO_COUNT = 3;

// NVM current code: 0 = flex, 0.5-3.0 A in 0.25 A steps (code 1-11),
// 3.0-5.0 A in 0.5 A steps (code 11-15).
static constexpr uint8_t k1_fe_nvm_current_code(uint32_t ma) {
  return (ma < 500u) ? 0u : (ma <= 3000u) ? (uint8_t)((4u * ma) / 1000u - 1u)
                                         : (uint8_t)((2u * ma) / 1000u + 5u);
}
static constexpr uint32_t k1_fe_nvm_current_ma(uint8_t code) {
  return (code == 0u) ? 0u : (code < 11u) ? (uint32_t)code * 250u + 250u
                                         : (uint32_t)code * 500u - 2500u;
}
static_assert(k1_fe_nvm_current_code(K1_FE_PD_PDO1_MA) == 1, "0.5 A must be NVM code 1");
static_assert(k1_fe_nvm_current_code(K1_FE_PD_PDO2_MA) == 11, "3.0 A must be NVM code 11");
static_assert(k1_fe_nvm_current_code(K1_FE_PD_PDO3_MA) == 15, "5.0 A must be NVM code 15");
static_assert(k1_fe_nvm_current_ma(k1_fe_nvm_current_code(K1_FE_PD_PDO1_MA)) == K1_FE_PD_PDO1_MA, "PDO1 round trip");
static_assert(k1_fe_nvm_current_ma(k1_fe_nvm_current_code(K1_FE_PD_PDO2_MA)) == K1_FE_PD_PDO2_MA, "PDO2 round trip");
static_assert(k1_fe_nvm_current_ma(k1_fe_nvm_current_code(K1_FE_PD_PDO3_MA)) == K1_FE_PD_PDO3_MA, "PDO3 round trip");
static const uint16_t K1_FE_PD_PDO23_V50 = (uint16_t)(K1_FE_PD_PDO23_MV / 50u);  // 10-bit, 50 mV units
static_assert(K1_FE_PD_PDO23_MV / 50u < 1024u, "PDO voltage must fit the 10-bit NVM field");

// ── State ───────────────────────────────────────────────────────────────────
enum K1FeSrcOverride : uint8_t { K1_FE_SRC_AUTO = 0, K1_FE_SRC_MIC = 1, K1_FE_SRC_LINE = 2 };

static bool s_board;            // STUSB4500 answered at boot; written once before led_task exists
static uint8_t s_device_id;
static bool s_permit;
static bool s_led_enable;
static uint32_t s_pg_high_since;
static uint32_t s_permit_at;
static uint32_t s_led_enable_at;
static bool s_led_pg_reported;
static int s_led_pg_a = -1;
static int s_led_pg_b = -1;
static int s_pd_fault_n = -1;
static uint32_t s_dark_reported_at;
static bool s_dark_reported;
static bool s_latched_off;      // 20 V input kept dropping while lit: LEDs stay off until reboot
static uint32_t s_pg_drop_at[K1_FE_PG_DROP_LATCH_COUNT];
static int s_pg_drop_n;
static bool s_cal_hold_reported;

static bool s_jack_raw;
static bool s_jack_stable;
static uint32_t s_jack_changed_at;
static K1FeSrcOverride s_override = K1_FE_SRC_AUTO;
static bool s_line_selected;
static bool s_line_active;      // latched per hop by k1_fe_audio_line_hop_begin()
static int s_reported_source = -1;
static bool s_unavailable_reported;

// ── STUSB4500 I2C ───────────────────────────────────────────────────────────
static bool pd_write(uint8_t reg, const uint8_t *data, size_t n) {
  Wire.beginTransmission((uint8_t)K1_FE_STUSB4500_ADDR);
  Wire.write(reg);
  Wire.write(data, n);
  return Wire.endTransmission() == 0;
}

static bool pd_write1(uint8_t reg, uint8_t value) { return pd_write(reg, &value, 1); }

static bool pd_read(uint8_t reg, uint8_t *data, size_t n) {
  Wire.beginTransmission((uint8_t)K1_FE_STUSB4500_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission() != 0) {
    return false;
  }
  if (Wire.requestFrom((uint16_t)K1_FE_STUSB4500_ADDR, n, true) != n) {
    return false;
  }
  for (size_t i = 0; i < n; i++) {
    data[i] = (uint8_t)Wire.read();
  }
  return true;
}

// FTP_CUST_REQ is cleared by the NVM controller when an operation finishes.
static bool pd_wait_req_clear(uint32_t timeout_ms) {
  const uint32_t t0 = millis();
  for (;;) {
    uint8_t v = 0;
    if (!pd_read(STUSB_FTP_CTRL_0, &v, 1)) {
      return false;
    }
    if ((v & FTP_CUST_REQ) == 0) {
      return true;
    }
    if (millis() - t0 >= timeout_ms) {
      return false;
    }
#ifdef K1_AUDIO_FREEZE_GUARD_V1
    feedLoopWDT();  // erase can take hundreds of ms; never let the loop watchdog cut a write
#endif
    delay(2);
  }
}

static bool pd_ftp_op(uint8_t opcode, uint8_t sector, uint32_t timeout_ms) {
  return pd_write1(STUSB_FTP_CTRL_1, (uint8_t)(opcode & FTP_CUST_OPCODE)) &&
         pd_write1(STUSB_FTP_CTRL_0, (uint8_t)((sector & FTP_CUST_SECT) | FTP_CUST_PWR |
                                                FTP_CUST_RST_N | FTP_CUST_REQ)) &&
         pd_wait_req_clear(timeout_ms);
}

static bool pd_nvm_exit() {
  const bool a = pd_write1(STUSB_FTP_CTRL_0, FTP_CUST_RST_N);
  const bool b = pd_write1(STUSB_FTP_PASSWORD_REG, 0x00);
  return a && b;
}

static bool pd_nvm_read(uint8_t s[K1_FE_NVM_SECTORS][K1_FE_NVM_SECTOR_BYTES]) {
  bool ok = pd_write1(STUSB_FTP_PASSWORD_REG, STUSB_FTP_PASSWORD) &&
            pd_write1(STUSB_FTP_CTRL_0, 0x00) &&
            pd_write1(STUSB_FTP_CTRL_0, FTP_CUST_PWR | FTP_CUST_RST_N);
  for (int i = 0; ok && i < K1_FE_NVM_SECTORS; i++) {
    ok = pd_write1(STUSB_FTP_CTRL_0, FTP_CUST_PWR | FTP_CUST_RST_N) &&
         pd_ftp_op(FTP_OP_READ, (uint8_t)i, 500) &&
         pd_read(STUSB_RW_BUFFER, s[i], K1_FE_NVM_SECTOR_BYTES);
  }
  const bool exit_ok = pd_nvm_exit();
  return ok && exit_ok;
}

static bool pd_nvm_write_all(const uint8_t s[K1_FE_NVM_SECTORS][K1_FE_NVM_SECTOR_BYTES]) {
  // Enter write mode and erase all five sectors.
  bool ok = pd_write1(STUSB_FTP_PASSWORD_REG, STUSB_FTP_PASSWORD) &&
            pd_write1(STUSB_RW_BUFFER, 0x00) &&  // must be NULL for the erase
            pd_write1(STUSB_FTP_CTRL_0, 0x00) &&
            pd_write1(STUSB_FTP_CTRL_0, FTP_CUST_PWR | FTP_CUST_RST_N) &&
            pd_write1(STUSB_FTP_CTRL_1, (uint8_t)(((FTP_ALL_SECTORS << 3) & FTP_CUST_SER) |
                                                  (FTP_OP_WRITE_SER & FTP_CUST_OPCODE))) &&
            pd_write1(STUSB_FTP_CTRL_0, FTP_CUST_PWR | FTP_CUST_RST_N | FTP_CUST_REQ) &&
            pd_wait_req_clear(2000) &&
            pd_ftp_op(FTP_OP_SOFT_PROG_SECTOR, 0, 2000) &&
            pd_ftp_op(FTP_OP_ERASE_SECTOR, 0, 2000);
  for (int i = 0; ok && i < K1_FE_NVM_SECTORS; i++) {
    ok = pd_write(STUSB_RW_BUFFER, s[i], K1_FE_NVM_SECTOR_BYTES) &&
         pd_write1(STUSB_FTP_CTRL_0, FTP_CUST_PWR | FTP_CUST_RST_N) &&
         pd_ftp_op(FTP_OP_WRITE_PL, 0, 500) &&
         pd_ftp_op(FTP_OP_PROG_SECTOR, (uint8_t)i, 500);
  }
  const bool exit_ok = pd_nvm_exit();
  return ok && exit_ok;
}

// NVM field map (SparkFun_STUSB4500 read()/write(), checked against ST's
// factory default sectors, which decode to 5 V 1.5 A / 15 V 1.5 A / 20 V 1.0 A).
static void pd_profile_apply(uint8_t s[K1_FE_NVM_SECTORS][K1_FE_NVM_SECTOR_BYTES]) {
  s[3][2] = (uint8_t)((s[3][2] & 0xF9) | (K1_FE_PD_PDO_COUNT << 1));                         // PDO count, bits 2:1
  s[3][2] = (uint8_t)((s[3][2] & 0x0F) | (k1_fe_nvm_current_code(K1_FE_PD_PDO1_MA) << 4));  // PDO1 current
  s[3][4] = (uint8_t)((s[3][4] & 0xF0) | k1_fe_nvm_current_code(K1_FE_PD_PDO2_MA));         // PDO2 current
  s[3][5] = (uint8_t)((s[3][5] & 0x0F) | (k1_fe_nvm_current_code(K1_FE_PD_PDO3_MA) << 4));  // PDO3 current
  s[4][0] = (uint8_t)((s[4][0] & 0x3F) | ((K1_FE_PD_PDO23_V50 & 0x03) << 6));               // PDO2 V bits 1:0
  s[4][1] = (uint8_t)(K1_FE_PD_PDO23_V50 >> 2);                                             // PDO2 V bits 9:2
  s[4][2] = (uint8_t)(K1_FE_PD_PDO23_V50 & 0xFF);                                           // PDO3 V bits 7:0
  s[4][3] = (uint8_t)((s[4][3] & 0xFC) | (K1_FE_PD_PDO23_V50 >> 8));                        // PDO3 V bits 9:8
}

static void pd_profile_print(const char *tag, const uint8_t s[K1_FE_NVM_SECTORS][K1_FE_NVM_SECTOR_BYTES]) {
  const uint32_t pdo2_v50 = ((uint32_t)s[4][1] << 2) | ((uint32_t)s[4][0] >> 6);
  const uint32_t pdo3_v50 = (((uint32_t)s[4][3] & 0x03) << 8) | (uint32_t)s[4][2];
  USBSerial.printf("[PDNVM] %s pdo_count=%u pdo1=5000mV/%umA pdo2=%umV/%umA pdo3=%umV/%umA gpio_cfg=%u\n", tag,
                   (unsigned)((s[3][2] & 0x06) >> 1),
                   (unsigned)k1_fe_nvm_current_ma((uint8_t)((s[3][2] & 0xF0) >> 4)),
                   (unsigned)(pdo2_v50 * 50u), (unsigned)k1_fe_nvm_current_ma((uint8_t)(s[3][4] & 0x0F)),
                   (unsigned)(pdo3_v50 * 50u), (unsigned)k1_fe_nvm_current_ma((uint8_t)((s[3][5] & 0xF0) >> 4)),
                   (unsigned)((s[1][0] & 0x30) >> 4));
  for (int i = 0; i < K1_FE_NVM_SECTORS; i++) {
    USBSerial.printf("[PDNVM] %s sector%d=", tag, i);
    for (int b = 0; b < K1_FE_NVM_SECTOR_BYTES; b++) {
      USBSerial.printf("%02X", s[i][b]);
    }
    USBSerial.println();
  }
}

// golden = operator recovery (`:pd_nvm_write=golden`): write the FE image even
// when the chip holds neither the ST factory image nor the FE image (e.g. a
// write that was interrupted part-way).
static void k1_fe_pd_nvm_write(bool golden) {
  if (!s_board) {
    USBSerial.println("[PDNVM] FAIL reason=stusb4500_not_detected");
    return;
  }
  uint8_t before[K1_FE_NVM_SECTORS][K1_FE_NVM_SECTOR_BYTES] = {};
  if (!pd_nvm_read(before)) {
    USBSerial.println("[PDNVM] FAIL reason=nvm_read_before");
    return;
  }
  pd_profile_print("before", before);
  uint8_t target[K1_FE_NVM_SECTORS][K1_FE_NVM_SECTOR_BYTES];
  memcpy(target, K1_FE_ST_FACTORY_NVM, sizeof(target));
  pd_profile_apply(target);
  const bool already = (memcmp(target, before, sizeof(target)) == 0);
  const bool factory = (memcmp(K1_FE_ST_FACTORY_NVM, before, sizeof(before)) == 0);
  if (already) {
    USBSerial.println("[PDNVM] already_programmed=1 write=SKIPPED");
  } else if (!factory && !golden) {
    USBSerial.println("[PDNVM] FAIL reason=unrecognised_nvm_image (neither ST factory nor FE profile); "
                      "nothing written. Review the sectors above; recovery: :pd_nvm_write=golden");
    return;
  } else {
    USBSerial.printf("[PDNVM] writing %s (show pauses about 1 s)...\n",
                     factory ? "factory->FE" : "GOLDEN over unrecognised image");
    if (!pd_nvm_write_all(target)) {
      USBSerial.println("[PDNVM] FAIL reason=nvm_write (rerun :pd_nvm_write=golden)");
      return;
    }
  }
  uint8_t after[K1_FE_NVM_SECTORS][K1_FE_NVM_SECTOR_BYTES] = {};
  if (!pd_nvm_read(after)) {
    USBSerial.println("[PDNVM] FAIL reason=nvm_read_after");
    return;
  }
  pd_profile_print("after", after);
  const bool match = (memcmp(after, target, sizeof(after)) == 0);
  USBSerial.printf("[PDNVM] %s readback=%s profile=5V0.5A/20V3A/20V5A%s\n", match ? "PASS" : "FAIL",
                   match ? "match" : "MISMATCH",
                   (match && !already) ? " takes_effect=after_unplug_replug" : "");
}

static void k1_fe_pd_status() {
  if (!s_board) {
    USBSerial.println("[FEPD] stusb4500=not_detected");
    return;
  }
  uint8_t numb = 0;
  uint8_t pdo[12] = {};
  uint8_t rdo[4] = {};
  const bool ok = pd_read(STUSB_DPM_PDO_NUMB, &numb, 1) && pd_read(STUSB_DPM_SNK_PDO1, pdo, sizeof(pdo)) &&
                  pd_read(STUSB_RDO_STATUS, rdo, sizeof(rdo));
  if (!ok) {
    USBSerial.println("[FEPD] FAIL reason=i2c_read");
    return;
  }
  USBSerial.printf("[FEPD] sink_pdo_count=%u", (unsigned)(numb & 0x07));
  for (int i = 0; i < 3; i++) {
    const uint32_t w = (uint32_t)pdo[4 * i] | ((uint32_t)pdo[4 * i + 1] << 8) |
                       ((uint32_t)pdo[4 * i + 2] << 16) | ((uint32_t)pdo[4 * i + 3] << 24);
    USBSerial.printf(" pdo%d=%umV/%umA", i + 1, (unsigned)(((w >> 10) & 0x3FF) * 50u),
                     (unsigned)((w & 0x3FF) * 10u));
  }
  USBSerial.println();
  const uint32_t r = (uint32_t)rdo[0] | ((uint32_t)rdo[1] << 8) | ((uint32_t)rdo[2] << 16) |
                     ((uint32_t)rdo[3] << 24);
  const unsigned obj = (unsigned)((r >> 28) & 0x07);
  USBSerial.printf("[FEPD] contract=%s source_pdo=%u op_ma=%u max_ma=%u mismatch=%u input_20v_pg=%d\n",
                   obj ? "PD" : "none(typec_5V)", obj, (unsigned)(((r >> 10) & 0x3FF) * 10u),
                   (unsigned)((r & 0x3FF) * 10u), (unsigned)((r >> 26) & 0x01),
                   digitalRead(K1_FE_INPUT_20V_PG_PIN));
}

// ── Power policy ────────────────────────────────────────────────────────────
static void k1_fe_set_power(bool permit, bool led_enable) {
  // LED_ENABLE always drops before POWER_PERMIT and rises after it.
  if (!led_enable) {
    gpio_set_level((gpio_num_t)K1_FE_LED_ENABLE_PIN, 0);
  }
  gpio_set_level((gpio_num_t)K1_FE_POWER_PERMIT_PIN, permit ? 1 : 0);
  if (led_enable) {
    gpio_set_level((gpio_num_t)K1_FE_LED_ENABLE_PIN, 1);
  }
  s_permit = permit;
  s_led_enable = led_enable;
}

static void k1_fe_report_dark(uint32_t t_now) {
  USBSerial.println("[FEPWR] input=5V_only led_enable=0 permit=0 LEDs stay dark: INPUT_20V_PG is low "
                    "(no 20 V USB-C PD contract). Use a 20 V USB-C PD supply to light the LEDs.");
  s_dark_reported = true;
  s_dark_reported_at = t_now;
}

static void k1_fe_power_poll(uint32_t t_now) {
  const bool pg = digitalRead(K1_FE_INPUT_20V_PG_PIN) != 0;
  if (!pg) {
    s_pg_high_since = 0;
    if (s_permit || s_led_enable) {
      k1_fe_set_power(false, false);
      s_led_pg_a = s_led_pg_b = -1;
      USBSerial.println("[FEPWR] INPUT_20V_PG fell: led_enable=0 permit=0");
      // Strobe guard: a supply that sags under LED load would otherwise cycle
      // the whole plate on and off every ~270 ms.
      const int slot = s_pg_drop_n % K1_FE_PG_DROP_LATCH_COUNT;
      const uint32_t oldest = s_pg_drop_at[slot];
      s_pg_drop_at[slot] = t_now;
      s_pg_drop_n++;
      if (s_pg_drop_n >= K1_FE_PG_DROP_LATCH_COUNT && (t_now - oldest) <= K1_FE_PG_DROP_LATCH_WINDOW_MS) {
        s_latched_off = true;
        USBSerial.printf("[FEPWR] LATCHED OFF: 20 V input dropped %d times in %u ms while lit; LEDs stay off "
                         "until the board is unplugged and replugged. Use a stronger 20 V USB-C PD supply.\n",
                         K1_FE_PG_DROP_LATCH_COUNT, (unsigned)K1_FE_PG_DROP_LATCH_WINDOW_MS);
      }
      k1_fe_report_dark(t_now);
    } else if (!s_dark_reported || (t_now - s_dark_reported_at) >= K1_FE_DARK_REMINDER_MS) {
      k1_fe_report_dark(t_now);
    }
  } else {
    if (s_pg_high_since == 0) {
      s_pg_high_since = t_now ? t_now : 1;
    }
    if (s_latched_off) {
      // stay dark; logged once when the latch tripped
    } else if (!s_permit && (t_now - s_pg_high_since) >= K1_FE_PG_RISE_STABLE_MS) {
      k1_fe_set_power(true, false);
      s_permit_at = t_now;
    } else if (s_permit && !s_led_enable && (t_now - s_permit_at) >= K1_FE_PERMIT_TO_LED_MS) {
      k1_fe_set_power(true, true);
      s_led_enable_at = t_now;
      s_led_pg_reported = false;
      s_dark_reported = false;
      USBSerial.println("[FEPWR] input=20V permit=1 led_enable=1");
    }
  }
  if (s_led_enable && (t_now - s_led_enable_at) >= K1_FE_LED_PG_READ_MS) {
    const int a = digitalRead(K1_FE_LED_PG_A_PIN);
    const int b = digitalRead(K1_FE_LED_PG_B_PIN);
    if (!s_led_pg_reported || a != s_led_pg_a || b != s_led_pg_b) {
      USBSerial.printf("[FEPWR] LED_PG_A=%d LED_PG_B=%d%s\n", a, b,
                       (a && b) ? " banks=OK" : " banks=FAULT (eFuse off: overload, short or no 5 V LED rail)");
      s_led_pg_a = a;
      s_led_pg_b = b;
      s_led_pg_reported = true;
    }
  }
  const int fault_n = digitalRead(K1_FE_PD_FAULT_N_PIN);
  if (fault_n != s_pd_fault_n) {
    USBSerial.printf("[FEPWR] PD_FAULT_N=%d%s\n", fault_n, fault_n ? "" : " (STUSB4500 reports a fault)");
    s_pd_fault_n = fault_n;
  }
}

// ── Audio source ────────────────────────────────────────────────────────────
static void k1_fe_source_poll(uint32_t t_now) {
  if (s_board) {
    const bool raw = digitalRead(K1_FE_JACK_DET_PIN) != 0;
    if (raw != s_jack_raw) {
      s_jack_raw = raw;
      s_jack_changed_at = t_now;
    } else if (raw != s_jack_stable && (t_now - s_jack_changed_at) >= K1_FE_JACK_STABLE_MS) {
      s_jack_stable = raw;
    }
  }
  bool want_line;
  const char *reason;
  if (s_override == K1_FE_SRC_LINE) {
    want_line = true;
    reason = "override_line";
  } else if (s_override == K1_FE_SRC_MIC) {
    want_line = false;
    reason = "override_mic";
  } else if (!s_board) {
    want_line = false;
    reason = "auto_no_fe_board";  // jack pin is not wired on non-FE units
  } else {
    want_line = s_jack_stable;
    reason = s_jack_stable ? "jack_in" : "jack_out";
  }
  if (want_line && !k1_pcm1808_clock_gate_pass()) {
    if (!s_unavailable_reported) {
      USBSerial.printf("[FEAUD] line-in requested (%s) but UNAVAILABLE: PCM1808 clock gate failed at boot; "
                       "staying on mic\n", reason);
      s_unavailable_reported = true;
    }
    want_line = false;
  } else if (!want_line) {
    s_unavailable_reported = false;
  }
  s_line_selected = want_line;
  if ((int)want_line != s_reported_source) {
    USBSerial.printf("[FEAUD] source=%s reason=%s jack=%s\n", want_line ? "line" : "mic", reason,
                     s_board ? (s_jack_stable ? "in" : "out") : "n/a");
    s_reported_source = (int)want_line;
  }
}

// ── Public ──────────────────────────────────────────────────────────────────
static void k1_fe_input(int pin) {
  gpio_config_t io = {};
  io.pin_bit_mask = 1ULL << pin;
  io.mode = GPIO_MODE_INPUT;
  io.pull_up_en = GPIO_PULLUP_DISABLE;     // the board carries the pull resistors
  io.pull_down_en = GPIO_PULLDOWN_DISABLE;
  io.intr_type = GPIO_INTR_DISABLE;
  gpio_config(&io);
}

static void k1_fe_output_low(int pin) {
  gpio_set_level((gpio_num_t)pin, 0);
  gpio_config_t io = {};
  io.pin_bit_mask = 1ULL << pin;
  io.mode = GPIO_MODE_OUTPUT;
  io.pull_up_en = GPIO_PULLUP_DISABLE;
  io.pull_down_en = GPIO_PULLDOWN_DISABLE;
  io.intr_type = GPIO_INTR_DISABLE;
  gpio_config(&io);
  gpio_set_level((gpio_num_t)pin, 0);
}

void k1_fe_board_begin() {
#ifdef K1_EMU_FE_MIC_ONLY
#ifndef K1_EMU_FIXTURE
#error "K1_EMU_FE_MIC_ONLY requires the non-uploadable replay fixture"
#endif
  // The replay supplies microphone PCM; it does not model FE peripherals.
  return;
#endif
  s_board = false;
  if (Wire.begin(K1_FE_PD_SDA_PIN, K1_FE_PD_SCL_PIN, 100000)) {
    for (int attempt = 0; attempt < 3 && !s_board; attempt++) {
      Wire.beginTransmission((uint8_t)K1_FE_STUSB4500_ADDR);
      s_board = (Wire.endTransmission() == 0);
      if (!s_board) {
        delay(10);
      }
    }
  }
  if (!s_board) {
    Wire.end();
    USBSerial.println("[FEBOARD] stusb4500=absent fe_board=0 outputs=passive (LED_ENABLE/POWER_PERMIT/heartbeat "
                      "not driven) jack=ignored source=mic");
    k1_fe_source_poll(millis());
    return;
  }
  (void)pd_read(STUSB_DEVICE_ID, &s_device_id, 1);
  USBSerial.printf("[FEBOARD] stusb4500=present addr=0x%02X device_id=0x%02X fe_board=1\n",
                   (unsigned)K1_FE_STUSB4500_ADDR, (unsigned)s_device_id);
  k1_fe_input(K1_FE_LED_PG_A_PIN);
  k1_fe_input(K1_FE_LED_PG_B_PIN);
  k1_fe_input(K1_FE_INPUT_20V_PG_PIN);
  k1_fe_input(K1_FE_PD_FAULT_N_PIN);
  k1_fe_input(K1_FE_JACK_DET_PIN);
  k1_fe_output_low(K1_FE_LED_ENABLE_PIN);
  k1_fe_output_low(K1_FE_POWER_PERMIT_PIN);
  k1_fe_output_low(K1_FE_HEARTBEAT_PIN);
  s_permit = false;
  s_led_enable = false;

  // Jack state at boot: settle before the first hop so a plugged cable starts on line-in.
  s_jack_raw = s_jack_stable = digitalRead(K1_FE_JACK_DET_PIN) != 0;

  // Boot power: if 20 V is already stable, light the rails now so the intro is visible.
  bool pg_stable = true;
  for (uint32_t i = 0; i < K1_FE_PG_RISE_STABLE_MS / 10u && pg_stable; i++) {
    pg_stable = digitalRead(K1_FE_INPUT_20V_PG_PIN) != 0;
    delay(10);
  }
  const uint32_t t_now = millis();
  if (pg_stable) {
    k1_fe_set_power(true, false);
    delay(K1_FE_PERMIT_TO_LED_MS);
    k1_fe_set_power(true, true);
    s_pg_high_since = t_now ? t_now : 1;
    s_permit_at = t_now;
    s_led_enable_at = millis();
    s_led_pg_reported = false;
    USBSerial.println("[FEPWR] input=20V permit=1 led_enable=1");
  }
  k1_fe_power_poll(millis());
  k1_fe_source_poll(millis());
  k1_fe_pd_status();
}

void k1_fe_board_poll(uint32_t t_now_ms) {
  if (s_board) {
    k1_fe_power_poll(t_now_ms);
  }
  k1_fe_source_poll(t_now_ms);
}

void k1_fe_heartbeat_tick(int64_t now_us) {
  static int64_t last_us = 0;
  static int level = 0;
  if (!s_board) {
    return;
  }
  if (now_us - last_us >= K1_FE_HEARTBEAT_HALF_US) {
    last_us = now_us;
    level ^= 1;
    gpio_set_level((gpio_num_t)K1_FE_HEARTBEAT_PIN, level);
  }
}

bool k1_fe_audio_line_hop_begin(bool hold_mic) {
  if (hold_mic && s_line_selected) {
    if (!s_cal_hold_reported) {
      USBSerial.println("[FEAUD] noise calibration running: holding the mic until it finishes");
      s_cal_hold_reported = true;
    }
    s_line_active = false;
    return false;
  }
  s_cal_hold_reported = false;
  s_line_active = s_line_selected;
  return s_line_active;
}

bool k1_fe_audio_line_active() { return s_line_active; }

static void k1_fe_status() {
  USBSerial.printf("[FESTATUS] fe_board=%d stusb4500=%s permit=%d led_enable=%d input_20v_pg=%d "
                   "led_pg_a=%d led_pg_b=%d pd_fault_n=%d\n",
                   s_board ? 1 : 0, s_board ? "present" : "absent", s_permit ? 1 : 0, s_led_enable ? 1 : 0,
                   s_board ? digitalRead(K1_FE_INPUT_20V_PG_PIN) : -1,
                   s_board ? digitalRead(K1_FE_LED_PG_A_PIN) : -1,
                   s_board ? digitalRead(K1_FE_LED_PG_B_PIN) : -1,
                   s_board ? digitalRead(K1_FE_PD_FAULT_N_PIN) : -1);
  USBSerial.printf("[FESTATUS] source=%s override=%s jack=%s pcm1808_gate=%s\n",
                   s_line_active ? "line" : "mic",
                   s_override == K1_FE_SRC_LINE ? "line" : s_override == K1_FE_SRC_MIC ? "mic" : "auto",
                   s_board ? (s_jack_stable ? "in" : "out") : "n/a",
                   k1_pcm1808_clock_gate_pass() ? "PASS" : "FAIL");
  if (s_latched_off) {
    USBSerial.println("[FESTATUS] power=LATCHED_OFF (20 V input unstable; replug to retry)");
  }
  if (k1_pcm1808_clock_gate_pass()) {
    k1_pcm1808_print_telemetry();  // line-in stats since the last print (on demand only)
  }
}

bool k1_fe_board_dispatch(const char *command_type, char *command_data) {
  if (strcmp(command_type, "fe_status") == 0) {
    k1_fe_status();
    return true;
  }
  if (strcmp(command_type, "pd_status") == 0) {
    k1_fe_pd_status();
    return true;
  }
  if (strcmp(command_type, "pd_nvm_write") == 0) {
    if (command_data[0] != 0 && strcmp(command_data, "golden") != 0) {
      USBSerial.println("[PDNVM] usage: pd_nvm_write  |  pd_nvm_write=golden (recovery)");
      return true;
    }
    k1_fe_pd_nvm_write(strcmp(command_data, "golden") == 0);
    return true;
  }
  if (strcmp(command_type, "audio_src") == 0) {
    if (strcmp(command_data, "auto") == 0) {
      s_override = K1_FE_SRC_AUTO;
    } else if (strcmp(command_data, "mic") == 0) {
      s_override = K1_FE_SRC_MIC;
    } else if (strcmp(command_data, "line") == 0) {
      s_override = K1_FE_SRC_LINE;
    } else {
      USBSerial.println("[FEAUD] usage: audio_src=auto|mic|line");
      return true;
    }
    USBSerial.printf("[FEAUD] override=%s (RAM only; reboot returns to auto)\n", command_data);
    k1_fe_source_poll(millis());
    return true;
  }
  return false;
}

#endif  // K1_FE_BOARD_V1
