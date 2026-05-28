from app.models import (
    Action,
    ActionPayloadKey,
    ActionType,
    ChatMode,
    NavigationKeyword,
    NavigationTarget,
)


def navigation_action(target: NavigationTarget) -> Action:
    return Action(type=ActionType.NAVIGATE, target=target)


def start_contact_flow_action() -> Action:
    return Action(
        type=ActionType.START_CONTACT_FLOW,
        payload={ActionPayloadKey.MODE.value: ChatMode.CONTACT},
    )


def complete_contact_flow_action(name: str, email: str, content: str) -> Action:
    return Action(
        type=ActionType.COMPLETE_CONTACT_FLOW,
        payload={
            ActionPayloadKey.CONTENT.value: content,
            ActionPayloadKey.EMAIL.value: email,
            ActionPayloadKey.MODE.value: ChatMode.CHAT,
            ActionPayloadKey.NAME.value: name,
        },
    )


def detect_navigation_target(message: str) -> NavigationTarget | None:
    normalized = message.lower()

    targets = {
        NavigationKeyword.HOME: NavigationTarget.HOME,
        NavigationKeyword.PROJECT: NavigationTarget.PROJECTS,
        NavigationKeyword.PROJECTS: NavigationTarget.PROJECTS,
        NavigationKeyword.CONTACT: NavigationTarget.CONTACT,
        NavigationKeyword.ABOUT: NavigationTarget.ABOUT,
    }

    for keyword, target in targets.items():
        if keyword.value in normalized:
            return target

    return None
