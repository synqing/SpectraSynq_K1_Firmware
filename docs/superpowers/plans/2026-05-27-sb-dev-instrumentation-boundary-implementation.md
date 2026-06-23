# SB Dev Instrumentation Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make developer instrumentation impossible to treat as production code, and make MabuTrace a mandatory dev-only escalation tool for timing/causality questions.

**Architecture:** SB-native diagnostics remain the canonical product-proof substrate. MabuTrace is not optional lore; it is a mandatory escalation path when scalar logs cannot answer timeline/causality questions, but it remains non-shippable and outside production build dependencies.

**Tech Stack:** Markdown governing docs, PlatformIO env inspection, Python `unittest` static guard tests.

---

## File Structure

- Modify: `docs/superpowers/specs/2026-05-27-sb-trace-diagnostic-design.md`
  - Tighten "optional MabuTrace" language to "mandatory dev-only escalation".
- Modify: `AGENTS.md`
  - Add Codex-side load-bearing production/developer instrumentation rule.
- Modify: `.claude/CLAUDE.md`
  - Add canonical Claude-side rule matching `AGENTS.md`.
- Create: `tests/test_dev_instrumentation_boundary.py`
  - Enforce doc language and build-config separation.

## Task 1: Tighten Design Language

**Files:**
- Modify: `docs/superpowers/specs/2026-05-27-sb-trace-diagnostic-design.md`

- [x] **Step 1: Replace optional wording**

Replace claims that MabuTrace is merely optional with:

```text
MabuTrace is a mandatory developer-only escalation tool for timeline/causality questions, not an optional diagnostic preference and never a production dependency.
```

- [x] **Step 2: Add escalation triggers**

Add explicit triggers:

```text
Escalate to MabuTrace dev trace when the unknown is nested timing, cross-core/audio-render causality, scalar counter disagreement, frame-drop causality, or diagnostic harness perturbation.
```

- [x] **Step 3: Keep SB-native canonical**

State:

```text
SB-native diagnostics remain canonical for product-proof evidence, VPAB/final-byte payloads, visual-memory gates, and anything that must survive as a reusable internal harness.
```

## Task 2: Encode Governing Rule

**Files:**
- Modify: `AGENTS.md`
- Modify: `.claude/CLAUDE.md`

- [x] **Step 1: Add load-bearing rule**

Add a section that says:

```text
Developer/instrumentation code never ships with production firmware.
```

- [x] **Step 2: Add MabuTrace escalation rule**

Add a rule that says:

```text
MabuTrace is mandatory for timeline/causality escalation when scalar SB-native diagnostics cannot answer the question, but MabuTrace remains developer-only and non-shippable.
```

- [x] **Step 3: Add production contamination rule**

Add a rule that production builds must not include MabuTrace dependencies, trace-dev flags, or developer-only behaviour.

## Task 3: Add Static Guard Tests

**Files:**
- Create: `tests/test_dev_instrumentation_boundary.py`

- [x] **Step 1: Test governing text exists**

Test that `AGENTS.md`, `.claude/CLAUDE.md`, and the spec contain the developer-code-never-ships rule and mandatory MabuTrace escalation language.

- [x] **Step 2: Test production env is clean**

Parse `platformio.ini`; assert `[env:k1_hardware]` contains no `mabutrace`, `ENABLE_MABUTRACE`, `MABUTRACE`, `trace_dev`, or `k1_hardware_trace_dev`.

- [x] **Step 3: Test MabuTrace includes are constrained**

Search firmware sources; if `<mabutrace.h>` appears, fail unless the only containing file is a future `sb_trace.h`.

- [x] **Step 4: Test trace-dev env naming if introduced**

If any PlatformIO env contains `mabutrace`, assert the env name includes `trace_dev` and comments contain `non-shippable`.

## Task 4: Verify

**Files:**
- Test: `tests/test_dev_instrumentation_boundary.py`
- Test: existing `tests/test_diag_capture_static.py`
- Test: existing `tests/test_vpab_gate.py`

- [x] **Step 1: Run static tests**

Run:

```bash
python3 -B -m unittest discover -s tests -p test_dev_instrumentation_boundary.py
python3 -B -m unittest discover -s tests -p test_diag_capture_static.py
python3 -B -m unittest discover -s tests -p test_vpab_gate.py
```

- [x] **Step 2: Build production**

Run:

```bash
pio run -e k1_hardware
```

- [x] **Step 3: Build harness**

Run:

```bash
pio run -e k1_hardware_harness
```

- [x] **Step 4: Report proof boundary**

Report that this slice proves static/build separation only. It does not provide runtime trace evidence, visual-memory proof, or hardware/video validation.

Completed 2026-05-27:

- `test_dev_instrumentation_boundary.py`: 8 tests OK.
- `test_diag_capture_static.py`: 4 tests OK.
- `test_vpab_gate.py`: 10 tests OK.
- `pio run -e k1_hardware`: exit 0, production compile proof only.
- `pio run -e k1_hardware_harness`: exit 0, harness compile proof only.
- Production artifact string scan found no `MabuTrace`, `mabutrace`, `VPAB`, `DIAG_CAPTURE`, `diagnostic_capture`, or `vpab_capture` strings in `firmware.elf`.
- Production build directory contains no `diagnostic_capture` or `vpab_capture` object/dependency files; harness build directory contains the expected `diagnostic_capture.cpp.o`, `vpab_capture.cpp.o`, `.d` files.
- No serial port was opened and no upload/runtime proof is claimed.
