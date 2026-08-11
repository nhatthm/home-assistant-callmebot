"""Unit tests for the CallMeBot Telegram API."""

import logging
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, call, patch

import pytest
from aiohttp import ClientError

from custom_components.callmebot.telegram import (
    CALL_API_URL,
    TEXT_API_URL,
    TEXT_VALIDATION_MESSAGE,
)
from custom_components.callmebot.telegram.api import (
    API_RATE_LIMIT_DELAY_SECONDS_CALL,
    TelegramCallAPIError,
    TelegramCallAPIErrorCode,
    TelegramCallConnectionError,
    TelegramCallRateLimit,
    TelegramCallResult,
    TelegramTextAPIError,
    TelegramTextAPIErrorCode,
    TelegramTextConnectionError,
    async_send_call,
    async_send_text_message,
    async_validate_call_recipient,
    async_validate_text_recipient,
    format_api_response,
    is_successful_response,
    parse_call_response,
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

FORMATTED_ERROR_RESPONSE = """User: sample_user
Text: This is a test from Callmebot
HTML format: no
Preview Links: no
**Error: Permission denied for sample_user.**
**Click** [**here**](https://api2.callmebot.com/txt/login.php)
**to Authenticate sample_user and then try again.**
Telegram Error Code: 400"""

SUCCESS_RESPONSE = """User: sample_user
Text: This is a test from Callmebot
HTML format: no
Preview Links: no

Name: Sample User
Status: Successful"""

CALL_ANSWERED_RESPONSE = """Autorization OK
Script started!
Script ended before Timeout.
Result: Call answered and ended by the user
End.-"""
CALL_REJECTED_RESPONSE = CALL_ANSWERED_RESPONSE.replace(
    "answered and ended by the user", "Rejected by user"
)
CALL_RATE_LIMIT_RESPONSE = """ERROR: Two calls to the same user (@sample_user)
within 42 seconds is not allowed."""


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


class _SequentialSession(_Session):
    """Minimal session double returning responses in order."""

    def __init__(self, responses: list[_Response]) -> None:
        super().__init__()
        self.responses = responses

    def get(self, url: str, *, params: dict[str, str]) -> _RequestContext:
        """Record a request and return the next response."""
        self.calls.append((url, params))
        return _RequestContext(self.responses.pop(0))


def test_format_api_error_response() -> None:
    """Test HTML errors retain all content and a clickable authentication link."""
    assert format_api_response(ERROR_RESPONSE) == FORMATTED_ERROR_RESPONSE


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


async def test_send_text_message_success() -> None:
    """Test sending the supplied Telegram text message."""
    session = _Session(_Response(200, SUCCESS_RESPONSE))

    await async_send_text_message(
        session,  # type: ignore[arg-type]
        "@sample_user",
        "Actual notification",
    )

    assert session.calls == [
        (
            TEXT_API_URL,
            {"user": "@sample_user", "text": "Actual notification"},
        )
    ]


async def test_validate_recipient_rejection() -> None:
    """Test an API rejection includes the complete formatted response."""
    session = _Session(_Response(400, ERROR_RESPONSE))

    with pytest.raises(TelegramTextAPIError) as error:
        await async_validate_text_recipient(
            session,
            "@sample_user",  # type: ignore[arg-type]
        )

    assert error.value.code is TelegramTextAPIErrorCode.PERMISSION_DENIED


async def test_validate_recipient_unknown_rejection() -> None:
    """Test an unknown API response only exposes a safe error code."""
    session = _Session(_Response(400, "Unexpected **untrusted** response"))

    with pytest.raises(TelegramTextAPIError) as error:
        await async_validate_text_recipient(
            session,
            "@sample_user",  # type: ignore[arg-type]
        )

    assert error.value.code is TelegramTextAPIErrorCode.API_ERROR
    assert "untrusted" not in str(error.value)


async def test_validate_recipient_connection_error() -> None:
    """Test client errors are exposed as integration connection failures."""
    session = _Session()

    with pytest.raises(TelegramTextConnectionError):
        await async_validate_text_recipient(
            session,
            "@sample_user",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (CALL_ANSWERED_RESPONSE, TelegramCallResult.ANSWERED),
        (CALL_REJECTED_RESPONSE, TelegramCallResult.REJECTED),
        (
            "Authorization for user @sample_user is not received.",
            TelegramCallAPIErrorCode.PERMISSION_DENIED,
        ),
        ("Unknown response", TelegramCallAPIErrorCode.API_ERROR),
    ],
)
def test_parse_call_response(
    response: str,
    expected: TelegramCallResult | TelegramCallAPIErrorCode,
) -> None:
    """Test Telegram Call response classification."""
    assert parse_call_response(response) is expected


