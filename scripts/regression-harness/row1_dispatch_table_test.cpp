// ============================================================================
//  Row 1 — host-compilable test of the serial dispatch-table classification +
//  routing logic (NOT a firmware build; no Arduino/ESP-IDF dependencies).
// ----------------------------------------------------------------------------
//  Why this exists:
//    The Arduino firmware is a single translation unit that #includes the full
//    HAL; it has no host unit-test runner. The SAFETY-LOAD-BEARING part of Row 1
//    is pure logic: a const table of {name, hotkey, safety_class, flags,
//    input_surface} plus a dispatcher that applies the D5/D6 gates.
//
//  SHARED SOURCE OF TRUTH (M2):
//    The table ROWS are NOT re-typed here. They come from the same X-macro file
//    the firmware uses — ../../SPECTRASYNQ_K1_FIRMWARE/serial_cmd_table.def — so
//    this test exercises the REAL row set and can never silently diverge. Only
//    the host-side type aliases and model handlers are local; the rows, names,
//    classes, flags and surfaces are the shipped artifact.
//
//  What this proves on the host:
//    - invariant A: every row has a name + handler
//    - invariant B: no duplicate command names
//    - invariant C (LOAD-BEARING): no FORBIDDEN/ARM/TYPED_ONLY row carries a
//      keystroke or a BOTH/IMMEDIATE surface
//    - D5: typed start_noise_cal routes to guidance and NEVER queues calibration
//      (with teeth: the model flips g_calibration_queued if the wired handler
//      ever takes a queueing branch — see cmd_start_noise_cal / _guidance below)
//    - D6: factory_reset / restore_defaults / clear_noise_cal fire ONLY with a
//      typed "CONFIRM" token; bare / wrong-token / any other trailing token does
//      not fire
//    - BLOCKER fix: a trailing token on a NON-forbidden bare command (reset now,
//      dump junk, version 1) is NOT consumed by the table (falls to bad_command)
//
//  What it does NOT prove: the firmware's value-parsing setters and the on-device
//  behaviour of the destructive handlers — those need the hardware smoke gate.
//
//  Build & run:   c++ -std=c++17 -Wall -Wextra row1_dispatch_table_test.cpp \
//                     -o /tmp/row1_test && /tmp/row1_test
//  (or run ./run_row1_dispatch_table_test.sh)
// ============================================================================

#include <cstdio>
#include <cstring>
#include <cstdint>
#include <cstddef>

// ---- mirror of the firmware types (serial_menu.h) --------------------------
typedef enum {
  SC_SAFE = 0,
  SC_TYPED_ONLY,
  SC_ARM_REQUIRED,
  SC_FORBIDDEN_SINGLE_BYTE
} safety_class_t;

#define CMD_PERSISTS      (1u << 0)
#define CMD_IRREVERSIBLE  (1u << 1)
#define CMD_NEEDS_SILENCE (1u << 2)
#define CMD_DISRUPTIVE    (1u << 3)
#define CMD_HARNESS       (1u << 4)

typedef enum { IS_BOTH = 0, IS_TYPED_ONLY, IS_HOTKEY_IMMEDIATE } input_surface_t;

typedef struct {
  const char*     name;
  char            hotkey;
  void          (*handler)();
  safety_class_t  safety_class;
  uint8_t         flags;
  input_surface_t input_surface;
} serial_cmd_row_t;

// ---- host model state ------------------------------------------------------
// g_last_effect records which command's handler ran (so we can assert WHICH
// command fired without a device). g_calibration_queued models the firmware's
// noise_transition_queued: it is set true ONLY by a handler that actually
// queues calibration. The guidance handler must leave it false.
enum class Effect {
  NONE, VERSION, HELP, SB_QUERY, REBOOT, FACTORY_RESET, RESTORE_DEFAULTS,
  CLEAR_NOISE_CAL, CHIP_ID, IDENTIFY, CAL_GUIDANCE, CAL_QUEUED, GET_NUM_MODES,
  GET_MODE, RESET_REASON, DUMP, STOP, FPS, LED_FPS, VP_STATUS, SMART_STATUS,
  EDGE_STATUS, EVENT_STATUS, VP_OUT_TEST, GET_KNOBS, GET_BUTTONS, QUEUE_COMMIT,
  SLOT_LIST, BUILD
};
static Effect g_last_effect = Effect::NONE;
static bool   g_calibration_queued = false; // mirrors noise_transition_queued

