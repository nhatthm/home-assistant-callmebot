"""Tests for CallMeBot API translations."""

from typing import TYPE_CHECKING

import pytest
from homeassistant.helpers.translation import async_get_translations

from custom_components.callmebot.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_config_flow_field_translations(hass: HomeAssistant) -> None:
    """Test Home Assistant loads config flow field labels."""
    translations = await async_get_translations(
        hass,
        "en",
        "config",
        integrations={DOMAIN},
    )

    assert (
        translations["component.callmebot.config.step.user.data.integration_type"]
        == "Integration Type"
    )
    assert (
        translations[
            "component.callmebot.config.step.telegram_message_type.data.message_type"
        ]
        == "Message Type"
    )
    assert translations["component.callmebot.config.error.telegram_text_api_error"] == (
        "The CallMeBot Telegram text API rejected the request."
    )
    assert translations[
        "component.callmebot.config.error.telegram_text_permission_denied"
    ] == (
        "**Error: Permission denied for {recipient}. You need to authorize CallMeBot "
        "to contact this Telegram user ({recipient}).**\n\n**Click** "
        "[**here**](https://api2.callmebot.com/txt/login.php) **to Authenticate "
        "{recipient} and then try again.**"
    )
