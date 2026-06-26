# Click Workflows Reference

## Contents
- New Diagnostic Tool Checklist
- Adding CLI to an Existing Script
- Subcommand Group Workflow
- CI Integration Pattern

---

## New Diagnostic Tool Checklist

Copy this checklist when building a new CLI tool:

```
- [ ] Place tool in tools/ or scripts/ (never project root)
- [ ] Add @click.command() or @click.group() at entry point
- [ ] Use envvar= for device paths (K1_DEVICE, K1_PORT)
- [ ] Use click.Path(exists=True) for required file inputs
- [ ] Use click.echo(..., err=True) for error output
- [ ] Add if __name__ == "__main__": main()
- [ ] Write a CliRunner smoke test in tests/
- [ ] Verify --help output is clean: python tools/mytool.py --help
- [ ] Run: bun run check-types (if .pyi stubs present)
```

---

## Adding CLI to an Existing Script

Refactoring a script that uses `sys.argv` or `argparse`:

1. Wrap the main logic in a function with no argument parsing
2. Create a `@click.command()` entry point that calls it
3. Map each `sys.argv[N]` to a `@click.option` or `@click.argument`
4. Replace all `print()` error output with `click.echo(..., err=True)`
5. Validate: `python mytool.py --help` — confirm all options appear

**Iterate-until-pass:**
```
1. Convert one argument at a time
2. Validate: python mytool.py --help
3. Validate: python -c "from tools.mytool import main" (import check)
4. Only move to next argument when current one works
```

---

## Subcommand Group Workflow

Use `@click.group()` when a tool has 3+ distinct operations (capture, replay, compare):

```python
# new code to add — tools/k1_harness.py
import click

@click.group()
@click.option("--device", envvar="K1_DEVICE", default="/dev/ttyUSB0", show_default=True)
@click.pass_context
def cli(ctx, device):
    """K1 diagnostic harness."""
    ctx.ensure_object(dict)
    ctx.obj["device"] = device

@cli.command()
@click.argument("output", type=click.Path(dir_okay=False, writable=True))
@click.pass_context
def capture(ctx, output):
    """Capture a diagnostic session to OUTPUT file."""
    device = ctx.obj["device"]
    ...

@cli.command()
@click.argument("transcript", type=click.Path(exists=True))
@click.pass_context
def replay(ctx, transcript):
    """Replay a captured transcript."""
    ...

if __name__ == "__main__":
    cli()
```

**Rule:** Share device/config state via `ctx.obj`, not global variables. Global state breaks parallel CliRunner tests.

---

## CI Integration Pattern

Diagnostic tools run in CI (regression harness) need structured output and deterministic exit codes:

```python
# new code to add
@click.command()
@click.option("--json", "fmt", flag_value="json", help="Machine-readable output")
@click.option("--text", "fmt", flag_value="text", default=True)
@click.pass_context
def run(ctx, fmt):
    results = collect_results()
    if fmt == "json":
        click.echo(json.dumps(results))
    else:
        for r in results:
            click.echo(f"  {r['name']}: {r['status']}")
    
    failed = [r for r in results if r["status"] == "FAIL"]
    ctx.exit(1 if failed else 0)  # explicit exit code for CI gating
```

**DO:** Use `ctx.exit(code)` not `sys.exit(code)` — `sys.exit` raises `SystemExit` which breaks `CliRunner` tests.

**DO:** Emit all diagnostic noise to stderr (`err=True`), structured results to stdout — this lets CI capture `--json` output cleanly via stdout redirection.

**DON'T:** Swallow exceptions silently. Let click propagate them with `standalone_mode=True` (default) so CI sees a non-zero exit.

---

## Related Skills

- See the **pytest** skill for `CliRunner`-based test patterns
- See the **aiofiles** skill when the CLI wraps async file operations
- See the **python** skill for project-wide conventions on script structure