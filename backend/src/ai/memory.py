
import threading
import time
from collections import deque
from dataclasses import dataclass

# (question, answer) pairs
_HistoryEntry = tuple[str, str]

_LOCK = threading.Lock()
_STORE: dict[int, deque[_HistoryEntry]] = {}
_META_STORE: dict[int, deque["TurnMetadata"]] = {}
_LAST_SEEN: dict[int, float] = {}

DEFAULT_MAX_TURNS = 3
DEFAULT_TTL_SECONDS = 30 * 60  # 30 minutes of inactivity


@dataclass(frozen=True)
class TurnMetadata:
    """Structured memory for follow-up SQL generation."""

    question: str
    answer: str
    sql: str = ""
    row_preview: str = ""
    intent: str = ""


def get_history(
    user_id: int,
    max_turns: int = DEFAULT_MAX_TURNS,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> list[_HistoryEntry]:
    """Return the recent (question, answer) history for a user, oldest first."""
    with _LOCK:
        _expire_if_stale(user_id, ttl_seconds)
        buf = _STORE.get(user_id)
        if not buf:
            return []
        return list(buf)[-max_turns:]


def add_turn(
    user_id: int,
    question: str,
    answer: str,
    max_turns: int = DEFAULT_MAX_TURNS,
    sql: str = "",
    row_preview: str = "",
    intent: str = "",
) -> None:
    """Record one (question, answer) turn for a user."""
    if not question or not answer:
        return
    with _LOCK:
        buf = _STORE.get(user_id)
        if buf is None or buf.maxlen != max_turns:
            buf = deque(buf or [], maxlen=max_turns)
            _STORE[user_id] = buf
        buf.append((question, answer))

        meta_buf = _META_STORE.get(user_id)
        if meta_buf is None or meta_buf.maxlen != max_turns:
            meta_buf = deque(meta_buf or [], maxlen=max_turns)
            _META_STORE[user_id] = meta_buf
        meta_buf.append(
            TurnMetadata(
                question=question,
                answer=answer,
                sql=sql or "",
                row_preview=row_preview or "",
                intent=intent or "",
            )
        )
        _LAST_SEEN[user_id] = time.time()


def get_turn_metadata(
    user_id: int,
    max_turns: int = DEFAULT_MAX_TURNS,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> list[TurnMetadata]:
    """Return recent structured turns, oldest first."""
    with _LOCK:
        _expire_if_stale(user_id, ttl_seconds)
        buf = _META_STORE.get(user_id)
        if not buf:
            return []
        return list(buf)[-max_turns:]


def get_context_summary(
    user_id: int,
    max_turns: int = DEFAULT_MAX_TURNS,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> str:
    """Build a compact text summary for follow-up-aware prompts."""
    turns = get_turn_metadata(user_id, max_turns=max_turns, ttl_seconds=ttl_seconds)
    if not turns:
        return ""

    lines: list[str] = []
    for index, turn in enumerate(turns, start=1):
        lines.append(f"{index}. User: {turn.question}")
        if turn.sql:
            lines.append(f"   SQL: {turn.sql}")
        if turn.row_preview:
            lines.append(f"   Rows: {turn.row_preview}")
        lines.append(f"   Assistant: {turn.answer}")
    return "\n".join(lines)


def get_last_sql(
    user_id: int,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> str:
    """Return the most recent successful SQL query for this user."""
    turns = get_turn_metadata(user_id, ttl_seconds=ttl_seconds)
    for turn in reversed(turns):
        if turn.sql:
            return turn.sql
    return ""


def clear(user_id: int) -> None:
    """Drop all stored history for a user (e.g. on explicit 'reset' action)."""
    with _LOCK:
        _STORE.pop(user_id, None)
        _META_STORE.pop(user_id, None)
        _LAST_SEEN.pop(user_id, None)


def _expire_if_stale(user_id: int, ttl_seconds: int) -> None:
    last_seen = _LAST_SEEN.get(user_id)
    if last_seen is not None and (time.time() - last_seen) > ttl_seconds:
        _STORE.pop(user_id, None)
        _META_STORE.pop(user_id, None)
        _LAST_SEEN.pop(user_id, None)
