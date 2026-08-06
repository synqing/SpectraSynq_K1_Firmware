#ifndef _KNOB_H
#define _KNOB_H

#ifdef __cplusplus
extern "C"
{
#endif

#include "lvgl.h"
#include "bidi_switch_knob.h"

void knob_gui(void);
void knob_tick(void);
void knob_cb(lv_event_t *e);
void knob_change(knob_event_t k, int cont);
void app_status_set(const char *text);
void led_status_set(const char *text);
void battery_status_set(const char *text);
void haptic_status_set(const char *text);
void gate_status_set(const char *text);

#ifdef __cplusplus
}
#endif

#endif
