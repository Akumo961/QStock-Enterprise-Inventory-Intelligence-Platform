from src.ai.intent import Intent, classify_intent
from src.ai.query_planner import plan_inventory_query


def _assert_find_item(question: str, canonical_name: str) -> None:
    intent = classify_intent(question)
    assert intent.intent == Intent.INVENTORY_SQL
    plan = plan_inventory_query(question)
    assert plan is not None
    assert plan.intent == "find_item"
    assert f"LOWER(i.name) = LOWER('{canonical_name}')" in plan.sql


def test_do_you_have_scissors():
    _assert_find_item("Do you have scissors?", "Ciseaux")


def test_is_there_a_projector():
    _assert_find_item("Is there a projector?", "Projecteur")


def test_are_there_any_pencils():
    _assert_find_item("Are there any pencils?", "Crayon à mine")


def test_avez_vous_des_ciseaux():
    _assert_find_item("Avez-vous des ciseaux ?", "Ciseaux")


def test_y_a_t_il_un_projecteur():
    _assert_find_item("Y a-t-il un projecteur ?", "Projecteur")


def test_existence_question_preserves_location():
    plan = plan_inventory_query("Do you have scissors in A1?")
    assert plan is not None
    assert plan.intent == "find_item"
    assert "LOWER(i.name) = LOWER('Ciseaux')" in plan.sql
    assert "LOWER(i.location) = LOWER('a1')" in plan.sql
