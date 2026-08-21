"""Deterministic semantic query planner for common inventory questions.

Runs before LLM SQL generation. High-confidence English/French questions are
converted into safe PostgreSQL SELECTs so question words can never become
item-name filters.

The planner deliberately handles the most common inventory intents
deterministically before falling back to LLM SQL generation.

Supported patterns include:
- global inventory counts
- available / maintenance / borrowed / retired counts
- inventory listings
- location-scoped listings and counts
- item-specific queries
- item existence questions
- English and French variants
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
    "how many",
    "how much",
    "count",
    "number of",
    "total number",
    "combien",
    "quel est le nombre",
    "quelle est la quantite",
    "quelle quantité",
    "nombre total",
    "quantite totale",
    "quantité totale",
)

_UNIT_WORDS = (
    "unit",
    "units",
    "unités",
    "unites",
    "quantity",
    "quantité",
    "quantite",
    "stock",
    "inventory",
    "inventaire",
    "on hand",
    "in stock",
    "en stock",
)

_AVAILABLE_WORDS = (
    "available",
    "availability",
    "available right now",
    "disponible",
    "disponibles",
    "disponibilité",
    "disponibilite",
)

_MAINTENANCE_WORDS = (
    "maintenance",
    "under maintenance",
    "in maintenance",
    "en maintenance",
)

_BORROWED_WORDS = (
    "borrowed",
    "borrow",
    "emprunté",
    "emprunte",
    "empruntés",
    "empruntes",
)

_RETIRED_WORDS = (
    "retired",
    "retire",
    "retiré",
    "retiree",
    "retirés",
    "retirees",
)

_DISTINCT_WORDS = (
    "different",
    "distinct",
    "types of",
    "references",
    "références",
    "different items",
    "different products",
    "types d'articles",
    "types d'items",
)

_LIST_WORDS = (
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

# Existence questions should resolve deterministically instead of falling
# through to the LLM.
#
# Examples:
#   Do we have a projector?
#   Do you have a projector?
#   Does QStock have a projector?
#   Is there a projector?
#   Are there any projectors?
#   Avons-nous un projecteur?
#   Y a-t-il un projecteur?
_EXISTENCE_PHRASES = (
    "do we have",
    "do you have",
    "does qstock have",
    "is there",
    "are there",
    "avons-nous",
    "avons nous",
    "avez-vous",
    "avez vous",
    "est-ce qu'on a",
    "est ce qu'on a",
    "est-ce que nous avons",
    "est ce que nous avons",
    "y a-t-il",
    "y a t il",
    "y a il",
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


def plan_inventory_query(question: str) -> PlannedQuery | None:
    """Return a deterministic query for a high-confidence inventory question.

    The order of evaluation is intentional:

    1. Normalize the question.
    2. Resolve a specific item, when possible.
    3. Handle location-scoped queries before global queries.
    4. Handle global counts.
    5. Handle global inventory listings.
    6. Return None when deterministic planning is not sufficiently confident.
    """
    original_text = " ".join((question or "").strip().split())
    text = original_text.lower()

    if not text:
        return None

    # ------------------------------------------------------------------
    # 1. Resolve item-specific questions first.
    # ------------------------------------------------------------------
    item = resolve_item(question)

    if item:
        item_sql = _escape_sql_literal(item.canonical_name)

        location = _extract_location(original_text)

        location_clause = (
            f"\n  AND LOWER(i.location) = "
            f"LOWER('{_escape_sql_literal(location.lower())}')"
            if location
            else ""
        )

        # Item + count
        if _contains_any(text, _COUNT_WORDS):
            if _contains_any(text, _MAINTENANCE_WORDS):
                return _item_status_count_plan(
                    item_sql,
                    "maintenance",
                    "maintenance",
                    location_clause,
                )

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
                return _item_status_count_plan(
                    item_sql,
                    "retired",
                    "retired",
                    location_clause,
                )

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

        # Item + availability
        if _contains_any(text, _AVAILABLE_WORDS):
            return _item_detail_plan(
                item_sql,
                item.canonical_name,
                location_clause,
                "item_availability",
            )

        # Item + location question
        if _contains_location_question(text):
            return _item_detail_plan(
                item_sql,
                item.canonical_name,
                location_clause,
                "locate_item",
            )

        # Item existence / discovery / listing.
        if (
            _contains_any(text, _EXISTENCE_PHRASES)
            or _contains_any(text, _LIST_WORDS)
        ):
            return _item_detail_plan(
                item_sql,
                item.canonical_name,
                location_clause,
                "find_item",
            )

    # ------------------------------------------------------------------
    # 2. Extract a physical location.
    #
    # This MUST be outside the "if item:" block.
    #
    # Examples:
    #   How many items are available in A1?
    #   What items are in A1?
    #   Quels articles sont à A5 ?
    # ------------------------------------------------------------------
    location = _extract_location(original_text)

    if location:
        location_sql = _escape_sql_literal(location.lower())
        location_filter = (
            f"LOWER(i.location) = LOWER('{location_sql}')"
        )

        # --------------------------------------------------------------
        # Location + COUNT
        # --------------------------------------------------------------
        if _contains_any(text, _COUNT_WORDS):
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

            if _contains_any(text, _RETIRED_WORDS):
                return PlannedQuery(
                    sql=f"""SELECT COUNT(*) AS retired_item_records,
       COALESCE(SUM(i.quantity), 0) AS retired_total_quantity
