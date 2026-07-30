#!/bin/sh
set -eu
BASE="$HOME/Library/Application Support/SupportBotPresence"
PLIST="$HOME/Library/LaunchAgents/com.supportbot.presence.plist"
mkdir -p "$BASE" "$HOME/Library/LaunchAgents"
case "$(uname -m)" in arm64) SRC="supportbot-presence-arm64" ;; *) SRC="supportbot-presence-amd64" ;; esac
cp "$(dirname "$0")/$SRC" "$BASE/supportbot-presence"
chmod 700 "$BASE/supportbot-presence"
sed "s|__PROGRAM__|$BASE/supportbot-presence|g" "$(dirname "$0")/com.supportbot.presence.plist" > "$PLIST"
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "SupportBot Presence installed. Return to the browser."
