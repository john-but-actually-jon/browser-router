#! /bin/bash

# Stop any running browser-router service and remove its launchd plist, logs,
# and the Chrome state cache.

set -euo pipefail

cd "$(dirname "$0")/.."

DOMAIN="gui/$(id -u)"
LAUNCH_AGENTS="/Users/$(whoami)/Library/LaunchAgents"
LOGS="/Users/$(whoami)/Library/Logs"
STATE_CACHE_DIR="/Users/$(whoami)/Library/Caches/browser-router"
LABEL_PREFIX="com.$(whoami).browser-router"

# Stop and unload any deployed browser-router agents (any version).
launchctl list | awk -v p="$LABEL_PREFIX" 'index($3, p) == 1 {print $3}' | while read -r svc; do
    echo "Stopping $svc"
    launchctl bootout "$DOMAIN/$svc" 2>/dev/null || true
done

# Remove the plist files, logs, and the Chrome state cache.
rm -f "$LAUNCH_AGENTS/$LABEL_PREFIX"*.plist
rm -f "$LOGS/$LABEL_PREFIX"*.log
rm -rf "$STATE_CACHE_DIR"

echo "Removed browser-router deployment (plist, logs, and cache)."
