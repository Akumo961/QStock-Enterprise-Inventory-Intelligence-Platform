from src.ai.performance import AIRequestMetric, AIMetrics


def test_ai_metrics_calculates_p50_and_p95():
    metrics = AIMetrics(max_samples=10)
    for latency in (100.0, 200.0, 300.0, 400.0, 500.0):
        metrics.record(AIRequestMetric(total_ms=latency))

    snapshot = metrics.snapshot()

    assert snapshot.requests == 5
    assert snapshot.total_ms_p50 == 300.0
    assert snapshot.total_ms_p95 == 480.0


def test_ai_metrics_tracks_llm_cost_and_fast_paths():
    metrics = AIMetrics(max_samples=10)
    metrics.record(
        AIRequestMetric(
            total_ms=100.0,
            llm_calls=1,
            input_tokens=100,
            output_tokens=20,
            estimated_cost_usd=0.01,
            deterministic_answer=True,
            sql_template_hit=True,
        )
    )
    metrics.record(
        AIRequestMetric(
            total_ms=200.0,
            llm_calls=2,
            input_tokens=200,
            output_tokens=40,
            estimated_cost_usd=0.02,
        )
    )

    snapshot = metrics.snapshot()

    assert snapshot.llm_calls_total == 3
    assert snapshot.input_tokens_total == 300
    assert snapshot.output_tokens_total == 60
    assert snapshot.estimated_cost_usd == 0.03
    assert snapshot.deterministic_answer_rate == 0.5
    assert snapshot.template_hit_rate == 0.5


def test_ai_metrics_is_bounded():
    metrics = AIMetrics(max_samples=2)
    metrics.record(AIRequestMetric(total_ms=100.0))
    metrics.record(AIRequestMetric(total_ms=200.0))
    metrics.record(AIRequestMetric(total_ms=300.0))

    snapshot = metrics.snapshot()

    assert snapshot.requests == 2
    assert snapshot.total_ms_p50 == 250.0
