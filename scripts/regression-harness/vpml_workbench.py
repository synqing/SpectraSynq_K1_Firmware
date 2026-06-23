#!/usr/bin/env python3
"""Local VPML compiler, parameter editor, and control workbench."""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
import sys
import time
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRESET_DIR = ROOT / "evidence" / "vpml-presets"
DEFAULT_RECIPE_DIR = ROOT / "evidence" / "vpml-recipes"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
DEFAULT_SERIAL_PORT = "/dev/cu.usbmodem1401"
DEFAULT_BAUD = 115200
DEFAULT_EXPECT_CHIP_ID = "F887A500"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _load_script(name: str):
    script = Path(__file__).with_name(name)
    module_name = name.replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, script)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


vpml_compiler = _load_script("vpml_compiler.py")
vpml_live_runner = _load_script("vpml_live_runner.py")


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return slug or "preset"


def _preset_path(preset_dir: Path, name: str) -> Path:
    return preset_dir / ("%s.json" % _slug(name))


def _recipe_path(recipe_dir: Path, name: str) -> Path:
    return recipe_dir / ("%s.json" % _slug(name))


def list_presets(preset_dir: Path) -> list[dict[str, Any]]:
    preset_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(preset_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            programme = str(data.get("programme") or "intro_bounce_loop")
            params = vpml_compiler.coerce_params(programme, data.get("params") or {})
            compiled = vpml_compiler.compile_command(programme, params, include_defaults=False)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        rows.append(
            {
                "name": str(data.get("name") or path.stem),
                "programme": programme,
                "path": str(path),
                "updated_at": data.get("updated_at"),
                "command": compiled["command"],
                "command_bytes": compiled["command_bytes"],
                "command_data_bytes": compiled["command_data_bytes"],
            }
        )
    return sorted(rows, key=lambda item: item["name"].lower())


def read_preset(preset_dir: Path, name: str) -> dict[str, Any]:
    path = _preset_path(preset_dir, name)
    data = json.loads(path.read_text(encoding="utf-8"))
    programme = str(data.get("programme") or "intro_bounce_loop")
    params = vpml_compiler.coerce_params(programme, data.get("params") or {})
    return {"programme": programme, "params": params, "name": str(data.get("name") or name)}


def write_preset(preset_dir: Path, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    clean_name = name.strip() or "Preset"
    compiled = vpml_compiler.compile_from_payload(payload, include_defaults=False)
    preset_dir.mkdir(parents=True, exist_ok=True)
    path = _preset_path(preset_dir, clean_name)
    data = {
        "schema": "vpml_preset.v1",
        "name": clean_name,
        "programme": compiled["programme"],
        "params": compiled["params"],
        "compiled_command": compiled["command"],
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "message": "Preset saved.", "preset": data, "path": str(path)}


def list_recipes(recipe_dir: Path) -> list[dict[str, Any]]:
    recipe_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(recipe_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            compiled = vpml_compiler.compile_recipe(data, include_defaults=False)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        rows.append(
            {
                "name": compiled["name"],
                "programme": compiled["programme"],
                "path": str(path),
                "updated_at": data.get("updated_at"),
                "variant_count": len(compiled["variants"]),
                "variants": compiled["variants"],
            }
        )
    return sorted(rows, key=lambda item: item["name"].lower())


def read_recipe_source(recipe_dir: Path, name: str) -> dict[str, Any]:
    return json.loads(_recipe_path(recipe_dir, name).read_text(encoding="utf-8"))


def read_recipe(recipe_dir: Path, name: str, *, include_defaults: bool = False) -> dict[str, Any]:
    return vpml_compiler.compile_recipe(read_recipe_source(recipe_dir, name), include_defaults=include_defaults)


def variant_payload_from_recipe(recipe: dict[str, Any], variant_name: str) -> dict[str, Any]:
    for variant in recipe["variants"]:
        if variant["name"] == variant_name:
            return {
                "programme": variant["programme"],
                "params": variant["params"],
                "name": variant["name"],
            }
    raise ValueError("recipe variant not found: %s" % variant_name)


def write_recipe_variant(
    recipe_dir: Path,
    recipe_name: str,
    variant_name: str,
    payload: dict[str, Any],
    *,
    selected_recipe: str = "",
) -> dict[str, Any]:
    clean_recipe_name = (recipe_name or selected_recipe or "Recipe").strip()
    clean_variant_name = variant_name.strip() or "Variant"
    compiled = vpml_compiler.compile_from_payload(payload, include_defaults=False)
    recipe_dir.mkdir(parents=True, exist_ok=True)
    path = _recipe_path(recipe_dir, clean_recipe_name)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        variants = [
            item
            for item in data.get("variants", [])
            if str(item.get("name") or "") != clean_variant_name
        ]
    else:
        data = {
            "schema": vpml_compiler.RECIPE_SCHEMA,
            "name": clean_recipe_name,
            "programme": compiled["programme"],
            "variants": [],
        }
        variants = []
    variants.append(
        {
            "name": clean_variant_name,
            "programme": compiled["programme"],
            "params": compiled["params"],
        }
    )
    data["schema"] = vpml_compiler.RECIPE_SCHEMA
    data["name"] = clean_recipe_name
    data["programme"] = str(data.get("programme") or compiled["programme"])
    data["variants"] = variants
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())
    compiled_recipe = vpml_compiler.compile_recipe(data, include_defaults=False)
    data["compiled_variants"] = [
        {
            "name": item["name"],
            "programme": item["programme"],
            "command": item["command"],
            "command_bytes": item["command_bytes"],
            "command_data_bytes": item["command_data_bytes"],
            "max_command_data_bytes": item["max_command_data_bytes"],
        }
        for item in compiled_recipe["variants"]
    ]
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "message": "Recipe variant saved.", "recipe": compiled_recipe, "path": str(path)}


def _hex_to_rgb_params(prefix: str, value: str, params: dict[str, Any]) -> None:
    value = value.strip()
    if not value.startswith("#") or len(value) != 7:
        return
    try:
        params["%s_red" % prefix] = int(value[1:3], 16) / 255.0
        params["%s_green" % prefix] = int(value[3:5], 16) / 255.0
        params["%s_blue" % prefix] = int(value[5:7], 16) / 255.0
    except ValueError:
        return


def _rgb_to_hex(params: dict[str, float], prefix: str) -> str:
    r = max(0, min(255, int(round(params["%s_red" % prefix] * 255))))
    g = max(0, min(255, int(round(params["%s_green" % prefix] * 255))))
    b = max(0, min(255, int(round(params["%s_blue" % prefix] * 255))))
    return "#%02x%02x%02x" % (r, g, b)


def payload_from_form(form: dict[str, str]) -> dict[str, Any]:
    programme = form.get("programme", "intro_bounce_loop")
    params: dict[str, Any] = {}
    for key in vpml_compiler.PARAMS:
        if key in form:
            params[key] = form[key]
    _hex_to_rgb_params("primary", form.get("primary_colour", ""), params)
    _hex_to_rgb_params("secondary", form.get("secondary_colour", ""), params)
    _hex_to_rgb_params("impact", form.get("impact_colour", ""), params)
    return {"programme": programme, "params": params}


def connection_from_form(form: dict[str, str]) -> dict[str, Any]:
    port = form.get("port", DEFAULT_SERIAL_PORT).strip()
    if not port.startswith("/dev/"):
        raise ValueError("port must be a local /dev serial path")
    baud = int(form.get("baud", str(DEFAULT_BAUD)))
    if baud <= 0:
        raise ValueError("baud must be positive")
    return {
        "port": port,
        "baud": baud,
        "expect_chip_id": form.get("expect_chip_id", DEFAULT_EXPECT_CHIP_ID).strip().upper(),
    }


def compile_form(form: dict[str, str]) -> dict[str, Any]:
    include_defaults = form.get("include_defaults") == "on"
    return vpml_compiler.compile_from_payload(payload_from_form(form), include_defaults=include_defaults)


def values_from_payload(payload: dict[str, Any], form: dict[str, str]) -> dict[str, Any]:
    return {
        "programme": payload.get("programme", "intro_bounce_loop"),
        "params": payload.get("params") or {},
        "port": form.get("port", DEFAULT_SERIAL_PORT),
        "baud": form.get("baud", str(DEFAULT_BAUD)),
        "expect_chip_id": form.get("expect_chip_id", DEFAULT_EXPECT_CHIP_ID),
        "preset_name": form.get("preset_name", ""),
        "preset_a": form.get("preset_a", ""),
        "preset_b": form.get("preset_b", ""),
        "recipe_name": form.get("recipe_name", ""),
        "recipe_variant": form.get("recipe_variant", ""),
        "recipe_select": form.get("recipe_select", ""),
        "variant_select": form.get("variant_select", ""),
    }


def send_live_command(form: dict[str, str], command: str, require: tuple[str, ...], *, allow_device: bool) -> dict[str, Any]:
    vpml_compiler.validate_command_length(command)
    if not allow_device:
        raise ValueError("device access is disabled; restart with --allow-device to send serial commands")
    connection = connection_from_form(form)
    transport = vpml_live_runner.SerialTransport(connection["port"], connection["baud"])
    try:
        result = vpml_live_runner.run_simple_command_transport(
            transport,
            command,
            connection["expect_chip_id"],
            require=require,
        )
    finally:
        transport.close()
    result["command"] = command
    result["port"] = connection["port"]
    return result


def run_action(
    form: dict[str, str],
    *,
    preset_dir: Path,
    recipe_dir: Path,
    allow_device: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any], dict[str, Any] | None]:
    action = form.get("action", "compile")
    compiled = compile_form(form)
    if action == "compile":
        return compiled, {"ok": True, "message": "Compiled command only; nothing sent."}, None
    if action == "save":
        saved = write_preset(preset_dir, form.get("preset_name", ""), payload_from_form(form))
        return compiled, saved, None
    if action == "save_recipe_variant":
        saved = write_recipe_variant(
            recipe_dir,
            form.get("recipe_name", ""),
            form.get("recipe_variant", ""),
            payload_from_form(form),
            selected_recipe=form.get("recipe_select", ""),
        )
        return saved["recipe"], saved, None
    if action == "compile_recipe":
        recipe_name = form.get("recipe_select", "")
        if not recipe_name:
            raise ValueError("select a recipe first")
        recipe = read_recipe(recipe_dir, recipe_name, include_defaults=False)
        return recipe, {"ok": True, "message": "Compiled recipe deck only; nothing sent."}, None
    if action in {"load_recipe_variant", "run_recipe_variant"}:
        recipe_name = form.get("recipe_select", "")
        variant_name = form.get("variant_select", "")
        if not recipe_name:
            raise ValueError("select a recipe first")
        if not variant_name:
            raise ValueError("select a recipe variant first")
        recipe = read_recipe(recipe_dir, recipe_name, include_defaults=False)
        payload = variant_payload_from_recipe(recipe, variant_name)
        loaded = vpml_compiler.compile_from_payload(payload, include_defaults=False)
        if action == "load_recipe_variant":
            return loaded, {"ok": True, "message": "Recipe variant loaded: %s" % variant_name}, payload
        live = send_live_command(
            form,
            loaded["command"],
            require=("VPML play_params", loaded["programme"], "active=1"),
            allow_device=allow_device,
        )
        return loaded, live, payload
    if action in {"load_a", "load_b"}:
        preset_name = form.get("preset_a" if action == "load_a" else "preset_b", "")
        if not preset_name:
            raise ValueError("select a preset first")
        preset = read_preset(preset_dir, preset_name)
        loaded = vpml_compiler.compile_from_payload(preset, include_defaults=True)
        return loaded, {"ok": True, "message": "Preset loaded: %s" % preset["name"]}, preset
    if action in {"run_a", "run_b"}:
        preset_name = form.get("preset_a" if action == "run_a" else "preset_b", "")
        if not preset_name:
            raise ValueError("select a preset first")
        preset = read_preset(preset_dir, preset_name)
        loaded = vpml_compiler.compile_from_payload(preset, include_defaults=False)
        live = send_live_command(
            form,
            loaded["command"],
            require=("VPML play_params", loaded["programme"], "active=1"),
            allow_device=allow_device,
        )
        return loaded, live, preset
    if action == "run":
        live = send_live_command(
            form,
            compiled["command"],
            require=("VPML play_params", compiled["programme"], "active=1"),
            allow_device=allow_device,
        )
        return compiled, live, None
    if action == "status":
        live = send_live_command(form, ":vpml=status", require=("VPML status",), allow_device=allow_device)
        return compiled, live, None
    if action == "stop":
        live = send_live_command(form, ":vpml=stop", require=("VPML stop",), allow_device=allow_device)
        return compiled, live, None
    raise ValueError("unsupported workbench action: %s" % action)


