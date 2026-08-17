# Archify living maps — inventory #21

**Archify pin:** `2.14.0`  
**Skill root:** `/Users/spectrasynq/.claude/skills/archify`

## Maps

| Map ID | Type | JSON | HTML | Receipt |
|---|---|---|---|---|
| `k1-runtime.architecture` | `architecture` | `k1-runtime.architecture.json` | `k1-runtime.architecture.html` | `k1-runtime.architecture.receipt.json` |

## Refresh recipe

```bash
ARCHIFY=/Users/spectrasynq/.claude/skills/archify/bin/archify.mjs
MAP=/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/architecture/archify/k1-runtime.architecture
node "$ARCHIFY" validate architecture "$MAP.json" --quality showcase --json --repo-root /Users/spectrasynq/SpectraSynq_K1_Firmware
node "$ARCHIFY" deliver architecture "$MAP.json" "$MAP.html" --quality showcase --json --repo-root /Users/spectrasynq/SpectraSynq_K1_Firmware
node "$ARCHIFY" visual-check "$MAP.html" --json
# Read visual-check PNG sidecars with vision before Captain-ready claims
```

## Source revision at authoring

- git SHA / pin: `1d45774059c3967fcb5e9e853f0105a7e2a28cf6`
- Captain selection inventory #: `21`
