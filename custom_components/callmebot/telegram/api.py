"""CallMeBot Telegram API helpers."""

from __future__ import annotations

import asyncio
import random
import re
from enum import StrEnum
from html import unescape
from html.parser import HTMLParser
from http import HTTPStatus

from aiohttp import ClientError, ClientSession

from . import CALL_API_URL, TEXT_API_URL, TEXT_VALIDATION_MESSAGE

API_TIMEOUT_SECONDS_TEXT = 10
API_TIMEOUT_SECONDS_CALL = 60
API_MAX_ATTEMPTS_CALL = 2
API_RATE_LIMIT_DELAY_SECONDS_CALL = 65
API_RATE_LIMIT_JITTER_SECONDS_CALL = 1.0


class TelegramTextAPIErrorCode(StrEnum):
    """Safe error codes for Telegram Text Message API errors."""

    API_ERROR = "telegram_text_api_error"
    PERMISSION_DENIED = "telegram_text_permission_denied"


class TelegramCallResult(StrEnum):
    """Successful Telegram Call outcomes."""

    ANSWERED = "answered"
    REJECTED = "rejected"


class TelegramCallAPIErrorCode(StrEnum):
    """Safe Telegram Call API error codes."""

    API_ERROR = "telegram_call_api_error"
    PERMISSION_DENIED = "telegram_call_permission_denied"
    RATE_LIMITED = "telegram_call_rate_limited"


class TelegramCallRateLimit:
    """A parsed Telegram Call retry delay."""

    def __init__(self, retry_after: int) -> None:
        """Initialize the retry delay."""
        self.retry_after = retry_after


class TelegramTextError(Exception):
    """Base exception for the CallMeBot Telegram Text Message API."""


class TelegramTextConnectionError(TelegramTextError):
    """Raised when the Telegram Text Message API cannot be reached."""


class TelegramTextAPIError(TelegramTextError):
    """Raised when CallMeBot rejects a Telegram Text Message request."""

    def __init__(self, code: TelegramTextAPIErrorCode) -> None:
        """Initialize a safe API error code."""
        super().__init__(code)
        self.code = code


class TelegramCallError(Exception):
    """Base exception for the CallMeBot Telegram Call API."""


class TelegramCallConnectionError(TelegramCallError):
    """Raised when the Telegram Call API cannot be reached."""


class TelegramCallAPIError(TelegramCallError):
    """Raised when CallMeBot rejects a Telegram Call request."""

    def __init__(self, code: TelegramCallAPIErrorCode) -> None:
        """Initialize a safe API error code."""
        super().__init__(code)
        self.code = code


class _ResponseTextParser(HTMLParser):
    """Convert the small CallMeBot Telegram HTML response into readable Markdown."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._link: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle relevant HTML start tags."""
        if tag in {"br", "p", "div"}:
            self._parts.append("\n")
        elif tag in {"b", "strong"}:
            self._parts.append("**")
        elif tag == "a":
            self._link = dict(attrs).get("href")
            self._parts.append("[")

    def handle_endtag(self, tag: str) -> None:
        """Handle relevant HTML end tags."""
        if tag in {"p", "div"}:
            self._parts.append("\n")
        elif tag in {"b", "strong"}:
            self._parts.append("**")
        elif tag == "a":
            self._parts.append(f"]({self._link})" if self._link else "]")
            self._link = None

    def handle_data(self, data: str) -> None:
        """Retain response text."""
        self._parts.append(data)

    def markdown(self) -> str:
        """Return normalized Markdown without losing response lines."""
        text = unescape("".join(self._parts)).replace("\r\n", "\n")
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line).strip()


def format_api_response(response: str) -> str:
    """Format a CallMeBot Telegram HTML or plain-text response."""
    parser = _ResponseTextParser()
    parser.feed(response)
    return parser.markdown()


def is_successful_response(status: int, response: str) -> bool:
    """Return whether CallMeBot accepted the Telegram validation message."""
    if status >= HTTPStatus.BAD_REQUEST:
        return False

    formatted_response = format_api_response(response)
    if re.search(
        r"(?:permission denied|(?:^|\n)\s*(?:\*\*)?error:)",
        formatted_response,
        flags=re.IGNORECASE,
    ):
        return False

    if re.search(
        r"(?:^|\n)\s*status:\s*successful\s*(?:$|\n)",
        formatted_response,
        flags=re.IGNORECASE,
    ):
        return True

    telegram_codes = re.findall(
        r"telegram error code:\s*(\d+)",
        formatted_response,
        flags=re.IGNORECASE,
    )
    return bool(telegram_codes) and all(code == "200" for code in telegram_codes)


