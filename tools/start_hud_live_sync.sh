#!/bin/sh
# Starts a read-only private view of the existing HUD. No worker settings change.
set -eu
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
export PATH
command -v node >/dev/null || { echo 'Node is unavailable on this Mac.'; exit 1; }
if ! command -v cloudflared >/dev/null 2>&1; then
  [ "$(uname -s)" = Darwin ] || { echo 'Install cloudflared or run node tools/hud_omniroute_bridge.mjs for local-only access.'; exit 1; }
  case "$(uname -m)" in
    x86_64) CF_ARCH=amd64; CF_SHA=81b7b85f2376815c4f59b1aa323887b62e16ce8b67555c2e1577dc23f2a82000 ;;
    arm64) CF_ARCH=arm64; CF_SHA=1165d14b6f6360a3b8c283d7d1100024d6ec7cd9bc9e32519e96150645f3ec55 ;;
    *) echo 'Unsupported Mac architecture.'; exit 1 ;;
  esac
  CF_TMP=$(mktemp -d "${TMPDIR:-/tmp}/rovor-hud-tunnel.XXXXXX")
  chmod 700 "$CF_TMP"
  trap 'rm -rf "$CF_TMP"' EXIT HUP INT TERM
  curl -fLsS --proto '=https' --tlsv1.2 "https://github.com/cloudflare/cloudflared/releases/download/2026.10.3/cloudflared-darwin-$CF_ARCH.tgz" -o "$CF_TMP/tunnel.tgz"
  CF_ACTUAL=$(shasum -a 256 "$CF_TMP/tunnel.tgz" | cut -d ' ' -f 1)
  [ "$CF_ACTUAL" = "$CF_SHA" ] || { echo 'Tunnel download checksum mismatch. Nothing started.'; exit 1; }
  tar -xzf "$CF_TMP/tunnel.tgz" -C "$CF_TMP" cloudflared
  chmod 700 "$CF_TMP/cloudflared"
  PATH="$CF_TMP:$PATH"; export PATH
  node "$TASK_ROOT/tools/hud_omniroute_bridge.mjs" --remote
else
  exec node "$TASK_ROOT/tools/hud_omniroute_bridge.mjs" --remote
fi
