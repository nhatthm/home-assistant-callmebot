"""CallMeBot notify entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import CONF_INTEGRATION_TYPE, CONF_MESSAGE_TYPE, INTEGRATION_TELEGRAM
from .telegram import MESSAGE_TYPE_CALL, MESSAGE_TYPE_TEXT
from .telegram.call_notify import CallMeBotTelegramCallNotifyEntity
from .telegram.text_notify import CallMeBotTelegramTextNotifyEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a CallMeBot notify entity for the configured integration type."""
    del hass
    if entry.data[CONF_INTEGRATION_TYPE] != INTEGRATION_TELEGRAM:
        return
    if entry.data[CONF_MESSAGE_TYPE] == MESSAGE_TYPE_TEXT:
        async_add_entities([CallMeBotTelegramTextNotifyEntity(entry)])
    elif entry.data[CONF_MESSAGE_TYPE] == MESSAGE_TYPE_CALL:
        async_add_entities([CallMeBotTelegramCallNotifyEntity(entry)])
