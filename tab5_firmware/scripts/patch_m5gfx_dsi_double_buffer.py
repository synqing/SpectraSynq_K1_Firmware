"""Expose two frozen M5GFX DSI framebuffers to the Tab5 presenter.

M5GFX 0.2.26 creates one ESP-IDF DPI framebuffer.  A single live framebuffer
cannot provide an atomic landscape presentation because the panel scans it while
LVGL writes rotated regions into it.  This narrow, checksum-gated overlay asks
ESP-IDF for two native 720x1280 buffers and exposes their pointers plus the panel
handle; all drawing policy remains in lvgl_bridge.cpp.
"""

from hashlib import sha256
from pathlib import Path

Import("env")  # type: ignore

HPP_PRISTINE_SHA256 = "f441c4f3668158abb85f5030cc55a6508c6d0cf73df64fb16ab8b43f925bab19"
CPP_PRISTINE_SHA256 = "8eb86ba9bfbb87fa5e7dcc4b8d6205e73c4e375b2138e2c93f6250dbd8f742d3"
HPP_PATCHED_SHA256 = "b3b1ef4fe5beee5939c69069f7e092c4d6e7fe9672938073bc2dd0afb4059f28"
CPP_PATCHED_SHA256 = "ab126b5d7270fbb7318bd14fcdab2e9280c56344be7db37f1ab0f02a8c3ca360"

HPP_BUFFER_PRISTINE = """      void* buffer = nullptr;
      uint32_t buffer_length = 0;
"""
HPP_BUFFER_PATCHED = """      void* buffer = nullptr;
      void* buffer2 = nullptr;
      uint32_t buffer_length = 0;
"""
HPP_HANDLE_PRISTINE = """    const config_detail_t& config_detail(void) const { return _config_detail; }
    void config_detail(const config_detail_t& config_detail) { _config_detail = config_detail; };
"""
HPP_HANDLE_PATCHED = """    const config_detail_t& config_detail(void) const { return _config_detail; }
    void config_detail(const config_detail_t& config_detail) { _config_detail = config_detail; };
    esp_lcd_panel_handle_t panel_handle(void) const { return _disp_panel_handle; }
"""
CPP_COUNT_PRISTINE = "    dpi_config.num_fbs = 1;"
CPP_COUNT_PATCHED = "    dpi_config.num_fbs = 2;"
CPP_GET_PRISTINE = """        esp_lcd_dpi_panel_get_frame_buffer(_disp_panel_handle, 1, &(_config_detail.buffer));
"""
CPP_GET_PATCHED = """        esp_lcd_dpi_panel_get_frame_buffer(_disp_panel_handle, 2,
                                                 &(_config_detail.buffer),
                                                 &(_config_detail.buffer2));
"""


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def replace_exact(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"M5GFX 0.2.26 {label} anchor is not unique")
    return text.replace(old, new)


project_dir = Path(env["PROJECT_DIR"])
pioenv = env["PIOENV"]
base = project_dir / ".pio" / "libdeps" / pioenv / "M5GFX" / "src" / "lgfx" / "v1" / "platforms" / "esp32p4"
hpp = base / "Panel_DSI.hpp"
cpp = base / "Panel_DSI.cpp"
if not hpp.exists() or not cpp.exists():
    raise RuntimeError(f"Pinned M5GFX sources were not resolved for {pioenv}")

hpp_actual = digest(hpp)
if hpp_actual == HPP_PRISTINE_SHA256:
    text = hpp.read_text(encoding="utf-8")
    text = replace_exact(text, HPP_BUFFER_PRISTINE, HPP_BUFFER_PATCHED, "buffer")
    text = replace_exact(text, HPP_HANDLE_PRISTINE, HPP_HANDLE_PATCHED, "handle")
    hpp.write_text(text, encoding="utf-8")
elif HPP_PATCHED_SHA256 and hpp_actual != HPP_PATCHED_SHA256:
    raise RuntimeError(f"Refusing unexpected Panel_DSI.hpp sha256={hpp_actual}")

cpp_actual = digest(cpp)
if cpp_actual == CPP_PRISTINE_SHA256:
    text = cpp.read_text(encoding="utf-8")
    text = replace_exact(text, CPP_COUNT_PRISTINE, CPP_COUNT_PATCHED, "framebuffer count")
    text = replace_exact(text, CPP_GET_PRISTINE, CPP_GET_PATCHED, "framebuffer retrieval")
    cpp.write_text(text, encoding="utf-8")
elif CPP_PATCHED_SHA256 and cpp_actual != CPP_PATCHED_SHA256:
    raise RuntimeError(f"Refusing unexpected Panel_DSI.cpp sha256={cpp_actual}")

print("[tab5_m5gfx] verified two-framebuffer DSI overlay")
