# ruff: noqa
from src.ai.followup_context import resolve_follow_up
from src.ai.memory import TurnMetadata


def _history(*questions: str) -> list[TurnMetadata]:
    return [TurnMetadata(question=q, answer="ok") for q in questions]


def test_quantity_followup_resolves_previous_item():
    result = resolve_follow_up(
        "How many are available?", _history("Do we have scissors?")
    )
    assert result.changed is True
    assert result.item is not None
    assert result.item.canonical_name == "Ciseaux"
    assert result.resolved_question == "How many Ciseaux are available?"


def test_location_followup_resolves_previous_item():
    result = resolve_follow_up(
        "Where are they?", _history("Do you have a projector?")
    )
    assert result.changed is True
    assert result.resolved_question == "Where is Projecteur?"


def test_availability_followup_resolves_previous_item_in_french():
    result = resolve_follow_up(
        "Sont-ils disponibles ?", _history("Avons-nous des ciseaux ?")
    )
    assert result.changed is True
    assert result.resolved_question == "Le Ciseaux est-il disponible ?"


def test_explicit_item_wins_over_context():
    result = resolve_follow_up(
        "How many projectors are available?",
        _history("Do we have scissors?"),
    )
    assert result.changed is False
    assert result.item is not None
    assert result.item.canonical_name == "Projecteur"
    assert result.resolved_question == "How many projectors are available?"


def test_unrelated_question_is_not_rewritten():
    result = resolve_follow_up(
        "What is the weather today?", _history("Do we have scissors?")
    )
    assert result.changed is False
    assert result.item is None
    assert result.resolved_question == "What is the weather today?"


def test_without_history_followup_remains_unchanged():
    result = resolve_follow_up("How many are available?", [])
    assert result.changed is False
    assert result.item is None
    assert result.resolved_question == "How many are available?"