async def async_send_text_message(
    session: ClientSession,
    recipient: str,
    message: str,
) -> None:
    """Send a Telegram Text Message and raise when CallMeBot rejects it."""
    try:
        async with asyncio.timeout(API_TIMEOUT_SECONDS_TEXT):
            async with session.get(
                TEXT_API_URL,
                params={"user": recipient, "text": message},
            ) as response:
                response_text = await response.text()
                status = response.status
    except (TimeoutError, ClientError) as err:
        raise TelegramTextConnectionError from err

    if not is_successful_response(status, response_text):
        formatted_response = format_api_response(response_text)
        code = (
            TelegramTextAPIErrorCode.PERMISSION_DENIED
            if re.search("permission denied", formatted_response, flags=re.IGNORECASE)
            else TelegramTextAPIErrorCode.API_ERROR
        )
        raise TelegramTextAPIError(code)


async def async_validate_text_recipient(session: ClientSession, recipient: str) -> None:
    """Send a Telegram Text Message test and raise when CallMeBot rejects it."""
    await async_send_text_message(session, recipient, TEXT_VALIDATION_MESSAGE)


def parse_call_response(
    response: str,
) -> TelegramCallResult | TelegramCallAPIErrorCode | TelegramCallRateLimit:
    """Classify a CallMeBot Telegram Call response."""
    response = format_api_response(response)
    if re.search(r"two calls to the same user", response, re.IGNORECASE):
        rate_limit = re.search(r"within\s+(\d+)\s+seconds", response, re.IGNORECASE)
        retry_after = (
            int(rate_limit.group(1))
            if rate_limit is not None
            else API_RATE_LIMIT_DELAY_SECONDS_CALL
        )
        return TelegramCallRateLimit(retry_after)
    if re.search(
        r"authorization .* not (?:received|authorized)", response, re.IGNORECASE
    ):
        return TelegramCallAPIErrorCode.PERMISSION_DENIED
    if re.search(r"result:\s*call rejected by user", response, re.IGNORECASE):
        return TelegramCallResult.REJECTED
    if re.search(
        r"result:\s*call answered and ended by the user", response, re.IGNORECASE
    ):
        return TelegramCallResult.ANSWERED
    return TelegramCallAPIErrorCode.API_ERROR


async def async_send_call(
    session: ClientSession,
    recipient: str,
    text: str,
    *,
    max_attempts: int = API_MAX_ATTEMPTS_CALL,
) -> TelegramCallResult:
    """Start a Telegram Call, retrying rate limits up to the attempt limit."""
    if max_attempts < 1:
        msg = "max_attempts must be at least 1"
        raise ValueError(msg)

    attempt = 1
    while True:
        try:
            async with asyncio.timeout(API_TIMEOUT_SECONDS_CALL):
                async with session.get(
                    CALL_API_URL,
                    params={"user": recipient, "text": text, "cc": "no"},
                ) as response:
                    response_text = await response.text()
        except (TimeoutError, ClientError) as err:
            raise TelegramCallConnectionError from err
        result = parse_call_response(response_text)
        if isinstance(result, TelegramCallResult):
            return result
        if isinstance(result, TelegramCallRateLimit):
            if attempt < max_attempts:
                jitter = random.uniform(  # noqa: S311
                    0,
                    API_RATE_LIMIT_JITTER_SECONDS_CALL,
                )
                await asyncio.sleep(result.retry_after + jitter)
                attempt += 1
                continue
            raise TelegramCallAPIError(TelegramCallAPIErrorCode.RATE_LIMITED)
        raise TelegramCallAPIError(result)


async def async_validate_call_recipient(
    session: ClientSession, recipient: str
) -> TelegramCallResult:
    """Start a Telegram test call to validate a recipient."""
    return await async_send_call(session, recipient, TEXT_VALIDATION_MESSAGE)
