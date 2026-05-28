from typing import Optional
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ConversationMessage, ConversationSession
from app.models import ChatMessage, MessageRole, StoredChatMessage, StoredChatSession


def get_or_create_session(
    db: Session,
    session_id: Optional[str] = None,
) -> ConversationSession:
    if session_id:
        existing_session = db.get(ConversationSession, session_id)
        if existing_session:
            return existing_session

    new_session = ConversationSession(id=session_id or str(uuid4()))
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


def get_recent_messages(
    db: Session,
    session_id: str,
    limit: int = 8,
) -> list[ChatMessage]:
    statement = (
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(limit)
    )
    rows = list(db.scalars(statement))
    rows.reverse()

    return [
        ChatMessage(role=MessageRole(row.role), content=row.content)
        for row in rows
        if row.role in {role.value for role in MessageRole}
    ]


def append_message(
    db: Session,
    session_id: str,
    role: MessageRole,
    content: str,
) -> ConversationMessage:
    message = ConversationMessage(
        session_id=session_id,
        role=role.value,
        content=content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def list_chat_sessions(
    db: Session,
    limit: int = 100,
    session_id: Optional[str] = None,
) -> list[StoredChatSession]:
    statement = (
        select(ConversationSession)
        .options(selectinload(ConversationSession.messages))
        .order_by(ConversationSession.updated_at.desc())
    )
    if session_id:
        statement = statement.where(ConversationSession.id == session_id)

    statement = statement.limit(limit)
    sessions = list(db.scalars(statement))

    return [
        StoredChatSession(
            id=session.id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=[
                StoredChatMessage(
                    id=message.id,
                    role=MessageRole(message.role),
                    content=message.content,
                    created_at=message.created_at,
                )
                for message in sorted(session.messages, key=lambda item: item.created_at)
                if message.role in {role.value for role in MessageRole}
            ],
        )
        for session in sessions
    ]


def delete_all_chat_sessions(db: Session) -> tuple[int, int]:
    session_count = db.scalar(select(func.count()).select_from(ConversationSession)) or 0
    message_count = db.scalar(select(func.count()).select_from(ConversationMessage)) or 0

    db.execute(delete(ConversationMessage))
    db.execute(delete(ConversationSession))
    db.commit()

    return int(session_count), int(message_count)