def validate_bind_host(host: str, *, allow_non_loopback: bool = False) -> None:
    if allow_non_loopback:
        return
    if host not in LOOPBACK_HOSTS:
        raise ValueError("VPML Workbench binds only to loopback unless --allow-non-loopback is set")


def _input(name: str, params: dict[str, float]) -> str:
    spec = vpml_compiler.PARAMS[name]
    value = params[name]
    input_type = "number" if name == "frames" else "range"
    return """
    <label>
      <span>%s <output id="%s_out">%s</output></span>
      <input name="%s" type="%s" min="%s" max="%s" step="%s" value="%s" oninput="%s_out.value=this.value">
    </label>
    """ % (
        _esc(spec.label),
        _esc(name),
        _esc(vpml_compiler._format_value(name, value)),
        _esc(name),
        input_type,
        _esc(spec.low),
        _esc(spec.high),
        _esc(spec.step),
        _esc(vpml_compiler._format_value(name, value)),
        _esc(name),
    )


def _colour_input(label: str, name: str, value: str) -> str:
    return """
    <label class="colour">
      <span>%s</span>
      <input name="%s_colour" type="color" value="%s">
    </label>
    """ % (_esc(label), _esc(name), _esc(value))


def _result_panel(compiled: dict[str, Any] | None, live: dict[str, Any] | None) -> str:
    if not compiled and not live:
        return ""
    compiled_text = json.dumps(compiled or {}, indent=2, sort_keys=True)
    live_text = json.dumps(live or {}, indent=2, sort_keys=True)
    live_ok = bool((live or {}).get("ok"))
    return """
    <section class="result">
      <div class="result-head">
        <h2>Last Action</h2>
        <span class="badge %s">%s</span>
      </div>
      <h3>Compiled Command</h3>
      <pre>%s</pre>
      <h3>Action Result</h3>
      <pre>%s</pre>
    </section>
    """ % (
        "ok" if live_ok else "bad",
        "OK" if live_ok else "CHECK",
        _esc(compiled_text),
        _esc(live_text),
    )


