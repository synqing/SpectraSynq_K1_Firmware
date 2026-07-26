// Second-TU smoke: proves serial_menu.h is include-safe without ODR duplicate
// definitions now that bodies live in serial_menu.cpp / serial_typed_dispatch.cpp.
#include "serial_menu.h"

void serial_menu_second_tu_smoke_anchor() {
  (void)serial_cmd_lookup("help");
  (void)serial_typed_cmd_lookup("photons");
}
