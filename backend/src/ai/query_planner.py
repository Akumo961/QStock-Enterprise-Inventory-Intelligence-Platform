"""Deterministic semantic query planner for common inventory questions.

The planner intentionally runs before LLM SQL generation. It converts common
English/French inventory questions into safe, explicit PostgreSQL SELECTs so
question words such as "how many", "combien", "which" and "quels" can never
be mistaken for item names.
"""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class PlannedQuery:
    sql: str
    description: str
    intent: str


_COUNT_WORDS = (
    "how many", "how much", "count", "number of", "total number",
    "combien", "quel est le nombre", "quelle est la quantite",
    "quelle quantité", "nombre total", "quantite totale", "quantité totale",
)

_UNIT_WORDS = (
    "unit", "units", "unités", "unites", "quantity", "quantité", "quantite",
    "stock", "inventory", "inventaire", "on hand", "in stock", "en stock",
)
_AVAILABLE_WORDS = (
    "available", "availability", "in stock", "on hand", "left", "disponible",
    "disponibles", "disponibilité", "disponibilite", "en stock",
)
_DISTINCT_WORDS = (
    "different", "distinct", "types of", "references", "références", "references",
    "different items", "different products", "types d'articles", "types d'items",
)


def plan_inventory_query(question: str) -> PlannedQuery | None:
    """Return a deterministic query for high-confidence aggregate/list asks."""
    text = " ".join((question or "").strip().lower().split())
    if not text:
        return None

    # Aggregations must run before generic listing/available detection.
    if _contains_any(text, _COUNT_WORDS):
        if _contains_any(text, _DISTINCT_WORDS):
            return PlannedQuery(
                sql="SELECT COUNT(*) AS item_records FROM items AS i",
                description="Number of distinct inventory item records.",
                intent="count_records",
            )

        # "How many units/items are available/in stock?" means inventory
        # quantity, not number of database rows. Use available_quantity when
        # availability is explicitly requested.
        if _contains_any(text, _AVAILABLE_WORDS):
            return PlannedQuery(
                sql="SELECT COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity, COUNT(*) AS item_records FROM items AS i",
                description="Total currently available inventory units and item records.",
                intent="sum_available_quantity",
            )

        if _contains_any(text, _UNIT_WORDS):
            return PlannedQuery(
                sql="SELECT COALESCE(SUM(i.quantity), 0) AS total_quantity, COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity, COUNT(*) AS item_records FROM items AS i",
                description="Total inventory quantity, available quantity, and item records.",
                intent="sum_quantity",
            )

        return PlannedQuery(
            sql="SELECT COUNT(*) AS item_records FROM items AS i",
            description="Number of inventory item records.",
            intent="count_records",
        )

    # Explicit total-stock questions that do not use "how many".
    if _contains_any(text, ("total stock", "total inventory", "total quantity", "stock total", "inventaire total", "stock total")):
        return PlannedQuery(
            sql="SELECT COALESCE(SUM(i.quantity), 0) AS total_quantity, COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity, COUNT(*) AS item_records FROM items AS i",
            description="Total inventory quantity, available quantity, and item records.",
            intent="sum_quantity",
        )

    # Availability listing: only list rows when the user asks to show/list,
    # not when the question is an aggregate.
    if _contains_any(text, _AVAILABLE_WORDS) and _contains_any(
        text,
        ("show", "list", "display", "which", "what", "find", "affiche", "afficher", "liste", "quels", "quelles", "montre", "montrer"),
    ):
        return PlannedQuery(
            sql="""SELECT i.id, i.name, i.item_code, i.brand, i.model, i.status,
       i.quantity, i.available_quantity, i.location
FROM items AS i
WHERE i.status = 'available' AND i.available_quantity > 0
ORDER BY i.name
LIMIT 100""",
            description="Currently available inventory items.",
            intent="list_available",
        )

    return None


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)
