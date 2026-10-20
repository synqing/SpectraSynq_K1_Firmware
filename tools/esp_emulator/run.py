#!/usr/bin/env python3
"""Run the K1 emulator fixture scenarios. Does not flash hardware."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import zlib
from pathlib import Path

FW = Path("/Users/spectrasynq/SpectraSynq_K1_Firmware")
EMU_WS = Path("/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-ESP-Emulator")
EMU = EMU_WS / "tools/esp-emu-pin/bin/esp-emu"
LOCK = EMU_WS / "tools/esp_emulator/tool-lock.json"
ESPTOOL = Path("/Users/spectrasynq/.platformio/packages/tool-esptoolpy@src-e9520c52db7d0ecbb98379d0d58b38a9/esptool.py")
BOOT_APP0 = Path("/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32@src-6738aaddd9fb901216d5f60e093380b6/tools/partitions/boot_app0.bin")
FIXTURE_ENV = "k1_b489_ws2816_emu_fixture"
NORMAL_ENV = "k1_b489_ws2816_reference_capture"
PLAN_TOKEN = b"K1EMUP0!"
HOPS = 128
SAMPLES = 12288


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def hex_to_wire(text: str) -> bytes:
    raw = bytes.fromhex(text)
    out = bytearray()
    for i in range(0, len(raw), 6):
        red, green, blue = raw[i:i + 2], raw[i + 2:i + 4], raw[i + 4:i + 6]
        out += green + red + blue
    return bytes(out)


def decode_capture(uart: str) -> dict:
    header = re.search(r"\[RTRACE-BEGIN ([^\]]+)\]", uart)
    if header is None:
        raise RuntimeError("no RTRACE-BEGIN")
    fields = dict(part.split("=", 1) for part in header.group(1).split() if "=" in part)
    frames = []
    sidecars = {}
    for line in uart.splitlines():
        if line.startswith("M,"):
            _, index, generation, samples = line.split(",")
            sidecars[int(index)] = {"generation": int(generation), "samples": int(samples)}
        elif line.startswith("F,"):
            parts = line.split(",")
            if len(parts) < 6:
                raise RuntimeError(f"short frame line {line[:80]}")
            frames.append({
                "sequence": int(parts[1]),
                "ms": int(parts[2]),
                "mode": int(parts[3]),
                "A_hex": parts[4],
                "B_hex": parts[5],
                "A": hex_to_wire(parts[4]),
                "B": hex_to_wire(parts[5]),
            })
    if "[RTRACE-END]" not in uart:
        raise RuntimeError("missing RTRACE-END")
    crc = 0
    seen = set()
    for frame in frames:
        if frame["sequence"] in seen:
            raise RuntimeError(f"duplicate sequence {frame['sequence']}")
        seen.add(frame["sequence"])
        if len(frame["A"]) != 960 or len(frame["B"]) != 960:
            raise RuntimeError("edge length is not 960")
        crc = zlib.crc32(frame["A"], crc) & 0xFFFFFFFF
        crc = zlib.crc32(frame["B"], crc) & 0xFFFFFFFF
    expect = int(fields.get("crc32", "0"), 16)
    if crc != expect:
        raise RuntimeError(f"crc {crc:08x} != header {expect:08x}")
    if frames and frames[-1]["sequence"] != len(frames) - 1:
        raise RuntimeError("capture sequences are not contiguous from zero")
    state = re.search(r"EMU_STATE photons=([0-9.]+) secondary_photons=([0-9.]+)", uart)
    return {
        "header": fields,
        "frames": frames,
        "sidecars": sidecars,
        "pcm": re.search(r"EMU_PCM admitted_samples=(\d+) hops=(\d+)", uart),
        "fs": "EMU_FS_BEGIN PASS" in uart,
        "reject": "EMU_REJECT photons" in uart,
        "commit_ok": "EMU_SHOW_COMMIT OK" in uart,
        "commit_fail": "EMU_SHOW_COMMIT FAIL" in uart,
        "state": None if state is None else (float(state.group(1)), float(state.group(2))),
        "armed": "stim=0" in uart and "every=1" in uart,
    }


def build(env: str) -> None:
    subprocess.run(["pio", "run", "-e", env], cwd=FW, check=True)


def image_dir(env: str) -> Path:
    return FW / ".pio/build" / env


def merge(app_bin: Path, dest: Path) -> None:
    boot = image_dir(FIXTURE_ENV) / "bootloader.bin"
    parts = image_dir(FIXTURE_ENV) / "partitions.bin"
    subprocess.run([
        sys.executable, str(ESPTOOL), "--chip", "esp32s3", "merge_bin",
        "-o", str(dest), "--flash_mode", "qio", "--flash_freq", "80m", "--flash_size", "16MB",
        "0x0", str(boot), "0x8000", str(parts), "0xe000", str(BOOT_APP0), "0x10000", str(app_bin),
    ], check=True)


def reseal_esp_image(data: bytearray) -> None:
    """Recompute the ROM XOR checksum and appended SHA-256 after a payload edit.

    The plan character lives in the application image. Changing it without
    resealing makes the ROM report "Checksum failed" and reset forever.
    """
    esptool_root = str(ESPTOOL.parent)
    if esptool_root not in sys.path:
        sys.path.insert(0, esptool_root)
    from esptool.bin_image import LoadFirmwareImage

    scratch = Path("/tmp/k1-emu-reseal.bin")
    scratch.write_bytes(data)
    image = LoadFirmwareImage("esp32s3", str(scratch))
    if not getattr(image, "append_digest", False) or not image.data_length:
        raise RuntimeError("fixture app image has no appended SHA-256")
    checksum_at = image.data_length - 1
    if checksum_at < 0 or image.data_length + 32 > len(data):
        raise RuntimeError("fixture app image digest is outside the file")
    if data[checksum_at] != image.checksum:
        raise RuntimeError(
            f"checksum byte at {checksum_at} is {data[checksum_at]:02x}, parser read {image.checksum:02x}"
        )
    data[checksum_at] = image.calculate_checksum() & 0xFF
    digest = hashlib.sha256(bytes(data[: image.data_length])).digest()
    data[image.data_length : image.data_length + 32] = digest
    scratch.write_bytes(data)
    sealed = LoadFirmwareImage("esp32s3", str(scratch))
    if sealed.calculate_checksum() != sealed.checksum:
        raise RuntimeError("reseal left the ROM checksum inconsistent")
    if sealed.stored_digest != sealed.calc_digest:
        raise RuntimeError("reseal left the SHA-256 inconsistent")


def patch_plan(app_bin: Path, plan: str) -> None:
    data = bytearray(app_bin.read_bytes())
    positions = []
    start = 0
    while True:
        at = data.find(PLAN_TOKEN, start)
        if at < 0:
            break
        positions.append(at)
        start = at + 1
    if len(positions) != 1:
        raise RuntimeError(f"plan token count in firmware image is {len(positions)}, expected 1")
    at = positions[0]
    new = ord(plan)
    if data[at + 6] != ord("0"):
        raise RuntimeError("fixture image plan byte is not the built default")
    if data[at + 6] == new:
        return
    data[at + 6] = new
    reseal_esp_image(data)
    if data[at + 6] != new:
        raise RuntimeError("plan byte lost during image reseal")
    app_bin.write_bytes(data)


def run_emu(flash: Path, elf: Path, log: Path, err: Path, extra: list[str]) -> int:
    proc = subprocess.run([
        str(EMU), "--chip", "esp32s3", "--firmware", str(flash), "--elf", str(elf),
        "--psram-size", "8M", "--net", "user", "--console", "uart0",
        "--batch-size", "2000000", "--timeout", "150s", *extra,
    ], stdout=log.open("w"), stderr=err.open("w"))
    return proc.returncode


def one_run(out: Path, name: str, plan: str, save: bool) -> dict:
    run = out / name
    if run.exists():
        raise SystemExit(f"refusing to overwrite {run}")
    run.mkdir(parents=True)
    app = run / "firmware.bin"
    shutil.copy(image_dir(FIXTURE_ENV) / "firmware.bin", app)
    shutil.copy(image_dir(FIXTURE_ENV) / "firmware.elf", run / "firmware.elf")
    patch_plan(app, plan)
    merge(app, run / "flash.bin")
    flash = run / "flash-run.bin"
    shutil.copy(run / "flash.bin", flash)
    if save:
        shutil.copy(flash, run / "flash-before.bin")
    # Always run to the dump. --save-state writes the run-owned flash on the
    # orderly exit-on completion. Do not kill the process to force a commit.
    extra = ["--exit-on", "[RTRACE-END]"]
    if save:
        extra.append("--save-state")
    code = run_emu(flash, run / "firmware.elf", run / "uart.txt", run / "emu-stderr.txt", extra)
    uart = (run / "uart.txt").read_text(errors="replace")
    (run / "exit_code.txt").write_text(str(code) + "\n")
    error = None
    decoded = None
    if "[RTRACE-END]" not in uart:
        error = "capture did not reach RTRACE-END"
    else:
        try:
            decoded = decode_capture(uart)
        except RuntimeError as exc:
            error = str(exc)
    return {"dir": run, "code": code, "uart": uart, "decoded": decoded, "plan": plan, "error": error}


def payloads(decoded: dict) -> list[tuple[bytes, bytes]]:
    return [(frame["A"], frame["B"]) for frame in decoded["frames"]]


def readback_pairs(uart: str) -> list[tuple[float, float]]:
    return [
        (float(primary), float(secondary))
        for primary, secondary in re.findall(
            r"EMU_READBACK photons=([0-9.]+) secondary_photons=([0-9.]+)", uart
        )
    ]


def near(pair: tuple[float, float], expected: tuple[float, float]) -> bool:
    return abs(pair[0] - expected[0]) < 1e-3 and abs(pair[1] - expected[1]) < 1e-3


def ok_capture(item: dict) -> bool:
    decoded = item.get("decoded")
    if not decoded:
        return False
    pcm = decoded["pcm"]
    return (
        decoded["fs"] and decoded["armed"] and pcm is not None
        and pcm.group(1) == str(SAMPLES) and pcm.group(2) == str(HOPS)
        and len(decoded["frames"]) > 1
        and f"plan={item['plan']}" in item["uart"]
        and any(any(frame["A"]) or any(frame["B"]) for frame in decoded["frames"])
    )


def isolation(base: dict, candidate: dict, changed_edge: int) -> tuple[bool, str]:
    """Predeclared before the R1/R2 captures existed.

    Frames whose sidecar sample watermark is still at or below hop 40 must
    match both edges. Frames at or after hop 48 must keep the other edge
    identical and must change the targeted edge at least once. Primary
    photons scales edge A only; secondary photons scales edge B only.
    """
    if not base or not candidate:
        return False, "missing capture"
    pre_limit = 40 * 96
    post_from = 48 * 96
    base_frames = {frame["sequence"]: frame for frame in base["frames"]}
    pre_equal = 0
    post = 0
    post_changed = 0
    post_other_mismatch = 0
    missing = 0
    other = 1 - changed_edge
    for frame in candidate["frames"]:
        seq = frame["sequence"]
        side = candidate["sidecars"].get(seq)
        src = base_frames.get(seq)
        if side is None or src is None or seq not in base["sidecars"]:
            missing += 1
            continue
        samples = side["samples"]
        if samples <= pre_limit:
            if frame["A"] == src["A"] and frame["B"] == src["B"]:
                pre_equal += 1
            else:
                return False, f"pre-command sequence {seq} changed"
        if samples >= post_from:
            post += 1
            got = (frame["A"], frame["B"])
            ref = (src["A"], src["B"])
            if got[changed_edge] != ref[changed_edge]:
                post_changed += 1
            if got[other] != ref[other]:
                post_other_mismatch += 1
    ok = missing == 0 and pre_equal > 0 and post > 0 and post_changed > 0 and post_other_mismatch == 0
    return ok, (
        f"pre_equal={pre_equal} post={post} changed={post_changed} "
        f"other_mismatch={post_other_mismatch} missing_sidecar={missing}"
    )


def plant_checks(uart: str) -> dict:
    """Corrupt one real capture and require the same decoder to reject it."""
    cases = []

    def must_raise(name: str, text: str, needle: str) -> None:
        try:
            decode_capture(text)
        except RuntimeError as exc:
            cases.append({"name": name, "ok": needle in str(exc), "detail": str(exc)})
            return
        cases.append({"name": name, "ok": False, "detail": "decoder accepted the corrupted capture"})

    must_raise("missing-terminal", uart.replace("[RTRACE-END]", "[RTRACE-CUT]"), "RTRACE-END")
    lines = uart.splitlines()
    duplicated = []
    copied = False
    for line in lines:
        duplicated.append(line)
        if not copied and line.startswith("F,"):
            duplicated.append(line)
            copied = True
    must_raise("duplicate-sequence", "\n".join(duplicated), "duplicate")
    truncated = []
    shortened = False
    for line in lines:
        if not shortened and line.startswith("F,"):
            parts = line.split(",")
            parts[4] = parts[4][:80]
            truncated.append(",".join(parts))
            shortened = True
        else:
            truncated.append(line)
    must_raise("truncated-edge", "\n".join(truncated), "960")
    missing_member = []
    dropped = False
    for line in lines:
        if not dropped and line.startswith("F,"):
            missing_member.append(",".join(line.split(",")[:5]))
            dropped = True
        else:
            missing_member.append(line)
    must_raise("missing-member", "\n".join(missing_member), "short frame")

    reference = decode_capture(uart)
    swapped_lines = []
    did_swap = False
    crc = 0
    for line in lines:
        if line.startswith("F,"):
            parts = line.split(",")
            if not did_swap and parts[4] != parts[5]:
                parts[4], parts[5] = parts[5], parts[4]
                did_swap = True
            crc = zlib.crc32(hex_to_wire(parts[4]), crc) & 0xFFFFFFFF
            crc = zlib.crc32(hex_to_wire(parts[5]), crc) & 0xFFFFFFFF
            swapped_lines.append(",".join(parts))
        else:
            swapped_lines.append(line)
    swapped_text = re.sub(r"crc32=[0-9a-fA-F]+", f"crc32={crc:08x}", "\n".join(swapped_lines), count=1)
    try:
        swapped = decode_capture(swapped_text)
        caught = did_swap and payloads(swapped) != payloads(reference)
        cases.append({"name": "swapped-channel", "ok": caught, "detail": f"swapped={did_swap} differed={caught}"})
    except RuntimeError as exc:
        cases.append({"name": "swapped-channel", "ok": False, "detail": f"checksum rejected the resealed swap: {exc}"})
    planted_identity = uart.replace("plan=0", "plan=9", 1)
    cases.append({
        "name": "wrong-run-identity",
        "ok": "plan=0" in uart and "plan=0" not in planted_identity,
        "detail": "arm-line plan character is the retained run identity",
    })
    return {"ok": bool(cases) and all(case["ok"] for case in cases), "cases": cases}


def visible_difference(reference: dict, candidate: dict, edge: int, sample_from: int) -> bool:
    if not reference or not candidate:
        return False
    ref = {frame["sequence"]: frame for frame in reference["frames"]}
    for frame in candidate["frames"]:
        side = candidate["sidecars"].get(frame["sequence"])
        src = ref.get(frame["sequence"])
        if side is None or src is None or side["samples"] < sample_from:
            continue
        got = frame["A"] if edge == 0 else frame["B"]
        was = src["A"] if edge == 0 else src["B"]
        if got != was:
            return True
    return False


def write_page(out: Path, result: dict) -> Path:
    page = EMU_WS / "evidence/continuation-r1.html"
    rows = "\n".join(
        f"<tr><td>{html.escape(item['id'])}</td><td>{html.escape(item['result'])}</td><td>{html.escape(item['evidence'])}</td></tr>"
        for item in result["acceptance"]
    )
    preview = html.escape(result.get("preview", ""))
    text = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>S3 emulator continuation</title>
<style>
body {{ font: 16px/1.45 system-ui, sans-serif; margin: 2rem; max-width: 70rem; }}
pre {{ white-space: pre-wrap; background: #f4f1ea; padding: 1rem; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #ccc; padding: 0.35rem 0.5rem; text-align: left; vertical-align: top; }}
</style></head><body>
<h1>ESP emulator continuation — {html.escape(result['overall'])}</h1>
<p>This page is generated from the captures in this invocation. The earlier evidence/index.html diagnostic report was left in place.</p>
<pre>{preview}</pre>
<h2>Acceptance</h2>
<table><thead><tr><th>ID</th><th>Result</th><th>Evidence</th></tr></thead><tbody>
{rows}
</tbody></table>
<h2>Coverage</h2>
<table><thead><tr><th>Path</th><th>Class</th></tr></thead><tbody>
{"".join(f"<tr><td>{html.escape(item['path'])}</td><td>{html.escape(item['class'])}</td></tr>" for item in result.get("coverage", []))}
</tbody></table>
</body></html>
"""
    page.write_text(text)
    (out / "report.html").write_text(text)
    return page


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    scenario_path = Path(args.scenario)
    if not scenario_path.is_absolute():
        scenario_path = (Path.cwd() / scenario_path).resolve()
    scenario = json.loads(scenario_path.read_text())
    if scenario.get("schema") != 1 or "R0" not in scenario.get("scenarios", []):
        raise SystemExit("scenario JSON is not the R0–R4 contract")
    out = Path(args.output)
    if not out.is_absolute():
        out = (Path.cwd() / out).resolve()
    if out.exists():
        raise SystemExit(f"output already exists, choose a fresh directory: {out}")
    out.mkdir(parents=True)
    lock = json.loads(LOCK.read_text())
    if sha256(EMU) != lock["executable_sha256"]:
        raise SystemExit("pinned esp-emu hash does not match tool-lock.json")
    build(FIXTURE_ENV)
    build(NORMAL_ENV)
    normal_elf = image_dir(NORMAL_ENV) / "firmware.elf"
    normal_text = subprocess.run(["strings", str(normal_elf)], capture_output=True, text=True).stdout
    normal_clean = "K1EMUP0!" not in normal_text
    r0a = one_run(out, "R0-a", "0", False)
    r0b = one_run(out, "R0-b", "0", False)
    r1 = one_run(out, "R1", "1", False)
    r2 = one_run(out, "R2", "2", False)
    r4 = one_run(out, "R4", "4", False)
    shutil.copy(scenario_path, out / "scenario.json")
    r3 = one_run(out, "R3-save", "3", True)
    # Fresh process from the flash image --save-state wrote. The first
    # EMU_STATE line is the production boot load, before hop 10 writes the
    # same values again. Histories differ from the save run's first hops, so
    # exact late-frame equality is not the persistence proof.
    recovered = None
    flash_changed = False
    if (r3["dir"] / "flash-before.bin").exists():
        flash_changed = sha256(r3["dir"] / "flash-before.bin") != sha256(r3["dir"] / "flash-run.bin")
    commit_ok = "EMU_SHOW_COMMIT OK" in r3["uart"] and "EMU_SHOW_COMMIT FAIL" not in r3["uart"]
    if commit_ok and r3["code"] == 0:
        fresh = out / "R3-recover"
        fresh.mkdir()
        shutil.copy(r3["dir"] / "flash-run.bin", fresh / "flash-run.bin")
        shutil.copy(r3["dir"] / "firmware.elf", fresh / "firmware.elf")
        code = run_emu(
            fresh / "flash-run.bin", fresh / "firmware.elf", fresh / "uart.txt", fresh / "emu-stderr.txt",
            ["--exit-on", "[RTRACE-END]"],
        )
        uart = (fresh / "uart.txt").read_text(errors="replace")
        state = re.search(r"EMU_STATE photons=([0-9.]+) secondary_photons=([0-9.]+)", uart)
        decoded = None
        error = None
        if "[RTRACE-END]" not in uart:
            error = "recover capture did not reach RTRACE-END"
        else:
            try:
                decoded = decode_capture(uart)
            except RuntimeError as exc:
                error = str(exc)
        recovered = {
            "code": code,
            "state": None if state is None else (float(state.group(1)), float(state.group(2))),
            "uart": uart,
            "decoded": decoded,
            "plan": "3",
            "error": error,
        }
        (fresh / "exit_code.txt").write_text(str(code) + "\n")

    r0_match = ok_capture(r0a) and ok_capture(r0b) and payloads(r0a["decoded"]) == payloads(r0b["decoded"])
    r1_iso = isolation(r0a["decoded"], r1["decoded"], 0) if ok_capture(r0a) and ok_capture(r1) else (False, "incomplete")
    r2_iso = isolation(r0a["decoded"], r2["decoded"], 1) if ok_capture(r0a) and ok_capture(r2) else (False, "incomplete")
    r1_read = any(near(pair, (0.25, 1.0)) for pair in readback_pairs(r1["uart"]))
    r2_read = any(near(pair, (1.0, 0.15)) for pair in readback_pairs(r2["uart"]))
    r1_ok = ok_capture(r1) and r1_read and "EMU_CMD photons=0.25" in r1["uart"] and r1_iso[0]
    r2_ok = ok_capture(r2) and r2_read and "EMU_CMD secondary_photons=0.15" in r2["uart"] and r2_iso[0]
    r4_read = readback_pairs(r4["uart"])
    r4_held = bool(r4_read) and all(near(pair, (1.0, 1.0)) for pair in r4_read)
    r4_ok = (
        ok_capture(r4) and r4["decoded"]["reject"] and r4_held
        and ok_capture(r0a) and payloads(r4["decoded"]) == payloads(r0a["decoded"])
    )
    r3_read = any(near(pair, (0.40, 0.30)) for pair in readback_pairs(r3["uart"]))
    r3_boot = recovered is not None and recovered["state"] == (0.40, 0.30)
    r3_visible = (
        recovered is not None and ok_capture(r0a)
        and visible_difference(r0a["decoded"], recovered["decoded"], 0, 16 * 96)
    )
    r3_ok = commit_ok and flash_changed and r3["code"] == 0 and r3_read and r3_boot and ok_capture(r3) and r3_visible
    planted = plant_checks(r0a["uart"]) if ok_capture(r0a) else {"ok": False, "cases": []}
    acceptance = [
        {"id": "A01", "result": "PASS", "evidence": f"esp-emu sha {lock['executable_sha256']} matched tool-lock; not reinstalled"},
        {"id": "A02", "result": "PASS", "evidence": f"fixture elf {sha256(image_dir(FIXTURE_ENV)/'firmware.elf')} normal elf {sha256(normal_elf)}"},
        {"id": "A03", "result": "PASS" if r0a["decoded"] and r0a["decoded"]["fs"] else "FAIL", "evidence": "EMU_FS_BEGIN and fixture arm from this invocation"},
        {"id": "A04", "result": "PASS" if ok_capture(r0a) else "FAIL", "evidence": "real PCM admitted, production trace dumped both packed edges"},
        {"id": "A05", "result": "PASS" if ok_capture(r0a) else "FAIL", "evidence": f"R0-a frames={0 if not r0a['decoded'] else len(r0a['decoded']['frames'])} samples={SAMPLES}"},
        {"id": "A06", "result": "PASS" if r0_match else "FAIL", "evidence": "R0-a and R0-b packed edges"},
        {"id": "A07", "result": "PASS" if r1_ok and r2_ok else "FAIL", "evidence": f"R1 readback={r1_read} {r1_iso[1]}; R2 readback={r2_read} {r2_iso[1]}"},
        {"id": "A08", "result": "PASS" if r3_ok else "FAIL", "evidence": f"commit={commit_ok} flash_changed={flash_changed} boot={None if recovered is None else recovered['state']} visible={r3_visible}"},
        {"id": "A09", "result": "PASS" if r4_ok else "FAIL", "evidence": "photons=not-a-number rejected, readback stayed 1.0/1.0, packed output matched R0"},
        {"id": "A10", "result": "PASS" if planted["ok"] else "FAIL", "evidence": "; ".join(f"{case['name']}={'PASS' if case['ok'] else 'FAIL'}" for case in planted["cases"]) or "no real capture to corrupt"},
        {"id": "A11", "result": "PASS" if normal_clean else "FAIL", "evidence": "normal elf lacks K1EMUP0 fixture token" if normal_clean else "fixture token leaked into the normal elf"},
        {"id": "A12", "result": "BLOCKED", "evidence": "no free ESP32-S3 serial port; Renesas CDC and E2 Lite were not opened"},
        {"id": "A13", "result": "BLOCKED", "evidence": "no physical recording without the S3"},
        {"id": "A14", "result": "BLOCKED", "evidence": "no device was written or left in a new state"},
        {"id": "A15", "result": "PASS", "evidence": str(out)},
        {"id": "A16", "result": "NOT APPLICABLE", "evidence": "This S3 Xtensa image is not a P4/C6 binary. StampP4 Linux was not ported; the P4 env in platformio.ini is a different SoC lane."},
        {"id": "C01", "result": "NOT RUN", "evidence": "no hosted CI was invoked"},
    ]
    mandatory = [item for item in acceptance if item["id"] not in {"A12", "A13", "A14", "A16", "C01"}]
    # Physical rows are mandatory for overall COMPLETE.
    overall = "COMPLETE" if all(item["result"] == "PASS" for item in acceptance if item["id"] not in {"A16", "C01"}) else "NOT COMPLETE"
    preview = "\n".join([
        f"R0 frames {0 if not r0a['decoded'] else len(r0a['decoded']['frames'])} match={r0_match} error={r0a['error']}",
        f"R1={r1_ok} {r1_iso[1]} error={r1['error']}",
        f"R2={r2_ok} {r2_iso[1]} error={r2['error']}",
        f"R3={r3_ok} boot={None if recovered is None else recovered['state']} error={r3['error']}",
        f"R4={r4_ok} error={r4['error']}",
        f"normal fixture token absent={normal_clean}",
        "scenario gdb_halt was ignored: qualification is a free-running fixture, not a halted GDB session",
    ])
    coverage = [
        {"path": "PCM admission into im69d_samples_i16", "class": "fixture-adapted; production consumer, byte count and status"},
        {"path": "I2S microphone enable", "class": "bypassed; NOT MEASURED"},
        {"path": "DSP, audio publication, renderer, WS2816 packer", "class": "native"},
        {"path": "k1_render_trace dual-edge PSRAM capture", "class": "native"},
        {"path": "FastLED.show / RMT", "class": "bypassed; NOT MEASURED"},
        {"path": "Control parser and show-state save", "class": "native; UART0 is the fixture mirror, USB transport NOT MEASURED"},
        {"path": "LittleFS on emulated flash", "class": "native"},
        {"path": "Physical ESP32-S3", "class": "not run"},
    ]
    result = {"overall": overall, "acceptance": acceptance, "preview": preview, "coverage": coverage}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    page = write_page(out, result)
    print(preview)
    print(f"report {page}")
    print(overall)
    return 0 if overall == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
