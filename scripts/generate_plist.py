"""
Generate a launchd plist for running browser-router in the background on macOS.

The plist is a per-user LaunchAgent, so the server runs as the current user inside
their login session, which it needs in order to launch Chrome.
"""

import argparse
import getpass
import os
import plistlib
import shlex
import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_version(project_root: Path) -> str:
    pyproject = project_root / "pyproject.toml"
    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        raise SystemExit(f"Couldn't read [project].version from {pyproject}: {exc}")


def find_executable(project_root: Path) -> Path:
    if (
        not (project_root / "pyproject.toml").is_file()
        or not (project_root / "src" / "browser_router").is_dir()
    ):
        raise SystemExit(f"{project_root} doesn't look like the browser-router project.")

    executable = project_root / ".venv" / "bin" / "browser-router"
    if not executable.is_file():
        raise SystemExit(
            f"{executable} not found. Run `uv sync` in {project_root} first."
        )
    return executable


def generate_plist(
    label: str,
    executable: Path,
    project_root: Path,
    port: int,
    log_file: Path,
    log_level: str | None = None,
) -> dict:
    # Python buffers stdout when it isn't a terminal, which delays log lines.
    env = {"PYTHONUNBUFFERED": "1"}
    if log_level:
        env["LOG_LEVEL"] = log_level

    return {
        "Label": label,
        "ProgramArguments": [str(executable), "--port", str(port)],
        "WorkingDirectory": str(project_root),
        "EnvironmentVariables": env,
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "StandardOutPath": str(log_file),
        "StandardErrorPath": str(log_file),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        "--label",
        default=f"com.{getpass.getuser()}.browser-router.{read_version(PROJECT_ROOT)}",
        help="launchd job label (default: %(default)s)",
    )
    parser.add_argument(
        "--print-label",
        action="store_true",
        help="Print the resolved launchd label and exit (does not write a plist).",
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="Port to listen on (default: %(default)s)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="LOG_LEVEL for the server (default: the server's own default, INFO)",
    )
    parser.add_argument(
        "--output",
        help="Where to write the plist, or '-' for stdout "
        "(default: ~/Library/LaunchAgents/<label>.plist)",
    )
    return parser.parse_args()


def main() -> None:
    if sys.platform != "darwin":
        raise SystemExit("launchd plists are only supported on macOS.")

    args = parse_args()

    if args.print_label:
        print(args.label)
        return

    executable = find_executable(PROJECT_ROOT)
    log_file = Path.home() / "Library" / "Logs" / f"{args.label}.log"
    plist = generate_plist(
        label=args.label,
        executable=executable,
        project_root=PROJECT_ROOT,
        port=args.port,
        log_file=log_file,
        log_level=args.log_level,
    )

    if args.output == "-":
        sys.stdout.buffer.write(plistlib.dumps(plist))
        return

    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else Path.home() / "Library" / "LaunchAgents" / f"{args.label}.plist"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(plistlib.dumps(plist))

    domain = f"gui/{os.getuid()}"
    service = f"{domain}/{args.label}"
    print(f"Wrote {output}")
    print(f"Project: {PROJECT_ROOT}")
    print()
    print("Start it now (if it's already loaded, run the stop command first):")
    print(f"  launchctl bootstrap {domain} {shlex.quote(str(output))}")
    print("Restart it after code or rulesets.yml changes:")
    print(f"  launchctl kickstart -k {service}")
    print("Stop and unload it:")
    print(f"  launchctl bootout {service}")
    print("Logs:")
    print(f"  {log_file}")


if __name__ == "__main__":
    main()
