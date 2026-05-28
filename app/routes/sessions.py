from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import DeleteChatsResponse, StoredChatSession
from app.services.auth_service import require_admin
from app.services.session_service import delete_all_chat_sessions, list_chat_sessions

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/", response_model=list[StoredChatSession])
def get_chat_sessions(
    session_id: Annotated[str | None, Query(alias="sessionId")] = None,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    return list_chat_sessions(db, session_id=session_id)


@router.delete("/", response_model=DeleteChatsResponse)
def delete_chat_sessions(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    deleted_sessions, deleted_messages = delete_all_chat_sessions(db)
    return DeleteChatsResponse(
        deleted_sessions=deleted_sessions,
        deleted_messages=deleted_messages,
    )
