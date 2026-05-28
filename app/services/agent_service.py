import json
import logging
import re

from pydantic import ValidationError

from app.constants.agent import (
    CONTACT_ASSISTANT_PROMPTS,
    CONTACT_BUTTON_MESSAGE,
    CONTACT_CONFIRMATION_PATTERN,
    CONTACT_DETAILS_PATTERN,
    CONTACT_EXTRACTION_SYSTEM_MESSAGE,
    CONTACT_EMAIL_PROMPT,
    CONTACT_FULL_DETAILS_PROMPT,
    CONTACT_MESSAGE_PROMPT,
    CONTACT_NAME_EMAIL_PROMPT,
    CONTACT_NAME_PROMPT,
    CONTACT_OFFER_ACCEPTANCE_PATTERN,
    CONTACT_OFFER_PATTERN,
    CONTACT_PROMPT,
    CONTACT_REQUEST_ONLY_PATTERNS,
    CONTACT_SEND_FAILURE_MESSAGE,
    CONTEXTUAL_USER_PROMPT_TEMPLATE,
    EMPTY_CONTACT_CONTENT,
    EMPTY_CHAT_MESSAGE_REPLY,
    MODEL_GENERATION_FAILURE_MESSAGE,
    MODEL_NOT_READY_MESSAGE,
    NAVIGATION_REPLY,
    RAG_NOT_READY_MESSAGE,
    RAG_RETRIEVAL_FAILURE_MESSAGE,
    ROUTER_SYSTEM_MESSAGE,
    SEND_WITHOUT_MESSAGE_PHRASES,
)
from app.constants.llm import SYSTEM_MESSAGE
from app.models import (
    AgentRequest,
    ChatMode,
    ChatResponse,
    ContactRequestDetails,
    MessageRole,
    NavigationTarget,
    RouteDecision,
    RouteIntent,
)
from app.services.email_service import ContactEmail, EmailServiceError, send_contact_email
from app.services.llm_service import (
    generate_chat_response,
    generate_router_response,
)
from app.services.tool_registry import (
    complete_contact_flow_action,
    navigation_action,
    start_contact_flow_action,
)


logger = logging.getLogger(__name__)


class ChatServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


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
            decision = RouteDecision(
                intent=RouteIntent.PORTFOLIO_QUESTION,
                needs_rag=True,
                navigation_target=None,
            )
            return decision

    return decision


def _history_to_messages(request: AgentRequest) -> list[dict[str, str]]:
    return [
        {"role": message.role.value, "content": message.content}
        for message in request.history
    ]


def _has_contact_details(message: str) -> bool:
    return CONTACT_DETAILS_PATTERN.search(message) is not None


def _is_contact_button_message(message: str) -> bool:
    return message.strip().casefold() == CONTACT_BUTTON_MESSAGE


def _is_contact_request_only_text(message: str) -> bool:
    return any(pattern.search(message) for pattern in CONTACT_REQUEST_ONLY_PATTERNS)


def _is_contact_offer_acceptance(request: AgentRequest) -> bool:
    last_message = _last_assistant_message(request)
    if not last_message or not CONTACT_OFFER_PATTERN.search(last_message):
        return False

    return CONTACT_OFFER_ACCEPTANCE_PATTERN.fullmatch(request.message) is not None


def _last_assistant_message(request: AgentRequest) -> str | None:
    for message in reversed(request.history):
        if message.role == MessageRole.ASSISTANT:
            return message.content
    return None


def _is_contact_flow_active(request: AgentRequest) -> bool:
    if request.mode == ChatMode.CONTACT:
        return True

    if not request.history:
        return False

    last_message = request.history[-1]
    return (
        last_message.role == MessageRole.ASSISTANT
        and last_message.content in CONTACT_ASSISTANT_PROMPTS
    )


def _contact_conversation(request: AgentRequest) -> list[dict[str, str]]:
    messages = _history_to_messages(request)
    messages.append({"role": MessageRole.USER.value, "content": request.message})

    last_confirmation_index = -1
    for index, message in enumerate(messages):
        if (
            message["role"] == MessageRole.ASSISTANT.value
            and CONTACT_CONFIRMATION_PATTERN.search(message["content"])
        ):
            last_confirmation_index = index

    for index in range(last_confirmation_index + 1, len(messages)):
        if (
            messages[index]["role"] == MessageRole.ASSISTANT.value
            and messages[index]["content"] == CONTACT_PROMPT
        ):
            return messages[index + 1 :]

    return messages[last_confirmation_index + 1 :]