FROM items AS i
WHERE i.status = 'retired'
  AND {location_filter}""",
                    description=f"Retired inventory in {location}.",
                    intent="count_retired_location",
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

        # --------------------------------------------------------------
        # Location + LIST
        # --------------------------------------------------------------
        #
        # "What items are in A1?" does not contain "list" or "show".
        # Therefore "what" must be recognized as a listing word.
        #
        if _contains_any(text, _LIST_WORDS):
            return PlannedQuery(
                sql=f"""SELECT i.id, i.name, i.item_code, i.brand, i.model, i.status,
       i.quantity, i.available_quantity, i.location
FROM items AS i
WHERE {location_filter}
ORDER BY i.name
LIMIT 100""",
                description=f"Inventory items located in {location}.",
                intent="list_location",
            )

    # ------------------------------------------------------------------
    # 3. Global COUNT queries.
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 4. Global total-stock queries that may not contain an explicit
    #    "how many" phrase.
    # ------------------------------------------------------------------
    if _contains_any(
        text,
        (
            "total stock",
            "total inventory",
            "total quantity",
            "stock total",
            "inventaire total",
            "quantité totale",
            "quantite totale",
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

    # ------------------------------------------------------------------
    # 5. Global inventory listing.
    # ------------------------------------------------------------------
    if any(phrase in text for phrase in _INVENTORY_LIST_PHRASES):
        return _list_items_plan()

    # ------------------------------------------------------------------
    # 6. Generic available-inventory listing.
    # ------------------------------------------------------------------
    if (
        _contains_any(text, _AVAILABLE_WORDS)
        and _contains_any(text, _LIST_WORDS)
    ):
        return PlannedQuery(
            sql="""SELECT i.id, i.name, i.item_code, i.brand, i.model, i.status,
       i.quantity, i.available_quantity, i.location
FROM items AS i
WHERE i.status = 'available'
  AND i.available_quantity > 0
ORDER BY i.name
LIMIT 100""",
            description="Currently available inventory items.",
            intent="list_available",
        )

    return None


def _item_status_count_plan(
    item_sql: str,
    status: str,
    label: str,
    location_clause: str,
) -> PlannedQuery:
    """Build a status-specific item count query."""
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


def _item_detail_plan(
    item_sql: str,
    canonical_name: str,
    location_clause: str,
    intent: str,
) -> PlannedQuery:
    """Build a deterministic item detail query."""
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
    """Build the global inventory listing query."""
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
    """Return True when any semantic term occurs in the normalized text."""
    return any(term in text for term in terms)


def _contains_location_question(text: str) -> bool:
    """Detect questions asking where an item is located."""
    return any(
        term in text
        for term in (
            "where",
            "où",
            "ou est",
            "ou sont",
            "location",
            "emplacement",
        )
    )


def _extract_location(text: str) -> str:
    """Extract a physical inventory location such as A1 or A5.

    Supported forms include:
        in A1
        at A1
        dans A1
        à A5
        a A5
        in room A1
        dans salle A5

    Status/inventory words are explicitly rejected so expressions such as
    "in stock" or "in maintenance" cannot accidentally become locations.
    """
    match = re.search(
        r"\b(?:in|at|dans|à|a)\s+"
        r"(?:location|building|room|emplacement|bâtiment|batiment|salle)?"
        r"\s*[:\-]?\s*"
        r"([A-Za-z0-9]+)\b",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    candidate = match.group(1).strip()

    if candidate.lower() in {
        "stock",
        "the",
        "a",
        "an",
        "this",
        "that",
        "inventory",
        "maintenance",
        "available",
        "borrowed",
        "retired",
        "overdue",
    }:
        return ""

    return candidate


def _escape_sql_literal(value: str) -> str:
    """Escape a value before embedding it in a SQL literal.

    The planner only emits SELECT statements, but literals are still escaped
    defensively because item/location values originate from user input or
    entity resolution.
    """
    return (value or "").replace("'", "''")