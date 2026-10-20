#include "k1_emu_fixture.h"

#ifdef K1_EMU_FIXTURE

#include <Arduino.h>
#include <string.h>

#include "k1_audio_frame.h"
#include "globals.h"

extern void parse_command(char* command_buf);
bool k1_render_trace_dispatch(const char* command_type, char* command_data);

#include "k1_emu_pcm.inc"

static const size_t kHopBytes = 192;
static const uint32_t kHops = sizeof(k1_emu_pcm) / kHopBytes;
static uint32_t s_hop = 0;
static uint32_t s_admitted_samples = 0;
static bool s_pcm_done = false;
static bool s_dump_requested = false;
static int s_settle = 0;
static bool s_started = false;

static const uint16_t kMaxSidecar = 2000;
static uint32_t s_render_generation[kMaxSidecar];
static uint32_t s_render_samples[kMaxSidecar];
static uint32_t s_pub_generation = 0;
static uint32_t s_pub_samples = 0;
static uint32_t s_consumed_generation = 0;
static uint32_t s_consumed_notes = 0;
static uint32_t s_consumed_nonzero = 0;
static volatile uint32_t s_shown_generation = 0;

// Patched in the merged image before a scenario run. '0' is the untouched default.
static const char k1_emu_plan_tag[] __attribute__((used)) = "K1EMUP0!";

static char plan_code() {
  // Volatile so the image byte, not a folded constant, selects the scenario.
  volatile const char* tag = k1_emu_plan_tag;
  return tag[6];
}

static void run_command(const char* text) {
  char buf[64];
  strncpy(buf, text, sizeof(buf) - 1);
  buf[sizeof(buf) - 1] = '\0';
  K1_EMU_LOG.printf("EMU_CMD %s\n", buf);
  parse_command(buf);
  // Read the variables the production handler writes. This is not a second parser.
  K1_EMU_LOG.printf("EMU_READBACK photons=%.4f secondary_photons=%.4f\n",
                    CONFIG.PHOTONS, SECONDARY_PHOTONS);
}

esp_err_t k1_emu_fixture_admit(int16_t* dest, size_t bytes_requested, size_t* bytes_read) {
  if (bytes_read != nullptr) *bytes_read = 0;
  if (dest == nullptr || bytes_read == nullptr || bytes_requested != kHopBytes) {
    return ESP_ERR_INVALID_ARG;
  }
  if (s_pcm_done || s_hop >= kHops) {
    s_pcm_done = true;
    return ESP_ERR_INVALID_SIZE;
  }
  const size_t off = (size_t)s_hop * kHopBytes;
  memcpy(dest, ((const uint8_t*)k1_emu_pcm) + off, kHopBytes);
  *bytes_read = kHopBytes;
  s_admitted_samples += (uint32_t)(kHopBytes / sizeof(int16_t));
  const char plan = plan_code();
  if (plan == '1' && s_hop == 40) run_command("photons=0.25");
  if (plan == '2' && s_hop == 40) run_command("secondary_photons=0.15");
  if (plan == '3' && s_hop == 10) {
    run_command("photons=0.40");
    run_command("secondary_photons=0.30");
  }
  if (plan == '4' && s_hop == 30) run_command("photons=not-a-number");
  s_hop++;
  if (s_hop >= kHops) s_pcm_done = true;
  return ESP_OK;
}

void k1_emu_fixture_note_publication(uint32_t generation) {
  s_pub_generation = generation;
  s_pub_samples = s_admitted_samples;
}

void k1_emu_fixture_note_consumed(uint32_t generation) {
  s_consumed_generation = generation;
  s_consumed_notes++;
  if (generation != 0) {
    s_consumed_nonzero++;
  }
}

void k1_emu_fixture_note_shown(uint32_t generation) {
  s_shown_generation = generation;
}

uint32_t k1_emu_fixture_shown(void) {
  return s_shown_generation;
}

void k1_emu_fixture_on_render_store(uint32_t capture_index) {
  if (capture_index >= kMaxSidecar) return;
  // The render thread records the acquired generation before it draws.
  // The VP-frame copy is the same value when acquire succeeded.
  const uint32_t consumed = s_consumed_generation;
  s_render_generation[capture_index] = consumed != 0 ? consumed : k1_vp_audio_frame().ap_generation;
  s_render_samples[capture_index] = s_pub_samples;
}

void k1_emu_fixture_write_sidecar(uint32_t capture_index) {
  if (capture_index >= kMaxSidecar) return;
  K1_EMU_LOG.printf("M,%lu,%lu,%lu\n",
                    (unsigned long)capture_index,
                    (unsigned long)s_render_generation[capture_index],
                    (unsigned long)s_render_samples[capture_index]);
}

void k1_emu_fixture_poll(void) {
  if (!s_started) {
    s_started = true;
#ifdef K1_EMU_UART0
    Serial0.begin(115200);
#endif
    char arm[] = "60,1";
    k1_render_trace_dispatch("rtrace_arm", arm);
    K1_EMU_LOG.write(k1_emu_plan_tag, 8);
    K1_EMU_LOG.printf("\nEMU_FIXTURE_ARMED every=1 stim=0 plan=%c hops=%lu\n",
                      plan_code(), (unsigned long)kHops);
    K1_EMU_LOG.printf("EMU_STATE photons=%.4f secondary_photons=%.4f secondary_mode=%u mode=%u\n",
                      CONFIG.PHOTONS, SECONDARY_PHOTONS, (unsigned)SECONDARY_LIGHTSHOW_MODE,
                      (unsigned)CONFIG.LIGHTSHOW_MODE);
  }
  if (plan_code() == '3' && s_hop == 20 && !s_dump_requested) {
    run_command("save_show");
  }
  if (!s_pcm_done || s_dump_requested) return;
  if (++s_settle < 8) return;
  s_dump_requested = true;
  char dump_arg[] = "1";
  k1_render_trace_dispatch("rtrace_dump", dump_arg);
  K1_EMU_LOG.println("EMU_FIXTURE_DUMP_REQUESTED");
  K1_EMU_LOG.printf("EMU_PCM admitted_samples=%lu hops=%lu\n",
                    (unsigned long)s_admitted_samples, (unsigned long)s_hop);
  K1_EMU_LOG.printf("EMU_CONSUMED notes=%lu nonzero=%lu last=%lu published=%lu\n",
                    (unsigned long)s_consumed_notes, (unsigned long)s_consumed_nonzero,
                    (unsigned long)s_consumed_generation, (unsigned long)s_pub_generation);
}

#endif
