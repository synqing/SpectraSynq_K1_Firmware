import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / "scripts" / "platformio" / "k1_upload_guard.py"
PLATFORMIO = ROOT / "platformio.ini"
K1_SRC_INCLUDES = ROOT / "scripts" / "platformio" / "k1_src_includes.py"


def load_guard():
    spec = importlib.util.spec_from_file_location("k1_upload_guard", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class K1UploadGuardTest(unittest.TestCase):
    def setUp(self):
        self.guard = load_guard()
        self.ports = [
            {
                "device": "/dev/cu.usbmodem12201",
                "serial_number": "B4:3A:45:A5:89:B4",
                "location": "0-1.2.2",
                "hwid": "USB VID:PID=303A:1001 SER=B4:3A:45:A5:89:B4 LOCATION=0-1.2.2",
            },
            {
                "device": "/dev/cu.usbmodem1401",
                "serial_number": "B4:3A:45:A5:87:F8",
                "location": "0-1.4",
                "hwid": "USB VID:PID=303A:1001 SER=B4:3A:45:A5:87:F8 LOCATION=0-1.4",
            },
        ]

    def test_hardware_env_is_bound_to_main_k1(self):
        ok, message = self.guard.validate_upload_target(
            "k1_hardware",
            "/dev/tty.usbmodem1401",
            self.ports,
        )
        self.assertTrue(ok, message)
        self.assertIn("F887A500", message)

    def test_bench_reference_env_is_bound_to_second_bench_k1(self):
        for env_name in (
            "k1_bench_reference",
            "k1_bench_tempo_probe",
            "k1_bench_ap_frontend_probe",
            "k1_bench_ap_frontend_probe_matrix_16000_120_d3",
            "k1_bench_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1",
            "k1_bench_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread4",
            "k1_bench_im73d",  # IM73D122 PDM mic eval — bench B489A500 only
            "k1_bench_im73d_dsr16",  # IM73D DSR_16S eval - bench B489A500 only
        ):
            with self.subTest(env_name=env_name):
                ok, message = self.guard.validate_upload_target(
                    env_name,
                    "/dev/tty.usbmodem12201",
                    self.ports,
                )
                self.assertTrue(ok, message)
                self.assertIn("B489A500", message)

    def test_harness_envs_follow_default_hardware_pinmap(self):
        for env_name in (
            "k1_hardware_harness",
            "k1_hardware_trace_dev",
            "k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1",
            "k1_ap_frontend_probe_matrix_16000_120_d3",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acq_probe",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread8",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread4",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_gdft",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_novelty",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_snapshot",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_onset",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_saliency",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_d8",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread16",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread12",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread8",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread4",
        ):
            ok, message = self.guard.validate_upload_target(
                env_name,
                "/dev/cu.usbmodem1401",
                self.ports,
            )
            self.assertTrue(ok, message)

    def test_32k_spike_upload_is_blocked_even_on_correct_main_identity(self):
        ok, message = self.guard.validate_upload_target(
            "k1_sample_rate_32k_spike",
            "/dev/cu.usbmodem1401",
            self.ports,
        )
        self.assertFalse(ok)
        self.assertIn("upload blocked", message)
        self.assertIn("acquisition-only", message)

    def test_prod_im73d_is_blocked_until_mic_swap(self):
        # k1_prod_im73d = production pinmap + IM73D PDM. The main K1 still carries
        # an SPH0645, so this env must HARD-BLOCK on every port (a PDM read of an
        # SPH i2s bitstream is garbage) until Captain does the physical mic swap.
        for port in ("/dev/tty.usbmodem1401", "/dev/tty.usbmodem12201"):
            with self.subTest(port=port):
                ok, message = self.guard.validate_upload_target(
                    "k1_prod_im73d", port, self.ports
                )
                self.assertFalse(ok)
                self.assertIn("upload blocked", message)
                self.assertIn("mic swap", message)

    def test_production_pinmap_defines_im73d_pdm_pins(self):
        # Captain D1 (2026-07-06): the production IM73D uses the IDENTICAL
        # bench-proven pins. Assert the production (#else) pinmap defines the PDM
        # pins clk=13 / din=12 / LR=14 under K1_MIC_IM73D_PDM_V1, so k1_prod_im73d
        # compiles and wires the mic to the proven GPIOs.
        constants = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h").read_text()
        # Isolate ONLY the production pinmap branch (the #else of
        # SB_K1_BENCH_REFERENCE_PINMAP) by its unique marker comment, bounded by
        # the shared I2C pins that close the GPIO block. This must NOT alias onto
        # the bench PDM block above (which defines identical pins) — else deleting
        # the production block would still pass (adversarial-review defect, fixed).
        marker = "K1 hardware production GPIO map"
        self.assertIn(marker, constants)
        prod = constants.split(marker, 1)[1].split("#define I2C_SDA_PIN", 1)[0]
        self.assertNotIn("bench-reference GPIO map", prod)  # proves branch isolation
        self.assertIn("#define K1_PDM_CLK_PIN 13", prod)
        self.assertIn("#define K1_PDM_DIN_PIN 12", prod)
        self.assertIn("#define K1_PDM_LR_PIN  14", prod)

    def test_cross_flash_attempts_are_rejected(self):
        cases = (
            ("k1_hardware", "/dev/tty.usbmodem12201"),
            ("k1_bench_reference", "/dev/tty.usbmodem1401"),
            ("k1_bench_ap_frontend_probe", "/dev/tty.usbmodem1401"),
            ("k1_bench_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread4", "/dev/tty.usbmodem1401"),
            ("k1_hardware_harness", "/dev/tty.usbmodem12201"),
            ("k1_bench_im73d", "/dev/tty.usbmodem1401"),  # PDM eval must reject the main K1 port
            ("k1_bench_im73d_dsr16", "/dev/tty.usbmodem1401"),  # DSR eval must reject the main K1 port
        )
        for env_name, port in cases:
            with self.subTest(env_name=env_name, port=port):
                ok, message = self.guard.validate_upload_target(env_name, port, self.ports)
                self.assertFalse(ok)
                self.assertIn("has USB serial", message)
                self.assertIn("expected", message)

    def test_platformio_defaults_match_guarded_physical_mapping(self):
        text = PLATFORMIO.read_text()
        self.assertIn("pre:scripts/platformio/k1_upload_guard.py", text)
        self.assertIn("upload_port   = /dev/tty.usbmodem1401", text)
        self.assertIn("monitor_port  = /dev/tty.usbmodem1401", text)
        self.assertIn("upload_port   = /dev/tty.usbmodem12201", text)
        self.assertIn("monitor_port  = /dev/tty.usbmodem12201", text)
        self.assertIn("B4:3A:45:A5:87:F8", text)
        self.assertIn("B4:3A:45:A5:89:B4", text)
        self.assertIn("[env:k1_bench_im73d_dsr16]", text)
        self.assertIn("-DK1_MIC_IM73D_DSR_16S_V1", text)

    def test_k1_pio_pre_includes_s3_sdkconfig_root(self):
        text = K1_SRC_INCLUDES.read_text()
        self.assertIn("framework-arduinoespressif32-libs", text)
        self.assertIn("board_build.arduino.memory_type", text)
        self.assertIn("sdkconfig.h", text)
        self.assertIn("env.Append(CPPPATH=[_SDKCONFIG_DIR])", text)

    def test_all_k1_chip_bound_envs_are_registered_in_guard(self):
        # DRIFT-CATCHER (2026-06-30): any env whose `extends` chain roots at
        # k1_hardware or k1_bench_reference is GPIO-pin-bound to a specific chip;
        # if it is not in the guard's K1_TARGETS map the guard fail-OPENS ("no K1
        # upload mapping enforced") and a cross-flash to the wrong unit (or the
        # K718 on the shared bus) is NOT blocked. This asserts full coverage so a
        # future probe env added without registration fails the gate, not the chip.
        import re

        text = PLATFORMIO.read_text()
        parent: dict[str, str] = {}
        envs: list[str] = []
        for chunk in re.split(r"(?m)^\[", text):
            m = re.match(r"env:([A-Za-z0-9_.]+)\]", chunk)
            if not m:
                continue
            name = m.group(1)
            envs.append(name)
            pm = re.search(r"(?m)^\s*extends\s*=\s*env:([A-Za-z0-9_.]+)", chunk)
            if pm:
                parent[name] = pm.group(1)

        def root_of(env: str) -> str:
            seen: set[str] = set()
            while env in parent and env not in seen:
                seen.add(env)
                env = parent[env]
            return env

        mapped: set[str] = set()
        for target in self.guard.K1_TARGETS:
            mapped.update(target.envs)
        # A BLOCKED env is also covered: validate_upload_target() hard-blocks it
        # (returns False) BEFORE the fail-open path, so it can never cross-flash.
        # k1_prod_im73d lives here until the main-K1 SPH0645 -> IM73D swap.
        mapped.update(self.guard.BLOCKED_UPLOAD_ENVS)

        K1_ROOTS = {"k1_hardware", "k1_bench_reference"}
        missing = sorted(
            e for e in envs if root_of(e) in K1_ROOTS and e not in mapped
        )
        self.assertEqual(
            missing,
            [],
            "K1 chip-bound envs missing from upload-guard K1_TARGETS "
            f"(cross-flash brick risk — register them): {missing}",
        )


if __name__ == "__main__":
    unittest.main()
