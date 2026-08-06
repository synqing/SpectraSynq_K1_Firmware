#!/usr/bin/env bash
# Consolidate project-local .claude/skills, .cursor/skills, .codex/skills, and .claude/agents.
# Usage: setup-project-skills.sh <profile> <project_dir>
# Profiles: k1-firmware | premium-site | embedded-knob

set -euo pipefail

PROFILE="${1:?profile required: k1-firmware|premium-site|embedded-knob}"
PROJECT="${2:?project_dir required}"
GLOBAL="${HOME}/.claude/skills"
K1="/Users/spectrasynq/SpectraSynq_K1_Firmware"
SB="/Users/spectrasynq/SensoryBridge-main 9"
PREMIUM="/Users/spectrasynq/Workspace_Management/Software/premium-site-harness"
# Required in every SpectraSynq project folder (K1 artefacts + comp discipline)
DESIGN_CANON_SRC="$PREMIUM/.codex/skills"
DESIGN_CANON_SKILLS=(nyt-data-viz muller-brockmann-grid vignelli-canon)

copy_design_canon_skills() {
  local src="${1:-$DESIGN_CANON_SRC}"
  for s in "${DESIGN_CANON_SKILLS[@]}"; do
    copy_skill "$s" "$src"
  done
}

copy_skill() {
  local name="$1" src="$2"
  [ -d "$src/$name" ] || { echo "  SKIP missing: $name"; return 0; }
  for base in "$PROJECT/.claude/skills" "$PROJECT/.cursor/skills" "$PROJECT/.codex/skills"; do
    mkdir -p "$base"
    rm -rf "$base/$name"
    cp -R "$src/$name" "$base/"
  done
  echo "  OK $name"
}

