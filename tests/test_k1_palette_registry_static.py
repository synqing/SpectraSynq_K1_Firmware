import hashlib
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PALETTES_H = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "Palettes.h"
PALETTES_CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "Palettes.cpp"
TAB5_UI = ROOT / "sb-tab5-wireless-controller" / "src" / "ui" / "LightComposerUI.cpp"
TAB5_PAGES = ROOT / "sb-tab5-wireless-controller" / "src" / "ui" / "LightComposerUI_pages.cpp"

K1_PALETTES = [
    "K1_Iris_Apricot_gp",
    "K1_Tropical_Ultraviolet_gp",
    "K1_Chameleon_Flare_gp",
    "K1_Coral_Sunset_gp",
    "K1_Night_Sea_Amber_gp",
    "K1_Crimson_Gold_gp",
    "K1_Ultraviolet_Ascend_gp",
    "K1_Naberius_Gold_gp",
    "K1_Vepar_Pink_gp",
    "K1_Flourish_Sweep_gp",
    "K1_Ultraviolet_Bright_gp",
]

# Deliberate A/B probes for the dark-anchor hypothesis: bright end-to-end, so
# the dark-anchor assertion does not apply. All other LED guards still do.
DARK_ANCHOR_EXEMPT = {
    "K1_Ultraviolet_Bright_gp",
}

# SHA-256 fingerprints (first 16 hex chars) of the numeric stop data for every
# legacy palette. The 2026-06-10/11 visual breakage included silent mutations
# of legacy palette stops; this lock turns that failure mode into a hard test
# failure. Regenerate a fingerprint ONLY for a palette Captain explicitly
# approved changing.
LEGACY_PALETTE_FINGERPRINTS = {
    "ib_jul01_gp": "20c0da6e5c218725",
    "es_vintage_57_gp": "7d8d137c7ca05522",
    "es_vintage_01_gp": "4968e4c5b2c43e14",
    "es_rivendell_15_gp": "952d9a1975093af4",
    "rgi_15_gp": "c50ffa05d50affdd",
    "retro2_16_gp": "b8cc787ff0214a0a",
    "Analogous_1_gp": "3bc77703aef8a626",
    "es_pinksplash_08_gp": "0a792d9e67e9a5e3",
    "es_pinksplash_07_gp": "3259e932adaac335",
    "Coral_reef_gp": "af525ad9088ac653",
    "es_ocean_breeze_068_gp": "b61cce76dbd596ce",
    "es_ocean_breeze_036_gp": "9c27af864b99d5a3",
    "departure_gp": "ca5b5b5b550ea377",
    "es_landscape_64_gp": "8f8628ae4a403817",
    "es_landscape_33_gp": "11ad6db7d8823a43",
    "rainbowsherbet_gp": "c96fe2484ff597d1",
    "gr65_hult_gp": "3c6973ae01ec330d",
    "gr64_hult_gp": "ac17ded8b7f1e5a6",
    "GMT_drywet_gp": "b554388d0b13a29f",
    "ib15_gp": "005bdc00c8b98030",
    "Fuschia_7_gp": "f0eb12f01c27f3ba",
    "es_emerald_dragon_08_gp": "0bf589db9f1213e8",
    "lava_gp": "0fa62945803e4803",
    "fire_gp": "8d61b9eba96878cb",
    "Colorfull_gp": "e006c0bc43115922",
    "Magenta_Evening_gp": "6cbfb4153de2615f",
    "Pink_Purple_gp": "c04cf89752aa4400",
    "Sunset_Real_gp": "e8e1439abb42d3c6",
    "es_autumn_19_gp": "a13dba99b0322ed1",
    "BlacK_Blue_Magenta_White_gp": "dc18fff065500537",
    "BlacK_Magenta_Red_gp": "8d8e28ae82d129ad",
    "BlacK_Red_Magenta_Yellow_gp": "115a96519270517a",
    "Blue_Cyan_Yellow_gp": "1f33979a9ca1cbff",
}


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_array(text: str, name: str) -> list[str]:
    match = re.search(rf"{name}\[\][^=]*=\s*\{{(?P<body>.*?)\n\}};", text, re.S)
    if not match:
        raise AssertionError(f"could not find {name} array")
    return [
        token.strip().strip('"')
        for token in match.group("body").split(",")
        if token.strip()
    ]


