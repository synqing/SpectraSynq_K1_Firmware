#!/usr/bin/env python3
"""Canonical K1 ESP32-S3 emulator replay runner. Never flashes or opens hardware.

    python3 tools/esp_emulator/run.py \
        --scenario tools/esp_emulator/s3_music_regression.json \
        --output _scratch/esp-emulator/<fresh-name> [--suite default|long]

Builds the emulator replay env and the normal product env, runs every case of
the selected suite through the pinned esp-emu, accepts each capture with the one
acceptance function in emu_capture.py, evaluates the declared comparisons and
planted negative cases, and writes one result.json plus report.html in the
run-owned output directory. Exit status 0 only when every enabled software
criterion passes. README.md beside this file is the contract.
"""

from __future__ import annotations

import argparse
import array
import datetime as dt
import glob
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import uuid
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import emu_blob  # noqa: E402
import emu_capture as ec  # noqa: E402
import emu_client  # noqa: E402
import emu_report_data as rd  # noqa: E402

STATUSES = ("PASS", "FAIL", "NOT_RUN", "DEFERRED_EXTERNAL", "NOT_APPLICABLE")


class ScenarioError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# Scenario schema: unknown fields, unsupported commands and bad windows are
# rejected before anything is built or run.
# --------------------------------------------------------------------------

HOST_CHECK_KEYS = {"pytest", "builds", "requires_git"}
TOP_KEYS = {"schema", "name", "description", "profile", "tool_lock", "time", "assets",
            "compositions", "cases", "comparisons", "planted", "suites", "historical",
            "host_checks", "fields_doc", "client"}
CLIENT_KEYS = {"name", "argv", "note"}          # top-level: the existing control client
CASE_CLIENT_KEYS = {"composition", "commands", "note"}
PROFILE_KEYS = {"env", "product_env", "adapter_flags", "forbidden_in_product", "trace", "emulator",
                "limiter"}
TRACE_KEYS = {"edges", "px", "bpp", "fmt", "native_order", "boundary"}
EMULATOR_KEYS = {"chip", "psram", "batch_size", "timeout_s"}
TIME_KEYS = {"rate_hz", "hop_samples", "convention", "coordinate", "elapsed_formula"}
ASSET_KEYS = {"kind", "path", "inventory", "fixture_id", "excerpt", "conversion", "sha256",
              "samples", "origin", "qualification", "segments", "note", "source_sha256"}
CASE_KEYS = {"purpose", "pcm", "tail_hops", "partial_hop", "epoch", "capture", "commands",
             "composition", "flash", "save_state", "stall_ms", "expect", "semantic", "trace_novelty",
             "client"}
CAPTURE_KEYS = {"start_hop", "end_hop", "every"}
COMMAND_KEYS = {"hop", "text", "expect"}
FLASH_KEYS = {"from", "recovery"}
EXPECT_KEYS = {"end_reason", "saves"}
EPOCH_KEYS = {"policy", "us"}
COMPARISON_KEYS = {"id", "kind", "a", "b", "edge", "from_hop", "criterion", "label", "before_case",
                   "default_case", "note", "expect"}
COMPARISON_KINDS = {"equal", "isolation", "limit_coupling", "recovery_state", "fallback_state",
                    "differs", "case", "startup_quiet_return", "tempo_lane", "semantic_continuity"}

# Production command names the scenario may schedule (production parser vocabulary;
# serial_cmd_handlers.cpp / serial_menu.cpp). Anything else is rejected up front.
SUPPORTED_COMMANDS = {
    "set_mode", "secondary_mode", "photons", "secondary_photons", "palette_index",
    "secondary_palette_index", "palette_mode", "secondary_palette_mode", "chroma",
    "secondary_chroma", "mood", "secondary_mood", "saturation", "secondary_saturation",
    "prism_count", "secondary_prism_count", "mirror_enabled", "secondary_mirror_enabled",
    "reverse_order", "secondary_reverse_order", "base_coat", "secondary_base_coat",
    "incandescent_filter", "auto_color_shift", "secondary_auto_color_shift",
    "secondary_enabled", "edge_enabled", "edge_mode", "edge_strength", "edge_spread",
    "edge_rotation", "edge_uniform", "edge_dual", "max_current_ma", "save_show",
}


def _check_keys(obj: dict, allowed: set[str], where: str) -> None:
    if not isinstance(obj, dict):
        raise ScenarioError(f"{where}: expected an object")
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise ScenarioError(f"{where}: unknown field(s) {unknown}")


def _command_name(text: str) -> str:
    return text.split("=", 1)[0]


def load_scenario(path: Path) -> dict:
    raw = path.read_text()

    def no_dupes(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ScenarioError(f"duplicate JSON key {k!r}")
            out[k] = v
        return out

    sc = json.loads(raw, object_pairs_hook=no_dupes)
    _check_keys(sc, TOP_KEYS, "scenario")
    if sc.get("schema") != "k1-emu-scenario/2":
        raise ScenarioError(f"schema {sc.get('schema')!r} is not k1-emu-scenario/2")
    prof = sc["profile"]
    _check_keys(prof, PROFILE_KEYS, "profile")
    _check_keys(prof["trace"], TRACE_KEYS, "profile.trace")
    _check_keys(prof["emulator"], EMULATOR_KEYS, "profile.emulator")
    t = sc["time"]
    _check_keys(t, TIME_KEYS, "time")
    if t["hop_samples"] != 96 or t["rate_hz"] != 12800 or t["convention"] != "hop_end":
        raise ScenarioError("time contract must be 12800 Hz, 96-sample hops, hop_end")
    for aid, asset in sc["assets"].items():
        _check_keys(asset, ASSET_KEYS, f"assets.{aid}")
        if asset["kind"] not in {"c_array_inc", "inventory_excerpt", "concat"}:
            raise ScenarioError(f"assets.{aid}: unsupported kind {asset['kind']!r}")
        if asset.get("qualification") not in {"synthetic_diagnostic", "real_music", "diagnostic_composite"}:
            raise ScenarioError(f"assets.{aid}: qualification must be declared")
    for cid, comp in sc.get("compositions", {}).items():
        if not isinstance(comp, dict) or set(comp) - {"commands", "note"}:
            raise ScenarioError(f"compositions.{cid}: expected {{commands, note}}")
        for text in comp["commands"]:
            if _command_name(text) not in SUPPORTED_COMMANDS:
                raise ScenarioError(f"compositions.{cid}: unsupported command {text!r}")
    for cid, case in sc["cases"].items():
        where = f"cases.{cid}"
        _check_keys(case, CASE_KEYS, where)
        if case["pcm"] not in sc["assets"]:
            raise ScenarioError(f"{where}: unknown pcm asset {case['pcm']!r}")
        cap = case.get("capture", {"start_hop": 0, "end_hop": None, "every": 1})
        _check_keys(cap, CAPTURE_KEYS, f"{where}.capture")
        if cap.get("every", 1) < 1 or cap.get("start_hop", 0) < 0:
            raise ScenarioError(f"{where}.capture: invalid window")
        if cap.get("end_hop") is not None and cap["end_hop"] <= cap.get("start_hop", 0):
            raise ScenarioError(f"{where}.capture: end_hop must exceed start_hop")
        if case.get("partial_hop", "reject") not in {"reject", "zero_pad"}:
            raise ScenarioError(f"{where}: partial_hop must be reject or zero_pad")
        ep = case.get("epoch", {"policy": "boot_monotonic"})
        _check_keys(ep, EPOCH_KEYS, f"{where}.epoch")
        if ep["policy"] not in emu_blob.EPOCH_POLICIES:
            raise ScenarioError(f"{where}.epoch: unknown policy {ep['policy']!r}")
        if (ep["policy"] == "declared") != ("us" in ep):
            raise ScenarioError(f"{where}.epoch: 'us' is required exactly for the declared policy")
        if case.get("composition") and case["composition"] not in sc.get("compositions", {}):
            raise ScenarioError(f"{where}: unknown composition {case['composition']!r}")
        for c in case.get("commands", []):
            _check_keys(c, COMMAND_KEYS, f"{where}.commands")
            if _command_name(c["text"]) not in SUPPORTED_COMMANDS:
                raise ScenarioError(f"{where}: unsupported command {c['text']!r}")
            if c.get("expect", "applied") not in {"applied", "rejected"}:
                raise ScenarioError(f"{where}: command expect must be applied or rejected")
            if not isinstance(c["hop"], int) or c["hop"] < 0:
                raise ScenarioError(f"{where}: command hop must be a non-negative hop boundary")
        if "client" in case:
            cl = case["client"]
            _check_keys(cl, CASE_CLIENT_KEYS, f"{where}.client")
            if "client" not in sc:
                raise ScenarioError(f"{where}: client lines need the top-level client declaration")
            if cl.get("composition") and cl["composition"] not in sc.get("compositions", {}):
                raise ScenarioError(f"{where}.client: unknown composition {cl['composition']!r}")
            if not cl.get("composition") and not cl.get("commands"):
                raise ScenarioError(f"{where}.client: declares no client lines")
            for c in cl.get("commands", []):
                _check_keys(c, COMMAND_KEYS, f"{where}.client.commands")
                if _command_name(c["text"]) not in SUPPORTED_COMMANDS:
                    raise ScenarioError(f"{where}.client: unsupported command {c['text']!r}")
                if c.get("expect", "applied") not in {"applied", "rejected"}:
                    raise ScenarioError(f"{where}.client: command expect must be applied or rejected")
                if not isinstance(c["hop"], int) or c["hop"] < 0:
                    raise ScenarioError(f"{where}.client: command hop must be a non-negative hop boundary")
        fl = case.get("flash", {"from": "blank", "recovery": False})
        _check_keys(fl, FLASH_KEYS, f"{where}.flash")
        if fl["from"] != "blank" and fl["from"] not in sc["cases"]:
            raise ScenarioError(f"{where}.flash: unknown source case {fl['from']!r}")
        if fl.get("recovery") and (case.get("commands") or case.get("composition") or case.get("client")):
            raise ScenarioError(f"{where}: a recovery run may not schedule commands, client lines or a composition")
        if fl["from"] != "blank" and not sc["cases"][fl["from"]].get("save_state"):
            raise ScenarioError(f"{where}.flash: source case {fl['from']!r} does not save state")
        _check_keys(case.get("expect", {}), EXPECT_KEYS, f"{where}.expect")
    for comp in sc.get("comparisons", []):
        _check_keys(comp, COMPARISON_KEYS, "comparisons")
        if comp["kind"] not in COMPARISON_KINDS:
            raise ScenarioError(f"comparison {comp.get('id')}: unknown kind {comp['kind']!r}")
        for key in ("a", "b", "before_case", "default_case"):
            if key in comp and comp[key] not in sc["cases"]:
                raise ScenarioError(f"comparison {comp['id']}: unknown case {comp[key]!r}")
    if "client" in sc:
        _check_keys(sc["client"], CLIENT_KEYS, "client")
        try:
            emu_client.check_client_argv(sc["client"].get("argv"))
        except emu_client.ClientSpecError as exc:
            raise ScenarioError(f"client: {exc}") from None
    _check_keys(sc.get("host_checks", {}), HOST_CHECK_KEYS, "host_checks")
    for name, members in sc["suites"].items():
        for cid in members:
            if cid not in sc["cases"]:
                raise ScenarioError(f"suite {name}: unknown case {cid!r}")
    return sc


# --------------------------------------------------------------------------
# Tool, toolchain and identity resolution (no hard-coded user directories).
# --------------------------------------------------------------------------

def resolve_esp_emu(lock: dict) -> tuple[Path, list[str]]:
    """K1_ESP_EMU env -> tools/esp_emulator/esp-emu.local.json -> PATH. Each is hash-checked."""
    tried = []
    candidates = []
    if os.environ.get("K1_ESP_EMU"):
        candidates.append(("K1_ESP_EMU", Path(os.environ["K1_ESP_EMU"])))
    local = HERE / "esp-emu.local.json"
    if local.is_file():
        candidates.append(("esp-emu.local.json", Path(json.loads(local.read_text())["executable"])))
    which = shutil.which("esp-emu")
    if which:
        candidates.append(("PATH", Path(which)))
    for source, path in candidates:
        if not path.is_file():
            tried.append(f"{source}: {path} missing")
            continue
        digest = sha256_file(path)
        if digest != lock["executable_sha256"]:
            tried.append(f"{source}: {path} sha256 {digest} != lock")
            continue
        return path, tried
    raise SystemExit("pinned esp-emu not found; tried: " + "; ".join(tried or ["no candidate"]))


def platformio_core_dir() -> Path:
    return Path(os.environ.get("PLATFORMIO_CORE_DIR", Path.home() / ".platformio"))


def find_nm() -> Path | None:
    hits = sorted(glob.glob(str(platformio_core_dir() / "packages/toolchain-xtensa-esp*/bin/xtensa-esp32s3-elf-nm")))
    return Path(hits[0]) if hits else None


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False).stdout.strip()


