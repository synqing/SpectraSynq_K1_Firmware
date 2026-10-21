#include "k1_emu_fixture.h"

#ifdef K1_EMU_FIXTURE

#include <Arduino.h>
#include <FastLED.h>
#include <string.h>

#include "esp_crc.h"
#include "esp_partition.h"
#include "esp_timer.h"

#include "k1_audio_frame.h"
#include "k1_tempo.h"
#include "k1_audio_snapshot.h"
#include "globals.h"
#include "../control/k1_show_state.h"

extern void parse_command(char* command_buf);
extern void check_serial(uint32_t t_now);
bool k1_render_trace_dispatch(const char* command_type, char* command_data);

// Builtin smoke PCM: used only when the run-owned scenario blob is absent.
#include "k1_emu_pcm.inc"

namespace {

// ---- Scenario blob (little-endian, see tools/esp_emulator/README.md) ----
constexpr char kMagic[8] = {'K', '1', 'E', 'M', 'U', 'S', 'C', '2'};
constexpr uint32_t kVersion = 2;
constexpr uint32_t kHeaderBytes = 256;
constexpr uint32_t kCommandBytes = 96;
constexpr uint32_t kCommandText = 88;
constexpr uint32_t kMaxCommands = 64;
constexpr uint32_t kFlagRecovery = 1u << 0;
// Pre-audio segment: the application clock follows the emulated monotonic
// timer from reset until the first hop (as millis() does on hardware), then
// hands off to epoch + processed samples. Without it the epoch is 0.
constexpr uint32_t kFlagBootEpoch = 1u << 1;
// Declared epoch: the same monotonic pre-audio clock, but the first hop is
// placed at the declared application time (header declared_epoch_us). It must
// not be earlier than the boot time already observed.
constexpr uint32_t kFlagDeclaredEpoch = 1u << 2;
// Per-hop novelty trace: the snapshot fields k1_tempo_update() consumed for
// every publication, dumped as N lines at the end (diagnostic, opt-in).
constexpr uint32_t kFlagNoveltyTrace = 1u << 3;
constexpr uint32_t kMaxNovelty = 16000;  // 120 s of hops
// Client transport: an external client drives the product's USBSerial on
// esp-emu --console usb-jtag. The fixture trace moves to UART1 (--uart1-tcp)
// and the fixture waits for the runner's ready line before printing anything.
constexpr uint32_t kFlagClientTransport = 1u << 4;
// UART1 pins for the client-transport trace. The Arduino defaults (15/16) are
// the Main RPL LED data/clock pins; 6/7 are unused there and not strapping/USB.
constexpr int kClientTraceTx = 6;
constexpr int kClientTraceRx = 7;
constexpr char kClientReady[] = "K1EMU-GO";
// Command record kind (the word after the hop, zero in older blobs).
constexpr uint32_t kCmdScheduled = 0;  // the fixture runs it through parse_command
constexpr uint32_t kCmdClient = 1;     // a client sends it; the fixture only waits

struct __attribute__((packed)) BlobHeader {
  char magic[8];
  uint32_t version;
  uint32_t header_bytes;
  char run_id[48];
  uint32_t sample_rate;
  uint32_t hop_samples;
  uint32_t real_samples;
  uint32_t pad_samples;
  uint32_t capture_start_hop;
  uint32_t capture_end_hop;
  uint32_t capture_every;
  uint32_t flags;
  uint32_t command_count;
  uint32_t command_offset;
  uint32_t pcm_offset;
  uint32_t stall_ms;
  uint32_t blob_bytes;
  uint32_t payload_crc32;
  uint64_t declared_epoch_us;
  uint8_t reserved[124];
  uint32_t header_crc32;
};
static_assert(sizeof(BlobHeader) == kHeaderBytes, "scenario header is 256 bytes");

struct Command {
  uint32_t hop;
  uint32_t kind;
  char text[kCommandText];
};

constexpr uint32_t kHop = 96;
constexpr size_t kHopBytes = kHop * sizeof(int16_t);

const esp_partition_t* s_part = nullptr;
bool s_from_blob = false;
bool s_valid = false;
char s_run_id[48] = "builtin";
uint32_t s_rate = 12800;
uint32_t s_real_samples = 0;
uint32_t s_pad_samples = 0;
uint32_t s_total_hops = 0;
uint32_t s_cap_start = 0;
uint32_t s_cap_end = 0xFFFFFFFFu;
uint32_t s_cap_every = 1;
uint32_t s_flags = 0;
uint32_t s_stall_ms = 20000;
uint32_t s_pcm_offset = 0;
uint32_t s_payload_crc = 0;
uint32_t s_cmd_count = 0;
uint32_t s_sched_count = 0;    // kCmdScheduled records
uint32_t s_gate_count = 0;     // kCmdClient records
Command s_cmds[kMaxCommands];
const char* s_invalid = nullptr;
bool s_client = false;         // client transport: trace on UART1

// ---- Progression ----
bool s_started = false;
bool s_finished = false;
uint32_t s_next_hop = 0;       // next hop index to stage
bool s_staged = false;
int16_t s_stage_buf[kHop];
uint64_t s_admitted = 0;       // real input samples admitted
uint64_t s_processed = 0;      // samples processed, real + declared padding
uint32_t s_admits_since_pub = 0;
uint32_t s_unstaged_admits = 0;
uint32_t s_pub_without_hop = 0;
uint32_t s_pub_count = 0;
uint32_t s_last_pub_gen = 0;
uint32_t s_saves = 0;
uint32_t s_rejects = 0;
uint32_t s_commands_run = 0;
uint32_t s_host_commands = 0;  // lines the production receive loop parsed from USBSerial
uint32_t s_host_rejects_before = 0;
uint32_t s_host_hop = 0;
bool s_in_host_command = false;
uint32_t s_power_mw = 0;       // 0 = no FastLED power limit installed
bool s_audio_started = false;  // first hop staged: clock is epoch + processed
constexpr uint32_t kEmuRngSeed = 0x9E3779B9u;
uint32_t s_rng = kEmuRngSeed;
uint32_t s_rng_draws = 0;
uint64_t s_epoch_us = 0;
uint64_t s_declared_epoch_us = 0;

bool monotonic_pre_audio() { return (s_flags & (kFlagBootEpoch | kFlagDeclaredEpoch)) != 0; }

const char* epoch_policy() {
  if (s_flags & kFlagDeclaredEpoch) return "declared";
  if (s_flags & kFlagBootEpoch) return "boot_monotonic";
  return "zero";
}

// The audio meaning a publication carries, as seen by the producer (P) and
// by the render thread that consumed it (C). Same generation, same fields.
struct Meaning {
  uint32_t generation;
  uint32_t onset_seq;
  uint32_t beat_seq;
  float onset_strength;
  float bpm;
  float phase01;
  float confidence;
  bool locked;
  bool beat_tick;
};

struct PubRecord {
  uint32_t generation;
  uint32_t admitted;
  uint32_t processed;
  uint32_t app_us;
  Meaning meaning;
};

Meaning meaning_of(const K1AudioFrame& f, bool producer) {
  Meaning m = {};
  m.generation = f.ap_generation;
  m.onset_seq = f.onset_sequence_total;
  m.beat_seq = f.beat_sequence_total;
  m.onset_strength = f.last_onset_strength;
#ifdef K1_SEMANTIC_STATE
  // The renderer's tempo/beat view travels in the frame's semantic snapshot.
  m.bpm = f.semantic.bpm;
  m.phase01 = f.semantic.beat_phase01;
  m.confidence = f.semantic.tempo_confidence;
  m.locked = f.semantic.tempo_locked;
  m.beat_tick = f.semantic.beat_tick;
  (void)producer;
#else
  if (producer) {
    const K1TempoEvent t = k1_tempo_read();
    m.bpm = t.bpm;
    m.phase01 = t.phase01;
    m.confidence = t.confidence;
    m.locked = t.locked;
    m.beat_tick = t.beat_tick;
  }
#endif
  return m;
}
constexpr uint32_t kRing = 16;
PubRecord s_ring[kRing];

volatile uint32_t s_consumed_gen = 0;
volatile bool s_render_ready = false;
volatile uint32_t s_shown_gen = 0;
uint32_t s_consumed_notes = 0;
uint32_t s_shown_notes = 0;
uint32_t s_pre_audio_shows = 0;

constexpr uint16_t kMaxSidecar = 2000;  // = dual-edge trace capacity
// Per-capture source identity, kept in PSRAM beside the trace itself.
struct CapRecord {
  uint32_t generation;
  uint32_t admitted;
  uint32_t processed;
  uint32_t app_us;
  uint32_t power_mw;
  uint8_t limit_scale;
  Meaning producer;
  Meaning consumed;
  uint32_t render_state[7];  // raw bits of render-thread globals at store time
};
CapRecord* s_cap = nullptr;
struct NoveltyRecord {
  float novelty;
  float vu_level;
  uint8_t silence;
  uint32_t producer_crc;  // snapshot + spectrogram + chromagram_smooth at publication
};
NoveltyRecord* s_nov = nullptr;
uint32_t s_nov_count = 0;
#ifdef K1_TEMPO_SILENCE_FROM_PRODUCER_V1
// Lane R1 (DEF-001, I1): the tracker's veto bits, internal lock and latched producer silence for
// every publication, with the published K1TempoEvent fields, printed as K lines after the N lines
// (only when the novelty trace is on): K,gen,veto,internal_locked,producer_silence,locked,beat_tick,conf,bpm
struct GateRecord {
  K1TempoGate gate;
  float bpm;
  float confidence;
  uint8_t locked;
  uint8_t beat_tick;
};
GateRecord* s_gate = nullptr;
#endif
#ifdef K1_EMU_SPECTRUM_TRACE
// Measurement probe only (env k1_main_rpl_emu_tempo_r1_spec, lane R1 Phase 3 feasibility): the
// snapshot's per-note spectrum (K1_ONSET_V2, post-AGC, [0,1]) for every publication, 16-bit
// quantised, printed as P lines after the N lines. Capped at kMaxSpectrum generations (PSRAM).
#ifndef K1_ONSET_V2
#error "K1_EMU_SPECTRUM_TRACE needs K1_ONSET_V2 (snapshot spectrum)"
#endif
constexpr uint32_t kMaxSpectrum = 4200;
uint16_t* s_spec = nullptr;
#endif
#ifdef K1_EMU_TEMPO_PROBE
// Measurement probe only (env k1_main_rpl_emu_tempo_probe, tempo lane R1, 2026-10-21).
// Per generation: loud-guard state of the hop just published, and the tempo tracker's
// internal state + ENABLE_TEMPO_STREAM stage timers (emulated time, not silicon).
// Printed as G lines after the N lines. Never compiled into a product env.
#if !ENABLE_TEMPO_STREAM
#error "K1_EMU_TEMPO_PROBE needs ENABLE_TEMPO_STREAM=1 (stage timers + debug snapshot)"
#endif
struct ProbeRecord {
  float input_trim;
  float gdft_trim;
  uint16_t clip_count;
  uint16_t sample_count;
  uint32_t emit_count;
  uint8_t silence_internal;
  uint8_t locked_internal;
  float conf_ema;
  uint32_t us_silence, us_acf, us_update, us_phase, us_publish, us_emit;
};
ProbeRecord* s_probe = nullptr;
#endif
Meaning s_last_consumed = {};
int32_t s_pending_lim_idx = -1;
uint32_t s_captured = 0;

uint8_t s_last_ss[128];
size_t s_last_ss_len = 0;

const char* hexc = "0123456789abcdef";

void fail_scenario(const char* why) {
  s_valid = false;
  s_invalid = why;
}

void load_blob() {
  s_part = esp_partition_find_first(ESP_PARTITION_TYPE_APP,
                                    ESP_PARTITION_SUBTYPE_APP_OTA_1, nullptr);
  if (s_part == nullptr) return;
  BlobHeader h;
  if (esp_partition_read(s_part, 0, &h, sizeof(h)) != ESP_OK) return;
  if (memcmp(h.magic, kMagic, sizeof(kMagic)) != 0) return;  // no blob: builtin
  s_from_blob = true;
  if (esp_crc32_le(0, (const uint8_t*)&h, offsetof(BlobHeader, header_crc32)) !=
      h.header_crc32) {
    return fail_scenario("header_crc");
  }
  if (h.version != kVersion || h.header_bytes != kHeaderBytes) {
    return fail_scenario("version");
  }
  // Decided first, so a later scenario failure is still reported on the port
  // the runner listens to.
  s_client = (h.flags & kFlagClientTransport) != 0;
  h.run_id[sizeof(h.run_id) - 1] = '\0';
  memcpy(s_run_id, h.run_id, sizeof(s_run_id));
  // Rate and hop are checked against the loaded CONFIG at the first poll.
  if (h.hop_samples != kHop) return fail_scenario("hop_samples");
  if (h.sample_rate == 0) return fail_scenario("sample_rate");
  if (h.pad_samples % kHop != 0) return fail_scenario("pad_alignment");
  if (h.command_count > kMaxCommands) return fail_scenario("command_count");
  if (h.capture_every == 0 || h.capture_end_hop < h.capture_start_hop) {
    return fail_scenario("capture_window");
  }
  if (h.blob_bytes > s_part->size || h.blob_bytes < kHeaderBytes) {
    return fail_scenario("blob_bytes");
  }
  const uint32_t pcm_bytes = h.real_samples * (uint32_t)sizeof(int16_t);
  const uint32_t padded_real = ((h.real_samples + kHop - 1) / kHop) * kHop;
  if (h.pcm_offset + padded_real * sizeof(int16_t) > h.blob_bytes ||
      h.command_offset + h.command_count * kCommandBytes > h.blob_bytes) {
    return fail_scenario("layout");
  }
  (void)pcm_bytes;
  // Payload CRC: commands and PCM, streamed. The host compares this value.
  uint8_t chunk[512];
  uint32_t crc = 0;
  for (uint32_t off = kHeaderBytes; off < h.blob_bytes; off += sizeof(chunk)) {
    const uint32_t n = (h.blob_bytes - off) < sizeof(chunk) ? (h.blob_bytes - off) : sizeof(chunk);
    if (esp_partition_read(s_part, off, chunk, n) != ESP_OK) return fail_scenario("read");
    crc = esp_crc32_le(crc, chunk, n);
  }
  if (crc != h.payload_crc32) return fail_scenario("payload_crc");
  s_payload_crc = crc;
  for (uint32_t i = 0; i < h.command_count; i++) {
    uint8_t raw[kCommandBytes];
    if (esp_partition_read(s_part, h.command_offset + i * kCommandBytes, raw, sizeof(raw)) != ESP_OK) {
      return fail_scenario("read");
    }
    memcpy(&s_cmds[i].hop, raw, sizeof(uint32_t));
    memcpy(&s_cmds[i].kind, raw + 4, sizeof(uint32_t));
    memcpy(s_cmds[i].text, raw + 8, kCommandText);
    s_cmds[i].text[kCommandText - 1] = '\0';
    if (i > 0 && s_cmds[i].hop < s_cmds[i - 1].hop) return fail_scenario("command_order");
    if (s_cmds[i].kind == kCmdScheduled) {
      s_sched_count++;
    } else if (s_cmds[i].kind == kCmdClient) {
      s_gate_count++;
    } else {
      return fail_scenario("command_kind");
    }
  }
  if ((h.flags & kFlagRecovery) != 0 && h.command_count != 0) {
    return fail_scenario("recovery_with_commands");
  }
  if (s_gate_count != 0 && (h.flags & kFlagClientTransport) == 0) {
    return fail_scenario("client_commands_without_client_transport");
  }
  s_rate = h.sample_rate;
  s_real_samples = h.real_samples;
  s_pad_samples = h.pad_samples;
  s_cap_start = h.capture_start_hop;
  s_cap_end = h.capture_end_hop;
  s_cap_every = h.capture_every;
  s_flags = h.flags;
  s_declared_epoch_us = h.declared_epoch_us;
  if ((h.flags & kFlagBootEpoch) && (h.flags & kFlagDeclaredEpoch)) return fail_scenario("epoch_policy");
  s_stall_ms = h.stall_ms != 0 ? h.stall_ms : 20000;
  s_pcm_offset = h.pcm_offset;
  s_cmd_count = h.command_count;
  s_valid = true;
}

void print_show_state(uint32_t generation, const char* when, uint32_t hop, bool only_if_changed) {
  uint8_t buf[128];
  const size_t n = k1_show_state_encode(k1_show_state_capture_live(), buf, sizeof(buf));
  if (only_if_changed && n == s_last_ss_len && memcmp(buf, s_last_ss, n) == 0) return;
  memcpy(s_last_ss, buf, n);
  s_last_ss_len = n;
  char hex[sizeof(buf) * 2 + 1];
  for (size_t i = 0; i < n; i++) {
    hex[2 * i] = hexc[buf[i] >> 4];
    hex[2 * i + 1] = hexc[buf[i] & 0x0F];
  }
  hex[2 * n] = '\0';
  K1_EMU_LOG.printf("EMU_SS gen=%lu when=%s hop=%lu hex=%s\n", (unsigned long)generation, when,
                    (unsigned long)hop, hex);
}

void print_counters(const char* reason, const char* where) {
  K1_EMU_LOG.printf(
      "EMU_END reason=%s where=%s run=%s admitted=%llu processed=%llu staged_hops=%lu "
      "total_hops=%lu published=%lu last_generation=%lu consumed=%lu shown=%lu "
      "last_shown=%lu pre_audio_shows=%lu captured=%lu commands=%lu host_commands=%lu rejects=%lu "
      "saves=%lu rng_draws=%lu "
      "unstaged_admits=%lu publications_without_hop=%lu app_us=%llu\n",
      reason, where, s_run_id, (unsigned long long)s_admitted, (unsigned long long)s_processed,
      (unsigned long)s_next_hop, (unsigned long)s_total_hops, (unsigned long)s_pub_count,
      (unsigned long)s_last_pub_gen, (unsigned long)s_consumed_notes,
      (unsigned long)s_shown_notes, (unsigned long)s_shown_gen,
      (unsigned long)s_pre_audio_shows, (unsigned long)s_captured,
      (unsigned long)s_commands_run, (unsigned long)s_host_commands, (unsigned long)s_rejects,
      (unsigned long)s_saves, (unsigned long)s_rng_draws,
      (unsigned long)s_unstaged_admits, (unsigned long)s_pub_without_hop,
      (unsigned long long)k1_emu_fixture_app_us());
}

[[noreturn]] void finish(const char* reason, const char* where) {
  s_finished = true;
  if (s_nov != nullptr) {
    for (uint32_t i = 0; i < s_nov_count; i++) {
      K1_EMU_LOG.printf("N,%lu,%.6f,%.6f,%u,%08lx\n", (unsigned long)(i + 1), s_nov[i].novelty,
                        s_nov[i].vu_level, (unsigned)s_nov[i].silence, (unsigned long)s_nov[i].producer_crc);
      if ((i & 0xFF) == 0xFF) {
        feedLoopWDT();
        vTaskDelay(1);
      }
    }
  }
#ifdef K1_TEMPO_SILENCE_FROM_PRODUCER_V1
  if (s_gate != nullptr) {
    for (uint32_t i = 0; i < s_nov_count; i++) {
      const GateRecord& k = s_gate[i];
      K1_EMU_LOG.printf("K,%lu,%u,%u,%u,%u,%u,%.5f,%.1f\n", (unsigned long)(i + 1), (unsigned)k.gate.veto,
                        (unsigned)k.gate.internal_locked, (unsigned)k.gate.producer_silence,
                        (unsigned)k.locked, (unsigned)k.beat_tick, k.confidence, k.bpm);
      if ((i & 0xFF) == 0xFF) {
        feedLoopWDT();
        vTaskDelay(1);
      }
    }
  }
#endif
#ifdef K1_EMU_SPECTRUM_TRACE
  if (s_spec != nullptr) {
    char line[16 + 4 * K1_ONSET_SPECTRUM_BINS + 2];
    const uint32_t n = s_nov_count < kMaxSpectrum ? s_nov_count : kMaxSpectrum;
    for (uint32_t i = 0; i < n; i++) {
      const uint16_t* v = &s_spec[i * K1_ONSET_SPECTRUM_BINS];
      size_t o = 0;
      for (uint32_t b = 0; b < K1_ONSET_SPECTRUM_BINS; b++) {
        line[o++] = hexc[(v[b] >> 12) & 15]; line[o++] = hexc[(v[b] >> 8) & 15];
        line[o++] = hexc[(v[b] >> 4) & 15];  line[o++] = hexc[v[b] & 15];
      }
      line[o] = 0;
      K1_EMU_LOG.printf("P,%lu,%s\n", (unsigned long)(i + 1), line);
      if ((i & 0x3F) == 0x3F) {
        feedLoopWDT();
        vTaskDelay(1);
      }
    }
  }
#endif
#ifdef K1_EMU_TEMPO_PROBE
  if (s_probe != nullptr) {
    for (uint32_t i = 0; i < s_nov_count; i++) {
      const ProbeRecord& p = s_probe[i];
      K1_EMU_LOG.printf("G,%lu,%.6f,%.6f,%u,%u,%lu,%u,%u,%.6f,%lu,%lu,%lu,%lu,%lu,%lu\n",
                        (unsigned long)(i + 1), p.input_trim, p.gdft_trim, (unsigned)p.clip_count,
                        (unsigned)p.sample_count, (unsigned long)p.emit_count, (unsigned)p.silence_internal,
                        (unsigned)p.locked_internal, p.conf_ema, (unsigned long)p.us_silence,
                        (unsigned long)p.us_acf, (unsigned long)p.us_update, (unsigned long)p.us_phase,
                        (unsigned long)p.us_publish, (unsigned long)p.us_emit);
      if ((i & 0xFF) == 0xFF) {
        feedLoopWDT();
        vTaskDelay(1);
      }
    }
  }
#endif
  print_counters(reason, where);
  char dump_arg[] = "1";
  k1_render_trace_dispatch("rtrace_dump", dump_arg);
  for (;;) {
    feedLoopWDT();
    vTaskDelay(10);
  }
}

void run_command(uint32_t hop, const char* text) {
  char buf[kCommandText];
  strncpy(buf, text, sizeof(buf) - 1);
  buf[sizeof(buf) - 1] = '\0';
  const uint32_t rejects_before = s_rejects;
  K1_EMU_LOG.printf("EMU_CMD hop=%lu sample=%lu text=%s\n", (unsigned long)hop,
                    (unsigned long)(hop * kHop), buf);
  parse_command(buf);
  s_commands_run++;
  K1_EMU_LOG.printf("EMU_CMD_DONE hop=%lu rejected=%d photons=%.4f secondary_photons=%.4f "
                    "mode=%u secondary_mode=%u max_current_ma=%lu\n",
                    (unsigned long)hop, s_rejects != rejects_before ? 1 : 0, CONFIG.PHOTONS,
                    SECONDARY_PHOTONS, (unsigned)CONFIG.LIGHTSHOW_MODE,
                    (unsigned)SECONDARY_LIGHTSHOW_MODE, (unsigned long)CONFIG.MAX_CURRENT_MA);
  print_show_state(s_shown_gen, "cmd", hop, false);
}

void stage_next_hop() {
  const uint32_t hop = s_next_hop;
  // Commands apply at the replay boundary before this hop is processed.
  for (uint32_t i = 0; i < s_cmd_count; i++) {
    if (s_cmds[i].hop == hop && s_cmds[i].kind == kCmdScheduled) run_command(hop, s_cmds[i].text);
  }
  if (!s_audio_started) {
    const uint64_t boot_us = (uint64_t)esp_timer_get_time();
    if (s_flags & kFlagDeclaredEpoch) {
      if (s_declared_epoch_us < boot_us) finish("epoch_before_boot", "stage");
      s_epoch_us = s_declared_epoch_us;
    } else {
      s_epoch_us = (s_flags & kFlagBootEpoch) ? boot_us : 0;
    }
    s_audio_started = true;
    K1_EMU_LOG.printf("EMU_EPOCH policy=%s epoch_us=%llu boot_us=%llu pre_audio_shows=%lu\n",
                      epoch_policy(), (unsigned long long)s_epoch_us,
                      (unsigned long long)boot_us, (unsigned long)s_pre_audio_shows);
  }
  memset(s_stage_buf, 0, sizeof(s_stage_buf));
  const uint64_t first = (uint64_t)hop * kHop;
  uint32_t real = 0;
  if (first < s_real_samples) {
    const uint64_t left = s_real_samples - first;
    real = left < kHop ? (uint32_t)left : kHop;
    if (s_from_blob) {
      if (esp_partition_read(s_part, s_pcm_offset + (uint32_t)(first * sizeof(int16_t)),
                             s_stage_buf, real * sizeof(int16_t)) != ESP_OK) {
        finish("read_error", "stage");
      }
    } else {
      memcpy(s_stage_buf, ((const uint8_t*)k1_emu_pcm) + first * sizeof(int16_t),
             real * sizeof(int16_t));
    }
  }
  s_admitted += real;
  s_processed += kHop;
  s_next_hop = hop + 1;
  s_staged = true;
}

// Replay boundary a command line received now applies before: the staged hop
// once staging has happened, otherwise the next hop to stage.
uint32_t current_hop() { return s_staged ? s_next_hop - 1 : s_next_hop; }

// Client gate: the scenario says a client delivers N command lines before this
// hop. Replay would otherwise outrun a host round trip, so the producer holds
// the hop and keeps running the production receive loop (check_serial) itself
// until the parser has taken N lines from USBSerial. The fixture sends nothing
// and decides nothing; the runner types only after seeing EMU_CLIENT_GATE, so
// the hop of application does not depend on host timing. Bounded by stall_ms.
void wait_client_gate(uint32_t hop) {
  uint32_t want = 0;
  for (uint32_t i = 0; i < s_cmd_count; i++) {
    if (s_cmds[i].hop == hop && s_cmds[i].kind == kCmdClient) want++;
  }
  if (want == 0) return;
  const uint32_t before = s_host_commands;
  K1_EMU_LOG.printf("EMU_CLIENT_GATE hop=%lu expect=%lu\n", (unsigned long)hop, (unsigned long)want);
  const int64_t start = esp_timer_get_time();
  while (s_host_commands - before < want) {
    if (esp_timer_get_time() - start > (int64_t)s_stall_ms * 1000) finish("stall", "client_gate");
    check_serial(k1_emu_fixture_time_ms());
    feedLoopWDT();
    vTaskDelay(1);
  }
  K1_EMU_LOG.printf("EMU_CLIENT_GATE_DONE hop=%lu received=%lu\n", (unsigned long)hop,
                    (unsigned long)(s_host_commands - before));
}

// Client transport: wait for the runner's ready line on UART1 so no trace text
// is printed before its TCP bridge is connected (esp-emu drops it otherwise).
void wait_client_ready() {
  Serial1.begin(115200, SERIAL_8N1, kClientTraceRx, kClientTraceTx);
  char line[16] = {};
  size_t n = 0;
  const int64_t start = esp_timer_get_time();
  for (;;) {
    while (Serial1.available()) {
      const char c = (char)Serial1.read();
      if (c == '\r' || c == '\n') {
        line[n] = '\0';
        if (strcmp(line, kClientReady) == 0) {
          Serial1.printf("EMU_CLIENT_READY trace=uart1 tx=%d rx=%d\n", kClientTraceTx, kClientTraceRx);
          return;
        }
        n = 0;
      } else if (n + 1 < sizeof(line)) {
        line[n++] = c;
      }
    }
    if (esp_timer_get_time() - start > (int64_t)s_stall_ms * 1000) {
      return fail_scenario("client_ready_timeout");
    }
    vTaskDelay(1);
  }
}

}  // namespace

