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
    return {param["name"]: {} for param in general_parameters_config if param.get("is_unique_between_tickets")}


def _validate_jobs_and_environments_selected(ticket: TicketEnvRequest) -> list[str]:
    if not ticket.jobs:
        return [f"{ticket.ticket_id}: no jobs selected"]

    return []


def _validate_general_parameters(
    ticket: TicketEnvRequest, general_parameters_config: list[dict], seen_unique_values: dict[str, dict[str, str]]
) -> list[str]:
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
    errors = []

    if not token_missing:
        if jenkins_client.check_connection():
            _log_connectivity_pass(log_buffer, "Jenkins", jenkins_client)
        else:
            errors.append("Jenkins connection check failed")
            log_buffer.append(
                f"[System] Jenkins connection check failed: {jenkins_client.last_check_detail}", LogLevel.FAILURE
            )

    if teams_client.webhook_url.strip():
        if teams_client.check_connection():
            _log_connectivity_pass(log_buffer, "Teams", teams_client)
        else:
            log_buffer.append(
                f"[System] Teams connection check failed: {teams_client.last_check_detail}", LogLevel.FAILURE
            )

    return errors


def _log_connectivity_pass(log_buffer: LogBuffer, service_name: str, client: JenkinsClient | MSTeamsClient) -> None:
    if client.last_check_was_cached:
        log_buffer.append(f"[System] {service_name} connection check skipped (cached, last check OK)", LogLevel.INFO)
    else:
        log_buffer.append(f"[System] {service_name} connection check passed", LogLevel.SUCCESS)
