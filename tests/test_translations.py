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
    assert translations[
        "component.callmebot.config.step.telegram_text.description"
    ] == (
        "Enter a Telegram username beginning with `@` or a full international phone "
        "number such as `+1234567890`. A test message will be sent to validate access. "
        "If CallMeBot reports permission denied, [authenticate the Telegram recipient]"
        "(https://api2.callmebot.com/txt/login.php) and try again."
    )
    assert (
        "<username>"
        not in translations[
            "component.callmebot.config.error.telegram_text_invalid_recipient"
        ]
    )
    assert translations["component.callmebot.config.error.telegram_text_api_error"] == (
        "The CallMeBot Telegram text API rejected the request."
    )
    assert translations[
        "component.callmebot.config.error.telegram_text_permission_denied"
    ] == (
        "Permission denied for {recipient}. Authorize CallMeBot using the "
        "authentication link above and try again."
    )
