---
name: k1-tab5-wireless-control
description: |
  Use when implementing, debugging, or reviewing Tab5-to-K1 wireless control: K1 AP join, WebSocket lifecycle, K1 control names, ACK/result handling, reconnection behaviour, or disconnects between Tab5 UI state and K1 runtime state.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# K1 Tab5 Wireless Control Skill

Use this skill for the wireless control lane between the M5Stack Tab5 dashboard and the K1 Lightwave device.

## Canon

- K1 is AP-only. Do not enable K1 STA mode or reopen that architecture decision.
- The Tab5 joins the K1 AP and acts as the wireless control client.
- K1 LED rendering and WiFi/WS work must stay separated. Do not place WiFi, JSON parsing, serial blocking, heap allocation, or network callbacks in a render path.
- UI labels may say `BRIGHTNESS`, `COLOUR`, and `SPEED`, but the K1 protocol fields are currently `photons`, `chroma`, and `mood`. Preserve the protocol contract while keeping user-facing wording correct.
- Treat K1 `control.set` and Tab5 `k1.control.result` as separate evidence surfaces. A Tab5 send log alone is not proof that K1 applied the control.

## Verify First

Before changing code, inspect current local source truth:

```sh
sed -n '1,240p' AGENTS.md
sed -n '1,220p' .claude/CLAUDE.md
sed -n '1,220p' docs/spec-index.md
sed -n '1,260p' docs/protocol/k1-ws-contract.yaml
sed -n '1,260p' sb-tab5-wireless-controller/src/network/K1WebSocketClient.cpp
sed -n '1,260p' sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp
rg -n "K1WS|control.set|k1.control.result|AP_ONLY|WiFi|WebSocket" SENSORY_BRIDGE_FIRMWARE sb-tab5-wireless-controller docs/protocol
```

If `rg` is unavailable or shadowed, use `find` plus `grep`.

## Control Contract

Expected control routing:

| User-facing control | K1 protocol control |
|---|---|
| Primary brightness | `primary.photons` |
| Primary colour | `primary.chroma` |
| Primary speed | `primary.mood` |
| Primary palette | `primary.palette` |
| Primary mode | `primary.mode` |
| Secondary brightness | `secondary.photons` |
| Secondary colour | `secondary.chroma` |
| Secondary speed | `secondary.mood` |
| Secondary palette | `secondary.palette` |
| Secondary mode | `secondary.mode` |
| Smart scene | `scene.smart` |

Do not invent effect names or expose inactive K1 effects. Verify active mode IDs from local K1 and Tab5 source before changing visible UI.

## Implementation Rules

1. Keep connection ownership narrow: Tab5 network client handles AP join, WS connect/reconnect, send, and receive; UI consumes a small client API.
2. Keep messages bounded and predictable. Avoid heap-heavy formatting in hot UI loops.
3. On send failure, report it on Tab5 serial and surface an error cue/state; do not silently drop user input.
4. On `k1.control.result`, update Tab5 local state only from the K1 result payload when available.
5. Preserve British spelling in logs, UI strings, and comments.

## Validation

Minimum validation for wireless changes:

```sh
python3 tests/test_sb_tab5_wireless_controller_static.py
pio run -e tab5 -d sb-tab5-wireless-controller
```

For live proof, also run the Tab5/K1 harness and require all three surfaces:

1. Tab5 command ACK: `OK UI_*`
2. K1 serial: `[K1WS] ... control.set ... control=<expected>`
3. Tab5 serial: `[UI] K1 result ok=1 control=<expected>`

Build success without live K1 result proof is compile-only, not completion.
