import time

import requests

from core.clients.base import BaseClient


class JenkinsClient(BaseClient):
    """All Jenkins REST API interaction for one base_url/username/token trio.

    Holds all three as instance state since every method needs them - crumb
    issuing, build triggering, queue/status polling, and promotion all hit
    the same authenticated base_url.
    """

    _CACHE_KEY = "jenkins"

    def __init__(self, base_url: str, username: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.token = token
        # Set by _test_connection() on every check_connection() call that
        # actually hits the network (i.e. whenever the cache doesn't already
        # hold a fresh "ok") - lets callers log *why* a failed check failed,
        # not just that it failed.
        self.last_check_detail: str = ""

    def _auth(self) -> tuple[str, str]:
        # Jenkins Basic Auth always requires the real username paired with
        # the API token as the password - confirmed against jenkins.io's own
        # "Authenticating scripted clients" docs after a live instance 401'd
        # on token-only auth (empty username). There is no token-only mode.
        return self.username, self.token

    def _crumb_headers(self) -> dict[str, str]:
        """CSRF crumb header to attach to a POST, or {} if this instance
        doesn't have crumb issuing enabled."""
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
        """base_url, username, and token joined - any one changing means a fresh check is needed."""
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
        """POST buildWithParameters with only the given params. Returns the
        queue item URL (from the Location header) - not a build number yet."""
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
        """Poll a queue item until it leaves the queue and gets a real build
        number. This is a separate, short-interval poll from the long
        build/promotion status wait - queue items normally resolve in
        seconds, not minutes."""
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
        """{'building': bool, 'result': 'SUCCESS' | 'FAILURE' | None} for one build."""
        response = requests.get(
            f"{self.base_url}/job/{job_name}/{build_number}/api/json",
            auth=self._auth(),
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()

        return {"building": data.get("building", False), "result": data.get("result")}

    def trigger_promotion(self, job_name: str, build_number: int, promotion_name: str) -> None:
        """Trigger the named promotion process for one build via
        PromotedBuildAction.doForcePromotion - NOT PromotionProcess.doBuild,
        which unconditionally 404s ("Promotion processes may not be built
        directly", true since the plugin's 2015-era phantom-build fix).
        Requires that promotion process to have a Manual Promotion condition
        configured in Jenkins; doForcePromotion looks one up and errors if
        none exists."""
        response = requests.post(
            f"{self.base_url}/job/{job_name}/{build_number}/promotion/forcePromotion",
            params={"name": promotion_name},
            auth=self._auth(),
            headers=self._crumb_headers(),
            timeout=15,
        )

        response.raise_for_status()

    def promotion_exists(self, job_name: str, build_number: int, promotion_name: str) -> bool:
        """True if a promotion for this exact build_number is already recorded."""
        data = self._get_promotion_process(job_name, promotion_name)

        return any(b.get("target", {}).get("number") == build_number for b in data.get("builds", []))

    def get_promotion_status(self, job_name: str, build_number: int, promotion_name: str) -> dict:
        """{'building': bool, 'result': 'SUCCESS' | 'FAILURE' | None} for the
        promotion entry matching build_number. Assumes Jenkins lists newest
        promotion attempts first (unverified against a real instance) - this
        matters after a "redo" leaves more than one entry for the same build."""
        data = self._get_promotion_process(job_name, promotion_name)

        for b in data.get("builds", []):
            if b.get("target", {}).get("number") == build_number:
                return {"building": b.get("building", False), "result": b.get("result")}

        return {"building": False, "result": None}

    def _get_promotion_process(self, job_name: str, promotion_name: str) -> dict:
        response = requests.get(
            f"{self.base_url}/job/{job_name}/promotion/process/{promotion_name}/api/json",
            auth=self._auth(),
            timeout=15,
        )

        response.raise_for_status()

        return response.json()
