import pytest
from pydantic import ValidationError

from browser_router.config import Config, Ruleset
from browser_router.utils.chrome import ChromeProfileInfo


def make_config(
    chrome_profiles: list[ChromeProfileInfo],
    rulesets: list[Ruleset] | None = None,
    default_profile: str = "Default",
) -> Config:
    return Config(
        domains=["login.microsoftonline.com"],
        chrome_profiles=chrome_profiles,
        rulesets=rulesets or [],
        default_profile=default_profile,
    )


def test_default_profile_matches_profile_directory(chrome_profiles):
    config = make_config(chrome_profiles, default_profile="Default")

    assert config.default_profile == "Default"


def test_unknown_default_profile_is_rejected(chrome_profiles):
    with pytest.raises(ValidationError, match="Default profile 'Profile 9' not found"):
        make_config(chrome_profiles, default_profile="Profile 9")


def test_default_profile_display_name_is_rejected(chrome_profiles):
    with pytest.raises(ValidationError, match="Default profile 'Work' not found"):
        make_config(chrome_profiles, default_profile="Work")


def test_ruleset_with_known_profile_is_accepted(chrome_profiles, ruleset):
    config = make_config(chrome_profiles, rulesets=[ruleset])

    assert config.rulesets == [ruleset]


def test_ruleset_with_unknown_profile_is_rejected(chrome_profiles, ruleset):
    bad_ruleset = ruleset.model_copy(update={"profile": "Profile 9"})

    with pytest.raises(
        ValidationError, match="Ruleset 'Client' uses unknown profile 'Profile 9'"
    ):
        make_config(chrome_profiles, rulesets=[bad_ruleset])


def test_error_lists_available_profiles(chrome_profiles):
    with pytest.raises(ValidationError, match=r"\['Default', 'Profile 3'\]"):
        make_config(chrome_profiles, default_profile="Profile 9")
