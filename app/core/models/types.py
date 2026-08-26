from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


# =============================== STATUS ENUMS ================================

class BuildStatus(StrEnum):
    """State of one JobRunResult's build, before/during/after retries."""

    PENDING = "pending"
    BUILDING = "building"
    SUCCESS = "success"
    FAILED = "failed"


class PromotionStatus(StrEnum):
    """State of one PromotionResult, before/during/after retries."""

    PENDING = "pending"
    PROMOTING = "promoting"
    SUCCESS = "success"
    FAILED = "failed"


class LogLevel(StrEnum):
    """Matches the UI's log-line color classes: info/ok/fail/warn."""

    INFO = "info"
    SUCCESS = "ok"
    FAILURE = "fail"
    WARNING = "warn"


# ================================= UI BRIDGE =================================

@dataclass
class LogEntry:
    """One buffered log line, held in a LogBuffer's append-order list.

    :ivar logged_at: Recorded at append time, not left for the polling
        caller to stamp on arrival - polling happens on an interval, so
        arrival time drifts from event time, worse across a sleep/resume.
    """

    logged_at: datetime
    message: str
    level: LogLevel

    @property
    def timestamp(self) -> str:
        """`logged_at` formatted as "mm-dd-yyyy HH:MM:SS.mmm"."""
        return self.logged_at.strftime("%m-%d-%Y %H:%M:%S.%f")[:-3]


# =============================== DOMAIN MODELS ===============================

# --- Request ---

@dataclass
class JobRequest:
    """One job's resolved request data for one ticket - already merged
    (general + job-specific) by the UI/API layer before core/ ever sees it.

    :ivar job_name: Jenkins job name to trigger.
    :ivar parameters: Every parameter this job needs, name -> value -
        general values and this job's job-specific values already combined.
    :ivar environments: Every environment to promote to for this job,
        UI display name -> Jenkins promotion process name - general
        environments (selected on the ticket) and this job's selected
        job-specific environments already combined.
    """

    job_name: str
    parameters: dict[str, str]
    environments: dict[str, str]


@dataclass
class TicketEnvRequest:
    """One user-entered request: build and promote a set of jobs for one
    ticket. One application run is a list of these.

    :ivar ticket_id: The external tracking system's ticket ID this request
        is for, e.g. 'ID-001'.
    :ivar jobs: One entry per job selected for this ticket, each already
        carrying its own resolved parameters/environments.
    """

    ticket_id: str
    jobs: list[JobRequest]


# --- Run Results ---

@dataclass
class PromotionResult:
    """Outcome of promoting one already-built job to one environment.

    :ivar environment: Environment name this promotion targets.
    :ivar status: Current state of the promotion attempt.
    :ivar retry_count: Number of retries attempted so far (0 on the first
        attempt).
    """

    environment: str
    status: PromotionStatus = PromotionStatus.PENDING
    retry_count: int = 0


@dataclass
class JobRunResult:
    """Outcome of building one job for one ticket, plus the promotion result
    for each environment that build was pushed to.

    :ivar ticket_id: The TicketEnvRequest.ticket_id this build belongs to.
    :ivar job_name: Jenkins job name that was built.
    :ivar build_number: Resolved Jenkins build number, or None before the
        queue item resolves or if triggering the build failed outright.
    :ivar status: Current state of the build.
    :ivar retry_count: Number of retries attempted so far (0 on the first
        attempt).
    :ivar promotions: One entry per environment this build was promoted to;
        populated only after the build itself succeeds.
    """

    ticket_id: str
    job_name: str
    build_number: int | None = None
    status: BuildStatus = BuildStatus.PENDING
    retry_count: int = 0
    promotions: list[PromotionResult] = field(default_factory=list)

    @property
    def tag(self) -> str:
        """Log-line identity for this job: job_name, plus the build number
        once one's been resolved."""
        return f"{self.job_name} - #{self.build_number}" if self.build_number is not None else self.job_name


# --- Validation ---

@dataclass
class ValidationResult:
    """Result of pre-run validation - collects every failure instead of
    stopping at the first one, so the UI can surface them all at once.

    :ivar errors: Human-readable validation failure messages.
    :ivar token_missing: True if no Jenkins API token is saved in keyring -
        kept separate from `errors` so the UI can point the user straight to
        Settings.
    """

    errors: list[str] = field(default_factory=list)
    token_missing: bool = False

    @property
    def passed(self) -> bool:
        return not self.errors and not self.token_missing