IDENTITY_PATHS = ["SPECTRASYNQ_K1_FIRMWARE", "platformio.ini", "tools/esp_emulator", "scripts/platformio",
                  "tests/test_esp_emulator_acceptance.py", "tests/test_esp_emulator_report.py"]


def source_identity() -> dict:
    if not (REPO / ".git").exists():
        # A clean export (git archive) carries its commit in .k1-source-identity.json.
        marker = REPO / ".k1-source-identity.json"
        rec = json.loads(marker.read_text()) if marker.is_file() else {}
        h = hashlib.sha256()
        for rel in IDENTITY_PATHS:
            for p in sorted((REPO / rel).rglob("*")) if (REPO / rel).is_dir() else [REPO / rel]:
                if p.is_file() and "__pycache__" not in p.parts and ".pio" not in p.parts:
                    h.update(str(p.relative_to(REPO)).encode() + b"\0" + p.read_bytes())
        return {"repository": str(REPO), "kind": "export", "head": rec.get("commit", "unknown"),
                "branch": rec.get("branch"), "dirty_paths": [], "dirty_inputs_sha256": h.hexdigest(),
                "export_tree_sha256": h.hexdigest(), "identity_paths": IDENTITY_PATHS}
    status = git("status", "--porcelain", "--untracked-files=all", "--", *IDENTITY_PATHS)
    diff = subprocess.run(["git", "diff", "HEAD", "--binary", "--", *IDENTITY_PATHS], cwd=REPO,
                          capture_output=True, check=False).stdout
    h = hashlib.sha256(diff)
    untracked = []
    for line in status.splitlines():
        if line.startswith("?? "):
            rel = line[3:]
            p = REPO / rel
            if p.is_file() and "__pycache__" not in rel:
                h.update(rel.encode() + b"\0" + p.read_bytes())
                untracked.append(rel)
    return {
        "repository": str(REPO), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "head": git("rev-parse", "HEAD"), "dirty_paths": [l for l in status.splitlines() if "__pycache__" not in l],
        "dirty_inputs_sha256": h.hexdigest(), "untracked_inputs": untracked,
        "identity_paths": IDENTITY_PATHS,
    }


def effective_env(env: str) -> dict:
    out = subprocess.run(["pio", "project", "config", "--json-output"], cwd=REPO, capture_output=True,
                         text=True, check=True).stdout
    for name, items in json.loads(out):
        if name == f"env:{env}":
            return {k: v for k, v in items}
    raise SystemExit(f"env {env} not in platformio.ini")


def build(env: str, log: Path) -> dict:
    t0 = time.time()
    with log.open("w") as fh:
        # The repository's prescribed build-only wrapper (allowlisted envs; never uploads).
        rc = subprocess.run(["bash", "scripts/agent/pio-build.sh", env], cwd=REPO, stdout=fh,
                            stderr=subprocess.STDOUT).returncode
    d = REPO / ".pio/build" / env
    rec = {"env": env, "exit_code": rc, "seconds": round(time.time() - t0, 1), "log": str(log),
           "command": f"bash scripts/agent/pio-build.sh {env}"}
    for name in ("firmware.elf", "firmware.bin", "bootloader.bin", "partitions.bin"):
        if (d / name).is_file():
            rec[f"{name}_sha256"] = sha256_file(d / name)
    return rec


def flag_names(values) -> set[str]:
    names = set()
    for v in values if isinstance(values, list) else [values]:
        for tok in str(v).split():
            if tok.startswith("-D"):
                names.add(tok[2:].split("=", 1)[0])
    return names


def symbols(elf: Path, nm: Path | None) -> set[str]:
    if nm is None or not elf.is_file():
        return set()
    out = subprocess.run([str(nm), "-C", str(elf)], capture_output=True, text=True, check=False).stdout
    return {line.split()[-1] for line in out.splitlines() if line.split()}


FIXTURE_SYMBOL_RE = re.compile(r"k1_emu_fixture|k1_render_trace|rtrace_")
FIXTURE_STRINGS = (b"EMU_FIXTURE_ARMED", b"K1EMUSC2", b"EMU_END reason", b"RTRACE-BEGIN")


def normal_build_check(sc: dict, out: Path, nm: Path | None) -> dict:
    """WP3: actual normal-target build, effective flags and symbols, with a positive control."""
    prof = sc["profile"]
    rec = build(prof["product_env"], out / "build-product.log")
    env = effective_env(prof["product_env"])
    emu_env = effective_env(prof["env"])
    product_flags = flag_names(env.get("build_flags", []))
    emu_flags = flag_names(emu_env.get("build_flags", []))
    forbidden = set(prof["forbidden_in_product"])
    leaked = sorted(product_flags & forbidden)
    src_flags = " ".join(env.get("build_src_flags", []) if isinstance(env.get("build_src_flags"), list)
                         else [str(env.get("build_src_flags", ""))])
    forced_clock = "k1_emu_clock_force" in src_flags
    added = sorted(emu_flags - product_flags)
    removed = sorted(product_flags - emu_flags)
    elf = REPO / ".pio/build" / prof["product_env"] / "firmware.elf"
    emu_elf = REPO / ".pio/build" / prof["env"] / "firmware.elf"
    prod_syms = {s for s in symbols(elf, nm) if FIXTURE_SYMBOL_RE.search(s)}
    emu_syms = {s for s in symbols(emu_elf, nm) if FIXTURE_SYMBOL_RE.search(s)}
    blob = elf.read_bytes() if elf.is_file() else b""
    emu_blob_bytes = emu_elf.read_bytes() if emu_elf.is_file() else b""
    prod_strings = [s.decode() for s in FIXTURE_STRINGS if s in blob]
    emu_strings = [s.decode() for s in FIXTURE_STRINGS if s in emu_blob_bytes]
    identities = json.loads((REPO / "scripts/platformio/k1_device_identities.json").read_text())
    blocked = prof["env"] in identities.get("blocked_envs", {})
    ok = (rec["exit_code"] == 0 and not leaked and not forced_clock and not prod_syms and not prod_strings
          and set(added) == set(prof["adapter_flags"]) and not removed and blocked
          and bool(emu_syms) and bool(emu_strings) and nm is not None)
    return {
        "status": "PASS" if ok else "FAIL", "build": rec,
        "product_flags_forbidden_present": leaked, "product_forced_clock_include": forced_clock,
        "emu_minus_product_flags": added, "product_minus_emu_flags": removed,
        "declared_adapter_flags": prof["adapter_flags"],
        "product_fixture_symbols": sorted(prod_syms)[:20], "product_fixture_strings": prod_strings,
        "positive_control_emu_symbols": len(emu_syms), "positive_control_emu_strings": emu_strings,
        "emu_env_upload_blocked": blocked, "nm": str(nm) if nm else None,
    }


