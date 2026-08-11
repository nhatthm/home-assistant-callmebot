"""Tests for CallMeBot Telegram notify behavior."""

import logging
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.callmebot.const import (
    CONF_INTEGRATION_TYPE,
    CONF_MESSAGE_TYPE,
    CONF_RECIPIENT,
    DOMAIN,
    INTEGRATION_TELEGRAM,
)
from custom_components.callmebot.notify import async_setup_entry as async_setup_notify
from custom_components.callmebot.telegram import (
    MESSAGE_TYPE_TEXT,
    text_notify_object_id,
)
from custom_components.callmebot.telegram.api import (
    CallMeBotTelegramTextAPIError,
    CallMeBotTelegramTextConnectionError,
    TelegramTextAPIErrorCode,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

CONNECTION_ERROR_LOG = (
    "Unable to reach the CallMeBot Telegram text API for recipient @sample_user"
)
REJECTION_ERROR_LOG = (
    "CallMeBot rejected the Telegram text message for recipient @sample_user: "
    "telegram_text_api_error"
)


async def _setup_notify_entity(
    hass: HomeAssistant,
    recipient: str = "@sample_user",
) -> tuple[MockConfigEntry, str]:
    """Set up and return a Telegram text config entry and entity ID."""
    object_id = text_notify_object_id(recipient)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Telegram Text Message {recipient}",
        unique_id=object_id,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TELEGRAM,
            CONF_MESSAGE_TYPE: MESSAGE_TYPE_TEXT,
            CONF_RECIPIENT: recipient,
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, f"notify.{object_id}"


@pytest.mark.parametrize(
    ("integration_type", "message_type"),
    [
        ("future-integration", MESSAGE_TYPE_TEXT),
        (INTEGRATION_TELEGRAM, "future-message-type"),
    ],
)
async def test_notify_platform_ignores_unsupported_entry_types(
    hass: HomeAssistant,
    integration_type: str,
    message_type: str,
) -> None:
    """Test the dispatcher does not create the wrong notify entity type."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: integration_type,
            CONF_MESSAGE_TYPE: message_type,
            CONF_RECIPIENT: "@sample_user",
        },
    )
    entities: list[object] = []

    await async_setup_notify(hass, entry, entities.extend)  # type: ignore[arg-type]

    assert entities == []


async def test_setup_trigger_and_unload_entry(
    hass: HomeAssistant,
) -> None:
    """Test setup, placeholder notify behavior, and unloading."""
    recipient = "@sample_user"
    entry, entity_id = await _setup_notify_entity(hass, recipient)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.name == f"Telegram Text Message {recipient}"

    api_sender = AsyncMock()
    with patch(
        "custom_components.callmebot.telegram.notify.async_send_text_message",
        new=api_sender,
    ):
        await hass.services.async_call(
            "notify",
            "send_message",
            {"entity_id": entity_id, "message": "Test message"},
            blocking=True,
        )

    api_sender.assert_awaited_once()
    assert api_sender.await_args.args[1:] == (recipient, "Test message")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.parametrize(
    ("api_error", "expected_log"),
    [
        (
            CallMeBotTelegramTextConnectionError(),
            CONNECTION_ERROR_LOG,
        ),
        (
            CallMeBotTelegramTextAPIError(TelegramTextAPIErrorCode.API_ERROR),
            REJECTION_ERROR_LOG,
        ),
    ],
)
async def test_send_error_is_logged_and_raised(
    hass: HomeAssistant,
    caplog: logging.LogCaptureFixture,
    api_error: Exception,
    expected_log: str,
) -> None:
    """Test Telegram delivery failures are logged and fail the service call."""
    _, entity_id = await _setup_notify_entity(hass)

    with (
        patch(
            "custom_components.callmebot.telegram.notify.async_send_text_message",
            new=AsyncMock(side_effect=api_error),
        ),
        caplog.at_level(logging.ERROR),
        pytest.raises(HomeAssistantError),
    ):
        await hass.services.async_call(
            "notify",
            "send_message",
            {"entity_id": entity_id, "message": "Sensitive message"},
            blocking=True,
        )

    assert expected_log in caplog.messages
    assert "Sensitive message" not in caplog.text
