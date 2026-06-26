---
name: ruff
description: |
  Lints Python code and detects style/logic issues at high speed using ruff.
  Use when: running Python linting, fixing style violations, configuring lint rules, integrating ruff into CI, or auditing Python files in this repo (tests/, tools/, scripts/).
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# Ruff

Ruff is a fast Python linter and formatter (replaces flake8, isort, pyupgrade, and more). This repo's Python surface includes `tests/`, `tools/`, and `scripts/` — primarily pytest harnesses and host-side analysis tools.

## Before You Code (REQUIRED)

This skill's content was captured at generation time and MAY be stale. For ANY non-trivial change involving ruff, verify against current docs FIRST:



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

```bash
# Check all Python files
ruff check .

# Auto-fix fixable violations
ruff check --fix .

# Format (ruff's black-compatible formatter)
ruff format .

# Check + format in one pass (CI pattern)
ruff check --fix . && ruff format .

# Check a specific file
ruff check tests/test_sb_tab5_wireless_controller_static.py
```

## Key Concepts

| Concept | Usage | Example |
|---------|-------|---------|
| Rule codes | `E`=pycodestyle, `F`=pyflakes, `I`=isort, `N`=pep8-naming, `UP`=pyupgrade | `ruff check --select F401` |
| `# noqa: CODE` | Suppress a specific rule on one line | `import os  # noqa: F401` |
| `--fix` | Auto-apply safe fixes | `ruff check --fix .` |
| `--unsafe-fixes` | Apply fixes that change semantics | Use only after review |
| Per-file ignores | Silence rules for generated/legacy files | `[tool.ruff.lint.per-file-ignores]` |

## Common Patterns

### CI Gate (iterate-until-pass)

```bash
# 1. Run check
ruff check .
# 2. Fix auto-fixable issues
ruff check --fix .
# 3. Re-run — must be clean before commit
ruff check .
# 4. If violations remain, fix manually then repeat step 3
```

### Minimal `pyproject.toml` Config

```toml
# new code to add
[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP"]
ignore = ["E501"]  # line length — adjust to project tolerance

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["F811"]  # fixture redefinition is normal in pytest
```

## See Also

- [patterns](references/patterns.md)
- [workflows](references/workflows.md)

## Related Skills

- See the **pytest** skill for test harness integration
- See the **python** skill for broader Python patterns
- See the **clang-format** skill for analogous C/C++ linting workflows