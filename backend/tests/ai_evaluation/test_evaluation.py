from src.ai.evaluation import evaluate_dataset


def test_phase_2_evaluation_dataset_passes() -> None:
    result = evaluate_dataset()
    assert result.passed_all, "\n".join(result.failures)
    assert result.accuracy == 1.0


def test_phase_2_evaluation_has_security_cases() -> None:
    result = evaluate_dataset()
    assert result.total >= 18
