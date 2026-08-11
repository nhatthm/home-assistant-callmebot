"""Config flow for CallMeBot API."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_INTEGRATION_TYPE,
    DOMAIN,
    INTEGRATION_TELEGRAM,
)
from .telegram.config_flow import TelegramConfigFlow


class CallMeBotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CallMeBot API."""

    VERSION = 1

    _telegram_config_flow: TelegramConfigFlow

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the CallMeBot integration type."""
        if user_input is not None:
            self._telegram_config_flow = TelegramConfigFlow(self)
            return await self.async_step_telegram_message_type()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_INTEGRATION_TYPE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=INTEGRATION_TELEGRAM,
                                    label="Telegram",
                                )
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_telegram_message_type(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Delegate the Telegram message type step."""
        return await self._telegram_config_flow.async_step_message_type(user_input)

    async def async_step_telegram_text(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Delegate the Telegram Text Message configuration step."""
        return await self._telegram_config_flow.async_step_text(user_input)

    async def async_step_telegram_text_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Delegate the Telegram Text Message confirmation step."""
        return await self._telegram_config_flow.async_step_text_confirm(user_input)
