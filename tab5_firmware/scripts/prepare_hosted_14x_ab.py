"""Prepare / tear down ESP-Hosted 1.4.0 A/B overlay for env tab5_p4_hosted_14x.

Default env tab5_p4 is untouched: vendor libs stay on 2.0.13.
See vendor/esp_hosted_ab/REVERT.md.
"""

from __future__ import annotations

import os
from pathlib import Path

Import("env")  # type: ignore

project_dir = Path(env["PROJECT_DIR"])
pioenv = env.subst("$PIOENV")
components_link = project_dir / "components" / "esp_hosted"
ab_component = (
    project_dir / "vendor" / "esp_hosted_ab" / "components" / "esp_hosted"
).resolve()

is_ab = pioenv == "tab5_p4_hosted_14x"
yml = ab_component / "idf_component.yml"
yml_disabled = ab_component / "idf_component.yml.ab_disabled"

if is_ab:
    if not ab_component.exists():
        print(f"[hosted_14x_ab] missing component at {ab_component}", file=__import__("sys").stderr)
        env.Exit(1)
    components_link.parent.mkdir(parents=True, exist_ok=True)
    if components_link.is_symlink() or components_link.exists():
        components_link.unlink()
    components_link.symlink_to(ab_component, target_is_directory=True)
    # IDF_COMPONENT_MANAGER=0 in toolchain shim; local tree needs no registry fetch.
    if yml.exists() and not yml_disabled.exists():
        yml.rename(yml_disabled)
        print(f"[hosted_14x_ab] parked {yml.name} -> {yml_disabled.name}")
    os.environ["TAB5_HOSTED_AB_VERSION"] = "1.4.0"
    env["ENV"]["TAB5_HOSTED_AB_VERSION"] = "1.4.0"
    marker = ab_component / ".tab5_hosted_ab"
    marker.write_text("1.4.0\n", encoding="utf-8")
    print(f"[hosted_14x_ab] linked {components_link} -> {ab_component}")
    print("[hosted_14x_ab] TAB5_HOSTED_AB_VERSION=1.4.0 (skip prebuilt 2.0.13 hosted.a)")
else:
    # Keep default builds free of the AB component so 2.0.13 prebuilt is used.
    if components_link.is_symlink() or components_link.exists():
        components_link.unlink()
        print(f"[hosted_14x_ab] removed stale link {components_link} for env {pioenv}")
    if yml_disabled.exists() and not yml.exists():
        yml_disabled.rename(yml)
        print(f"[hosted_14x_ab] restored {yml.name}")
    marker = ab_component / ".tab5_hosted_ab"
    if marker.exists():
        marker.unlink()
        print("[hosted_14x_ab] cleared AB marker")
    os.environ.pop("TAB5_HOSTED_AB_VERSION", None)
    env["ENV"].pop("TAB5_HOSTED_AB_VERSION", None)