def extract_palette_definition(text: str, name: str) -> list[tuple[int, int, int, int]]:
    match = re.search(rf"DEFINE_GRADIENT_PALETTE\({name}\)\{{(?P<body>.*?)\n\}};", text, re.S)
    if not match:
        raise AssertionError(f"could not find palette definition for {name}")
    values = [int(v) for v in re.findall(r"\b\d+\b", match.group("body"))]
    if len(values) % 4 != 0:
        raise AssertionError(f"{name} has incomplete gradient rows")
    return [
        (values[i], values[i + 1], values[i + 2], values[i + 3])
        for i in range(0, len(values), 4)
    ]


class K1PaletteRegistryStaticTest(unittest.TestCase):
    def test_gradient_registry_names_and_tab5_names_stay_in_sync(self) -> None:
        header = read(PALETTES_H)
        registry = extract_array(header, "gGradientPalettes")
        names = extract_array(header, "paletteNames")

        self.assertEqual(len(registry), len(names))
        self.assertEqual(registry[-len(K1_PALETTES):], K1_PALETTES)
        self.assertEqual(names[-len(K1_PALETTES):], K1_PALETTES)

        expected_max = len(registry) - 1
        if not TAB5_UI.exists():
            self.skipTest(
                "Tab5 controller (sb-tab5-wireless-controller) is not part of the "
                "firmware-only repo; the firmware<->Tab5 palette/MAX_PALETTE sync "
                "contract is enforced in integration CI where both repos are present."
            )
        for path in (TAB5_UI, TAB5_PAGES):
            text = read(path)
            self.assertIn(f"static constexpr uint8_t MAX_PALETTE = {expected_max};", text)
            for palette in K1_PALETTES:
                label = palette.replace("_gp", "").replace("_", " ").upper()
                self.assertIn(f'"{label}"', text)

    def test_k1_led_palettes_avoid_white_bloom_and_keep_dark_anchors(self) -> None:
        source = read(PALETTES_CPP)

        for palette in K1_PALETTES:
            rows = extract_palette_definition(source, palette)
            self.assertLessEqual(len(rows), 16, palette)
            positions = [row[0] for row in rows]
            self.assertEqual(positions, sorted(positions), palette)
            self.assertEqual(positions[0], 0, palette)
            self.assertEqual(positions[-1], 255, palette)

            for _, r, g, b in rows:
                # Near-white blooms through the LGP and was explicitly rejected.
                self.assertFalse(r >= 220 and g >= 220 and b >= 220, palette)
                # Bright non-anchor stops should be saturated, not pastel/grey.
                if max(r, g, b) >= 96:
                    self.assertGreaterEqual(max(r, g, b) - min(r, g, b), 85, palette)

            if palette not in DARK_ANCHOR_EXEMPT:
                for _, r, g, b in (rows[0], rows[-1]):
                    self.assertLessEqual(max(r, g, b), 40, palette)

    def test_legacy_palette_stop_data_is_locked(self) -> None:
        source = read(PALETTES_CPP)
        defined = re.findall(r"DEFINE_GRADIENT_PALETTE\((\w+)\)", source)
        legacy = [name for name in defined if not name.startswith("K1_")]

        self.assertEqual(sorted(legacy), sorted(LEGACY_PALETTE_FINGERPRINTS))

        for name in legacy:
            rows = extract_palette_definition(source, name)
            values = ",".join(str(v) for row in rows for v in row)
            digest = hashlib.sha256(values.encode()).hexdigest()[:16]
            self.assertEqual(
                digest,
                LEGACY_PALETTE_FINGERPRINTS[name],
                f"legacy palette {name} stop data changed — legacy palettes are "
                "locked; revert the mutation or get explicit Captain approval "
                "and regenerate the fingerprint",
            )


if __name__ == "__main__":
    unittest.main()
