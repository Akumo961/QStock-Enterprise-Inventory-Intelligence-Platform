"""Lightweight regression cases for the AI routing policy.

These cases are intentionally framework-free so they can be imported by the
existing test suite without requiring an LLM, database, or network service.
"""

from src.ai.intent import Intent, classify_intent
from src.ai.policy import normalize_user_message, validate_user_message


def test_policy_normalizes_whitespace():
    assert normalize_user_message("  show   me\n laptops  ") == "show me laptops"


def test_policy_rejects_empty_message():
    try:
        validate_user_message("   ")
    except ValueError as exc:
        assert "empty" in str(exc).lower()
    else:
        raise AssertionError("Expected empty message to be rejected")


def test_inventory_question_routes_to_sql():
    result = classify_intent("show me available laptops")
    assert result.intent is Intent.INVENTORY_SQL


def test_procedural_question_routes_to_general_chat():
    result = classify_intent("How do I borrow a laptop?")
    assert result.intent is Intent.GENERAL_CHAT


def test_follow_up_routes_to_sql_with_history():
    result = classify_intent("only Dell ones", has_history=True)
    assert result.intent is Intent.INVENTORY_SQL
