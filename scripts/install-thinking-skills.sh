#!/usr/bin/env bash
# Install all thinking-skills marketplace skills into project-local agent dirs.
# Targets: .claude/skills (Claude Code), .cursor/skills (Cursor), .codex/skills (Codex).
#
# Usage: bash scripts/install-thinking-skills.sh [project_dir]
# Override source: THINKING_SKILLS_SRC=/path/to/skills bash scripts/install-thinking-skills.sh

set -euo pipefail

PROJECT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
MARKETPLACE="${THINKING_SKILLS_SRC:-$HOME/.claude/plugins/cache/thinking-skills-marketplace/thinking-skills/1.0.0/skills}"

if [ ! -d "$MARKETPLACE" ]; then
  echo "ERROR: thinking-skills marketplace not found at $MARKETPLACE" >&2
  echo "Install the thinking-skills marketplace plugin, or set THINKING_SKILLS_SRC." >&2
  exit 1
fi

copy_skill() {
  local name="$1"
  local src="$MARKETPLACE/$name"
  [ -d "$src" ] || { echo "  SKIP missing: $name"; return 0; }
  for base in "$PROJECT/.claude/skills" "$PROJECT/.cursor/skills" "$PROJECT/.codex/skills"; do
    mkdir -p "$base"
    rm -rf "$base/$name"
    cp -R "$src" "$base/"
  done
  echo "  OK $name"
}

echo "== install thinking-skills -> $PROJECT =="
echo "   source: $MARKETPLACE"
mkdir -p "$PROJECT/.claude/skills" "$PROJECT/.cursor/skills" "$PROJECT/.codex/skills"

installed=0
for d in "$MARKETPLACE"/thinking-*; do
  [ -d "$d" ] || continue
  copy_skill "$(basename "$d")"
  installed=$((installed + 1))
done

echo "  thinking-skills installed: $installed"
echo "  .claude/skills: $(find "$PROJECT/.claude/skills" -maxdepth 1 -type d -name 'thinking-*' | wc -l | tr -d ' ')"
echo "  .cursor/skills: $(find "$PROJECT/.cursor/skills" -maxdepth 1 -type d -name 'thinking-*' | wc -l | tr -d ' ')"
echo "  .codex/skills:  $(find "$PROJECT/.codex/skills" -maxdepth 1 -type d -name 'thinking-*' | wc -l | tr -d ' ')"
