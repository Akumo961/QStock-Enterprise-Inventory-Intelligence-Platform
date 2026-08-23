"""Read-only SQL execution for the AI assistant."""

import logging
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MAX_ROWS = 100
QUERY_TIMEOUT_MS = 10_000

_REDACTED_COLUMN_NAMES = {
    "hashed_password",
    "password",
    "qr_code_image",
    "qr_code_data",
    "secret",
    "api_key",
    "access_token",
    "refresh_token",
}

_LIMIT_RE = re.compile(r"\bLIMIT\s+\d+\b", re.IGNORECASE)


class SQLExecutor:
    """Executes already-validated SELECT statements with row/time limits."""

    def __init__(self, max_rows: int = MAX_ROWS, timeout_ms: int = QUERY_TIMEOUT_MS):
        self.max_rows = max_rows
        self.timeout_ms = timeout_ms

    def execute(self, db: Session, sql: str) -> list[dict[str, Any]]:
        db.execute(text(f"SET LOCAL statement_timeout = {self.timeout_ms}"))

        limited_sql = self._ensure_limit(sql)
        result = db.execute(text(limited_sql))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchmany(self.max_rows)]

        redacted_cols = [column for column in columns if column.lower() in _REDACTED_COLUMN_NAMES]
        if redacted_cols:
            logger.warning("Redacting restricted AI result columns: %s", redacted_cols)
            for row in rows:
                for column in redacted_cols:
                    row.pop(column, None)

        return rows

    def _ensure_limit(self, sql: str) -> str:
        if _LIMIT_RE.search(sql):
            return sql
        return f"{sql.rstrip(';')} LIMIT {self.max_rows}"


def preview_rows(rows: list[dict[str, Any]], limit: int = 3) -> str:
    """Compact row preview for conversation memory."""
    if not rows:
        return "No rows."

    lines: list[str] = []
    for row in rows[:limit]:
        pairs = ", ".join(f"{key}={value}" for key, value in row.items())
        lines.append(pairs)
    if len(rows) > limit:
        lines.append(f"... {len(rows) - limit} more row(s)")
    return " | ".join(lines)
