from src.ai.location_templates import maybe_build_location_template_sql
from src.ai.response_generator import deterministic_list_answer, fallback_format_rows
from src.ai.sql_guard import validate_sql


def test_available_in_location_is_planned_before_global_available_template():
    template = maybe_build_location_template_sql("What is available in A1?")

    assert template is not None
    assert "lower(i.location) = lower('a1')" in template.sql.lower()
    assert "i.status = 'available'" in template.sql
    assert "i.available_quantity > 0" in template.sql


def test_french_available_in_location_is_planned():
    template = maybe_build_location_template_sql("Qu'est-ce qui est disponible à A1 ?")

    assert template is not None
    assert "lower(i.location) = lower('a1')" in template.sql.lower()
    assert "i.available_quantity > 0" in template.sql


def test_location_count_returns_deterministic_aggregate_shape():
    template = maybe_build_location_template_sql("How many items are available in A1?")

    assert template is not None
    assert "COUNT(*) AS item_records" in template.sql
    assert "total_available_quantity" in template.sql
    ok, reason = validate_sql(template.sql)
    assert ok, reason


def test_location_list_answer_uses_natural_wording():
    answer = deterministic_list_answer(
        [{
            "id": 1,
            "name": "Projector",
            "status": "available",
            "quantity": 2,
            "available_quantity": 1,
            "location": "A1",
        }],
        "en",
    )

    assert answer is not None
    assert answer.startswith("I found 1 available item(s) in A1:")
    assert "Found 1 result(s)" not in answer


def test_french_location_list_answer_is_natural():
    answer = deterministic_list_answer(
        [{
            "id": 1,
            "name": "Projecteur",
            "status": "available",
            "quantity": 2,
            "available_quantity": 1,
            "location": "A1",
        }],
        "fr",
    )

    assert answer is not None
    assert answer.startswith("J’ai trouvé 1 article(s) disponible(s) à A1 :")


def test_fallback_is_user_facing_not_debug_style():
    answer = fallback_format_rows(
        [{"name": "Projector", "location": "A1", "status": "available"}],
        "en",
    )

    assert answer.startswith("Here are the results:")
    assert "Found 1 result(s)" not in answer