#ifdef K1_EMU_UART0
HardwareSerial& k1_emu_log_port(void) { return s_client ? Serial1 : Serial0; }
#endif

void k1_emu_fixture_begin(void) {
  s_cap = (CapRecord*)ps_malloc(sizeof(CapRecord) * kMaxSidecar);
  if (s_cap != nullptr) memset(s_cap, 0, sizeof(CapRecord) * kMaxSidecar);
  load_blob();
  if (s_client) {
#ifdef K1_EMU_UART0
    wait_client_ready();
#else
    fail_scenario("client_transport_needs_uart_trace");
#endif
  }
  if (!s_from_blob) {
    s_valid = true;
    s_real_samples = sizeof(k1_emu_pcm) / sizeof(int16_t);
    s_pad_samples = 0;
  }
  if (s_cap == nullptr) fail_scenario("sidecar_psram");
  if (s_valid && (s_flags & kFlagNoveltyTrace)) {
    s_nov = (NoveltyRecord*)ps_malloc(sizeof(NoveltyRecord) * kMaxNovelty);
    if (s_nov == nullptr) fail_scenario("novelty_psram");
#ifdef K1_TEMPO_SILENCE_FROM_PRODUCER_V1
    s_gate = (GateRecord*)ps_malloc(sizeof(GateRecord) * kMaxNovelty);
    if (s_gate == nullptr) fail_scenario("gate_psram");
#endif
#ifdef K1_EMU_SPECTRUM_TRACE
    s_spec = (uint16_t*)ps_malloc(sizeof(uint16_t) * K1_ONSET_SPECTRUM_BINS * kMaxSpectrum);
    if (s_spec == nullptr) fail_scenario("spectrum_psram");
#endif
#ifdef K1_EMU_TEMPO_PROBE
    s_probe = (ProbeRecord*)ps_malloc(sizeof(ProbeRecord) * kMaxNovelty);
    if (s_probe == nullptr) fail_scenario("probe_psram");
#endif
  }
  if (s_valid) {
    s_total_hops = (s_real_samples + kHop - 1) / kHop + s_pad_samples / kHop;
  }
}

