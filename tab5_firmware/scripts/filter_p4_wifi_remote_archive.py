"""Create Tab5-safe ESP32-P4 precompiled archives for Arduino-as-IDF builds.

1) esp_wifi_remote: drop wifi_default/netif objects that collide with IDF esp_wifi.
2) esp_hosted: drop hci_stub_drv.c.obj so project src/hosted_vhci_drv.c can supply
   real NimBLE VHCI transport over ESP-Hosted SDIO (Deck16 P1 GATT unlock).
"""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

Import("env")  # type: ignore

WIFI_REMOTE_EXCLUDED = {
    "wifi_default.c.obj",
    "wifi_netif.c.obj",
    "wifi_default_ap.c.obj",
}

HOSTED_EXCLUDED = {
    "hci_stub_drv.c.obj",
}


def _filter_archive(
    *,
    archive_tool: Path,
    source_archive: Path,
    output_archive: Path,
    excluded: set[str],
    label: str,
) -> None:
    if not source_archive.exists():
        print(f"[{label}] missing source archive: {source_archive}", file=sys.stderr)
        env.Exit(1)

    output_archive.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"{label}_") as tmp_name:
        tmp_dir = Path(tmp_name)
        members_raw = subprocess.check_output(
            [str(archive_tool), "t", str(source_archive)],
            text=True,
        )
        members = [line.strip() for line in members_raw.splitlines() if line.strip()]
        keep = [member for member in members if Path(member).name not in excluded]
        dropped = len(members) - len(keep)

        if keep:
            subprocess.check_call(
                [str(archive_tool), "x", str(source_archive), *keep], cwd=tmp_dir
            )
        candidate = tmp_dir / output_archive.name
        if keep:
            subprocess.check_call(
                [str(archive_tool), "qc", str(candidate), *keep], cwd=tmp_dir
            )
        else:
            # Empty archive is invalid for ar; should never happen for these libs.
            print(f"[{label}] refused empty archive after filter", file=sys.stderr)
            env.Exit(1)
        subprocess.check_call([str(archive_tool), "s", str(candidate)], cwd=tmp_dir)
        shutil.copy2(candidate, output_archive)

    print(
        f"[{label}] filtered -> {output_archive} "
        f"({len(keep)} kept, {dropped} excluded)"
    )


def main() -> None:
    project_dir = Path(env["PROJECT_DIR"])
    package_root = project_dir / "vendor" / "pio_packages"
    archive_tool = package_root / "toolchain-riscv32-esp" / "bin" / "riscv32-esp-elf-ar"
    lib_dir = package_root / "framework-arduinoespressif32-libs" / "esp32p4" / "lib"
    output_dir = project_dir / ".pio" / "generated" / "tab5_p4"

    if not archive_tool.exists():
        print(f"[tab5_archives] missing archive tool: {archive_tool}", file=sys.stderr)
        env.Exit(1)

    _filter_archive(
        archive_tool=archive_tool,
        source_archive=lib_dir / "libespressif__esp_wifi_remote.a",
        output_archive=output_dir / "libespressif__esp_wifi_remote_tab5.a",
        excluded=WIFI_REMOTE_EXCLUDED,
        label="tab5_wifi_remote",
    )
    # A/B env builds esp_hosted 1.4.x from source — do not emit/link 2.0.13 archive.
    if os.environ.get("TAB5_HOSTED_AB_VERSION"):
        print(
            f"[tab5_hosted_vhci] skip prebuilt filter "
            f"(TAB5_HOSTED_AB_VERSION={os.environ.get('TAB5_HOSTED_AB_VERSION')})"
        )
    else:
        _filter_archive(
            archive_tool=archive_tool,
            source_archive=lib_dir / "libespressif__esp_hosted.a",
            output_archive=output_dir / "libespressif__esp_hosted_tab5.a",
            excluded=HOSTED_EXCLUDED,
            label="tab5_hosted_vhci",
        )


main()
