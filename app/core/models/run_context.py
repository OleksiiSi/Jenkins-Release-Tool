from dataclasses import dataclass

from core.clients.jenkins import JenkinsClient
from core.log_buffer import LogBuffer


@dataclass
class RunContext:
    """Fixed config + dependencies shared by every task a Runner submits.

    Deliberately excludes the ThreadPoolExecutor: nothing outside Runner
    ever submits to it, so it's Runner's own internal implementation detail
    (how it schedules its own work), not something callers should inject.
    Also excludes any settings-derived job/environment config - every
    JobRequest a Runner receives already carries its own resolved
    parameters/environments (see core/models/types.py's JobRequest), so
    there's nothing left for Runner to look up.

    :ivar jenkins_client: Authenticated client for all Jenkins REST calls.
    :ivar poll_interval_seconds: Delay between build/promotion status polls.
    :ivar max_retries: Max retries per build/promotion attempt (0 means no
        retries - 1 attempt total).
    :ivar teams_webhook_url: None disables the Teams notification channel.
    :ivar log_buffer: Every build/promotion log line is appended here.
    """

    jenkins_client: JenkinsClient
    poll_interval_seconds: float
    max_retries: int
    teams_webhook_url: str | None
    log_buffer: LogBuffer
