import json
import os
import shutil
import sys
from pathlib import Path

from pydantic import BaseModel

from browser_router.intlogging import get_logger
from browser_router.errors import StartupError

logger = get_logger(__name__)

class ChromeProfileInfo(BaseModel):
    name: str
    user_name: str
    profile_ref: str


def find_chrome_state_file() -> Path:
    """Path to Chrome's live 'Local State' file for the current platform."""
    if sys.platform == "darwin":
        return Path(
            os.path.expanduser(
                "~/Library/Application Support/Google/Chrome/Local State"
            )
        )
    else:
        raise NotImplementedError(f"Unsupported platform: {sys.platform}")


def cached_chrome_state_file() -> Path:
    """
    Path to our own copy of Chrome's 'Local State'.

    Chrome's application-support directory is protected by macOS privacy (TCC), so a
    launchd agent without Full Disk Access gets 'Operation not permitted' reading the
    live file. We instead read from this copy, which is refreshed by the deploy script
    (run from a session that does have access) and, best-effort, on startup.
    """
    return Path(os.path.expanduser("~/Library/Caches/browser-router")) / "Local State"


def refresh_chrome_state_cache() -> bool:
    """Best-effort copy of the live 'Local State' into our cache. True if it succeeded."""
    source = find_chrome_state_file()
    cache = cached_chrome_state_file()
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, cache)
        logger.debug(f"Refreshed Chrome state cache: {cache}")
        return True
    except OSError as exc:
        # Expected when this process lacks Full Disk Access; fall back to the last copy.
        logger.debug(f"Could not refresh Chrome state cache from {source}: {exc}")
        return False


def get_chrome_profiles() -> list[ChromeProfileInfo]:
    profiles = []

    # Keep our copy current when we can; otherwise fall back to the last good copy.
    refresh_chrome_state_cache()
    file_path = cached_chrome_state_file()

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Cached Chrome state file not found: {file_path}")
        raise StartupError(
            e=(
                f"No Chrome state copy found at {file_path}. Run "
                "scripts/osx_refresh_local_deployment.sh from a terminal that can read "
                "Chrome's data (one with Full Disk Access) to create it."
            )
        )
    except PermissionError:
        logger.error(f"Operation not permitted reading cached Chrome state file: {file_path}")
        raise StartupError(
            e=f"Operation not permitted reading {file_path}."
        )

    for d, i in data["profile"]["info_cache"].items():
        logger.debug(f"{d:12} {i.get('name')}  {i.get('user_name', '')}")

        profiles.append(ChromeProfileInfo(
            name=i.get("name"),
            user_name=i.get("user_name", ""),
            profile_ref=d
        ))

    logger.debug(f"Chrome profiles: {profiles}")

    return profiles
