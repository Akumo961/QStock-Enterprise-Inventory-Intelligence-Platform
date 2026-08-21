"""Deterministic SQL templates for location-scoped inventory questions.

Kept separate from the broader template registry so location extraction can
be evaluated and extended without making generic availability matching win
before a requested location is considered.
"""

from __future__ import annotations

import re

from src.ai.query_templates import TemplateSQL


_LOCATION_RE = re.compile(
    r"\b(?:in|at|dans|à|a)\s+"
    r"(?:(?:location|building|room|emplacement|bâtiment|batiment|salle)\s*)?"
    r"[:\-]?\s*([A-Za-z0-9]+)\b",
    flags=re.IGNORECASE,
)

_STOP_LOCATIONS = frozenset(
    {
        "stock",
        "the",
        "this",
        "that",
        "inventory",
        "maintenance",
        "available",
        "borrowed",
        "retired",
        "overdue",
    }
)

_AVAILABLE_TERMS = (
    "available",
    "availability",
    "in stock",
    "left",
    "disponible",
    "disponibles",
    "disponibilité",
    "disponibilite",
    "en stock",
)

_COUNT_TERMS = (
    "how many",
    "count",
    "number of",
    "combien",
    "nombre de",
    "nombre total",
)

_LIST_TERMS = (
    "show",
    "list",
    "display",
    "which",
    "what",
    "find",
    "search",
    "affiche",
    "afficher",
    "liste",
    "lister",
    "quels",
    "quelles",
    "montre",
    "montrer",
    "trouve",
    "trouver",
    "recherche",
    "rechercher",
)

_MAINTENANCE_TERMS = ("maintenance", "under maintenance", "en maintenance")
_BORROWED_TERMS = ("borrowed", "emprunté", "emprunte", "empruntés", "empruntes")
_RETIRED_TERMS = ("retired", "retiré", "retire", "retirés", "retires")


def maybe_build_location_template_sql(question: str) -> TemplateSQL | None:
    """Return safe SQL when the question explicitly names a location."""
    text = _extract_question(question).lower()
    location = _extract_location(text)
    if not location:
        return None

    location_sql = _escape_literal(location)
    location_filter = f"LOWER(i.location) = LOWER('{location_sql}')"

    if _contains_any(text, _COUNT_TERMS):
        if _contains_any(text, _AVAILABLE_TERMS):
            return TemplateSQL(
                sql=f"""SELECT COUNT(*) AS item_records,
       COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity
FROM items AS i
WHERE i.available_quantity > 0
  AND {location_filter}""",
                description=f"Available inventory in {location}.",
            )
        if _contains_any(text, _MAINTENANCE_TERMS):
            return TemplateSQL(
                sql=f"""SELECT COUNT(*) AS maintenance_item_records,
       COALESCE(SUM(i.quantity), 0) AS maintenance_total_quantity
FROM items AS i
WHERE i.status = 'maintenance'
  AND {location_filter}""",
                description=f"Inventory under maintenance in {location}.",
            )
        if _contains_any(text, _BORROWED_TERMS):
            return TemplateSQL(
                sql=f"""SELECT COUNT(*) AS borrowed_item_records,
       COALESCE(SUM(i.quantity - i.available_quantity), 0) AS borrowed_total_quantity
FROM items AS i
WHERE i.status = 'borrowed'
  AND {location_filter}""",
                description=f"Borrowed inventory in {location}.",
            )
        if _contains_any(text, _RETIRED_TERMS):
            return TemplateSQL(
                sql=f"""SELECT COUNT(*) AS retired_item_records,
       COALESCE(SUM(i.quantity), 0) AS retired_total_quantity
FROM items AS i
WHERE i.status = 'retired'
  AND {location_filter}""",
                description=f"Retired inventory in {location}.",
            )
        return TemplateSQL(
            sql=f"""SELECT COUNT(*) AS item_records,
       COALESCE(SUM(i.quantity), 0) AS total_quantity,
       COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity
FROM items AS i
WHERE {location_filter}""",
            description=f"Inventory in {location}.",
        )

    if _contains_any(text, _MAINTENANCE_TERMS):
        status_filter = "i.status = 'maintenance'"
    elif _contains_any(text, _BORROWED_TERMS):
        status_filter = "i.status = 'borrowed'"
    elif _contains_any(text, _RETIRED_TERMS):
        status_filter = "i.status = 'retired'"
    elif _contains_any(text, _AVAILABLE_TERMS):
        status_filter = "i.status = 'available' AND i.available_quantity > 0"
    else:
        status_filter = ""

    if _contains_any(text, _LIST_TERMS) or status_filter:
        where = location_filter
        if status_filter:
            where += f"\n  AND {status_filter}"
        return TemplateSQL(
            sql=f"""SELECT i.id, i.name, i.item_code, i.brand, i.model, i.status,
       i.quantity, i.available_quantity, i.location
FROM items AS i
WHERE {where}
ORDER BY i.name
LIMIT 100""",
            description=(
                f"Available inventory items in {location}."
                if _contains_any(text, _AVAILABLE_TERMS)
                else f"Inventory items in {location}."
            ),
        )

    return None


def _extract_question(question: str) -> str:
    match = re.search(r"User Question:\s*(.+)", question or "", flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else (question or "").strip()


def _extract_location(text: str) -> str:
    match = _LOCATION_RE.search(text)
    if not match:
        return ""
    candidate = match.group(1).strip()
    if candidate.lower() in _STOP_LOCATIONS:
        return ""
    return candidate


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _escape_literal(value: str) -> str:
    return (value or "").replace("'", "''")
