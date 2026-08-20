"""Input/output safety policy for the QStock AI assistant.

This module keeps request normalization and conservative limits outside the
LLM orchestration code. The goal is to make the chat boundary predictable:
large or whitespace-only inputs are rejected, and user-visible text is
normalized without changing its meaning.
"""

import re

MAX_MESSAGE_LENGTH = 2000
_MAX_WHITESPACE_RUN = re.compile(r"[ \t\r\n]+")


def normalize_user_message(message: str) -> str:
    """Normalize user text while preserving its semantic content."""
    return _MAX_WHITESPACE_RUN.sub(" ", (message or "").strip())


def validate_user_message(message: str) -> str:
    """Return normalized text or raise ValueError for invalid input."""
    normalized = normalize_user_message(message)
    if not normalized:
        raise ValueError("Message cannot be empty.")
    if len(normalized) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"Message exceeds the {MAX_MESSAGE_LENGTH}-character limit.")
    return normalized
