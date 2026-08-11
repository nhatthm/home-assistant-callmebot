"""Unit tests for the CallMeBot Telegram API."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError

from custom_components.callmebot.telegram import (
    TEXT_API_URL,
    TEXT_VALIDATION_MESSAGE,
)
from custom_components.callmebot.telegram.api import (
    CallMeBotTelegramTextConnectionError,
    CallMeBotTelegramTextValidationError,
    async_validate_text_recipient,
    format_api_response,
    is_successful_response,
)

if TYPE_CHECKING:
    from types import TracebackType

ERROR_RESPONSE = """User: sample_user<br>
Text: This is a test from Callmebot<br>
HTML format: no<br>
Preview Links: no<br><br>
<b>Error: Permission denied for sample_user.</b><br>
<b>Click</b> <a href="https://api2.callmebot.com/txt/login.php"><b>here</b></a>
<b>to Authenticate sample_user and then try again.</b><br><br>
Telegram Error Code: 400"""

SUCCESS_RESPONSE = """User: sample_user
Text: This is a test from Callmebot
HTML format: no
Preview Links: no

Name: Sample User
Status: Successful"""


class _Response:
    """Minimal aiohttp response double."""

    def __init__(self, status: int, text: str) -> None:
        self.status = status
        self.text = AsyncMock(return_value=text)


class _RequestContext:
    """Minimal aiohttp request context double."""

    def __init__(self, response: _Response) -> None:
        self.response = response

    async def __aenter__(self) -> _Response:
        """Return the response."""
        return self.response

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the request context."""


class _Session:
    """Minimal aiohttp session double."""

    def __init__(self, response: _Response | None = None) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, url: str, *, params: dict[str, str]) -> _RequestContext:
        """Record and return a request context."""
        self.calls.append((url, params))
        if self.response is None:
            raise ClientError
        return _RequestContext(self.response)


def test_format_api_error_response() -> None:
    """Test HTML errors retain all content and a clickable authentication link."""
    formatted = format_api_response(ERROR_RESPONSE)

    assert "User: sample_user" in formatted
    assert "Text: This is a test from Callmebot" in formatted
    assert "HTML format: no" in formatted
    assert "Preview Links: no" in formatted
    assert "**Error: Permission denied for sample_user.**" in formatted
    assert "[**here**](https://api2.callmebot.com/txt/login.php)" in formatted
    assert "Telegram Error Code: 400" in formatted


def test_format_plain_link_without_href() -> None:
    """Test paragraphs, unknown tags, and links without targets remain readable."""
    assert format_api_response("<p>First</p><a>Click</a><span>tail</span>") == (
        "First\n[Click]tail"
    )


@pytest.mark.parametrize(
    ("status", "response", "expected"),
    [
        (200, SUCCESS_RESPONSE, 1),
        (200, "Message sent successfully\nTelegram Error Code: 200", 1),
        (200, "Unknown response", 0),
        (200, ERROR_RESPONSE, 0),
        (400, ERROR_RESPONSE, 0),
        (500, "Internal server error", 0),
    ],
)
def test_successful_response(status: int, response: str, expected: int) -> None:
    """Test CallMeBot response classification."""
    assert is_successful_response(status, response) is bool(expected)


async def test_validate_recipient_success() -> None:
    """Test a successful validation API request."""
    session = _Session(_Response(200, SUCCESS_RESPONSE))

    await async_validate_text_recipient(
        session,
        "@sample_user",  # type: ignore[arg-type]
    )

    assert session.calls == [
        (
            TEXT_API_URL,
            {"user": "@sample_user", "text": TEXT_VALIDATION_MESSAGE},
        )
    ]


async def test_validate_recipient_rejection() -> None:
    """Test an API rejection includes the complete formatted response."""
    session = _Session(_Response(400, ERROR_RESPONSE))

    with pytest.raises(CallMeBotTelegramTextValidationError) as error:
        await async_validate_text_recipient(
            session,
            "@sample_user",  # type: ignore[arg-type]
        )

    assert "Permission denied" in str(error.value)
    assert "[**here**](https://api2.callmebot.com/txt/login.php)" in str(error.value)


async def test_validate_recipient_connection_error() -> None:
    """Test client errors are exposed as integration connection failures."""
    session = _Session()

    with pytest.raises(CallMeBotTelegramTextConnectionError):
        await async_validate_text_recipient(
            session,
            "@sample_user",  # type: ignore[arg-type]
        )
