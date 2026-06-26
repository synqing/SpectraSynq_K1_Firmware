---
name: discover-specialists
description: Discover and list all available custom specialist agents. Use this skill when you need to find the right specialist agent for a task, or when reminded to check agent inventory before complex tasks.
---

# Discover Specialists Skill

This skill helps you discover and select the right specialist agent for your current task.

## When to Use This Skill

- Before starting any complex task involving specialized domains
- When unsure which specialist agent to use
- When reminded by session context to check agent inventory
- After receiving a task that mentions colors, effects, firmware, networking, displays, etc.

## Agent Discovery Protocol

### Step 1: Scan Agent Directories

Specialist agents are stored in:
1. **Global agents**: `~/.claude/agents/*.md`
2. **Project agents**: `./.claude/agents/*.md` (relative to project root)

### Step 2: Extract Agent Information

Each agent file has YAML frontmatter with:
```yaml
---
name: agent-name
description: What this agent specializes in
tools: Available tools
model: Preferred model (optional)
---
```

### Step 3: Match Domain to Specialists

Use this decision matrix:

| Domain | Primary Specialist | Secondary |
|--------|-------------------|-----------|
| LED effects, animations | visual-fx-architect | palette-specialist |
| Color palettes, RGB/HSV | fastled-color-specialist | palette-specialist |
| ESP32 firmware, FreeRTOS | embedded-system-engineer | - |
| Network, REST API, WebSocket | network-api-engineer | - |
| M5GFX displays, graphics | m5gfx-dashboard-architect | - |
| Serial commands, CLI | serial-interface-engineer | - |
| Audio DSP, beat tracking | audio specialists | - |
| C/C++ optimization | cpp-pro, c-pro | - |
| Python code | python-pro | - |
| Code review | code-reviewer | - |
| Debugging | debugger, systematic-debugger | error-detective |
| Architecture | architect-review | deep-technical-analyst |
| Documentation | docs-architect, api-documenter | - |
| Deployment | deployment-engineer | devops-troubleshooter |

### Step 4: Invoke Selected Agent

Use the Task tool to invoke a specialist:

```
Task tool with:
  subagent_type: "<agent-name>"
  prompt: "<detailed task description>"
  description: "<3-5 word summary>"
```

## Quick Reference: Common Project Specialists

### Lightwave-Ledstrip Project

| Agent | Expertise |
|-------|-----------|
| **visual-fx-architect** | LED effects, Zone Composer, transitions, CENTER ORIGIN patterns |
| **palette-specialist** | Color science, WS2812, perception, LGP considerations |
| **embedded-system-engineer** | ESP32-S3/P4, FreeRTOS, memory management, FastLED |
| **network-api-engineer** | REST API v1, WebSocket, WiFiManager, ESP-NOW |
| **m5gfx-dashboard-architect** | M5GFX displays, sprites, performance optimization |
| **serial-interface-engineer** | SerialMenu, telemetry, zone commands |

## Red Flags: Missing a Specialist

If you find yourself thinking:
- "I'll just write a quick color function" → Use fastled-color-specialist
- "This effect is straightforward" → Use visual-fx-architect
- "I can handle the FreeRTOS part" → Use embedded-system-engineer
- "The API endpoint is simple" → Use network-api-engineer
- "I'll optimize the display code myself" → Use m5gfx-dashboard-architect

## Example: Selecting a Specialist

**Task**: "Add a new audio-reactive effect that pulses with the beat"

**Analysis**:
1. **Primary domain**: LED effects → visual-fx-architect
2. **Secondary domain**: Color/palettes → palette-specialist
3. **Hardware context**: ESP32 firmware → embedded-system-engineer (for audio hooks)

**Action**: Invoke visual-fx-architect first, then consult palette-specialist for colors.

## Integration with SessionStart Hook

If the `specialist-agents-discovery` plugin is installed, agent inventory is automatically injected at session start. This skill is for:
- Manual discovery when hook context has scrolled away
- Detailed decision-making about which specialist to use
- Refreshing agent awareness during long sessions

## Maintaining Agent Inventory

To add a new specialist agent:
1. Create `<agent-name>.md` in `.claude/agents/` (project) or `~/.claude/agents/` (global)
2. Include YAML frontmatter with name, description, tools
3. Document the agent's expertise, decision trees, and guardrails
4. The SessionStart hook will automatically discover it
