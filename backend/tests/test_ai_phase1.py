"""Phase 1 AI routing and input-policy regression tests.

These tests do not require an LLM, database, or network connection.
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


def test_policy_rejects_oversized_message():
    try:
        validate_user_message("x" * 2001)
    except ValueError as exc:
        assert "2000" in str(exc)
    else:
        raise AssertionError("Expected oversized message to be rejected")


def test_english_inventory_question_routes_to_sql():
    result = classify_intent("show me available laptops")
    assert result.intent is Intent.INVENTORY_SQL


def test_french_inventory_question_routes_to_sql():
    result = classify_intent("affiche-moi les ordinateurs disponibles")
    assert result.intent is Intent.INVENTORY_SQL


def test_english_procedural_question_routes_to_general_chat():
    result = classify_intent("How do I borrow a laptop?")
    assert result.intent is Intent.GENERAL_CHAT


def test_french_procedural_question_routes_to_general_chat():
    result = classify_intent("Comment emprunter un ordinateur ?")
    assert result.intent is Intent.GENERAL_CHAT


def test_follow_up_routes_to_sql_with_history():
    result = classify_intent("only Dell ones", has_history=True)
    assert result.intent is Intent.INVENTORY_SQL


def test_french_follow_up_routes_to_sql_with_history():
    result = classify_intent("seulement les Dell", has_history=True)
    assert result.intent is Intent.INVENTORY_SQL
