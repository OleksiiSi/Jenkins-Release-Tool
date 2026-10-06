import os
import sys

import webview

from core import secrets, settings_manager
from core.validation import validate
from core.clients.jenkins import JenkinsClient
from core.clients.ms_teams import MSTeamsClient
from core.log_buffer import LogBuffer
from core.models import JobRequest, TicketEnvRequest
from core.models.run_context import RunContext
from core.runner import Runner


class Api:
    def __init__(self):
        self._window: webview.Window | None = None

        settings = settings_manager.load_settings()

        self._log_buffer = LogBuffer()
        self._jenkins_client = JenkinsClient(
            settings["jenkins"]["base_url"], settings["jenkins"]["username"], secrets.get_token() or ""
        )
        self._teams_client = MSTeamsClient(settings["notification_connectors"]["teams"]["webhook_url"])

        self._jobs_config = settings["jobs_config"]

        context = RunContext(
            jenkins_client=self._jenkins_client,
            poll_interval_seconds=settings["job_run_config"]["poll_interval_minutes"] * 60,
            max_retries=settings["job_run_config"]["max_retries"],
            teams_webhook_url=settings["notification_connectors"]["teams"]["webhook_url"] or None,
            log_buffer=self._log_buffer,
        )
        self._runner = Runner(context)

    def run_all(self, ticket_requests: list[dict]) -> dict:
        ticket_requests = [
            TicketEnvRequest(
                ticket_id=ticket_request["ticket_id"],
                jobs=[JobRequest(**job) for job in ticket_request["jobs"]],
            )
            for ticket_request in ticket_requests
        ]
        for index, ticket in enumerate(ticket_requests, start=1):
            ticket.ticket_id = ticket.ticket_id.strip() or f"Ticket {index}"

        user_input_check = validate(
            ticket_requests,
            self._jobs_config,
            self._jenkins_client,
            self._teams_client,
            self._log_buffer,
        )

        if not user_input_check.passed:
            return {"errors": user_input_check.errors, "token_missing": user_input_check.token_missing}

        self._log_buffer.clear_before_new_run()
        self._runner.start(ticket_requests)

        return {"errors": [], "token_missing": False}

    def get_new_logs(self) -> list[dict]:
        return [
            {"timestamp": entry.timestamp, "level": entry.level.value, "message": entry.message}
            for entry in self._log_buffer.pull_new_logs()
        ]

    def is_runner_finished(self) -> bool:
        return not self._runner.is_in_progress

    def get_settings(self) -> dict:
        return settings_manager.load_settings()

    def save_settings(self, data: dict) -> None:
        settings_manager.save_settings(data)

    def reset_settings(self) -> dict:
        return settings_manager.reset_to_defaults()

    def save_token(self, token: str) -> dict:
        secrets.set_token(token)
        return self.get_token_status()

    def get_token_status(self) -> dict:
        return {"saved": secrets.has_token()}

    def get_connection_status(self) -> dict:
        return {
            "jenkins": self._jenkins_client.check_connection(),
            "teams": self._teams_client.check_connection(),
        }

    def restart_app(self) -> None:
        if self._window is not None:
            self._window.is_exiting = True
            self._window.destroy()

        os.execv(sys.executable, [sys.executable] + sys.argv)

    def exit_app(self) -> None:
        if self._window is not None:
            self._window.is_exiting = True
            self._window.destroy()

        os._exit(0)