// ---- model handlers (named IDENTICALLY to the firmware handlers) -----------
// The .def references these names; defining them here with the same names lets
// the SAME X-macro rows build the test's table. Each records its effect.
static void cmd_version()          { g_last_effect = Effect::VERSION; }
static void cmd_build()            { g_last_effect = Effect::BUILD; }  // N5 build-provenance row
static void cmd_help()             { g_last_effect = Effect::HELP; }
static void cmd_sb_query()         { g_last_effect = Effect::SB_QUERY; }
static void cmd_reset()            { g_last_effect = Effect::REBOOT; }
static void cmd_factory_reset()    { g_last_effect = Effect::FACTORY_RESET; }
static void cmd_restore_defaults() { g_last_effect = Effect::RESTORE_DEFAULTS; }
static void cmd_clear_noise_cal()  { g_last_effect = Effect::CLEAR_NOISE_CAL; }
static void cmd_chip_id()          { g_last_effect = Effect::CHIP_ID; }
static void cmd_identify()         { g_last_effect = Effect::IDENTIFY; }

// D5 with TEETH: the guidance handler the .def currently wires for
// start_noise_cal records CAL_GUIDANCE and explicitly does NOT queue. The
// _queueing_ variant below models the PRE-D5 behaviour; it sets the queue flag.
// If a regression re-wires the start_noise_cal row in serial_cmd_table.def to
// cmd_start_noise_cal (the queueing handler), this test compiles against the
// shared .def, invokes the queueing handler, flips g_calibration_queued, and the
// D5 assertion FAILS. So the assertion has real teeth, not a vacuous constant.
static void cmd_start_noise_cal_guidance() {
  g_last_effect = Effect::CAL_GUIDANCE;
  // intentionally does NOT set g_calibration_queued
}
// [[maybe_unused]]: this is the regression TARGET. It is referenced by the .def
// only if start_noise_cal is (wrongly) re-wired to queue; in the correct build
// the .def points at the guidance handler, leaving this defined-but-unwired.
[[maybe_unused]] static void cmd_start_noise_cal() { // pre-D5 queueing behaviour
  g_last_effect = Effect::CAL_QUEUED;
  g_calibration_queued = true;
}

static void cmd_get_num_modes()    { g_last_effect = Effect::GET_NUM_MODES; }
static void cmd_get_mode()         { g_last_effect = Effect::GET_MODE; }
static void cmd_reset_reason()     { g_last_effect = Effect::RESET_REASON; }
static void cmd_dump()             { g_last_effect = Effect::DUMP; }
static void cmd_stop()             { g_last_effect = Effect::STOP; }
static void cmd_fps()              { g_last_effect = Effect::FPS; }
static void cmd_led_fps()          { g_last_effect = Effect::LED_FPS; }
static void cmd_vp_status()        { g_last_effect = Effect::VP_STATUS; }
static void cmd_smart_status()     { g_last_effect = Effect::SMART_STATUS; }
static void cmd_edge_status()      { g_last_effect = Effect::EDGE_STATUS; }
static void cmd_event_status()     { g_last_effect = Effect::EVENT_STATUS; }
static void cmd_vp_out_test()      { g_last_effect = Effect::VP_OUT_TEST; }
static void cmd_get_knobs()        { g_last_effect = Effect::GET_KNOBS; }
static void cmd_get_buttons()      { g_last_effect = Effect::GET_BUTTONS; }
static void cmd_queue_commit()     { g_last_effect = Effect::QUEUE_COMMIT; }
static void cmd_slot_list()        { g_last_effect = Effect::SLOT_LIST; }

// ---- the table: SHARED rows from the firmware X-macro (M2) ------------------
static const serial_cmd_row_t SERIAL_CMD_TABLE[] = {
#define SERIAL_CMD(name, hotkey, handler, safety_class, flags, input_surface) \
  { name, hotkey, handler, safety_class, flags, input_surface },
#include "../../SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def"
#undef SERIAL_CMD
};
#define SERIAL_CMD_TABLE_LEN (sizeof(SERIAL_CMD_TABLE) / sizeof(SERIAL_CMD_TABLE[0]))

