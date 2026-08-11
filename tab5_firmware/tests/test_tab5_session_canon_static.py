"""Keep the 2026-08-11 Tab5 lessons reachable and mechanically binding."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CANON = REPO_ROOT / "docs/canon/TAB5_SESSION_FAILURES_AND_ENGINEERING_CANON_2026-08-11.md"
AGENTS = REPO_ROOT / "tab5_firmware/AGENTS.md"
CLAUDE_SKILL = REPO_ROOT / ".claude/skills/tab5-embedded-ui-motion-gate/SKILL.md"
CODEX_SKILL = REPO_ROOT / ".codex/skills/tab5-embedded-ui-motion-gate/SKILL.md"
LIVE_SKILL = REPO_ROOT / ".claude/skills/k1-tab5-live-harness/SKILL.md"
FONT_DECLARATIONS = REPO_ROOT / "tab5_firmware/src/fonts/deck_fonts.h"


def test_canon_covers_every_session_failure_class():
    text = CANON.read_text(encoding="utf-8")
    for required in (
        "BLE_ERR_UNK_CONN_ID",
        "lv_inv_area",
        "loopTask",
        "68-control",
        "Queue loss",
        "CLAMPED/REJECTED",
        "100%",
        "PPA",
        "byte_swap",
        "one shared `PaletteFlowState`",
        "Circular 11-tap",
        "both Countach and Berkeley Mono source assets as TRIAL",
        "busy-work loops",
        "FULL_G3_FAULT_AND_ORDINARY_SOAK=NOT_VERIFIED",
        "shared framework package",
        "Rail A can block a release. It cannot pass Rail B.",
    ):
        assert required in text


def test_nested_agents_contract_routes_future_work_to_canon_and_motion_gate():
    text = AGENTS.read_text(encoding="utf-8")
    assert CANON.name in text
    assert "tab5-embedded-ui-motion-gate" in text
    assert "30:ed:a0:e0:c1:a0" in text
    assert "LVGL and confirmed-state mutation belong to loopTask only" in text
    assert "Captain eyes-on rejection reopens" in text


def test_motion_skill_has_trigger_only_frontmatter_and_two_rail_gate():
    text = CLAUDE_SKILL.read_text(encoding="utf-8")
    assert "description: >-\n  Use when" in text
    assert "## RED baseline" in text
    assert "## Two rails" in text
    assert "## Red-team mutants" in text
    assert "## OODA closeout" in text
    mirror = CODEX_SKILL.read_text(encoding="utf-8")
    assert "Read and follow that\ncanonical file completely" in mirror


def test_live_harness_skill_cannot_route_by_stale_port_memory():
    text = LIVE_SKILL.read_text(encoding="utf-8")
    assert "Never decide that a device is absent" in text
    assert "/dev/cu.usbmodem12401" in text
    assert "30:ed:a0:e0:c1:a0" in text
    assert "--verify-only" in text


def test_historical_g3_receipt_does_not_overclaim_full_gate_closure():
    receipt = REPO_ROOT / "docs/receipts/tab5-hardening-20260811/G3_SILICON_RELEASE_PROOF.md"
    text = receipt.read_text(encoding="utf-8")
    assert "WDT_RSSI_RECONNECT_REPAIR=PASS" in text
    assert "FULL_G3_FAULT_AND_ORDINARY_SOAK=NOT_VERIFIED" in text
    assert "earlier “lane closed” wording overreached" in text


def test_selected_trial_font_risk_covers_both_live_families():
    text = FONT_DECLARATIONS.read_text(encoding="utf-8")
    assert "Countach and Berkeley Mono" in text
    assert "TRIAL — bench evaluation flashes only" in text
