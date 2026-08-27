"""State / profile / queue transitions executed on shipped colourlab-core.js."""
from __future__ import annotations

from colourlab_node import call_core, require_core

require_core()


def _reduce(actions, state=None):
    payload = {"op": "reduce", "actions": actions}
    if state is not None:
        payload["state"] = state
    return call_core(payload)


def _paint(mode="off", target="both", r=140, g=140, b=140, s=1.0, v=0.55, stops=0):
    return {
        "mode": mode,
        "target": target,
        "r": r,
        "g": g,
        "b": b,
        "s": s,
        "v": v,
        "stops": stops,
    }


def _tune(gr=1.0, gg=1.0, gb=1.0, gamma=1.0):
    return {"gain_r": gr, "gain_g": gg, "gain_b": gb, "gamma": gamma}


def test_controls_disabled_until_ready():
    st = call_core({"op": "initialState", "supported": True})
    assert st["connection"] == "disconnected"
    assert call_core({"op": "controlsEnabled", "state": st})["enabled"] is False
    st = _reduce(
        [
            {"type": "PROFILE_START"},
            {
                "type": "PROFILE_RESOLVED",
                "profile": call_core(
                    {"op": "resolveProfile", "chip_id": "9087A500", "look_env": "k1_main_rpl_im69d"}
                ),
            },
            {"type": "DEVICE_PAINT", "paint": _paint(), "seq": 1},
            {"type": "DEVICE_TUNE", "tune": _tune(), "seq": 1, "established_by": "tune_status"},
        ]
    )
    assert st["connection"] == "ready"
    assert call_core({"op": "controlsEnabled", "state": st})["enabled"] is True


def test_tune_status_never_establishes_slot15_or_baseline():
    st = _reduce(
        [
            {"type": "PROFILE_START"},
            {"type": "HYDRATE_START"},
            {"type": "DEVICE_PAINT", "paint": _paint(), "seq": 1},
            {"type": "DEVICE_TUNE", "tune": _tune(1.2, 1.0, 0.8, 2.2), "seq": 1},
        ]
    )
    assert st["slot15Content"]["status"] == "unknown"
    assert st["sessionBaseline"] is None
    assert st["confirmed"]["tune"]["gain_r"] == 1.2
    action = call_core({"op": "identityAction", "state": st})["action"]
    assert action == "set_identity"
    framing = call_core({"op": "previewFraming", "state": st, "channel": "primary"})
    assert framing["kind"] == "pre_lut"


def test_set_identity_then_revert_session_gating():
    st = _reduce(
        [
            {"type": "HYDRATE_START"},
            {"type": "DEVICE_PAINT", "paint": _paint(), "seq": 1},
            {"type": "DEVICE_TUNE", "tune": _tune(), "seq": 1},
            {
                "type": "DEVICE_TUNE",
                "tune": _tune(),
                "seq": 2,
                "established_by": "tune_reset",
            },
        ]
    )
    assert st["slot15Content"]["status"] == "known-this-session"
    assert st["slot15Content"]["established_by"] == "tune_reset"
    assert st["sessionBaseline"] == _tune()
    assert call_core({"op": "identityAction", "state": st})["action"] == "revert_session"

    st = _reduce(
        [
            {
                "type": "DEVICE_TUNE",
                "tune": _tune(1.5, 1.0, 1.0, 1.0),
                "seq": 3,
                "established_by": "tune_gain",
            }
        ],
        state=st,
    )
    assert st["sessionBaseline"] == _tune()
    assert st["confirmed"]["tune"]["gain_r"] == 1.5
    assert st["persistence"] == "dirty"


def test_reset_is_not_revert_session():
    consts = call_core({"op": "constants"})
    reset = call_core({"op": "serializeNamed", "fn": "tuneReset"})["line"]
    revert = call_core(
        {
            "op": "serializeNamed",
            "fn": "revertSession",
            "args": [_tune(1.1, 0.9, 1.0, 2.2)],
        }
    )["line"]
    identity = call_core({"op": "serializeNamed", "fn": "setIdentity"})["line"]
    assert reset == ":tune_reset"
    assert identity == ":tune_reset"
    assert revert == [":tune_gain=1.1,0.9,1", ":tune_gamma=2.2"]
    assert reset not in revert
    assert consts["COMMANDS"].count("tune_reset") == 1


def test_failed_save_stays_dirty():
    st = _reduce(
        [
            {
                "type": "DEVICE_TUNE",
                "tune": _tune(1.1, 1.0, 1.0, 1.0),
                "seq": 1,
                "established_by": "tune_gain",
            },
            {"type": "SAVE_START"},
            {"type": "DEVICE_SAVE_FAIL"},
        ]
    )
    assert st["persistence"] == "save-failed"
    assert st["slot15Content"]["status"] == "known-this-session"