void k1_emu_fixture_poll(void) {
  if (s_finished) {
    for (;;) {
      feedLoopWDT();
      vTaskDelay(10);
    }
  }
  if (!s_started) {
    s_started = true;
#ifdef K1_EMU_UART0
    Serial0.begin(115200);
#endif
    char arm[] = "600,1";
    k1_render_trace_dispatch("rtrace_arm", arm);
    K1_EMU_LOG.printf(
        "EMU_FIXTURE_ARMED run=%s source=%s valid=%d invalid=%s rate=%lu hop=%lu "
        "real_samples=%lu pad_samples=%lu total_hops=%lu capture=%lu..%lu every=%lu "
        "recovery=%d commands=%lu client_commands=%lu transport=%s payload_crc32=%08lx stall_ms=%lu "
        "clock=hop_end_us epoch=%s mode=lockstep rng=xorshift32:%08lx\n",
        s_run_id, s_from_blob ? "blob" : "builtin", s_valid ? 1 : 0,
        s_invalid ? s_invalid : "-", (unsigned long)s_rate, (unsigned long)kHop,
        (unsigned long)s_real_samples, (unsigned long)s_pad_samples,
        (unsigned long)s_total_hops, (unsigned long)s_cap_start, (unsigned long)s_cap_end,
        (unsigned long)s_cap_every, (s_flags & kFlagRecovery) ? 1 : 0,
        (unsigned long)s_sched_count, (unsigned long)s_gate_count, s_client ? "client" : "scheduled",
        (unsigned long)s_payload_crc, (unsigned long)s_stall_ms,
        epoch_policy(), (unsigned long)kEmuRngSeed);
    K1_EMU_LOG.printf("EMU_STATE photons=%.4f secondary_photons=%.4f secondary_mode=%u mode=%u "
                      "max_current_ma=%lu boot_animation=%d\n",
                      CONFIG.PHOTONS, SECONDARY_PHOTONS, (unsigned)SECONDARY_LIGHTSHOW_MODE,
                      (unsigned)CONFIG.LIGHTSHOW_MODE, (unsigned long)CONFIG.MAX_CURRENT_MA,
                      CONFIG.BOOT_ANIMATION ? 1 : 0);
    print_show_state(0, "boot", 0, false);
    if (s_valid && (CONFIG.SAMPLES_PER_CHUNK != kHop || CONFIG.SAMPLE_RATE != s_rate)) {
      fail_scenario("rate_or_hop_differs_from_config");
    }
    if (!s_valid) finish("scenario_invalid", s_invalid ? s_invalid : "-");
  }
  if (s_staged) return;  // acquisition has not taken the staged hop yet
  if (!s_audio_started) {
    // Startup ordering: hold the first hop until the render loop is running.
    const int64_t start = esp_timer_get_time();
    while (!s_render_ready) {
      if (esp_timer_get_time() - start > (int64_t)s_stall_ms * 1000) finish("stall", "startup");
      feedLoopWDT();
      vTaskDelay(1);
    }
  }
  if (s_next_hop < s_total_hops) {
    wait_client_gate(s_next_hop);
    stage_next_hop();
    return;
  }
  // End of declared input: the last publication has been shown (wait_shown).
  finish("eof", "poll");
}