async def test_send_call_uses_supported_parameters() -> None:
    """Test Telegram Call sends only user, text, and disabled carbon copy."""
    session = _Session(_Response(200, CALL_ANSWERED_RESPONSE))

    assert (
        await async_send_call(
            session,  # type: ignore[arg-type]
            "@sample_user",
            "Voice message",
        )
        is TelegramCallResult.ANSWERED
    )
    assert session.calls == [
        (
            CALL_API_URL,
            {"user": "@sample_user", "text": "Voice message", "cc": "no"},
        )
    ]


async def test_validate_call_recipient_uses_validation_message() -> None:
    """Test Telegram Call validation uses the shared validation message."""
    session = _Session(_Response(200, CALL_ANSWERED_RESPONSE))

    result = await async_validate_call_recipient(
        session,  # type: ignore[arg-type]
        "@sample_user",
    )

    assert result is TelegramCallResult.ANSWERED
    assert session.calls == [
        (
            CALL_API_URL,
            {"user": "@sample_user", "text": TEXT_VALIDATION_MESSAGE, "cc": "no"},
        )
    ]


async def test_send_call_uses_configured_attempts_and_jitter() -> None:
    """Test call retries use the attempt limit, parsed delay, and jitter."""
    session = _Session(_Response(200, CALL_RATE_LIMIT_RESPONSE))

    with (
        patch(
            "custom_components.callmebot.telegram.api.asyncio.sleep",
            new=AsyncMock(),
        ) as sleep,
        patch(
            "custom_components.callmebot.telegram.api.random.uniform",
            return_value=0.25,
        ) as jitter,
        pytest.raises(TelegramCallAPIError) as error,
    ):
        await async_send_call(
            session,  # type: ignore[arg-type]
            "@sample_user",
            "Voice message",
            max_attempts=3,
        )

    assert sleep.await_args_list == [call(42.25), call(42.25)]
    assert jitter.call_count == 2
    assert error.value.code is TelegramCallAPIErrorCode.RATE_LIMITED
    assert len(session.calls) == 3


async def test_send_call_waits_before_successful_retry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test a rate-limited call waits before a successful retry."""
    session = _SequentialSession(
        [
            _Response(200, CALL_RATE_LIMIT_RESPONSE),
            _Response(200, CALL_ANSWERED_RESPONSE),
        ]
    )

    with (
        patch(
            "custom_components.callmebot.telegram.api.asyncio.sleep",
            new=AsyncMock(),
        ) as sleep,
        patch(
            "custom_components.callmebot.telegram.api.random.uniform",
            return_value=0.5,
        ),
        caplog.at_level(logging.WARNING),
    ):
        result = await async_send_call(
            session,  # type: ignore[arg-type]
            "@sample_user",
            "Voice message",
        )

    assert result is TelegramCallResult.ANSWERED
    sleep.assert_awaited_once_with(42.5)
    assert len(session.calls) == 2
    assert (
        "Telegram Call rate limited for @sample_user; retrying in 42.50 seconds "
        "(attempt 2/2)"
    ) in caplog.messages


@pytest.mark.parametrize(
    ("response", "expected_code"),
    [
        (
            "Authorization for user @sample_user is not received.",
            TelegramCallAPIErrorCode.PERMISSION_DENIED,
        ),
        ("Unexpected response", TelegramCallAPIErrorCode.API_ERROR),
    ],
)
async def test_send_call_api_error(
    response: str,
    expected_code: TelegramCallAPIErrorCode,
) -> None:
    """Test Telegram Call failures expose only safe error codes."""
    session = _Session(_Response(200, response))

    with pytest.raises(TelegramCallAPIError) as error:
        await async_send_call(
            session,  # type: ignore[arg-type]
            "@sample_user",
            "Voice message",
        )

    assert error.value.code is expected_code
    assert error.value.response == response
    assert "Unexpected response" not in str(error.value)


async def test_send_call_connection_error() -> None:
    """Test Telegram Call connection errors use the dedicated exception."""
    session = _Session()

    with pytest.raises(TelegramCallConnectionError):
        await async_send_call(
            session,  # type: ignore[arg-type]
            "@sample_user",
            "Voice message",
        )


def test_parse_call_rate_limit_delay() -> None:
    """Test the retry delay is parsed instead of hard-coded."""
    result = parse_call_response(CALL_RATE_LIMIT_RESPONSE)
    assert isinstance(result, TelegramCallRateLimit)
    assert result.retry_after == 42


def test_parse_call_rate_limit_uses_default_delay() -> None:
    """Test a rate limit without a duration uses the safe default delay."""
    result = parse_call_response("ERROR: Two calls to the same user are not allowed.")
    assert isinstance(result, TelegramCallRateLimit)
    assert result.retry_after == API_RATE_LIMIT_DELAY_SECONDS_CALL


async def test_send_call_rejects_invalid_attempt_limit() -> None:
    """Test the configured call attempt limit must allow at least one request."""
    session = _Session(_Response(200, CALL_ANSWERED_RESPONSE))

    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        await async_send_call(
            session,  # type: ignore[arg-type]
            "@sample_user",
            "Voice message",
            max_attempts=0,
        )

    assert session.calls == []
