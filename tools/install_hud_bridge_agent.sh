#!/bin/bash
# Installs a LaunchAgent that keeps the local HUD bridge (and chat) running, loopback only.
# Usage: tools/install_hud_bridge_agent.sh [install|open|uninstall]
set -euo pipefail
LABEL=com.rovor.hud-bridge
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NODE="$(command -v node)"
case "${1:-install}" in
  install)
    mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
    cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$LABEL</string>
<key>ProgramArguments</key><array><string>$NODE</string><string>$ROOT/tools/hud_omniroute_bridge.mjs</string><string>--persistent</string></array>
<key>WorkingDirectory</key><string>$ROOT</string>
<key>EnvironmentVariables</key><dict><key>PATH</key><string>$(dirname "$NODE"):/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>ThrottleInterval</key><integer>30</integer>
<key>StandardOutPath</key><string>$HOME/Library/Logs/rovor-hud-bridge.log</string>
<key>StandardErrorPath</key><string>$HOME/Library/Logs/rovor-hud-bridge.log</string>
</dict></plist>
PL
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST"
    echo "Installed $LABEL. Run: $0 open" ;;
  open)
    CODE="$(security find-generic-password -s rovordigital.hud.bridge.pair -w)"
    open "http://127.0.0.1:20129/#pair=$CODE" ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"; echo "Removed $LABEL" ;;
esac
