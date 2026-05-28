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
    COMPLETE_CONTACT_FLOW = "complete_contact_flow"


class ActionPayloadKey(str, Enum):
    CONTENT = "content"
    EMAIL = "email"
    MESSAGE = "message"
    MODE = "mode"
    NAME = "name"


class NavigationTarget(str, Enum):
    HOME = "#home"
    ABOUT = "#about"
    PROJECTS = "#projects"
    CONTACT = "#contact"


class NavigationKeyword(str, Enum):
    HOME = "home"
    PROJECT = "project"
    PROJECTS = "projects"
    CONTACT = "contact"
    ABOUT = "about"


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
    current_location: Optional[NavigationTarget] = None


class AgentRequest(BaseModel):
    message: str
    session_id: str
    history: list[ChatMessage] = Field(default_factory=list)
    mode: ChatMode = ChatMode.CHAT
    current_location: Optional[NavigationTarget] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: Optional[str] = None
    action: Optional[Action] = None
    mode: Optional[ChatMode] = None
    sources: list[Source] = Field(default_factory=list)


class RouteDecision(BaseModel):
    intent: RouteIntent = RouteIntent.GENERAL_CHAT
    needs_rag: bool = False
    navigation_target: Optional[NavigationTarget] = None


class ContactRequestDetails(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    content: Optional[str] = None
    send_without_message: bool = False


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


class DeleteChatsResponse(BaseModel):
    deleted_sessions: int
    deleted_messages: int


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
