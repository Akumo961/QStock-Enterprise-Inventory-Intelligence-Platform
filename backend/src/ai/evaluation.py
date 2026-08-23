"""Offline evaluation harness for QStock AI routing and SQL safety.

The evaluator intentionally has no LLM, database, network, or application-state
requirements. This makes it safe to run in CI and useful for regression testing.
Live answer/latency evaluation remains separate because those metrics depend on
configured providers and representative inventory data.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.ai.intent import classify_intent
from src.ai.sql_guard import validate_sql

DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "tests" / "ai_evaluation" / "dataset.json"


@dataclass(frozen=True)
class EvaluationResult:
    total: int
    passed: int
    failed: int
    accuracy: float
    failures: tuple[str, ...]
    elapsed_ms: float

    @property
    def passed_all(self) -> bool:
        return self.failed == 0


def load_dataset(path: str | Path = DEFAULT_DATASET) -> list[dict[str, Any]]:
    """Load the versioned evaluation dataset."""
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise TypeError("AI evaluation dataset must be a JSON array")
    return payload


def evaluate_dataset(path: str | Path = DEFAULT_DATASET) -> EvaluationResult:
    """Evaluate deterministic routing and SQL safety cases."""
    cases = load_dataset(path)
    failures: list[str] = []
    passed = 0
    started = time.perf_counter()

    for case in cases:
        case_id = case.get("id", "unknown")
        if "expected_intent" in case:
            result = classify_intent(
                case.get("message", ""),
                has_history=bool(case.get("has_history", False)),
            )
            actual = result.intent.value
            expected = case["expected_intent"]
            ok = actual == expected
            if not ok:
                failures.append(
                    f"{case_id}: intent expected={expected} actual={actual} confidence={result.confidence:.2f}"
                )
        elif "expected_valid" in case:
            actual, reason = validate_sql(case.get("sql", ""))
            expected = bool(case["expected_valid"])
            ok = actual == expected
            if not ok:
                failures.append(f"{case_id}: sql_valid expected={expected} actual={actual} reason={reason}")
        else:
            failures.append(f"{case_id}: unsupported evaluation case")
            ok = False

        if ok:
            passed += 1

    elapsed_ms = (time.perf_counter() - started) * 1000
    total = len(cases)
    accuracy = passed / total if total else 1.0
    return EvaluationResult(
        total=total,
        passed=passed,
        failed=total - passed,
        accuracy=accuracy,
        failures=tuple(failures),
        elapsed_ms=elapsed_ms,
    )


def format_report(result: EvaluationResult) -> str:
    """Return a concise CI-friendly evaluation report."""
    lines = [
        "QStock AI Evaluation",
        f"Total: {result.total}",
        f"Passed: {result.passed}",
        f"Failed: {result.failed}",
        f"Accuracy: {result.accuracy:.1%}",
        f"Evaluation latency: {result.elapsed_ms:.1f} ms",
    ]
    if result.failures:
        lines.append("Failures:")
        lines.extend(f"- {failure}" for failure in result.failures)
    return "\n".join(lines)


if __name__ == "__main__":
    result = evaluate_dataset()
    print(format_report(result))
    raise SystemExit(0 if result.passed_all else 1)
