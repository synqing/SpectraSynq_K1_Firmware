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
            "k1_bench_im73d_mic_auto_telemetry",  # IM73D mic auto-sense telemetry - bench B489A500 only
            "k1_bench_im73d_dsr16",  # IM73D DSR_16S eval - bench B489A500 only
            "k1_bench_im69d",  # IM69D130 dual-mic PCB3 PDM eval — bench B489A500 only
            "k1_bench_im69d_ble",  # IM69D + BLE-MIDI Deck16 P0 baseline — bench B489A500 only
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

    def test_prod_im73d_upload_is_blocked_on_every_port(self):
        # 628f69b (2026-07-08) re-blocked k1_prod_im73d outright: no
        # production-LED-wired (6/7) IM73D unit exists, and the 2026-07-07
        # misflash onto the 4/5-wired bench darkened both LED channels. The
        # block fires before any port/identity matching, on any target.
        for port in ("/dev/tty.usbmodem1401", "/dev/tty.usbmodem12201"):
            with self.subTest(port=port):
                ok, message = self.guard.validate_upload_target(
                    "k1_prod_im73d", port, self.ports
                )
                self.assertFalse(ok)
                self.assertIn("upload blocked", message)
                self.assertIn("production-LED-wired", message)

    def test_sync_probe_envs_are_bound_to_their_devices(self):
        # Phase-0 dual-K1 sync probes (F5 grant 2026-07-08): LEADER env only on
        # the main K1 (F887A500), FOLLOWER env only on the bench K1 (B489A500).
        for env_name in ("k1_sync_probe_main", "k1_sync_probe_main_sync_only"):
            with self.subTest(env_name=env_name):
                ok, message = self.guard.validate_upload_target(
                    env_name, "/dev/tty.usbmodem1401", self.ports
                )
                self.assertTrue(ok, message)
                self.assertIn("F887A500", message)
        ok, message = self.guard.validate_upload_target(
            "k1_sync_probe_bench", "/dev/tty.usbmodem12201", self.ports
        )
        self.assertTrue(ok, message)
        self.assertIn("B489A500", message)

    def test_prod_im73d_blocked_rejects_bench_target(self):
        # Blocked envs fail closed before MAC matching — bench port also rejected.
        ok, message = self.guard.validate_upload_target(
            "k1_prod_im73d", "/dev/tty.usbmodem12201", self.ports
        )
        self.assertFalse(ok, message)
        self.assertIn("upload blocked", message)
        self.assertIn("6/7", message)

    def test_unmapped_sync_probe_environment_fails_closed(self):
        ok, message = self.guard.validate_upload_target(
            "k1_sync_probe_typo", "/dev/tty.usbmodem1401", self.ports
        )
        self.assertFalse(ok)
        self.assertIn("unmapped sync probe environment", message)
        self.assertIn("upload blocked", message)

    def test_production_pinmap_defines_im73d_pdm_pins(self):
        # Captain D1 (2026-07-06): the production IM73D uses the IDENTICAL
        # bench-proven pins. Assert the production (#else) pinmap defines the PDM
        # pins clk=13 / din=12 / LR=14 under K1_MIC_IM73D_PDM_V1, so k1_prod_im73d
        # compiles and wires the mic to the proven GPIOs.
        constants = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h").read_text()
        # Isolate ONLY the production pinmap branch (the #else of
        # K1_BENCH_REFERENCE_PINMAP) by its unique marker comment, bounded by
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
            ("k1_bench_im73d_mic_auto_telemetry", "/dev/tty.usbmodem1401"),  # mic auto-sense telemetry must reject the main K1 port
            ("k1_bench_im73d_dsr16", "/dev/tty.usbmodem1401"),  # DSR eval must reject the main K1 port
            ("k1_bench_im69d", "/dev/tty.usbmodem1401"),  # IM69D eval must reject the main K1 port
            ("k1_bench_im69d_ble", "/dev/tty.usbmodem1401"),  # Deck16 P0 radio baseline must reject the main K1 port
            # k1_prod_im73d is upload-blocked outright (628f69b) — covered by blocked-env tests.
            ("k1_sync_probe_main", "/dev/tty.usbmodem12201"),  # sync LEADER must reject the bench port
            ("k1_sync_probe_main_sync_only", "/dev/tty.usbmodem12201"),  # Case A leader must reject bench
            ("k1_sync_probe_bench", "/dev/tty.usbmodem1401"),  # sync FOLLOWER must reject the main port
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

    def test_p4_env_accepts_wch_serial_and_refuses_s3_cdc(self):
        p4_ports = [
            {
                "device": "/dev/tty.wchusbserial5AAF2781791",
                "serial_number": "5AAF278179",
                "location": "0-1",
                "hwid": "SER=5AAF278179",
            }
        ]
        ok, message = self.guard.validate_upload_target(
            "k1_p4_wifi6",
            "/dev/tty.wchusbserial5AAF2781791",
            p4_ports,
        )
        self.assertTrue(ok, message)
        self.assertIn("0743E200", message)

        ok2, message2 = self.guard.validate_upload_target(
            "k1_p4_wifi6",
            "/dev/tty.usbmodem1401",
            self.ports,
        )
        self.assertFalse(ok2, message2)
        self.assertIn("usbmodem", message2)

        ok3, message3 = self.guard.validate_upload_target(
            "k1_hardware",
            "/dev/tty.wchusbserial5AAF2781791",
            p4_ports,
        )
        self.assertFalse(ok3, message3)
        self.assertIn("wchusbserial", message3)


if __name__ == "__main__":
    unittest.main()
