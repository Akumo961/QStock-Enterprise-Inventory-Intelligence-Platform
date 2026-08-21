"""Input/output safety policy for the QStock AI assistant.

The policy keeps request normalization, conservative limits, and prompt-injection
classification outside the LLM orchestration code. User text is untrusted input;
application instructions and retrieved data remain authoritative.
"""

import re

MAX_MESSAGE_LENGTH = 2000
_MAX_WHITESPACE_RUN = re.compile(r"[ \t\r\n]+")

# High-signal injection phrases. This is intentionally conservative: detection
# is a safety signal, not a claim that every matching message is malicious.
_PROMPT_INJECTION_RE = re.compile(
    r"(?:"
    r"ignore|disregard|forget|override|bypass|reveal|show|print|leak"
    r").{0,80}(?:previous|prior|above|system|developer|instructions?|prompt|rules?|secret|password|api key|token)"
    r"|(?:system prompt|developer message|hidden instructions?|internal prompt)"
    r"|(?:ignore|disregard|oublie|ignorez|contourne).{0,80}(?:instructions?|r[eè]gles?|prompt|syst[eè]me)",
    re.IGNORECASE | re.DOTALL,
)


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


def looks_like_prompt_injection(message: str) -> bool:
    """Return True for high-signal attempts to override model instructions."""
    return bool(_PROMPT_INJECTION_RE.search(normalize_user_message(message)))


def safety_message(language: str = "en") -> str:
    """User-facing response for an instruction-override attempt."""
    if language == "fr":
        return "Je peux vous aider avec l'inventaire et l'utilisation de QStock, mais je ne peux pas divulguer les instructions internes, secrets ou données protégées."
    return "I can help with QStock inventory and usage, but I can't disclose internal instructions, secrets, or protected data."

