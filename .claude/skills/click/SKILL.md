---
name: click
description: |
  Creates command-line interfaces for Python diagnostic tools in the SensoryBridge K1 project.
  Use when: adding CLI flags/options to diagnostic scripts, harness tools, or replay utilities; building Python tools that accept device paths, file inputs, verbosity flags, or structured output modes; wrapping pytest fixtures or tools/tab5_k1_dashboard_harness.py-style scripts with proper argument parsing.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# Click Skill

Click is the CLI framework for SensoryBridge Python tooling — diagnostic harnesses, replay scripts, and test fixtures. Use it over `argparse` for all new tooling: it composes better, handles types natively, and produces consistent `--help` output across tools.

## Before You Code (REQUIRED)

This skill's content was captured at generation time and MAY be stale. For ANY non-trivial change involving click, verify against current docs FIRST:



Then:

1. **Match the installed version.** Cross-reference against the version installed in this repo. APIs change across minor versions; do not assume.
2. **Discover provider best practices.** If the task touches a production-sensitive capability, inspect the provider service catalog, official docs, and project docs before choosing an implementation.
3. **Respect explicit direction.** If the user explicitly asks for a specific mechanism, follow it. If project docs clearly mandate a mechanism, follow the project. In both cases, mention the provider-recommended alternative and make the chosen path safe.
4. **Prefer provider-native primitives by default.** If no explicit user/project override exists and the change involves caching, rate limiting, background work, scheduled jobs, shared state, queues, or secrets, use the provider-recommended binding/API. Do not hand-roll an in-memory or polyfill solution that "works" locally but breaks under the provider's execution model — derive the need→native-primitive mapping yourself from this provider's docs.

## Skill Advantage Protocol

Using this skill should produce a meaningfully better result than an unskilled baseline. Apply this loop before and during implementation:

1. **Clarify only when it changes the outcome.** Ask the smallest useful set of questions when the request is ambiguous, preference-heavy, or could change architecture, user-visible behavior, data shape, security posture, analytics, or external side effects. If the safe assumption is obvious, state it and proceed. When asked to surface data that no existing code path captures, state up front the assumption that capture starts now (no backfill) or ask if a backfill source exists — do not silently build net-new storage without surfacing this.
2. **Inspect the nearest real patterns.** Read adjacent files, routes, components, tests, schema, infra, copy, and analytics surfaces before inventing structure. Treat local conventions as the starting point.
3. **Optimize the task's highest-leverage axis.** Identify what would make the result win a review: user-visible correctness, integration quality, accessibility, security, reliability, maintainability, operability, or speed of future change.
4. **Reuse before reimplementing.** Prefer existing components, hooks, helpers, formatting/utility functions, data registries, metadata builders, analytics, pricing, checkout, auth, routing utilities, and API procedures/endpoints/data sources over local one-off clones. Before adding a new API procedure, query, or data fetch, search for one that already returns this data and extend it in place — a surface that fetches data and only logs or partially uses it is a reuse target, not an absent one; never author a parallel endpoint or leave the original orphaned. Before importing for a data fetch, grep the screen for the call it already makes and reuse that exact client/singleton import path and endpoint/procedure name; never create a second client, transport, or parallel endpoint for data an existing call returns, and confirm every imported path and symbol actually exists in the repo before writing it.
5. **Use semantic structures.** Tables, lists, forms, buttons, links, headings, and disclosure controls should use native/project accessible primitives instead of div-only lookalikes.
6. **Prevent drift by construction.** Centralize repeated facts, labels, claims, product defaults, and shared table cells in registries or helpers when multiple surfaces need the same answer.
7. **Synthesize, do not merely comply.** Combine this skill's guidance with repo evidence and the user's goal. When two good approaches exist, borrow the strongest parts of each instead of blindly choosing one.
8. **Check claims against code.** Product copy, docs, and comments must not imply automation, integrations, performance, security, refresh cadence, counts, or data flow that the implementation does not actually provide. Any claim that one component writes, records, updates, calls, or is the source of truth for another is allowed only if the edit performing it is in this same change; before finishing, check each such cross-component claim against the actual edits and downgrade unbacked ones to an explicit TODO or implement them now.
9. **Ship the complete slice.** Include every adjacent artifact needed for the change to be usable and maintainable: wiring, state handling, validation, analytics, tests, docs, migrations, or infra when those surfaces are part of the behavior. When the task shows, displays, or lists user data, deliver the full vertical slice and do not stop at an internal/API/CLI layer: the data-model/schema change AND its migration (a schema change without a migration is incomplete), the path that writes or populates the data, an authenticated endpoint scoped to the current user, and the primary user-facing surface wired through the project's typed data client. Before declaring done, trace one record end-to-end (triggering event → write → read → render); if any hop exists only in a comment or docstring rather than edited code, the slice is NOT done. Shipping only the persistence layer (a schema/migration with no writer, reader, or surface) is an incomplete slice, not a milestone.

