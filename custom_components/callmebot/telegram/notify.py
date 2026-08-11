"""CallMeBot Telegram notify entities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.notify import NotifyEntity

from custom_components.callmebot.const import CONF_RECIPIENT

from . import text_notify_object_id

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
        self._attr_name = f"CallMeBot Telegram {recipient} Text"
        self._attr_unique_id = object_id

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Log a placeholder until Telegram message delivery is implemented."""
        del title
        _LOGGER.info("Recipient: %s; Message: %s", self._recipient, message)
