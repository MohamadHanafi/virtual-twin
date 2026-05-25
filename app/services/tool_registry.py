from app.models import Action, ActionType, NavigationTarget


def navigation_action(target: NavigationTarget) -> Action:
    return Action(type=ActionType.NAVIGATE, target=target)


def start_contact_flow_action() -> Action:
    return Action(type=ActionType.START_CONTACT_FLOW)


def detect_navigation_target(message: str) -> NavigationTarget | None:
    normalized = message.lower()

    targets = {
        "project": NavigationTarget.PROJECTS,
        "service": NavigationTarget.SERVICES,
        "experience": NavigationTarget.EXPERIENCE,
        "publication": NavigationTarget.PUBLICATIONS,
        "contact": NavigationTarget.CONTACT,
        "about": NavigationTarget.ABOUT,
    }

    for keyword, target in targets.items():
        if keyword in normalized:
            return target

    return None
