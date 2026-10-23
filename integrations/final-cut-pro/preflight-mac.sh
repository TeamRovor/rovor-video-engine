#!/bin/sh
# ROVOR Final Cut Pro MCP read-only host preflight.
# No installation, network calls, project modification or permission prompts.
set -eu
printf 'ROVOR FCP PILOT PREFLIGHT (read-only)\n'
printf 'Date (UTC): '
date -u '+%Y-%m-%dT%H:%M:%SZ'
printf 'Operating system: '
uname -s
printf 'Architecture: '
uname -m
if [ "$(uname -s)" != "Darwin" ]; then
  printf 'Mac-specific application checks skipped (not macOS).\n'
else
  printf 'macOS version: '
  sw_vers -productVersion
  app="/Applications/Final Cut Pro.app"
  if [ -d "$app" ] && [ ! -L "$app" ]; then
    printf 'Final Cut at /Applications: present\n'
    printf 'FCP version: '
    /usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app/Contents/Info.plist" 2>/dev/null || printf 'unreadable\n'
  else
    printf 'Final Cut at /Applications: not found (other install locations unverified)\n'
  fi
fi
for command_name in git uvx codex ffmpeg ffprobe; do
  if command -v "$command_name" >/dev/null 2>&1; then
    printf '%s: available\n' "$command_name"
  else
    printf '%s: missing or not in PATH\n' "$command_name"
  fi
done
printf 'FCPXML MCP: not tested by this preflight\n'
printf 'macOS Automation permission: not checked or changed\n'
printf 'Remote ChatGPT-to-Mac connection: not implied\n'
printf 'Next: read integrations/final-cut-pro/README.md; approve restricted disposable sandbox before enabling.\n'
