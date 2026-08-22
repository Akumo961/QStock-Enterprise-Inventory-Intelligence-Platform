from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import get_current_user
from src.models.user import User
from src.ai.schemas import ChatRequest, ChatResponse
from src.ai import memory as conversation_memory
from src.ai import policy
from src.ai import service as ai_service
from src.ai.followup_context import resolve_follow_up
from src.core.config import settings

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    # The request schema already enforces the HTTP size boundary. Normalize
    # whitespace once at the API boundary so downstream routing, memory, and
    # prompt construction receive the same canonical question.
    question = policy.validate_user_message(body.message)

    # Phase 7: resolve clearly underspecified follow-ups before the SQL/intent
    # pipeline sees them. The original question is still passed as the display
    # question so the UI and conversation memory preserve what the user typed.
    max_turns = getattr(settings, "AI_MAX_HISTORY_TURNS", conversation_memory.DEFAULT_MAX_TURNS)
    history = conversation_memory.get_turn_metadata(current_user.id, max_turns=max_turns)
    follow_up = resolve_follow_up(question, history)
    query_question = follow_up.resolved_question

    # Keep authenticated identity as application context rather than allowing
    # the raw request body to masquerade as trusted metadata. The AI pipeline
    # receives the resolved query separately from the original display text.
    enriched_message = (
        "Authenticated User:\n"
        f"id={current_user.id}\n"
        f"name={current_user.full_name}\n"
        f"email={current_user.email}\n"
        f"department={current_user.department}\n"
        f"is_admin={current_user.is_admin}\n\n"
        "User Question:\n"
        f"{query_question}"
    )

    return ai_service.handle_chat(
        db=db,
        user_message=enriched_message,
        requesting_user_id=current_user.id,
        language=body.language,
        display_question=question,
    )
