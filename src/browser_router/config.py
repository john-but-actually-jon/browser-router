from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

from browser_router.intlogging import get_logger
from browser_router.utils.chrome import ChromeProfileInfo, get_chrome_profiles

logger = get_logger(__name__)


class Ruleset(BaseModel):
    name: str = Field(..., description="The name of the ruleset.")
    profile: str = Field(..., description="The profile to use for the ruleset.")
    routing_identifier: str = Field(
        ..., description="The routing identifier to use for the ruleset."
    )
    domains: list[str] = Field(..., description="The domains to route to the ruleset.")


class Config(BaseModel):
    domains: list[str] = Field(
        ..., description="Domains that are allowed to be routed."
    )
    chrome_profiles: list[ChromeProfileInfo] = Field(
        ...,
        description="A dictionary of Chrome profiles and their corresponding rulesets.",
    )
    rulesets: list[Ruleset] = Field(
        ..., description="A rulesets defined in the rulesets.yml file."
    )
    default_profile: str = Field(
        ..., description="The default profile to use for the ruleset."
    )

    @model_validator(mode="after")
    def validate_profiles(self) -> "Config":
        # Profiles are referenced by directory name (e.g. "Profile 3"), not display name,
        # because that is what Chrome's --profile-directory flag expects.
        available = sorted(p.profile_ref for p in self.chrome_profiles)
        if self.default_profile not in available:
            raise ValueError(
                f"Default profile {self.default_profile!r} not found in Chrome. "
                f"Available profiles: {available}. Please fix it in rulesets.yml."
            )
        for ruleset in self.rulesets:
            if ruleset.profile not in available:
                raise ValueError(
                    f"Ruleset {ruleset.name!r} uses unknown profile {ruleset.profile!r}. "
                    f"Available profiles: {available}. Please fix it in rulesets.yml."
                )
        return self


@lru_cache(maxsize=1)
def get_config() -> Config:
    root_path = Path(__file__).parent.parent.parent
    config_path = root_path / "rulesets.yml"
    config_data = yaml.safe_load(config_path.read_text())
    
    load_dotenv(root_path / ".env")
    chrome_profiles = get_chrome_profiles()
    rulesets = config_data.get("rulesets", [])
    default_profile = config_data.get("default_profile", "Default")
    domains = config_data.get("domains", [])

    return Config(
        rulesets=[Ruleset(**rule) for rule in rulesets],
        chrome_profiles=chrome_profiles,
        default_profile=default_profile,
        domains=domains,
    )
