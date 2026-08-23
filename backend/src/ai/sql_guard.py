"""
Validates LLM-generated SQL before it is ever sent to the database.

Rules enforced
--------------
1. Only SELECT statements are allowed.
2. Banned keywords: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE.
3. Multiple statements (semicolons not at the very end) are rejected.
4. Empty / whitespace-only queries are rejected.
5. Wildcard SELECT is never allowed.
6. Sensitive columns (credentials, secrets, raw QR payloads) may never be
   selected, by name or via a wildcard on a table that contains them.

The guard works on the *raw* SQL string returned by the LLM, before any
execution attempt.  It is intentionally conservative: when in doubt, reject.
"""

import re

# ---------------------------------------------------------------------------
# Banned keyword patterns
# ---------------------------------------------------------------------------

_BANNED_KEYWORDS: list[str] = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
]

# Build a single compiled regex that catches any banned keyword used as a
# SQL token (surrounded by word boundaries so e.g. "created_at" is fine).
_BANNED_RE = re.compile(
    r"\b(?:" + "|".join(_BANNED_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Multiple-statement detector: semicolons that are NOT at the very end of the
# trimmed string indicate a second statement.
_MULTI_STMT_RE = re.compile(r";(?!\s*$)")

# ---------------------------------------------------------------------------
# Sensitive-data protection.
#
# The AI assistant is exposed to every authenticated user, not just admins
# (see src/api/endpoints/ai.py — only `get_current_user` is required). The
# documented SCHEMA_DESCRIPTION in prompts.py intentionally never mentions
# these columns, but an LLM can still guess common column names (e.g.
# "hashed_password") and the database itself has no column-level ACL for
# this read-only connection. These checks are the actual enforcement point.
# ---------------------------------------------------------------------------

_SENSITIVE_COLUMNS: list[str] = [
    "hashed_password",
    "password",
    "qr_code_image",   # large base64 PNG payload, not useful to a chat answer
    "secret",
    "api_key",
    "access_token",
    "refresh_token",
]

_SENSITIVE_COLUMN_RE = re.compile(
    r"\b(?:" + "|".join(_SENSITIVE_COLUMNS) + r")\b",
    re.IGNORECASE,
)

# A bare `SELECT *` (or `SELECT alias.*`) against the `users` table would
# pull hashed_password/qr_code_image/qr_code_data along with everything
# else, even though no single forbidden column name appears in the query
# text. Block wildcard selection whenever "users" appears anywhere in the
# statement (covers `FROM users`, `JOIN users`, aliased forms, etc.) — this
# is intentionally conservative.
_WILDCARD_RE = re.compile(
    r"\bSELECT\s+(?:\*|[a-zA-Z_][a-zA-Z0-9_]*\.\*)|,\s*(?:\*|[a-zA-Z_][a-zA-Z0-9_]*\.\*)",
    re.IGNORECASE,
)
_USERS_TABLE_RE = re.compile(r"\busers\b", re.IGNORECASE)

_COMMENT_RE = re.compile(r"(--|/\*)")
_TABLE_REFERENCE_RE = re.compile(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", re.IGNORECASE)
_ALLOWED_TABLES = {"items", "users", "transactions", "requests"}


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validate a SQL string.

    Returns
    -------
    (True, cleaned_sql)   — safe to execute
    (False, reason)       — must NOT be executed
    """
    if not sql or not sql.strip():
        return False, "Empty SQL query."

    cleaned = sql.strip()

    # ---- 1. Must start with SELECT ----------------------------------------
    first_token = cleaned.split()[0].upper()
    if first_token != "SELECT":
        return False, f"Only SELECT queries are allowed. Got: {first_token!r}."

    # ---- 2. No banned keywords --------------------------------------------
    match = _BANNED_RE.search(cleaned)
    if match:
        return False, f"Forbidden keyword detected: {match.group().upper()!r}."

    # ---- 3. No multiple statements ----------------------------------------
    if _MULTI_STMT_RE.search(cleaned):
        return False, "Multiple SQL statements are not allowed."

    # ---- 4. No comments ----------------------------------------------------
    if _COMMENT_RE.search(cleaned):
        return False, "SQL comments are not allowed."

    # ---- 5. No wildcard SELECT anywhere ------------------------------------
    if _WILDCARD_RE.search(cleaned):
        return False, "Wildcard SELECT is not allowed; select specific columns."

    # ---- 6. Only known application tables ----------------------------------
    referenced_tables = {match.group(1).lower() for match in _TABLE_REFERENCE_RE.finditer(cleaned)}
    unknown_tables = referenced_tables - _ALLOWED_TABLES
    if unknown_tables:
        return False, f"Query references unknown or disallowed table(s): {', '.join(sorted(unknown_tables))}."

    if not referenced_tables:
        return False, "Query must read from an allowed application table."

    # ---- 7. No sensitive columns by name -----------------------------------
    sensitive_match = _SENSITIVE_COLUMN_RE.search(cleaned)
    if sensitive_match:
        return False, f"Query references a restricted column: {sensitive_match.group()!r}."

    # ---- 8. No wildcard SELECT against the users table ---------------------
    if _USERS_TABLE_RE.search(cleaned) and _WILDCARD_RE.search(cleaned):
        return False, (
            "Wildcard SELECT against the users table is not allowed; "
            "select specific non-sensitive columns instead."
        )

    # ---- 9. Strip trailing semicolon for safety ---------------------------
    cleaned = cleaned.rstrip(";").strip()

    return True, cleaned
