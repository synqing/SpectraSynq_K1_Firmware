#!/usr/bin/env bash
# Install claude-mem memory + semantic-search skills into project-local agent dirs.
# Targets: .claude/skills (Claude Code), .cursor/skills (Cursor), .codex/skills (Codex).
#
# Usage: bash scripts/install-claude-mem-skills.sh [project_dir]
# Override source: CLAUDE_MEM_SKILLS_SRC=/path/to/skills bash scripts/install-claude-mem-skills.sh
#
# Installs:
#   Plugin skills: mem-search, knowledge-agent, timeline-report, how-it-works,
#                  smart-explore, learn-codebase, weekly-digests
#   Project skills (mirrored to all three dirs): claude-mem-router, spec-recall, memory-authority-gate

set -euo pipefail

PROJECT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"

# Prefer marketplace (stable path), fall back to versioned cache.
MARKETPLACE_DEFAULT="$HOME/.claude/plugins/marketplaces/thedotmack/plugin/skills"
CACHE_DEFAULT="$HOME/.claude/plugins/cache/thedotmack/claude-mem/13.6.0/skills"
if [ -n "${CLAUDE_MEM_SKILLS_SRC:-}" ]; then
  MARKETPLACE="$CLAUDE_MEM_SKILLS_SRC"
elif [ -d "$MARKETPLACE_DEFAULT" ]; then
  MARKETPLACE="$MARKETPLACE_DEFAULT"
elif [ -d "$CACHE_DEFAULT" ]; then
  MARKETPLACE="$CACHE_DEFAULT"
else
  echo "ERROR: claude-mem skills not found." >&2
  echo "Tried: $MARKETPLACE_DEFAULT" >&2
  echo "       $CACHE_DEFAULT" >&2
  echo "Install the claude-mem plugin, or set CLAUDE_MEM_SKILLS_SRC." >&2
  exit 1
fi

# Memory + semantic-search skills from the claude-mem plugin.
PLUGIN_SKILLS=(
  mem-search
  knowledge-agent
  timeline-report
  how-it-works
  smart-explore
  learn-codebase
  weekly-digests
)

# Repo-local companions that must exist in all three tool skill trees.
PROJECT_SKILLS=(
  claude-mem-router
  spec-recall
  memory-authority-gate
)

copy_skill_from() {
  local name="$1"
  local src="$2/$name"
  [ -d "$src" ] || { echo "  SKIP missing: $name (src=$2)"; return 0; }
  for base in "$PROJECT/.claude/skills" "$PROJECT/.cursor/skills" "$PROJECT/.codex/skills"; do
    mkdir -p "$base"
    rm -rf "$base/$name"
    cp -R "$src" "$base/"
  done
  echo "  OK $name"
}

echo "== install claude-mem skills -> $PROJECT =="
echo "   plugin source: $MARKETPLACE"
mkdir -p "$PROJECT/.claude/skills" "$PROJECT/.cursor/skills" "$PROJECT/.codex/skills"

installed=0
for name in "${PLUGIN_SKILLS[@]}"; do
  copy_skill_from "$name" "$MARKETPLACE"
  installed=$((installed + 1))
done

# Prefer existing project copies of companions; fall back to any one tool dir.
for name in "${PROJECT_SKILLS[@]}"; do
  if [ -d "$PROJECT/.claude/skills/$name" ]; then
    # Re-mirror from .claude canonical copy into cursor + codex.
    for base in "$PROJECT/.cursor/skills" "$PROJECT/.codex/skills"; do
      mkdir -p "$base"
      rm -rf "$base/$name"
      cp -R "$PROJECT/.claude/skills/$name" "$base/"
    done
    echo "  OK $name (mirrored from .claude/skills)"
  elif [ -d "$PROJECT/.cursor/skills/$name" ]; then
    for base in "$PROJECT/.claude/skills" "$PROJECT/.codex/skills"; do
      mkdir -p "$base"
      rm -rf "$base/$name"
      cp -R "$PROJECT/.cursor/skills/$name" "$base/"
    done
    echo "  OK $name (mirrored from .cursor/skills)"
  else
    echo "  SKIP missing project skill: $name"
  fi
  installed=$((installed + 1))
done

count_named() {
  local base="$1"
  local n=0
  local s
  for s in "${PLUGIN_SKILLS[@]}" "${PROJECT_SKILLS[@]}"; do
    [ -f "$base/$s/SKILL.md" ] && n=$((n + 1))
  done
  echo "$n"
}

# Global availability for /claude-mem-router (Claude Code + Cursor + Codex).
# Canonical body stays in the project; home skill dirs get symlinks.
link_router_global() {
  local src="$PROJECT/.claude/skills/claude-mem-router"
  [ -f "$src/SKILL.md" ] || {
    echo "  SKIP global claude-mem-router (project copy missing)"
    return 0
  }
  local dest target
  for dest in \
    "$HOME/.claude/skills" \
    "$HOME/.cursor/skills" \
    "$HOME/.codex/skills" \
    "$HOME/.agents/skills"
  do
    mkdir -p "$dest"
    target="$dest/claude-mem-router"
    if [ -L "$target" ] || [ ! -e "$target" ]; then
      rm -f "$target"
      ln -s "$src" "$target"
      echo "  GLOBAL $target -> $src"
    elif [ -d "$target" ]; then
      rm -rf "$target"
      ln -s "$src" "$target"
      echo "  GLOBAL (replaced dir) $target -> $src"
    else
      echo "  SKIP global $target (unexpected non-dir entry)"
    fi
  done
}

echo "  skills processed: $installed"
echo "  .claude/skills present: $(count_named "$PROJECT/.claude/skills")/$((${#PLUGIN_SKILLS[@]} + ${#PROJECT_SKILLS[@]}))"
echo "  .cursor/skills present: $(count_named "$PROJECT/.cursor/skills")/$((${#PLUGIN_SKILLS[@]} + ${#PROJECT_SKILLS[@]}))"
echo "  .codex/skills present:  $(count_named "$PROJECT/.codex/skills")/$((${#PLUGIN_SKILLS[@]} + ${#PROJECT_SKILLS[@]}))"
link_router_global
echo "  invoke: /claude-mem-router  (scenario → one skill; project + GLOBAL)"
echo "          /mem-search /knowledge-agent /timeline-report /how-it-works /spec-recall"
echo "          /smart-explore /learn-codebase /weekly-digests /memory-authority-gate"
