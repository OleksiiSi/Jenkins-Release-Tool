import requests

from core.clients.base import BaseClient


class MSTeamsClient(BaseClient):
    """Sends messages to one MS Teams Workflows webhook URL."""

    _CACHE_KEY = "teams"

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        # Set by _test_connection() on every check_connection() call that
        # actually hits the network (i.e. whenever the cache doesn't already
        # hold a fresh "ok") - lets callers log *why* a failed check failed,
        # not just that it failed.
        self.last_check_detail: str = ""

    def notify(self, title: str, message: str) -> None:
        """Post `title`/`message` to the webhook as a Teams message card."""
        requests.post(self.webhook_url, json={"text": f"**{title}**\n{message}"}, timeout=10)

    @property
    def _current_value(self) -> str:
        """The webhook URL - the only config this connection depends on."""
        return self.webhook_url

    def _test_connection(self) -> bool:
        try:
            response = requests.post(
                self.webhook_url, json={"text": "\U0001f527 Connectivity check"}, timeout=10
            )
            detail = f"HTTP {response.status_code} {response.reason}".rstrip()
            # A real Teams Workflows HTTP trigger replies 202 Accepted once the
            # request reaches an actual flow - even if the flow's own condition
            # logic then declines to act on it. A non-existent webhook path
            # (wrong org, deleted flow, placeholder URL) never reaches a flow at
            # all; Microsoft's edge proxy for *.webhook.office.com answers those
            # with a generic 200 (carrying an internal X-ProxyErrorMessage
            # header) regardless of the path, so 200 must NOT count as success.
            # 200 reads as "it worked" to anyone glancing at the log, so spell
            # out why it isn't whenever the response wasn't the expected 202.
            is_valid = response.status_code == 202
            self.last_check_detail = detail if is_valid else f"{detail} (expected HTTP 202 Accepted - webhook did not reach a flow)"
            return is_valid

        except requests.RequestException as exc:
            self.last_check_detail = str(exc)
            return False
