import pathlib
import subprocess
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
YAML = ROOT / "docs/protocol/k1-ws-controls-registry.yaml"
OUT = ROOT / "sb-tab5-wireless-controller/src/network/K1ControlRegistry.h"
CODEGEN = ROOT / "scripts/regression-harness/k1_ws_registry_codegen.py"
FACADE = ROOT / "SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp"


class K1WsRegistryCodegenTest(unittest.TestCase):
    def test_codegen_matches_yaml_and_facade_allowlist(self) -> None:
        subprocess.run(
            ["python3", str(CODEGEN)],
            check=True,
            cwd=ROOT,
        )
        data = yaml.safe_load(YAML.read_text(encoding="utf-8"))
        controls = [str(item) for item in data["controls"]]
        header = OUT.read_text(encoding="utf-8")
        facade = FACADE.read_text(encoding="utf-8")

        self.assertIn(f'#define K1_CONTROL_REGISTRY_ID "{data["version"]}"', header)
        self.assertIn(f"#define K1_CONTROL_REGISTRY_COUNT {len(controls)}", header)
        for path in controls:
            self.assertIn(f'"{path}"', header)
            self.assertIn(f'"{path}"', facade)

        self.assertIn("k1ControlPathKnown", header)
        self.assertIn("k1ControlTierForPath", header)


if __name__ == "__main__":
    unittest.main()
