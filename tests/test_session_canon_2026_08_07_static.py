"""Session canon 2026-08-07 — discoverability + product-framing guards.

These tests do not re-prove silicon. They keep the immune memory files and
Deck16 product framing from rotting out of the tree unnoticed.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "docs" / "canon" / "SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md"
SKILL = ROOT / ".claude" / "skills" / "k1-vj-session-discipline" / "SKILL.md"
SPEC_INDEX = ROOT / "docs" / "spec-index.md"
ARCH = ROOT / "docs" / "architecture" / "K1_DECK16_ARCHITECTURE_R1.md"


def test_session_canon_exists_and_names_hard_fails():
    text = CANON.read_text(encoding="utf-8")
    assert "HF-1" in text and "HF-13" in text
    assert "complementary discriminators" in text
    assert "K718" in text and "Tab5" in text
    assert "OR composition" in text


def test_discipline_skill_exists_and_points_at_canon():
    text = SKILL.read_text(encoding="utf-8")
    assert "k1-vj-session-discipline" in text
    assert "SESSION_CANON_2026-08-07" in text
    assert "HF-7" in text  # Tab5 vs K718


def test_spec_index_cites_session_canon():
    text = SPEC_INDEX.read_text(encoding="utf-8")
    assert "SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot" in text


def test_deck16_architecture_is_tab5_not_k718_product():
    text = ARCH.read_text(encoding="utf-8")
    assert "K1_DECK16_TAB5_BLE_R1" in text
    assert "Tab5" in text
    # Product surface must not re-elevate K718 as the controller endpoint.
    assert "K718" not in text or "retired" in text.lower() or "supersedes" in text.lower()
