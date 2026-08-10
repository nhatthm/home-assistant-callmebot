"""Config flow for CallMeBot API."""

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class CallMeBotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CallMeBot API."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the single configuration entry without requesting input."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title="CallMeBot API", data={})
