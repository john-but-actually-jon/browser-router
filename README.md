# browser-router

A small local HTTP server that opens CLI authentication flows (OAuth/SSO logins) in the right Chrome profile.

When you work for several clients, each with its own identity provider, a CLI login like `az login` opens in whichever Chrome profile happens to be active, and you end up signed in with the wrong account. browser-router fixes this per workspace: the workspace's `$BROWSER` is replaced with a small script that forwards the URL to the router together with a context identifier (`ctx`). The router then opens the URL in the Chrome profile configured for that context. For example, every login started from the DERTOUR workspace opens in the DERTOUR Chrome profile.

## How it works

1. A CLI in your workspace terminal wants to open a login page and calls `$BROWSER <url>`.
2. The `$BROWSER` script sends `GET /open?url=<url>&ctx=<ctx>` to the router on `127.0.0.1:8765`.
3. The router decides what to do with the URL:
   - If the URL isn't `https://`, or its host isn't listed in `domains` in `rulesets.yml` (subdomains count), it responds `403` and opens nothing.
   - If a ruleset's `routing_identifier` equals `ctx` and the host matches one of that ruleset's domains, it opens the URL in that ruleset's Chrome profile.
   - Otherwise it opens the URL in `default_profile`.
4. Chrome is launched with `--profile-directory=<profile>`, and the router responds `204`.

This works with any CLI that opens URLs through `$BROWSER`, such as tools built on Python's `webbrowser` module (the Azure CLI, for example). Tools that call `open` or `xdg-open` directly bypass `$BROWSER` and won't be routed.

## Requirements

- macOS. Chrome profile discovery currently only supports macOS.
- Google Chrome
- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

## Development setup

```sh
uv sync                      # create .venv and install dependencies, including dev tools
uv run browser-router        # start the server on 127.0.0.1:8765
uv run pytest                # run the tests
uv run ruff check src tests  # lint
uv run black src tests       # format
```

Server options:

- `--port <port>` sets the port to listen on (default `8765`).
- `LOG_LEVEL=DEBUG uv run browser-router` logs the discovered Chrome profiles, the loaded config, and every routing decision. The `--verbose` flag currently only enables debug logs from `main.py`.

The router reads `rulesets.yml` from the repository root, so run it from this checkout, or use `uv run --project /path/to/browser-router browser-router` from elsewhere.

## Running in the background (launchd)

`scripts/generate_plist.py` writes a launchd LaunchAgent that keeps the router running as your user, starts it at login, and restarts it if it crashes. It detects the project location from where the script lives and runs the project's `.venv/bin/browser-router`, so run `uv sync` first.

```sh
uv run python scripts/generate_plist.py
```

This writes `~/Library/LaunchAgents/com.<you>.browser-router.plist` and prints the commands to manage the service:

```sh
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.<you>.browser-router.plist  # start now
launchctl kickstart -k gui/$(id -u)/com.<you>.browser-router                          # restart
launchctl bootout gui/$(id -u)/com.<you>.browser-router                               # stop and unload
```

- The router reads `rulesets.yml` only at startup, so restart it with `kickstart -k` after changing the config or the code.
- Output goes to `~/Library/Logs/com.<you>.browser-router.log`.
- Options: `--port`, `--log-level DEBUG`, `--label`, and `--output -` to print the plist without writing it.
- The plist contains absolute paths. If you move the checkout, run `bootout`, regenerate the plist, and `bootstrap` it again. Do the same after changing any of the options above.

## Configuration

Routing is configured in `rulesets.yml`:

```yaml
# Only URLs on these hosts (or their subdomains) are opened; everything else is refused.
domains:
  - login.microsoftonline.com
  - microsoft.com
  - accounts.google.com

# Chrome profile used when no ruleset matches.
default_profile: "Default"

rulesets:
  - name: "DERTOUR"
    profile: "Profile 3"                          # Chrome profile directory
    routing_identifier: "dtgs-customer-layer"     # the ctx sent by the $BROWSER script
    domains:                                      # hosts that route to this profile
      - "login.microsoftonline.com"
      - "microsoft.com"
```

