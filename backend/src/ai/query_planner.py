"""Deterministic semantic query planner for common inventory questions.

Runs before LLM SQL generation. High-confidence English/French questions are
converted into safe PostgreSQL SELECTs so question words can never become
item-name filters. Item-specific questions are resolved before generic counts
so English names can target French canonical inventory names.
"""

from dataclasses import dataclass
import re

from src.ai.entity_resolver import resolve_item


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
    "available", "availability", "available right now", "disponible", "disponibles",
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
    "different", "distinct", "types of", "references", "références",
    "different items", "different products", "types d'articles", "types d'items",
)

_LIST_WORDS = (
    "show", "list", "display", "which", "what", "find", "search",
    "affiche", "afficher", "liste", "lister", "quels", "quelles",
    "montre", "montrer", "trouve", "trouver", "recherche", "rechercher",
)

# A live existence question should never fall through to the LLM merely
# because its grammatical form differs from "Do we have X?".  These phrases
# are equivalent inventory lookups: Do you have X? / Is there X? / Are there
# any X? / Avons-nous X? / Y a-t-il X?
_EXISTENCE_PHRASES = (
    "do we have", "do you have", "does qstock have", "is there", "are there",
    "avons-nous", "avons nous", "avez-vous", "avez vous", "est-ce qu'on a",
    "est ce qu'on a", "est-ce que nous avons", "est ce que nous avons",
    "y a-t-il", "y a t il", "y a il",
)

_INVENTORY_LIST_PHRASES = (
    "what items do we have", "what items do we currently have",
    "what inventory do we have", "what do we have in inventory",
    "what is in our inventory", "list our inventory", "show our inventory",
    "show me our inventory", "list all items", "show all items",
    "what items are in stock", "what is currently in stock",
    "quels articles avons-nous", "quelles articles avons-nous",
    "qu'est-ce qu'on a en stock", "qu'est-ce que nous avons en stock",
    "quels articles sont en stock", "montre-moi notre inventaire",
    "liste notre inventaire",
)


