# QStock AI Performance & Cost

Phase 4 establishes a measurable performance baseline without adding a mandatory external observability dependency.

## What is already optimized

- SQL templates bypass the LLM for known query shapes.
- Simple aggregate/list responses can bypass answer-generation LLM calls.
- Ollama uses an explicit read timeout and HTTP connection pooling.
- Ollama keeps the model alive for 30 minutes between requests.
- Qwen thinking is disabled for deterministic SQL/answer workloads.
- SQL and answer context/token budgets are configurable.

## Metrics

`src/ai/performance.py` provides a bounded in-process collector for aggregate:

- request count
- total latency p50/p95
- LLM call count
- input/output token totals
- estimated cost
- deterministic-answer rate
- SQL-template hit rate

The collector must never receive prompts, SQL, user IDs, emails, or other PII.

## Offline benchmark

From `backend/`:

```bash
python scripts/benchmark_ai_performance.py
```

The benchmark deliberately performs no network or database calls. It measures the cheap deterministic routing path and provides a regression baseline.

## Live production benchmark

For a representative deployed dataset, collect at least 100 requests and report:

| Metric | Target |
|---|---:|
| p50 total latency | < 2 s for deterministic paths |
| p95 total latency | < 5 s for deterministic paths |
| LLM calls / simple list query | 0 |
| LLM calls / template query | 0 for SQL + 0 for deterministic answer |
| SQL execution timeout | 10 s hard limit |
| answer context rows | <= configured limit |

LLM-backed requests depend on the selected model, hardware and network, so their latency must be measured in the actual deployment rather than claimed from local code.

## Cost accounting

For providers that expose token usage, populate `AIRequestMetric.input_tokens` and `output_tokens`, then calculate cost using the provider/model price table configured for the deployment. Never hard-code a stale price into application correctness logic.

## Performance regression rule

A future change should not be merged if it materially increases p95 latency, LLM calls, or token consumption for the same evaluation dataset without an explicit reason documented in the PR.