esp_err_t k1_emu_fixture_admit(int16_t* dest, size_t bytes_requested, size_t* bytes_read) {
  if (bytes_read != nullptr) *bytes_read = 0;
  if (dest == nullptr || bytes_read == nullptr || bytes_requested != kHopBytes) {
    return ESP_ERR_INVALID_ARG;
  }
  if (!s_staged) {
    s_unstaged_admits++;
    return ESP_ERR_INVALID_STATE;
  }
  memcpy(dest, s_stage_buf, kHopBytes);
  *bytes_read = kHopBytes;
  s_staged = false;
  s_admits_since_pub++;
  return ESP_OK;
}

void k1_emu_fixture_note_publication(const K1AudioFrame& frame) {
  const uint32_t generation = frame.ap_generation;
  if (s_admits_since_pub == 0) s_pub_without_hop++;
  s_admits_since_pub = 0;
  PubRecord& r = s_ring[generation % kRing];
  r.generation = generation;
  r.admitted = (uint32_t)s_admitted;
  r.processed = (uint32_t)s_processed;
  r.app_us = (uint32_t)k1_emu_fixture_app_us();
  r.meaning = meaning_of(frame, true);
  if (s_nov != nullptr && generation >= 1 && generation <= kMaxNovelty) {
    const K1AudioSnapshot snap = k1_audio_snapshot_read();
    uint32_t crc = esp_crc32_le(0, (const uint8_t*)&snap, sizeof(snap));
    crc = esp_crc32_le(crc, (const uint8_t*)spectrogram, sizeof(spectrogram));
    crc = esp_crc32_le(crc, (const uint8_t*)spectrogram_smooth, sizeof(SQ15x16) * NUM_FREQS);
    crc = esp_crc32_le(crc, (const uint8_t*)chromagram_smooth, sizeof(SQ15x16) * 12);
#ifdef K1_TEMPO_NOVELTY_LINEAR_V1
    s_nov[generation - 1] = {snap.tempo_novelty, snap.vu_level, (uint8_t)(snap.silence ? 1 : 0), crc};
#else
    s_nov[generation - 1] = {snap.novelty, snap.vu_level, (uint8_t)(snap.silence ? 1 : 0), crc};
#endif
#ifdef K1_TEMPO_SILENCE_FROM_PRODUCER_V1
    if (s_gate != nullptr) {
      const K1TempoEvent ev = k1_tempo_read();
      s_gate[generation - 1] = {k1_tempo_gate_read(), ev.bpm, ev.confidence, (uint8_t)(ev.locked ? 1 : 0),
                                (uint8_t)(ev.beat_tick ? 1 : 0)};
    }
#endif
#ifdef K1_EMU_SPECTRUM_TRACE
    if (s_spec != nullptr && generation <= kMaxSpectrum) {
      uint16_t* v = &s_spec[(generation - 1) * K1_ONSET_SPECTRUM_BINS];
      for (uint32_t b = 0; b < K1_ONSET_SPECTRUM_BINS; b++) {
        float x = snap.spectrum[b];
        x = x < 0.0f ? 0.0f : (x > 1.0f ? 1.0f : x);
        v[b] = (uint16_t)(x * 65535.0f + 0.5f);
      }
    }
#endif
#ifdef K1_EMU_TEMPO_PROBE
    if (s_probe != nullptr) {
      const K1TempoDebugSnapshot d = k1_tempo_debug_read();
      ProbeRecord& p = s_probe[generation - 1];
#ifdef K1_LOUD_GUARD_V1
      p.input_trim = k1_loud_input_trim;
      p.gdft_trim = k1_loud_gdft_trim;
      p.clip_count = k1_loud_frame_clip_count;
      p.sample_count = k1_loud_frame_sample_count;
#else
      p.input_trim = -1.0f;
      p.gdft_trim = -1.0f;
      p.clip_count = 0;
      p.sample_count = 0;
#endif
      p.emit_count = d.emit_count;
      p.silence_internal = d.silence_detected ? 1 : 0;
      p.locked_internal = d.v2_locked ? 1 : 0;
      p.conf_ema = d.v2_conf_ema;
      p.us_silence = d.silence_elapsed_us;
      p.us_acf = d.acf_elapsed_us;
      p.us_update = d.update_elapsed_us;
      p.us_phase = d.phase_elapsed_us;
      p.us_publish = d.publish_elapsed_us;
      p.us_emit = d.emit_elapsed_us;
    }
#endif
    if (generation > s_nov_count) s_nov_count = generation;
  }
  s_last_pub_gen = generation;
  s_pub_count++;
}

