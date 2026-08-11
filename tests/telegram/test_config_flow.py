"""Tests for the CallMeBot Telegram config flow."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.callmebot.const import (
    CONF_INTEGRATION_TYPE,
    CONF_MESSAGE_TYPE,
    CONF_RECIPIENT,
    DOMAIN,
    INTEGRATION_TELEGRAM,
)
from custom_components.callmebot.telegram import (
    MESSAGE_TYPE_CALL,
    MESSAGE_TYPE_TEXT,
    text_notify_object_id,
)
from custom_components.callmebot.telegram.api import (
    TelegramCallAPIError,
    TelegramCallAPIErrorCode,
    TelegramCallConnectionError,
    TelegramCallResult,
    TelegramTextAPIError,
    TelegramTextAPIErrorCode,
    TelegramTextConnectionError,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def _advance_to_telegram(hass: HomeAssistant) -> str:
    """Advance a config flow to its Telegram recipient form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_INTEGRATION_TYPE: INTEGRATION_TELEGRAM},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "telegram_message_type"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_MESSAGE_TYPE: MESSAGE_TYPE_TEXT},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "telegram_text"
    return result["flow_id"]


async def _advance_to_call(hass: HomeAssistant) -> dict[str, object]:
    """Advance a config flow to its Telegram Call recipient form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_INTEGRATION_TYPE: INTEGRATION_TELEGRAM}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MESSAGE_TYPE: MESSAGE_TYPE_CALL}
    )
    assert result["step_id"] == "telegram_call"
    return result


async def test_call_flow_creates_entry(hass: HomeAssistant) -> None:
    """Test Telegram Call recipient validation and entry creation."""
    result = await _advance_to_call(hass)
    with patch(
        "custom_components.callmebot.telegram.config_flow.async_validate_call_recipient",
        new=AsyncMock(return_value=TelegramCallResult.REJECTED),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_RECIPIENT: "@sample_user"}
        )
    assert result["step_id"] == "telegram_call_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Telegram Call @sample_user"
    assert result["data"][CONF_MESSAGE_TYPE] == MESSAGE_TYPE_CALL


@pytest.mark.parametrize(
    ("api_error", "expected_error"),
    [
        (
            TelegramCallConnectionError(),
            "telegram_call_cannot_connect",
        ),
        (
            TelegramCallAPIError(TelegramCallAPIErrorCode.PERMISSION_DENIED),
            "telegram_call_permission_denied",
        ),
    ],
)
async def test_call_flow_api_error(
    hass: HomeAssistant,
    api_error: Exception,
    expected_error: str,
) -> None:
    """Test Telegram Call validation errors stay on the recipient form."""
    result = await _advance_to_call(hass)

    with patch(
        "custom_components.callmebot.telegram.config_flow.async_validate_call_recipient",
        new=AsyncMock(side_effect=api_error),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_RECIPIENT: "@sample_user"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "telegram_call"
    assert result["errors"] == {"base": expected_error}


async def _advance_to_confirm(hass: HomeAssistant, recipient: str) -> str:
    """Advance a successfully validated config flow to confirmation."""
    flow_id = await _advance_to_telegram(hass)
    with patch(
        "custom_components.callmebot.telegram.config_flow.async_validate_text_recipient",
        new=AsyncMock(),
    ):
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            {CONF_RECIPIENT: recipient},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "telegram_text_confirm"
    assert result["last_step"] is True
    return result["flow_id"]


async def test_user_flow_creates_notify_entity(hass: HomeAssistant) -> None:
    """Test the complete flow and resulting notify entity."""
    recipient = "@Sample_User"
    flow_id = await _advance_to_confirm(hass, recipient)

    result = await hass.config_entries.flow.async_configure(flow_id, {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Telegram Text Message {recipient}"
    assert result["data"] == {
        CONF_INTEGRATION_TYPE: INTEGRATION_TELEGRAM,
        CONF_MESSAGE_TYPE: MESSAGE_TYPE_TEXT,
        CONF_RECIPIENT: recipient,
    }
    await hass.async_block_till_done()
    assert (
        hass.states.get("notify.callmebot_telegram_870dda90d6bc1ef5_text") is not None
    )


@pytest.mark.parametrize(
    "recipient",
    ["sample_user", "@bad!", "@abc", "+0123456789", "49123", ""],
)
async def test_invalid_recipient(
    hass: HomeAssistant,
    recipient: str,
) -> None:
    """Test invalid Telegram recipients are rejected before an API call."""
    flow_id = await _advance_to_telegram(hass)
    api_validator = AsyncMock()

    with patch(
        "custom_components.callmebot.telegram.config_flow.async_validate_text_recipient",
        new=api_validator,
    ):
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            {CONF_RECIPIENT: recipient},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "telegram_text"
    assert result["errors"] == {CONF_RECIPIENT: "telegram_text_invalid_recipient"}
    api_validator.assert_not_awaited()


async def test_api_error_is_displayed_in_full(hass: HomeAssistant) -> None:
    """Test a safe permission error code and recipient are exposed to the UI."""
    flow_id = await _advance_to_telegram(hass)

    with patch(
        "custom_components.callmebot.telegram.config_flow.async_validate_text_recipient",
        new=AsyncMock(
            side_effect=TelegramTextAPIError(TelegramTextAPIErrorCode.PERMISSION_DENIED)
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            {CONF_RECIPIENT: "@sample_user"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "telegram_text_permission_denied"}
    assert result["description_placeholders"] == {"recipient": "@sample_user"}


async def test_connection_error(hass: HomeAssistant) -> None:
    """Test a CallMeBot connection failure can be retried."""
    flow_id = await _advance_to_telegram(hass)

    with patch(
        "custom_components.callmebot.telegram.config_flow.async_validate_text_recipient",
        new=AsyncMock(side_effect=TelegramTextConnectionError),
    ):
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            {CONF_RECIPIENT: "@sample_user"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "telegram_text_cannot_connect"}


async def test_existing_entity_aborts_on_submit(hass: HomeAssistant) -> None:
    """Test submission aborts when the requested entity ID already exists."""
    recipient = "@sample_user"
    object_id = text_notify_object_id(recipient)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "notify",
        DOMAIN,
        "orphan-notify-entity",
        suggested_object_id=object_id,
    )
    flow_id = await _advance_to_confirm(hass, recipient)

    result = await hass.config_entries.flow.async_configure(flow_id, {})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "entity_already_exists"


async def test_existing_config_entry_aborts_on_submit(hass: HomeAssistant) -> None:
    """Test submission aborts when the config entry unique ID already exists."""
    recipient = "@sample_user"
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=text_notify_object_id(recipient),
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TELEGRAM,
            CONF_MESSAGE_TYPE: MESSAGE_TYPE_TEXT,
            CONF_RECIPIENT: recipient,
        },
    )
    entry.add_to_hass(hass)
    flow_id = await _advance_to_confirm(hass, recipient)

    result = await hass.config_entries.flow.async_configure(flow_id, {})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