# --------------------------------------------------------------------------
# PCM assets
# --------------------------------------------------------------------------

def _read_c_array_inc(path: Path) -> bytes:
    text = path.read_text()
    body = text[text.index("{") + 1:text.rindex("}")]
    values = [int(v, 0) for v in re.findall(r"-?0x[0-9a-fA-F]+|-?\d+", body)]
    if all(-32768 <= v <= 32767 for v in values) and "int16_t" in text:
        return array.array("h", values).tobytes()
    return bytes(v & 0xFF for v in values)


def load_asset(sc: dict, aid: str, cache: dict, workdir: Path) -> tuple[bytes, dict]:
    if aid in cache:
        return cache[aid]
    a = sc["assets"][aid]
    rate = sc["time"]["rate_hz"]
    meta = {"id": aid, "kind": a["kind"], "qualification": a["qualification"], "origin": a.get("origin")}
    if a["kind"] == "c_array_inc":
        pcm = _read_c_array_inc(REPO / a["path"])
        meta["source"] = a["path"]
    elif a["kind"] == "inventory_excerpt":
        inv = json.loads((REPO / a["inventory"]).read_text())
        entry = next((f for f in inv["fixtures"] if f["id"] == a["fixture_id"]), None)
        if entry is None:
            raise ScenarioError(f"assets.{aid}: fixture {a['fixture_id']} not in inventory")
        src = Path(os.path.expanduser(entry["path"]))
        if not src.is_absolute():
            src = REPO / src
        meta.update({"inventory": a["inventory"], "fixture_id": a["fixture_id"], "fixture_status": entry.get("status"),
                     "fixture_required": entry.get("required"), "fixture_type": entry.get("fixture_type")})
        if not src.is_file():
            raise FileNotFoundError(f"asset {aid}: source {src} is not accessible")
        meta["source_sha256"] = sha256_file(src)
        if a.get("source_sha256") and a["source_sha256"] != meta["source_sha256"]:
            raise ScenarioError(f"assets.{aid}: source sha256 {meta['source_sha256']} != declared")
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise FileNotFoundError(f"asset {aid}: ffmpeg is not accessible for the declared conversion")
        ex = a["excerpt"]
        conv = a["conversion"]
        raw = workdir / f"asset-{aid}.raw.s16le"
        cmd = [ffmpeg, "-nostdin", "-v", "error", "-ss", f"{ex['start_ms'] / 1000:.3f}", "-t",
               f"{ex['duration_ms'] / 1000:.3f}", "-i", str(src), "-map", "0:a:0", "-ac", "1", "-ar", str(rate),
               "-af", "aresample=resampler=soxr" if conv.get("resampler") == "soxr" else "anull",
               "-f", "s16le", "-acodec", "pcm_s16le", str(raw)]
        subprocess.run(cmd, check=True)
        version = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True).stdout.splitlines()[0]
        samples = array.array("h")
        samples.frombytes(raw.read_bytes())
        peak = max((abs(s) for s in samples), default=0)
        target = conv["gain"]["peak"]
        gain = (target / peak) if peak else 1.0
        scaled = array.array("h", (max(-32768, min(32767, int(round(s * gain)))) for s in samples))
        pcm = scaled.tobytes()
        meta.update({"excerpt": ex, "conversion": {**conv, "ffmpeg": version, "argv": cmd[1:],
                                                   "decoded_peak": peak, "applied_gain": gain}})
    elif a["kind"] == "concat":
        parts = []
        segs = []
        for seg in a["segments"]:
            if "zeros_ms" in seg:
                n = seg["zeros_ms"] * rate // 1000
                parts.append(b"\0" * (2 * n))
                segs.append({"zeros_samples": n, "label": seg.get("label", "diagnostic zero section")})
            else:
                src_pcm, _ = load_asset(sc, seg["asset"], cache, workdir)
                lo = seg["from_ms"] * rate // 1000
                hi = seg["to_ms"] * rate // 1000
                parts.append(src_pcm[2 * lo:2 * hi])
                segs.append({"asset": seg["asset"], "from_sample": lo, "to_sample": hi, "label": seg.get("label")})
        pcm = b"".join(parts)
        meta["segments"] = segs
    else:  # pragma: no cover - schema already restricts kinds
        raise ScenarioError(aid)
    meta["samples"] = len(pcm) // 2
    meta["sha256"] = sha256_bytes(pcm)
    if a.get("sha256") and a["sha256"] != meta["sha256"]:
        raise ScenarioError(f"assets.{aid}: PCM sha256 {meta['sha256']} != declared {a['sha256']}")
    if a.get("samples") and a["samples"] != meta["samples"]:
        raise ScenarioError(f"assets.{aid}: {meta['samples']} samples != declared {a['samples']}")
    cache[aid] = (pcm, meta)
    return cache[aid]


# --------------------------------------------------------------------------
# Running one case
# --------------------------------------------------------------------------

def case_commands(sc: dict, case: dict) -> list[dict]:
    cmds = []
    if case.get("composition"):
        cmds += [{"hop": 0, "text": t, "expect": "applied"} for t in sc["compositions"][case["composition"]]["commands"]]
    cmds += [{"hop": c["hop"], "text": c["text"], "expect": c.get("expect", "applied")} for c in case.get("commands", [])]
    order = sorted(range(len(cmds)), key=lambda i: (cmds[i]["hop"], i))
    return [cmds[i] for i in order]


def case_client_lines(sc: dict, case: dict) -> list[dict]:
    """Command lines the existing client delivers, each at its declared replay hop."""
    cl = case.get("client") or {}
    lines = []
    if cl.get("composition"):
        lines += [{"hop": 0, "text": t, "expect": "applied"} for t in sc["compositions"][cl["composition"]]["commands"]]
    lines += [{"hop": c["hop"], "text": c["text"], "expect": c.get("expect", "applied")} for c in cl.get("commands", [])]
    order = sorted(range(len(lines)), key=lambda i: (lines[i]["hop"], i))
    return [lines[i] for i in order]


def resolve_client(sc: dict) -> tuple[list[str] | None, dict]:
    """The declared existing client, resolved on PATH. Never installed or fetched."""
    spec = sc.get("client") or {}
    argv = list(spec.get("argv") or [])
    exe = shutil.which(argv[0]) if argv else None
    rec = {"name": spec.get("name"), "declared_argv": argv, "executable": exe}
    if exe is None:
        return None, rec
    try:
        rec["version"] = subprocess.run([exe, "--version"], capture_output=True, text=True,
                                        timeout=60).stdout.strip().splitlines()[-1:]
    except (OSError, subprocess.SubprocessError) as exc:
        rec["version_error"] = repr(exc)
    return [exe, *argv[1:]], rec


