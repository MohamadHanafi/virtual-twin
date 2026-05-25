from enum import Enum
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class RouteIntent(str, Enum):
    PORTFOLIO_QUESTION = "portfolio_question"
    NAVIGATION_REQUEST = "navigation_request"
    CONTACT_REQUEST = "contact_request"
    MEETING_REQUEST = "meeting_request"
    GENERAL_CHAT = "general_chat"
    OFF_TOPIC = "off_topic"


class ActionType(str, Enum):
    NAVIGATE = "navigate"
    START_CONTACT_FLOW = "start_contact_flow"


class NavigationTarget(str, Enum):
    ABOUT = "#about"
    PROJECTS = "#projects"
    SERVICES = "#services"
    EXPERIENCE = "#experience"
    PUBLICATIONS = "#publications"
    CONTACT = "#contact"


class ChatMode(str, Enum):
    CHAT = "chat"
    CONTACT = "contact"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str


class Action(BaseModel):
    type: ActionType
    target: Optional[NavigationTarget] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class Source(BaseModel):
    source_file: Optional[str] = None
    page: Optional[int] = None
    chunk_index: Optional[int] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    mode: Optional[ChatMode] = None


class AgentRequest(BaseModel):
    message: str
    session_id: str
    history: list[ChatMessage] = Field(default_factory=list)
    mode: ChatMode = ChatMode.CHAT


class ChatResponse(BaseModel):
    reply: str
    session_id: Optional[str] = None
    action: Optional[Action] = None
    sources: list[Source] = Field(default_factory=list)


class RouteDecision(BaseModel):
    intent: RouteIntent = RouteIntent.GENERAL_CHAT
    needs_rag: bool = False
    navigation_target: Optional[NavigationTarget] = None


class StoredChatMessage(BaseModel):
    id: int
    role: MessageRole
    content: str
    created_at: datetime


class StoredChatSession(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    messages: list[StoredChatMessage] = Field(default_factory=list)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
