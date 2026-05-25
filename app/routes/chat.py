from pydantic import BaseModel
from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("/", response_model=ChatResponse)
def create_chat_message(request: ChatRequest):
    return ChatResponse(reply=f"Received: {request.message}")
