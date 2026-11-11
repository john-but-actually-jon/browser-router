import json
import os
import sys

from pydantic import BaseModel

from browser_router.intlogging import get_logger

logger = get_logger(__name__)

class ChromeProfileInfo(BaseModel):
    name: str
    user_name: str
    profile_ref: str


def find_chrome_state_file() -> os.PathLike:
    """Find the Chrome state file in the user's home directory."""
    if sys.platform == "darwin":
        return os.path.expanduser(
            "~/Library/Application Support/Google/Chrome/Local State"
        )
    else:
        raise NotImplementedError(f"Unsupported platform: {sys.platform}")


def get_chrome_profiles() -> list[ChromeProfileInfo]:
    profiles = []
    file_path = find_chrome_state_file()

    with open(file_path, "r") as f:
        data = json.load(f)

    for d, i in data["profile"]["info_cache"].items():
        logger.debug(f"{d:12} {i.get('name')}  {i.get('user_name', '')}")

        profiles.append(ChromeProfileInfo(
            name=i.get("name"),
            user_name=i.get("user_name", ""),
            profile_ref=d
        ))

    logger.debug(f"Chrome profiles: {profiles}")

    return profiles
