"""
Interactive editor for rulesets.yml.

Lets a new user define a rulesets.yml from scratch, or edit/extend an existing
one: add new rulesets, edit or delete existing rulesets, and set the top-level
allowed `domains` and `default_profile`. Every field is required.

Run it from the project with:

    uv run python scripts/edit_rulesets.py

Chrome profiles are offered as a numbered list so you pick the profile
*directory name* (e.g. "Profile 3") that the router needs, not the display name.
"""

import getpass
import os
import shutil
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "rulesets.yml"

# Make `browser_router` importable even without an editable install.
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_router.config import Ruleset


class QuitWithoutSaving(Exception):
    """Raised to abort the editor (Ctrl-D / Ctrl-C / explicit quit)."""


# --------------------------------------------------------------------------- #
# Input helpers
# --------------------------------------------------------------------------- #
def read_line(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        raise QuitWithoutSaving() from None


def ask(prompt: str, default: str | None = None) -> str:
    """Prompt for a required, non-empty string. `default` is used on empty input."""
    suffix = f" [{default}]" if default is not None else ""
    while True:
        value = read_line(f"{prompt}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        print("  This field is required.")


def confirm(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        value = read_line(f"{prompt} [{hint}]: ").strip().lower()
        if not value:
            return default
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


def ask_int(prompt: str, low: int, high: int, default: int | None = None) -> int:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        value = read_line(f"{prompt}{suffix}: ").strip()
        if not value and default is not None:
            return default
        try:
            number = int(value)
        except ValueError:
            print(f"  Enter a number between {low} and {high}.")
            continue
        if low <= number <= high:
            return number
        print(f"  Enter a number between {low} and {high}.")


def choose_profile(profiles: list, current: str | None = None) -> str:
    """Pick a Chrome profile directory name, or type one if detection failed."""
    if not profiles:
        print(
            "  Could not read your Chrome profiles; enter the profile directory "
            "name manually (e.g. 'Profile 3')."
        )
        return ask("  Profile directory", default=current)

    print("  Available Chrome profiles:")
    default_index = None
    for i, profile in enumerate(profiles, 1):
        label = profile.profile_ref
        extra = " / ".join(x for x in (profile.name, profile.user_name) if x)
        if extra:
            label += f"  ({extra})"
        if profile.profile_ref == current:
            default_index = i
            label += "  <- current"
        print(f"    {i}. {label}")

    choice = ask_int("  Select a profile", 1, len(profiles), default=default_index)
    return profiles[choice - 1].profile_ref


def collect_domains(current: list[str] | None = None) -> list[str]:
    """Collect at least one domain. On edit, offer to keep the current list."""
    if current:
        print("  Current domains:")
        for domain in current:
            print(f"    - {domain}")
        if confirm("  Keep these domains?", default=True):
            return list(current)

    print("  Enter domains one per line. Submit an empty line when done.")
    domains: list[str] = []
    while True:
        line = read_line("    domain> ").strip()
        if not line:
            if domains:
                return domains
            print("    At least one domain is required.")
            continue
        if line in domains:
            print("    Already added.")
            continue
        domains.append(line)


# --------------------------------------------------------------------------- #
# Load / render rulesets.yml
# --------------------------------------------------------------------------- #
def load_config() -> dict:
    if not CONFIG_PATH.is_file():
        print(f"No {CONFIG_PATH.name} found; starting a new one.")
        return {"domains": [], "default_profile": "", "rulesets": []}

    data = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    return {
        "domains": list(data.get("domains") or []),
        "default_profile": data.get("default_profile") or "",
        "rulesets": list(data.get("rulesets") or []),
    }


def _yq(value: str) -> str:
    """Render a string as a safely quoted YAML double-quoted scalar."""
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_yaml(data: dict) -> str:
    lines = [
        "# Domains that should be routed to specific Chrome profiles",
        "# Others will be ignored by the router",
    ]
    if data["domains"]:
        lines.append("domains:")
        lines += [f"  - {_yq(d)}" for d in data["domains"]]
    else:
        lines.append("domains: []")

    lines += ["", f"default_profile: {_yq(data['default_profile'])}", "", "rulesets:"]
    if not data["rulesets"]:
        lines[-1] = "rulesets: []"

    for rs in data["rulesets"]:
        lines.append(f"  - name: {_yq(rs['name'])}")
        lines.append(f"    profile: {_yq(rs['profile'])}")
        lines.append(f"    routing_identifier: {_yq(rs['routing_identifier'])}")
        lines.append("    domains:")
        lines += [f"      - {_yq(d)}" for d in rs["domains"]]

    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Ruleset editing
# --------------------------------------------------------------------------- #
def build_ruleset(profiles: list, existing: dict | None = None) -> dict:
    existing = existing or {}
    name = ask("  Name", default=existing.get("name"))
    print("  Profile (the Chrome profile this ruleset routes to):")
    profile = choose_profile(profiles, current=existing.get("profile"))
    routing_identifier = ask(
        "  Routing identifier (the ctx sent by the $BROWSER script)",
        default=existing.get("routing_identifier"),
    )
    print("  Domains (hosts that route to this profile):")
    domains = collect_domains(existing.get("domains"))

    ruleset = {
        "name": name,
        "profile": profile,
        "routing_identifier": routing_identifier,
        "domains": domains,
    }
    # Validate the shape using the project's own model.
    Ruleset(**ruleset)
    return ruleset


def pick_ruleset(data: dict) -> int | None:
    rulesets = data["rulesets"]
    if not rulesets:
        print("No rulesets defined yet.")
        return None
    print("Rulesets:")
    for i, rs in enumerate(rulesets, 1):
        print(
            f"  {i}. {rs['name']}  (profile: {rs['profile']}, ctx: {rs['routing_identifier']})"
        )
    choice = ask_int("Select a ruleset", 1, len(rulesets))
    return choice - 1


# --------------------------------------------------------------------------- #
# Menu actions
# --------------------------------------------------------------------------- #
def print_summary(data: dict) -> None:
    print()
    print("Current configuration")
    print("---------------------")
    print(f"  default_profile: {data['default_profile'] or '(not set)'}")
    print(f"  allowed domains: {len(data['domains'])}")
    print(f"  rulesets:        {len(data['rulesets'])}")
    for rs in data["rulesets"]:
        print(
            f"    - {rs['name']} -> {rs['profile']} (ctx: {rs['routing_identifier']})"
        )
    print()


def save(data: dict) -> None:
    if not data["default_profile"]:
        print("default_profile is required before saving. Set it from the menu.")
        raise _NotReady()
    if not data["domains"]:
        print("At least one top-level allowed domain is required before saving.")
        raise _NotReady()

    if CONFIG_PATH.is_file():
        backup = CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + ".bak")
        shutil.copy2(CONFIG_PATH, backup)
        print(f"Backed up existing config to {backup.name}")

    CONFIG_PATH.write_text(render_yaml(data))
    print(f"Saved {CONFIG_PATH}")


class _NotReady(Exception):
    """Raised when the config can't be saved yet; keeps the menu open."""


def reminder() -> None:
    label = f"com.{getpass.getuser()}.browser-router"
    service = f"gui/{os.getuid()}/{label}"
    print()
    print("Done. The router reads rulesets.yml only at startup.")
    print("If the launchctl service is already running, restart it to apply changes:")
    print(f"  launchctl kickstart -k {service}")


# --------------------------------------------------------------------------- #
# Main loop
# --------------------------------------------------------------------------- #
def get_profiles() -> list:
    try:
        from browser_router.utils.chrome import get_chrome_profiles

        return get_chrome_profiles()
    except Exception as exc:  # noqa: BLE001 - detection is best-effort
        print(f"Warning: could not read Chrome profiles ({exc}).")
        print("You can still type profile directory names manually.")
        return []


def main() -> None:
    print("browser-router rulesets.yml editor")
    profiles = get_profiles()
    data = load_config()

    try:
        while True:
            print_summary(data)
            print("What would you like to do?")
            print("  1. Add a new ruleset")
            print("  2. Edit an existing ruleset")
            print("  3. Delete a ruleset")
            print("  4. Edit allowed domains (top-level)")
            print("  5. Set default profile")
            print("  6. Save and exit")
            print("  7. Quit without saving")
            choice = ask_int("Choose", 1, 7)

            if choice == 1:
                print("New ruleset:")
                data["rulesets"].append(build_ruleset(profiles))
                print("Added.")
            elif choice == 2:
                index = pick_ruleset(data)
                if index is not None:
                    print(f"Editing '{data['rulesets'][index]['name']}':")
                    data["rulesets"][index] = build_ruleset(
                        profiles, existing=data["rulesets"][index]
                    )
                    print("Updated.")
            elif choice == 3:
                index = pick_ruleset(data)
                if index is not None:
                    name = data["rulesets"][index]["name"]
                    if confirm(f"Delete ruleset '{name}'?", default=False):
                        data["rulesets"].pop(index)
                        print("Deleted.")
            elif choice == 4:
                print("Top-level allowed domains (only these hosts are ever opened):")
                data["domains"] = collect_domains(data["domains"])
                print("Updated.")
            elif choice == 5:
                print("Default profile (used when no ruleset matches):")
                data["default_profile"] = choose_profile(
                    profiles, current=data["default_profile"] or None
                )
                print("Updated.")
            elif choice == 6:
                try:
                    save(data)
                except _NotReady:
                    continue
                reminder()
                return
            elif choice == 7:
                raise QuitWithoutSaving()
    except QuitWithoutSaving:
        print("\nExited without saving.")


if __name__ == "__main__":
    main()
