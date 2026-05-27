import json
import logging
import re

from pydantic import ValidationError

from app.models import (
    AgentRequest,
    ChatResponse,
    MessageRole,
    RouteDecision,
    RouteIntent,
)
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
    "navigation_target must be one of null, #about, #projects, and #contact. "
    "Infer intent from meaning and conversation context, not just exact words. "
    "Use contact_request when the user wants a channel, introduction, message, "
    "or way to communicate with Mohamad. "
    "Use navigation_request only when the user wants the interface to move to a "
    "portfolio section; include the target section. "
    "If the user is already on the requested section, return portfolio_question "
    "with needs_rag true instead of navigation_request. "
    "Use portfolio_question with needs_rag true for questions about Mohamad, his "
    "skills, experience, projects, publications, patents, CV, services, work, "
    "background, hobbies, interests, or lifestyle. "
    "Use general_chat only for conversational messages that do not need portfolio "
    "knowledge or an action."
)

def _default_route() -> RouteDecision:
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
    fallback = _default_route()
    current_location = (
        request.current_location.value if request.current_location else "unknown"
    )

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
                f"Current portfolio section: {current_location}\n\n"
                f"Current user message: {request.message}\n\n"
                "Return only JSON."
            ),
        },
    ]

    try:
        raw_decision = generate_router_response(router_messages)
    except Exception:
        logger.exception("LLM router failed; using default route")
        return fallback

    parsed = _extract_json_object(raw_decision)

    if parsed is None:
        return fallback

    try:
        decision = RouteDecision.model_validate(parsed)
    except ValidationError:
        return fallback

    if decision.intent == RouteIntent.CONTACT_REQUEST:
        decision.needs_rag = False
        decision.navigation_target = None
        return decision

    if decision.intent == RouteIntent.PORTFOLIO_QUESTION:
        decision.needs_rag = True
        decision.navigation_target = None
        return decision

    if decision.intent == RouteIntent.NAVIGATION_REQUEST:
        decision.needs_rag = False
        if not decision.navigation_target:
            return fallback
        if decision.navigation_target == request.current_location:
            return RouteDecision(
                intent=RouteIntent.PORTFOLIO_QUESTION,
                needs_rag=True,
                navigation_target=None,
            )

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
            reply="Sure. I can help you contact Mohamad. Could you please provide your name and email address?",
            action=start_contact_flow_action(),
        )

    navigation_target = route.navigation_target
    if navigation_target == request.current_location:
        navigation_target = None
        route = RouteDecision(
            intent=RouteIntent.PORTFOLIO_QUESTION,
            needs_rag=True,
            navigation_target=None,
        )

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