void k1_emu_fixture_wait_shown(uint32_t generation) {
  const int64_t start = esp_timer_get_time();
  const int64_t deadline_us = (int64_t)s_stall_ms * 1000;
  while (s_shown_gen != generation) {
    if (esp_timer_get_time() - start > deadline_us) finish("stall", "wait_shown");
    feedLoopWDT();
    vTaskDelay(1);
  }
  print_show_state(generation, "shown", generation, true);
}

void k1_emu_fixture_note_render_loop(void) { s_render_ready = true; }

void k1_emu_fixture_note_consumed(const K1AudioFrame& frame) {
  s_last_consumed = meaning_of(frame, false);
  s_consumed_gen = frame.ap_generation;
  s_consumed_notes++;
}

void k1_emu_fixture_note_shown(uint32_t generation) {
  if (generation == 0) return;
  s_shown_notes++;
  s_shown_gen = generation;
}

uint32_t k1_emu_fixture_shown(void) { return s_shown_gen; }

bool k1_emu_fixture_capture_wanted(void) {
  const uint32_t g = s_consumed_gen;
  if (g == 0) return false;
  const PubRecord& r = s_ring[g % kRing];
  if (r.generation != g || r.processed < kHop) return false;
  const uint32_t hop = r.processed / kHop - 1;
  if (hop < s_cap_start || hop >= s_cap_end) return false;
  return ((hop - s_cap_start) % s_cap_every) == 0;
}