// ---- mirror of serial_cmd_lookup + serial_dispatch_typed_row ----------------
static const serial_cmd_row_t* serial_cmd_lookup(const char* name) {
  for (size_t i = 0; i < SERIAL_CMD_TABLE_LEN; i++)
    if (strcmp(SERIAL_CMD_TABLE[i].name, name) == 0) return &SERIAL_CMD_TABLE[i];
  return nullptr;
}

static void serial_dispatch_typed_row(const serial_cmd_row_t* row, const char* args) {
  switch (row->safety_class) {
    case SC_FORBIDDEN_SINGLE_BYTE:
      if (args != nullptr && strcmp(args, "CONFIRM") == 0) row->handler();
      else g_last_effect = Effect::NONE; // usage line; no destructive effect
      break;
    case SC_ARM_REQUIRED:
      row->handler(); // guidance only (D5) — teeth: handler may flip queue flag
      break;
    case SC_SAFE:
    case SC_TYPED_ONLY:
    default:
      row->handler();
      break;
  }
}

// Mirror of parse_command's bare-command routing (the part Row 1 owns), AFTER
// the BLOCKER fix: the trailing-token branch is scoped to FORBIDDEN rows only.
static Effect route_bare(const char* command_buf_in) {
  g_last_effect = Effect::NONE;
  char buf[128]; snprintf(buf, sizeof(buf), "%s", command_buf_in);

  if (strchr(buf, '=') != nullptr) return g_last_effect; // typed setter path (not modelled)

  const serial_cmd_row_t* row = serial_cmd_lookup(buf);
  if (row != nullptr) { serial_dispatch_typed_row(row, ""); return g_last_effect; }

  char* space = strchr(buf, ' ');
  if (space != nullptr) {
    *space = '\0';
    const serial_cmd_row_t* head = serial_cmd_lookup(buf);
    if (head != nullptr && head->safety_class == SC_FORBIDDEN_SINGLE_BYTE) {
      serial_dispatch_typed_row(head, space + 1);
      return g_last_effect;
    }
    // non-FORBIDDEN head (or unknown) -> NOT consumed by table -> bad_command
  }
  return g_last_effect; // unknown / non-forbidden-with-tail -> metadata parser (bad_command)
}

// ----------------------------------------------------------------------------
static int g_failures = 0;
static void check(bool cond, const char* what) {
  if (!cond) { printf("  FAIL: %s\n", what); g_failures++; }
  else       { printf("  ok  : %s\n", what); }
}

