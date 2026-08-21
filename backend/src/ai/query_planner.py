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
    "available", "availability", "disponible", "disponibles",
    "disponibilité", "disponibilite",
)

_MAINTENANCE_WORDS = (
    "maintenance", "under maintenance", "in maintenance", "en maintenance",
)

_BORROWED_WORDS = (
    "borrowed", "borrow", "emprunté", "emprunte", "empruntés", "empruntes",
)

_RETIRED_WORDS = (
    "retired", "retire", "retiré", "retiree", "retirés", "retirees",
)

_DISTINCT_WORDS = (
    "different", "distinct", "types of", "references", "références", "references",
    "different items", "different products", "types d'articles", "types d'items",
)

_LIST_WORDS = (
    "show", "list", "display", "which", "what", "find", "search",
    "affiche", "afficher", "liste", "lister", "quels", "quelles",
    "montre", "montrer", "trouve", "trouver", "recherche", "rechercher",
)

_INVENTORY_LIST_PHRASES = (
    "what items do we have",
    "what items do we currently have",
    "what inventory do we have",
    "what do we have in inventory",
    "what is in our inventory",
    "list our inventory",
    "show our inventory",
    "show me our inventory",
    "list all items",
    "show all items",
    "what items are in stock",
    "what is currently in stock",
    "quels articles avons-nous",
    "quelles articles avons-nous",
    "qu'est-ce qu'on a en stock",
    "qu'est-ce que nous avons en stock",
    "quels articles sont en stock",
    "montre-moi notre inventaire",
    "liste notre inventaire",
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
    """Return a deterministic query for high-confidence inventory questions."""
    text = " ".join((question or "").strip().lower().split())
    if not text:
        return None

    # ---------------------------------------------------------------
    # 1. Status-specific counts MUST happen before generic "available"
    #    and generic count handling. This prevents:
    #      "How many items are in maintenance?"
    #    from becoming a global inventory statistics query.
    # ---------------------------------------------------------------
    if _contains_any(text, _COUNT_WORDS):
        if _contains_any(text, _MAINTENANCE_WORDS):
            return PlannedQuery(
                sql="""SELECT COUNT(*) AS maintenance_item_records,
       COALESCE(SUM(i.quantity), 0) AS maintenance_total_quantity
FROM items AS i
WHERE i.status = 'maintenance'""",
                description="Inventory items currently in maintenance.",
                intent="count_maintenance",
            )

        if _contains_any(text, _BORROWED_WORDS):
            return PlannedQuery(
                sql="""SELECT COUNT(*) AS borrowed_item_records,
       COALESCE(SUM(i.quantity - i.available_quantity), 0) AS borrowed_total_quantity
FROM items AS i
WHERE i.status = 'borrowed'""",
                description="Inventory items currently borrowed.",
                intent="count_borrowed",
            )

        if _contains_any(text, _RETIRED_WORDS):
            return PlannedQuery(
                sql="""SELECT COUNT(*) AS retired_item_records,
       COALESCE(SUM(i.quantity), 0) AS retired_total_quantity
FROM items AS i
WHERE i.status = 'retired'""",
                description="Inventory items currently retired.",
                intent="count_retired",
            )

        if _contains_any(text, _DISTINCT_WORDS):
            return PlannedQuery(
                sql="""SELECT COUNT(*) AS item_records
FROM items AS i""",
                description="Number of distinct inventory item records.",
                intent="count_records",
            )

        # "How many items are available?" means the currently available
        # inventory, not the entire dashboard. Return only the relevant facts.
        if _contains_any(text, _AVAILABLE_WORDS):
            return PlannedQuery(
                sql="""SELECT COUNT(*) FILTER (WHERE i.status = 'available') AS item_records,
       COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity
FROM items AS i""",
                description="Currently available inventory quantity and item records.",
                intent="count_available",
            )

        # "How many items do we have in stock?" is a total inventory question.
        if _contains_any(text, _UNIT_WORDS):
            return PlannedQuery(
                sql="""SELECT COUNT(*) AS item_records,
       COALESCE(SUM(i.quantity), 0) AS total_quantity,
       COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity
FROM items AS i""",
                description="Total inventory quantity and available quantity.",
                intent="sum_quantity",
            )

        return PlannedQuery(
            sql="""SELECT COUNT(*) AS item_records
FROM items AS i""",
            description="Number of inventory item records.",
            intent="count_records",
        )

    # ---------------------------------------------------------------
    # 2. Explicit total inventory questions.
    # ---------------------------------------------------------------
    if _contains_any(
        text,
        (
            "total stock", "total inventory", "total quantity", "stock total",
            "inventaire total", "quantité totale", "quantite totale",
            "stock total",
        ),
    ):
        return PlannedQuery(
            sql="""SELECT COUNT(*) AS item_records,
       COALESCE(SUM(i.quantity), 0) AS total_quantity,
       COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity
FROM items AS i""",
            description="Total inventory quantity and available quantity.",
            intent="sum_quantity",
        )

    # ---------------------------------------------------------------
    # 3. Generic inventory list questions.
    # ---------------------------------------------------------------
    if any(phrase in text for phrase in _INVENTORY_LIST_PHRASES):
        return _list_items_plan()

    # ---------------------------------------------------------------
    # 4. Available-item list questions.
    # ---------------------------------------------------------------
    if _contains_any(text, _AVAILABLE_WORDS) and _contains_any(text, _LIST_WORDS):
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


def _list_items_plan() -> PlannedQuery:
    """Return the canonical read-only inventory listing query."""
    return PlannedQuery(
        sql="""SELECT i.id, i.name, i.item_code, i.brand, i.model, i.status,
       i.quantity, i.available_quantity, i.location
FROM items AS i
ORDER BY i.name
LIMIT 100""",
        description="Current inventory item list.",
        intent="list_items",
    )


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)