def run_case(sc: dict, cid: str, out: Path, emu: Path, build_dir: Path, assets: dict,
             results: dict) -> dict:
    case = sc["cases"][cid]
    run_dir = out / cid
    run_dir.mkdir()
    hop = sc["time"]["hop_samples"]
    rate = sc["time"]["rate_hz"]
    rec = {"case": cid, "purpose": case.get("purpose"), "dir": str(run_dir)}
    try:
        pcm, pmeta = load_asset(sc, case["pcm"], assets, out)
    except FileNotFoundError as exc:
        rec.update(status="DEFERRED_EXTERNAL", reasons=[str(exc)])
        return rec
    rec["pcm"] = pmeta
    real = len(pcm) // 2
    if real % hop and case.get("partial_hop", "reject") == "reject":
        rec.update(status="FAIL", reasons=[f"PCM has {real} samples, not a multiple of {hop}, and partial_hop=reject"])
        return rec
    tail_hops = case.get("tail_hops", 0)
    total_hops = -(-real // hop) + tail_hops
    cap = case.get("capture", {})
    start = cap.get("start_hop", 0)
    end = cap.get("end_hop")
    end = total_hops if end is None else min(end, total_hops)
    every = cap.get("every", 1)
    n_capture = len(range(start, end, every))
    if n_capture > 2000:
        rec.update(status="FAIL", reasons=[f"window needs {n_capture} frames; trace capacity is 2000"])
        return rec
    cmds = case_commands(sc, case)
    client_lines = case_client_lines(sc, case)
    client_argv = None
    if client_lines:
        client_argv, client_rec = resolve_client(sc)
        rec["client_resolution"] = client_rec
        if client_argv is None:
            rec.update(status="DEFERRED_EXTERNAL",
                       reasons=[f"declared client {client_rec['declared_argv'][:1]} is not on PATH (named dependency)"])
            return rec
    for c in cmds + client_lines:
        if c["hop"] >= total_hops:
            rec.update(status="FAIL", reasons=[f"command at hop {c['hop']} is beyond the {total_hops} declared hops"])
            return rec
    blob_cmds = [(c["hop"], c["text"]) for c in cmds] + [(c["hop"], c["text"], emu_blob.CMD_CLIENT)
                                                        for c in client_lines]
    blob_cmds.sort(key=lambda e: e[0])
    ep = case.get("epoch", {"policy": "boot_monotonic"})
    flash_spec = case.get("flash", {"from": "blank", "recovery": False})
    run_id = uuid.uuid4().hex
    spec = emu_blob.BlobSpec(run_id=run_id, sample_rate=rate, hop_samples=hop, pcm=pcm,
                             pad_samples=tail_hops * hop, capture_start_hop=start, capture_end_hop=end,
                             capture_every=every, recovery=bool(flash_spec.get("recovery")),
                             commands=blob_cmds,
                             stall_ms=case.get("stall_ms", 20000), epoch_policy=ep["policy"],
                             declared_epoch_us=ep.get("us", 0),
                             novelty_trace=bool(case.get("trace_novelty")),
                             client_transport=bool(client_lines))
    blob, payload_crc = emu_blob.build_blob(spec)
    boot = (build_dir / "bootloader.bin").read_bytes()
    parts = (build_dir / "partitions.bin").read_bytes()
    app = (build_dir / "firmware.bin").read_bytes()
    if flash_spec["from"] == "blank":
        flash = emu_blob.merge_flash(boot, parts, app)
        input_fs = None
    else:
        src = results.get(flash_spec["from"])
        if not src or src.get("status") != "PASS" or not src.get("flash_after"):
            rec.update(status="FAIL", reasons=[f"source flash case {flash_spec['from']} did not produce a passing saved flash"])
            return rec
        flash = bytearray(Path(src["flash_after"]).read_bytes())
        # Same built image; only the LittleFS region carries over from the saved run.
        fresh = emu_blob.merge_flash(boot, parts, app)
        fs = emu_blob.littlefs_region(flash)
        flash = fresh
        flash[emu_blob.LITTLEFS_AT:emu_blob.LITTLEFS_AT + emu_blob.LITTLEFS_SIZE] = fs
        input_fs = sha256_bytes(fs)
    emu_blob.place_blob(flash, blob)
    flash_path = run_dir / "flash-run.bin"
    flash_path.write_bytes(flash)
    (run_dir / "scenario-blob.bin").write_bytes(blob)
    executed = {
        "flash_sha256": sha256_bytes(bytes(flash)),
        "app_region_matches_build": emu_blob.app_region(flash, len(app)) == app,
        "app_sha256": sha256_bytes(app), "scenario_blob_sha256": sha256_bytes(blob),
        "payload_crc32": f"{payload_crc:08x}", "input_littlefs_sha256": input_fs or sha256_bytes(emu_blob.littlefs_region(flash)),
        "input_flash_from": flash_spec["from"], "image_patched": False,
    }
    elf = run_dir / "firmware.elf"
    shutil.copy(build_dir / "firmware.elf", elf)
    emu_cfg = sc["profile"]["emulator"]
    base = [str(emu), "--chip", emu_cfg["chip"], "--firmware", str(flash_path), "--elf", str(elf),
            "--psram-size", emu_cfg["psram"], "--net", "user",
            "--batch-size", str(emu_cfg["batch_size"]), "--timeout", f"{emu_cfg['timeout_s']}s"]
    if case.get("save_state"):
        base.append("--save-state")
    t0 = time.time()
    client_reasons: list[str] = []
    if client_lines:
        # Existing client -> run-owned pty -> product USBSerial; trace on UART1.
        cres = emu_client.run_client_case(
            emu_argv=base, client_argv=client_argv,
            lines=[emu_client.ClientLine(c["hop"], c["text"], c["expect"]) for c in client_lines],
            run_dir=run_dir, timeout_s=emu_cfg["timeout_s"] + 60)
        code = cres.exit_code
        argv = [str(emu), *cres.record["emulator_argv"]]
        client_reasons = [f"client: {r}" for r in cres.reasons]
        terminal = (run_dir / "client-terminal.txt").read_bytes()
        rb_reasons, segments = emu_client.check_readback(terminal, cres.record["typed"])
        client_reasons += [f"client readback: {r}" for r in rb_reasons]
        rec["client"] = {**cres.record, "readback": segments}
        # The emulator's own --exit-on follows the USB console, so the runner
        # observes the terminal string on the UART1 trace and stops the child.
        process = ec.Process(code, cres.terminal_observed)
    else:
        argv = [*base[:base.index("--batch-size")], "--console", "uart0", *base[base.index("--batch-size"):],
                "--exit-on", "[RTRACE-END]"]
        with (run_dir / "uart.txt").open("w") as so, (run_dir / "emu-stderr.txt").open("w") as se:
            try:
                proc = subprocess.run(argv, stdout=so, stderr=se, timeout=emu_cfg["timeout_s"] + 60)
                code = proc.returncode
            except subprocess.TimeoutExpired:
                code = -9
        stderr = (run_dir / "emu-stderr.txt").read_text(errors="replace")
        process = ec.Process(code, "Exit-on string" in stderr)
    wall = round(time.time() - t0, 2)
    uart = (run_dir / "uart.txt").read_text(errors="replace")
    (run_dir / "exit_code.txt").write_text(f"{code}\n")
    expect = ec.Expect(
        run_id=run_id, payload_crc32=payload_crc, real_samples=real, pad_samples=tail_hops * hop,
        rate_hz=rate, hop_samples=hop, capture_start_hop=start, capture_end_hop=end, capture_every=every,
        recovery=bool(flash_spec.get("recovery")), commands=cmds,
        end_reason=case.get("expect", {}).get("end_reason", "eof"), saves=case.get("expect", {}).get("saves"),
        epoch_policy=ep["policy"], declared_epoch_us=ep.get("us"),
        client_commands=client_lines, client_transport=bool(client_lines))
    decode_error = None
    cap_obj = None
    try:
        cap_obj = ec.decode(uart)
    except ec.CaptureError as exc:
        decode_error = str(exc)
    reasons = ec.accept(cap_obj, expect, process, decode_error) + client_reasons
    status = "PASS" if not reasons else "FAIL"
    flash_after = None
    if case.get("save_state"):
        flash_after = str(flash_path)
        executed["output_littlefs_sha256"] = sha256_bytes(emu_blob.littlefs_region(flash_path.read_bytes()))
        executed["littlefs_changed"] = executed["output_littlefs_sha256"] != executed["input_littlefs_sha256"]
    rec.update({
        "status": status, "reasons": reasons, "run_id": run_id, "argv": argv[1:], "exit_code": code,
        "exit_on_found": process.exit_on_found, "wall_seconds": wall, "executed": executed,
        "requested": {"real_samples": real, "tail_hops": tail_hops, "total_hops": total_hops,
                      "capture": {"start_hop": start, "end_hop": end, "every": every, "frames": n_capture},
                      "epoch": ep, "commands": cmds, "client_commands": client_lines,
                      "flash": flash_spec, "stall_ms": spec.stall_ms},
        "flash_after": flash_after,
    })
    if cap_obj is not None:
        rec["observed"] = {
            "frames": len(cap_obj.frames), "payload_sha256": ec.payload_sha256(cap_obj),
            "header": cap_obj.header, "end": cap_obj.ends[0] if cap_obj.ends else None,
            "epoch": cap_obj.epochs[0] if cap_obj.epochs else None,
            "saves": cap_obj.saves, "rejects": cap_obj.rejects, "power_limits": cap_obj.power_limits,
            "boot_show_state": cap_obj.show_states[0]["hex"] if cap_obj.show_states else None,
            "nonzero_frames": {"A": sum(1 for f in cap_obj.frames if any(f.A)),
                               "B": sum(1 for f in cap_obj.frames if any(f.B))},
        }
        if client_lines:
            # Original text, parser outcome, and the generation the applied state
            # first reaches (a line applied before hop h affects generation h+1).
            hstates = [s for s in cap_obj.show_states if s.get("when") == "hcmd"]
            rec["observed"]["client_commands"] = [
                {"hop": int(h.get("hop", -1)), "text": h.get("text"),
                 "rejected": (r or {}).get("rejected") == "1",
                 "first_effect_generation": int(h.get("hop", -1)) + 1,
                 "show_state_hex": (s or {}).get("hex")}
                for h, r, s in zip(cap_obj.host_commands,
                                   cap_obj.host_results + [None] * len(cap_obj.host_commands),
                                   hstates + [None] * len(cap_obj.host_commands))]
            rec["observed"]["client_gates"] = cap_obj.client_gates
    rec["_capture"] = cap_obj
    rec["_uart"] = uart
    rec["_expect"] = expect
    rec["_process"] = process
    return rec


# --------------------------------------------------------------------------
# Comparisons
# --------------------------------------------------------------------------

def _by_hop(cap: ec.Capture, hop_samples: int) -> dict[int, ec.Frame]:
    out = {}
    for f in cap.frames:
        h = ec.frame_hop(cap, f, hop_samples)
        if h is not None:
            out[h] = f
    return out


def _decode_show_state(hex_text: str) -> dict:
    """Independent reader of the K1ShowState V1 encoding (oracle for the firmware codec)."""
    b = bytes.fromhex(hex_text)
    magic, version, _ = struct.unpack_from("<IHH", b, 0)
    off = 8

    def preset():
        nonlocal off
        fmt = "<BBffffffBBBBfBB"
        vals = struct.unpack_from(fmt, b, off)
        off += struct.calcsize(fmt)
        keys = ["lightshow_mode", "mirror_enabled", "photons", "chroma", "mood", "saturation", "prism_count",
                "incandescent_filter", "incandescent_mode", "base_coat", "reverse_order", "auto_color_shift",
                "base_coat_intensity", "palette_index", "palette_mode_enabled"]
        return dict(zip(keys, vals))

    p, s = preset(), preset()
    e = dict(zip(["enabled", "mode", "strength", "spread", "rotation", "uniform", "dual"],
                 struct.unpack_from("<BBfBBBB", b, off)))
    off += struct.calcsize("<BBfBBBB")
    enable = b[off]
    off += 1
    crc = struct.unpack_from("<I", b, off)[0]
    return {"magic": magic, "version": version, "primary": p, "secondary": s, "edge": e,
            "enable_secondary": enable, "crc_ok": zlib.crc32(b[8:off]) == crc, "bytes": len(b)}


def _encode_show_state(d: dict) -> str:
    keys = ["lightshow_mode", "mirror_enabled", "photons", "chroma", "mood", "saturation", "prism_count",
            "incandescent_filter", "incandescent_mode", "base_coat", "reverse_order", "auto_color_shift",
            "base_coat_intensity", "palette_index", "palette_mode_enabled"]
    payload = struct.pack("<BBffffffBBBBfBB", *[d["primary"][k] for k in keys])
    payload += struct.pack("<BBffffffBBBBfBB", *[d["secondary"][k] for k in keys])
    e = d["edge"]
    payload += struct.pack("<BBfBBBB", e["enabled"], e["mode"], e["strength"], e["spread"], e["rotation"],
                           e["uniform"], e["dual"])
    payload += bytes([d["enable_secondary"]])
    return (struct.pack("<IHH", d["magic"], d["version"], 0) + payload
            + struct.pack("<I", zlib.crc32(payload) & 0xFFFFFFFF)).hex()


FIELD_OF_COMMAND = {
    "set_mode": ("primary", "lightshow_mode"), "secondary_mode": ("secondary", "lightshow_mode"),
    "palette_index": ("primary", "palette_index"), "secondary_palette_index": ("secondary", "palette_index"),
    "photons": ("primary", "photons"), "secondary_photons": ("secondary", "photons"),
    "chroma": ("primary", "chroma"), "secondary_chroma": ("secondary", "chroma"),
    "mood": ("primary", "mood"), "secondary_mood": ("secondary", "mood"),
    "saturation": ("primary", "saturation"), "secondary_saturation": ("secondary", "saturation"),
    "edge_enabled": ("edge", "enabled"), "edge_strength": ("edge", "strength"), "edge_spread": ("edge", "spread"),
    "secondary_enabled": (None, "enable_secondary"),
}


def requested_fields_mismatch(commands: list[dict], state: dict) -> list[str]:
    """Check the applied state holds what each composition command asked for."""
    bad = []
    for c in commands:
        name, _, value = c["text"].partition("=")
        if name not in FIELD_OF_COMMAND:
            continue
        grp, key = FIELD_OF_COMMAND[name]
        got = state[key] if grp is None else state[grp][key]
        want = {"true": 1, "false": 0}.get(value, None)
        want = float(value) if want is None else want
        if abs(float(got) - want) > 1e-6:
            bad.append(f"{name}: applied {got} != requested {value}")
    return bad


def last_state_before_save(cap: ec.Capture) -> str | None:
    """Applied show state (shown readback) immediately before the save command."""
    save_hop = next((int(c["hop"]) for c in cap.commands + cap.host_commands if c["text"] == "save_show"), None)
    best = None
    for st in cap.show_states:
        if st["when"] == "shown" and save_hop is not None and int(st["gen"]) <= save_hop:
            best = st["hex"]
    return best


def evaluate_comparison(comp: dict, results: dict, hop_samples: int) -> dict:
    kind = comp["kind"]
    a = results.get(comp.get("a"))
    b = results.get(comp.get("b"))
    out = {"id": comp["id"], "kind": kind, "a": comp.get("a"), "b": comp.get("b"),
           "criterion": comp.get("criterion"), "label": comp.get("label")}
    needed = [x for x in (comp.get("a"), comp.get("b"), comp.get("before_case"), comp.get("default_case")) if x]
    missing = [x for x in needed if x not in results]
    if missing:
        out.update(status="NOT_RUN", detail=f"case(s) not in this suite: {missing}")
        return out
    deferred = [x for x in needed if results[x].get("status") == "DEFERRED_EXTERNAL"]
    if deferred:
        out.update(status="DEFERRED_EXTERNAL", detail=f"depends on deferred case(s) {deferred}")
        return out
    failed = [x for x in needed if results[x].get("status") != "PASS"]
    if failed:
        out.update(status="FAIL", detail=f"case(s) {failed} were not accepted")
        return out
    ca, cb = a["_capture"], b["_capture"] if b else None
    if kind == "case":
        first = ca.sidecars.get(0)
        end = ca.ends[0] if ca.ends else {}
        ep = ca.epochs[0] if ca.epochs else {}
        out.update(status="PASS", detail=(
            f"accepted: end={end.get('reason')} admitted={end.get('admitted')} processed={end.get('processed')} "
            f"published={end.get('published')} shown={end.get('last_shown')} captured={end.get('captured')}; "
            f"epoch {ep.get('policy')} {ep.get('epoch_us')} us; first captured hop app_us={first.app_us if first else None} "
            f"(processed {first.processed if first else None})"))
        return out
    if kind == "semantic_continuity":
        frames = ca.frames
        ms = [ca.meanings.get(f.index) for f in frames]
        missing = sum(1 for m in ms if m is None)
        mismatched = [f.index for f, m in zip(frames, ms) if m is not None and m.producer() != m.consumed()]
        gens_ok = all(m.c_generation == ca.sidecars[f.index].generation for f, m in zip(frames, ms) if m)
        seq = [(m.c_onset_seq, m.c_beat_seq) for m in ms if m]
        monotone = all(b[0] >= a[0] and b[1] >= a[1] for a, b in zip(seq, seq[1:]))
        ok = bool(frames) and not missing and not mismatched and gens_ok and monotone
        out.update(status="PASS" if ok else "FAIL", detail=(
            f"{len(frames)} frames: producer meaning == render-thread meaning for the same generation on "
            f"{len(frames) - len(mismatched) - missing}/{len(frames)} (first mismatch {mismatched[:1]}); onset/beat sequence "
            f"monotone={monotone}; onset_seq {seq[0][0] if seq else None}->{seq[-1][0] if seq else None}, "
            f"beat_seq {seq[0][1] if seq else None}->{seq[-1][1] if seq else None}"))
        return out
    if kind == "tempo_lane":
        # The repository's own production tempo-lane rule (k1_av_layer_classifier.py) on the
        # render-thread tempo view of every scored frame; no thresholds invented here.
        sys.path.insert(0, str(REPO / "scripts/regression-harness"))
        import k1_av_layer_classifier as avc  # noqa: WPS433
        fx = comp["expect"]
        rows = []
        prev_onset = None
        for f in ca.frames:
            m = ca.meanings[f.index]
            rows.append({"t_ms": ca.sidecars[f.index].app_us // 1000, "bpm": float(m.c_bpm), "lock": m.c_locked,
                         "conf": float(m.c_confidence), "beat": m.c_beat_tick,
                         "onset": int(prev_onset is not None and m.c_onset_seq > prev_onset)})
            prev_onset = m.c_onset_seq
        summary = avc.summarise_production_ap_stream(rows, warm_ms=0, expected_bpm=fx["expected_bpm"])
        summary["lock_frac"] = sum(r["lock"] for r in rows) / max(1, len(rows))
        summary["max_conf"] = max((r["conf"] for r in rows), default=0.0)
        cls, why = avc.classify_production_tempo(summary, expected_bpm=fx["expected_bpm"],
                                                 fixture_type=fx["fixture_type"], tempo_gate=fx.get("tempo_gate"))
        ok = cls in fx["accept"]
        out.update(status="PASS" if ok else "FAIL", classification=cls, detail=(
            f"k1_av_layer_classifier: {cls} ({why}); median bpm {summary['warm_median_bpm']}, near-target "
            f"{summary['warm_near_target_rows']}/{summary['warm_near_target_denominator']}, locked-near "
            f"{summary['warm_locked_near_rows']}, lock_frac {summary['lock_frac']:.2f}, max_conf {summary['max_conf']:.3f}, "
            f"beat ticks {summary['beat_tick_count']}, onsets {summary['onset_count']}"))
        return out
    if kind == "startup_quiet_return":
        x = comp["expect"]
        rows = [(ec.frame_hop(ca, f, hop_samples), ca.sidecars[f.index].app_us, any(f.A), any(f.B)) for f in ca.frames]
        end = ca.ends[0] if ca.ends else {}
        startup_frames = int(end.get("pre_audio_shows", 0))
        before_gate = [r for r in rows if r[1] < x["fade_gate_us"]]
        a_dark_before_gate = bool(before_gate) and not any(r[2] for r in before_gate)
        first_a = next((r for r in rows if r[2]), None)
        b_lit_from_start = bool(rows) and rows[0][3]
        quiet = [r for r in rows if x["zero_from_hop"] <= r[0] < x["return_hop"]]
        last_quiet = quiet[-1] if quiet else None
        dark_by_return = last_quiet is not None and not last_quiet[2] and not last_quiet[3]
        first_dark = next((r[0] for r in quiet if not r[2] and not r[3]), None)
        back = next((r for r in rows if r[0] >= x["return_hop"]), None)
        lit_on_return = back is not None and back[2] and back[3]
        checks = {"startup_traversed": startup_frames >= x["min_startup_frames"],
                  "A_dark_below_fade_gate": a_dark_before_gate,
                  "A_lit_after_gate": first_a is not None and first_a[1] >= x["fade_gate_us"],
                  "B_lit_from_first_hop": b_lit_from_start, "both_dark_before_return": dark_by_return,
                  "both_lit_on_first_return_hop": lit_on_return}
        out.update(status="PASS" if all(checks.values()) else "FAIL",
                   detail=(f"{checks}; startup frames before audio={startup_frames}; first lit A hop={first_a[0] if first_a else None} "
                           f"at app {first_a[1] if first_a else None} us; zero section from hop {x['zero_from_hop']} dark from "
                           f"hop {first_dark}; first return frame hop {back[0] if back else None}"))
        return out
    if kind in ("equal", "differs"):
        va, vb = ec.deterministic_view(ca), ec.deterministic_view(cb)
        same = va == vb
        ok = same if kind == "equal" else not same
        out.update(status="PASS" if ok else "FAIL",
                   detail=f"deterministic payload+source metadata equal={same} frames={len(va)}/{len(vb)} "
                          f"sha {ec.payload_sha256(ca)[:12]}/{ec.payload_sha256(cb)[:12]}")
    elif kind == "isolation":
        edge = 0 if comp["edge"] == "A" else 1
        fa, fb = _by_hop(ca, hop_samples), _by_hop(cb, hop_samples)
        if sorted(fa) != sorted(fb):
            out.update(status="FAIL", detail="hop sets differ; not comparable")
            return out
        pre_diff = changed = other = 0
        first = None
        for h in sorted(fa):
            x, y = (fa[h].A, fa[h].B), (fb[h].A, fb[h].B)
            if h < comp["from_hop"]:
                pre_diff += x != y
            else:
                if x[edge] != y[edge]:
                    changed += 1
                    first = h if first is None else first
                other += x[1 - edge] != y[1 - edge]
        lim = sorted({s.limit_scale for s in cb.sidecars.values()} | {s.limit_scale for s in ca.sidecars.values()})
        ok = pre_diff == 0 and changed > 0 and other == 0 and first == comp["from_hop"] and lim == [255]
        out.update(status="PASS" if ok else "FAIL",
                   detail=f"edge {comp['edge']}: pre-command frames differing={pre_diff}, changed frames={changed} "
                          f"(first at hop {first}), other-edge frames differing={other}, limiter scales={lim}")
    elif kind == "limit_coupling":
        edge = 0 if comp["edge"] == "A" else 1
        fa, fb = _by_hop(ca, hop_samples), _by_hop(cb, hop_samples)
        sa, sb = ({ec.frame_hop(c, f, hop_samples): c.sidecars[f.index] for f in c.frames} for c in (ca, cb))
        other_native_diff = sum(1 for h in fa if h in fb and (fa[h].A, fa[h].B)[1 - edge] != (fb[h].A, fb[h].B)[1 - edge])
        binding = sum(1 for h, s in sa.items() if s.limit_scale < 255)
        scale_changed = sum(1 for h in sa if h in sb and h >= comp["from_hop"] and sa[h].limit_scale != sb[h].limit_scale)
        pre_changed = sum(1 for h in sa if h in sb and h < comp["from_hop"] and sa[h].limit_scale != sb[h].limit_scale)
        installed = bool(ca.power_limits) and bool(cb.power_limits)
        ok = installed and binding > 0 and other_native_diff == 0 and scale_changed > 0 and pre_changed == 0
        out.update(status="PASS" if ok else "FAIL",
                   detail=f"FastLED power limit installed={installed}; base frames limited={binding}; "
                          f"untouched edge native frames differing={other_native_diff}; shared submission scale "
                          f"changed in {scale_changed} frames after the {comp['edge']}-only command "
                          f"(before: {pre_changed}). The limit is one scale over every registered controller, "
                          f"so an {comp['edge']}-only change moves the other edge's emitted brightness.")
    elif kind == "recovery_state":
        save = results[comp["before_case"]]["_capture"]
        saved = last_state_before_save(save)
        recovered = cb.show_states[0]["hex"] if cb.show_states else None
        fields = None
        if saved and recovered:
            ds, dr = _decode_show_state(saved), _decode_show_state(recovered)
            fields = sorted(f"{grp}.{k}" for grp in ("primary", "secondary", "edge")
                            for k in ds[grp] if ds[grp][k] != dr[grp][k])
            if ds["enable_secondary"] != dr["enable_secondary"]:
                fields.append("enable_secondary")
        saves_ok = any(s.get("kind") == "show" and s.get("ok") == "1" for s in save.saves)
        changed_fs = results[comp["before_case"]]["executed"].get("littlefs_changed")
        cmds = len(cb.commands) + len(cb.host_commands)
        req = results[comp["before_case"]]["requested"]
        requested = [c for c in req["commands"] + req.get("client_commands", []) if c["hop"] == 0]
        not_applied = requested_fields_mismatch(requested, _decode_show_state(saved)) if saved else ["no state"]
        ok = (bool(saved) and saved == recovered and saves_ok and changed_fs and cmds == 0 and not cb.saves
              and not not_applied)
        out.update(status="PASS" if ok else "FAIL",
                   detail=f"applied state before save == recovered boot state: {saved == recovered}; "
                          f"differing fields={fields}; show save ok={saves_ok}; LittleFS changed={changed_fs}; "
                          f"recovery commands={cmds} saves={len(cb.saves)}; requested composition fields "
                          f"applied before save: {not not_applied} {not_applied[:3]}; "
                          f"{_decode_show_state(recovered)['bytes'] if recovered else 0}-byte V1 record")
    elif kind == "fallback_state":
        save = results[comp["before_case"]]["_capture"]
        default = results[comp["default_case"]]["_capture"]
        saved_hex = [st["hex"] for st in save.show_states if st["when"] == "shown"][-1]
        ds, dd = _decode_show_state(saved_hex), _decode_show_state(default.show_states[0]["hex"])
        expected = {**dd, "primary": {**ds["primary"], "palette_index": dd["primary"]["palette_index"],
                                      "palette_mode_enabled": dd["primary"]["palette_mode_enabled"]}}
        exp_hex = _encode_show_state(expected)
        rec_hex = cb.show_states[0]["hex"] if cb.show_states else None
        show_saved = any(s.get("kind") == "show" for s in save.saves)
        cfg_saved = any(s.get("kind") == "config" for s in save.saves)
        ok = rec_hex == exp_hex and cfg_saved and not show_saved and not cb.commands and not cb.saves
        out.update(status="PASS" if ok else "FAIL",
                   detail=f"config saved={cfg_saved}, show file saved={show_saved}; recovered == implementation "
                          f"fallback (primary from saved CONFIG, palettes from the boot palette lock, secondary/edge "
                          f"compiled defaults): {rec_hex == exp_hex}")
    return out


# --------------------------------------------------------------------------
# Planted negative cases: every one goes through ec.accept
# --------------------------------------------------------------------------

def r2_counterexample() -> str:
    """The R2 malformed capture: two valid-CRC frames claiming 135, px=999, bpp=8, edges=7."""
    lines = []
    crc = 0
    for i, (gen, samples) in enumerate(((1, 96), (128, 12288))):
        a = bytes([i + 1]) * 960
        b = bytes([i + 2]) * 960
        crc = zlib.crc32(b, zlib.crc32(a, crc))
        hexa = "".join(a[j + 2:j + 4].hex() + a[j:j + 2].hex() + a[j + 4:j + 6].hex() for j in range(0, 960, 6))
        hexb = "".join(b[j + 2:j + 4].hex() + b[j:j + 2].hex() + b[j + 4:j + 6].hex() for j in range(0, 960, 6))
        lines.append(f"M,{i},{gen},{samples}")
        lines.append(f"F,{i},{i},18,{hexa},{hexb}")
    return (f"[RTRACE-BEGIN frames=135 every=1 px=999 fmt=rgb16hex bpp=8 edges=7 crc32={crc:08x}]\n"
            + "\n".join(lines) + "\n[RTRACE-END]\n")


def planted_cases(base: dict) -> list[dict]:
    uart, expect, process = base["_uart"], base["_expect"], base["_process"]
    lines = uart.splitlines()
    out = []

    def run(name: str, text: str, exp: ec.Expect, proc: ec.Process, needle: str) -> None:
        err = None
        cap = None
        try:
            cap = ec.decode(text)
        except ec.CaptureError as exc:
            err = str(exc)
        reasons = ec.accept(cap, exp, proc, err)
        hit = any(needle in r for r in reasons)
        out.append({"name": name, "rejected": bool(reasons), "expected_reason": needle,
                    "reason_matched": hit, "ok": bool(reasons) and hit, "reasons": reasons[:4]})

    def edit(pred, fn) -> str:
        done = False
        res = []
        for line in lines:
            if not done and pred(line):
                done = True
                r = fn(line)
                if r is not None:
                    res.extend(r if isinstance(r, list) else [r])
            else:
                res.append(line)
        return "\n".join(res) + "\n"

    run("r2-malformed-counterexample", r2_counterexample(), expect, ec.Process(1, False), "header px")
    run("missing-sidecar", edit(lambda l: l.startswith("S,"), lambda l: None), expect, process, "without a sidecar")
    run("duplicate-sidecar", edit(lambda l: l.startswith("S,"), lambda l: [l, l]), expect, process, "duplicate sidecar")
    run("missing-channel", edit(lambda l: l.startswith("F,"), lambda l: ",".join(l.split(",")[:5])), expect, process,
        "two edges")
    run("corrupted-payload", edit(lambda l: l.startswith("F,"),
                                  lambda l: l[:-1] + ("0" if l[-1] != "0" else "1")), expect, process, "native crc")
    wrong = ec.Expect(**{**expect.__dict__, "run_id": uuid.uuid4().hex})
    run("wrong-invocation", uart, wrong, process, "armed run=")
    run("failed-process", uart, expect, ec.Process(1, True), "process exit code 1")
    run("missing-terminal", uart.replace("[RTRACE-END]", "[RTRACE-CUT]"), expect, process, "RTRACE-END count")
    run("duplicate-header-key", uart.replace("[RTRACE-BEGIN frames=", "[RTRACE-BEGIN px=160 frames=", 1), expect,
        process, "duplicate key px")
    run("historical-receipt-substituted",
        uart.replace(f"run={expect.run_id}", "run=physical-rpl-004"), expect, process, "armed run=")
    return out


# --------------------------------------------------------------------------
# Historical references (labelled; never part of the software result)
# --------------------------------------------------------------------------

def historical_references(sc: dict) -> list[dict]:
    out = []
    for item in sc.get("historical", []):
        path = Path(os.path.expanduser(item["path"]))
        rec = {"id": item["id"], "path": str(path), "profile": item["profile"], "role": "historical reference only"}
        if not path.is_file():
            rec["status"] = "unavailable"
            out.append(rec)
            continue
        text = path.read_text(errors="replace")
        m = re.search(r"\[RTRACE-BEGIN ([^\]]*)\]", text)
        fields = dict(t.split("=", 1) for t in (m.group(1).split() if m else []) if "=" in t)
        crc = 0
        pairs = 0
        h = hashlib.sha256()
        for line in text.splitlines():
            if line.startswith("F,"):
                p = line.split(",")
                if len(p) >= 6:
                    a, b = ec.dump_hex_to_wire(p[4]), ec.dump_hex_to_wire(p[5])
                    crc = zlib.crc32(b, zlib.crc32(a, crc))
                    h.update(a)
                    h.update(b)
                    pairs += 1
        rec.update(status="decoded", pairs=pairs, crc32=f"{crc & 0xFFFFFFFF:08x}", header_crc32=fields.get("crc32"),
                   paired_native_sha256=h.hexdigest(),
                   matches_recorded=(f"{crc & 0xFFFFFFFF:08x}" == item.get("crc32") and h.hexdigest() == item.get("sha256")))
        out.append(rec)
    return out


# --------------------------------------------------------------------------
# Host checks
# --------------------------------------------------------------------------

def host_checks(sc: dict, out: Path) -> dict:
    """Repository commit gate: the declared pytest selection and the shipping builds."""
    cfg = sc.get("host_checks", {})
    tests = cfg.get("pytest", [])
    # A clean export has no .git. Tests that read git history (pinned-commit receipts, tracked-file
    # checks) cannot run there; they are excluded by name, recorded, and run in the checkout.
    excluded = list(cfg.get("requires_git", [])) if identity_kind() == "export" else []
    ignore = [f"--ignore={p}" for p in excluded]
    log = out / "host-pytest.log"
    with log.open("w") as fh:
        rc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *ignore, *tests],
                            cwd=REPO, stdout=fh, stderr=subprocess.STDOUT).returncode
    tail = log.read_text().strip().splitlines()[-1:] or [""]
    builds = [build(env, out / f"build-{env}.log") for env in cfg.get("builds", [])]
    ok = rc == 0 and all(b["exit_code"] == 0 for b in builds)
    summary = tail[0] + "".join(f"; pio run -e {b['env']} exit={b['exit_code']}" for b in builds)
    if excluded:
        summary += f"; {len(excluded)} git-history test file(s) excluded in this export (run in the checkout)"
    return {"status": "PASS" if ok else "FAIL", "exit_code": rc, "tests": tests, "summary": summary,
            "log": str(log), "builds": builds, "excluded_without_git": excluded}


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--suite", default="default")
    args = parser.parse_args()
    scenario_path = Path(args.scenario)
    if not scenario_path.is_absolute():
        scenario_path = (Path.cwd() / scenario_path).resolve()
    try:
        sc = load_scenario(scenario_path)
    except (ScenarioError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f"scenario rejected before build/run: {exc}")
    if args.suite not in sc["suites"]:
        raise SystemExit(f"unknown suite {args.suite!r}; scenario declares {sorted(sc['suites'])}")
    out = Path(args.output)
    if not out.is_absolute():
        out = (Path.cwd() / out).resolve()
    if out.exists():
        raise SystemExit(f"output already exists, choose a fresh directory: {out}")
    out.mkdir(parents=True)
    invocation = uuid.uuid4().hex
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    lock_path = (scenario_path.parent / sc["tool_lock"]).resolve()
    lock = json.loads(lock_path.read_text())
    emu, tried = resolve_esp_emu(lock)
    nm = find_nm()
    identity = source_identity()
    shutil.copy(scenario_path, out / "scenario.json")
    print(f"invocation {invocation} source {identity['head'][:12]} dirty_inputs {identity['dirty_inputs_sha256'][:12]}")
    emu_build = build(sc["profile"]["env"], out / "build-emu.log")
    if emu_build["exit_code"] != 0:
        print("emulator env build failed; see", emu_build["log"])
    build_dir = REPO / ".pio/build" / sc["profile"]["env"]
    product = normal_build_check(sc, out, nm)
    hosts = host_checks(sc, out)
    results: dict[str, dict] = {}
    assets: dict = {}
    for cid in sc["suites"][args.suite]:
        if emu_build["exit_code"] != 0:
            results[cid] = {"case": cid, "status": "FAIL", "reasons": ["emulator env build failed"]}
            continue
        print(f"case {cid} ...", flush=True)
        results[cid] = run_case(sc, cid, out, emu, build_dir, assets, results)
        r = results[cid]
        print(f"  {r['status']} {('; '.join(r.get('reasons', [])[:3]))}", flush=True)
    comparisons = [evaluate_comparison(c, results, sc["time"]["hop_samples"]) for c in sc.get("comparisons", [])]
    planted_base = results.get(sc.get("planted", {}).get("base_case", ""))
    planted = planted_cases(planted_base) if planted_base and planted_base.get("status") == "PASS" else []
    history = historical_references(sc)
    criteria = criteria_matrix(sc, results, comparisons, planted, product, hosts, emu_build)
    enabled = [c for c in criteria if c["status"] not in ("DEFERRED_EXTERNAL", "NOT_APPLICABLE")]
    software_complete = bool(enabled) and all(c["status"] == "PASS" for c in enabled)
    overall = "SOFTWARE COMPLETE" if software_complete else "SOFTWARE INCOMPLETE"
    result = {
        "schema": "k1-emu-result/3", "invocation_id": invocation, "started_utc": started,
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "overall": overall,
        "suite": args.suite, "hardware_accessed": False,
        "scenario": {"path": str(scenario_path), "sha256": sha256_file(scenario_path), "name": sc["name"]},
        "tool": {"lock": str(lock_path), "lock_sha256": sha256_file(lock_path), "executable": str(emu),
                 "executable_sha256": lock["executable_sha256"], "version": lock["version"], "rejected_candidates": tried},
        "source": identity, "emu_build": emu_build, "profile": sc["profile"],
        "effective_emu_env": effective_env(sc["profile"]["env"]),
        "normal_build": product, "host_checks": hosts,
        "cases": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in results.items()},
        "comparisons": comparisons, "planted": planted, "criteria": criteria,
        "historical_references": history,
        "deferred": sc.get("fields_doc", {}).get("deferred", []),
    }
    (out / "result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    write_report(sc, out, result, results)
    rc = result.get("report_checks", {"status": "FAIL", "detail": "report not built"})
    for c in criteria:
        if c["id"] == "SW10":
            c["status"] = rc["status"]
            c["evidence"] = f"report.html from this invocation; {rc.get('detail')}"
    enabled = [c for c in criteria if c["status"] not in ("DEFERRED_EXTERNAL", "NOT_APPLICABLE") and not c.get("optional")]
    software_complete = bool(enabled) and all(c["status"] == "PASS" for c in enabled)
    overall = "SOFTWARE COMPLETE" if software_complete else "SOFTWARE INCOMPLETE"
    result["overall"] = overall
    result["criteria"] = criteria
    (out / "result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    write_report(sc, out, result, results, check=False)  # header carries the final criteria
    for c in criteria:
        print(f"{c['id']:5} {c['status']:18} {c['evidence'][:150]}")
    print(f"result {out / 'result.json'}")
    print(f"report {out / 'report.html'}")
    print(overall)
    return 0 if software_complete else 1


def write_report(sc: dict, out: Path, result: dict, results: dict, check: bool = True) -> None:
    cases = []
    for cid, r in results.items():
        cap = r.get("_capture")
        ep = (cap.epochs[0] if cap is not None and cap.epochs else {})
        req = r.get("requested", {})
        cases.append(rd.case_record(
            cid, cap, status=r["status"], reasons=r.get("reasons", []), run_id=r.get("run_id", ""),
            profile={"env": sc["profile"]["env"], "product_env": sc["profile"]["product_env"],
                     "trace": sc["profile"]["trace"]["boundary"]},
            initial_state={"flash": req.get("flash", {}).get("from", "blank"),
                           "recovery": req.get("flash", {}).get("recovery", False),
                           "startup": "normal (product startup animation and fade)",
                           "epoch": req.get("epoch"), "epoch_us": int(ep.get("epoch_us", 0)) if ep else None},
            window=req.get("capture", {}), epoch_us=int(ep["epoch_us"]) if ep else None,
            hop_samples=sc["time"]["hop_samples"], rate_hz=sc["time"]["rate_hz"],
            pcm=r.get("pcm", {})))
    comps = []
    for c in result["comparisons"]:
        if c.get("a") and c.get("b") and c["kind"] in ("equal", "isolation", "limit_coupling", "differs"):
            comps.append(rd.comparison_record(
                c["id"], "equal" if c["kind"] == "equal" else "labelled", c["a"], c["b"],
                compatible=c["status"] in ("PASS", "FAIL") and "not comparable" not in c.get("detail", ""),
                status=c["status"], detail=c.get("detail", ""), strict=c["kind"] == "equal",
                label=c.get("label") or c["kind"]))
    data = {"schema": "k1-emu-report-data/1",
            "invocation": {"id": result["invocation_id"], "overall": result["overall"], "scenario": sc["name"],
                           "source": {"head": result["source"]["head"],
                                      "dirty_inputs_sha256": result["source"]["dirty_inputs_sha256"]},
                           },
            "criteria": result["criteria"], "cases": cases, "comparisons": comps}
    (out / "report-data.json").write_text(json.dumps(data) + "\n")
    try:
        import report  # noqa: WPS433 - sibling module (WP7)
        report.write_report(data, out / "report.html")
        if check:
            result["report_checks"] = report_checks(report, data, out / "report.html", result["invocation_id"])
    except Exception as exc:  # report failure must be visible, never silent
        (out / "report.html").write_text(f"<!doctype html><title>report failed</title><pre>{exc!r}</pre>")
        result["report_error"] = repr(exc)
        result["report_checks"] = {"status": "FAIL", "detail": repr(exc)}


def report_checks(report, data: dict, html_path: Path, invocation: str) -> dict:
    """SW10 on this invocation's real data: identical pair, one planted native byte, incompatible pair."""
    import copy
    cases = {c["case"]: c for c in data["cases"]}
    out = {}
    a, b = cases.get("smoke-a"), cases.get("smoke-b")
    if not (a and b and a["frames"]):
        return {"status": "NOT_RUN", "detail": "smoke-a/smoke-b not in this suite"}
    same = report.compare_cases(a, b)
    out["identical_pair"] = same["aligned_ok"] and same["diff_pixels_total"] == 0
    planted = copy.deepcopy(a)
    fi, px = len(planted["frames"]) // 2, 79
    wire = bytearray.fromhex(planted["frames"][fi]["A"])
    wire[px * 6 + 1] ^= 0x01  # one LSB of G16 on edge A: invisible in an 8-bit projection
    planted["frames"][fi]["A"] = wire.hex()
    diff = report.compare_cases(a, planted)
    first = diff.get("first_difference") or {}
    out["planted_pixel"] = (diff["diff_pixels_total"] == 1 and first.get("edge") == "A"
                            and first.get("pixel") == px and first.get("hop") == planted["frames"][fi]["hop"])
    other = next((c for k, c in cases.items() if c["frames"] and {f["hop"] for f in c["frames"]} != {f["hop"] for f in a["frames"]}), None)
    out["incompatible_rejected"] = other is not None and not report.compare_cases(a, other)["aligned_ok"]
    html = html_path.read_text(errors="replace")
    out["self_contained"] = not re.search(r"(src|href)=[\"']https?://", html) and "@import url(http" not in html
    out["names_invocation"] = invocation in html
    ok = all(out.values())
    return {"status": "PASS" if ok else "FAIL", "checks": out, "planted_first_difference": first,
            "detail": f"{out}; html {html_path.stat().st_size} bytes"}


def criteria_matrix(sc, results, comparisons, planted, product, hosts, emu_build) -> list[dict]:
    comp = {c["id"]: c for c in comparisons}
    rows = []

    def from_comps(cid: str, ids: list[str], extra_ok: bool = True, note: str = "") -> None:
        got = [comp[i] for i in ids if i in comp]
        if not got:
            rows.append({"id": cid, "status": "NOT_RUN", "evidence": "no comparison in this suite"})
            return
        st = [g["status"] for g in got]
        if all(s == "PASS" for s in st) and extra_ok:
            status = "PASS"
        elif any(s == "FAIL" for s in st) or not extra_ok:
            status = "FAIL"
        elif all(s == "DEFERRED_EXTERNAL" for s in st):
            status = "DEFERRED_EXTERNAL"
        else:
            status = "NOT_RUN"
        rows.append({"id": cid, "status": status,
                     "evidence": (note + " " + " | ".join(f"{g['id']}: {g['status']} {g['detail']}" for g in got)).strip()})

    mapping = {c["id"]: c.get("criterion") for c in sc.get("comparisons", [])}
    by_crit: dict[str, list[str]] = {}
    for k, v in mapping.items():
        if v:
            by_crit.setdefault(v, []).append(k)
    accepted = [r for r in results.values() if r.get("status") == "PASS"]
    ran = [r for r in results.values() if r.get("status") not in ("DEFERRED_EXTERNAL",)]
    all_ok = bool(ran) and all(r.get("status") == "PASS" for r in ran)
    identity_ok = all_ok and all(r.get("executed", {}).get("app_region_matches_build") for r in accepted)
    rows.append({"id": "SW01", "status": "PASS" if identity_ok and emu_build["exit_code"] == 0 else "FAIL",
                 "evidence": f"{len(accepted)}/{len(ran)} runs accepted with firmware-observed run id, scenario CRC "
                             f"and counters; executed app region == built firmware.bin; image never patched"})
    from_comps("SW02", by_crit.get("SW02", []), all_ok)
    from_comps("SW03", by_crit.get("SW03", []), all_ok)
    planted_ok = bool(planted) and all(p["ok"] for p in planted)
    rows.append({"id": "SW04", "status": "PASS" if planted_ok and all_ok else "FAIL",
                 "evidence": f"{sum(p['ok'] for p in planted)}/{len(planted)} planted captures rejected for the stated "
                             f"reason through ec.accept; " + ", ".join(p["name"] for p in planted if not p["ok"])})
    from_comps("SW05", by_crit.get("SW05", []))
    from_comps("SW06", by_crit.get("SW06", []))
    rows.append({"id": "SW07", "status": product["status"],
                 "evidence": f"pio run -e {sc['profile']['product_env']} exit={product['build']['exit_code']}; "
                             f"forbidden flags={product['product_flags_forbidden_present']}; fixture symbols="
                             f"{len(product['product_fixture_symbols'])}; emu-only flags={product['emu_minus_product_flags']}; "
                             f"positive control symbols={product['positive_control_emu_symbols']}; upload blocked="
                             f"{product['emu_env_upload_blocked']}; host tests {hosts['status']} ({hosts['summary']})"})
    if hosts["status"] != "PASS":
        rows[-1]["status"] = "FAIL"
    for cid in ("SW08", "SW09"):
        from_comps(cid, by_crit.get(cid, []))
    rows.append({"id": "SW10", "status": "NOT_RUN", "evidence": "set after report.html is built"})
    exported = identity_kind() == "export"
    others = all(r["status"] == "PASS" for r in rows if r["id"] not in ("SW10",))
    rows.append({"id": "SW11", "status": ("PASS" if exported and others else "FAIL") if exported else "NOT_RUN",
                 "evidence": ("invocation ran from a clean export of the committed candidate (no .git, no prior outputs, "
                              "no emulator-workspace sources); tool via K1_ESP_EMU, hash-checked" if exported else
                              "this invocation ran in the maintained working checkout; SW11 is proven only by the clean-export run")})
    model_syms = model_symbols(sc)
    rows.append({"id": "SW12", "status": "NOT_APPLICABLE" if not model_syms else "NOT_RUN",
                 "evidence": ("no learned-model runtime in the product ELF (no tflite/tensorflow/interpreter/esp_nn/"
                              "MicroInterpreter symbols); model inference is not active on k1_main_rpl_im69d") if not model_syms
                             else f"model-like symbols present: {model_syms[:5]}"})
    client_runs = [r for r in results.values() if r.get("requested", {}).get("client_commands")
                   or r.get("client_resolution")]
    if by_crit.get("SW13") or client_runs:
        deferred = [r["case"] for r in client_runs if r.get("status") == "DEFERRED_EXTERNAL"]
        client_ok = bool(client_runs) and all(r.get("status") == "PASS" for r in client_runs)
        from_comps("SW13", by_crit.get("SW13", []), client_ok and not deferred,
                   note=(f"local client chain (existing client -> run-owned pty -> esp-emu USB-Serial/JTAG -> "
                         f"production parser), not physical USB; client cases "
                         f"{[(r['case'], r.get('status')) for r in client_runs]}"))
        if deferred and all(r.get("status") == "DEFERRED_EXTERNAL" for r in client_runs):
            rows[-1]["status"] = "DEFERRED_EXTERNAL"
    else:
        rows.append({"id": "SW13", "status": "NOT_RUN", "optional": True,
                     "evidence": "no client-transport case in this suite"})
    rows.append({"id": "EX01", "status": "DEFERRED_EXTERNAL",
                 "evidence": "physical parity, device/optical/AV/leave-state evidence: shelved by the Captain's R3 instruction; no hardware accessed"})
    rows.append({"id": "EX02", "status": "DEFERRED_EXTERNAL",
                 "evidence": "hosted CI/publication: no push authorised; no Linux-pinned esp-emu executable hash exists, so CI only builds k1_main_rpl_im69d and k1_main_rpl_emu"})
    return rows


def identity_kind() -> str:
    return "export" if not (REPO / ".git").exists() else "checkout"


def model_symbols(sc: dict) -> list[str]:
    elf = REPO / ".pio/build" / sc["profile"]["product_env"] / "firmware.elf"
    syms = symbols(elf, find_nm())
    return sorted(s for s in syms if re.search(r"tflite|tensorflow|MicroInterpreter|esp_nn|onnx", s, re.I))[:20]


if __name__ == "__main__":
    raise SystemExit(main())
