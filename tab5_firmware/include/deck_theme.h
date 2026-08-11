#pragma once

/**
 * Operator phosphor theme — matches tab5-ui-v6-quintet.html CSS vars.
 * Hierarchy by colour tier (amber-hi / amber / amber-dim); no runtime glow.
 */

#define DECK_COLOR_BG           0x0B0906u  /* warm near-black */
#define DECK_COLOR_CRT          0x120D04u  /* elevated CRT zone fill */
#define DECK_COLOR_SHEET        0x17140Du  /* sheet surface @ ~92% opa */
#define DECK_COLOR_KEY_IDLE     0x14110Cu
#define DECK_COLOR_KEY_PRESS    0x241E12u
#define DECK_COLOR_BORDER       0x3A2E18u
#define DECK_COLOR_TRACK        0x1A140Au
#define DECK_COLOR_FILL_LO      0x8A5E1Cu
#define DECK_COLOR_FILL_HI      0xFFB84Du
#define DECK_COLOR_THUMB        0xFFE2B8u
#define DECK_COLOR_AMBER_HI     0xFFE2B8u
#define DECK_COLOR_AMBER        0xFFB84Du
#define DECK_COLOR_AMBER_DIM    0x7A5A26u
#define DECK_COLOR_LAMP_OFF     0x7A5A26u  /* legacy hue; OFF chrome uses outline tokens */
#define DECK_COLOR_LAMP_ON      0x1AFF66u  /* vivid green (~+25% chroma vs prior 0x3DDB7A) */
/* Soft-key lamp: OFF = unlit outline; ON = solid (MERGE 2026-08-11). */
#define DECK_COLOR_LAMP_OFF_FILL    0x0A0907u
#define DECK_COLOR_LAMP_OFF_BORDER  0x5A5040u
/* Sheet bool ON/OFF: selected fill vs idle outline (not hue/label-only). */
#define DECK_COLOR_BOOL_IDLE_FILL     0x0A0907u
#define DECK_COLOR_BOOL_IDLE_BORDER   0x5A5040u
#define DECK_COLOR_BOOL_SEL_FILL      0x5C4520u  /* brighter selected fill for glance Δ≥0.12 */
#define DECK_COLOR_BOOL_SEL_BORDER    0xFFB84Du
#define DECK_COLOR_BOOL_SEL_LABEL     0xFFF0C8u
#define DECK_COLOR_BOOL_PENDING_BORDER 0xFFB84Du
#define DECK_COLOR_RED          0xFF4D5Eu
#define DECK_COLOR_SCRIM        0x000000u
