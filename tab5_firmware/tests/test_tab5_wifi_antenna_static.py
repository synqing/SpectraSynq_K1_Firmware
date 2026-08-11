"""Keep the product Tab5 RF selector in the recovered firmware path."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = ROOT / "platformio.ini"
MAIN = ROOT / "src/main.cpp"
ANTENNA = ROOT / "src/network/WiFiAntenna.cpp"


def test_product_build_initialises_the_internal_rf_path_after_m5_begin():
    platformio = PLATFORMIO.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    antenna = ANTENNA.read_text(encoding="utf-8")

    assert "+<network/WiFiAntenna.cpp>" in platformio
    assert '#include "network/WiFiAntenna.h"' in main
    assert main.index("M5.begin(cfg);") < main.index("initWiFiAntennaPin();")
    assert "constexpr bool kBootDefaultExternal = false" in antenna
    assert "ioe.setDirection(ANTENNA_SELECTOR_PIN, true)" in antenna
    assert "ioe.setHighImpedance(ANTENNA_SELECTOR_PIN, false)" in antenna
    assert "selectorMatchesRequest" in antenna