def _email_from_text(text: str) -> str | None:
    match = CONTACT_DETAILS_PATTERN.search(text)
    return match.group(0) if match else None


def _is_valid_email(email: str | None) -> bool:
    return bool(email and CONTACT_DETAILS_PATTERN.fullmatch(email.strip()))


def _looks_like_name(text: str) -> bool:
    if _email_from_text(text):
        return False

    words = text.strip().split()
    if not 1 <= len(words) <= 4:
        return False

    return all(re.fullmatch(r"[A-Za-z][A-Za-z' -]*", word) for word in words)


def _previous_sent_contact_details(request: AgentRequest) -> ContactRequestDetails:
    for message in reversed(request.history):
        if message.role != MessageRole.ASSISTANT:
            continue

        match = CONTACT_CONFIRMATION_PATTERN.search(message.content)
        if not match:
            continue

        return ContactRequestDetails(
            name=match.group("name"),
            email=match.group("email"),
        )

    return ContactRequestDetails()


def _fallback_contact_details(request: AgentRequest) -> ContactRequestDetails:
    user_messages = [
        message["content"].strip()
        for message in _contact_conversation(request)
        if message["role"] == MessageRole.USER.value and message["content"].strip()
    ]
    details = _previous_sent_contact_details(request)
    details.content = None
    details.send_without_message = False

    for content in user_messages:
        if _is_contact_request_only_text(content):
            continue

        email = _email_from_text(content)
        if email:
            details.email = details.email or email
            possible_name = content.replace(email, "").strip(" ,.;:-")
            if possible_name and not details.name and _looks_like_name(possible_name):
                details.name = possible_name
            continue

        lowered = content.lower()
        if any(phrase in lowered for phrase in SEND_WITHOUT_MESSAGE_PHRASES):
            details.send_without_message = True
            continue

        if not details.name and _looks_like_name(content):
            details.name = content
            continue

        if not details.content:
            details.content = content

    return details


def _merge_contact_details(
    primary: ContactRequestDetails,
    fallback: ContactRequestDetails,
) -> ContactRequestDetails:
    name = primary.name or fallback.name
    primary_email = primary.email.strip() if primary.email else None
    fallback_email = fallback.email.strip() if fallback.email else None
    email = None
    if _is_valid_email(primary_email):
        email = primary_email
    elif _is_valid_email(fallback_email):
        email = fallback_email
    content = primary.content or fallback.content

    if content and content.strip().lower() in {
        value.strip().lower()
        for value in [name, email]
        if value
    }:
        content = None

    return ContactRequestDetails(
        name=name,
        email=email,
        content=content,
        send_without_message=primary.send_without_message or fallback.send_without_message,
    )


def _extract_contact_details(request: AgentRequest) -> ContactRequestDetails:
    extraction_messages = [
        {"role": MessageRole.SYSTEM.value, "content": CONTACT_EXTRACTION_SYSTEM_MESSAGE},
        {
            "role": MessageRole.USER.value,
            "content": (
                "Conversation:\n"
                f"{json.dumps(_contact_conversation(request), ensure_ascii=False)}\n\n"
                "Return only JSON."
            ),
        },
    ]

    try:
        raw_details = generate_router_response(extraction_messages)
    except Exception:
        logger.exception("Contact detail extraction failed")
        return _fallback_contact_details(request)

    parsed = _extract_json_object(raw_details)
    if parsed is None:
        return _fallback_contact_details(request)

    try:
        llm_details = ContactRequestDetails.model_validate(parsed)
    except ValidationError:
        llm_details = ContactRequestDetails()

    return _merge_contact_details(llm_details, _fallback_contact_details(request))


def _send_contact_request(details: ContactRequestDetails, session_id: str) -> None:
    if not details.name or not details.email:
        raise ValueError("name and email are required before sending")

    content = details.content or EMPTY_CONTACT_CONTENT
    send_contact_email(
        ContactEmail(
            name=details.name,
            email=details.email,
            content=content,
            session_id=session_id,
        )
    )


def _contact_confirmation(details: ContactRequestDetails) -> str:
    return (
        f"A contact request with name: {details.name}, email: {details.email} was sent. "
        "Mohamad will contact you as soon as possible."
    )


def _handle_contact_flow(request: AgentRequest) -> ChatResponse:
    message = request.message.strip()

    if not message:
        return ChatResponse(
            reply=CONTACT_FULL_DETAILS_PROMPT,
            mode=ChatMode.CONTACT,
        )

    details = _extract_contact_details(request)
    last_assistant_message = _last_assistant_message(request)

    if not details.name or not details.email:
        if details.name:
            return ChatResponse(
                reply=CONTACT_EMAIL_PROMPT,
                mode=ChatMode.CONTACT,
            )
        if details.email:
            return ChatResponse(
                reply=CONTACT_NAME_PROMPT,
                mode=ChatMode.CONTACT,
            )
        return ChatResponse(
            reply=CONTACT_NAME_EMAIL_PROMPT,
            mode=ChatMode.CONTACT,
        )

    if last_assistant_message != CONTACT_MESSAGE_PROMPT:
        return ChatResponse(reply=CONTACT_MESSAGE_PROMPT, mode=ChatMode.CONTACT)

    try:
        _send_contact_request(details, request.session_id)
    except EmailServiceError as exc:
        logger.exception("Contact email delivery is not configured or failed")
        raise ChatServiceError(
            CONTACT_SEND_FAILURE_MESSAGE,
            status_code=503,
        ) from exc

    content = details.content or EMPTY_CONTACT_CONTENT
    return ChatResponse(
        reply=_contact_confirmation(details),
        action=complete_contact_flow_action(details.name, details.email, content),
        mode=ChatMode.CHAT,
    )


def handle_chat(request: AgentRequest) -> ChatResponse:
    message = request.message.strip()

    if not message:
        return ChatResponse(reply=EMPTY_CHAT_MESSAGE_REPLY)

    if _is_contact_flow_active(request):
        return _handle_contact_flow(request)

    if _is_contact_button_message(message):
        return ChatResponse(
            reply=CONTACT_PROMPT,
            action=start_contact_flow_action(),
            mode=ChatMode.CONTACT,
        )

    if _is_contact_offer_acceptance(request):
        return ChatResponse(
            reply=CONTACT_PROMPT,
            action=start_contact_flow_action(),
            mode=ChatMode.CONTACT,
        )

    route = route_message(request)

    if route.intent == RouteIntent.CONTACT_REQUEST:
        existing_details = _fallback_contact_details(request)
        if _has_contact_details(message) or (
            existing_details.name and existing_details.email
        ):
            return _handle_contact_flow(request)

        return ChatResponse(
            reply=CONTACT_PROMPT,
            action=start_contact_flow_action(),
            mode=ChatMode.CONTACT,
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
            reply=NAVIGATION_REPLY,
            action=navigation_action(navigation_target),
        )

    sources = []
    context = ""

    if route.needs_rag:
        try:
            from app.services.rag_service import (
                document_sources,
                format_documents_for_prompt,
                retrieve_context,
            )

            documents = retrieve_context(message)
            sources = document_sources(documents)
            context = format_documents_for_prompt(documents)
        except (FileNotFoundError, ImportError, ModuleNotFoundError) as exc:
            logger.exception("RAG dependencies or vector database are missing")
            raise ChatServiceError(
                RAG_NOT_READY_MESSAGE,
                status_code=503,
            ) from exc
        except Exception as exc:
            logger.exception("RAG retrieval failed")
            raise ChatServiceError(
                RAG_RETRIEVAL_FAILURE_MESSAGE,
                status_code=503,
            ) from exc

    user_content = message
    if context:
        user_content = CONTEXTUAL_USER_PROMPT_TEMPLATE.format(
            context=context,
            message=message,
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
            MODEL_NOT_READY_MESSAGE,
            status_code=503,
        ) from exc
    except Exception as exc:
        logger.exception("LLM generation failed")
        raise ChatServiceError(
            MODEL_GENERATION_FAILURE_MESSAGE,
            status_code=503,
        ) from exc

    return ChatResponse(reply=reply, sources=sources)
