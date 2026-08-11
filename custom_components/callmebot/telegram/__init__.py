"""CallMeBot Telegram integration support."""

import re
from hashlib import sha256
from typing import Final

import voluptuous as vol

_USERNAME_PATTERN = re.compile(r"^@[A-Za-z][A-Za-z0-9_]{4,31}$")
_PHONE_NUMBER_PATTERN = re.compile(r"^\+[1-9][0-9]{7,14}$")
_RECIPIENT_HASH_LENGTH = 16
INVALID_RECIPIENT: Final = "invalid_recipient"

MESSAGE_TYPE_TEXT: Final = "text"
TEXT_API_URL: Final = "https://api.callmebot.com/text.php"
TEXT_VALIDATION_MESSAGE: Final = "This is a test from Callmebot"


def validate_recipient(recipient: str) -> str:
    """Validate and normalize a Telegram username or international phone number."""
    recipient = recipient.strip()
    if not (
        _USERNAME_PATTERN.fullmatch(recipient)
        or _PHONE_NUMBER_PATTERN.fullmatch(recipient)
    ):
        raise vol.Invalid(INVALID_RECIPIENT)
    return recipient


def normalize_recipient(recipient: str) -> str:
    """Normalize a Telegram recipient before hashing or comparison."""
    return re.sub(r"[^a-z0-9]+", "_", recipient.lstrip("@+").lower()).strip("_")


def recipient_hash(recipient: str) -> str:
    """Return a stable pseudonymous identifier for a Telegram recipient."""
    normalized_recipient = normalize_recipient(recipient)
    return sha256(normalized_recipient.encode()).hexdigest()[:_RECIPIENT_HASH_LENGTH]


def text_notify_object_id(recipient: str) -> str:
    """Return the deterministic Telegram Text Message entity object ID."""
    return f"callmebot_telegram_{recipient_hash(recipient)}_text"
