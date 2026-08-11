#!/usr/bin/env python3
"""Kill perceptual-mechanism regressions in the Tab5 palette motion path."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


SCHEMA = "spectrasynq-tab5-palette-motion-mutations-v1"


def replace_exact(path: Path, old: str, new: str, expected_count: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected_count:
        raise ValueError(f"{path.name}: expected {expected_count} targets, found {count}")
    updated = text.replace(old, new)
    if updated == text:
        raise ValueError(f"{path.name}: inert mutation")
    path.write_text(updated, encoding="utf-8")


def source_findings(specimen: Path) -> list[str]:
    flow = (specimen / "src/palette_flow.cpp").read_text(encoding="utf-8")
    ui = (specimen / "src/deck_ui.cpp").read_text(encoding="utf-8")
    findings: list[str] = []
    if any(token in flow for token in ("malloc(", "calloc(", "new ", "String", "std::vector")):
        findings.append("hot-path heap allocation")
    if "static PaletteFlowState gPaletteFlow = {};" not in ui or "gPaletteFlow[2]" in ui:
        findings.append("independent consumer motion state")
    if "lv_obj_set_style_translate_x" in ui:
        findings.append("integer widget translation")
    required_filter = (
        "palette_flow_prefilter_rgb888(raw_lut, 256, z->palette_lut)",
    )
    required_filter_engine = (
        "static constexpr uint8_t kWeights[11]",
        "r_linear += r * r * weight",
        "g_linear += g * g * weight",
        "b_linear += b * b * weight",
    )
    if (any(token not in ui for token in required_filter) or
            any(token not in flow for token in required_filter_engine)):
        findings.append("linear-light palette prefilter missing")
    return findings


def run_flow_harness(specimen: Path) -> list[str]:
    executable = specimen / "palette_flow_harness"
    build = subprocess.run(
        [
            "clang++",
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{specimen / 'include'}",
            str(specimen / "src/palette_flow.cpp"),
            str(specimen / "tests/palette_flow_harness.cpp"),
            "-o",
            str(executable),
        ],
        text=True,
        capture_output=True,
    )
    if build.returncode != 0:
        return ["motion harness did not compile"]
    run = subprocess.run([str(executable)], text=True, capture_output=True)
    findings: list[str] = []
    combined = run.stdout + run.stderr
    if "field is still one-dimensional across its height" in combined:
        findings.append("one-dimensional field collapse")
    if "vertical effect size is technically nonzero but visually negligible" in combined:
        findings.append("vertical effect size too weak")
    if "caustic modulation is too weak to be visually meaningful" in combined:
        findings.append("caustic field removed")
    if any(
        message in combined
        for message in (
            "uniform palette colour was not preserved",
            "palette filter lost its centred triangular weighting",
            "palette filter is not circular at the wrap boundary",
            "palette filter support is not the intended eleven taps",
        )
    ):
        findings.append("linear-light palette prefilter missing")
    if run.returncode != 0 and not findings:
        findings.append("motion harness failed for an unrelated reason")
    return findings


@dataclass(frozen=True)
class Mutation:
    name: str
    expected_finding: str
    apply: Callable[[Path], None]


def mutations() -> tuple[Mutation, ...]:
    def collapse_to_one_dimension(root: Path) -> None:
        replace_exact(
            root / "src/palette_flow.cpp",
            "constexpr float kWaveVerticalFrequency[PALETTE_FLOW_WAVE_COUNT] = {0.38f, 0.85f, 1.35f};",
            "constexpr float kWaveVerticalFrequency[PALETTE_FLOW_WAVE_COUNT] = {0.0f, 0.0f, 0.0f};",
        )

    def remove_caustic(root: Path) -> None:
        replace_exact(
            root / "src/palette_flow.cpp",
            "float delta = -8.0f + 34.0f * shimmer;",
            "float delta = shimmer * 0.0f;",
        )

    def make_vertical_effect_negligible(root: Path) -> None:
        replace_exact(
            root / "src/palette_flow.cpp",
            "constexpr float kWaveVerticalFrequency[PALETTE_FLOW_WAVE_COUNT] = {0.38f, 0.85f, 1.35f};",
            "constexpr float kWaveVerticalFrequency[PALETTE_FLOW_WAVE_COUNT] = {0.001f, 0.002f, 0.003f};",
        )

    def add_heap(root: Path) -> None:
        replace_exact(
            root / "src/palette_flow.cpp",
            "#include <math.h>\n",
            "#include <math.h>\nstatic int* gForbiddenHeap = new int(1);\n",
        )

    def split_consumers(root: Path) -> None:
        replace_exact(
            root / "src/deck_ui.cpp",
            "static PaletteFlowState gPaletteFlow = {};",
            "static PaletteFlowState gPaletteFlow[2] = {};",
        )

    def restore_integer_translation(root: Path) -> None:
        replace_exact(
            root / "src/deck_ui.cpp",
            "    if (z.is_palette && z.grad) paint_palette_strip(&z, z.grad_last);",
            "    if (z.is_palette && z.grad) {\n"
            "      lv_obj_set_style_translate_x(z.grad, 1, LV_PART_MAIN);\n"
            "      paint_palette_strip(&z, z.grad_last);\n"
            "    }",
        )

    def linearise_in_srgb(root: Path) -> None:
        path = root / "src/palette_flow.cpp"
        for channel in ("r", "g", "b"):
            replace_exact(
                path,
                f"{channel}_linear += {channel} * {channel} * weight;",
                f"{channel}_linear += {channel} * weight;",
            )

    return (
        Mutation("vertical-frequency-zero", "one-dimensional field collapse", collapse_to_one_dimension),
        Mutation("vertical-effect-negligible", "vertical effect size too weak", make_vertical_effect_negligible),
        Mutation("caustic-zero", "caustic field removed", remove_caustic),
        Mutation("hot-path-new", "hot-path heap allocation", add_heap),
        Mutation("independent-consumers", "independent consumer motion state", split_consumers),
        Mutation("integer-translation", "integer widget translation", restore_integer_translation),
        Mutation("srgb-stop-average", "linear-light palette prefilter missing", linearise_in_srgb),
    )


def create_specimen(repo_root: Path, destination: Path) -> None:
    for relative in (
        "tab5_firmware/include/palette_flow.h",
        "tab5_firmware/src/palette_flow.cpp",
        "tab5_firmware/src/deck_ui.cpp",
        "tab5_firmware/tests/palette_flow_harness.cpp",
    ):
        source = repo_root / relative
        target = destination / Path(relative).relative_to("tab5_firmware")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def evaluate(specimen: Path) -> list[str]:
    return source_findings(specimen) + run_flow_harness(specimen)


def run_gate(repo_root: Path) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="tab5-palette-motion-") as temporary:
        base = Path(temporary) / "positive"
        create_specimen(repo_root, base)
        positive_findings = evaluate(base)

        for index, mutation in enumerate(mutations()):
            specimen = Path(temporary) / f"mutant-{index:02d}"
            create_specimen(repo_root, specimen)
            mutation.apply(specimen)
            findings = evaluate(specimen)
            rows.append(
                {
                    "name": mutation.name,
                    "expected_finding": mutation.expected_finding,
                    "observed_findings": sorted(findings),
                    "killed": mutation.expected_finding in findings,
                }
            )

    passed = not positive_findings and all(bool(row["killed"]) for row in rows)
    return {
        "schema": SCHEMA,
        "passed": passed,
        "positive_control": {"passed": not positive_findings, "findings": positive_findings},
        "mutation_count": len(rows),
        "mutations": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    report = run_gate(args.repo_root.resolve())
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"TAB5_PALETTE_MOTION_MUTATION_GATE={'PASS' if report['passed'] else 'FAIL'} "
        f"mutants={report['mutation_count']}"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
