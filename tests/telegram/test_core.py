"""Unit tests for core CallMeBot Telegram behavior."""

import pytest
import voluptuous as vol

from custom_components.callmebot.telegram import (
    normalize_recipient,
    recipient_hash,
    text_notify_object_id,
    validate_recipient,
)


@pytest.mark.parametrize("recipient", ["@valid_user", "+491234567890"])
def test_valid_recipient(recipient: str) -> None:
    """Test supported Telegram recipient formats."""
    assert validate_recipient(f" {recipient} ") == recipient


@pytest.mark.parametrize(
    "recipient",
    ["sample_user", "@bad!", "@abc", "+0123456789", "49123", ""],
)
def test_invalid_recipient(recipient: str) -> None:
    """Test unsupported Telegram recipient formats."""
    with pytest.raises(vol.Invalid, match="invalid_recipient"):
        validate_recipient(recipient)


def test_recipient_normalization() -> None:
    """Test deterministic Telegram recipient normalization."""
    assert normalize_recipient("@User_Name") == "user_name"


def test_recipient_hash_is_stable_and_case_insensitive() -> None:
    """Test recipient hashes are stable without exposing the recipient."""
    assert recipient_hash("@Sample_User") == "870dda90d6bc1ef5"
    assert recipient_hash("@sample_user") == "870dda90d6bc1ef5"


def test_text_notify_object_id() -> None:
    """Test deterministic Telegram Text Message entity ID generation."""
    assert text_notify_object_id("+491234567890") == (
        "callmebot_telegram_b0492275843c1559_text"
    )
