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
    """The pywebview js_api bridge - the only file that imports both core/
    and exposes methods to JS. Every method here is a thin delegation to
    core/; no business logic lives here.
    """

    def __init__(self):
        # Set by main.py right after webview.create_window() returns (Api is
        # constructed first, so the window doesn't exist yet in __init__).
        # Used only to destroy() the WebView2 control cleanly before
        # restart_app()/exit_app() tear down the process - see those methods.
        # MUST stay underscore-prefixed: pywebview's js_api introspection
        # (webview/util.py's get_functions()) walks every *public* attribute
        # reachable from this object to build the JS bridge, recursing into
        # non-callable ones - a public `self.window` here made it recurse
        # into the Window object's own attributes and crash on a .NET
        # Rectangle geometry property pythonnet couldn't compare against Api.
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
            # Mirrors the "Ticket N" placeholder shown in the UI's ticket-ID
            # input when left blank - normalized here, once, so validation
            # messages and the actual run/log output agree on the same ID.
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
        # Dispose the WebView2 control before re-launching - os.execv on
        # Windows isn't a true in-place replace (it spawns the new process,
        # then _exit(0)s this one - see bpo-19124/bpo-9148), so without this
        # the old, uncleanly-killed WebView2 helper processes and the new
        # process's fresh WebView2 environment can contend over the same
        # user-data-folder lock, slowing down the very restart this triggers.
        if self._window is not None:
            # is_exiting=True stops main.py's on_closing() from mistaking the
            # Form.Close() destroy() triggers for the user clicking "X" and
            # firing its "still running in background" toast - misleading
            # here, since the app is restarting, not backgrounding.
            self._window.is_exiting = True
            self._window.destroy()

        os.execv(sys.executable, [sys.executable] + sys.argv)

    def exit_app(self) -> None:
        # Full process termination, not a graceful shutdown - in-progress
        # builds/promotions are killed outright. Same semantics as the tray
        # icon's "Exit" (main.py), just reachable without opening the tray menu.
        # window.destroy() first still lets WebView2 dispose its own helper
        # processes cleanly rather than being orphaned by os._exit() - it
        # only tears down the UI, not any of the background work.
        if self._window is not None:
            # See restart_app()'s comment - same misleading-toast risk here.
            self._window.is_exiting = True
            self._window.destroy()

        os._exit(0)
