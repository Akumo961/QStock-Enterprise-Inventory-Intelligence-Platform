"""Deterministic semantic query planner for common inventory questions.

Runs before LLM SQL generation. High-confidence English/French questions are
converted into safe PostgreSQL SELECTs so question words can never become
item-name filters.
"""

from dataclasses import dataclass


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

_STATS_SQL = """SELECT COUNT(*) AS item_records,
       COALESCE(SUM(i.quantity), 0) AS total_quantity,
       COALESCE(SUM(i.available_quantity), 0) AS available_quantity,
       COALESCE(SUM(i.quantity - i.available_quantity), 0) AS unavailable_quantity,
       COUNT(*) FILTER (WHERE i.status = 'available') AS available_records,
       COUNT(*) FILTER (WHERE i.status = 'borrowed') AS borrowed_records,
       COUNT(*) FILTER (WHERE i.status = 'maintenance') AS maintenance_records,
       COUNT(*) FILTER (WHERE i.status = 'retired') AS retired_records
FROM items AS i"""


def plan_inventory_query(question: str) -> PlannedQuery | None:
    """Return a deterministic query for high-confidence aggregate/list asks."""
    text = " ".join((question or "").strip().lower().split())
    if not text:
        return None

    # Always resolve aggregation before generic listing/availability rules.
    # The result deliberately uses QStock's existing statistics shape so the
    # current deterministic answer path can handle it without another LLM call.
    if _contains_any(text, _COUNT_WORDS):
        if _contains_any(text, _DISTINCT_WORDS):
            return PlannedQuery(
                sql=_STATS_SQL,
                description="Inventory statistics including the number of item records.",
                intent="count_records",
            )

        if _contains_any(text, _AVAILABLE_WORDS):
            return PlannedQuery(
                sql=_STATS_SQL,
                description="Inventory statistics including currently available quantity.",
                intent="sum_available_quantity",
            )

        if _contains_any(text, _UNIT_WORDS):
            return PlannedQuery(
                sql=_STATS_SQL,
                description="Inventory statistics including total and available quantity.",
                intent="sum_quantity",
            )

        return PlannedQuery(
            sql=_STATS_SQL,
            description="Inventory statistics including the number of item records.",
            intent="count_records",
        )

    if _contains_any(
        text,
        ("total stock", "total inventory", "total quantity", "stock total", "inventaire total", "stock total"),
    ):
        return PlannedQuery(
            sql=_STATS_SQL,
            description="Inventory statistics including total and available quantity.",
            intent="sum_quantity",
        )

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
