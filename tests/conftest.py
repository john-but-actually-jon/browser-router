import pytest

from browser_router.config import Config, Ruleset
from browser_router.utils.chrome import ChromeProfileInfo


@pytest.fixture
def chrome_profiles() -> list[ChromeProfileInfo]:
    return [
        ChromeProfileInfo(name="Work", user_name="me@work.com", profile_ref="Default"),
        ChromeProfileInfo(
            name="Client", user_name="me@client.com", profile_ref="Profile 3"
        ),
    ]


@pytest.fixture
def ruleset() -> Ruleset:
    return Ruleset(
        name="Client",
        profile="Profile 3",
        routing_identifier="client-ctx",
        domains=["login.microsoftonline.com"],
    )


@pytest.fixture
def config(chrome_profiles: list[ChromeProfileInfo], ruleset: Ruleset) -> Config:
    return Config(
        domains=["login.microsoftonline.com", "accounts.google.com"],
        chrome_profiles=chrome_profiles,
        rulesets=[ruleset],
        default_profile="Default",
    )
