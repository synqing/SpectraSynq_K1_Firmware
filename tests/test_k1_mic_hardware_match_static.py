"""Static MIC/hardware-match guardrail — the E1 bench session's worst failure, encoded.

CANON: docs/K1_BENCH_HARDWARE_LESSONS.md §1. A probe env was built on the WRONG
mic base (k1_bench_reference_harness — SPH/pinmap, mic-LESS) and FLASHED to the
bench B489A500, whose physical mic is the IM73D122 PDM. The env lacked
`K1_MIC_IM73D_PDM_V1` → wrong mic driver → garbage/no audio. Recon had verified
compile + link + identity-guard + gate tests but NEVER the mic/hardware match, so
a GREEN BUILD masqueraded as a correct hardware config until Captain caught it
post-flash.

This gate makes the mic mismatch a RED at commit time (no toolchain, no device):
every PlatformIO env authorized (in k1_device_identities.json) for a chip whose
declared physical `mic` is IM73D must RESOLVE that chip's `mic_flag` in its
build_flags — EXCEPT the manifest's declared `mic_exempt_envs` (the legacy
SPH-compatible / GDFT reference-base envs retained only as `extends` bases, never
IM73D capture/flash targets).

Resolution is TEXT-only: it expands `${env:X.build_flags}` / `${env:X.build_unflags}`
interpolation down the `extends` chain and collects `-DMACRO` names. It is NOT a
full PlatformIO evaluation — it is the same class of static-manifest check as
tests/test_k1_upload_guard.py, sufficient to prove mic-flag presence/absence. The
on-device VERIFY of record remains `pio run -e <env> -t idedata | grep
K1_MIC_IM73D_PDM_V1` (docs/K1_BENCH_HARDWARE_LESSONS.md §1); this gate is the cheap
commit-time backstop so the mistake never reaches a flash.

Anti-gaming (Gate-Fα, mirrors test_k1_upload_guard_identity_static.py):
  * a synthetic mic-less env injected as authorized-and-not-exempt is FLAGGED —
    proves the checker is not theatre;
  * an env whose `extends` chain passes through the IM73D base can NEVER be
    exempted — you cannot silence a broken IM73D-derived env by listing it in
    mic_exempt_envs; the wrong-base defect still REDs the gate.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = ROOT / "platformio.ini"
MANIFEST = ROOT / "scripts" / "platformio" / "k1_device_identities.json"

# Human mic name -> the -D driver-select macro that env MUST resolve. Single
# source is the manifest's per-chip `mic_flag`; this map is the independent
# cross-check so a manifest typo (mic/mic_flag disagree) is itself caught.
MIC_NAME_TO_FLAG = {"IM73D122": "K1_MIC_IM73D_PDM_V1"}

_D_MACRO = re.compile(r"-D([A-Za-z_][A-Za-z0-9_]*)")
_INTERP = re.compile(r"\$\{env:([A-Za-z0-9_.]+)\.(build_flags|build_unflags)\}")


def parse_envs(text):
    """Parse platformio.ini into {env_name: {option: raw_multiline_value}}.

    Handles PlatformIO continuation lines (an option value spans following lines
    that are indented / blank-then-indented until the next `key =` or section).
    """
    envs = {}
    cur_env = None
    cur_key = None
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()
        m = re.match(r"\[env:([A-Za-z0-9_.]+)\]", stripped)
        if m:
            cur_env = m.group(1)
            envs[cur_env] = {}
            cur_key = None
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            cur_env = None
            cur_key = None
            continue
        if cur_env is None:
            continue
        if stripped.startswith(";"):  # full-line comment
            continue
        # New option?  key = value   (key is unindented-ish and has an '=')
        km = re.match(r"([A-Za-z0-9_.]+)\s*=(.*)$", line)
        if km and not line[:1].isspace():
            cur_key = km.group(1)
            envs[cur_env][cur_key] = km.group(2).strip()
            continue
        # Continuation of the current option value.
        if cur_key is not None and (line[:1].isspace() or stripped):
            envs[cur_env][cur_key] += "\n" + stripped
    return envs


def _expand(text, envs, kind, depth=0):
    """Recursively expand ${env:X.build_flags|build_unflags} interpolations."""
    if depth > 40 or not text:
        return text or ""

    def sub(mo):
        name, opt = mo.group(1), mo.group(2)
        val = envs.get(name, {}).get(opt, "")
        return _expand(val, envs, opt, depth + 1)

    return _INTERP.sub(sub, text)


def resolved_macros(env_name, envs):
    """The set of -D macro NAMES effective for `env_name`.

    Expands the env's own build_flags interpolation chain (which, by the repo
    idiom `${env:parent.build_flags}`, pulls inherited macros in), then falls
    back to `extends` inheritance if the env defines no build_flags of its own,
    then subtracts this env's build_unflags. Sufficient to decide mic-flag
    presence; not a byte-exact PlatformIO evaluation.
    """
    env = envs.get(env_name, {})
    bf = env.get("build_flags")
    if bf is not None:
        macros = set(_D_MACRO.findall(_expand(bf, envs, "build_flags")))
    else:
        parent = env.get("extends", "")
        parent = parent[len("env:"):] if parent.startswith("env:") else ""
        macros = resolved_macros(parent, envs) if parent else set()
    uf = env.get("build_unflags")
    if uf is not None:
        macros -= set(_D_MACRO.findall(_expand(uf, envs, "build_unflags")))
    return macros


def extends_chain(env_name, envs):
    """The list of ancestor env names via `extends` (excluding env_name)."""
    chain = []
    seen = set()
    cur = envs.get(env_name, {}).get("extends", "")
    while cur.startswith("env:"):
        name = cur[len("env:"):]
        if name in seen:
            break
        seen.add(name)
        chain.append(name)
        cur = envs.get(name, {}).get("extends", "")
    return chain


class MicHardwareMatchTest(unittest.TestCase):
    def setUp(self):
        self.envs = parse_envs(PLATFORMIO.read_text(encoding="utf-8"))
        self.data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        # Chips that declare a physical mic (and thus a required build flag).
        self.mic_chips = [
            a for a in self.data["authorized"] if a.get("mic_flag")
        ]

    def test_at_least_one_mic_chip_is_declared(self):
        # Guards against the manifest silently losing the mic declaration (which
        # would make this whole gate vacuously pass).
        self.assertTrue(
            self.mic_chips,
            "no authorized chip declares a `mic_flag`; the mic-match gate would "
            "be vacuous. B489A500 (bench, IM73D122) must declare it.",
        )

    def test_bench_chip_declares_im73d(self):
        bench = next(a for a in self.data["authorized"] if a["chip_id"] == "B489A500")
        self.assertEqual(bench.get("mic"), "IM73D122")
        self.assertEqual(bench.get("mic_flag"), "K1_MIC_IM73D_PDM_V1")
        # mic <-> mic_flag agreement (catches a manifest typo drift).
        self.assertEqual(MIC_NAME_TO_FLAG.get(bench["mic"]), bench["mic_flag"])

    def test_manifest_env_names_exist_in_platformio(self):
        # A stale env name in the manifest would make the gate check nothing for
        # that entry — catch it.
        for chip in self.mic_chips:
            for env_name in list(chip["envs"]) + list(chip.get("mic_exempt_envs", [])):
                self.assertIn(
                    env_name,
                    self.envs,
                    f"{chip['chip_id']}: manifest lists env '{env_name}' that is "
                    f"absent from platformio.ini",
                )

    def test_mic_exempt_envs_are_authorized_and_not_stale(self):
        for chip in self.mic_chips:
            authorized = set(chip["envs"])
            for env_name in chip.get("mic_exempt_envs", []):
                self.assertIn(
                    env_name,
                    authorized,
                    f"{chip['chip_id']}: mic_exempt_envs lists '{env_name}' which "
                    f"is not in this chip's authorized `envs` (stale exemption).",
                )

    def test_mic_exempt_envs_never_derive_from_the_mic_base(self):
        """Fault-evidence: an IM73D-derived env cannot be exempted.

        The exemption exists only for the legacy reference-base (SPH / GDFT)
        envs. If an env whose `extends` chain passes through the IM73D base
        (k1_bench_im73d) somehow lost the mic flag, that is a genuine defect and
        MUST NOT be silenceable by listing it here — otherwise the gate could be
        gamed exactly the way the original bug arose.
        """
        for chip in self.mic_chips:
            for env_name in chip.get("mic_exempt_envs", []):
                chain = extends_chain(env_name, self.envs)
                self.assertNotIn(
                    "k1_bench_im73d",
                    chain,
                    f"{chip['chip_id']}: '{env_name}' derives from the IM73D base "
                    f"(chain={chain}) and must not be mic-exempt — fix its flags, "
                    f"do not exempt it.",
                )

    def test_every_non_exempt_authorized_env_resolves_the_mic_flag(self):
        """THE guardrail. docs/K1_BENCH_HARDWARE_LESSONS.md §1."""
        for chip in self.mic_chips:
            flag = chip["mic_flag"]
            exempt = set(chip.get("mic_exempt_envs", []))
            for env_name in chip["envs"]:
                if env_name in exempt:
                    continue
                with self.subTest(chip=chip["chip_id"], env=env_name):
                    macros = resolved_macros(env_name, self.envs)
                    self.assertIn(
                        flag,
                        macros,
                        f"{chip['chip_id']} ({chip.get('mic')}): env '{env_name}' "
                        f"is authorized to FLASH this unit but its resolved "
                        f"build_flags do NOT define -D{flag}. A green build with "
                        f"the wrong mic driver produces garbage audio "
                        f"(docs/K1_BENCH_HARDWARE_LESSONS.md §1). Extend "
                        f"k1_bench_im73d (or add -D{flag}); do not flash this to "
                        f"the IM73D bench without it.",
                    )

    # ── anti-gaming ─────────────────────────────────────────────────────────
    def test_resolver_reads_the_real_flag_on_a_known_env(self):
        # Positive control: the IM73D base itself resolves the flag.
        self.assertIn(
            "K1_MIC_IM73D_PDM_V1", resolved_macros("k1_bench_im73d", self.envs)
        )
        # Negative control: the legacy reference base does NOT.
        self.assertNotIn(
            "K1_MIC_IM73D_PDM_V1", resolved_macros("k1_bench_reference", self.envs)
        )
        # Inheritance-through-interpolation works (child pulls the base flag).
        self.assertIn(
            "K1_MIC_IM73D_PDM_V1", resolved_macros("k1_bench_vp_probe", self.envs)
        )

    def test_gate_flags_a_synthetic_mic_less_target(self):
        """Inject the ORIGINAL bug shape and prove the checker catches it.

        A new probe env built on the mic-less reference-harness base, authorized
        for the IM73D bench, NOT exempted — exactly `k1_bench_vp_probe` before its
        fix. The checker must report it missing the mic flag.
        """
        envs = dict(self.envs)
        envs["k1_bench_bug_probe"] = {
            "extends": "env:k1_bench_reference_harness",
            "build_flags": "${env:k1_bench_reference_harness.build_flags}\n-DSOME_PROBE=1",
        }
        macros = resolved_macros("k1_bench_bug_probe", envs)
        self.assertNotIn(
            "K1_MIC_IM73D_PDM_V1",
            macros,
            "checker failed to detect a mic-less env — the gate is theatre",
        )
        # And it WOULD carry the flag once rebased onto the IM73D base (the fix).
        envs["k1_bench_bug_probe"]["extends"] = "env:k1_bench_im73d"
        envs["k1_bench_bug_probe"]["build_flags"] = (
            "${env:k1_bench_im73d.build_flags}\n-DSOME_PROBE=1"
        )
        self.assertIn(
            "K1_MIC_IM73D_PDM_V1", resolved_macros("k1_bench_bug_probe", envs)
        )

    def test_gate_flags_an_env_that_unflags_the_mic(self):
        """A build_unflags that strips the mic flag must be caught too."""
        envs = dict(self.envs)
        envs["k1_bench_unmic_probe"] = {
            "extends": "env:k1_bench_im73d",
            "build_flags": "${env:k1_bench_im73d.build_flags}",
            "build_unflags": "-DK1_MIC_IM73D_PDM_V1",
        }
        self.assertNotIn(
            "K1_MIC_IM73D_PDM_V1",
            resolved_macros("k1_bench_unmic_probe", envs),
            "resolver ignored build_unflags stripping the mic flag",
        )


if __name__ == "__main__":
    unittest.main()
