from src.ai.intent import Intent, classify_intent


def test_french_where_item_question_routes_to_sql():
    result = classify_intent("Où sont les Ciseaux ?")
    assert result.intent == Intent.INVENTORY_SQL


def test_french_where_item_singular_routes_to_sql():
    result = classify_intent("Où est le Projecteur ?")
    assert result.intent == Intent.INVENTORY_SQL


def test_french_location_question_routes_to_sql():
    result = classify_intent("Quels articles sont à A1 ?")
    assert result.intent == Intent.INVENTORY_SQL


def test_english_location_question_routes_to_sql():
    result = classify_intent("What items are in A1?")
    assert result.intent == Intent.INVENTORY_SQL


def test_general_help_question_stays_general():
    result = classify_intent("What can you do?")
    assert result.intent == Intent.GENERAL_CHAT
