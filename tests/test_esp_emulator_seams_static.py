"""Static ratchets for the emulator replay seams (R3, 20 October 2026).

Each rule below cost a real failure in the R3 session. The full inventory is
/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-ESP-Emulator/docs/LESSONS.md
(F12, F14, F15, F26). They keep long replays deterministic and keep host oracles
compiling. Every rule is also run against a planted violation, so it is shown to go red.

Rules
1. Every reference to the fixture (include or k1_emu_fixture_* call) outside the
   fixture's own files sits inside an `#if`/`#ifdef` that names K1_EMU_FIXTURE.
   (The golden-master host oracle compiles serial_cmd_handlers.cpp; an unguarded
   include pulled esp_err.h onto the host.)
2. Every esp_timer_get_time() in the render loop (led_thread) is either a perf/
   diagnostic measurement, inside a non-shipping harness branch, or the non-fixture
   side of a fixture seam. A new functional wall-clock read makes replays depend
   on emulation speed and host load.
3. esp_random() appears only where it is allowed: the non-fixture side of
   random_float(), and two boot nonces. Product randomness must go through
   random_float(), which the fixture seeds.
4. The render-loop seams exist: render-loop start notification before the frame
   loop, frame time sampled after the fixture accepts a generation, LED_FPS on that
   time, the producer holding hop 0 until the render loop runs, random_float() seeded.
5. No renderer ages the producer's esp_timer-stamped frame fields
   (last_onset_time_us, last_beat_time_us). If one ever does, it needs an
   application-time seam first.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
INO = FW / "SPECTRASYNQ_K1_FIRMWARE.ino"

FIXTURE_OWN_FILES = {"audio/k1_emu_fixture.cpp", "audio/k1_emu_fixture.h", "audio/k1_emu_clock_force.h"}
SOURCE_SUFFIXES = {".h", ".hpp", ".c", ".cpp", ".ino"}

# Render-loop wall-clock reads that are measurement only, never functional.
PERF_PATTERNS = (
    r"\bvp_perf", r"K1_TRACE_COUNTER", r"\bvp_render_elapsed_us\b", r"\bvpml_render_elapsed_us\b",
    r"\bpark_now_us\b",
)
# Branches compiled only in non-shipping harness envs.
HARNESS_GUARDS = ("ENABLE_MOTION_PROBE", "ENABLE_VP_MOTION_LAB", "ENABLE_VP_PERF_AUDIT")
# esp_random() is allowed only here (file -> reason).
ESP_RANDOM_ALLOWED = {
    "system/utilities.h": "non-fixture branch of random_float()",
    "serial/serial_menu.h": "boot nonce",
    "serial/k1_scheduling_trace_telemetry.cpp": "trace epoch nonce",
}


# ---------------------------------------------------------------------------
# A small preprocessor-region tracker: for each line, the enclosing conditions
# and whether each is in its #else branch. Good enough for this codebase's
# #if/#ifdef/#ifndef/#elif/#else/#endif usage.
# ---------------------------------------------------------------------------

def regions(lines: list[str]) -> list[list[tuple[str, bool]]]:
    stack: list[list] = []
    out = []
    for raw in lines:
        s = raw.strip()
        m = re.match(r"#\s*(ifdef|ifndef|if|elif|else|endif)\b(.*)", s)
        if m:
            kind, rest = m.group(1), m.group(2).strip()
            if kind in ("if", "ifdef", "ifndef"):
                cond = ("!" if kind == "ifndef" else "") + rest
                stack.append([cond, False])
            elif kind == "elif" and stack:
                stack[-1] = [rest, False]
            elif kind == "else" and stack:
                stack[-1][1] = True
            elif kind == "endif" and stack:
                stack.pop()
        out.append([(c, e) for c, e in stack])
    return out


def _guarded_by_fixture(frames: list[tuple[str, bool]]) -> bool:
    """Inside a branch that is only compiled when K1_EMU_FIXTURE is defined."""
    for cond, in_else in frames:
        positive = "K1_EMU_FIXTURE" in cond and not cond.startswith("!") and "!defined(K1_EMU_FIXTURE)" not in cond
        if positive and not in_else:
            return True
        if cond.startswith("!") and "K1_EMU_FIXTURE" in cond and in_else:
            return True
    return False


def _fixture_else_branch(frames: list[tuple[str, bool]]) -> bool:
    """The non-fixture side of a fixture seam (the fixture has its own branch)."""
    return any("K1_EMU_FIXTURE" in c and not c.startswith("!") and e for c, e in frames)


def _harness_branch(frames: list[tuple[str, bool]]) -> bool:
    return any(any(g in c for g in HARNESS_GUARDS) and not e for c, e in frames)


# ---------------------------------------------------------------------------
# Rule checks (pure functions over text, so planted violations can be fed in)
# ---------------------------------------------------------------------------

def unguarded_fixture_refs(rel: str, text: str) -> list[str]:
    if rel in FIXTURE_OWN_FILES:
        return []
    lines = text.splitlines()
    bad = []
    for i, (line, frames) in enumerate(zip(lines, regions(lines)), 1):
        code = line.split("//", 1)[0]
        if ("k1_emu_fixture.h" in code and "#include" in code) or re.search(r"\bk1_emu_fixture_\w+\s*\(", code):
            if not _guarded_by_fixture(frames):
                bad.append(f"{rel}:{i}: {line.strip()[:100]}")
    return bad


def led_thread_span(lines: list[str]) -> tuple[int, int]:
    start = next(i for i, l in enumerate(lines) if l.startswith("void led_thread"))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("}"))
    return start, end


def functional_wall_clock_reads(ino_text: str) -> list[str]:
    lines = ino_text.splitlines()
    start, end = led_thread_span(lines)
    regs = regions(lines)
    bad = []
    seam = "vp_frame_start_us = (int64_t)k1_emu_fixture_app_us();" in ino_text
    for i in range(start, end):
        line = lines[i]
        code = line.split("//", 1)[0]
        if "esp_timer_get_time()" not in code:
            continue
        frames = regs[i]
        if any(re.search(p, code) for p in PERF_PATTERNS):
            continue
        if _harness_branch(frames) or _fixture_else_branch(frames):
            continue
        if re.match(r"\s*int64_t vp_frame_start_us = esp_timer_get_time\(\);", code) and seam:
            continue  # overridden by the fixture's application-time seam after accept
        if "vp_render_start_us = vp_frame_start_us" in code:
            continue
        bad.append(f"SPECTRASYNQ_K1_FIRMWARE.ino:{i + 1}: {line.strip()[:110]}")
    return bad


def disallowed_esp_random(rel: str, text: str) -> list[str]:
    if rel.startswith("diag/") or rel in FIXTURE_OWN_FILES:
        return []
    lines = text.splitlines()
    bad = []
    for i, (line, frames) in enumerate(zip(lines, regions(lines)), 1):
        code = line.split("//", 1)[0]
        if not re.search(r"\besp_random\s*\(", code):
            continue
        if rel not in ESP_RANDOM_ALLOWED:
            bad.append(f"{rel}:{i}: {line.strip()[:100]}")
        elif rel == "system/utilities.h" and not _fixture_else_branch(frames):
            bad.append(f"{rel}:{i}: esp_random() outside the non-fixture branch of random_float()")
    return bad


def missing_render_seams(ino_text: str, fixture_cpp: str, utilities_h: str) -> list[str]:
    missing = []
    lines = ino_text.splitlines()
    start, end = led_thread_span(lines)
    body = "\n".join(lines[start:end])
    loop_at = body.find("while (true)")
    note_at = body.find("k1_emu_fixture_note_render_loop();")
    if note_at < 0 or loop_at < 0 or note_at > loop_at:
        missing.append("led_thread must call k1_emu_fixture_note_render_loop() before its frame loop")
    accept = body.find("k1_emu_fixture_note_consumed(vp_frame);")
    sample = body.find("vp_frame_start_us = (int64_t)k1_emu_fixture_app_us();")
    if accept < 0 or sample < 0 or sample < accept:
        missing.append("frame time must be sampled (vp_frame_start_us = app time) right after the fixture accepts a generation")
    if "1000000.0 / (double)(vp_frame_start_us - (int64_t)last_frame_us)" not in body:
        missing.append("LED_FPS must use the sampled frame time under the fixture")
    if "while (!s_render_ready)" not in fixture_cpp:
        missing.append("the fixture must hold hop 0 until the render loop runs (s_render_ready)")
    m = re.search(r"inline float random_float\(\)\s*\{(.*?)\n\}", utilities_h, re.S)
    if not m or "K1_EMU_FIXTURE" not in m.group(1) or "k1_emu_fixture_random_u32" not in m.group(1):
        missing.append("random_float() must draw from k1_emu_fixture_random_u32() under K1_EMU_FIXTURE")
    return missing


def renderer_ages_producer_stamps(files: dict[str, str]) -> list[str]:
    bad = []
    for rel, text in files.items():
        if rel.split("/")[0] in {"visual", "effects", "director"}:
            for i, line in enumerate(text.splitlines(), 1):
                if re.search(r"\blast_(onset|beat)_time_us\b", line.split("//", 1)[0]):
                    bad.append(f"{rel}:{i}: {line.strip()[:100]}")
    return bad


def _sources() -> dict[str, str]:
    out = {}
    for p in FW.rglob("*"):
        if p.suffix in SOURCE_SUFFIXES and p.is_file():
            out[str(p.relative_to(FW))] = p.read_text(errors="replace")
    return out


# ---------------------------------------------------------------------------
# Tests on the real source
# ---------------------------------------------------------------------------

def test_fixture_references_are_guarded():
    bad = [b for rel, text in _sources().items() for b in unguarded_fixture_refs(rel, text)]
    assert not bad, "fixture references outside #ifdef K1_EMU_FIXTURE (breaks host oracles):\n" + "\n".join(bad)


def test_render_loop_has_no_new_functional_wall_clock_read():
    bad = functional_wall_clock_reads(INO.read_text())
    assert not bad, (
        "new esp_timer_get_time() in led_thread. If it is functional (affects pixels or state), give it a "
        "fixture application-time seam (see ESP-Emulator docs/LESSONS.md F14); if it is a measurement, name it vp_perf_* / "
        "K1_TRACE_COUNTER:\n" + "\n".join(bad))


def test_esp_random_only_where_allowed():
    bad = [b for rel, text in _sources().items() for b in disallowed_esp_random(rel, text)]
    assert not bad, ("esp_random() outside its allowlist. Product randomness must use random_float(), which the "
                     "emulator fixture seeds (ESP-Emulator docs/LESSONS.md F15):\n" + "\n".join(bad))


def test_render_loop_seams_exist():
    missing = missing_render_seams(INO.read_text(), (FW / "audio/k1_emu_fixture.cpp").read_text(),
                                   (FW / "system/utilities.h").read_text())
    assert not missing, "\n".join(missing)


def test_no_renderer_ages_producer_timestamps():
    bad = renderer_ages_producer_stamps(_sources())
    assert not bad, ("a renderer reads esp_timer-stamped producer fields; in the replay those are emulator wall "
                     "time, not application time. Add a fixture seam first:\n" + "\n".join(bad))


# ---------------------------------------------------------------------------
# Planted violations: each rule must go red
# ---------------------------------------------------------------------------

def test_planted_unguarded_include_goes_red():
    text = '#include "serial_tx.h"\n#include "../audio/k1_emu_fixture.h"\nvoid f() { k1_emu_fixture_note_save("x", true); }\n'
    assert len(unguarded_fixture_refs("serial/serial_cmd_handlers.cpp", text)) == 2
    guarded = "#ifdef K1_EMU_FIXTURE\n" + text + "#endif\n"
    assert unguarded_fixture_refs("serial/serial_cmd_handlers.cpp", guarded) == []
    negated = "#ifndef K1_EMU_FIXTURE\n" + text + "#endif\n"
    assert len(unguarded_fixture_refs("serial/serial_cmd_handlers.cpp", negated)) == 2


def test_planted_wall_clock_read_goes_red():
    real = INO.read_text()
    planted = real.replace("      k1_effect_queue_frame_tick(uint32_t(vp_frame_start_us / 1000));",
                           "      k1_effect_queue_frame_tick(uint32_t(esp_timer_get_time() / 1000));", 1)
    assert planted != real
    assert functional_wall_clock_reads(planted), "a functional esp_timer read in led_thread was not detected"


def test_planted_esp_random_goes_red():
    assert disallowed_esp_random("effects/light_mode_comet.cpp", "float r = esp_random() / 1.0f;\n")
    util = (FW / "system/utilities.h").read_text()
    stripped = re.sub(r"#ifdef K1_EMU_FIXTURE.*?#else\n(.*?)#endif\n", r"\1", util, count=1, flags=re.S)
    assert stripped != util
    assert disallowed_esp_random("system/utilities.h", stripped), "unseeded random_float() was not detected"


def test_planted_missing_seams_go_red():
    ino = INO.read_text()
    fx = (FW / "audio/k1_emu_fixture.cpp").read_text()
    util = (FW / "system/utilities.h").read_text()
    assert missing_render_seams(ino.replace("k1_emu_fixture_note_render_loop();", "/* removed */"), fx, util)
    assert missing_render_seams(ino.replace("vp_frame_start_us = (int64_t)k1_emu_fixture_app_us();", "/* removed */"), fx, util)
    assert missing_render_seams(ino, fx.replace("while (!s_render_ready)", "while (false)"), util)
    assert missing_render_seams(ino, fx, util.replace("k1_emu_fixture_random_u32", "esp_random"))


def test_planted_renderer_stamp_read_goes_red():
    assert renderer_ages_producer_stamps({"effects/x.cpp": "uint32_t age = micros() - f.last_beat_time_us;\n"})
