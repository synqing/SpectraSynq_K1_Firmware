#!/usr/bin/env python3
"""Export one PlatformIO env's K1 build profile for the ESP32-S31 ESP-IDF build.

platformio.ini stays the single source of truth for the K1 product flags and the
compiled file list. The S31 build (targets/esp32s31, plain ESP-IDF v6.1) calls this
at CMake configure time and compiles exactly the same sources with exactly the same
flags, plus the declared S31 additions below. Nothing is retyped by hand.

Output JSON (stdout or --out):
  env, flags (build_flags minus build_unflags, in order, split to argv items),
  src_flags (build_src_flags: K1 sources only), sources (absolute paths, sorted, the
  PlatformIO build_src_filter applied to src_dir), lib_deps, ino (the sketch file).

The filter follows PlatformIO's rule: tokens apply in order, `+<glob>` adds and
`-<glob>` removes the files (or every file under a directory) the glob matches,
relative to src_dir. Only C/C++ translation units are returned.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TU_SUFFIXES = (".c", ".cpp", ".cc", ".cxx", ".S", ".ino")


def pio_config() -> dict:
    out = subprocess.run(["pio", "project", "config", "--json-output"], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout
    return {name: dict(items) for name, items in json.loads(out)}


def split_flags(values) -> list[str]:
    items: list[str] = []
    for v in values if isinstance(values, list) else [values]:
        items.extend(shlex.split(v))
    return items


def apply_filter(src_dir: Path, filters: list[str]) -> list[Path]:
    tokens = re.findall(r"([+-])<([^>]*)>", " ".join(filters))
    chosen: set[Path] = set()
    for sign, pattern in tokens:
        matched: set[Path] = set()
        for hit in glob.glob(str(src_dir / pattern)):
            p = Path(hit)
            if p.is_dir():
                matched.update(q for q in p.rglob("*") if q.is_file())
            elif p.is_file():
                matched.add(p)
        chosen = chosen | matched if sign == "+" else chosen - matched
    return sorted(p.resolve() for p in chosen if p.suffix in TU_SUFFIXES)


def include_subdirs() -> list[str]:
    """The source subfolders scripts/platformio/k1_src_includes.py puts on CPPPATH."""
    text = (REPO / "scripts/platformio/k1_src_includes.py").read_text()
    body = re.search(r"_SUBDIRS\s*=\s*\(([^)]*)\)", text)
    if not body:
        raise SystemExit("k1_pio_profile: _SUBDIRS not found in k1_src_includes.py")
    return re.findall(r'"([^"]+)"', body.group(1))


def provenance(env: str, tag_prefix: str) -> list[str]:
    """The defines scripts/platformio/k1_build_provenance.py stamps, for this S31 build."""
    import time

    def git(*args: str) -> str:
        try:
            return subprocess.check_output(["git", *args], cwd=REPO, stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return ""

    defines = [f'-DK1_BUILD_GIT_HASH="{git("rev-parse", "--short", "HEAD") or "unknown"}"',
               f"-DK1_BUILD_EPOCH={int(time.time())}",
               f'-DK1_BUILD_ENV="{env}@esp32s31"']
    if tag_prefix:
        tags = sorted(t for t in git("tag", "--points-at", "HEAD", "--list", tag_prefix + "*").split() if t)
        dirty = git("status", "--porcelain", "--untracked-files=all", "--", "SPECTRASYNQ_K1_FIRMWARE",
                    "platformio.ini", "targets/esp32s31")
        defines.append(f'-DK1_BUILD_TAG="{(tags[-1] if tags else "untagged") + ("-dirty" if dirty else "")}"')
    return defines


def profile(env: str) -> dict:
    cfg = pio_config()
    sec = cfg[f"env:{env}"]
    src_dir = Path(cfg["platformio"]["src_dir"])
    unflags = set(split_flags(sec.get("build_unflags", [])))
    flags = [f for f in split_flags(sec.get("build_flags", [])) if f not in unflags]
    # "-include file" arrives as two argv items; keep them paired.
    src_flags = split_flags(sec.get("build_src_flags", []))
    sources = apply_filter(src_dir, sec.get("build_src_filter", []))
    inos = [s for s in sources if s.suffix == ".ino"]
    return {
        "env": env,
        "src_dir": str(src_dir),
        "include_dirs": [str(src_dir)] + [str(src_dir / d) for d in include_subdirs()],
        "flags": flags,
        "unflags": sorted(unflags),
        "src_flags": src_flags,
        "provenance": provenance(env, sec.get("custom_release_tag_prefix", "")),
        "sources": [str(s) for s in sources if s.suffix != ".ino"],
        "ino": [str(s) for s in inos],
        "lib_deps": sec.get("lib_deps", []),
    }


def cmake_list(name: str, items: list[str]) -> str:
    quoted = "\n".join('  "' + i.replace("\\", "\\\\").replace('"', '\\"') + '"' for i in items)
    return f"set({name}\n{quoted}\n)\n"


def as_cmake(p: dict) -> str:
    """CMake lists. Flags keep their exact argv form (quoted defines stay C string literals)."""
    return ("# Generated by targets/esp32s31/tools/k1_pio_profile.py from platformio.ini. Do not edit.\n"
            f'set(K1_PROFILE_ENV "{p["env"]}")\n'
            f'set(K1_SRC_DIR "{p["src_dir"]}")\n'
            + cmake_list("K1_INCLUDE_DIRS", p["include_dirs"])
            + cmake_list("K1_FLAGS", p["flags"])
            + cmake_list("K1_SRC_FLAGS", p["src_flags"])
            + cmake_list("K1_PROVENANCE", p["provenance"])
            + cmake_list("K1_SOURCES", p["sources"])
            + cmake_list("K1_INO", p["ino"]))


def write_if_changed(path: Path, data: str) -> None:
    if not path.exists() or path.read_text() != data:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True)
    ap.add_argument("--out", help="write the JSON profile here")
    ap.add_argument("--cmake", help="write the CMake include here")
    args = ap.parse_args()
    p = profile(args.env)
    data = json.dumps(p, indent=1) + "\n"
    if args.out:
        write_if_changed(Path(args.out), data)
    if args.cmake:
        write_if_changed(Path(args.cmake), as_cmake(p))
    if not args.out and not args.cmake:
        sys.stdout.write(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
