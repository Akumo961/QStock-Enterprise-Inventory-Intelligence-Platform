"""LLM SQL generation with validation-aware retries."""

from dataclasses import dataclass
import logging
import re
import time
from typing import Any

from src.ai.prompts import build_system_prompt, build_user_prompt
from src.ai.query_planner import plan_inventory_query
from src.ai.query_templates import maybe_build_template_sql
from src.ai.sql_guard import validate_sql
from src.core.config import settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SQLGenerationResult:
    sql: str | None
    raw_sql: str | None
    description: str
    error: str | None = None
    attempts: int = 1


def parse_llm_sql_output(raw: str) -> tuple[str | None, str]:
    """Extract SQL or NO_SQL clarification from the model response."""
    raw = (raw or "").strip()

    if raw.upper().startswith("NO_SQL"):
        explanation = raw[len("NO_SQL"):].lstrip(": \n\t")
        return None, explanation

    parts = re.split(r"\n\s*\n", raw, maxsplit=1)
    sql_part = parts[0].strip()
    description = parts[1].strip() if len(parts) > 1 else ""

    sql_part = re.sub(r"^```[a-zA-Z]*\n?", "", sql_part).strip()
    sql_part = re.sub(r"\n?```$", "", sql_part).strip()

    return sql_part, description


class SQLGenerator:
    """Generate safe SQL using deterministic planning before the LLM."""

    def __init__(self, provider: Any, max_attempts: int = 2):
        self.provider = provider
        self.max_attempts = max(1, max_attempts)

    def generate(
        self,
        *,
        question: str,
        language: str,
        history_messages: list[dict[str, str]],
        history_summary: str,
        last_sql: str,
        timing: dict[str, float] | None = None,
    ) -> SQLGenerationResult:
        timing = timing if timing is not None else {}
        timing.setdefault("prompt_build", 0.0)
        timing.setdefault("ollama_sql", 0.0)
        timing.setdefault("validation", 0.0)
        timing.setdefault("template_match", 0.0)
        timing.setdefault("query_plan", 0.0)

        # High-confidence semantic planning runs before legacy templates and
        # before any LLM call. This prevents question words ("how many",
        # "combien", "which", "quels", "montre-moi") from being interpreted
        # as item-name search terms.
        t0 = time.time()
        planned = plan_inventory_query(question)
        timing["query_plan"] += time.time() - t0
        if planned:
            t0 = time.time()
            ok, sql_or_reason = validate_sql(planned.sql)
            timing["validation"] += time.time() - t0
            if ok:
                logger.info("Deterministic query plan | intent=%s | %s", planned.intent, planned.description)
                return SQLGenerationResult(
                    sql=sql_or_reason,
                    raw_sql=planned.sql,
                    description=planned.description,
                    attempts=0,
                )
            logger.warning("Rejected deterministic query plan: %s", sql_or_reason)

        # Existing deterministic templates remain the next fast path.
        t0 = time.time()
        template = maybe_build_template_sql(question, history_summary=history_summary, last_sql=last_sql)
        timing["template_match"] += time.time() - t0
        if template:
            t0 = time.time()
            ok, sql_or_reason = validate_sql(template.sql)
            timing["validation"] += time.time() - t0
            if ok:
                return SQLGenerationResult(
                    sql=sql_or_reason,
                    raw_sql=template.sql,
                    description=template.description,
                    attempts=0,
                )
            logger.warning("Rejected internal SQL template: %s", sql_or_reason)

        retry_reason: str | None = None
        last_raw_sql: str | None = None
        last_description = ""

        max_tokens = getattr(settings, "AI_SQL_MAX_TOKENS", 300)
        num_ctx = getattr(settings, "AI_SQL_NUM_CTX", 4096)

        for attempt in range(1, self.max_attempts + 1):
            t0 = time.time()
            messages = (
                [{"role": "system", "content": build_system_prompt(language, retry_reason=retry_reason)}]
                + history_messages
                + [
                    {
                        "role": "user",
                        "content": build_user_prompt(
                            question=question,
                            history_summary=history_summary,
                            last_sql=last_sql,
                        ),
                    }
                ]
            )
            timing["prompt_build"] += time.time() - t0

            raw = self.provider.complete(
                messages,
                max_tokens=max_tokens,
                temperature=0.0 if attempt == 1 else 0.15,
                num_ctx=num_ctx,
            )
            timing["ollama_sql"] += getattr(self.provider, "last_elapsed", 0.0)

            raw_sql, description = parse_llm_sql_output(raw)
            last_raw_sql = raw_sql
            last_description = description

            if raw_sql is None:
                retry_reason = (
                    "The previous attempt returned NO_SQL. Try again using the schema, "
                    "synonym rules, and conversation context. If a precise answer is "
                    "impossible, ask one clarification question."
                )
                continue

            t0 = time.time()
            ok, sql_or_reason = validate_sql(raw_sql)
            timing["validation"] += time.time() - t0
            if ok:
                return SQLGenerationResult(
                    sql=sql_or_reason,
                    raw_sql=raw_sql,
                    description=description,
                    attempts=attempt,
                )

            retry_reason = f"SQL validation failed: {sql_or_reason}. Previous SQL: {raw_sql}"
            logger.info("SQL generation attempt %d failed validation: %s", attempt, sql_or_reason)

        return SQLGenerationResult(
            sql=None,
            raw_sql=last_raw_sql,
            description=last_description,
            error=retry_reason or "SQL generation failed.",
            attempts=self.max_attempts,
        )