def plan_inventory_query(question: str) -> PlannedQuery | None:
    """Return a deterministic query for a high-confidence inventory question."""
    text = " ".join((question or "").strip().lower().split())
    if not text:
        return None

    item = resolve_item(question)
    if item:
        item_sql = _escape_sql_literal(item.canonical_name)
        location = _extract_location(text)
        location_clause = (
            f"\n  AND LOWER(i.location) = LOWER('{_escape_sql_literal(location)}')"
            if location else ""
        )

        if _contains_any(text, _COUNT_WORDS):
            if _contains_any(text, _MAINTENANCE_WORDS):
                return _item_status_count_plan(item_sql, "maintenance", "maintenance", location_clause)
            if _contains_any(text, _BORROWED_WORDS):
                return PlannedQuery(
                    sql=f"""SELECT i.name,
       COUNT(*) AS item_records,
       COALESCE(SUM(i.quantity - i.available_quantity), 0) AS borrowed_total_quantity
FROM items AS i
WHERE LOWER(i.name) = LOWER('{item_sql}')
  AND i.status = 'borrowed'{location_clause}
GROUP BY i.name""",
                    description=f"Borrowed quantity for {item.canonical_name}.",
                    intent="count_item_borrowed",
                )
            if _contains_any(text, _RETIRED_WORDS):
                return _item_status_count_plan(item_sql, "retired", "retired", location_clause)
            if _contains_any(text, _AVAILABLE_WORDS):
                return PlannedQuery(
                    sql=f"""SELECT i.name,
       COUNT(*) AS item_records,
       COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity
FROM items AS i
WHERE LOWER(i.name) = LOWER('{item_sql}')
  AND i.available_quantity > 0{location_clause}
GROUP BY i.name""",
                    description=f"Available quantity for {item.canonical_name}.",
                    intent="count_item_available",
                )
            return PlannedQuery(
                sql=f"""SELECT i.name,
       COUNT(*) AS item_records,
       COALESCE(SUM(i.quantity), 0) AS total_quantity,
       COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity
FROM items AS i
WHERE LOWER(i.name) = LOWER('{item_sql}'){location_clause}
GROUP BY i.name""",
                description=f"Total quantity for {item.canonical_name}.",
                intent="count_item",
            )

        if _contains_any(text, _AVAILABLE_WORDS):
            return _item_detail_plan(item_sql, item.canonical_name, location_clause, "item_availability")

        if _contains_location_question(text):
            return _item_detail_plan(item_sql, item.canonical_name, location_clause, "locate_item")

        # All common existence formulations resolve to the same deterministic
        # item lookup. This is deliberately broader than the old literal
        # "do we have" check, which missed "do you have", "is there", and
        # "are there any" and unnecessarily fell back to the LLM.
        if _contains_any(text, _EXISTENCE_PHRASES) or _contains_any(text, _LIST_WORDS):
            return _item_detail_plan(item_sql, item.canonical_name, location_clause, "find_item")

    location = _extract_location(text)
    if location and _contains_any(text, _COUNT_WORDS):
        location_sql = _escape_sql_literal(location)
        location_filter = f"LOWER(i.location) = LOWER('{location_sql}')"
        if _contains_any(text, _MAINTENANCE_WORDS):
            return PlannedQuery(
                sql=f"""SELECT COUNT(*) AS maintenance_item_records,
       COALESCE(SUM(i.quantity), 0) AS maintenance_total_quantity
FROM items AS i
WHERE i.status = 'maintenance'
  AND {location_filter}""",
                description=f"Inventory under maintenance in {location}.",
                intent="count_maintenance_location",
            )
        if _contains_any(text, _BORROWED_WORDS):
            return PlannedQuery(
                sql=f"""SELECT COUNT(*) AS borrowed_item_records,
       COALESCE(SUM(i.quantity - i.available_quantity), 0) AS borrowed_total_quantity
FROM items AS i
WHERE i.status = 'borrowed'
  AND {location_filter}""",
                description=f"Borrowed inventory in {location}.",
                intent="count_borrowed_location",
            )
        if _contains_any(text, _AVAILABLE_WORDS):
            return PlannedQuery(
                sql=f"""SELECT COUNT(*) AS item_records,
       COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity
FROM items AS i
WHERE i.status = 'available'
  AND i.available_quantity > 0
  AND {location_filter}""",
                description=f"Available inventory in {location}.",
                intent="count_available_location",
            )
        return PlannedQuery(
            sql=f"""SELECT COUNT(*) AS item_records,
       COALESCE(SUM(i.quantity), 0) AS total_quantity,
       COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity
FROM items AS i
WHERE {location_filter}""",
            description=f"Inventory in {location}.",
            intent="count_location",
        )

    if location and _contains_any(text, _LIST_WORDS):
        location_sql = _escape_sql_literal(location)
        return PlannedQuery(
            sql=f"""SELECT i.id, i.name, i.item_code, i.brand, i.model, i.status,
       i.quantity, i.available_quantity, i.location
FROM items AS i
WHERE LOWER(i.location) = LOWER('{location_sql}')
ORDER BY i.name
LIMIT 100""",
            description=f"Inventory items located in {location}.",
            intent="list_location",
        )

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
        if _contains_any(text, _AVAILABLE_WORDS):
            return PlannedQuery(
                sql="""SELECT COUNT(*) FILTER (WHERE i.status = 'available') AS item_records,
       COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity
FROM items AS i""",
                description="Currently available inventory quantity and item records.",
                intent="count_available",
            )
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

    if _contains_any(text, (
        "total stock", "total inventory", "total quantity", "stock total",
        "inventaire total", "quantité totale", "quantite totale",
    )):
        return PlannedQuery(
            sql="""SELECT COUNT(*) AS item_records,
       COALESCE(SUM(i.quantity), 0) AS total_quantity,
       COALESCE(SUM(i.available_quantity), 0) AS total_available_quantity
FROM items AS i""",
            description="Total inventory quantity and available quantity.",
            intent="sum_quantity",
        )

    if any(phrase in text for phrase in _INVENTORY_LIST_PHRASES):
        return _list_items_plan()

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


def _item_status_count_plan(item_sql: str, status: str, label: str, location_clause: str) -> PlannedQuery:
    return PlannedQuery(
        sql=f"""SELECT i.name,
       COUNT(*) AS item_records,
       COALESCE(SUM(i.quantity), 0) AS {label}_total_quantity
FROM items AS i
WHERE LOWER(i.name) = LOWER('{item_sql}')
  AND i.status = '{status}'{location_clause}
GROUP BY i.name""",
        description=f"{label.title()} quantity for the requested item.",
        intent=f"count_item_{label}",
    )


def _item_detail_plan(item_sql: str, canonical_name: str, location_clause: str, intent: str) -> PlannedQuery:
    return PlannedQuery(
        sql=f"""SELECT i.id, i.name, i.item_code, i.brand, i.model, i.status,
       i.quantity, i.available_quantity, i.location
FROM items AS i
WHERE LOWER(i.name) = LOWER('{item_sql}'){location_clause}
ORDER BY i.name
LIMIT 100""",
        description=f"Inventory details for {canonical_name}.",
        intent=intent,
    )


def _list_items_plan() -> PlannedQuery:
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


def _contains_location_question(text: str) -> bool:
    return any(term in text for term in ("where", "où", "ou est", "ou sont", "location", "emplacement"))


def _extract_location(text: str) -> str:
    match = re.search(
        r"\b(?:in|at|dans|à|a)\s+(?:location|building|room|emplacement|bâtiment|batiment|salle)?\s*[:\-]?\s*([A-Za-z0-9]+)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    candidate = match.group(1).strip()
    if candidate.lower() in {"stock", "the", "a", "an", "this", "that", "inventory"}:
        return ""
    return candidate


def _escape_sql_literal(value: str) -> str:
    return (value or "").replace("'", "''")