def test_timeout_never_promotes_draft():
    st = call_core({"op": "initialState", "supported": True})
    st = _reduce(
        [
            {"type": "DRAFT_TUNE", "values": {"gain_r": 1.8}},
            {"type": "COMMAND_TIMEOUT", "command": "tune_gain"},
        ],
        state=st,
    )
    assert st["confirmed"]["tune"] is None
    assert st["draft"]["tune"]["gain_r"] == 1.8
    assert st["needsResync"] is True


def test_stale_reply_cannot_overwrite_newer_confirmed():
    st = _reduce(
        [
            {"type": "DEVICE_PAINT", "paint": _paint("solid"), "seq": 2},
            {"type": "DEVICE_PAINT", "paint": _paint("card"), "seq": 1},
        ]
    )
    assert st["confirmed"]["paint"]["mode"] == "solid"


def test_reconnect_discards_slot15_knowledge():
    st = _reduce(
        [
            {
                "type": "DEVICE_TUNE",
                "tune": _tune(1.4, 1.0, 1.0, 1.0),
                "seq": 1,
                "established_by": "tune_gain",
            },
            {"type": "PROFILE_START"},
        ]
    )
    assert st["connection"] == "profiling"
    assert st["slot15Content"]["status"] == "unknown"
    assert st["sessionBaseline"] is None
    assert st["confirmed"]["paint"] is None


def test_verified_and_unverified_profiles():
    main = call_core(
        {"op": "resolveProfile", "chip_id": "9087A500", "look_env": "k1_main_rpl_im69d"}
    )
    assert main["identity_status"] == "verified"
    assert main["primary_led_count"] == 160
    assert main["both_scale_enabled"] is True
    assert main["slot15_supported"] is True
    assert call_core({"op": "showTune", "profile": main})["show"] is True
    assert call_core({"op": "showBothScale", "profile": main})["show"] is True

    bench = call_core(
        {
            "op": "resolveProfile",
            "chip_id": "B489A500",
            "look_env": "k1_bench_im69d_led150",
        }
    )
    assert bench["identity_status"] == "verified"
    assert bench["primary_led_count"] == 150
    assert bench["both_scale_enabled"] is False
    assert bench["slot15_supported"] is False
    assert call_core({"op": "showTune", "profile": bench})["show"] is False
    assert call_core({"op": "showBothScale", "profile": bench})["show"] is False

    unknown = call_core(
        {"op": "resolveProfile", "chip_id": "DEADBEEF", "look_env": "k1_mystery"}
    )
    assert unknown["identity_status"] == "unverified"
    assert unknown["exact_parity"] is False


def test_device_effective_requires_known_slot15_and_active_look_15():
    st = _reduce(
        [
            {
                "type": "DEVICE_TUNE",
                "tune": _tune(),
                "seq": 1,
                "established_by": "tune_gain",
            },
            {"type": "LOOK_STATUS", "look": {"slot": 15, "sec": "inherit"}},
        ]
    )
    framing = call_core({"op": "previewFraming", "state": st, "channel": "primary"})
    assert framing["kind"] == "device_effective"
    st["activeLookPrimary"] = 0
    framing = call_core({"op": "previewFraming", "state": st, "channel": "primary"})
    assert framing["kind"] == "simulate_session"


def test_stop_output_discards_queued_mutations_and_jumps():
    paint_reply = {
        "kind": "paint",
        "mode": "off",
        "target": "both",
        "r": 140,
        "g": 140,
        "b": 140,
        "s": 1.0,
        "v": 0.55,
        "stops": 0,
    }
    out = call_core(
        {
            "op": "queue",
            "steps": [
                {"enqueue": {"cmd": "tune_gain", "line": ":tune_gain=1.1,1,1"}},
                {"enqueue": {"cmd": "paint", "line": ":paint=solid"}},
                {"enqueue": {"cmd": "paint_sv", "line": ":paint_sv=0.5,0.5"}},
                {"priorityStop": True},
                {"event": paint_reply},
            ],
        }
    )
    assert ":paint=off" in out["sent"]
    assert ":paint=solid" not in out["sent"]
    assert ":paint_sv=0.5,0.5" not in out["sent"]
    assert any(s.get("followUp") == ":paint_status" for s in out["settled"])
    assert out["queued"] == ["paint_status"] or out["inFlight"] == "paint_status"


def test_stop_timeout_surfaces_output_state_unknown():
    out = call_core(
        {
            "op": "queue",
            "safetyTimeoutMs": 800,
            "steps": [
                {"priorityStop": True},
                {"advance": 800},
            ],
        }
    )
    timeouts = [s for s in out["settled"] if s["outcome"] == "timeout"]
    assert timeouts
    assert timeouts[0]["warning"] == "output state unknown"
    assert timeouts[0]["priority"] is True


