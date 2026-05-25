import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AgentRequest, ChatMode, ChatRequest, ChatResponse
from app.models import MessageRole
from app.services.agent_service import ChatServiceError, handle_chat
from app.services.session_service import (
    append_message,
    get_or_create_session,
    get_recent_messages,
)

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=ChatResponse)
def create_chat_message(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        conversation_session = get_or_create_session(db, request.session_id)
        stored_history = get_recent_messages(db, conversation_session.id)

        agent_request = AgentRequest(
            message=request.message,
            session_id=conversation_session.id,
            history=stored_history,
            mode=request.mode or ChatMode.CHAT,
        )

        response = handle_chat(agent_request)
        response.session_id = conversation_session.id

        append_message(db, conversation_session.id, MessageRole.USER, request.message)
        append_message(db, conversation_session.id, MessageRole.ASSISTANT, response.reply)

        return response
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        logger.exception("Unexpected chat endpoint failure")
        raise HTTPException(
            status_code=500,
            detail="Unexpected chat service error.",
        ) from exc
