"""Natural-language response generation for QStock AI."""

import re
from typing import Any

from src.ai.prompts import (
    build_answer_system_prompt,
    build_answer_user_prompt,
    build_empty_result_prompt,
    build_general_system_prompt,
    build_general_user_prompt,
)
from src.core.config import settings

_VERBOSE_COLUMNS = frozenset({
    "description", "notes", "image_url", "qr_code_data", "qr_code_image",
    "hashed_password", "purchase_date", "created_at", "updated_at",
    "is_borrowable", "requires_approval", "max_borrow_days",
})


def slim_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove verbose fields before sending database rows to an LLM."""
    if not rows:
        return rows
    if len(rows[0]) <= 6:
        return rows
    return [
        {key: value for key, value in row.items() if key not in _VERBOSE_COLUMNS}
        for row in rows
    ]


def serialize_rows_for_prompt(rows: list[dict[str, Any]], limit: int) -> str:
    """Serialize database rows compactly for answer generation."""
    if not rows:
        return "(no rows)"
    compact_rows = slim_rows(rows)
    lines: list[str] = []
    for index, row in enumerate(compact_rows[:limit], start=1):
        pairs = ", ".join(f"{key}={value}" for key, value in row.items())
        lines.append(f"{index}. {pairs}")
    if len(rows) > limit:
        lines.append(f"... and {len(rows) - limit} more row(s), total matched: {len(rows)}.")
    return "\n".join(lines)


class ResponseGenerator:
    """Turn retrieved data or general prompts into user-facing answers."""

    def __init__(self, provider: Any):
        self.provider = provider

    def answer_from_rows(self, *, language: str, question: str, sql: str,
                         rows: list[dict[str, Any]], history_messages: list[dict[str, str]]) -> str:
        row_limit = getattr(settings, "AI_CONTEXT_ROW_LIMIT", 15)
        max_tokens = getattr(settings, "AI_ANSWER_MAX_TOKENS", 180)
        data_block = serialize_rows_for_prompt(rows, row_limit)
        messages = (
            [{"role": "system", "content": build_answer_system_prompt(language)}]
            + history_messages
            + [{"role": "user", "content": build_answer_user_prompt(
                question=question, sql=sql, data_block=data_block, row_count=len(rows)
            )}]
        )
        answer_num_ctx = getattr(settings, "AI_ANSWER_NUM_CTX", 2048)
        return self.provider.complete(
            messages, max_tokens=max_tokens, temperature=0.25, num_ctx=answer_num_ctx
        ).strip()

    def empty_result_answer(self, *, language: str, question: str, sql: str,
                            history_summary: str) -> str:
        messages = [
            {"role": "system", "content": build_answer_system_prompt(language)},
            {"role": "user", "content": build_empty_result_prompt(
                language=language, question=question, sql=sql, history_summary=history_summary
            )},
        ]
        answer_num_ctx = getattr(settings, "AI_ANSWER_NUM_CTX", 2048)
        return self.provider.complete(
            messages, max_tokens=120, temperature=0.25, num_ctx=answer_num_ctx
        ).strip()

    def general_answer(self, *, language: str, question: str) -> str:
        messages = [
            {"role": "system", "content": build_general_system_prompt(language)},
            {"role": "user", "content": build_general_user_prompt(question)},
        ]
        answer_num_ctx = getattr(settings, "AI_ANSWER_NUM_CTX", 2048)
        return self.provider.complete(
            messages, max_tokens=180, temperature=0.35, num_ctx=answer_num_ctx
        ).strip()


def fallback_format_rows(rows: list[dict[str, Any]], language: str) -> str:
    """Safe deterministic fallback with human wording instead of debug text."""
    if not rows:
        if language == "fr":
            return "Je n’ai trouvé aucun résultat correspondant. Vérifiez l’article, l’emplacement ou le filtre demandé."
        return "I couldn’t find any results matching that request. Check the item, location, or filter and try again."

    lines: list[str] = []
    for row in rows[:20]:
        label = row.get("name") or row.get("full_name") or row.get("item_name")
        if label:
            details = [
                f"{key.replace('_', ' ').title()}: {value}"
                for key, value in row.items()
                if key not in {"id", "user_id", "name", "full_name", "item_name"} and value is not None
            ]
            lines.append(f"- **{label}**" + (f" — {', '.join(details)}" if details else ""))
        else:
            lines.append("- " + ", ".join(f"{key}: {value}" for key, value in row.items()))
    if len(rows) > 20:
        lines.append(
            f"- … {len(rows) - 20} more result(s)."
            if language != "fr"
            else f"- … {len(rows) - 20} résultat(s) supplémentaire(s)."
        )
    return ("Voici les résultats :" if language == "fr" else "Here are the results:") + "\n\n" + "\n".join(lines)


def deterministic_list_answer(rows: list[dict[str, Any]], language: str,
                              max_items: int = 20, question: str = "") -> str | None:
    """Format simple item/user lists with context-aware natural wording."""
    if not rows:
        return None

    first = rows[0]
    if "name" in first:
        label_key = "name"
    elif "full_name" in first:
        label_key = "full_name"
    else:
        return None

    display_fields = [
        ("item_code", "Item Code" if language != "fr" else "Code"),
        ("email", "Email"),
        ("department", "Department" if language != "fr" else "Département"),
        ("brand", "Brand" if language != "fr" else "Marque"),
        ("model", "Model" if language != "fr" else "Modèle"),
        ("category", "Category" if language != "fr" else "Catégorie"),
        ("status", "Status" if language != "fr" else "Statut"),
        ("quantity", "Quantity" if language != "fr" else "Quantité"),
        ("available_quantity", "Available" if language != "fr" else "Disponible"),
        ("location", "Location" if language != "fr" else "Emplacement"),
        ("overdue_transaction_count", "Overdue Count" if language != "fr" else "Retards"),
        ("oldest_due_date", "Oldest Due" if language != "fr" else "Échéance"),
        ("times_borrowed", "Times Borrowed" if language != "fr" else "Fois empruntée"),
        ("borrowed_at", "Borrowed At" if language != "fr" else "Emprunté le"),
        ("due_date", "Due" if language != "fr" else "Échéance"),
    ]

    shown = rows[:max_items]
    lines: list[str] = []
    for index, row in enumerate(shown, start=1):
        label = row.get(label_key) or "(unnamed)"
        details = [
            f"{display_name}: {row[key]}"
            for key, display_name in display_fields
            if key in row and row[key] is not None
        ]
        suffix = f" — {', '.join(details)}" if details else ""
        lines.append(f"{index}. **{label}**{suffix}")

    text = (question or "").lower()
    location = _extract_location_from_question(text)
    if location is None:
        row_locations = {str(row.get("location")) for row in rows if row.get("location")}
        if len(row_locations) == 1:
            location = next(iter(row_locations))

    availability = any(term in text for term in (
        "available", "availability", "in stock", "disponible", "disponibles",
        "disponibilité", "disponibilite", "en stock",
    ))
    if not availability:
        statuses = {str(row.get("status", "")).lower() for row in rows}
        availability = statuses == {"available"} and all(
            row.get("available_quantity", 0) not in (None, 0) for row in rows
        )

    if language == "fr":
        if availability and location:
            header = f"J’ai trouvé {len(rows)} article(s) disponible(s) à {location} :\n\n"
        elif location:
            header = f"J’ai trouvé {len(rows)} article(s) à {location} :\n\n"
        elif availability:
            header = f"Voici {len(rows)} article(s) actuellement disponible(s) :\n\n"
        elif len(rows) > max_items:
            header = f"Voici les {max_items} premiers sur {len(rows)} résultat(s) :\n\n"
        else:
            header = f"Voici les {len(rows)} résultat(s) :\n\n"
    else:
        if availability and location:
            header = f"I found {len(rows)} available item(s) in {location}:\n\n"
        elif location:
            header = f"I found {len(rows)} item(s) in {location}:\n\n"
        elif availability:
            header = f"Here are the {len(rows)} item(s) currently available:\n\n"
        elif len(rows) > max_items:
            header = f"Here are the first {max_items} of {len(rows)} result(s):\n\n"
        else:
            header = f"Here are the {len(rows)} result(s):\n\n"

    if len(rows) > max_items:
        header += (
            f"Affichage des {max_items} premiers résultats.\n\n"
            if language == "fr"
            else f"Showing the first {max_items} results.\n\n"
        )
    return header + "\n".join(lines)


def deterministic_data_answer(question: str, rows: list[dict[str, Any]], language: str) -> str | None:
    """Answer known aggregate results directly from database values."""
    if not rows:
        return None
    first = rows[0]
    keys = set(first.keys())

    if {"total_quantity", "total_available_quantity", "item_records"}.issubset(keys):
        if language == "fr":
            return f"Vous avez actuellement {first['total_quantity']} unités en stock sur {first['item_records']} référence(s). Dont {first['total_available_quantity']} unité(s) sont actuellement disponibles."
        return f"You currently have {first['total_quantity']} units in stock across {first['item_records']} inventory item(s). Of those, {first['total_available_quantity']} unit(s) are currently available."

    if {"total_available_quantity", "item_records"}.issubset(keys):
        if language == "fr":
            return f"Vous avez actuellement {first['total_available_quantity']} unité(s) disponibles sur {first['item_records']} référence(s) d’inventaire."
        return f"You currently have {first['total_available_quantity']} available unit(s) across {first['item_records']} inventory item(s)."

    if "item_records" in keys and len(keys) == 1:
        if language == "fr":
            return f"QStock contient actuellement {first['item_records']} référence(s) d’inventaire."
        return f"QStock currently has {first['item_records']} inventory item(s)."

    dashboard_keys = {
        "item_records", "total_quantity", "available_quantity", "unavailable_quantity",
        "available_records", "borrowed_records", "maintenance_records", "retired_records",
    }
    if dashboard_keys.issubset(keys):
        if language == "fr":
            return (
                f"L’inventaire contient {first['item_records']} fiche(s), {first['total_quantity']} unité(s) au total et "
                f"{first['available_quantity']} unité(s) disponibles. Unités indisponibles : {first['unavailable_quantity']}. "
                f"Statuts : {first['available_records']} disponibles, {first['borrowed_records']} empruntées, "
                f"{first['maintenance_records']} en maintenance et {first['retired_records']} retirées."
            )
        return (
            f"Inventory has {first['item_records']} item record(s), {first['total_quantity']} total unit(s), and "
            f"{first['available_quantity']} available unit(s). Unavailable units: {first['unavailable_quantity']}. "
            f"Statuses: {first['available_records']} available, {first['borrowed_records']} borrowed, "
            f"{first['maintenance_records']} in maintenance, and {first['retired_records']} retired."
        )

    if {"current_available_inventory", "total_inventory", "unavailable_inventory"}.issubset(keys):
        if language == "fr":
            return f"Inventaire actuellement disponible : {first['current_available_inventory']}. Inventaire total : {first['total_inventory']}. Indisponible : {first['unavailable_inventory']}."
        return f"Current available inventory is {first['current_available_inventory']}. Total inventory is {first['total_inventory']}. Unavailable inventory is {first['unavailable_inventory']}."

    if {"maintenance_item_records", "maintenance_total_quantity"}.issubset(keys):
        if language == "fr":
            return f"{first['maintenance_item_records']} fiche(s) sont en maintenance, pour {first['maintenance_total_quantity']} unité(s) au total."
        return f"{first['maintenance_item_records']} item record(s) are under maintenance, totaling {first['maintenance_total_quantity']} unit(s)."

    return None


def deterministic_general_answer(question: str, language: str) -> str:
    """Provide deterministic answers for a small set of general QStock topics."""
    text = question.lower()
    if language == "fr":
        if "low stock" in text or "faible" in text:
            return "Dans QStock, un stock faible signifie généralement que la quantité disponible est sous un seuil. Si aucun seuil n’est précisé, utilisez le seuil configuré par QStock plutôt que de l’inventer."
        if "status" in text or "statut" in text:
            return "Les statuts principaux de l’inventaire sont available, borrowed, maintenance et retired."
        return "Je peux répondre aux questions sur les articles, les quantités, les disponibilités, les emprunts, les retards, les utilisateurs, les demandes et les statistiques d’inventaire."
    if "low stock" in text:
        return "I can identify low-stock inventory using QStock’s configured threshold. I won’t invent a threshold if the application has not configured one."
    if "status" in text:
        return "QStock inventory statuses include available, borrowed, maintenance, and retired."
    return "I can answer live inventory questions about items, quantities, availability, borrowed and overdue transactions, users, requests, categories, and inventory statistics."


def can_answer_general_deterministically(question: str) -> bool:
    text = question.lower()
    return any(phrase in text for phrase in (
        "what can you do", "what can you help", "help", "low stock", "inventory status",
        "status mean", "explain inventory status", "que peux-tu faire", "que pouvez-vous faire",
        "aide", "stock faible", "statut inventaire",
    ))


def _extract_location_from_question(text: str) -> str | None:
    match = re.search(
        r"\b(?:in|at|dans|à|a)\s+"
        r"(?:(?:location|building|room|emplacement|bâtiment|batiment|salle)\s*)?"
        r"[:\-]?\s*([A-Za-z0-9]+)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    candidate = match.group(1).strip()
    if candidate.lower() in {
        "stock", "the", "this", "that", "inventory", "maintenance",
        "available", "borrowed", "retired", "overdue",
    }:
        return None
    return candidate
