import json
import logging
import re

from pydantic import ValidationError

from app.models import AgentRequest, ChatResponse, MessageRole, RouteDecision, RouteIntent
from app.services.llm_service import (
    SYSTEM_MESSAGE,
    generate_chat_response,
    generate_router_response,
)
from app.services.rag_service import (
    document_sources,
    format_documents_for_prompt,
    retrieve_context,
)
from app.services.tool_registry import (
    detect_navigation_target,
    navigation_action,
    start_contact_flow_action,
)


logger = logging.getLogger(__name__)


class ChatServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


ROUTER_SYSTEM_MESSAGE = (
    "You route user messages for Mohamad's portfolio assistant. "
    "Return only valid JSON with these fields: "
    "intent, needs_rag, navigation_target. "
    f"intent must be one of: {', '.join(intent.value for intent in RouteIntent)}. "
    "navigation_target must be one of null, #about, #projects, #services, "
    "#experience, #publications, #contact. "
    "Use contact_request when the user wants to email, contact, reach, or message Mohamad. "
    "Use navigation_request when the user wants to see or go to a portfolio section. "
    "Use portfolio_question and needs_rag true for questions about Mohamad's skills, "
    "experience, projects, publications, patents, CV, services, work, background, "
    "hobbies, interests, personal profile, running, marathons, fitness, training, "
    "sports, or lifestyle."
)


def _needs_rag(message: str) -> bool:
    normalized = message.lower()
    keywords = [
        "skill",
        "experience",
        "project",
        "publication",
        "patent",
        "cv",
        "background",
        "education",
        "service",
        "work",
        "research",
        "hobbies",
        "interest",
    ]
    return any(keyword in normalized for keyword in keywords)


def _is_contact_request(message: str) -> bool:
    normalized = message.lower()
    return any(
        phrase in normalized
        for phrase in ["contact", "email", "get in touch", "reach mohamad"]
    )


def _fallback_route(message: str) -> RouteDecision:
    if _is_contact_request(message):
        return RouteDecision(intent=RouteIntent.CONTACT_REQUEST, needs_rag=False)

    navigation_target = detect_navigation_target(message)
    if navigation_target:
        return RouteDecision(
            intent=RouteIntent.NAVIGATION_REQUEST,
            needs_rag=False,
            navigation_target=navigation_target,
        )

    if _needs_rag(message):
        return RouteDecision(intent=RouteIntent.PORTFOLIO_QUESTION, needs_rag=True)

    return RouteDecision(intent=RouteIntent.GENERAL_CHAT, needs_rag=False)


def _extract_json_object(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def route_message(request: AgentRequest) -> RouteDecision:
    fallback = _fallback_route(request.message)

    history_preview = [
        {"role": message.role.value, "content": message.content}
        for message in request.history[-4:]
    ]

    router_messages = [
        {"role": MessageRole.SYSTEM.value, "content": ROUTER_SYSTEM_MESSAGE},
        {
            "role": MessageRole.USER.value,
            "content": (
                "Conversation history:\n"
                f"{json.dumps(history_preview, ensure_ascii=False)}\n\n"
                f"Current user message: {request.message}\n\n"
                "Return only JSON."
            ),
        },
    ]

    try:
        raw_decision = generate_router_response(router_messages)
    except Exception:
        logger.exception("LLM router failed; using fallback route")
        return fallback

    parsed = _extract_json_object(raw_decision)

    if parsed is None:
        return fallback

    try:
        decision = RouteDecision.model_validate(parsed)
    except ValidationError:
        return fallback

    if decision.intent == RouteIntent.NAVIGATION_REQUEST and not decision.navigation_target:
        decision.navigation_target = fallback.navigation_target

    return decision


def _history_to_messages(request: AgentRequest) -> list[dict[str, str]]:
    return [
        {"role": message.role.value, "content": message.content}
        for message in request.history
    ]


def handle_chat(request: AgentRequest) -> ChatResponse:
    message = request.message.strip()

    if not message:
        return ChatResponse(reply="Please send a message so I can help.")

    route = route_message(request)

    if route.intent == RouteIntent.CONTACT_REQUEST:
        return ChatResponse(
            reply="Sure. I can help you contact Mohamad. What is your name?",
            action=start_contact_flow_action(),
        )

    navigation_target = route.navigation_target or detect_navigation_target(message)
    if navigation_target:
        return ChatResponse(
            reply="Sure. I can take you there.",
            action=navigation_action(navigation_target),
        )

    sources = []
    context = ""

    if route.needs_rag:
        try:
            documents = retrieve_context(message)
            sources = document_sources(documents)
            context = format_documents_for_prompt(documents)
        except FileNotFoundError as exc:
            logger.exception("RAG vector database is missing")
            raise ChatServiceError(
                "The knowledge base is not ready yet. Please try again later.",
                status_code=503,
            ) from exc
        except Exception as exc:
            logger.exception("RAG retrieval failed")
            raise ChatServiceError(
                "I could not retrieve portfolio context right now. Please try again later.",
                status_code=503,
            ) from exc

    user_content = message
    if context:
        user_content = (
            "Answer the specific user question using only the context below. "
            "If the context contains the answer, answer directly. "
            "If the context partially answers the question, state exactly what the "
            "context says and avoid overstating it. "
            "If the context does not contain the answer, say you could not find "
            "that detail in the available context and ask one concise follow-up question. "
            "Do not answer with a generic list of things you can discuss. "
            "Do not list topics unless the user asks for a list. "
            "Avoid repeating the same word or phrase.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {message}"
        )

    messages = [
        {"role": MessageRole.SYSTEM.value, "content": SYSTEM_MESSAGE},
        *_history_to_messages(request),
        {"role": MessageRole.USER.value, "content": user_content},
    ]

    try:
        reply = generate_chat_response(messages)
    except FileNotFoundError as exc:
        logger.exception("Local LLM files are missing")
        raise ChatServiceError(
            "The assistant model is not ready yet. Please try again later.",
            status_code=503,
        ) from exc
    except Exception as exc:
        logger.exception("LLM generation failed")
        raise ChatServiceError(
            "I could not generate a response right now. Please try again later.",
            status_code=503,
        ) from exc

    return ChatResponse(reply=reply, sources=sources)
