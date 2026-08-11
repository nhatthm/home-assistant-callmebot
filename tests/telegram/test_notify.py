"""Tests for CallMeBot Telegram notify behavior."""

import logging
from typing import TYPE_CHECKING

import pytest
from homeassistant.const import STATE_UNAVAILABLE
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

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


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
    caplog: logging.LogCaptureFixture,
) -> None:
    """Test setup, placeholder notify behavior, and unloading."""
    recipient = "@sample_user"
    object_id = text_notify_object_id(recipient)
    entity_id = f"notify.{object_id}"
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
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.name == f"Telegram Text Message {recipient}"

    with caplog.at_level(logging.INFO):
        await hass.services.async_call(
            "notify",
            "send_message",
            {"entity_id": entity_id, "message": "Test message"},
            blocking=True,
        )

    assert "Recipient: @sample_user; Message: Test message" in caplog.messages

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE
