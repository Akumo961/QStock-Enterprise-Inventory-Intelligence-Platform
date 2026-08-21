from src.ai.entity_resolver import normalize_text, resolve_item
from src.ai.query_planner import plan_inventory_query


def test_normalize_text_removes_accents_and_punctuation():
    assert normalize_text("Crayon à mine !") == "crayon a mine"


def test_english_scissors_resolve_to_french_canonical_name():
    result = resolve_item("How many scissors do we have?")
    assert result is not None
    assert result.canonical_name == "Ciseaux"
    assert result.source == "alias"


def test_english_projectors_resolve_to_projecteur():
    result = resolve_item("Where is the projector?")
    assert result is not None
    assert result.canonical_name == "Projecteur"


def test_english_pencils_resolve_to_crayon_a_mine():
    result = resolve_item("How many pencils do we have?")
    assert result is not None
    assert result.canonical_name == "Crayon à mine"


def test_french_canonical_name_resolves_without_translation():
    result = resolve_item("How many Ciseaux do we have?")
    assert result is not None
    assert result.canonical_name == "Ciseaux"
    assert result.source == "canonical"


def test_item_count_uses_item_name_and_sum_quantity():
    plan = plan_inventory_query("How many scissors do we have?")
    assert plan is not None
    assert plan.intent == "count_item"
    assert "SUM(i.quantity)" in plan.sql
    assert "LOWER(i.name) = LOWER('Ciseaux')" in plan.sql
    assert "FROM items AS i" in plan.sql


def test_item_available_count_is_filtered_to_item():
    plan = plan_inventory_query("How many scissors are available?")
    assert plan is not None
    assert plan.intent == "count_item_available"
    assert "SUM(i.available_quantity)" in plan.sql
    assert "LOWER(i.name) = LOWER('Ciseaux')" in plan.sql
    assert "i.available_quantity > 0" in plan.sql


def test_item_availability_is_not_a_global_inventory_list():
    plan = plan_inventory_query("Are the projectors available?")
    assert plan is not None
    assert plan.intent == "item_availability"
    assert "LOWER(i.name) = LOWER('Projecteur')" in plan.sql
    assert "i.status" in plan.sql


def test_item_location_is_resolved_to_item_query():
    plan = plan_inventory_query("Where is the projector?")
    assert plan is not None
    assert plan.intent == "locate_item"
    assert "LOWER(i.name) = LOWER('Projecteur')" in plan.sql
    assert "i.location" in plan.sql


def test_location_count_is_not_global():
    plan = plan_inventory_query("How many items are available in A1?")
    assert plan is not None
    assert plan.intent == "count_available_location"
    assert "LOWER(i.location) = LOWER('a1')" in plan.sql
    assert "SUM(i.available_quantity)" in plan.sql
    assert "WHERE i.status = 'available'" in plan.sql


def test_french_item_question_resolves_same_as_english_alias():
    plan = plan_inventory_query("Combien de Ciseaux avons-nous ?")
    assert plan is not None
    assert plan.intent == "count_item"
    assert "LOWER(i.name) = LOWER('Ciseaux')" in plan.sql


def test_global_maintenance_query_stays_global():
    plan = plan_inventory_query("How many items are in maintenance?")
    assert plan is not None
    assert plan.intent == "count_maintenance"
    assert "WHERE i.status = 'maintenance'" in plan.sql
    assert "LOWER(i.name)" not in plan.sql


def test_global_inventory_count_stays_global():
    plan = plan_inventory_query("How many units do we currently have in stock?")
    assert plan is not None
    assert plan.intent == "sum_quantity"
    assert "LOWER(i.name)" not in plan.sql
    assert "SUM(i.quantity)" in plan.sql


def test_generic_products_question_does_not_become_an_item_filter():
    result = resolve_item("What products are in our inventory?")
    assert result is None
    plan = plan_inventory_query("What products are in our inventory?")
    assert plan is None or "LOWER(i.name) = LOWER('products')" not in plan.sql


def test_generic_units_question_does_not_become_an_item_filter():
    result = resolve_item("How many units do we currently have in stock?")
    assert result is None


def test_all_items_available_does_not_become_an_item_filter():
    result = resolve_item("Are all our items available?")
    assert result is None


def test_pronoun_follow_up_does_not_become_an_item_filter():
    result = resolve_item("Where are they located?")
    assert result is None
