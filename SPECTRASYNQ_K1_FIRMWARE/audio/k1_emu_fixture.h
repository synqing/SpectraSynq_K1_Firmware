#pragma once
// Disabled unless the build defines K1_EMU_FIXTURE. Normal images do not call these.
//
// The emulator replay reads one run-owned scenario blob from the unused ota_1
// partition of the run's own flash copy: run identity, PCM, window and the
// scheduled production command strings. The application image is never patched.
// tools/esp_emulator/README.md is the host-side contract for this blob and for
// every EMU_* line printed here.
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef K1_EMU_FIXTURE

#ifdef K1_EMU_UART0
// The fixture trace port. UART0 for scheduled runs (esp-emu --console uart0).
// A client-transport run (scenario flag) moves it to UART1: the product's own
// USBSerial then carries an external client on --console usb-jtag, which
// discards UART0 output, and esp-emu 0.49.0 disconnects stdio entirely while
// --uart-tcp is active, so the trace leaves on --uart1-tcp instead.
class HardwareSerial;
HardwareSerial& k1_emu_log_port(void);
#define K1_EMU_LOG (k1_emu_log_port())
#else
#define K1_EMU_LOG USBSerial
#endif

// Read and verify the scenario blob. Called once from setup() before the render
// task starts. Without a valid blob the fixture uses the compiled smoke PCM
// with no commands and says so (source=builtin).
void k1_emu_fixture_begin(void);

// Producer-side poll at the top of loop(). Stages the next hop (hop-end
// application time), runs the production commands scheduled for that hop, and
// at end of input waits for the last show before requesting the trace dump.
void k1_emu_fixture_poll(void);

// Copy the staged hop into the production acquisition buffer. Real samples and
// declared zero padding are counted separately.
esp_err_t k1_emu_fixture_admit(int16_t* dest, size_t bytes_requested, size_t* bytes_read);

struct K1AudioFrame;

// Record the frame the producer is about to publish: its generation, the sample
// watermark and application time of the hops processed for it, and the audio
// meaning it carries (onset/beat sequence and the tempo state at publication).
void k1_emu_fixture_note_publication(const K1AudioFrame& frame);

// Deterministic one-show-per-publication mode: the producer waits until the
// render thread has shown this generation. A real-time deadline turns a stall
// into a reported failure with the last positions and the partial capture.
void k1_emu_fixture_wait_shown(uint32_t generation);

// Render thread: entered its frame loop (product startup animation finished).
// The producer does not stage the first hop before this, so startup always runs
// entirely on the pre-audio clock and the epoch hand-off is deterministic.
void k1_emu_fixture_note_render_loop(void);

// Render thread: the generation acquired for this frame (0 = none) and the
// generation just shown.
void k1_emu_fixture_note_consumed(const K1AudioFrame& frame);
void k1_emu_fixture_note_shown(uint32_t generation);
uint32_t k1_emu_fixture_shown(void);

// Render trace hooks. capture_wanted() selects frames by the consumed hop and
// the scenario window; on_render_store/write_sidecar carry its source identity.
bool k1_emu_fixture_capture_wanted(void);
void k1_emu_fixture_on_render_store(uint32_t capture_index);
void k1_emu_fixture_write_sidecar(uint32_t capture_index);

// Submission suppressed by K1_EMU_SKIP_EMIT. Records the brightness scale the
// installed FastLED power limit would apply to this frame (255 when none is
// installed). The production install sites report their budget here.
void k1_emu_fixture_note_submission(void);
void k1_emu_fixture_note_power_limit_mw(uint32_t milliwatts);

// A configuration or show-state save reached flash.
void k1_emu_fixture_note_save(const char* kind, bool ok);

// The production parser rejected a command (serial_tx reject path).
void k1_emu_fixture_note_reject(const char* command_type);

// The production receive loop (check_serial) is about to parse, and has parsed,
// one command line that arrived on USBSerial from an external client. Reports
// the text, the replay hop it applies before, the parser outcome and the
// resulting show state. State changes stay with the production parser.
void k1_emu_fixture_host_command_begin(const char* text);
void k1_emu_fixture_host_command_end(void);

// Application clock. Before the first hop it stays at the epoch (0); afterwards
// it is processed_samples * 1e6 / sample_rate with a 64-bit intermediate.
// C linkage so a fixture build can redirect Arduino millis/micros here.
#ifdef __cplusplus
extern "C" {
#endif
uint32_t k1_emu_fixture_time_ms(void);
uint32_t k1_emu_fixture_time_us(void);
uint64_t k1_emu_fixture_app_us(void);
// Declared deterministic replacement for esp_random() in product randomness
// (random_float): xorshift32, seed kEmuRngSeed, reported as rng= in EMU_FIXTURE_ARMED.
uint32_t k1_emu_fixture_random_u32(void);
#ifdef __cplusplus
}
#endif

#endif