Instead of editing the file by hand, you can use the interactive editor, which lets you add, edit, or delete rulesets, set the allowed `domains` and `default_profile`, and picks Chrome profiles from a numbered list so you get the directory name right. Every field is required:

```sh
uv run python scripts/edit_rulesets.py
```

It backs up the existing file to `rulesets.yml.bak` before saving, and reminds you to restart the launchd service if it's already running.

`profile` and `default_profile` must be Chrome profile **directory names** such as `Default` or `Profile 3`, not the display names shown in Chrome. To find a profile's directory, open `chrome://version` in that profile and look at the last part of "Profile Path". The router checks every profile against your Chrome installation at startup. If one doesn't exist, it refuses to start and lists the available profiles.

## Routing a workspace to a Chrome profile

### 1. Create the `$BROWSER` script

Save this somewhere outside the workspace, for example `~/bin/browser-router-open`, and make it executable with `chmod +x ~/bin/browser-router-open`:

```sh
#!/bin/sh
# Forwards a URL to browser-router with the workspace's routing context.
ROUTER_URL="${BROWSER_ROUTER_URL:-http://127.0.0.1:8765}"

curl -fsS -o /dev/null -G "$ROUTER_URL/open" \
  --data-urlencode "url=$1" \
  --data-urlencode "ctx=${BROWSER_ROUTER_CTX:-}" \
  || { echo "browser-router did not open the URL. Open it manually: $1" >&2; exit 1; }
```

The script exits non-zero when the router refuses the URL or isn't running, so CLIs that support it can fall back to printing the URL.

### 2. Point the workspace at it

In the workspace's `.vscode/settings.json` (Cursor reads the same file):

```json
{
  "terminal.integrated.env.osx": {
    "BROWSER": "/Users/<you>/bin/browser-router-open",
    "BROWSER_ROUTER_CTX": "dtgs-customer-layer"
  }
}
```

`BROWSER_ROUTER_CTX` must match the `routing_identifier` of a ruleset in `rulesets.yml`. The setting only applies to terminals opened after the change, so open a new terminal before testing.

### 3. Dev containers

The same approach works in a dev container running on Docker Desktop. A few things differ:

- Use `terminal.integrated.env.linux` instead of `terminal.integrated.env.osx`.
- Point `BROWSER_ROUTER_URL` at the host with `http://host.docker.internal:8765`.
- The script must exist inside the container, for example committed as `.devcontainer/browser-router-open`.
- `curl` must be installed in the container image.

```json
{
  "terminal.integrated.env.linux": {
    "BROWSER": "${workspaceFolder}/.devcontainer/browser-router-open",
    "BROWSER_ROUTER_CTX": "dtgs-customer-layer",
    "BROWSER_ROUTER_URL": "http://host.docker.internal:8765"
  }
}
```

### 4. Test it

With the router running, open a new terminal in the workspace and run:

```sh
echo "$BROWSER"                                    # should print the script path
"$BROWSER" "https://login.microsoftonline.com/"    # should open in the configured profile
```

## Troubleshooting

- **Nothing opens and the script prints "Open it manually".** The URL isn't `https://`, its host isn't in the top-level `domains` list, or the router isn't running.
- **The URL opens in the default profile instead of the workspace's profile.** Check that `BROWSER_ROUTER_CTX` exactly matches the ruleset's `routing_identifier`, and that the URL's host matches one of the ruleset's `domains`. Run the router with `LOG_LEVEL=DEBUG` to see the routing decision for each request.
- **The router fails at startup with "profile ... not found".** Use the profile's directory name (for example `Profile 3`), not its display name. See [Configuration](#configuration).
- **`$BROWSER` isn't the script.** Open a new terminal after changing the workspace settings.
