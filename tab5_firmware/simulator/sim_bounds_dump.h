#pragma once
/** Recursive object-bounds JSON dump for native-SDL optical gates. */

#include <lvgl.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

bool sim_dump_bounds_json(lv_display_t* disp, const char* path);

#ifdef __cplusplus
}
#endif
