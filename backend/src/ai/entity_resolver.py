"""Inventory item entity resolution for the QStock assistant.

This module is deliberately deterministic and dependency-free. It resolves
common bilingual user-facing names to the canonical inventory names used by
QStock, while also extracting explicit item phrases for names that are already
stored in the user's language.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class ResolvedItem:
    """Resolved inventory entity."""

    canonical_name: str
    matched_text: str
    source: str


_ITEM_ALIASES: dict[str, tuple[str, ...]] = {
    "Ciseaux": (
        "ciseaux", "scissors", "pair of scissors", "pairs of scissors",
    ),
    "Crayon à mine": (
        "crayon à mine", "crayon a mine", "crayons à mine", "crayons a mine",
        "pencil", "pencils", "lead pencil", "lead pencils",
    ),
    "Crayons de couleur en bois": (
        "crayons de couleur en bois", "crayon de couleur en bois",
        "wooden colored pencils", "wooden colour pencils", "colored pencils",
        "colour pencils",
    ),
    "Crayons de couleurs feutre": (
        "crayons de couleurs feutre", "crayon de couleurs feutre",
        "felt crayons", "felt tip crayons", "felt-tip crayons",
    ),
    "Marqueur pour tableau": (
        "marqueur pour tableau", "marqueurs pour tableau", "whiteboard marker",
        "whiteboard markers", "board marker", "board markers",
    ),
    "Projecteur": (
        "projecteur", "projecteurs", "projector", "projectors",
        "video projector", "video projectors",
    ),
    "Stylos": (
        "stylo", "stylos", "pen", "pens", "ballpoint", "ballpoint pen",
        "ballpoint pens",
    ),
}

_GENERIC_ITEM_WORDS = {
    "all", "our", "my", "the", "they", "them", "their", "it", "its", "this",
    "that", "these", "those", "ones", "we", "items", "item", "products",
    "product", "articles", "article", "inventory", "stock", "units", "unit",
    "quantity", "quantities", "quantite", "quantites", "available", "currently",
    "right", "now", "things", "everything", "located", "tout", "tous", "toutes",
    "nos", "inventaire", "unites", "unité", "unités",
}


def normalize_text(value: str) -> str:
    """Normalize accents, punctuation, whitespace and case for matching."""
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def resolve_item(question: str) -> ResolvedItem | None:
    """Resolve an item entity from a natural-language inventory question.

    Alias matching handles bilingual English/French questions even when the
    database stores only the French canonical name. If no alias matches, an
    explicit item phrase is returned as-is so SQL can search for a real name
    without inventing a translation.
    """
    normalized = normalize_text(question)
    if not normalized:
        return None

    aliases: list[tuple[str, str]] = []
    for canonical, values in _ITEM_ALIASES.items():
        aliases.append((normalize_text(canonical), canonical))
        aliases.extend((normalize_text(alias), canonical) for alias in values)

    for alias, canonical in sorted(aliases, key=lambda pair: len(pair[0]), reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", normalized):
            source = "alias" if normalize_text(canonical) != alias else "canonical"
            return ResolvedItem(canonical, alias, source)

    candidate = _extract_explicit_item_phrase(normalized)
    if candidate:
        return ResolvedItem(candidate, candidate, "explicit")
    return None


def aliases_for_tests() -> dict[str, tuple[str, ...]]:
    """Return a copy of the supported alias dictionary for tests/tooling."""
    return {key: tuple(values) for key, values in _ITEM_ALIASES.items()}


def _extract_explicit_item_phrase(text: str) -> str:
    """Extract a subject from common item-specific question forms."""
    patterns = (
        r"^how many (.+?) (?:do|did) (?:we|i) have(?:\s+in stock)?$",
        r"^how many (.+?) (?:are|is) available$",
        r"^where (?:is|are) (?:the )?(.+?)$",
        r"^(?:do|does) (?:we|you) have (?:any )?(?:the )?(.+?)$",
        r"^(?:are|is) (?:the )?(.+?) available$",
        r"^(?:show|list|display) (?:me )?(?:the )?(.+?)(?:\s+available)?$",
        r"^combien (?:de |d')(.+?) (?:avons-nous|avons nous|avons)\b.*$",
        r"^combien (?:de |d')(.+?) (?:sont|est) disponible(?:s)?$",
        r"^(?:ou|où) (?:est|sont) (?:le |la |les )?(.+?)$",
        r"^(?:avons-nous|avons nous) (?:des |du |de la |de l')?(.+?)\??$",
    )
    for pattern in patterns:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = _clean_candidate(match.group(1).strip(" ?.,!;:"))
        if candidate:
            return candidate
    return ""


def _clean_candidate(candidate: str) -> str:
    words = candidate.split()
    if not words or any(word in _GENERIC_ITEM_WORDS for word in words):
        return ""
    return " ".join(words).strip()
