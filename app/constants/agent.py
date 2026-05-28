import re

from app.models import NavigationTarget, RouteIntent


ROUTER_NAVIGATION_TARGETS = ", ".join(
    ["null", *(target.value for target in NavigationTarget)]
)
CONTACT_DETAILS_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
CONTACT_PROMPT = (
    "Sure. I can help you contact Mohamad. Could you please provide your name "
    "and a valid email address?"
)
CONTACT_MESSAGE_PROMPT = (
    "Thanks. Do you want me to add a message, or should I send the contact "
    "request as is?"
)
CONTACT_FULL_DETAILS_PROMPT = (
    "Please send your name, a valid email address, and a short message for Mohamad."
)
CONTACT_NAME_EMAIL_PROMPT = (
    "Please provide your name and a valid email address so I can prepare the contact request."
)
CONTACT_EMAIL_PROMPT = (
    "Please provide a valid email address so I can prepare the contact request."
)
CONTACT_NAME_PROMPT = (
    "Please provide your name so I can prepare the contact request."
)
CONTACT_SEND_FAILURE_MESSAGE = (
    "I could not send the contact request right now. Please try again later."
)
CONTACT_OFFER_PROMPT = (
    "Would you like me to connect you to Mohamad so he can answer you?"
)
EMPTY_CHAT_MESSAGE_REPLY = "Please send a message so I can help."
NAVIGATION_REPLY = "Sure. I can take you there."
MODEL_NOT_READY_MESSAGE = "The assistant model is not ready yet. Please try again later."
MODEL_GENERATION_FAILURE_MESSAGE = (
    "I could not generate a response right now. Please try again later."
)
RAG_NOT_READY_MESSAGE = "The knowledge base is not ready yet. Please try again later."
RAG_RETRIEVAL_FAILURE_MESSAGE = (
    "I could not retrieve portfolio context right now. Please try again later."
)
EMPTY_CONTACT_CONTENT = "No additional message provided."
CONTACT_EXTRACTION_SYSTEM_MESSAGE = (
    "You extract structured contact request details for Mohamad's portfolio assistant. "
    "Return only valid JSON with these fields: name, email, content, send_without_message. "
    "Use null for unknown name, email, or content. "
    "Only return an email when it is a valid email address in the format local@domain.tld. "
    "The domain must include a dot and a final alphabetic part of at least two letters. "
    "If the email is malformed, incomplete, misspelled, or uncertain, return null for email. "
    "Do not correct, complete, or invent email addresses. "
    "Set send_without_message to true only when the user clearly says to send without "
    "a message, just send a contact request, no message, or equivalent. "
    "Do not invent missing details."
)
CONTACT_ASSISTANT_PROMPTS = {
    CONTACT_PROMPT,
    CONTACT_MESSAGE_PROMPT,
    CONTACT_FULL_DETAILS_PROMPT,
    CONTACT_NAME_EMAIL_PROMPT,
    CONTACT_EMAIL_PROMPT,
    CONTACT_NAME_PROMPT,
}
CONTACT_BUTTON_MESSAGE = "get in touch"
CONTACT_CONFIRMATION_PATTERN = re.compile(
    r'A contact request with name: (?P<name>.+?), email: (?P<email>.+?) was sent\.',
    flags=re.DOTALL,
)
CONTACT_OFFER_PATTERN = re.compile(
    r"\bconnect you (?:to|with) mohamad\b",
    flags=re.IGNORECASE,
)
CONTACT_OFFER_ACCEPTANCE_PATTERN = re.compile(
    r"^\s*(?:yes|yes[,\s]+please|yeah|yep|sure|ok(?:ay)?|please(?: do)?|"
    r"do it|go ahead|sounds good|that would be (?:good|great)|"
    r"connect me(?: to mohamad)?)"
    r"(?:[.! ]*)$",
    flags=re.IGNORECASE,
)
CONTACT_REQUEST_ONLY_PATTERNS = [
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in [
        r"\bcan i get in touch\b",
        r"\bget in touch\b",
        r"\bcontact mohamad\b",
        r"\breach out to mohamad\b",
        r"\btalk to mohamad\b",
    ]
]
SEND_WITHOUT_MESSAGE_PHRASES = [
    "as is",
    "just a contact",
    "no message",
    "send it",
    "without message",
]

ROUTER_SYSTEM_MESSAGE = (
    "You route user messages for Mohamad's portfolio assistant. "
    "User messages may end with an attached section titled 'Page content'. "
    "Treat that section as page context, not as the user's actual request, and "
    "only consider it when the user asks about that page content. "
    "Return only valid JSON with these fields: "
    "intent, needs_rag, navigation_target. "
    f"intent must be one of: {', '.join(intent.value for intent in RouteIntent)}. "
    f"navigation_target must be one of {ROUTER_NAVIGATION_TARGETS}. "
    "Infer intent from meaning and conversation context, not just exact words. "
    "Use contact_request when the user wants a channel, introduction, message, "
    "or way to communicate with or contact Mohamad. "
    "Use contact_request when the assistant just offered to connect the user "
    "to Mohamad and the user agrees. "
    "Use contact_request when the conversation already contains a sent contact "
    "request and the user asks to also send, add, include, tell, forward, or "
    "update another message using the same contact details. "
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

CONTEXTUAL_USER_PROMPT_TEMPLATE = (
    "Answer the specific user question using only the context below. "
    "The user's message may end with an attached section titled 'Page content'. "
    "That section is page context the user is providing, not the user's actual "
    "request. Use it only when the user asks a question about that page content; "
    "otherwise ignore it. "
    "If the context contains the answer, answer directly. "
    "If the context partially answers the question, state exactly what the "
    "context says and avoid overstating it. "
    "If the context does not contain the answer, say you could not find "
    "that detail in the available context. In that same reply, you must offer "
    "to start a contact request by asking exactly: "
    f'"{CONTACT_OFFER_PROMPT}" '
    "Do not stop after saying the detail is not in the available context. "
    "Do not answer with a generic list of things you can discuss. "
    "Do not list topics unless the user asks for a list. "
    "Avoid repeating the same word or phrase.\n\n"
    "Context:\n{context}\n\n"
    "Question: {message}"
)
