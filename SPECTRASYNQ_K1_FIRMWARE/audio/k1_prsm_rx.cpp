#include "k1_prsm_rx.h"

#include <string.h>

static const char kExitText[] = K1_PRSM_RX_EXIT_TEXT;
static const uint8_t kExitLen = (uint8_t)(sizeof(kExitText) - 1);

void k1_prsm_rx_reset(k1_prsm_rx_t *rx) {
  if (!rx) return;
  memset(rx, 0, sizeof(*rx));
}

static bool is_text(uint8_t b) {
  return b == '\t' || (b >= 0x20 && b <= 0x7E);
}

static void enter_session(k1_prsm_rx_t *rx) {
  if (!rx->binary_session) {
    rx->binary_session = true;
    rx->n.sessions++;
  }
  rx->exit_match = 0;
}

static void abort_command(k1_prsm_rx_t *rx) {
  rx->command_mode = false;
  rx->cmd_len = 0;
  rx->cmd[0] = '\0';
  rx->n.cmd_aborts++;
}

/* A byte that is not part of a frame, while a session is open. Only the exit
 * line gets through; everything else is counted and dropped. */
static void session_text_byte(k1_prsm_rx_t *rx, uint8_t byte, uint32_t idle_ms,
                              uint32_t now_ms, k1_prsm_rx_event_t *ev) {
  if (rx->exit_match == 0) {
    if (byte == ':' && idle_ms >= K1_PRSM_RX_EXIT_GUARD_MS) {
      rx->exit_match = 1;
      return;
    }
    rx->n.dropped_bytes++;
    return;
  }
  if (rx->exit_match < kExitLen) {
    if (byte == (uint8_t)kExitText[rx->exit_match]) {
      rx->exit_match++;
      return;
    }
  } else if (byte == '\r' || byte == '\n') {
    rx->binary_session = false;
    rx->exit_match = 0;
    k1_prsm_scanner_reset(&rx->scanner);
    rx->n.exits++;
    ev->kind = K1_PRSM_RX_SESSION_EXIT;
    return;
  }
  /* A line began after the guard time but is not the exit line: someone is
   * typing at a locked port. Say so, at most once every two seconds. */
  rx->n.dropped_bytes += (uint32_t)rx->exit_match + 1u;
  rx->exit_match = 0;
  if (!rx->have_notice || (uint32_t)(now_ms - rx->last_notice_ms) >= 2000u) {
    rx->have_notice = true;
    rx->last_notice_ms = now_ms;
    ev->kind = K1_PRSM_RX_LOCKED_NOTICE;
  }
}

void k1_prsm_rx_push(k1_prsm_rx_t *rx, uint8_t byte, uint32_t now_ms,
                     k1_prsm_rx_event_t *ev) {
  if (!rx || !ev) return;
  ev->kind = K1_PRSM_RX_NONE;
  ev->byte = byte;
  ev->line = rx->cmd;

  const uint32_t idle_ms = rx->have_rx ? (uint32_t)(now_ms - rx->last_rx_ms) : 0xFFFFFFFFu;
  rx->have_rx = true;
  rx->last_rx_ms = now_ms;

  if (rx->command_mode && idle_ms > K1_PRSM_RX_CMD_IDLE_MS) {
    abort_command(rx); /* stale half-typed line; treat this byte as fresh input */
  }

  if (rx->discard_line) {
    if (idle_ms > K1_PRSM_RX_CMD_IDLE_MS) {
      rx->discard_line = false; /* stale; treat this byte as fresh input */
    } else if (byte == '\r' || byte == '\n') {
      rx->discard_line = false; /* end of the discarded line: interactive again */
      return;
    } else if (is_text(byte)) {
      rx->n.dropped_bytes++;    /* never a hotkey, never part of a command */
      return;
    } else {
      rx->discard_line = false; /* binary inside the line: as in a command line */
      enter_session(rx);
      rx->n.dropped_bytes++;
      return;
    }
  }

  if (rx->command_mode) {
    if (byte == '\r' || byte == '\n') {
      rx->command_mode = false;
      if (rx->cmd_len > 0) {
        rx->cmd[rx->cmd_len] = '\0';
        rx->cmd_len = 0;
        ev->kind = K1_PRSM_RX_COMMAND;
      }
      return;
    }
    if (!is_text(byte)) {
      /* Binary in a command line. */
      abort_command(rx);
      enter_session(rx);
      rx->n.dropped_bytes++;
      return;
    }
    if (rx->cmd_len >= K1_PRSM_RX_CMD_MAX - 1) {
      /* A text line longer than any command: drop it through its CR/LF. */
      abort_command(rx);
      rx->discard_line = true;
      rx->n.dropped_bytes++;
      return;
    }
    rx->cmd[rx->cmd_len++] = (char)byte;
    return;
  }

  /* A frame is one burst. A part-frame followed by a pause is a frame cut
   * short at the end of a stream; drop it so it cannot swallow what follows. */
  if ((rx->scanner.fill > 0 || rx->scanner.pending) && idle_ms >= K1_PRSM_RX_EXIT_GUARD_MS) {
    if (rx->scanner.fill >= 4 || rx->scanner.pending) rx->n.frames_bad++;
    k1_prsm_scanner_reset(&rx->scanner);
  }

  const uint8_t fill_before = rx->scanner.pending ? 0 : rx->scanner.fill;
  const k1_prsm_scan_result_t scan =
      k1_prsm_scanner_push(&rx->scanner, byte, &ev->frame);

  if (scan == K1_PRSM_SCAN_FRAME_OK) {
    enter_session(rx);
    rx->n.frames_ok++;
    ev->kind = K1_PRSM_RX_FRAME;
    return;
  }
  if (scan == K1_PRSM_SCAN_FRAME_BAD) {
    enter_session(rx);
    rx->n.frames_bad++;
    return;
  }
  if (scan == K1_PRSM_SCAN_CONSUMED) {
    rx->exit_match = 0;
    return;
  }

  /* Not part of a frame. */
  if (rx->binary_session) {
    session_text_byte(rx, byte, idle_ms, now_ms, ev);
    return;
  }
  if (fill_before >= 2) {
    /* 'P','R'[,'S'] then something else: a damaged frame header. */
    enter_session(rx);
    rx->n.dropped_bytes++;
    return;
  }
  if (byte == ':') {
    rx->command_mode = true;
    rx->cmd_len = 0;
    rx->cmd[0] = '\0';
    return;
  }
  if (byte == '\r' || byte == '\n') return;
  if (!is_text(byte)) {
    enter_session(rx);
    rx->n.dropped_bytes++;
    return;
  }
  ev->kind = K1_PRSM_RX_HOTKEY;
}

void k1_prsm_rx_burst_end(k1_prsm_rx_t *rx, k1_prsm_rx_event_t *ev) {
  if (!rx || !ev) return;
  ev->kind = K1_PRSM_RX_NONE;
  ev->byte = 0;
  ev->line = rx->cmd;
  const k1_prsm_scan_result_t scan = k1_prsm_scanner_flush(&rx->scanner, &ev->frame);
  if (scan == K1_PRSM_SCAN_FRAME_OK) {
    enter_session(rx);
    rx->n.frames_ok++;
    ev->kind = K1_PRSM_RX_FRAME;
  } else if (scan == K1_PRSM_SCAN_FRAME_BAD) {
    enter_session(rx);
    rx->n.frames_bad++;
  }
}