def render_page(
    *,
    compiled: dict[str, Any] | None = None,
    live: dict[str, Any] | None = None,
    values: dict[str, Any] | None = None,
    defaults: dict[str, Any] | None = None,
) -> str:
    values = values or {}
    defaults = defaults or {}
    programme = values.get("programme") or defaults.get("programme") or "intro_bounce_loop"
    params = vpml_compiler.coerce_params(programme, values.get("params") or {})
    port = values.get("port") or defaults.get("port") or DEFAULT_SERIAL_PORT
    baud = int(values.get("baud") or defaults.get("baud") or DEFAULT_BAUD)
    expect_chip_id = values.get("expect_chip_id") or defaults.get("expect_chip_id") or DEFAULT_EXPECT_CHIP_ID
    allow_device = bool(defaults.get("allow_device"))
    device_badge = "Device Enabled" if allow_device else "Device Disabled"
    device_disabled_attr = "" if allow_device else " disabled"
    preset_dir = Path(defaults.get("preset_dir") or DEFAULT_PRESET_DIR)
    recipe_dir = Path(defaults.get("recipe_dir") or DEFAULT_RECIPE_DIR)
    preset_name = values.get("preset_name") or ""
    selected_a = values.get("preset_a") or ""
    selected_b = values.get("preset_b") or ""
    recipe_name = values.get("recipe_name") or ""
    recipe_variant = values.get("recipe_variant") or ""
    selected_recipe = values.get("recipe_select") or ""
    selected_variant = values.get("variant_select") or ""
    programmes = "".join(
        '<option value="%s"%s>%s</option>' % (
            _esc(name),
            " selected" if name == programme else "",
            _esc(name),
        )
        for name in sorted(vpml_compiler.PROGRAMMES)
    )
    presets = list_presets(preset_dir)
    preset_options_a = '<option value="">Select A</option>' + "".join(
        '<option value="%s"%s>%s</option>'
        % (
            _esc(item["name"]),
            " selected" if item["name"] == selected_a else "",
            _esc(item["name"]),
        )
        for item in presets
    )
    preset_options_b = '<option value="">Select B</option>' + "".join(
        '<option value="%s"%s>%s</option>'
        % (
            _esc(item["name"]),
            " selected" if item["name"] == selected_b else "",
            _esc(item["name"]),
        )
        for item in presets
    )
    preset_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td><code>%s</code></td></tr>"
        % (
            _esc(item["name"]),
            _esc(item.get("programme")),
            _esc(item.get("command_data_bytes")),
            _esc(item.get("command")),
        )
        for item in presets[-8:]
    ) or '<tr><td colspan="4">No saved presets yet.</td></tr>'
    recipes = list_recipes(recipe_dir)
    if not selected_recipe and recipe_name and any(item["name"] == recipe_name for item in recipes):
        selected_recipe = recipe_name
    recipe_options = '<option value="">Select Recipe</option>' + "".join(
        '<option value="%s"%s>%s</option>'
        % (
            _esc(item["name"]),
            " selected" if item["name"] == selected_recipe else "",
            _esc(item["name"]),
        )
        for item in recipes
    )
    selected_recipe_data: dict[str, Any] | None = None
    if selected_recipe:
        try:
            selected_recipe_data = read_recipe(recipe_dir, selected_recipe, include_defaults=False)
        except (OSError, ValueError, json.JSONDecodeError):
            selected_recipe_data = None
    recipe_variants = selected_recipe_data["variants"] if selected_recipe_data else []
    variant_options = '<option value="">Select Variant</option>' + "".join(
        '<option value="%s"%s>%s</option>'
        % (
            _esc(item["name"]),
            " selected" if item["name"] == selected_variant else "",
            _esc(item["name"]),
        )
        for item in recipe_variants
    )
    recipe_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s / %s</td><td><code>%s</code></td></tr>"
        % (
            _esc(item["name"]),
            _esc(item["programme"]),
            _esc(item["command_data_bytes"]),
            _esc(item["max_command_data_bytes"]),
            _esc(item["command"]),
        )
        for item in recipe_variants
    ) or '<tr><td colspan="4">No recipe selected.</td></tr>'

    motion_controls = "".join(_input(name, params) for name in ("frames", "secondary_phase", "primary_width", "secondary_width", "tail_scale"))
    level_controls = "".join(
        _input(name, params)
        for name in (
            "primary_level_base",
            "primary_level_gain",
            "secondary_level_base",
            "secondary_level_gain",
            "edge_level",
            "centre_level",
        )
    )
    colour_controls = "".join(
        [
            _colour_input("Primary Colour", "primary", _rgb_to_hex(params, "primary")),
            _colour_input("Secondary Colour", "secondary", _rgb_to_hex(params, "secondary")),
            _colour_input("Impact Colour", "impact", _rgb_to_hex(params, "impact")),
        ]
    )

    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VPML Workbench</title>
  <style>
    :root {
      --ink: #17202a;
      --muted: #5f6b76;
      --line: #cad3dd;
      --panel: #f5f7fa;
      --field: #ffffff;
      --action: #0f766e;
      --action-ink: #ffffff;
      --bad: #b42318;
      --ok: #0f7a4c;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); background: #ffffff; }
    main { max-width: 1220px; margin: 0 auto; padding: 22px; }
    header { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; border-bottom: 1px solid var(--line); padding-bottom: 14px; margin-bottom: 16px; }
    h1 { margin: 0 0 4px; font-size: 26px; }
    h2 { margin: 0 0 12px; font-size: 17px; }
    h3 { margin: 14px 0 8px; font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: 0; }
    p { margin: 0; color: var(--muted); }
    form { display: grid; grid-template-columns: 360px minmax(0, 1fr); gap: 18px; align-items: start; }
    .panel { background: var(--panel); border: 1px solid var(--line); padding: 14px; }
    .stack { display: grid; gap: 12px; }
    .control-grid { display: grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap: 12px; }
    label { display: grid; gap: 6px; font-size: 13px; font-weight: 700; }
    label span { display: flex; justify-content: space-between; gap: 10px; }
    input, select { width: 100%%; min-height: 38px; border: 1px solid var(--line); background: var(--field); padding: 8px 9px; font: inherit; }
    input[type="range"] { padding-left: 0; padding-right: 0; }
    input[type="color"] { padding: 2px; height: 42px; }
    .two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
    button { min-height: 40px; border: 1px solid var(--action); background: var(--action); color: var(--action-ink); padding: 9px 13px; font-weight: 800; cursor: pointer; }
    button.secondary { background: #ffffff; color: var(--action); }
    button.stop { border-color: var(--bad); background: #ffffff; color: var(--bad); }
    .badge { display: inline-block; border: 1px solid var(--line); padding: 4px 7px; font-size: 12px; font-weight: 800; text-transform: uppercase; }
    .badge.ok { border-color: var(--ok); color: var(--ok); background: #f0fff7; }
    .badge.bad { border-color: var(--bad); color: var(--bad); background: #fff1f0; }
    .result { margin-top: 18px; border: 1px solid var(--line); padding: 14px; background: #ffffff; }
    .result-head { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
    pre { margin: 0; overflow: auto; background: #eef3f7; border: 1px solid var(--line); padding: 10px; max-height: 260px; font-size: 12px; }
    table { width: 100%%; border-collapse: collapse; table-layout: fixed; }
    th, td { border: 1px solid var(--line); padding: 7px 8px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }
    th { background: #eef3f7; font-size: 12px; }
    code { background: #eef3f7; padding: 2px 4px; }
    .notice { border-left: 4px solid #9a5a00; background: #fff8eb; padding: 10px 12px; margin-bottom: 14px; color: #503300; }
    @media (max-width: 920px) {
      main { padding: 14px; }
      header, form { display: block; }
      .panel { margin-bottom: 14px; }
      .control-grid, .two { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>VPML Workbench</h1>
      <p>Compile bounded motion parameters and host-local recipe variants for the VPML harness.</p>
    </div>
    <span class="badge %s">%s</span>
  </header>
  <div class="notice">This workbench compiles host-local presets and recipes. Serial actions are disabled unless the server starts with <code>--allow-device</code>. It does not upload firmware, run arbitrary code, use raw receive, or use AP/REST/WebSocket control.</div>
  <form method="post" action="/action">
    <aside class="panel stack">
      <h2>Connection</h2>
      <label>Serial Port
        <input name="port" value="%s" autocomplete="off">
      </label>
      <div class="two">
        <label>Baud
          <input name="baud" type="number" min="1" value="%s">
        </label>
        <label>Expected Chip
          <input name="expect_chip_id" value="%s" autocomplete="off">
        </label>
      </div>
      <label>Programme
        <select name="programme">%s</select>
      </label>
      <label class="colour">
        <span>Emit Defaults</span>
        <input name="include_defaults" type="checkbox">
      </label>
      <div class="actions">
        <button name="action" value="compile" type="submit" class="secondary">Compile</button>
        <button name="action" value="run" type="submit"%s>Run</button>
        <button name="action" value="status" type="submit" class="secondary"%s>Status</button>
        <button name="action" value="stop" type="submit" class="stop"%s>Stop</button>
      </div>
      <h2>Preset Bank</h2>
      <label>Preset Name
        <input name="preset_name" value="%s" autocomplete="off" placeholder="e.g. wide delayed bounce">
      </label>
      <button name="action" value="save" type="submit" class="secondary">Save Preset</button>
      <div class="two">
        <label>Preset A
          <select name="preset_a">%s</select>
        </label>
        <label>Preset B
          <select name="preset_b">%s</select>
        </label>
      </div>
      <div class="actions">
        <button name="action" value="load_a" type="submit" class="secondary">Load A</button>
        <button name="action" value="run_a" type="submit"%s>Run A</button>
        <button name="action" value="load_b" type="submit" class="secondary">Load B</button>
        <button name="action" value="run_b" type="submit"%s>Run B</button>
      </div>
      <h2>Recipe Deck</h2>
      <label>Recipe Name
        <input name="recipe_name" value="%s" autocomplete="off" placeholder="e.g. phase ladder">
      </label>
      <label>Variant Name
        <input name="recipe_variant" value="%s" autocomplete="off" placeholder="e.g. wide phase">
      </label>
      <button name="action" value="save_recipe_variant" type="submit" class="secondary">Save Variant</button>
      <label>Recipe
        <select name="recipe_select">%s</select>
      </label>
      <label>Variant
        <select name="variant_select">%s</select>
      </label>
      <div class="actions">
        <button name="action" value="compile_recipe" type="submit" class="secondary">Compile Recipe</button>
        <button name="action" value="load_recipe_variant" type="submit" class="secondary">Load Variant</button>
        <button name="action" value="run_recipe_variant" type="submit"%s>Run Variant</button>
      </div>
    </aside>
    <section class="stack">
      <div class="panel">
        <h2>Motion</h2>
        <div class="control-grid">%s</div>
      </div>
      <div class="panel">
        <h2>Levels</h2>
        <div class="control-grid">%s</div>
      </div>
      <div class="panel">
        <h2>Colours</h2>
        <div class="control-grid">%s</div>
      </div>
      <div class="panel">
        <h2>Saved Presets</h2>
        <table>
          <thead><tr><th>Name</th><th>Programme</th><th>Data Bytes</th><th>Compiled Command</th></tr></thead>
          <tbody>%s</tbody>
        </table>
      </div>
      <div class="panel">
        <h2>Recipe Variants</h2>
        <table>
          <thead><tr><th>Variant</th><th>Programme</th><th>Data Bytes</th><th>Command</th></tr></thead>
          <tbody>%s</tbody>
        </table>
      </div>
      %s
    </section>
  </form>
</main>
</body>
</html>
""" % (
        "ok" if allow_device else "bad",
        _esc(device_badge),
        _esc(port),
        _esc(baud),
        _esc(expect_chip_id),
        programmes,
        device_disabled_attr,
        device_disabled_attr,
        device_disabled_attr,
        _esc(preset_name),
        preset_options_a,
        preset_options_b,
        device_disabled_attr,
        device_disabled_attr,
        _esc(recipe_name),
        _esc(recipe_variant),
        recipe_options,
        variant_options,
        device_disabled_attr,
        motion_controls,
        level_controls,
        colour_controls,
        preset_rows,
        recipe_rows,
        _result_panel(compiled, live),
    )


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "VPMLWorkbench/1"

    def _send_html(self, text: str, status: int = 200) -> None:
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(404)
            return
        self._send_html(render_page(defaults=self.server.defaults))

    def do_POST(self) -> None:
        if self.path != "/action":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        form = {key: values[-1] for key, values in urllib.parse.parse_qs(body, keep_blank_values=True).items()}
        values = values_from_payload(payload_from_form(form), form)
        try:
            compiled, live, loaded_payload = run_action(
                form,
                preset_dir=Path(self.server.defaults["preset_dir"]),
                recipe_dir=Path(self.server.defaults["recipe_dir"]),
                allow_device=bool(self.server.defaults.get("allow_device")),
            )
            if loaded_payload is not None:
                values = values_from_payload(loaded_payload, form)
            if form.get("action") == "save_recipe_variant":
                values["recipe_select"] = form.get("recipe_name") or form.get("recipe_select", "")
                values["variant_select"] = form.get("recipe_variant", "")
            self._send_html(render_page(compiled=compiled, live=live, values=values, defaults=self.server.defaults))
        except Exception as exc:
            sys.stderr.write("VPML workbench error: %s\n" % traceback.format_exc(limit=4))
            live = {"ok": False, "error": str(exc)}
            compiled = None
            try:
                compiled = compile_form(form)
            except Exception:
                pass
            self._send_html(render_page(compiled=compiled, live=live, values=values, defaults=self.server.defaults), status=400)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("VPML workbench: " + fmt % args + "\n")


class WorkbenchServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_class, defaults: dict[str, Any]):
        super().__init__(server_address, handler_class)
        self.defaults = defaults


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--serial-port", default=DEFAULT_SERIAL_PORT)
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--expect-chip-id", default=DEFAULT_EXPECT_CHIP_ID)
    parser.add_argument("--preset-dir", default=str(DEFAULT_PRESET_DIR))
    parser.add_argument("--recipe-dir", default=str(DEFAULT_RECIPE_DIR))
    parser.add_argument("--allow-device", action="store_true")
    parser.add_argument("--allow-non-loopback", action="store_true")
    args = parser.parse_args(argv)

    try:
        validate_bind_host(args.host, allow_non_loopback=args.allow_non_loopback)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 2

    defaults = {
        "port": args.serial_port,
        "baud": args.baud,
        "expect_chip_id": args.expect_chip_id,
        "programme": "intro_bounce_loop",
        "preset_dir": str(Path(args.preset_dir)),
        "recipe_dir": str(Path(args.recipe_dir)),
        "allow_device": args.allow_device,
    }
    server = WorkbenchServer((args.host, args.port), WorkbenchHandler, defaults)
    print("VPML Workbench: http://%s:%d" % (args.host, args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
