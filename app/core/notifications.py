import logging

from win11toast import notify as _win11_notify

from core.clients.ms_teams import MSTeamsClient

logger = logging.getLogger(__name__)


def notify(title: str, message: str, teams_webhook_url: str | None = None) -> str | None:
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
