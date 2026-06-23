#!/usr/bin/env python3
"""Compile bounded VPML parameter sets into typed USB CDC commands."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROGRAMMES = {
    "intro_bounce": {"frames": 112},
    "intro_bounce_loop": {"frames": 96},
}

RECIPE_SCHEMA = "vpml_recipe_deck.v1"
MAX_RECIPE_VARIANTS = 12
VPML_SERIAL_PREFIX = ":vpml="
MAX_FIRMWARE_COMMAND_DATA_BYTES = 93


@dataclass(frozen=True)
class ParamSpec:
    default: float
    low: float
    high: float
    step: float
    label: str


PARAMS: dict[str, ParamSpec] = {
    "frames": ParamSpec(96, 48, 180, 1, "Frames"),
    "secondary_phase": ParamSpec(0.10, 0.0, 0.35, 0.01, "Secondary Phase"),
    "primary_width": ParamSpec(5.5, 2.0, 18.0, 0.1, "Primary Width"),
    "secondary_width": ParamSpec(6.8, 2.0, 18.0, 0.1, "Secondary Width"),
    "tail_scale": ParamSpec(1.0, 0.25, 2.0, 0.01, "Tail Scale"),
    "primary_level_base": ParamSpec(0.64, 0.0, 1.0, 0.01, "Primary Base"),
    "primary_level_gain": ParamSpec(0.30, 0.0, 1.0, 0.01, "Primary Gain"),
    "secondary_level_base": ParamSpec(0.58, 0.0, 1.0, 0.01, "Secondary Base"),
    "secondary_level_gain": ParamSpec(0.34, 0.0, 1.0, 0.01, "Secondary Gain"),
    "edge_level": ParamSpec(0.56, 0.0, 0.75, 0.01, "Edge Hit"),
    "centre_level": ParamSpec(0.38, 0.0, 0.70, 0.01, "Centre Catch"),
    "primary_red": ParamSpec(1.0, 0.0, 1.0, 0.01, "Primary Red"),
    "primary_green": ParamSpec(0.38, 0.0, 1.0, 0.01, "Primary Green"),
    "primary_blue": ParamSpec(0.04, 0.0, 1.0, 0.01, "Primary Blue"),
    "secondary_red": ParamSpec(1.0, 0.0, 1.0, 0.01, "Secondary Red"),
    "secondary_green": ParamSpec(0.76, 0.0, 1.0, 0.01, "Secondary Green"),
    "secondary_blue": ParamSpec(0.10, 0.0, 1.0, 0.01, "Secondary Blue"),
    "impact_red": ParamSpec(1.0, 0.0, 1.0, 0.01, "Impact Red"),
    "impact_green": ParamSpec(0.20, 0.0, 1.0, 0.01, "Impact Green"),
    "impact_blue": ParamSpec(0.02, 0.0, 1.0, 0.01, "Impact Blue"),
}


def defaults_for(programme: str) -> dict[str, float]:
    if programme not in PROGRAMMES:
        raise ValueError("unsupported VPML programme: %s" % programme)
    defaults = {key: spec.default for key, spec in PARAMS.items()}
    defaults["frames"] = float(PROGRAMMES[programme]["frames"])
    return defaults


def coerce_params(programme: str, raw_params: dict[str, Any]) -> dict[str, float]:
    params = defaults_for(programme)
    for key, value in raw_params.items():
        if key not in PARAMS:
            raise ValueError("unsupported VPML parameter: %s" % key)
        spec = PARAMS[key]
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid numeric value for %s: %r" % (key, value)) from exc
        if numeric < spec.low or numeric > spec.high:
            raise ValueError("%s must be between %s and %s" % (key, spec.low, spec.high))
        params[key] = numeric
    params["frames"] = float(int(round(params["frames"])))
    if params["primary_level_base"] + params["primary_level_gain"] > 1.0:
        raise ValueError("primary_level_base + primary_level_gain must be <= 1.0")
    if params["secondary_level_base"] + params["secondary_level_gain"] > 1.0:
        raise ValueError("secondary_level_base + secondary_level_gain must be <= 1.0")
    return params


def _format_value(key: str, value: float) -> str:
    if key == "frames":
        return str(int(round(value)))
    return ("%.3f" % value).rstrip("0").rstrip(".")


def _is_default_equivalent(key: str, value: float, default: float) -> bool:
    tolerance = max(0.0005, PARAMS[key].step * 0.5)
    return abs(value - default) < tolerance


def command_data_bytes(command: str) -> int:
    if not command.startswith(VPML_SERIAL_PREFIX):
        raise ValueError("VPML command must start with %s" % VPML_SERIAL_PREFIX)
    return len(command[len(VPML_SERIAL_PREFIX) :].encode("utf-8"))


def validate_command_length(command: str) -> None:
    data_bytes = command_data_bytes(command)
    if data_bytes > MAX_FIRMWARE_COMMAND_DATA_BYTES:
        raise ValueError(
            "compiled command data is %d bytes; firmware metadata parser accepts at most %d"
            % (data_bytes, MAX_FIRMWARE_COMMAND_DATA_BYTES)
        )


def compile_command(programme: str, raw_params: dict[str, Any], *, include_defaults: bool = False) -> dict[str, Any]:
    params = coerce_params(programme, raw_params)
    defaults = defaults_for(programme)
    emitted: list[str] = []
    for key in PARAMS:
        value = params[key]
        if not include_defaults and _is_default_equivalent(key, value, defaults[key]):
            continue
        emitted.append("%s=%s" % (key, _format_value(key, value)))
    if not emitted:
        emitted.append("frames=%s" % _format_value("frames", params["frames"]))
    command = ":vpml=play_params,%s,%s" % (programme, ",".join(emitted))
    validate_command_length(command)
    return {
        "ok": True,
        "programme": programme,
        "params": params,
        "changed": emitted,
        "command": command,
        "command_bytes": len(command.encode("utf-8")),
        "command_data_bytes": command_data_bytes(command),
        "max_command_data_bytes": MAX_FIRMWARE_COMMAND_DATA_BYTES,
    }


def compile_from_payload(payload: dict[str, Any], *, include_defaults: bool = False) -> dict[str, Any]:
    programme = str(payload.get("programme") or "intro_bounce_loop")
    raw_params = payload.get("params") or {}
    if not isinstance(raw_params, dict):
        raise ValueError("params must be an object")
    return compile_command(programme, raw_params, include_defaults=include_defaults)


def _clean_variant_name(value: Any, fallback: str) -> str:
    name = str(value or "").strip()
    return name or fallback


def compile_variant(
    variant: dict[str, Any],
    *,
    default_programme: str,
    index: int,
    include_defaults: bool = False,
) -> dict[str, Any]:
    if not isinstance(variant, dict):
        raise ValueError("recipe variant %d must be an object" % (index + 1))
    programme = str(variant.get("programme") or default_programme)
    raw_params = variant.get("params") or {}
    if not isinstance(raw_params, dict):
        raise ValueError("recipe variant %d params must be an object" % (index + 1))
    compiled = compile_command(programme, raw_params, include_defaults=include_defaults)
    return {
        "name": _clean_variant_name(variant.get("name"), "variant-%02d" % (index + 1)),
        "programme": compiled["programme"],
        "params": compiled["params"],
        "changed": compiled["changed"],
        "command": compiled["command"],
        "command_bytes": compiled["command_bytes"],
        "command_data_bytes": compiled["command_data_bytes"],
        "max_command_data_bytes": compiled["max_command_data_bytes"],
    }


def compile_recipe(payload: dict[str, Any], *, include_defaults: bool = False) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("recipe must be an object")
    schema = str(payload.get("schema") or RECIPE_SCHEMA)
    if schema != RECIPE_SCHEMA:
        raise ValueError("unsupported VPML recipe schema: %s" % schema)
    default_programme = str(payload.get("programme") or "intro_bounce_loop")
    if default_programme not in PROGRAMMES:
        raise ValueError("unsupported VPML programme: %s" % default_programme)
    variants = payload.get("variants") or []
    if not isinstance(variants, list) or not variants:
        raise ValueError("recipe variants must be a non-empty array")
    if len(variants) > MAX_RECIPE_VARIANTS:
        raise ValueError("recipe variants must contain at most %d entries" % MAX_RECIPE_VARIANTS)
    compiled_variants = [
        compile_variant(
            variant,
            default_programme=default_programme,
            index=index,
            include_defaults=include_defaults,
        )
        for index, variant in enumerate(variants)
    ]
    return {
        "ok": True,
        "schema": RECIPE_SCHEMA,
        "name": str(payload.get("name") or "Untitled Recipe"),
        "programme": default_programme,
        "device_sequencing": False,
        "runtime_owner": "host_manual",
        "variants": compiled_variants,
        "command_bytes_total": sum(item["command_bytes"] for item in compiled_variants),
    }


def schema_payload() -> dict[str, Any]:
    return {
        "programmes": PROGRAMMES,
        "params": {
            key: {
                "default": spec.default,
                "low": spec.low,
                "high": spec.high,
                "step": spec.step,
                "label": spec.label,
            }
            for key, spec in PARAMS.items()
        },
        "recipe": {
            "schema": RECIPE_SCHEMA,
            "max_variants": MAX_RECIPE_VARIANTS,
            "device_sequencing": False,
            "runtime_owner": "host_manual",
        },
        "serial": {
            "vpml_prefix": VPML_SERIAL_PREFIX,
            "max_firmware_command_data_bytes": MAX_FIRMWARE_COMMAND_DATA_BYTES,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="JSON file with programme + params; stdin if omitted")
    parser.add_argument("--programme", choices=sorted(PROGRAMMES))
    parser.add_argument("--param", action="append", default=[], help="key=value override; may repeat")
    parser.add_argument("--include-defaults", action="store_true")
    parser.add_argument("--recipe", action="store_true", help="Compile a recipe deck from --input or stdin")
    parser.add_argument("--schema", action="store_true")
    args = parser.parse_args(argv)

    try:
      if args.schema:
          result = schema_payload()
      else:
          payload: dict[str, Any] = {}
          if args.input:
              payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
          elif not sys.stdin.isatty():
              text = sys.stdin.read().strip()
              payload = json.loads(text) if text else {}
          if args.recipe:
              result = compile_recipe(payload, include_defaults=args.include_defaults)
              print(json.dumps(result, indent=2, sort_keys=True))
              return 0
          if args.programme:
              payload["programme"] = args.programme
          params = dict(payload.get("params") or {})
          for item in args.param:
              if "=" not in item:
                  raise ValueError("--param must be key=value")
              key, value = item.split("=", 1)
              params[key] = value
          payload["params"] = params
          result = compile_from_payload(payload, include_defaults=args.include_defaults)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
      result = {"ok": False, "error": str(exc)}

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
