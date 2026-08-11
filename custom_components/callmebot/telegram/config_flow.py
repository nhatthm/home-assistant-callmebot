"""Config flow steps for CallMeBot Telegram support."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.callmebot.const import (
    CONF_INTEGRATION_TYPE,
    CONF_MESSAGE_TYPE,
    CONF_RECIPIENT,
    INTEGRATION_TELEGRAM,
)

from . import MESSAGE_TYPE_TEXT, text_notify_object_id, validate_recipient
from .api import (
    CallMeBotTelegramTextConnectionError,
    CallMeBotTelegramTextValidationError,
    async_validate_text_recipient,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult

    from custom_components.callmebot.config_flow import CallMeBotConfigFlow


class TelegramConfigFlow:
    """Handle the Telegram-specific CallMeBot config flow steps."""

    def __init__(self, flow: CallMeBotConfigFlow) -> None:
        """Initialize a Telegram config flow delegate."""
        self._flow = flow
        self._recipient = ""

    async def async_step_message_type(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the Telegram message type."""
        if user_input is not None:
            return await self._flow.async_step_telegram_text()

        return self._flow.async_show_form(
            step_id="telegram_message_type",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MESSAGE_TYPE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=MESSAGE_TYPE_TEXT,
                                    label="Text Message",
                                )
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_text(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate a Telegram Text Message recipient with CallMeBot."""
        errors: dict[str, str] = {}
        api_error = ""
        recipient = ""

        if user_input is not None:
            recipient = user_input[CONF_RECIPIENT]
            try:
                recipient = validate_recipient(recipient)
            except vol.Invalid:
                errors[CONF_RECIPIENT] = "invalid_recipient"
            else:
                try:
                    await async_validate_text_recipient(
                        async_get_clientsession(self._flow.hass), recipient
                    )
                except CallMeBotTelegramTextConnectionError:
                    errors["base"] = "cannot_connect"
                except CallMeBotTelegramTextValidationError as err:
                    errors["base"] = "api_error"
                    api_error = str(err)
                else:
                    self._recipient = recipient
                    return await self._flow.async_step_telegram_text_confirm()

        return self._flow.async_show_form(
            step_id="telegram_text",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RECIPIENT, default=recipient): (
                        selector.TextSelector()
                    )
                }
            ),
            errors=errors,
            description_placeholders={"api_error": api_error},
        )

    async def async_step_text_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm Telegram Text Message entity creation."""
        if user_input is not None:
            object_id = text_notify_object_id(self._recipient)
            entity_id = f"notify.{object_id}"
            registry = er.async_get(self._flow.hass)

            if registry.async_get(entity_id) or self._flow.hass.states.get(entity_id):
                return self._flow.async_abort(reason="entity_already_exists")

            await self._flow.async_set_unique_id(object_id)
            self._flow._abort_if_unique_id_configured()  # noqa: SLF001

            return self._flow.async_create_entry(
                title=f"Telegram Text Message {self._recipient}",
                data={
                    CONF_INTEGRATION_TYPE: INTEGRATION_TELEGRAM,
                    CONF_MESSAGE_TYPE: MESSAGE_TYPE_TEXT,
                    CONF_RECIPIENT: self._recipient,
                },
            )

        return self._flow.async_show_form(
            step_id="telegram_text_confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"recipient": self._recipient},
            last_step=True,
        )
