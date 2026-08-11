"""CallMeBot Telegram API helpers."""

from __future__ import annotations

import asyncio
import re
from html import unescape
from html.parser import HTMLParser
from http import HTTPStatus

from aiohttp import ClientError, ClientSession

from . import TEXT_API_URL, TEXT_VALIDATION_MESSAGE

API_TIMEOUT_SECONDS = 10


class CallMeBotTelegramTextError(Exception):
    """Base exception for CallMeBot Telegram Text Message API validation."""


class CallMeBotTelegramTextConnectionError(CallMeBotTelegramTextError):
    """Raised when the Telegram Text Message API cannot be reached."""


class CallMeBotTelegramTextValidationError(CallMeBotTelegramTextError):
    """Raised when CallMeBot rejects a Telegram Text Message recipient."""


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


async def async_validate_text_recipient(session: ClientSession, recipient: str) -> None:
    """Send a Telegram Text Message test and raise when CallMeBot rejects it."""
    try:
        async with asyncio.timeout(API_TIMEOUT_SECONDS):
            async with session.get(
                TEXT_API_URL,
                params={"user": recipient, "text": TEXT_VALIDATION_MESSAGE},
            ) as response:
                response_text = await response.text()
                status = response.status
    except (TimeoutError, ClientError) as err:
        raise CallMeBotTelegramTextConnectionError from err

    if not is_successful_response(status, response_text):
        raise CallMeBotTelegramTextValidationError(format_api_response(response_text))
