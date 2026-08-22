# ruff: noqa
"""Deterministic conversational-context resolution for inventory follow-ups.

Phase 7 keeps the existing LLM pipeline intact while making short follow-up
questions explicit before intent classification and SQL planning. The
resolver only acts when the new question is clearly underspecified and a
recent turn contains a resolvable inventory item.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.ai.entity_resolver import ResolvedItem, resolve_item
from src.ai.memory import TurnMetadata


@dataclass(frozen=True)
class ResolvedFollowUp:
    original_question: str
    resolved_question: str
    item: ResolvedItem | None
    source_turn: int | None
    changed: bool


_FOLLOWUP_PATTERNS = (
    re.compile(
        r"^how many (?:do we have|are there|do you have)?\s*"
        r"(?:available|in stock|units?)?\??$",
        re.I,
    ),
    re.compile(
        r"^(?:how much|what(?:'s| is) the) (?:available|remaining|total)?\s*"
        r"(?:stock|quantity)?\??$",
        re.I,
    ),
    re.compile(
        r"^(?:are|is) (?:they|it|those|these) (?:available|in stock)\??$",
        re.I,
    ),
    re.compile(
        r"^(?:where (?:are|is)|where can i find) "
        r"(?:they|it|those|these)\??$",
        re.I,
    ),
    re.compile(
        r"^(?:what|which) (?:about|of) (?:them|it|those|these)\??$",
        re.I,
    ),
    re.compile(
        r"^(?:and|what about) (?:the )?"
        r"(?:quantity|availability|location|status)\??$",
        re.I,
    ),
    re.compile(
        r"^(?:combien|quelle quantité) (?:en|de)?\s*"
        r"(?:reste|restent|sont disponibles|est disponible)\??$",
        re.I,
    ),
    re.compile(
        r"^(?:sont-ils|sont elles|est-il|est-elle) "
        r"(?:disponibles?|en stock)\??$",
        re.I,
    ),
    re.compile(
        r"^(?:où|ou) (?:sont|est)-?(?:ils|elles|il|elle)\??$",
        re.I,
    ),
)


def resolve_follow_up(question: str, history: list[TurnMetadata]) -> ResolvedFollowUp:
    """Resolve a clearly underspecified follow-up against the latest item turn."""
    original = " ".join((question or "").strip().split())
    explicit_item = resolve_item(original) if original else None
    if explicit_item:
        return ResolvedFollowUp(original, original, explicit_item, None, False)

    if not original or not _looks_like_follow_up(original):
        return ResolvedFollowUp(original, original, None, None, False)

    for index in range(len(history) - 1, -1, -1):
        previous = history[index]
        item = resolve_item(previous.question)
        if item:
            resolved = _rewrite_follow_up(original, item.canonical_name)
            return ResolvedFollowUp(
                original, resolved, item, index, resolved != original
            )

    return ResolvedFollowUp(original, original, None, None, False)


def _looks_like_follow_up(question: str) -> bool:
    normalized = " ".join(question.lower().replace("’", "'").split())
    return any(pattern.match(normalized) for pattern in _FOLLOWUP_PATTERNS)


def _rewrite_follow_up(question: str, canonical_item: str) -> str:
    lower = question.strip().lower().replace("’", "'")

    if re.match(r"^how many", lower):
        if "available" in lower or "in stock" in lower:
            return f"How many {canonical_item} are available?"
        return f"How many {canonical_item} do we have?"

    if re.match(r"^(?:are|is) (?:they|it|those|these)", lower):
        return f"Is {canonical_item} available?"

    if re.match(r"^(?:where (?:are|is)|where can i find)", lower):
        return f"Where is {canonical_item}?"

    if re.match(r"^(?:combien|quelle quantité)", lower):
        return f"Combien de {canonical_item} sont disponibles ?"

    if re.match(r"^(?:sont-ils|sont elles|est-il|est-elle)", lower):
        return f"Le {canonical_item} est-il disponible ?"

    if re.match(r"^(?:où|ou)", lower):
        return f"Où est {canonical_item} ?"

    if "availability" in lower or "available" in lower or "stock" in lower:
        return f"Is {canonical_item} available?"
    if "location" in lower or "where" in lower:
        return f"Where is {canonical_item}?"
    if "quantity" in lower or "how much" in lower:
        return f"How many {canonical_item} do we have?"

    return f"What about {canonical_item}?"
