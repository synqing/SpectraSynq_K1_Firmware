"""Report data records (schema ``k1-emu-report-data/1``) built from decoded captures.

The offline report (report.py) reads only these records. Native values are
carried exactly: each edge is the 960-byte packed wire in hex (per pixel
G16BE R16BE B16BE). Any 8-bit screen projection is the report's job and must
never feed equality or difference results.
"""

from __future__ import annotations

from emu_capture import Capture


def case_record(case_id: str, cap: Capture | None, *, status: str, reasons: list[str],
                run_id: str, profile: dict, initial_state: dict, window: dict,
                epoch_us: int | None, hop_samples: int, rate_hz: int, pcm: dict) -> dict:
    frames = []
    commands = []
    states = []
    if cap is not None:
        for f in cap.frames:
            s = cap.sidecars.get(f.index)
            frames.append({
                "index": f.index,
                "hop": None if s is None else s.processed // hop_samples - 1,
                "generation": None if s is None else s.generation,
                "admitted": None if s is None else s.admitted,
                "processed": None if s is None else s.processed,
                "app_us": None if s is None else s.app_us,
                "mode": f.mode,
                "limit_scale": None if s is None else s.limit_scale,
                "power_mw": None if s is None else s.power_mw,
                "A": f.A.hex(),
                "B": f.B.hex(),
            })
        results = cap.command_results
        for i, c in enumerate(cap.commands):
            res = results[i] if i < len(results) else {}
            commands.append({
                "hop": int(c.get("hop", -1)),
                "sample": int(c.get("sample", -1)),
                "text": c.get("text", ""),
                "rejected": res.get("rejected") == "1",
                "applied_generation": _applied_generation(cap, int(c.get("hop", -1))),
            })
        for st in cap.show_states:
            states.append({k: st.get(k) for k in ("gen", "when", "hop", "hex")})
    return {
        "case": case_id,
        "status": status,
        "reasons": reasons,
        "run_id": run_id,
        "profile": profile,
        "initial_state": initial_state,
        "window": window,
        "epoch_us": epoch_us,
        "hop_samples": hop_samples,
        "rate_hz": rate_hz,
        "pcm": pcm,
        "frames": frames,
        "commands": commands,
        "show_states": states,
    }


def _applied_generation(cap: Capture, hop: int) -> int | None:
    """First generation whose show-state readback follows the command's hop.

    A command at hop h is applied before hop h is processed, so the first
    publication that can carry it is generation h + 1. A queued change (for
    example a mode transition) lands at the first later shown state change.
    """
    for st in cap.show_states:
        if st.get("when") == "shown" and int(st.get("gen", 0)) >= hop + 1:
            return int(st["gen"])
    return None


def comparison_record(comp_id: str, kind: str, a: str, b: str, *, compatible: bool,
                      status: str, detail: str, strict: bool, label: str) -> dict:
    """kind: 'equal' (strict equivalence) or 'labelled' (intended difference)."""
    return {"id": comp_id, "kind": kind, "a": a, "b": b, "compatible": compatible,
            "status": status, "detail": detail, "strict": strict, "label": label}
