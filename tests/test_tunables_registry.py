"""The runtime tunable registry must not drift from globals.h.

Captain's directive (2026-08-14): every AP/VP parameter retunable at runtime. A
hand-maintained list rots silently — someone adds a threshold, forgets the registry,
and the next person concludes "there's no setter for that" and burns a
rebuild-and-reflash cycle per value, which is exactly what happened this session.

So the table is generated, and this pins it: add a parameter without regenerating and
CI goes red.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "tools" / "gen_tunables.py"
OUT = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "k1_tunables_generated.h"
HDR = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "k1_tunables.h"
MENU = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.cpp"


def test_generated_registry_is_in_sync_with_globals():
    r = subprocess.run([sys.executable, str(GEN), "--check"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, (
        f"tunable registry is stale:\n{r.stdout}{r.stderr}\n"
        "run: python3 scripts/tools/gen_tunables.py"
    )


def test_registry_is_not_empty_and_count_matches_entries():
    text = OUT.read_text(encoding="utf-8")
    m = re.search(r"#define K1_TUNABLE_COUNT (\d+)", text)
    assert m, "K1_TUNABLE_COUNT missing"
    declared = int(m.group(1))
    entries = len(re.findall(r'^\s*\{\s*"', text, re.M))
    assert declared == entries, f"count {declared} != {entries} table rows"
    assert declared >= 20, (
        f"only {declared} parameters exposed — the registry has collapsed; "
        "check the name filter and the hot-path exclusion in gen_tunables.py"
    )


def test_setter_rejects_non_finite_and_reports_the_change():
    """A setter that silently no-ops is worse than one that refuses: the receipt must
    show the value actually moved, and NaN/Inf must never reach a live DSP parameter."""
    h = HDR.read_text(encoding="utf-8")
    assert "isfinite(v)" in h, "apply() does not reject NaN/Inf"
    assert "end == value" in h, "apply() does not reject unparseable text"
    menu = MENU.read_text(encoding="utf-8")
    blk = re.search(r'strcmp\(command_type, "tune"\) == 0.*?\n    \}', menu, re.S)
    assert blk, ":tune command not found in the serial dispatch chain"
    assert "before" in blk.group(0) and "->" in blk.group(0), (
        ":tune does not echo before -> after, so a no-op write would look successful"
    )


def test_tune_command_is_gated_out_of_shippable_envs():
    ini = (ROOT / "platformio.ini").read_text(encoding="utf-8")
    sections = {}
    for m in re.finditer(r"^\[env:([^\]]+)\]\n(.*?)(?=^\[|\Z)", ini, re.M | re.S):
        sections[m.group(1)] = m.group(2)

    def eff(env, seen=None):
        seen = seen or set()
        if env in seen or env not in sections:
            return set()
        seen.add(env)
        body = sections[env]
        unc = "\n".join(l for l in body.splitlines()
                        if not l.lstrip().startswith(("#", ";")))
        flags = set(re.findall(r"-D([A-Za-z0-9_]+)", unc))
        ext = re.search(r"^extends\s*=\s*env:(\S+)", body, re.M)
        if ext:
            flags |= eff(ext.group(1), seen)
        return flags

    leaks = sorted(e for e in ("k1_hardware", "k1_prod_im73d", "k1_bench_reference")
                   if e in sections and "K1_TUNABLE_REGISTRY_V1" in eff(e))
    assert leaks == [], (
        f"the live parameter-write surface reached shippable envs: {leaks} — "
        "promoting it to production is a deliberate decision, not a default"
    )
