"""Skip FastLED's clockless_i2s_esp32s3.cpp when K1_LED_I2S_DIRECT_V1 is on.

That FastLED TU includes the Yves driver.h shim (COLOR_ORDER_RBG) and defines
the namespace-scope Yves globals. k1_i2s_emit.cpp includes the Yves header once
with COLOR_ORDER_RGB. Two TUs would duplicate DRIVER_READY / led_io_handle.

This script is a no-op unless the env defines K1_LED_I2S_DIRECT_V1.
"""
Import("env")  # noqa: F821  (injected by PlatformIO/SCons)


def _has_direct_flag():
    defs = env.get("CPPDEFINES", [])  # noqa: F821
    for item in defs:
        name = item[0] if isinstance(item, (list, tuple)) else item
        if str(name) == "K1_LED_I2S_DIRECT_V1":
            return True
    flags = env.GetProjectOption("build_flags", default="")  # noqa: F821
    return "K1_LED_I2S_DIRECT_V1" in str(flags)


if _has_direct_flag():

    def skip_fastled_i2s_wrapper(node):
        path = node.get_abspath().replace("\\", "/")
        if path.endswith("clockless_i2s_esp32s3.cpp"):
            return None
        return node

    env.AddBuildMiddleware(skip_fastled_i2s_wrapper)  # noqa: F821
