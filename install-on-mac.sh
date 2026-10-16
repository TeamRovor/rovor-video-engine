#!/bin/bash
# Install locally and register an additional Codex MCP server.
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
ENGINE="$ROOT/evan-engine"
PYTHON="$(command -v python3 || true)"
if [ -z "$PYTHON" ]; then
  echo "ERROR: python3 was not found. Install Python 3 and try again." >&2
  exit 1
fi
chmod +x "$ENGINE/Make Evan Video.command"
cd "$ENGINE"
echo '1/3 — Testing Evan Engine V3...'
"$PYTHON" -m unittest -q test_evan_engine.py

echo '2/3 — Checking original local animation tools...'
if "$PYTHON" launch_evan.py --check; then
  TOOLS_READY=1
else
  TOOLS_READY=0
  echo 'The Mac-specific tools from your old Codex workspace were not all found.'
  echo 'Keep that workspace. Update evan-engine/local_tools.json to the real tool paths.'
fi

echo '3/3 — Registering separate Codex MCP server...'
if command -v codex >/dev/null 2>&1; then
  if codex mcp get rovor-evan-v3 >/dev/null 2>&1; then
    echo 'MCP entry rovor-evan-v3 already exists. Check its path with: codex mcp get rovor-evan-v3'
  else
    codex mcp add rovor-evan-v3 -- "$PYTHON" "$ENGINE/evan_mcp.py"
  fi
  codex mcp get rovor-evan-v3
else
  echo 'Codex CLI not found in PATH. MCP registration was skipped.'
  echo "After installing Codex CLI, run: codex mcp add rovor-evan-v3 -- '$PYTHON' '$ENGINE/evan_mcp.py'"
fi

echo ''
echo "ENGINE INSTALLED: $ROOT"
echo "TO CREATE VIDEO: open '$ENGINE/Make Evan Video.command'"
if [ "$TOOLS_READY" -eq 1 ]; then
  echo 'All original tool paths were found. Ready for an MP3 test render.'
else
  echo 'Engine and MCP adapter are installed, but missing local tools must be restored before rendering.'
fi
echo 'NOTE: This is a separate Evan animation MCP. It does not control Moho or change your existing Moho MCP.'
