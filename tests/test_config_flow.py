"""Tests for the CallMeBot API config flow."""

from typing import TYPE_CHECKING

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.callmebot.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    """Test that the user flow creates the empty config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "CallMeBot API"
    assert result["data"] == {}


async def test_user_flow_aborts_when_already_configured(hass: HomeAssistant) -> None:
    """Test that only one config entry can be created."""
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
