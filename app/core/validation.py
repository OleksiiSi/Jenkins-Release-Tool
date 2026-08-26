from core import secrets
from core.clients.jenkins import JenkinsClient
from core.clients.ms_teams import MSTeamsClient
from core.log_buffer import LogBuffer
from core.models import LogLevel, TicketEnvRequest, ValidationResult


def validate(
    tickets: list[TicketEnvRequest],
    jobs_config: dict,
    jenkins_client: JenkinsClient,
    teams_client: MSTeamsClient,
    log_buffer: LogBuffer,
) -> ValidationResult:
    """Run every pre-run check against `tickets` and the two clients,
    collecting all failures instead of stopping at the first one.

    :param tickets: The run's requested tickets, each already carrying its
        jobs' resolved parameters/environments.
    :param jobs_config: settings.json's jobs_config, as-is - "general"
        ({"parameters": [...], "environments": [...]}) drives the
        uniqueness and required-ness checks for general parameters below;
        "job_specific" (job name -> {"parameters": [...], "environments":
        [...]}) drives which job-specific parameters each selected job
        requires.
    :param jenkins_client: Used for the Jenkins connectivity check.
    :param teams_client: Used for the Teams connectivity check.
    :param log_buffer: Connectivity check failures are logged here.
    """
    general_parameters_config = jobs_config["general"]["parameters"]
    job_specific_config = jobs_config["job_specific"]

    validation_result = ValidationResult()
    seen_unique_values = _build_unique_value_trackers(general_parameters_config)

    for ticket in tickets:
        validation_result.errors.extend(_validate_jobs_and_environments_selected(ticket))

        if not ticket.jobs:
            continue

        validation_result.errors.extend(_validate_general_parameters(ticket, general_parameters_config, seen_unique_values))
        validation_result.errors.extend(_validate_job_specific_parameters(ticket, job_specific_config))

    validation_result.token_missing = not secrets.has_token()
    validation_result.errors.extend(_validate_connectivity(validation_result.token_missing, jenkins_client, teams_client, log_buffer))

    return validation_result


def _build_unique_value_trackers(general_parameters_config: list[dict]) -> dict[str, dict[str, str]]:
    """name -> {value -> ticket_id that used it first}, one entry per
    general parameter flagged unique. Shared across every ticket
    `_validate_general_parameters` is called for, so uniqueness is tracked
    across the whole run rather than reset per ticket."""
    return {param["name"]: {} for param in general_parameters_config if param.get("is_unique_between_tickets")}


def _validate_jobs_and_environments_selected(ticket: TicketEnvRequest) -> list[str]:
    """A ticket needs at least one job. Environments are optional - a job
    with none is a build-only run (Runner skips promotion for it and logs
    that it did so), so no environments-selected check is needed here."""
    if not ticket.jobs:
        return [f"{ticket.ticket_id}: no jobs selected"]

    return []


def _validate_general_parameters(
    ticket: TicketEnvRequest, general_parameters_config: list[dict], seen_unique_values: dict[str, dict[str, str]]
) -> list[str]:
    """Required-ness and cross-ticket uniqueness for one ticket's general
    parameters, read from its first job - every job on a ticket carries an
    identical copy of each general value (the UI merges them in), so
    reading from any one job is representative of the whole ticket."""
    errors = []
    representative_job = ticket.jobs[0]

    for general_param_config in general_parameters_config:
        param_name = general_param_config["name"]
        value = representative_job.parameters.get(param_name, "").strip()

        if not value:
            errors.append(f"{ticket.ticket_id}: {param_name} is not set")
            continue

        if not param_name in seen_unique_values:
            continue

        if value in seen_unique_values[param_name]:
            errors.append(
                f"{ticket.ticket_id}: {param_name} '{value}' is also used by {seen_unique_values[param_name][value]}"
            )

        else:
            seen_unique_values[param_name][value] = ticket.ticket_id

    return errors


def _validate_job_specific_parameters(ticket: TicketEnvRequest, job_specific_config: dict[str, dict]) -> list[str]:
    """Required-ness for each of a ticket's selected jobs' job-specific
    parameters."""
    errors = []

    for requested_job in ticket.jobs:

        for param_config in job_specific_config.get(requested_job.job_name, {}).get("parameters", []):
            param_name = param_config["name"]

            if not requested_job.parameters.get(param_name, "").strip():
                errors.append(f"{ticket.ticket_id}: {requested_job.job_name} - {param_name} is not set")

    return errors


def _validate_connectivity(
    token_missing: bool, jenkins_client: JenkinsClient, teams_client: MSTeamsClient, log_buffer: LogBuffer
) -> list[str]:
    """Jenkins/Teams connectivity checks - independent of any ticket."""
    errors = []

    if not token_missing:
        if jenkins_client.check_connection():
            _log_connectivity_pass(log_buffer, "Jenkins", jenkins_client)
        else:
            errors.append("Jenkins connection check failed")
            log_buffer.append(
                f"[System] Jenkins connection check failed: {jenkins_client.last_check_detail}", LogLevel.FAILURE
            )

    # Teams connectivity is checked (refreshing the cache/chip) but doesn't
    # block the run - notifications are a best-effort side channel (see
    # core/notifications.py), not a reason to stop actual Jenkins work.
    if teams_client.webhook_url.strip():
        if teams_client.check_connection():
            _log_connectivity_pass(log_buffer, "Teams", teams_client)
        else:
            log_buffer.append(
                f"[System] Teams connection check failed: {teams_client.last_check_detail}", LogLevel.FAILURE
            )

    return errors


def _log_connectivity_pass(log_buffer: LogBuffer, service_name: str, client: JenkinsClient | MSTeamsClient) -> None:
    """Logs a passing connectivity check - distinguishing a fresh network
    probe from one skipped because the cache already held a fresh "ok", so a
    passing check isn't silent either way."""
    if client.last_check_was_cached:
        log_buffer.append(f"[System] {service_name} connection check skipped (cached, last check OK)", LogLevel.INFO)
    else:
        log_buffer.append(f"[System] {service_name} connection check passed", LogLevel.SUCCESS)