def test_disconnect_shutdown_requires_this_turn_paint_off():
    stale = call_core(
        {
            "op": "classifyDisconnectShutdown",
            "hadActivePaint": True,
            "inFlightAtStart": False,
            "stopOutcome": None,
            "paintModeFromReply": None,
        }
    )
    assert stale["claim"] == "unknown"
    assert stale["paintStopped"] is False
    assert stale["outputUnknown"] is True

    confirmed = call_core(
        {
            "op": "classifyDisconnectShutdown",
            "hadActivePaint": True,
            "inFlightAtStart": True,
            "stopOutcome": "ok",
            "paintModeFromReply": "off",
        }
    )
    assert confirmed["claim"] == "confirmed-off"
    assert confirmed["paintStopped"] is True
    assert confirmed["outputUnknown"] is False

    timed_out = call_core(
        {
            "op": "classifyDisconnectShutdown",
            "hadActivePaint": True,
            "inFlightAtStart": True,
            "stopOutcome": "timeout",
            "paintModeFromReply": None,
        }
    )
    assert timed_out["claim"] == "unknown"
    assert timed_out["outputUnknown"] is True
    assert timed_out["paintStopped"] is False

    idle = call_core(
        {
            "op": "classifyDisconnectShutdown",
            "hadActivePaint": False,
            "inFlightAtStart": False,
            "stopOutcome": None,
            "paintModeFromReply": None,
        }
    )
    assert idle["claim"] == "already-idle"
    assert idle["paintStopped"] is True
    assert idle["outputUnknown"] is False

    wrong_mode = call_core(
        {
            "op": "classifyDisconnectShutdown",
            "hadActivePaint": True,
            "stopOutcome": "ok",
            "paintModeFromReply": "solid",
        }
    )
    assert wrong_mode["claim"] == "unknown"
    assert wrong_mode["outputUnknown"] is True


def test_disconnected_records_shutdown_not_stale_paint():
    st = _reduce(
        [
            {"type": "DEVICE_PAINT", "paint": _paint("solid"), "seq": 1},
            {
                "type": "DISCONNECTED",
                "shutdown": "unknown",
                "paintStopped": False,
                "outputUnknown": True,
                "paintMayBeActive": True,
            },
        ]
    )
    assert st["connection"] == "disconnected"
    assert st["lastShutdown"] == "unknown"
    assert st["outputStateUnknown"] is True
    assert st["paintMayBeActive"] is True
    assert st["confirmed"]["paint"] is None

    idle = _reduce(
        [
            {
                "type": "DISCONNECTED",
                "shutdown": "already-idle",
                "paintStopped": True,
                "outputUnknown": False,
            }
        ]
    )
    assert idle["lastShutdown"] == "already-idle"
    assert idle["outputStateUnknown"] is False
    assert idle["paintMayBeActive"] is False


def test_persist_leave_state_cannot_claim_restore_without_authority():
    lying = call_core(
        {
            "op": "classifyPersistLeaveState",
            "preTestLutStatus": "unknown",
            "leaveAction": "prior-restored",
            "savedTune": {"gain_r": 1.2, "gain_g": 1.0, "gain_b": 0.8, "gamma": 2.2},
            "rebootResult": "slot-15 unknown after reconnect",
        }
    )
    assert lying["claim"] == "invalid-restore"
    assert lying["restored"] is False
    assert lying["priorReconstructable"] is False

    left_identity = call_core(
        {
            "op": "classifyPersistLeaveState",
            "preTestLutStatus": "unknown",
            "leaveAction": "identity-saved",
            "savedTune": {"gain_r": 1.0, "gain_g": 1.0, "gain_b": 1.0, "gamma": 1.0},
            "rebootResult": "TUNE identity; Set Identity offered",
        }
    )
    assert left_identity["claim"] == "identity-saved"
    assert left_identity["restored"] is False
    assert left_identity["leaveState"] == "identity"

    dirty = call_core(
        {
            "op": "classifyPersistLeaveState",
            "preTestLutStatus": "unknown",
            "leaveAction": "test-curve-left",
            "savedTune": {"gain_r": 1.4, "gain_g": 1.0, "gain_b": 1.0, "gamma": 2.0},
        }
    )
    assert dirty["claim"] == "test-curve-left"
    assert dirty["leaveState"] == "verification-curve"

    honest = call_core(
        {
            "op": "classifyPersistLeaveState",
            "preTestLutStatus": "known-this-session",
            "leaveAction": "prior-restored",
            "savedTune": {"gain_r": 1.1, "gain_g": 1.0, "gain_b": 1.0, "gamma": 1.0},
        }
    )
    assert honest["claim"] == "prior-restored"
    assert honest["restored"] is True


def test_serialize_commands_use_colon_prefix():
    line = call_core({"op": "serialize", "name": "paint", "data": "card"})["line"]
    assert line == ":paint=card"
    bare = call_core({"op": "serialize", "name": "paint_status"})["line"]
    assert bare == ":paint_status"
    stops = call_core(
        {
            "op": "serializeNamed",
            "fn": "paintStops",
            "args": [[[255, 255, 255]] * 8],
        }
    )["line"]
    data = stops.split("=", 1)[1]
    assert len(data) < 159
    assert stops.startswith(":paint_stops=")
