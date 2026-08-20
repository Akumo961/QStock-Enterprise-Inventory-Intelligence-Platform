from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import get_current_user
from src.models.user import User
from src.ai.schemas import ChatRequest, ChatResponse
from src.ai import policy
from src.ai import service as ai_service

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

    # Keep authenticated identity as application context rather than allowing
    # the raw request body to masquerade as trusted metadata. The AI pipeline
    # receives the user's question separately through display_question.
    enriched_message = (
        "Authenticated User:\n"
        f"id={current_user.id}\n"
        f"name={current_user.full_name}\n"
        f"email={current_user.email}\n"
        f"department={current_user.department}\n"
        f"is_admin={current_user.is_admin}\n\n"
        "User Question:\n"
        f"{question}"
    )

    return ai_service.handle_chat(
        db=db,
        user_message=enriched_message,
        requesting_user_id=current_user.id,
        language=body.language,
        display_question=question,
    )
