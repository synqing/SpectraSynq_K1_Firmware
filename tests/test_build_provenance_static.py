"""Lane N5 build-provenance — host structural gate.

Pins the N5 release-engineering machinery so a silent regression cannot land
host-green:

  * the PlatformIO pre-script ``scripts/platformio/k1_build_provenance.py``
    exists, injects the three provenance defines, and is fail-soft (degrades to
    "unknown" rather than failing the build when git is unavailable);
  * it is registered under ``[env:k1_hardware]`` ``extra_scripts`` *in addition
    to* the existing src-includes + upload-guard pre-scripts (append, not
    replace — every derived env extends k1_hardware, so all inherit it);
  * the serial ``build`` command prints the provenance, guarding each define
    with ``#ifdef`` + a default, and is wired into the X-macro command table;
  * the release script ``scripts/release/make_release.py`` exists, contains NO
    ``git push``, and only PRINTS the ``git tag`` command (never executes a tag
    or push) — tag creation is Captain-gated.

These are static assertions only; the runtime provenance string and the actual
tag cut are out of host scope.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "scripts" / "platformio" / "k1_build_provenance.py"
PLATFORMIO_INI = ROOT / "platformio.ini"
SERIAL_MENU = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.h"
SERIAL_MENU_CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.cpp"
CMD_TABLE = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_cmd_table.def"
MAKE_RELEASE = ROOT / "scripts" / "release" / "make_release.py"

PROVENANCE_DEFINES = ("K1_BUILD_GIT_HASH", "K1_BUILD_EPOCH", "K1_BUILD_ENV")


def _serial_menu_surface() -> str:
    return SERIAL_MENU.read_text(encoding="utf-8") + "\n" + SERIAL_MENU_CPP.read_text(encoding="utf-8")


def _k1_hardware_section(ini_text: str) -> str:
    """Return the body of [env:k1_hardware] up to the next section header."""
    m = re.search(r"^\[env:k1_hardware\]\s*$", ini_text, re.MULTILINE)
    assert m, "platformio.ini has no [env:k1_hardware] section"
    rest = ini_text[m.end():]
    nxt = re.search(r"^\[", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


# ---------------------------------------------------------------------------
# 1. The pre-script exists and does its job (inject + fail-soft).
# ---------------------------------------------------------------------------
def test_provenance_prescript_exists():
    assert PROVENANCE.exists(), f"missing provenance pre-script: {PROVENANCE}"


def test_provenance_prescript_injects_all_three_defines():
    text = PROVENANCE.read_text(encoding="utf-8")
    assert "CPPDEFINES" in text, "pre-script must append CPPDEFINES"
    for name in PROVENANCE_DEFINES:
        assert name in text, f"pre-script does not inject {name}"
    # git hash sourced from rev-parse --short
    assert "rev-parse" in text and "--short" in text, "git short-hash not read via rev-parse --short"


def test_provenance_prescript_is_fail_soft():
    text = PROVENANCE.read_text(encoding="utf-8")
    # Must degrade to "unknown" on any git failure and never raise out of the hook.
    assert "unknown" in text, "pre-script must fall back to 'unknown' when git is unavailable"
    assert "except" in text, "pre-script must catch git failures (try/except), never fail the build"


# ---------------------------------------------------------------------------
# 2. Registered under k1_hardware extra_scripts (appended, not replacing).
# ---------------------------------------------------------------------------
def test_provenance_registered_in_k1_hardware_extra_scripts():
    section = _k1_hardware_section(PLATFORMIO_INI.read_text(encoding="utf-8"))
    assert "extra_scripts" in section, "[env:k1_hardware] has no extra_scripts"
    assert "k1_build_provenance.py" in section, (
        "k1_build_provenance.py not registered in k1_hardware extra_scripts"
    )
    # Append, not replace: the pre-existing pre-scripts must still be present.
    assert "k1_src_includes.py" in section, "src-includes pre-script was dropped"
    assert "k1_upload_guard.py" in section, "upload-guard pre-script was dropped"


# ---------------------------------------------------------------------------
# 3. Serial `build` provenance print exists and is define-guarded.
# ---------------------------------------------------------------------------
def test_serial_build_command_prints_provenance():
    text = _serial_menu_surface()
    assert "void cmd_build()" in text, "serial surface has no cmd_build() handler"
    # Build line must surface FIRMWARE_VERSION + all three provenance defines.
    assert "FIRMWARE_VERSION" in text
    for name in PROVENANCE_DEFINES:
        assert ("#ifdef %s" % name) in text, f"{name} not guarded by #ifdef in serial surface"


def test_serial_build_command_registered_in_table():
    table = CMD_TABLE.read_text(encoding="utf-8")
    assert re.search(r'SERIAL_CMD\(\s*"build"\s*,.*cmd_build', table), (
        "build command not wired to cmd_build in serial_cmd_table.def"
    )


def test_version_command_left_untouched():
    # cmd_version output is locked by host goldens; provenance must not change it.
    text = _serial_menu_surface()
    assert 'USBSerial.print("VERSION: ")' in text, "cmd_version VERSION line must remain intact"


# ---------------------------------------------------------------------------
# 4. Release script: read-only, print-only, no push, no executed tag.
# ---------------------------------------------------------------------------
def _code_lines(text: str):
    """Lines with line-comments stripped, so prose mentioning git push/tag is
    not mistaken for executable code."""
    for ln in text.splitlines():
        code = ln.split("#", 1)[0]
        yield ln, code


def test_make_release_exists():
    assert MAKE_RELEASE.exists(), f"missing release script: {MAKE_RELEASE}"


def test_make_release_never_pushes():
    text = MAKE_RELEASE.read_text(encoding="utf-8")
    for raw, code in _code_lines(text):
        assert "git push" not in code, f"make_release.py must never push: {raw!r}"


def test_make_release_only_prints_tag_command():
    text = MAKE_RELEASE.read_text(encoding="utf-8")
    saw_tag_print = False
    for raw, code in _code_lines(text):
        if "git tag" in code:
            stripped = code.strip()
            assert stripped.startswith("print("), (
                f"'git tag' must appear ONLY inside a print(): {raw!r}"
            )
            saw_tag_print = True
    assert saw_tag_print, "make_release.py must PRINT a 'git tag' command for the Captain"
    # subprocess must only ever drive read-only git (rev-parse), never tag/push.
    for raw, code in _code_lines(text):
        if "subprocess" in code and ("check_output" in code or "run(" in code or "call(" in code):
            assert "tag" not in code and "push" not in code, (
                f"subprocess must not execute git tag/push: {raw!r}"
            )
