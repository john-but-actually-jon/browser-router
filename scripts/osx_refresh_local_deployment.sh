#! /bin/bash

# Regenerate the launchd plist and redeploy browser-router with the latest changes.

set -euo pipefail

cd "$(dirname "$0")/.."

UID_NUM=$(id -u)
DOMAIN="gui/$UID_NUM"
LAUNCH_AGENTS="/Users/$(whoami)/Library/LaunchAgents"
LOGS="/Users/$(whoami)/Library/Logs"
LABEL_PREFIX="com.$(whoami).browser-router"
CHROME_STATE="/Users/$(whoami)/Library/Application Support/Google/Chrome/Local State"
STATE_CACHE_DIR="/Users/$(whoami)/Library/Caches/browser-router"

# Install the project + dependencies. The project is installed editable, so source
# changes under src/ are picked up automatically on the next restart.
uv sync

# Copy Chrome's "Local State" into a readable cache dir. Chrome's own directory is
# protected by macOS privacy (TCC), so the launchd service (which lacks Full Disk
# Access) can't read it directly; it reads this copy instead. This copy must be made
# from a session that CAN read Chrome's data (e.g. a Terminal with Full Disk Access).
mkdir -p "$STATE_CACHE_DIR"
if cp "$CHROME_STATE" "$STATE_CACHE_DIR/Local State"; then
    echo "Copied Chrome state to $STATE_CACHE_DIR/Local State"
else
    echo "WARNING: couldn't read $CHROME_STATE." >&2
    echo "         Grant this terminal Full Disk Access, or the service will fail to start." >&2
fi

# Resolve the versioned label from pyproject.toml (single source of truth).
LABEL="$(.venv/bin/python scripts/generate_plist.py --print-label)"
PLIST="$LAUNCH_AGENTS/$LABEL.plist"

# Stop and remove any previously-deployed browser-router agents (any version),
# so old versions don't linger or fight over the port.
launchctl list | awk -v p="$LABEL_PREFIX" 'index($3, p) == 1 {print $3}' | while read -r svc; do
    launchctl bootout "$DOMAIN/$svc" 2>/dev/null || true
done
rm -f "$LAUNCH_AGENTS/$LABEL_PREFIX"*.plist
rm -f "$LOGS/$LABEL_PREFIX"*.log

# Regenerate the plist for the current version.
.venv/bin/python scripts/generate_plist.py --label "$LABEL"

# Load and (re)start the service.
launchctl bootstrap "$DOMAIN" "$PLIST"
launchctl kickstart -k "$DOMAIN/$LABEL"

echo "Deployed $LABEL"
