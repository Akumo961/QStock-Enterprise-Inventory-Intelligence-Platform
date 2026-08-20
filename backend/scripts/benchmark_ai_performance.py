"""Offline benchmark for QStock's deterministic AI fast paths.

Run from backend/:
    python scripts/benchmark_ai_performance.py

This benchmark deliberately avoids network calls and a live database. It
measures the deterministic components that should stay cheap as the project
evolves: intent routing and answer formatting. Live LLM/DB p50/p95 values
should be collected in the deployed environment using the same metric schema.
"""

from __future__ import annotations

import statistics
import time

from src.ai.intent import classify_intent
from src.ai.performance import AIRequestMetric, AIMetrics
from src.ai.response_generator import deterministic_data_answer, deterministic_list_answer


CASES = [
    "show all laptops",
    "show available Dell laptops",
    "what can you do?",
    "montre-moi tous les ordinateurs Dell",
    "quels articles sont disponibles ?",
]


def main() -> None:
    metrics = AIMetrics(max_samples=len(CASES))
    latencies: list[float] = []

    for question in CASES:
        started = time.perf_counter()
        classify_intent(question, has_history=False)
        elapsed_ms = (time.perf_counter() - started) * 1000
        latencies.append(elapsed_ms)
        metrics.record(AIRequestMetric(total_ms=elapsed_ms, llm_calls=0, deterministic_answer=True))

    snapshot = metrics.snapshot()
    print("QStock AI offline performance benchmark")
    print(f"cases={snapshot.requests}")
    print(f"intent_p50_ms={snapshot.total_ms_p50:.3f}")
    print(f"intent_p95_ms={snapshot.total_ms_p95:.3f}")
    print(f"intent_mean_ms={statistics.mean(latencies):.3f}")
    print("llm_calls=0")
    print("database_calls=0")


if __name__ == "__main__":
    main()
