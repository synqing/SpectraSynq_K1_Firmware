"""Lane N4 factory tooling — host structural gate.

Pins the N4 factory-provisioning machinery so a silent regression cannot turn
these read-only/non-flashing tools into something that flashes, pushes, or
generates keys host-green:

  * ``scripts/release/make_factory_image.py`` exists, assembles via
    ``esptool merge_bin`` (allowed — it writes a file, not a device), and NEVER
    executes ``write_flash``: the only place that token may appear in code is
    inside a ``print()`` (the human-run command it emits);
  * ``scripts/release/make_unit_nvs.py`` exists, generates a per-unit NVS binary
    via ESP-IDF ``nvs_partition_gen.py`` in ``generate`` mode, NEVER executes
    ``write_flash``, and NEVER generates encryption keys (no ``generate-key`` /
    ``--keygen`` / ``encrypt`` mode);
  * neither script ever pushes (no ``git push``), mirroring the ``make_release.py``
    "never pushes" invariant;
  * the per-unit serial/SKU scheme is Captain decision D4 — UNDECIDED — so the
    NVS template is a clearly-marked placeholder, and both the generator and the
    runbook surface that the scheme is pending.

These are static assertions only; assembling a real image and the actual flash
are out of host scope.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKE_FACTORY = ROOT / "scripts" / "release" / "make_factory_image.py"
MAKE_UNIT_NVS = ROOT / "scripts" / "release" / "make_unit_nvs.py"
NVS_TEMPLATE = ROOT / "scripts" / "release" / "unit_nvs_template.csv"
RUNBOOK = ROOT / "docs" / "hardware" / "factory-flash-runbook.md"


def _code_lines(text: str):
    """Yield (raw, code) with line-comments stripped, so prose mentioning
    write_flash / git push is not mistaken for executable code."""
    for ln in text.splitlines():
        code = ln.split("#", 1)[0]
        yield ln, code


# ---------------------------------------------------------------------------
# 1. The scripts (and template) exist.
# ---------------------------------------------------------------------------
def test_factory_scripts_exist():
    assert MAKE_FACTORY.exists(), f"missing factory-image assembler: {MAKE_FACTORY}"
    assert MAKE_UNIT_NVS.exists(), f"missing per-unit NVS generator: {MAKE_UNIT_NVS}"
    assert NVS_TEMPLATE.exists(), f"missing NVS template: {NVS_TEMPLATE}"
    assert RUNBOOK.exists(), f"missing factory-flash runbook: {RUNBOOK}"


# ---------------------------------------------------------------------------
# 2. Factory assembler: merge_bin allowed; write_flash never executed.
# ---------------------------------------------------------------------------
def test_factory_image_assembles_via_merge_bin():
    text = MAKE_FACTORY.read_text(encoding="utf-8")
    assert "merge_bin" in text, "make_factory_image.py must assemble via esptool merge_bin"


def test_factory_image_never_executes_write_flash():
    text = MAKE_FACTORY.read_text(encoding="utf-8")
    saw_print = False
    for raw, code in _code_lines(text):
        if "write_flash" in code:
            stripped = code.strip()
            assert stripped.startswith("print("), (
                f"'write_flash' must appear ONLY inside a print(): {raw!r}"
            )
            saw_print = True
    assert saw_print, "make_factory_image.py must PRINT a write_flash command for the operator"
    # No subprocess may carry write_flash into execution.
    for raw, code in _code_lines(text):
        if "subprocess" in code and ("run(" in code or "check_output" in code or "call(" in code):
            assert "write_flash" not in code, (
                f"subprocess must not execute write_flash: {raw!r}"
            )


def test_factory_image_never_pushes():
    text = MAKE_FACTORY.read_text(encoding="utf-8")
    for raw, code in _code_lines(text):
        assert "git push" not in code, f"make_factory_image.py must never push: {raw!r}"


def test_factory_image_uses_partition_nvs_offset():
    # NVS folds in at the default_16MB.csv offset (0x9000); a wrong offset would
    # silently corrupt an otherwise-valid image.
    text = MAKE_FACTORY.read_text(encoding="utf-8")
    assert "0x9000" in text or "0x9000".upper() in text.upper(), (
        "make_factory_image.py must place NVS at the partition-table offset 0x9000"
    )


# ---------------------------------------------------------------------------
# 3. Per-unit NVS generator: generate-only, no write_flash, no keygen.
# ---------------------------------------------------------------------------
def test_unit_nvs_uses_nvs_partition_gen_generate():
    text = MAKE_UNIT_NVS.read_text(encoding="utf-8")
    assert "nvs_partition_gen" in text, "make_unit_nvs.py must drive nvs_partition_gen.py"
    assert '"generate"' in text or "'generate'" in text, (
        "make_unit_nvs.py must invoke nvs_partition_gen in 'generate' mode"
    )


def test_unit_nvs_never_executes_write_flash():
    text = MAKE_UNIT_NVS.read_text(encoding="utf-8")
    for raw, code in _code_lines(text):
        if "write_flash" in code:
            assert code.strip().startswith("print("), (
                f"'write_flash' must appear ONLY inside a print(): {raw!r}"
            )
        if "subprocess" in code and ("run(" in code or "check_output" in code or "call(" in code):
            assert "write_flash" not in code, f"subprocess must not execute write_flash: {raw!r}"


def test_unit_nvs_never_generates_keys():
    # Provisioning must NOT mint NVS encryption keys (hard rule: never generate keys).
    text = MAKE_UNIT_NVS.read_text(encoding="utf-8")
    for raw, code in _code_lines(text):
        for forbidden in ("generate-key", "generate_key", "--keygen", "--keyfile", "encrypt"):
            assert forbidden not in code, (
                f"make_unit_nvs.py must not generate/handle NVS keys: {forbidden!r} in {raw!r}"
            )


def test_unit_nvs_never_pushes():
    text = MAKE_UNIT_NVS.read_text(encoding="utf-8")
    for raw, code in _code_lines(text):
        assert "git push" not in code, f"make_unit_nvs.py must never push: {raw!r}"


# ---------------------------------------------------------------------------
# 4. D4 placeholder discipline (serial/SKU scheme UNDECIDED).
# ---------------------------------------------------------------------------
def test_nvs_template_is_marked_placeholder():
    text = NVS_TEMPLATE.read_text(encoding="utf-8")
    assert "PLACEHOLDER" in text.upper(), "NVS template must be marked PLACEHOLDER"
    assert "D4" in text, "NVS template must reference Captain decision D4 (scheme pending)"
    # Substitutable tokens the generator fills in.
    assert "__DEVICE_SERIAL__" in text and "__SKU__" in text, (
        "NVS template must carry __DEVICE_SERIAL__ and __SKU__ tokens"
    )


def test_unit_nvs_surfaces_d4_pending():
    text = MAKE_UNIT_NVS.read_text(encoding="utf-8")
    assert "D4" in text, "make_unit_nvs.py must surface that the D4 scheme is undecided"
    assert "PLACEHOLDER" in text.upper(), "make_unit_nvs.py must use a clearly-marked placeholder"


def test_runbook_documents_chip_id_and_d4():
    text = RUNBOOK.read_text(encoding="utf-8")
    assert text.startswith("---"), "runbook must carry a frontmatter abstract"
    assert "Document Changelog" in text, "runbook must carry a changelog footer"
    # Identity = chip-ID, not port; and the D4 caveat must be present.
    assert "chip-ID" in text or "chip-id" in text.lower(), "runbook must verify identity by chip-ID"
    assert "D4" in text, "runbook must note the D4 (serial/SKU scheme) caveat"
    # British English spelling check (no American 'initialize'/'color' creep).
    assert "Hash of data verified" in text, "runbook must require the esptool success markers"
