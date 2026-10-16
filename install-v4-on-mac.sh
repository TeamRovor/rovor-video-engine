#!/bin/bash
# Install the V4 patch in an independent Git worktree. Do not mutate V3.
set -euo pipefail
ROOT="$HOME/Documents/Rovor/Evan-Engine-V3-Reference-Art"
DEST="$HOME/Documents/Rovor/Evan-Engine-V4-Development"
ZIP="${1:-$HOME/Downloads/Evan-Engine-V4-Patch.zip}"
BRANCH="feature/evan-v4"
if [ ! -f "$ZIP" ]; then echo "ERROR: V4 patch ZIP not found: $ZIP" >&2; exit 1; fi
if [ ! -d "$ROOT/.git" ] && [ ! -f "$ROOT/.git" ]; then echo "ERROR: V3 Git repository missing at $ROOT" >&2; exit 1; fi
if [ -n "$(git -C "$ROOT" status --porcelain)" ]; then
  echo 'ERROR: Existing V3 worktree has uncommitted changes. Save them before installing V4.' >&2; exit 1
fi
if [ -e "$DEST" ] || git -C "$ROOT" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "ERROR: V4 worktree or branch already exists. Nothing was overwritten." >&2; exit 1
fi
printf '\n1/5 Creating independent V4 branch and worktree...\n'
git -C "$ROOT" worktree add -b "$BRANCH" "$DEST" main
printf '\n2/5 Applying V4 changes...\n'
ditto -x -k "$ZIP" "$DEST"
if [ -f "$ROOT/evan-engine/local_tools.json" ]; then
  cp "$ROOT/evan-engine/local_tools.json" "$DEST/evan-engine/local_tools.json"
fi
if [ -f "$ROOT/evan-character/evan-original-extracted.mp3" ]; then
  cp "$ROOT/evan-character/evan-original-extracted.mp3" "$DEST/evan-character/evan-original-extracted.mp3"
fi
printf '\n3/5 Running V4 tests...\n'
(cd "$DEST/evan-engine" && python3 -m unittest -q test_evan_engine.py)
printf '\n4/5 Saving branch commit...\n'
git -C "$DEST" add evan-engine evan-character/brand evan-character/v4-assets V4-RELEASE-NOTES.md install-v4-on-mac.sh
git -C "$DEST" commit -m "Evan Engine V4: calibrated speech, official Rovor identity, better scenes"
if command -v codex >/dev/null 2>&1; then
  if ! codex mcp get rovor-evan-v4 >/dev/null 2>&1; then
    codex mcp add rovor-evan-v4 -- "$(command -v python3)" "$DEST/evan-engine/evan_mcp.py"
  fi
fi
printf '\n5/5 Pushing isolated V4 branch to GitHub...\n'
if git -C "$DEST" push -u origin "$BRANCH"; then
  echo 'GitHub branch uploaded. V3 main stays unchanged.'
else
  echo 'GitHub push failed; V4 is saved in its independent local branch.' >&2
  exit 1
fi
echo "V4 is ready: $DEST"
echo "Run locally: cd '$DEST/evan-engine' && python3 launch_evan.py"
