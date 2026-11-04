#!/bin/bash
# Installs/diagnoses only ROVOR's existing read-only outbound telemetry service.
# Does not call an AI model, open an inbound port, or modify worker approvals.
set -euo pipefail
LABEL="com.rovor.hud-reporting"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
MODE="status"
ORIGIN="https://rovor-hud-telemetry.rovordigital.workers.dev"
if [[ "$#" -ge 1 ]]; then MODE="$1"; fi
if [[ "$#" -ge 2 ]]; then ORIGIN="$2"; fi

if [[ "$(uname -s)" != Darwin ]]; then
  echo 'The persistent telemetry LaunchAgent is macOS-only.' >&2
  exit 2
fi
if [[ "$MODE" != "status" && "$MODE" != "install" && "$MODE" != "restart" ]]; then
  echo 'Usage: bash tools/manage_hud_telemetry_agent.sh [status|install|restart] [private HUD HTTPS origin]' >&2
  exit 2
fi
if ! command -v node >/dev/null; then
  echo 'Node.js is required; no changes made.' >&2
  exit 2
fi
NODE="$(command -v node)"
USER_ID="$(id -u)"
SERVICE="gui/$USER_ID/$LABEL"

echo 'ROVOR telemetry (read-only, outbound)'
if [[ -f "$PLIST" ]]; then echo 'Plist present: yes'; else echo 'Plist present: no'; fi
if launchctl print "$SERVICE" >/dev/null 2>&1; then
  echo 'LaunchAgent registered: yes'
else
  echo 'LaunchAgent registered: no'
fi
if [[ "$MODE" == "status" ]]; then
  if [[ ! -f "$PLIST" ]]; then
    echo 'Not installed. Run: bash tools/manage_hud_telemetry_agent.sh install'
  fi
  echo 'The command does not prove a fresh report; check your private HUD last-report timestamp.'
  exit 0
fi

# Never embed passwords/keys in LaunchAgent files or stdout.
if ! /usr/bin/security find-generic-password -s rovordigital.hud.writer -w >/dev/null 2>&1; then
  echo 'HUD writer Keychain entry missing. No changes made.' >&2
  exit 2
fi
"$NODE" --check "$ROOT/tools/hud_telemetry_publisher.mjs"
"$NODE" -e '
const raw=process.argv[1], u=new URL(raw);
if(u.protocol!=="https:"||u.origin!==raw.replace(/\/$/,"")||
   u.username||u.password||u.search||u.hash||
   (u.pathname!=="/"&&u.pathname!==""))throw Error("Invalid private HUD origin");
' "$ORIGIN"
ORIGIN="$(printf '%s' "$ORIGIN" | sed 's,/$,,')"

if [[ "$MODE" == "restart" ]]; then
  if [[ ! -f "$PLIST" ]]; then
    echo 'LaunchAgent missing. Use install instead of restart.' >&2
    exit 2
  fi
  if ! launchctl print "$SERVICE" >/dev/null 2>&1; then
    launchctl bootstrap "gui/$USER_ID" "$PLIST"
  fi
  launchctl kickstart -k "$SERVICE"
  echo 'Existing telemetry LaunchAgent restart requested (not proof of successful publishing).'
  exit 0
fi

if [[ -e "$PLIST" ]]; then
  echo 'Existing telemetry plist found; refusing to overwrite it. Use status/restart to preserve configuration.' >&2
  exit 2
fi
PYTHON="$(command -v python3 || true)"
if [[ -z "$PYTHON" ]]; then
  echo 'Python 3 required for safe LaunchAgent generation. No changes made.' >&2
  exit 2
fi
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
"$PYTHON" - "$PLIST" "$ROOT" "$NODE" "$ORIGIN" <<'PY'
import os, plistlib, sys
target, root, node, origin = sys.argv[1:]
data = {
  'Label': 'com.rovor.hud-reporting',
  'ProgramArguments': [node, os.path.join(root, 'tools/hud_telemetry_publisher.mjs')],
  'WorkingDirectory': root,
  'EnvironmentVariables': {
    'ROVOR_HUD_ORIGIN': origin,
    'PATH': ':'.join([os.path.join(os.path.expanduser('~'), '.local/bin'),
                      os.path.dirname(node), '/usr/local/bin', '/opt/homebrew/bin',
                      '/usr/bin', '/bin', '/usr/sbin', '/sbin'])
  },
  'RunAtLoad': True,
  'KeepAlive': True,
  'ThrottleInterval': 30,
  'StandardOutPath': os.path.expanduser('~/Library/Logs/rovor-hud-reporting.log'),
  'StandardErrorPath': os.path.expanduser('~/Library/Logs/rovor-hud-reporting-error.log'),
}
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'wb') as out: plistlib.dump(data, out)
PY
if ! launchctl bootstrap "gui/$USER_ID" "$PLIST"; then
  echo 'LaunchAgent file exists but registration failed. Inspect launchctl; no existing service was modified.' >&2
  exit 1
fi
launchctl kickstart -k "$SERVICE"
echo 'Read-only telemetry service installed. Verify two advancing reports in the private HUD.'
echo 'No API keys were printed or written to the plist.'
