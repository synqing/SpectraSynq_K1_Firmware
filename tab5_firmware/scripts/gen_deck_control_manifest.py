#!/usr/bin/env python3
"""Precision Bay R1 — soft-key manifest validator + C stub generator (G2).

Authority: ui/spec/deck_softkey_manifest.json
Does not invent paths. Validates schema keys and path presence against the
live K1 map when --map is provided.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


REQUIRED_KEY_IDS = [
    "F01_CALIBRATE",
    "F02_EDGE",
    "F03_RENDER",
    "F04_SENSITIVITY",
    "F05_SMART",
    "F06_DIRECTOR",
    "F07_VIVID",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def load_map_paths(map_path: Path) -> set[str]:
    data = json.loads(map_path.read_text())
    paths: set[str] = set()
    entries = data.get("entries")
    if isinstance(entries, list):
        for item in entries:
            if isinstance(item, dict) and item.get("path"):
                paths.add(item["path"])
        return paths
    controls = data.get("controls") or data.get("map") or data
    if isinstance(controls, dict):
        for k, v in controls.items():
            if isinstance(v, dict) and "path" in v:
                paths.add(v["path"])
            else:
                paths.add(k)
    elif isinstance(controls, list):
        for item in controls:
            if isinstance(item, dict) and "path" in item:
                paths.add(item["path"])
    return paths


def validate(manifest: dict, map_paths: set[str] | None) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != "precision_bay_r1.deck_softkey_manifest/1":
        errors.append(f"unexpected schema: {manifest.get('schema')!r}")
    keys = manifest.get("keys") or []
    if len(keys) != 7:
        errors.append(f"expected 7 keys, got {len(keys)}")
    seen = []
    for entry in keys:
        kid = entry.get("key_id")
        seen.append(kid)
        if not entry.get("controls"):
            status = entry.get("status") or ""
            if status not in ("SUPERSEDED_DEAD_ON_GLASS", "DISABLED_NO_OPEN"):
                errors.append(f"{kid}: EMPTY_SHEET (no controls)")
            # Empty sheet allowed for dead/disabled soft-keys (no glass TX).
        for ctrl in entry.get("controls") or []:
            path = ctrl.get("path")
            if not path:
                errors.append(f"{kid}: control missing path")
                continue
            ack = ctrl.get("ack_policy", "")
            if ack in ("CONFIRMED_REMOTE", "REMOTE_ECHO"):
                errors.append(f"{kid}/{path}: forbidden ack_policy {ack} before B2")
            if map_paths is not None and path not in map_paths:
                errors.append(f"{kid}: REGISTRY_GAP path not in map: {path}")
    for required in REQUIRED_KEY_IDS:
        if required not in seen:
            errors.append(f"missing key_id {required}")
    return errors


def emit_header(manifest: dict, out: Path, manifest_sha: str) -> None:
    lines = [
        "/* Auto-generated — Precision Bay R1 G2 manifest stub.",
        f" * Source sha256: {manifest_sha}",
        " * DO NOT hand-edit; regenerate via scripts/gen_deck_control_manifest.py",
        " */",
        "#ifndef DECK_CONTROL_MANIFEST_H",
        "#define DECK_CONTROL_MANIFEST_H",
        "",
        "#include <stdint.h>",
        "",
        "#ifdef __cplusplus",
        'extern "C" {',
        "#endif",
        "",
        f"#define DECK_MANIFEST_KEY_COUNT {len(manifest.get('keys') or [])}",
        f"#define DECK_MANIFEST_SHA256 \"{manifest_sha}\"",
        "",
        "typedef struct {",
        "  const char* key_id;",
        "  const char* label;",
        "  const char* sheet_id;",
        "  uint8_t control_count;",
        "} DeckManifestKey;",
        "",
        "typedef struct {",
        "  const char* key_id;",
        "  const char* path;",
        "  const char* kind;",
        "  const char* ack_policy;",
        "} DeckManifestControl;",
        "",
        "const DeckManifestKey* deck_manifest_keys(uint8_t* out_count);",
        "const DeckManifestControl* deck_manifest_controls(uint8_t* out_count);",
        "int deck_manifest_validate_runtime(void);",
        "",
        "#ifdef __cplusplus",
        "}",
        "#endif",
        "",
        "#endif /* DECK_CONTROL_MANIFEST_H */",
        "",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))


def emit_cpp(manifest: dict, out: Path, manifest_sha: str) -> None:
    keys = manifest.get("keys") or []
    controls = []
    for k in keys:
        for c in k.get("controls") or []:
            controls.append((k.get("key_id", ""), c))

    lines = [
        "/* Auto-generated — Precision Bay R1 G2 manifest tables. */",
        '#include "generated/deck_control_manifest.h"',
        "",
        "static const DeckManifestKey kKeys[] = {",
    ]
    for k in keys:
        lines.append(
            f'  {{"{k.get("key_id","")}", "{k.get("label","")}", '
            f'"{k.get("sheet_id","")}", {len(k.get("controls") or [])}}},'
        )
    lines += [
        "};",
        "",
        "static const DeckManifestControl kControls[] = {",
    ]
    for kid, c in controls:
        lines.append(
            f'  {{"{kid}", "{c.get("path","")}", "{c.get("kind","")}", '
            f'"{c.get("ack_policy","")}"}},'
        )
    lines += [
        "};",
        "",
        "const DeckManifestKey* deck_manifest_keys(uint8_t* out_count)",
        "{",
        "  if (out_count) *out_count = (uint8_t)(sizeof(kKeys) / sizeof(kKeys[0]));",
        "  return kKeys;",
        "}",
        "",
        "const DeckManifestControl* deck_manifest_controls(uint8_t* out_count)",
        "{",
        "  if (out_count) *out_count = (uint8_t)(sizeof(kControls) / sizeof(kControls[0]));",
        "  return kControls;",
        "}",
        "",
        "int deck_manifest_validate_runtime(void)",
        "{",
        f'  /* Embedded sha {manifest_sha} — host validator is authoritative. */',
        "  uint8_t n = 0;",
        "  deck_manifest_keys(&n);",
        "  return (n == DECK_MANIFEST_KEY_COUNT) ? 0 : -1;",
        "}",
        "",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "ui" / "spec" / "deck_softkey_manifest.json",
    )
    ap.add_argument(
        "--map",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "docs" / "protocol" / "k1-ble-midi-map.json",
    )
    ap.add_argument("--skip-map", action="store_true")
    ap.add_argument(
        "--header-out",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "include"
        / "generated"
        / "deck_control_manifest.h",
    )
    ap.add_argument(
        "--cpp-out",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "src"
        / "generated"
        / "deck_control_manifest.cpp",
    )
    ap.add_argument("--emit", action="store_true", help="Write generated header/cpp")
    args = ap.parse_args()

    if not args.manifest.is_file():
        print(f"FAIL: manifest missing: {args.manifest}", file=sys.stderr)
        return 2

    manifest = json.loads(args.manifest.read_text())
    manifest_sha = sha256_file(args.manifest)
    map_paths = None
    if not args.skip_map:
        if not args.map.is_file():
            print(f"FAIL: map missing: {args.map}", file=sys.stderr)
            return 2
        map_paths = load_map_paths(args.map)

    errors = validate(manifest, map_paths)
    if errors:
        print("MANIFEST_VALIDATE=FAIL")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("MANIFEST_VALIDATE=PASS")
    print(f"manifest_sha256={manifest_sha}")
    print(f"keys={len(manifest.get('keys') or [])}")
    ctrl_n = sum(len(k.get("controls") or []) for k in (manifest.get("keys") or []))
    print(f"controls={ctrl_n}")

    if args.emit:
        emit_header(manifest, args.header_out, manifest_sha)
        emit_cpp(manifest, args.cpp_out, manifest_sha)
        print(f"wrote {args.header_out}")
        print(f"wrote {args.cpp_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
