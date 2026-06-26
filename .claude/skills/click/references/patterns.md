# Click Patterns Reference

## Contents
- Core Argument Patterns
- K1 Harness-Specific Patterns
- Anti-Patterns
- Testing Click CLIs

---

## Core Argument Patterns

### Device Path (most common in this repo)

```python
# new code to add
@click.option(
    "--port",
    envvar="K1_DEVICE",          # allows K1_DEVICE=/dev/ttyACM0 in CI
    default="/dev/ttyUSB0",
    show_default=True,
    help="K1 serial device path",
)
```

Always use `envvar=` for device paths — CI runners and Tab5 harnesses may not have the same `/dev/tty*` paths as dev machines.

### Input File (WAV, fixture, transcript)

```python
# new code to add
@click.argument("wav_file", type=click.Path(exists=True, dir_okay=False, readable=True))
```

Use `click.Path(exists=True)` — gives a clean error message before your code runs, not a cryptic `FileNotFoundError` mid-execution.

### Output File (optional write)

```python
# new code to add
@click.option("--out", type=click.Path(dir_okay=False, writable=True), default=None)
# then in body:
if out:
    Path(out).write_text(result)
else:
    click.echo(result)
```

### Verbosity Levels

```python
# new code to add — matches existing harness convention
@click.option("-v", "--verbose", count=True, help="Repeat for more detail (-vvv)")
# 0=quiet, 1=info, 2=debug, 3=trace
```

Use `count=True` not `is_flag=True` when tools have multiple verbosity levels. `is_flag=True` is fine for simple on/off.

---

## K1 Harness-Specific Patterns

### Mode/Channel Selection (matches K1 effect indexing)

```python
# new code to add
@click.option(
    "--mode", type=click.IntRange(0, 24), default=None,
    help="Light mode index (0-24); omit to test all"
)
@click.option(
    "--channel", type=click.Choice(["primary", "secondary", "both"]), default="both"
)
```

Effect modes are 0-indexed, currently 0–24. Use `IntRange` — it rejects out-of-bounds before your validation logic runs.

### JSON vs Human Output

```python
# new code to add
@click.option("--json", "output_format", flag_value="json")
@click.option("--text", "output_format", flag_value="text", default=True)
```

Diagnostic tools piped into CI need `--json`; interactive use needs readable text. This flag_value pattern avoids an extra `--format` enum.

---

## Anti-Patterns

### WARNING: sys.argv Parsing in Diagnostic Scripts

**The Problem:**
```python
# BAD — found in older scripts
import sys
port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
```

**Why This Breaks:**
1. No `--help`, no type validation, no error messages
2. Breaks when called via `CliRunner` in pytest (args are positional and fragile)
3. Cannot be composed into a `@click.group()` subcommand later

**The Fix:**
```python
# GOOD
@click.command()
@click.option("--port", default="/dev/ttyUSB0")
def main(port): ...
```

### WARNING: print() Instead of click.echo()

**The Problem:**
```python
# BAD
print(f"Connected to {port}")
```

**Why This Breaks:**
1. `print()` goes to stdout unconditionally — mixing with structured JSON output breaks pipe consumers
2. `click.echo()` respects `standalone_mode=False` and can be redirected in tests
3. Error messages via `print()` go to stdout, not stderr

**The Fix:**
```python
# GOOD
click.echo(f"Connected to {port}")
click.echo("Error: device not found", err=True)  # → stderr
```

### WARNING: Mutable Default in Option

**The Problem:**
```python
# BAD
@click.option("--modes", default=[0, 1, 2], multiple=True)
```

**Why This Breaks:** Click handles `multiple=True` via tuple accumulation, not list mutation — but passing a mutable list default causes confusing behaviour across invocations.

**The Fix:**
```python
# GOOD — use tuple or None + in-body default
@click.option("--modes", multiple=True, type=int)
# body: modes = modes or (0, 1, 2)
```

---

## Testing Click CLIs

Use `CliRunner` from `click.testing` — already available if click is installed. See the **pytest** skill for full harness integration.

```python
# new code to add — tests/test_my_tool.py
from click.testing import CliRunner
from tools.my_diagnostic import main

def test_help():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0

def test_missing_device(tmp_path):
    result = CliRunner().invoke(main, ["--port", "/dev/nonexistent"])
    assert result.exit_code != 0
```

Always test `exit_code`, not just output text — harnesses in CI gate on exit code.