void k1_emu_fixture_on_render_store(uint32_t capture_index) {
  if (capture_index >= kMaxSidecar || s_cap == nullptr) return;
  const uint32_t g = s_consumed_gen;
  const PubRecord& r = s_ring[g % kRing];
  const bool known = (r.generation == g);
  CapRecord& c = s_cap[capture_index];
  c.generation = g;
  c.admitted = known ? r.admitted : 0xFFFFFFFFu;
  c.processed = known ? r.processed : 0xFFFFFFFFu;
  c.app_us = known ? r.app_us : 0xFFFFFFFFu;
  c.limit_scale = 255;
  c.power_mw = s_power_mw;
  c.consumed = s_last_consumed;
  c.producer = known ? r.meaning : Meaning{};
  {
    // Render-thread view of shared state that both edges' injection uses.
    const float fps = LED_FPS, master = MASTER_BRIGHTNESS, silent = silent_scale, peak = waveform_peak_scaled;
    const int32_t hue = hue_position.getInternal(), mix = hue_shifting_mix.getInternal(),
                  vu = audio_vu_level.getInternal();
    memcpy(&c.render_state[0], &hue, 4);
    memcpy(&c.render_state[1], &mix, 4);
    memcpy(&c.render_state[2], &master, 4);
    memcpy(&c.render_state[3], &silent, 4);
    memcpy(&c.render_state[4], &fps, 4);
    memcpy(&c.render_state[5], &vu, 4);
    memcpy(&c.render_state[6], &peak, 4);
  }
  s_pending_lim_idx = (int32_t)capture_index;
  s_captured = capture_index + 1;
}

