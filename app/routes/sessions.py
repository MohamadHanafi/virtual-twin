from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import StoredChatSession
from app.services.auth_service import require_admin
from app.services.session_service import list_chat_sessions

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/", response_model=list[StoredChatSession])
def get_chat_sessions(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    return list_chat_sessions(db)
