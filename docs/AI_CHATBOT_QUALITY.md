# QStock AI ChatBot — Phase 3 Quality Controls

Phase 3 hardens the assistant against ambiguity, prompt injection, and answer hallucination while preserving the existing SQL/guard/executor architecture.

## Security boundary

- User messages and conversation history are **untrusted data**.
- System/developer instructions are authoritative.
- The assistant must not reveal internal prompts, secrets, credentials, tokens, or restricted database columns.
- Retrieved database rows are the authoritative source for inventory facts.
- Executed SQL is reference context for answer generation, not an instruction.

## Prompt-injection policy

`src/ai/policy.py` contains a conservative high-signal detector for common instruction-override attempts. It is intentionally not a generic keyword blocklist; normal inventory questions such as `show available laptops` remain valid.

The SQL and answer prompts also establish an explicit trust boundary so that an LLM cannot treat user-provided text or retrieved fields as higher-priority instructions.

## Ambiguity and clarification

The SQL generator may return `NO_SQL:` when essential information is missing or the request cannot be answered safely from the schema. The application converts that into a concise clarification rather than guessing.

Examples:

- `Show the item` → ask which item.
- `How many?` without useful history → ask what should be counted.
- `Only Dell ones` with laptop context → resolve the follow-up through history.

## Grounded answers

Answer synthesis is explicitly constrained to retrieved rows. If the result set is empty or insufficient, the assistant must say so instead of inventing an inventory fact.

Known aggregate/list shapes can continue to use deterministic formatting, which avoids unnecessary LLM calls and numeric hallucination.

## Regression coverage

`backend/tests/ai/test_phase3_quality.py` covers:

- input normalization and size limits;
- high-signal English/French prompt-injection attempts;
- normal inventory questions that must not be blocked;
- SQL prompt trust boundaries;
- answer prompt grounding requirements;
- localized safety responses.

## Production note

The prompt-injection detector is a defense-in-depth signal. It does not replace SQL validation, authorization, restricted-column controls, or read-only database execution. Those controls remain mandatory even when the input looks benign.