void k1_emu_fixture_note_submission(void) {
  if (s_consumed_gen == 0) s_pre_audio_shows++;  // startup frames before the first hop
  if (s_pending_lim_idx < 0) return;
  const uint8_t target = FastLED.getBrightness();
  // FastLED's own estimate over every registered controller, as show() would use.
  if (s_cap != nullptr) {
    s_cap[s_pending_lim_idx].limit_scale =
        s_power_mw != 0 ? calculate_max_brightness_for_power_mW(target, s_power_mw) : target;
  }
  s_pending_lim_idx = -1;
}

void k1_emu_fixture_note_power_limit_mw(uint32_t milliwatts) {
  s_power_mw = milliwatts;
  K1_EMU_LOG.printf("EMU_POWER_LIMIT installed_mw=%lu\n", (unsigned long)milliwatts);
}

void k1_emu_fixture_note_save(const char* kind, bool ok) {
  s_saves++;
  K1_EMU_LOG.printf("EMU_SAVE kind=%s ok=%d hop=%lu\n", kind, ok ? 1 : 0,
                    (unsigned long)s_next_hop);
}

void k1_emu_fixture_note_reject(const char* command_type) {
  s_rejects++;
  K1_EMU_LOG.printf("EMU_REJECT %s\n", command_type);
}

