"""CallMeBot Telegram notify entities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.notify import NotifyEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.callmebot.const import CONF_RECIPIENT

from . import text_notify_object_id
from .api import (
    CallMeBotTelegramTextAPIError,
    CallMeBotTelegramTextConnectionError,
    async_send_text_message,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class CallMeBotTelegramTextNotifyEntity(NotifyEntity):
    """A CallMeBot Telegram text notify entity."""

    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the Telegram text notify entity."""
        recipient = entry.data[CONF_RECIPIENT]
        object_id = text_notify_object_id(recipient)

        self._recipient = recipient
        self.entity_id = f"notify.{object_id}"
        self._attr_name = entry.title
        self._attr_unique_id = object_id

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send a Telegram text message through CallMeBot."""
        del title
        try:
            await async_send_text_message(
                async_get_clientsession(self.hass),
                self._recipient,
                message,
            )
        except CallMeBotTelegramTextConnectionError as err:
            error_message = "Unable to reach the CallMeBot Telegram text API"
            _LOGGER.exception(
                "Unable to reach the CallMeBot Telegram text API for recipient %s",
                self._recipient,
            )
            raise HomeAssistantError(error_message) from err
        except CallMeBotTelegramTextAPIError as err:
            error_message = "CallMeBot rejected the Telegram text message"
            _LOGGER.exception(
                "CallMeBot rejected the Telegram text message for recipient %s: %s",
                self._recipient,
                err.code.value,
            )
            raise HomeAssistantError(error_message) from err
