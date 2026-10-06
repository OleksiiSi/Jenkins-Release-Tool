import time

import requests

from core.clients.base import BaseClient


class JenkinsClient(BaseClient):
    _CACHE_KEY = "jenkins"

    def __init__(self, base_url: str, username: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.token = token
        self.last_check_detail: str = ""

    def _auth(self) -> tuple[str, str]:
        return self.username, self.token

    def _crumb_headers(self) -> dict[str, str]:
        try:
            response = requests.get(
                f"{self.base_url}/crumbIssuer/api/json", auth=self._auth(), timeout=10
            )

            if response.status_code != 200:
                return {}

            data = response.json()
            return {data["crumbRequestField"]: data["crumb"]}

        except requests.RequestException:
            return {}

    @property
    def _current_value(self) -> str:
        return f"{self.base_url}:{self.username}:{self.token}"

    def _test_connection(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/json", auth=self._auth(), timeout=10)
            self.last_check_detail = f"HTTP {response.status_code} {response.reason}".rstrip()
            return response.status_code == 200

        except requests.RequestException as exc:
            self.last_check_detail = str(exc)
            return False

    def trigger_build(self, job_name: str, params: dict[str, str]) -> str:
        response = requests.post(
            f"{self.base_url}/job/{job_name}/buildWithParameters",
            params=params,
            auth=self._auth(),
            headers=self._crumb_headers(),
            timeout=15,
        )

        response.raise_for_status()

        return response.headers["Location"]

    def resolve_build_number(
        self, queue_item_url: str, poll_seconds: float = 2.0, timeout_seconds: float = 300.0
    ) -> int:
        deadline = time.monotonic() + timeout_seconds
        queue_api_url = queue_item_url.rstrip("/") + "/api/json"

        while True:
            response = requests.get(queue_api_url, auth=self._auth(), timeout=15)
            response.raise_for_status()
            executable = response.json().get("executable")

            if executable and "number" in executable:
                return executable["number"]

            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Queue item did not resolve to a build number within "
                    f"{timeout_seconds}s: {queue_item_url}"
                )
            time.sleep(poll_seconds)

    def get_build_status(self, job_name: str, build_number: int) -> dict:
        response = requests.get(
            f"{self.base_url}/job/{job_name}/{build_number}/api/json",
            auth=self._auth(),
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()

        return {"building": data.get("building", False), "result": data.get("result")}

    def trigger_promotion(self, job_name: str, build_number: int, promotion_name: str) -> None:
        response = requests.post(
            f"{self.base_url}/job/{job_name}/{build_number}/promotion/forcePromotion",
            params={"name": promotion_name},
            auth=self._auth(),
            headers=self._crumb_headers(),
            timeout=15,
        )

        response.raise_for_status()

    def promotion_exists(self, job_name: str, build_number: int, promotion_name: str) -> bool:
        return self._get_latest_promotion(job_name, build_number, promotion_name) is not None

    def get_promotion_status(self, job_name: str, build_number: int, promotion_name: str) -> dict:
        latest = self._get_latest_promotion(job_name, build_number, promotion_name)

        if latest is not None:
            return {"building": latest.get("building"), "result": latest.get("result")}

        return {"building": False, "result": None}

    def _get_latest_promotion(self, job_name: str, build_number: int, promotion_name: str) -> dict | None:
        response = requests.get(
            f"{self.base_url}/job/{job_name}/{build_number}/api/json",
            params={"tree": "actions[promotions[name,promotionBuilds[result,building]]]"},
            auth=self._auth(),
            timeout=15,
        )

        response.raise_for_status()

        for action in response.json().get("actions", []):
            for promotion in action.get("promotions", []):
                if promotion.get("name") == promotion_name and promotion.get("promotionBuilds"):
                    return promotion["promotionBuilds"][0]

        return None
