#pragma once

#include <stdint.h>
#include <stdbool.h>

#include "k1_prsm.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Serial receive demultiplexer: decides, byte by byte, whether input is a
 * prepared-show frame, a typed ':' command, a single-key hotkey, or nothing.
 * check_serial() feeds every received byte through k1_prsm_rx_push() and acts
 * only on the event it returns. Plain C, no Arduino: the host tests drive this
 * same file.
 *
 * Two modes.
 *
 * INTERACTIVE (boot default). Text behaves as it always has: ':' starts a
 * command line, CR/LF ends it, other printable keys are hotkeys.
 *
 * BINARY SESSION. Entered, and the triggering byte dropped, when any of these
 * is seen outside a command line:
 *   - a complete frame, accepted or rejected (bad version, length or CRC);
 *   - a frame header ('P','R' or more) broken by a byte that is not 'P';
 *   - a byte that is not text (anything but TAB, CR, LF and 0x20..0x7E).
 * It is also entered when a pending command line receives a non-text byte;
 * that line is discarded, never executed.
 *
 * OVER-LONG TEXT LINE (Stage F, 10 Nov 2026). A ':' line longer than any
 * command is discarded through its CR/LF: nothing in it executes, none of its
 * bytes become hotkeys, and the receiver stays INTERACTIVE so the next line
 * works. A non-text byte inside it still opens a binary session.
 * In a binary session only frames are acted on. Every other byte is dropped:
 * no hotkey, no ':' command.
 *
 * EXIT. The session ends only when the exact line ":prsm_exit" + CR or LF
 * arrives with its ':' at least K1_PRSM_RX_EXIT_GUARD_MS after the previous
 * byte. Reset also returns to INTERACTIVE.
 *
 * A part-received frame followed by the same pause is dropped.
 *
 * A command line left pending for K1_PRSM_RX_CMD_IDLE_MS is discarded, so a
 * later newline cannot run a stale half-typed command. */

#define K1_PRSM_RX_CMD_MAX 128
#define K1_PRSM_RX_EXIT_GUARD_MS 200u
#define K1_PRSM_RX_CMD_IDLE_MS 5000u
#define K1_PRSM_RX_EXIT_TEXT ":prsm_exit"

typedef enum {
  K1_PRSM_RX_NONE = 0,       /* nothing for the caller to do */
  K1_PRSM_RX_FRAME,          /* validated frame in ev->frame */
  K1_PRSM_RX_HOTKEY,         /* interactive key in ev->byte */
  K1_PRSM_RX_COMMAND,        /* complete command line in ev->line */
  K1_PRSM_RX_SESSION_EXIT,   /* binary session ended by the exit line */
  K1_PRSM_RX_LOCKED_NOTICE   /* a text line was ignored because a session is open */
} k1_prsm_rx_kind_t;

typedef struct {
  k1_prsm_rx_kind_t kind;
  uint8_t byte;
  k1_prsm_frame_t frame;
  char *line; /* NUL-terminated, valid until the next push */
} k1_prsm_rx_event_t;

typedef struct {
  uint32_t sessions;       /* binary sessions entered */
  uint32_t exits;          /* binary sessions ended by the exit line */
  uint32_t frames_ok;
  uint32_t frames_bad;     /* candidate frames rejected by the scanner */
  uint32_t dropped_bytes;  /* non-frame bytes dropped while in a session, or entering one */
  uint32_t cmd_aborts;     /* pending command lines discarded unexecuted */
} k1_prsm_rx_counters_t;

typedef struct {
  k1_prsm_scanner_t scanner;
  bool binary_session;
  bool command_mode;
  bool discard_line;   /* dropping an over-long text line up to its CR/LF */
  bool have_rx;
  uint8_t exit_match;
  uint8_t cmd_len;
  uint32_t last_rx_ms;
  uint32_t last_notice_ms;
  bool have_notice;
  char cmd[K1_PRSM_RX_CMD_MAX];
  k1_prsm_rx_counters_t n;
} k1_prsm_rx_t;

void k1_prsm_rx_reset(k1_prsm_rx_t *rx);
void k1_prsm_rx_push(k1_prsm_rx_t *rx, uint8_t byte, uint32_t now_ms,
                     k1_prsm_rx_event_t *ev);
/* Call once when the receive queue has run empty: releases a frame the scanner
 * was holding for its next byte (see k1_prsm_scanner_flush). */
void k1_prsm_rx_burst_end(k1_prsm_rx_t *rx, k1_prsm_rx_event_t *ev);

#ifdef __cplusplus
}
#endif
