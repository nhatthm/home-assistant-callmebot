"""CallMeBot Telegram Call notify entity."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.notify import NotifyEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.callmebot.const import CONF_RECIPIENT

from . import call_notify_object_id
from .api import (
    TelegramCallAPIError,
    TelegramCallConnectionError,
    TelegramCallResult,
    async_send_call,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class CallMeBotTelegramCallNotifyEntity(NotifyEntity):
    """A CallMeBot Telegram Call notify entity."""

    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the Telegram Call notify entity."""
        self._recipient = entry.data[CONF_RECIPIENT]
        object_id = call_notify_object_id(self._recipient)
        self.entity_id = f"notify.{object_id}"
        self._attr_name = entry.title
        self._attr_unique_id = object_id

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Start a Telegram Call through CallMeBot."""
        del title
        try:
            result = await async_send_call(
                async_get_clientsession(self.hass), self._recipient, message
            )
        except TelegramCallConnectionError as err:
            _LOGGER.exception(
                "Unable to reach Telegram Call API for %s", self._recipient
            )
            raise HomeAssistantError(type(err).__name__) from err
        except TelegramCallAPIError as err:
            _LOGGER.exception(
                "Telegram Call failed for %s: %s", self._recipient, err.code
            )
            raise HomeAssistantError(err.code.value) from err
        if result is TelegramCallResult.REJECTED:
            _LOGGER.warning(
                "Telegram Call was rejected by recipient %s", self._recipient
            )
