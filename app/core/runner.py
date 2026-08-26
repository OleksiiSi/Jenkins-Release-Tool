import time
from concurrent.futures import Future, ThreadPoolExecutor, wait
from typing import Callable

from core import notifications
from core.config import MAX_WORKERS
from core.models import (
    BuildStatus,
    JobRequest,
    JobRunResult,
    LogLevel,
    PromotionResult,
    PromotionStatus,
    TicketEnvRequest,
)
from core.models.run_context import RunContext


class Runner:
    """Orchestrates build -> poll -> promote-per-environment-in-parallel for
    a batch of tickets, submitting every step to its own executor. One
    instance can be reused across multiple `start()` calls - everything in
    `context` is fixed for the process lifetime, and the executor is built
    once, here, for the same reason (nothing outside Runner ever submits to
    it, so nobody else needs a reference to construct or share it)."""

    def __init__(self, context: RunContext):
        self.context = context
        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self._active_futures: list[Future] = []

    @property
    def is_in_progress(self) -> bool:
        """True if any future submitted by any `start()` call so far -
        across possibly multiple overlapping runs - isn't done yet. False
        before the first `start()` call (the list starts empty) and once
        every submitted future has completed."""
        return not all(future.done() for future in self._active_futures)

    def start(self, tickets: list[TicketEnvRequest]) -> None:
        """Submit one task per (ticket x job) and return immediately -
        doesn't block until the run finishes. Each task builds, then (on
        success) submits one promotion task per environment to the same
        executor and waits on those - so `context.executor` needs a generous
        worker count. A worker blocked waiting on other futures does not free
        itself up to run other queued tasks in the meantime; with too few
        workers, enough simultaneous build tasks blocked on their own
        promotion futures can starve those very promotion tasks of a thread
        to run on, deadlocking the run. Threads (not asyncio) is a deliberate
        MVP choice for this app's scale - if starvation ever becomes a real
        risk rather than a theoretical one, migrating to asyncio
        (httpx.AsyncClient + asyncio.sleep instead of requests + blocking
        time.sleep) is the known escape hatch. One more worker stays blocked
        for the whole run's duration beyond that: one task per ticket that
        waits on just that ticket's own job futures to log when the ticket
        finishes - factor these into `max_workers` sizing too, alongside
        `_track_new_futures`'s job of keeping `_active_futures` accurate
        across overlapping `start()` calls."""
        self.context.log_buffer.append(
            f"[System] Run started for tickets: {', '.join(ticket.ticket_id for ticket in tickets)}", LogLevel.INFO
        )

        all_new_futures: list[Future] = []

        for ticket in tickets:
            ticket_futures: list[Future] = []
            # Parallel to `ticket_futures` - job_name for each submitted
            # task, so _log_ticket_finished can attribute an unhandled
            # exception back to the job it came from without needing
            # JobRunResult (which isn't available when a task raised
            # instead of returning one). ticket_id isn't needed here - every
            # job in this list belongs to the same `ticket`.
            ticket_job_names: list[str] = []

            for job in ticket.jobs:
                future = self._executor.submit(self._run_job, ticket, job)
                ticket_futures.append(future)
                ticket_job_names.append(job.job_name)
                all_new_futures.append(future)

            self._executor.submit(self._log_ticket_finished, ticket, ticket_futures, ticket_job_names)

        self._track_new_futures(all_new_futures)

    def _track_new_futures(self, new_futures: list[Future]) -> None:
        """Folds this `start()` call's futures into `_active_futures`,
        dropping any already-done futures from a prior overlapping
        `start()` call along the way - so `is_in_progress` reflects every
        run still active, not just the most recent one, without the list
        growing unboundedly across a long-running session."""
        still_running_futures = [future for future in self._active_futures if not future.done()]
        self._active_futures = still_running_futures + new_futures

    def _log_ticket_finished(self, ticket: TicketEnvRequest, futures: list[Future], job_names: list[str]) -> None:
        wait(futures)

        succeeded = 0
        failed = 0

        for future, job_name in zip(futures, job_names):
            # A worker task's exception is only surfaced by fetching it -
            # wait() alone would let it vanish silently (a documented
            # ThreadPoolExecutor footgun: nothing else in this run ever
            # calls .result() on these top-level futures). Checking
            # every future here, once, closes that hole - the only other
            # thing done with them (is_in_progress) just checks .done().
            exc = future.exception()

            if exc is not None:
                failed += 1
                self.context.log_buffer.append(
                    f"[{ticket.ticket_id}][{job_name}][System] Unexpected error - job did not complete: {exc}",
                    LogLevel.FAILURE,
                )
                continue

            job_result = future.result()
            job_fully_succeeded = job_result.status == BuildStatus.SUCCESS and all(
                promo.status == PromotionStatus.SUCCESS for promo in job_result.promotions
            )

            if job_fully_succeeded:
                succeeded += 1
            else:
                failed += 1

        self.context.log_buffer.append(
            f"[{ticket.ticket_id}][System] Ticket finished: {succeeded} succeeded, {failed} failed "
            f"({len(futures)} jobs)",
            LogLevel.INFO,
        )

    def _notify(self, title: str, message: str, ticket_id: str, tag: str) -> None:
        """Fire both notification channels (core.notifications.notify) and,
        if the Teams send specifically failed, surface it in the UI log
        panel - it otherwise only reaches a Python logger the QA user never
        sees."""
        teams_failure_detail = notifications.notify(title, message, self.context.teams_webhook_url)

        if teams_failure_detail:
            self.context.log_buffer.append(
                f"[{ticket_id}][{tag}][Notify] Teams notification failed: {teams_failure_detail}", LogLevel.FAILURE
            )

    def _run_job(self, ticket: TicketEnvRequest, job: JobRequest) -> JobRunResult:
        job_result = self._build_with_retries(ticket, job)

        if job_result.status != BuildStatus.SUCCESS:
            return job_result

        if not job.environments:
            self.context.log_buffer.append(
                f"[{ticket.ticket_id}][{job_result.tag}][Promote] No environments selected - skipping promotion",
                LogLevel.INFO,
            )
            return job_result

        env_promotion_futures = [
            self._executor.submit(self._promote_with_retries, job_result, env_name, promotion_process)
            for env_name, promotion_process in job.environments.items()
        ]

        job_result.promotions = [future.result() for future in env_promotion_futures]

        return job_result

    def _build_with_retries(self, ticket: TicketEnvRequest, job: JobRequest) -> JobRunResult:
        job_run_result = JobRunResult(ticket_id=ticket.ticket_id, job_name=job.job_name)

        def on_build_number_resolved(build_number: int) -> None:
            # Fired from inside _run_single_build as soon as the queue item
            # resolves, before it starts polling build status - so the log
            # panel shows the build number the moment it's known, not only
            # once the build finishes.
            job_run_result.build_number = build_number
            self.context.log_buffer.append(
                f"[{ticket.ticket_id}][{job_run_result.tag}][Build] Build number assigned", LogLevel.INFO
            )

        for attempt_num in range(self.context.max_retries + 1):
            job_run_result.status = BuildStatus.BUILDING
            job_run_result.retry_count = attempt_num

            params_text = ", ".join(f"{name}={value}" for name, value in job.parameters.items())
            message = f"Build triggered, {params_text}" if params_text else "Build triggered"
            self.context.log_buffer.append(
                f"[{ticket.ticket_id}][{job.job_name}][Build] {message}",
                LogLevel.INFO,
            )

            success, build_number, error_detail = self._run_single_build(
                job.job_name, job.parameters, on_build_number_resolved
            )
            job_run_result.build_number = build_number
            tag = job_run_result.tag

            if error_detail:
                self.context.log_buffer.append(
                    f"[{ticket.ticket_id}][{tag}][Build] ERROR: {error_detail}", LogLevel.FAILURE
                )

            if success and isinstance(build_number, int):
                job_run_result.status = BuildStatus.SUCCESS
                self.context.log_buffer.append(f"[{ticket.ticket_id}][{tag}][Build] SUCCESS", LogLevel.SUCCESS)

                self._notify(
                    f"[{ticket.ticket_id}] {job.job_name} build succeeded",
                    f"Build #{build_number} succeeded.",
                    ticket.ticket_id,
                    tag,
                )

                return job_run_result

            if attempt_num < self.context.max_retries:
                self.context.log_buffer.append(
                    f"[{ticket.ticket_id}][{tag}][Build] FAILURE, retry {attempt_num + 1}/{self.context.max_retries}",
                    LogLevel.FAILURE,
                )

            else:
                self.context.log_buffer.append(
                    f"[{ticket.ticket_id}][{tag}][Build] FAILURE, retries exhausted",
                    LogLevel.FAILURE
                )

        job_run_result.status = BuildStatus.FAILED

        self._notify(
            f"[{ticket.ticket_id}] {job.job_name} build failed",
            f"Build failed after {self.context.max_retries} retries.",
            ticket.ticket_id,
            job_run_result.tag,
        )

        return job_run_result

    def _run_single_build(
        self, job_name: str, params: dict[str, str], on_build_number_resolved: Callable[[int], None]
    ) -> tuple[bool, int | None, str | None]:
        build_number = None

        try:
            queue_url = self.context.jenkins_client.trigger_build(job_name, params)
            build_number = self.context.jenkins_client.resolve_build_number(queue_url)
            on_build_number_resolved(build_number)

            while True:
                time.sleep(self.context.poll_interval_seconds)

                status = self.context.jenkins_client.get_build_status(job_name, build_number)

                if not status["building"]:
                    return status["result"] == "SUCCESS", build_number, None

        except Exception as exc:
            return False, build_number, str(exc)

    def _promote_with_retries(self, result: JobRunResult, env: str, promotion_name: str) -> PromotionResult:
        assert result.build_number is not None, "a SUCCESS build must have a resolved build_number"
        build_number = result.build_number

        promo = PromotionResult(environment=env)
        tag = result.tag

        if self.context.jenkins_client.promotion_exists(result.job_name, build_number, promotion_name):
            self.context.log_buffer.append(
                f"[{result.ticket_id}][{tag}][Promote] Promotion to {env} already exists - redoing it",
                LogLevel.WARNING,
            )

        for attempt in range(self.context.max_retries + 1):
            promo.status = PromotionStatus.PROMOTING
            promo.retry_count = attempt

            self.context.log_buffer.append(
                f"[{result.ticket_id}][{tag}][Promote] Promotion to {env} triggered", LogLevel.INFO
            )

            success, error_detail = self._run_single_promotion(result.job_name, build_number, promotion_name)

            if error_detail:
                self.context.log_buffer.append(
                    f"[{result.ticket_id}][{tag}][Promote] ERROR: {error_detail}", LogLevel.FAILURE
                )

            if success:
                promo.status = PromotionStatus.SUCCESS

                self.context.log_buffer.append(f"[{result.ticket_id}][{tag}][Promote] Promote to {env} - SUCCESS",
                                         LogLevel.SUCCESS)

                self._notify(
                    f"[{result.ticket_id}] {result.job_name} promoted to {env}",
                    f"Build #{build_number} promoted to {env}.",
                    result.ticket_id,
                    tag,
                )

                return promo

            if attempt < self.context.max_retries:
                self.context.log_buffer.append(
                    f"[{result.ticket_id}][{tag}][Promote] Promote to {env} - FAILURE, "
                    f"retry {attempt + 1}/{self.context.max_retries}",
                    LogLevel.FAILURE,
                )
            else:
                self.context.log_buffer.append(
                    f"[{result.ticket_id}][{tag}][Promote] Promote to {env} - FAILURE, retries exhausted",
                    LogLevel.FAILURE,
                )

        promo.status = PromotionStatus.FAILED
        self._notify(
            f"[{result.ticket_id}] {result.job_name} promotion to {env} failed",
            f"Promotion of build #{build_number} to {env} failed after {self.context.max_retries} retries.",
            result.ticket_id,
            tag,
        )

        return promo

    def _run_single_promotion(self, job_name: str, build_number: int, promotion_name: str) -> tuple[bool, str | None]:
        try:
            self.context.jenkins_client.trigger_promotion(job_name, build_number, promotion_name)

            while True:
                time.sleep(self.context.poll_interval_seconds)

                status = self.context.jenkins_client.get_promotion_status(job_name, build_number, promotion_name)

                if not status["building"]:
                    return status["result"] == "SUCCESS", None

        except Exception as exc:
            return False, str(exc)
