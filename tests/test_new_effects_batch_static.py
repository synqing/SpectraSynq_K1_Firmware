"""Static gates for the 2026-06-11 effect batch (modes 25-29).

Enforces the method + hardened-rules contract for all five new variant modes:
CHROMA CONSTELLATION (25), PERCUSSION BURST (26), TEMPO COMET ANTICIPATE (27),
RIVER SURGE (28), TEMPO RIVER WALK (29). Variant contract: originals untouched;
append-only registration; Strobe Law (no global amplitude on beat/onset); no
heap in render; event-gated percussion (no continuous-level fallbacks); the
audio path (i2s_audio/GDFT) receives ZERO changes from this lane.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
EFFECTS = FW / "effects"

NEW_FILES = {
    "chroma_constellation": (EFFECTS / "light_mode_chroma_constellation.cpp").read_text(),
    "percussion_burst": (EFFECTS / "light_mode_percussion_burst.cpp").read_text(),
    "tempo_comet_anticipate": (EFFECTS / "light_mode_tempo_comet_anticipate.cpp").read_text(),
    "river_surge": (EFFECTS / "light_mode_river_surge.cpp").read_text(),
    "tempo_river_walk": (EFFECTS / "light_mode_tempo_river_walk.cpp").read_text(),
}
ORIGINALS = {
    "spectrum_river_v2": (EFFECTS / "light_mode_spectrum_river_v2.cpp").read_text(),
    "tempo_river": (EFFECTS / "light_mode_tempo_river.cpp").read_text(),
    "tempo_comet": (EFFECTS / "light_mode_tempo_comet.cpp").read_text(),
    "dense_forge": (EFFECTS / "light_mode_dense_forge.cpp").read_text(),
}
CONFIG_TYPES = (FW / "system" / "config_types.h").read_text()
SYSTEM = (FW / "system" / "system.h").read_text()
INO = (FW / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text()
STATE = (FW / "visual" / "channel_effect_state.h").read_text()

ENUM_ORDER = [
    "LIGHT_MODE_DENSE_FORGE_CHORD,",
    "LIGHT_MODE_CHROMA_CONSTELLATION,",
    "LIGHT_MODE_PERCUSSION_BURST,",
    "LIGHT_MODE_TEMPO_COMET_ANTICIPATE,",
    "LIGHT_MODE_RIVER_SURGE,",
    "LIGHT_MODE_TEMPO_RIVER_WALK,",
]

NAMES = {
    25: "CHROMA CONSTELLATION",
    26: "PERCUSSION BURST",
    27: "TEMPO COMET ANTICIPATE",
    28: "RIVER SURGE",
    29: "TEMPO RIVER WALK",
}


class NewEffectsBatchStaticTest(unittest.TestCase):
    def test_enum_appended_in_order_before_num_modes(self):
        idx = [CONFIG_TYPES.index(tok) for tok in ENUM_ORDER]
        self.assertEqual(idx, sorted(idx))
        self.assertLess(idx[-1], CONFIG_TYPES.index("NUM_MODES", idx[-1]))

    def test_mode_names_registered(self):
        for num, name in NAMES.items():
            self.assertIn(f'set_mode_name({num}, "{name}");', SYSTEM)

    def test_dispatch_wired_with_correct_history_contracts(self):
        # Transport-class effects: standard self-managed-history dispatch.
        for fn in ("chroma_constellation", "percussion_burst", "river_surge",
                   "tempo_river_walk"):
            self.assertIn(f"light_mode_{fn}(channel.history, *channel.effect);", INO)
        # Particle-class (Comet lineage): seed-from-history + store-back wrap.
        anticipate = INO.index("light_mode_tempo_comet_anticipate(*channel.effect);")
        block = INO[INO.index("LIGHT_MODE_TEMPO_COMET_ANTICIPATE"):anticipate + 200]
        self.assertIn("memcpy(leds_16, channel.history", block)
        self.assertIn("memcpy(channel.history, leds_16", block)

    def test_state_fields_exist_for_every_new_effect(self):
        for tok in ("cc_chroma_smooth", "pburst_pos[PBURST_MAX]",
                    "tcanta_t[COMET_MAX]", "rsurge_slow_env", "trwalk_offset"):
            self.assertIn(tok, STATE)

    def test_originals_are_untouched_by_variant_tokens(self):
        # Variant contract: no new-lane token may appear in any original effect.
        for name, text in ORIGINALS.items():
            for tok in ("cc_chroma", "pburst_", "tcanta_", "rsurge_", "trwalk_",
                        "_anticipate", "_surge", "_walk"):
                self.assertNotIn(tok, text, f"{tok} leaked into {name}")

    def test_no_heap_and_no_mutable_statics_in_new_effects(self):
        for name, text in NEW_FILES.items():
            for banned in ("malloc", "new CRGB", "ps_malloc", "calloc"):
                self.assertNotIn(banned, text, f"heap token in {name}")
            # File-scope mutable static VARIABLES banned (functions are fine:
            # internal linkage, not state). A static variable line has `=` (or
            # a bare `;` declaration) before any parameter list opens.
            for line in text.splitlines():
                s = line.strip()
                if not s.startswith("static ") or s.startswith(
                        ("static const", "static inline", "static_assert")):
                    continue
                head = s.split("=")[0] if "=" in s else s
                is_function = "(" in head
                if not is_function:
                    self.fail(f"mutable file-scope static in {name}: {s[:70]}")

    def test_percussion_is_event_gated_not_level_driven(self):
        # The Codex lesson: consume event ids, never continuous-level fallbacks.
        pb = NEW_FILES["percussion_burst"]
        for tok in ("pburst_kick_id", "pburst_snare_id", "pburst_hihat_id"):
            self.assertIn(tok, pb)
        self.assertNotIn("FALLBACK_GAIN", pb)

    def test_audio_path_untouched_by_this_lane(self):
        # The strobe lesson: the Core-0 audio path is a frozen surface.
        i2s = (FW / "audio" / "i2s_audio.h").read_text()
        gdft = (FW / "audio" / "GDFT.h").read_text()
        for tok in ("cc_", "pburst_", "tcanta_", "rsurge_", "trwalk_",
                    "constellation", "ch_root"):
            self.assertNotIn(tok, i2s)
            self.assertNotIn(tok, gdft)


if __name__ == "__main__":
    unittest.main()