void k1_emu_fixture_host_command_begin(const char* text) {
  // Printed before parsing: the parser tokenises the buffer in place.
  s_in_host_command = true;
  s_host_rejects_before = s_rejects;
  s_host_hop = current_hop();
  K1_EMU_LOG.printf("EMU_HCMD hop=%lu sample=%lu text=%s\n", (unsigned long)s_host_hop,
                    (unsigned long)(s_host_hop * kHop), text);
}

void k1_emu_fixture_host_command_end(void) {
  if (!s_in_host_command) return;
  s_in_host_command = false;
  s_host_commands++;
  K1_EMU_LOG.printf("EMU_HCMD_DONE hop=%lu rejected=%d photons=%.4f secondary_photons=%.4f "
                    "mode=%u secondary_mode=%u max_current_ma=%lu\n",
                    (unsigned long)s_host_hop, s_rejects != s_host_rejects_before ? 1 : 0, CONFIG.PHOTONS,
                    SECONDARY_PHOTONS, (unsigned)CONFIG.LIGHTSHOW_MODE,
                    (unsigned)SECONDARY_LIGHTSHOW_MODE, (unsigned long)CONFIG.MAX_CURRENT_MA);
  print_show_state(s_shown_gen, "hcmd", s_host_hop, false);
}

void k1_emu_fixture_write_sidecar(uint32_t capture_index) {
  if (capture_index >= kMaxSidecar || s_cap == nullptr) return;
  // V: producer meaning for this frame's generation, then what the render
  // thread consumed. P is looked up by generation in the publication ring only
  // while it is still resident; the dump runs after the run, so P comes from
  // the per-capture copy taken at store time.
  const Meaning& c = s_cap[capture_index].consumed;
  const Meaning& p = s_cap[capture_index].producer;
  K1_EMU_LOG.printf("V,%lu,%lu,%lu,%lu,%.4f,%.3f,%.4f,%.4f,%d,%d,%lu,%lu,%lu,%.4f,%.3f,%.4f,%.4f,%d,%d\n",
                    (unsigned long)capture_index, (unsigned long)p.generation, (unsigned long)p.onset_seq,
                    (unsigned long)p.beat_seq, p.onset_strength, p.bpm, p.phase01, p.confidence,
                    p.locked ? 1 : 0, p.beat_tick ? 1 : 0, (unsigned long)c.generation,
                    (unsigned long)c.onset_seq, (unsigned long)c.beat_seq, c.onset_strength, c.bpm,
                    c.phase01, c.confidence, c.locked ? 1 : 0, c.beat_tick ? 1 : 0);
  const CapRecord& s = s_cap[capture_index];
  K1_EMU_LOG.printf("R,%lu,%08lx,%08lx,%08lx,%08lx,%08lx,%08lx,%08lx\n", (unsigned long)capture_index,
                    (unsigned long)s.render_state[0], (unsigned long)s.render_state[1],
                    (unsigned long)s.render_state[2], (unsigned long)s.render_state[3],
                    (unsigned long)s.render_state[4], (unsigned long)s.render_state[5],
                    (unsigned long)s.render_state[6]);
  K1_EMU_LOG.printf("S,%lu,%lu,%lu,%lu,%lu,%u,%lu\n", (unsigned long)capture_index,
                    (unsigned long)s.generation, (unsigned long)s.admitted,
                    (unsigned long)s.processed, (unsigned long)s.app_us,
                    (unsigned)s.limit_scale, (unsigned long)s.power_mw);
}

extern "C" uint64_t k1_emu_fixture_app_us(void) {
  if (!s_audio_started) {
    return monotonic_pre_audio() ? (uint64_t)esp_timer_get_time() : 0;
  }
  return s_epoch_us + (s_processed * 1000000ull) / (uint64_t)s_rate;
}

extern "C" uint32_t k1_emu_fixture_random_u32(void) {
  uint32_t x = s_rng;
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  s_rng = x;
  s_rng_draws++;
  return x;
}

extern "C" uint32_t k1_emu_fixture_time_us(void) { return (uint32_t)k1_emu_fixture_app_us(); }

extern "C" uint32_t k1_emu_fixture_time_ms(void) {
  return (uint32_t)(k1_emu_fixture_app_us() / 1000ull);
}

#endif
