---
name: k1-lineage-routing
description: >-
  Mandatory routing for K1 firmware build, flash, effect port, and WB-4 migration.
  Prevents donor-repo confusion, port-vs-MAC errors, and framework paste. Canonical
  oracle mirror at docs/agent/K1_LINEAGE_AGENT_ORACLE.md.
disable-model-invocation: false
---

# K1 Lineage Routing (K1 repo)

**Canonical oracle (full):** `docs/agent/K1_LINEAGE_AGENT_ORACLE.md`  
**Lightwave master:** `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/instructions/k1-lineage-agent-oracle.md`

## HARD STOP

1. **This repo** (`SpectraSynq_K1_Firmware`) is the **only** shipping firmware.
2. **`Lightwave-Ledstrip/firmware-v3`** is dead donor — read-only for WB-4; no product edits/flashes there.
3. **"Latest build"** — three answers (product env / git HEAD / on-device). See oracle.
4. **`read_mac` before flash** — main `F887A500`, bench `B489A500`.
5. **No `RenderContext`/`ControlBus` paste** — use `light_mode_*` + `K1AudioContext`.

## Preflight

```bash
bash scripts/agent/session-bootstrap.sh
```

## Port checklist

1. Decomposition doc in `docs/architecture/effect-decomposition/`
2. `tests/test_<name>_static.py` failing first
3. `effects/light_mode_<name>.cpp` — centre-origin, no rainbow, no heap in render
4. 8-file registration gate
5. VPAB if motion claimed

**Withhold:** `0x0E06`, `0x1B04`, STM (WB-3), bins256 without producers.

## Related

- `AGENT_OS.md` — bootstrap ritual
- `K1_CANONICAL_CONTEXT.md` §8 — lineage traps
- `k1-effect-development` skill — registration gate
