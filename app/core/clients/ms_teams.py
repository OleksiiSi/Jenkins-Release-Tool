import requests

from core.clients.base import BaseClient


class MSTeamsClient(BaseClient):
    _CACHE_KEY = "teams"

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.last_check_detail: str = ""

    def notify(self, title: str, message: str) -> None:
        requests.post(self.webhook_url, json={"text": f"**{title}**\n{message}"}, timeout=10)

    @property
    def _current_value(self) -> str:
        return self.webhook_url

    def _test_connection(self) -> bool:
        try:
            response = requests.post(
                self.webhook_url, json={"text": "\U0001f527 Connectivity check"}, timeout=10
            )
            detail = f"HTTP {response.status_code} {response.reason}".rstrip()
            is_valid = response.status_code == 202
            self.last_check_detail = detail if is_valid else f"{detail} (expected HTTP 202 Accepted - webhook did not reach a flow)"
            return is_valid

        except requests.RequestException as exc:
            self.last_check_detail = str(exc)
            return False
