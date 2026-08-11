/**
 * Recursive LVGL object-bounds dump for Precision Bay optical gates.
 * Simulator-only.
 */

#include "sim_bounds_dump.h"

#include <lvgl.h>

#include <stdio.h>
#include <string.h>

namespace {

void json_escape(FILE* out, const char* s)
{
  if (!s) {
    fputs("", out);
    return;
  }
  for (const char* p = s; *p; ++p) {
    const unsigned char c = static_cast<unsigned char>(*p);
    if (c == '"' || c == '\\') {
      fputc('\\', out);
      fputc(c, out);
    } else if (c == '\n') {
      fputs("\\n", out);
    } else if (c == '\r') {
      fputs("\\r", out);
    } else if (c == '\t') {
      fputs("\\t", out);
    } else if (c < 0x20) {
      fprintf(out, "\\u%04x", c);
    } else {
      fputc(c, out);
    }
  }
}

const char* obj_class_name(const lv_obj_t* obj)
{
  if (!obj) return "null";
  if (lv_obj_check_type(obj, &lv_label_class)) return "label";
  if (lv_obj_check_type(obj, &lv_image_class)) return "image";
  if (lv_obj_check_type(obj, &lv_bar_class)) return "bar";
  if (lv_obj_check_type(obj, &lv_arc_class)) return "arc";
  return "obj";
}

void dump_obj(FILE* out, lv_obj_t* obj, int depth, bool* first)
{
  if (!obj) return;
  lv_area_t a;
  lv_obj_get_coords(obj, &a);
  if (!*first) fputc(',', out);
  *first = false;
  fputs("\n", out);
  for (int i = 0; i < depth + 1; ++i) fputs("  ", out);
  fputs("{\"class\":\"", out);
  fputs(obj_class_name(obj), out);
  fprintf(out,
          "\",\"x\":%d,\"y\":%d,\"w\":%d,\"h\":%d,\"abs\":[%d,%d,%d,%d],\"hidden\":%s",
          int(lv_obj_get_x(obj)), int(lv_obj_get_y(obj)), int(lv_obj_get_width(obj)),
          int(lv_obj_get_height(obj)), int(a.x1), int(a.y1), int(a.x2), int(a.y2),
          lv_obj_has_flag(obj, LV_OBJ_FLAG_HIDDEN) ? "true" : "false");

  if (lv_obj_check_type(obj, &lv_label_class)) {
    const char* txt = lv_label_get_text(obj);
    fputs(",\"text\":\"", out);
    json_escape(out, txt);
    fputc('"', out);
  }

  const uint32_t n = lv_obj_get_child_count(obj);
  if (n > 0) {
    fputs(",\"children\":[", out);
    bool child_first = true;
    for (uint32_t i = 0; i < n; ++i) {
      dump_obj(out, lv_obj_get_child(obj, i), depth + 1, &child_first);
    }
    fputs("]", out);
  }
  fputc('}', out);
}

}  // namespace

bool sim_dump_bounds_json(lv_display_t* disp, const char* path)
{
  if (!disp || !path) return false;
  lv_obj_t* scr = lv_display_get_screen_active(disp);
  if (!scr) return false;
  lv_obj_update_layout(scr);

  FILE* out = fopen(path, "w");
  if (!out) return false;

  fprintf(out,
          "{\n  \"schema\":\"precision_bay_r1.bounds_dump/1\",\n"
          "  \"screen\":{\"w\":%d,\"h\":%d},\n"
          "  \"tree\":",
          int(lv_obj_get_width(scr)), int(lv_obj_get_height(scr)));
  bool first = true;
  /* Wrap root as single-element by dumping root itself. */
  fputc('[', out);
  dump_obj(out, scr, 0, &first);
  fputs("\n  ]\n}\n", out);
  fclose(out);
  printf("[sim] bounds dump written: %s\n", path);
  return true;
}
