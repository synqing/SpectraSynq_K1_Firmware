"""Build-config policy golden — resolved brownout / coredump / WDT snapshot.

WHY THIS IS A DRIFT-GATE, NOT "sdkconfig pinning":
  k1_hardware builds with `framework = arduino` on the pioarduino platform
  (espressif32 54.03.x). In that mode the IDF sdkconfig is *baked into the
  precompiled* `framework-arduinoespressif32-libs/<chip>/sdkconfig`. A bare
  project-root `sdkconfig.defaults` is NEVER read (arduino.py only honours the
  `custom_sdkconfig` option, which forces a from-source rebuild) — so a hand
  `sdkconfig.defaults` would be inert theatre. This module instead PINS the
  current resolved policy values and lets a host test detect drift when the
  platform/package version moves. It enforces nothing into the binary; it
  *notices* when the binary's config silently changes.

AUTHORITATIVE SOURCE (in priority order, resolved live by the test):
  1. `.pio/build/k1_hardware/sdkconfig`            (the actual app build output)
  2. `$PLATFORMIO_CORE_DIR/packages/framework-arduinoespressif32-libs/esp32s3/sdkconfig`
     (the prebuilt-libs source-of-truth governing the app in prebuilt mode)
  If neither is locatable the test SKIPS LOUD — it must never silently pass and
  report "no drift" from an absent source.

Snapshot captured 2026-06-27 from pioarduino platform 54.03.21,
framework-arduinoespressif32-libs/esp32s3/sdkconfig (esp32-s3-devkitc1-n16r8).
"""
from __future__ import annotations

import os
from pathlib import Path

CHIP = "esp32s3"  # board = esp32-s3-devkitc1-n16r8 (K1 main + bench both S3)

# --- GOLDEN: the pinned resolved policy (full CONFIG_ keys) ------------------
# Captured from the prebuilt esp32s3 sdkconfig. Each value is the raw sdkconfig
# token: "y" (set), "n" (is not set), or a literal (int/string). Changing any
# of these is a DELIBERATE policy decision, not a silent platform drift.
GOLDEN_POLICY = {
    # Brownout detector — undervoltage reset protection (level 7 = highest trip)
    "CONFIG_ESP_BROWNOUT_DET": "y",
    "CONFIG_ESP_BROWNOUT_DET_LVL": "7",
    # Coredump — post-mortem on field crashes. ALREADY enabled to flash with an
    # ELF/CRC32 payload and a boot-time integrity check; the default_16MB.csv
    # partition table already carries the `coredump` partition. The gate locks
    # that this stays on (a platform bump must not silently disable it).
    "CONFIG_ESP_COREDUMP_ENABLE_TO_FLASH": "y",
    "CONFIG_ESP_COREDUMP_DATA_FORMAT_ELF": "y",
    "CONFIG_ESP_COREDUMP_CHECK_BOOT": "y",
    # Task watchdog — catches a starved/hung task (pairs with N2's esp_task_wdt
    # subscription). 5 s timeout, panic-on-starve, init at boot.
    "CONFIG_ESP_TASK_WDT_EN": "y",
    "CONFIG_ESP_TASK_WDT_INIT": "y",
    "CONFIG_ESP_TASK_WDT_PANIC": "y",
    "CONFIG_ESP_TASK_WDT_TIMEOUT_S": "5",
    # Interrupt watchdog — catches an ISR/critical-section that blocks too long.
    "CONFIG_ESP_INT_WDT": "y",
    "CONFIG_ESP_INT_WDT_TIMEOUT_MS": "300",
    # Bootloader watchdog — covers the pre-app window.
    "CONFIG_BOOTLOADER_WDT_ENABLE": "y",
    "CONFIG_BOOTLOADER_WDT_TIME_MS": "9000",
}

# The active default_16MB.csv must carry this partition for flash coredump to work.
GOLDEN_PARTITION_SUBTYPE = "coredump"


def parse_sdkconfig(text: str) -> dict:
    """Parse an IDF sdkconfig into {CONFIG_KEY: token}.

    `CONFIG_X=y` -> "y"; `CONFIG_X=5` -> "5"; `CONFIG_X="s"` -> "s";
    `# CONFIG_X is not set` -> "n".
    """
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            # "# CONFIG_X is not set"
            if line.endswith("is not set"):
                key = line[1:].strip().split(" ", 1)[0].strip()
                if key.startswith("CONFIG_"):
                    out[key] = "n"
            continue
        if "=" in line and line.startswith("CONFIG_"):
            key, val = line.split("=", 1)
            val = val.strip()
            if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
                val = val[1:-1]
            out[key.strip()] = val
    return out


def _pio_core_dir() -> Path:
    return Path(os.environ.get("PLATFORMIO_CORE_DIR", Path.home() / ".platformio"))


def resolve_live_sdkconfig(repo: Path) -> Path | None:
    """Locate the authoritative resolved sdkconfig, build-artifact first."""
    candidates = [
        repo / ".pio" / "build" / "k1_hardware" / "sdkconfig",
        _pio_core_dir() / "packages" / "framework-arduinoespressif32-libs" / CHIP / "sdkconfig",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def resolve_partition_csv(repo: Path) -> Path | None:
    """Locate the resolved partition table, build-artifact first."""
    artifact = repo / ".pio" / "build" / "k1_hardware" / "partitions.csv"
    if artifact.is_file():
        return artifact
    pkgs = _pio_core_dir() / "packages"
    if pkgs.is_dir():
        # Prefer the unversioned active package dir, else any installed one.
        active = pkgs / "framework-arduinoespressif32" / "tools" / "partitions" / "default_16MB.csv"
        if active.is_file():
            return active
        hits = sorted(pkgs.glob("framework-arduinoespressif32*/tools/partitions/default_16MB.csv"))
        if hits:
            return hits[0]
    return None


def extract_policy(resolved: dict) -> dict:
    """Subset a parsed sdkconfig to the golden's keys (missing -> '<absent>')."""
    return {k: resolved.get(k, "<absent>") for k in GOLDEN_POLICY}


def diff_policy(golden: dict, live_policy: dict) -> list[str]:
    """Return human-readable drift lines (empty list == no drift)."""
    drift = []
    for key, want in golden.items():
        got = live_policy.get(key, "<absent>")
        if got != want:
            drift.append(f"{key}: golden={want!r} live={got!r}")
    return drift


def partition_has_coredump(csv_text: str) -> bool:
    for raw in csv_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Name, Type, SubType, ...
        fields = [f.strip() for f in line.split(",")]
        if len(fields) >= 3 and fields[2] == GOLDEN_PARTITION_SUBTYPE:
            return True
    return False