copy_all_from_dir() {
  local src="$1"
  mkdir -p "$PROJECT/.claude/skills" "$PROJECT/.cursor/skills" "$PROJECT/.codex/skills"
  rm -rf "$PROJECT/.claude/skills"/* "$PROJECT/.cursor/skills"/* "$PROJECT/.codex/skills"/*
  for d in "$src"/*; do
    [ -d "$d" ] || continue
    [ -f "$d/SKILL.md" ] || continue
    copy_skill "$(basename "$d")" "$src"
  done
}

copy_thinking_suite() {
  local src="$1"
  for d in "$src"/thinking-*; do
    [ -d "$d" ] || continue
    copy_skill "$(basename "$d")" "$src"
  done
}

copy_agents() {
  mkdir -p "$PROJECT/.claude/agents"
  for f in "$@"; do
    if [ -f "$f" ]; then
      cp "$f" "$PROJECT/.claude/agents/"
      echo "  agent $(basename "$f")"
    fi
  done
}

echo "== setup $PROFILE -> $PROJECT =="

case "$PROFILE" in
  k1-firmware)
    # Ensure K1 canonical tree has full thinking-skills + claude-mem skills in all agent dirs.
    if [ "$PROJECT" = "$K1" ]; then
      bash "$K1/scripts/install-thinking-skills.sh" "$K1"
      bash "$K1/scripts/install-claude-mem-skills.sh" "$K1"
    fi
    rsync -a --delete "$K1/.claude/skills/" "$PROJECT/.claude/skills/"
    rsync -a --delete "$K1/.cursor/skills/" "$PROJECT/.cursor/skills/"
    if [ -d "$K1/.codex/skills" ]; then
      rsync -a --delete "$K1/.codex/skills/" "$PROJECT/.codex/skills/"
    else
      rsync -a --delete "$K1/.claude/skills/" "$PROJECT/.codex/skills/"
    fi
    rsync -a --delete "$K1/.claude/agents/" "$PROJECT/.claude/agents/"
    copy_design_canon_skills "$DESIGN_CANON_SRC"
    # Harness-first autonomous build doctrine (canonical: ~/.claude/skills)
    copy_skill autonomous-agentic-build "$GLOBAL"
    ;;
  premium-site)
    PREMIUM_SRC="$PROJECT/.codex/skills"
    [ -d "$PREMIUM_SRC" ] || PREMIUM_SRC="$K1/.claude/skills"
    # Remember git-tracked cursor-only skills before wipe (e.g. higgsfield-*)
    CURSOR_ONLY=()
    if [ -d "$PROJECT/.git" ]; then
      while IFS= read -r f; do
        skill_dir=$(echo "$f" | cut -d/ -f3)
        [ -n "$skill_dir" ] || continue
        [ -d "$PREMIUM_SRC/$skill_dir" ] && continue
        CURSOR_ONLY+=("$skill_dir")
      done < <(git -C "$PROJECT" ls-files '.cursor/skills/*/SKILL.md' 2>/dev/null || true)
    fi
    copy_all_from_dir "$PREMIUM_SRC"
    for s in discover-specialists memory-authority-gate parallel-agent-sandboxing cross-stack-debugging; do
      copy_skill "$s" "$GLOBAL"
    done
    copy_skill ssa-management "$K1/.claude/skills"
    if [ -d "$PROJECT/.git" ] && [ "${#CURSOR_ONLY[@]}" -gt 0 ]; then
      for skill_dir in "${CURSOR_ONLY[@]}"; do
        git -C "$PROJECT" checkout HEAD -- ".cursor/skills/$skill_dir" 2>/dev/null || true
        if [ -d "$PROJECT/.cursor/skills/$skill_dir" ]; then
          rm -rf "$PROJECT/.claude/skills/$skill_dir" "$PROJECT/.codex/skills/$skill_dir"
          cp -R "$PROJECT/.cursor/skills/$skill_dir" "$PROJECT/.claude/skills/"
          cp -R "$PROJECT/.cursor/skills/$skill_dir" "$PROJECT/.codex/skills/"
          echo "  preserved $skill_dir (cursor-only)"
        fi
      done
    fi
    copy_agents \
      "$GLOBAL/../agents/deep-technical-analyst.md" \
      "$GLOBAL/../agents/error-detective.md" \
      "$GLOBAL/../agents/test-automator.md"
    copy_design_canon_skills "$DESIGN_CANON_SRC"
    ;;
  embedded-knob)
    mkdir -p "$PROJECT/.claude/skills" "$PROJECT/.cursor/skills" "$PROJECT/.codex/skills"
    rm -rf "$PROJECT/.claude/skills"/* "$PROJECT/.cursor/skills"/* "$PROJECT/.codex/skills"/*
    EMBEDDED=(
      ssa-management discover-specialists
      hardware-bringup firmware-crash-analysis firmware-profiling
      peripheral-bus-debugging register-map-verification signal-processing-verification
      esp32 esp-idf platformio arduino cpp ziglang embedded-graphics-patterns
      memory-authority-gate parallel-agent-sandboxing
      k1-tab5-lvgl-dashboard k1-tab5-ux-feedback k1-tab5-wireless-control
      spectrasynq-build-system
    )
    for s in "${EMBEDDED[@]}"; do
      if [ -d "$K1/.claude/skills/$s" ]; then
        copy_skill "$s" "$K1/.claude/skills"
      elif [ -d "$SB/.claude/skills/$s" ]; then
        copy_skill "$s" "$SB/.claude/skills"
      else
        copy_skill "$s" "$GLOBAL"
      fi
    done
    copy_thinking_suite "$K1/.claude/skills"
    copy_design_canon_skills "$DESIGN_CANON_SRC"
    copy_agents \
      "$GLOBAL/../agents/engineering-embedded-firmware-engineer.md" \
      "$GLOBAL/../agents/error-detective.md" \
      "$GLOBAL/../agents/deep-technical-analyst.md" \
      "$SB/.claude/agents/debugger.md" \
      "$SB/.claude/agents/performance-engineer.md"
    ;;
  *)
    echo "Unknown profile: $PROFILE" >&2
    exit 1
    ;;
esac

echo "  skills: $(find "$PROJECT/.claude/skills" -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')"
echo "  agents: $(ls -1 "$PROJECT/.claude/agents" 2>/dev/null | wc -l | tr -d ' ')"
