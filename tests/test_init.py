"""Tests for CallMeBot API setup and teardown."""

from typing import TYPE_CHECKING

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.callmebot import async_setup_entry, async_unload_entry
from custom_components.callmebot.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_setup_and_unload_entry(hass: HomeAssistant) -> None:
    """Test setting up and unloading an empty config entry."""
    entry = MockConfigEntry(domain=DOMAIN)

    assert await async_setup_entry(hass, entry)
    assert await async_unload_entry(hass, entry)