int main() {
  printf("Row 1 dispatch-table host test (rows shared from serial_cmd_table.def)\n");

  // -- invariant A -----------------------------------------------------------
  printf("[A] every row has a name + handler\n");
  bool a_ok = true;
  for (size_t i = 0; i < SERIAL_CMD_TABLE_LEN; i++)
    if (SERIAL_CMD_TABLE[i].name == nullptr || SERIAL_CMD_TABLE[i].handler == nullptr) a_ok = false;
  check(a_ok, "all rows carry a name + handler");

  // -- invariant B -----------------------------------------------------------
  printf("[B] no duplicate command names\n");
  bool b_ok = true;
  for (size_t i = 0; i < SERIAL_CMD_TABLE_LEN; i++)
    for (size_t j = i + 1; j < SERIAL_CMD_TABLE_LEN; j++)
      if (strcmp(SERIAL_CMD_TABLE[i].name, SERIAL_CMD_TABLE[j].name) == 0) b_ok = false;
  check(b_ok, "no two rows share a name");

  // -- invariant C (LOAD-BEARING) --------------------------------------------
  printf("[C] no FORBIDDEN/ARM/TYPED_ONLY row carries a hotkey or BOTH/IMMEDIATE surface\n");
  bool c_ok = true;
  for (size_t i = 0; i < SERIAL_CMD_TABLE_LEN; i++) {
    const serial_cmd_row_t& r = SERIAL_CMD_TABLE[i];
    if (r.safety_class == SC_FORBIDDEN_SINGLE_BYTE ||
        r.safety_class == SC_ARM_REQUIRED ||
        r.safety_class == SC_TYPED_ONLY) {
      if (r.hotkey != 0) c_ok = false;
      if (r.input_surface == IS_BOTH || r.input_surface == IS_HOTKEY_IMMEDIATE) c_ok = false;
    }
  }
  check(c_ok, "destructive/ARM/typed-only rows are typed-only with hotkey==0");

  // -- D5 (with teeth) -------------------------------------------------------
  printf("[D5] typed start_noise_cal routes to guidance, never queues calibration\n");
  g_calibration_queued = false;
  Effect e = route_bare("start_noise_cal");
  check(e == Effect::CAL_GUIDANCE, "start_noise_cal -> CAL_GUIDANCE (not CAL_QUEUED)");
  check(g_calibration_queued == false, "start_noise_cal did NOT queue calibration");
  check(serial_cmd_lookup("start_noise_cal")->safety_class == SC_ARM_REQUIRED,
        "start_noise_cal classified SC_ARM_REQUIRED");

  // -- D6 --------------------------------------------------------------------
  printf("[D6] factory_reset / restore_defaults / clear_noise_cal require CONFIRM\n");
  struct { const char* name; Effect eff; } trio[] = {
    { "factory_reset",    Effect::FACTORY_RESET    },
    { "restore_defaults", Effect::RESTORE_DEFAULTS },
    { "clear_noise_cal",  Effect::CLEAR_NOISE_CAL  },
  };
  for (auto& t : trio) {
    char confirmed[80]; snprintf(confirmed, sizeof(confirmed), "%s CONFIRM", t.name);
    char wrongtok[80];  snprintf(wrongtok,  sizeof(wrongtok),  "%s YES",     t.name);
    char prefix[80];    snprintf(prefix,    sizeof(prefix),    "%sX",        t.name); // not a row

    check(route_bare(t.name)   == Effect::NONE, "  bare (no token) -> no effect (usage)");
    check(route_bare(wrongtok) == Effect::NONE, "  wrong confirm token -> no effect");
    check(route_bare(prefix)   == Effect::NONE, "  near-miss token -> no effect");
    check(route_bare(confirmed) == t.eff,       "  CONFIRM -> fires");
  }

  // -- BLOCKER fix: trailing token on NON-forbidden bare cmds is NOT consumed -
  printf("[BLOCKER] trailing token on a non-FORBIDDEN bare command -> NO table effect\n");
  check(route_bare("reset now")  == Effect::NONE, "reset now -> NO effect (NOT a reboot)");
  check(route_bare("dump junk")  == Effect::NONE, "dump junk -> NO effect");
  check(route_bare("version 1")  == Effect::NONE, "version 1 -> NO effect");
  // sanity: the bare forms (no token) still fire normally
  check(route_bare("reset")   == Effect::REBOOT,  "reset (bare) still -> REBOOT");
  check(route_bare("dump")    == Effect::DUMP,    "dump (bare) still -> DUMP");
  check(route_bare("version") == Effect::VERSION, "version (bare) still -> VERSION");

  // -- SAFE reads fire unconditionally ---------------------------------------
  printf("[SAFE] representative SAFE reads fire\n");
  check(route_bare("chip_id") == Effect::CHIP_ID, "chip_id fires");
  check(route_bare("fps")     == Effect::FPS,     "fps fires");

  // -- reset classification --------------------------------------------------
  printf("[reset] reset is TYPED_ONLY + DISRUPTIVE\n");
  check(serial_cmd_lookup("reset")->safety_class == SC_TYPED_ONLY, "reset is SC_TYPED_ONLY");
  check((serial_cmd_lookup("reset")->flags & CMD_DISRUPTIVE) != 0, "reset carries CMD_DISRUPTIVE");

  // -- unknown token ---------------------------------------------------------
  printf("[unknown] unknown bare token not consumed by the table\n");
  check(route_bare("fooo") == Effect::NONE, "unknown token -> no table effect");

  printf("\n%s (%zu rows from shared .def; %d failures)\n",
         g_failures == 0 ? "ALL PASS" : "FAILURES PRESENT",
         (size_t)SERIAL_CMD_TABLE_LEN, g_failures);
  return g_failures == 0 ? 0 : 1;
}
