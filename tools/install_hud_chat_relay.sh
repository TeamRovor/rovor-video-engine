#!/bin/bash
# Installs a separate outbound-only Ask ROVOR bridge, preserving existing services.
set -euo pipefail
if [[ "$#" -ne 1 ]]; then
  echo 'Usage: bash tools/install_hud_chat_relay.sh https://YOUR-CLOUDFLARE-HUD-ORIGIN' >&2
  exit 2
fi
origin="$1"
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo 'This LaunchAgent installer requires macOS.' >&2
  exit 2
fi
root="$(cd "$(dirname "$0")/.." && pwd -P)"
node_bin="$(command -v node || true)"
python_bin="$(command -v python3 || true)"
if [[ -z "$node_bin" || -z "$python_bin" ]]; then
  echo 'Need Node.js and Python 3 for this installer.' >&2
  exit 2
fi
"$node_bin" --check "$root/tools/hud_chat_relay_client.mjs"
"$node_bin" -e '
const value=process.argv[1];const url=new URL(value);
if(url.protocol!=="https:"||url.origin!==value.replace(/\/$/,"")||url.username||url.password||url.hash||url.search)throw Error("Invalid private HUD HTTPS origin");
' "$origin"
if ! /usr/bin/security find-generic-password -s rovordigital.hud.cloudflare.writer -w >/dev/null 2>&1 &&
   ! /usr/bin/security find-generic-password -s rovordigital.hud.writer -w >/dev/null 2>&1; then
  echo 'Existing HUD writer credential is missing from Keychain (checked both supported service names). No new credentials were created.' >&2
  exit 2
fi
if ! /usr/bin/security find-generic-password -s rovordigital.omniroute.endpoint -w >/dev/null 2>&1; then
  echo 'Existing OmniRoute endpoint credential is missing from Keychain. No new credentials were created.' >&2
  exit 2
fi
plist="$HOME/Library/LaunchAgents/com.rovor.hud-chat-relay.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
"$python_bin" - "$plist" "$root" "$node_bin" "$origin" <<'PY'
import os,plistlib,sys
target,root,node,origin=sys.argv[1:]
data={
 'Label':'com.rovor.hud-chat-relay',
 'ProgramArguments':[node,os.path.join(root,'tools/hud_chat_relay_client.mjs')],
 'WorkingDirectory':root,
 'EnvironmentVariables':{'ROVOR_HUD_ORIGIN':origin},
 'RunAtLoad':True,
 'KeepAlive':True,
 'StandardOutPath':os.path.expanduser('~/Library/Logs/rovor-hud-chat.log'),
 'StandardErrorPath':os.path.expanduser('~/Library/Logs/rovor-hud-chat-error.log')
}
with open(target,'wb') as f:plistlib.dump(data,f)
os.chmod(target,0o600)
PY
label="gui/$(id -u)/com.rovor.hud-chat-relay"
launchctl bootout "$label" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$plist"
launchctl kickstart -k "$label"
echo 'Ask ROVOR outbound chat LaunchAgent installed. Verify the model list in your private HUD.'
echo 'A model is not proven usable until one benign test prompt returns an actual completion receipt.'
