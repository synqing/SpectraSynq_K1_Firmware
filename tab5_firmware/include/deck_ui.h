#pragma once

#include <lvgl.h>
#include <stdint.h>

/**
 * Operator MAIN UI — Deck16 authority consumer (not Precision Bay).
 * Display: deck_state_display_* (pending preferred when pending_active).
 * Mutations: deck_input → pending only; confirmed only via deck_state_rx.
 * Commands gated until deck_state_rx_armed(); LINK chrome follows link phase.
 * Legacy OSC snapshot/DSP APIs kept as soft stubs for main.cpp compatibility.
 */

struct DeckSnapshot {
  int    effect;
  float  brightness;
  float  p1;
  float  p2;
  float  p6;
  float  bpm;
  char   key[8];
};

void Deck_UI_Init(lv_display_t* disp);
void Deck_UI_Tick(void);

/** LINK lamp (+ optional RSSI when NimBLE reports connection RSSI). */
void Deck_UI_UpdateLinkStatus(bool linked);

/** Legacy alias — maps hostConnected → LINK. */
void Deck_UI_UpdateNetworkStatus(const char* ip, int port, bool hostConnected,
                                 int latencyMs, int deltaTimeMs);

void Deck_UI_UpdateSnapshot(const DeckSnapshot* snap);
void Deck_UI_UpdateFooterStats(int fps, uint32_t uptime_seconds);
void Deck_UI_ShowWaitingScreen(bool show, const char* dotsText = nullptr);

void Deck_UI_UpdatePPM(float left_db, float right_db);
void Deck_UI_UpdateSpectrum(const float* spectrum_data);
void Deck_UI_UpdateDSPParam(int param_index, float value);

/** Native-gate / sim only — open or close a soft-key sheet without a touch event. */
void Deck_UI_OpenSheetForGate(int sheet_id);
void Deck_UI_CloseSheetForGate(void);

const char* Deck_GetNextKey(const char* currentKey);
const char* Deck_GetPrevKey(const char* currentKey);
