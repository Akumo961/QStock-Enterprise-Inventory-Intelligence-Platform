from src.ai.query_planner import plan_inventory_query


def test_how_many_items_in_stock_uses_quantity_not_listing():
    plan = plan_inventory_query("How many items do we currently have in stock?")
    assert plan is not None
    assert plan.intent == "sum_quantity"
    assert "SUM(i.quantity)" in plan.sql
    assert "SUM(i.available_quantity)" in plan.sql
    assert "COUNT(*)" in plan.sql
    assert "ILIKE" not in plan.sql


def test_combien_items_en_stock_uses_quantity_not_word_combien_as_filter():
    plan = plan_inventory_query("Combien d'items avons-nous en stock ?")
    assert plan is not None
    assert plan.intent == "sum_quantity"
    assert "SUM(i.quantity)" in plan.sql
    assert "ILIKE" not in plan.sql


def test_how_many_available_items_uses_only_available_inventory():
    plan = plan_inventory_query("How many items are currently available?")
    assert plan is not None
    assert plan.intent == "count_available"
    assert "SUM(i.available_quantity)" in plan.sql
    assert "COUNT(*) FILTER (WHERE i.status = 'available')" in plan.sql
    assert "maintenance" not in plan.sql.lower()
    assert "ILIKE" not in plan.sql


def test_how_many_items_in_maintenance_is_status_specific():
    plan = plan_inventory_query("How many items are in maintenance?")
    assert plan is not None
    assert plan.intent == "count_maintenance"
    assert "WHERE i.status = 'maintenance'" in plan.sql
    assert "SUM(i.quantity)" in plan.sql
    assert "ILIKE" not in plan.sql


def test_how_many_different_items_counts_records():
    plan = plan_inventory_query("How many different items do we have?")
    assert plan is not None
    assert plan.intent == "count_records"
    assert "COUNT(*)" in plan.sql
    assert "ILIKE" not in plan.sql


def test_what_items_do_we_have_is_a_list_query():
    plan = plan_inventory_query("What items do we have?")
    assert plan is not None
    assert plan.intent == "list_items"
    assert "FROM items AS i" in plan.sql
    assert "ORDER BY i.name" in plan.sql
    assert "LIMIT 100" in plan.sql
    assert "ILIKE" not in plan.sql


def test_french_inventory_list_is_a_list_query():
    plan = plan_inventory_query("Quels articles avons-nous en stock ?")
    assert plan is not None
    assert plan.intent == "list_items"
    assert "FROM items AS i" in plan.sql
    assert "ORDER BY i.name" in plan.sql


def test_french_available_listing_is_a_list_query():
    plan = plan_inventory_query("Quels sont les items disponibles ?")
    assert plan is not None
    assert plan.intent == "list_available"
    assert "available_quantity > 0" in plan.sql
    assert "ORDER BY i.name" in plan.sql


def test_show_available_items_is_not_ambiguous():
    plan = plan_inventory_query("Show me the available items")
    assert plan is not None
    assert plan.intent == "list_available"


def test_french_item_location_question_resolves_item():
    plan = plan_inventory_query("Où sont les Ciseaux ?")
    assert plan is not None
    assert plan.intent == "locate_item"
    assert "LOWER(i.name) = LOWER('Ciseaux')" in plan.sql
    assert "LOWER(i.location)" not in plan.sql


def test_english_item_location_question_resolves_item():
    plan = plan_inventory_query("Where is the projector?")
    assert plan is not None
    assert plan.intent == "locate_item"
    assert "LOWER(i.name) = LOWER('Projecteur')" in plan.sql


def test_location_list_is_scoped():
    plan = plan_inventory_query("What items are in A1?")
    assert plan is not None
    assert plan.intent == "list_location"
    assert "LOWER(i.location) = LOWER('a1')" in plan.sql
    assert "ORDER BY i.name" in plan.sql
    assert "LIMIT 100" in plan.sql


def test_french_location_list_is_scoped():
    plan = plan_inventory_query("Quels articles sont à A5 ?")
    assert plan is not None
    assert plan.intent == "list_location"
    assert "LOWER(i.location) = LOWER('a5')" in plan.sql


def test_location_count_is_not_global():
    plan = plan_inventory_query("How many items are available in A1?")
    assert plan is not None
    assert plan.intent == "count_available_location"
    assert "LOWER(i.location) = LOWER('a1')" in plan.sql
    assert "FROM items AS i" in plan.sql
