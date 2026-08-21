from src.ai.intent import Intent, classify_intent
from src.ai.query_planner import plan_inventory_query


def test_english_item_existence_routes_to_inventory_sql():
    result = classify_intent("Do we have scissors?")
    assert result.intent == Intent.INVENTORY_SQL
    assert result.confidence >= 0.9


def test_french_item_existence_routes_to_inventory_sql():
    result = classify_intent("Avons-nous des ciseaux ?")
    assert result.intent == Intent.INVENTORY_SQL


def test_item_existence_planner_resolves_canonical_name():
    plan = plan_inventory_query("Do we have scissors?")
    assert plan is not None
    assert plan.intent == "find_item"
    assert "LOWER(i.name) = LOWER('Ciseaux')" in plan.sql


def test_item_existence_planner_resolves_projector():
    plan = plan_inventory_query("Do we have a projector?")
    assert plan is not None
    assert plan.intent == "find_item"
    assert "LOWER(i.name) = LOWER('Projecteur')" in plan.sql
