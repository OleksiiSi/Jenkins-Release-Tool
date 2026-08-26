import logging

from win11toast import notify as _win11_notify

from core.clients.ms_teams import MSTeamsClient

logger = logging.getLogger(__name__)


def notify(title: str, message: str, teams_webhook_url: str | None = None) -> str | None:
    """Fire both notification channels, unconditionally and independently.

    A failure in one channel must never prevent the other from firing or
    crash the calling worker thread - each channel is isolated in its own
    try/except.

    :return: The Teams failure detail if the Teams send failed, else None -
        covers both "it succeeded" and "Teams wasn't configured for this
        call". Toast failures stay silent (logged, not returned) per this
        function's existing best-effort design; callers that want a Teams
        failure surfaced in the UI log panel act on this return value
        themselves, keeping this module free of any LogBuffer/UI dependency.
    """
    notify_toast(title, message)
    if teams_webhook_url:
        return notify_teams(title, message, teams_webhook_url)
    return None


def notify_toast(title: str, message: str) -> None:
    try:
        _win11_notify(title, message)
    except Exception:
        logger.exception("Failed to show Windows toast notification")


def notify_teams(title: str, message: str, webhook_url: str) -> str | None:
    try:
        MSTeamsClient(webhook_url).notify(title, message)
        return None
    except Exception as exc:
        logger.exception("Failed to send Teams notification")
        return str(exc)