## Capability Contract

Use this section when the user prompt touches production risk, even if the prompt does not name this technology explicitly.




Required wiring surfaces:
- provider/runtime configuration discovered during implementation
- nearest typed request/context boundary
- handler/procedure boundary before external side effects

Side-effect barrier:
- Place guards before external APIs, auth mutations, email sends, analytics events, storage writes, and database mutations.


Fallback policy:
- Prefer provider-native/platform-managed primitives by default when no explicit override exists.
- Follow clear user/project overrides, but mention the native alternative and tradeoff.
- Fallbacks must be durable, multi-instance safe, and atomic under concurrency.

Verification rules:
- [error] native-or-explicit-override: Use the provider-native primitive first unless the user/project explicitly overrides it.
- [error] atomic-fallback: Fallback counters must be atomic under concurrency.

## Quick Start

### New Diagnostic Tool Pattern

```python
# new code to add — tools/my_diagnostic.py
import click

@click.command()
@click.option("--port", default="/dev/ttyUSB0", show_default=True, help="Serial device path")
@click.option("--baud", default=115200, type=int, show_default=True)
@click.option("--output", type=click.Path(dir_okay=False, writable=True), help="Write results to file")
@click.option("--verbose", "-v", is_flag=True)
def main(port, baud, output, verbose):
    """Diagnose K1 device over serial."""
    ...

if __name__ == "__main__":
    main()
```

### Multi-Command Tool (harness with subcommands)

```python
# new code to add
@click.group()
@click.option("--device", envvar="K1_DEVICE", default="/dev/ttyUSB0")
@click.pass_context
def cli(ctx, device):
    ctx.ensure_object(dict)
    ctx.obj["device"] = device

@cli.command()
@click.pass_context
def capture(ctx):
    """Capture a diagnostic trace."""
    device = ctx.obj["device"]
    ...
```

## Key Concepts

| Concept | Usage | Example |
|---------|-------|---------|
| `@click.option` | Named flags/values | `--port /dev/ttyUSB0` |
| `@click.argument` | Positional required input | `<wav_file>` |
| `click.Path` | File/dir with existence checks | `type=click.Path(exists=True)` |
| `click.Choice` | Validated enum-like input | `type=click.Choice(["ap", "vp"])` |
| `@click.pass_context` | Share state across subcommands | `ctx.obj["device"]` |
| `envvar=` | Fall back to env var | `envvar="K1_DEVICE"` |

## Common Patterns

See [patterns](references/patterns.md) for harness-specific patterns and anti-patterns.
See [workflows](references/workflows.md) for tool development workflow checklists.

## Related Skills

- See the **pytest** skill for integrating click CLIs with the test harness via `CliRunner`
- See the **python** skill for project-wide Python conventions
- See the **aiofiles** skill if the CLI wraps async I/O operations