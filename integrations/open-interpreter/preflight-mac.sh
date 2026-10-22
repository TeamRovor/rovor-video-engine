#!/usr/bin/env bash
# ROVOR Open Interpreter pilot: read-only local inspection, no network or installs.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
printf '\nROVOR Open Interpreter preflight\nProject: %s\n' "$root"
for path in AGENTS.md WORK.md .openinterpreter/config.toml \
            .agents/skills/ponytail/SKILL.md \
            .agents/skills/context-engineering/SKILL.md \
            .agents/skills/debugging-and-error-recovery/SKILL.md \
            integrations/open-interpreter/OMNIROUTE.md \
            integrations/open-interpreter/GRAPHIFY.md; do
  if [[ -f "$path" ]]; then
    printf 'OK   %s\n' "$path"
  else
    printf 'MISS %s\n' "$path"
  fi
done

printf '\nGit branch and status (read only):\n'
git branch --show-current || true
git status --short || true

printf '\nLocal executable availability (not proof of tool connectivity):\n'
for program in git gh interpreter python3 node npm uv graphify omniroute ffmpeg blender; do
  if command -v "$program" >/dev/null 2>&1; then
    printf 'FOUND %-14s %s\n' "$program" "$(command -v "$program")"
  else
    printf 'MISS  %s\n' "$program"
  fi
done

printf '\nConfiguration TOML parsing:\n'
if python3 -c 'import tomllib; tomllib.load(open(".openinterpreter/config.toml","rb")); print("OK  TOML syntax")' 2>/dev/null; then
  :
else
  printf 'WARN Could not parse project TOML (Python 3.11+ required for this check).\n'
fi

printf '\nNo files changed, API requests sent or programs installed by this preflight.\n'
printf 'Next: start interpreter from this directory and inspect /debug-config and /agent.\n\n'
