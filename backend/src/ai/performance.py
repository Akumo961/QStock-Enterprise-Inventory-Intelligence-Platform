"""Lightweight, dependency-free performance and cost instrumentation for QStock AI.

This module intentionally keeps metrics in-process so the assistant does not
require Redis, Prometheus, or another service just to measure itself locally.
It is suitable for development/CI benchmarks and can later be adapted to an
external metrics backend without changing the AI pipeline API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from threading import Lock
from typing import Iterable


@dataclass(frozen=True)
class AIRequestMetric:
    total_ms: float
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    deterministic_answer: bool = False
    sql_template_hit: bool = False


@dataclass
class AIMetricsSnapshot:
    requests: int
    total_ms_p50: float
    total_ms_p95: float
    llm_calls_total: int
    input_tokens_total: int
    output_tokens_total: int
    estimated_cost_usd: float
    deterministic_answer_rate: float
    template_hit_rate: float


class AIMetrics:
    """Thread-safe bounded in-memory metrics collector."""

    def __init__(self, max_samples: int = 1000) -> None:
        self.max_samples = max(1, max_samples)
        self._samples: list[AIRequestMetric] = []
        self._lock = Lock()

    def record(self, metric: AIRequestMetric) -> None:
        with self._lock:
            self._samples.append(metric)
            if len(self._samples) > self.max_samples:
                del self._samples[: len(self._samples) - self.max_samples]

    def snapshot(self) -> AIMetricsSnapshot:
        with self._lock:
            samples = list(self._samples)

        if not samples:
            return AIMetricsSnapshot(0, 0.0, 0.0, 0, 0, 0, 0.0, 0.0, 0.0)

        latencies = sorted(sample.total_ms for sample in samples)
        p50 = _percentile(latencies, 0.50)
        p95 = _percentile(latencies, 0.95)
        count = len(samples)
        return AIMetricsSnapshot(
            requests=count,
            total_ms_p50=p50,
            total_ms_p95=p95,
            llm_calls_total=sum(s.llm_calls for s in samples),
            input_tokens_total=sum(s.input_tokens for s in samples),
            output_tokens_total=sum(s.output_tokens for s in samples),
            estimated_cost_usd=sum(s.estimated_cost_usd for s in samples),
            deterministic_answer_rate=sum(s.deterministic_answer for s in samples) / count,
            template_hit_rate=sum(s.sql_template_hit for s in samples) / count,
        )

    def clear(self) -> None:
        with self._lock:
            self._samples.clear()


def _percentile(values: Iterable[float], percentile: float) -> float:
    values = list(values)
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    index = (len(values) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    weight = index - lower
    return values[lower] + (values[upper] - values[lower]) * weight


# Shared process-local collector. It is deliberately not persisted and must
# never contain prompts, SQL, user IDs, emails, or other user data.
ai_metrics = AIMetrics()
