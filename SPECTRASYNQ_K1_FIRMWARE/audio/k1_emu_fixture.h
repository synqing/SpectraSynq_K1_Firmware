#pragma once
// Disabled unless the build defines K1_EMU_FIXTURE. Normal images do not call these.
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef K1_EMU_FIXTURE

#ifdef K1_EMU_UART0
#define K1_EMU_LOG Serial0
#else
#define K1_EMU_LOG USBSerial
#endif

// Copy one complete mono IM69D hop. A short tail returns an error and bytes_read 0
// so the existing freeze-guard zero-fill runs. It does not repeat an old hop.
esp_err_t k1_emu_fixture_admit(int16_t* dest, size_t bytes_requested, size_t* bytes_read);

// First call arms the existing render trace (every frame, stim off) and prints
// recovered show state. Later calls issue scheduled production commands and,
// after the declared PCM interval has been published, the existing rtrace dump.
void k1_emu_fixture_poll(void);

// Record the generation the producer is about to publish, with the sample
// watermark of the hops already admitted for that publication.
void k1_emu_fixture_note_publication(uint32_t generation);

// Record the generation the render thread just acquired for this frame.
// Zero means this frame did not consume a published audio frame.
void k1_emu_fixture_note_consumed(uint32_t generation);

// The render thread has finished showing this generation. The producer waits
// for it so the fixture stores one frame per hop on the emulator and on silicon.
void k1_emu_fixture_note_shown(uint32_t generation);
uint32_t k1_emu_fixture_shown(void);

// Hop clock. A command's print time must not move the beat or the gain.
// C linkage so a fixture build can redirect Arduino millis/micros here.
#ifdef __cplusplus
extern "C" {
#endif
uint32_t k1_emu_fixture_time_ms(void);
uint32_t k1_emu_fixture_time_us(void);
#ifdef __cplusplus
}
#endif

// Called from the existing dual-edge store with the renderer's acquired frame.
void k1_emu_fixture_on_render_store(uint32_t capture_index);

void k1_emu_fixture_write_sidecar(uint32_t capture_index);

#endif
