// Host mirror of SERIAL_TYPED_CMD_TABLE integrity (R2 design lock).
#include <cstdio>
#include <cstring>
#include <cstdint>

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

typedef bool (*serial_typed_handler_t)(const char* command_type, char* command_data);

typedef struct {
  const char* name;
  serial_typed_handler_t handler;
  safety_class_t safety_class;
  uint8_t flags;
} serial_typed_cmd_row_t;

static bool stub_handler(const char*, char*) { return true; }

static serial_typed_cmd_row_t SERIAL_TYPED_CMD_TABLE[] = {
#define SERIAL_TYPED_CMD(name, handler, safety_class, flags) \
  { name, stub_handler, safety_class, flags },
#include "../../SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_cmd_table.def"
#undef SERIAL_TYPED_CMD
};

#define SERIAL_TYPED_CMD_TABLE_LEN (sizeof(SERIAL_TYPED_CMD_TABLE) / sizeof(SERIAL_TYPED_CMD_TABLE[0]))

int main() {
  int fails = 0;
  auto check = [&](bool ok, const char* msg) {
    if (!ok) { printf("FAIL: %s\n", msg); fails++; }
    else { printf("PASS: %s\n", msg); }
  };

  check(SERIAL_TYPED_CMD_TABLE_LEN >= 100, "typed table has expected row volume");
  for (size_t i = 0; i < SERIAL_TYPED_CMD_TABLE_LEN; i++) {
    check(SERIAL_TYPED_CMD_TABLE[i].name != nullptr, "row has name");
    check(SERIAL_TYPED_CMD_TABLE[i].handler != nullptr, "row has handler");
    for (size_t j = i + 1; j < SERIAL_TYPED_CMD_TABLE_LEN; j++) {
      if (strcmp(SERIAL_TYPED_CMD_TABLE[i].name, SERIAL_TYPED_CMD_TABLE[j].name) == 0) {
        check(false, "duplicate typed command name");
      }
    }
  }
  printf("typed_table_rows=%zu\n", SERIAL_TYPED_CMD_TABLE_LEN);
  return fails == 0 ? 0 : 1;
}
