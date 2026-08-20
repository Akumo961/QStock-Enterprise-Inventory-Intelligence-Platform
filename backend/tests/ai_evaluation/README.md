# QStock AI Evaluation

Phase 2 introduces a deterministic regression harness for the AI assistant. It is intentionally safe to run without an LLM, database, network, or production credentials.

## What is measured

| Metric | Offline | Live |
|---|---:|---:|
| Intent accuracy | Yes | Yes |
| SQL safety/validation accuracy | Yes | Yes |
| Template coverage | Covered by SQL-generation tests | Yes |
| SQL generation success | No | Yes |
| SQL execution success | No | Yes |
| Answer correctness / groundedness | No | Yes |
| End-to-end latency | Harness latency | Yes |
| Provider/model/token cost | No | Yes |

The offline suite is the CI gate. Live metrics depend on representative inventory data and configured providers, so they must not be made deterministic by mocking away the behavior being measured.

## Run offline evaluation

From `backend/`:

```bash
python -m src.ai.evaluation
pytest tests/ai_evaluation/test_evaluation.py
```

The dataset contains English and French routing cases, follow-up cases, and adversarial SQL safety cases. A regression causes a non-zero exit code.

## Live evaluation protocol

For a production-quality benchmark, run a separate environment with a fixed seed dataset and capture:

- intent accuracy;
- template-hit rate;
- SQL generation success rate;
- SQL validation rejection rate;
- SQL execution success rate;
- answer correctness;
- answer groundedness;
- clarification rate;
- end-to-end p50/p95 latency;
- LLM calls per turn;
- input/output tokens and estimated cost;
- provider/model and evaluation timestamp.

Live results should be stored as versioned artifacts rather than hard-coded into tests, because inventory contents, provider versions, and model behavior can change.
