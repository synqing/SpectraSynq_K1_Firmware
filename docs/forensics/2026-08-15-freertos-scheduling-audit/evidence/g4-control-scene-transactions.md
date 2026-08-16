# Gate 4 — Transactional control and scene channels

**Date:** 2026-08-17

```text
G4_HOST        = CLOSED
G4_FIRMWARE    = WIRED (dual-scene publish + VP apply)
```

Primitives: latest-wins state mailbox, one two-channel scene generation, bounded at-most-once edge queue. Host: `tests/test_k1_command_channels_interleave.py`.

Wireless `primary.mode` / `secondary.mode` publish one complete scene. VP applies secondary (and primary when no mode transition is queued) on the same frame. Existing primary crossfade path is preserved.

Queue capacity `K1_CMD_EDGE_CAPACITY = 8` (compile-time; not yet derived from a measured drain pause).
