// Trims a required text/number input, toggles its `.error` class, and
// returns the trimmed value plus an error message (or null) - shared by the
// three flat required fields in collectRequiredFieldsFromForm().
function collectRequiredField(input, emptyMessage) {
    const value = input.value.trim();
    input.classList.toggle('error', !value);

    return { value, error: value ? null : emptyMessage };
}

function collectRequiredFieldsFromForm() {
    const errors = [];

    const baseUrl = collectRequiredField(
        document.getElementById('jenkinsBaseUrl'), 'Jenkins base URL cannot be empty'
    );

    const username = collectRequiredField(
        document.getElementById('jenkinsUsername'), 'Jenkins username cannot be empty'
    );

    const pollIntervalMinutes = collectRequiredField(
        document.getElementById('pollIntervalMinutes'), 'Poll interval (min) cannot be empty'
    );

    const maxRetries = collectRequiredField(
        document.getElementById('maxRetries'), 'Max retries cannot be empty'
    );

    if (baseUrl.error) errors.push(baseUrl.error);
    if (username.error) errors.push(username.error);
    if (pollIntervalMinutes.error) errors.push(pollIntervalMinutes.error);
    if (maxRetries.error) errors.push(maxRetries.error);

    return {
        baseUrl: baseUrl.value,
        username: username.value,
        pollIntervalMinutes: Number(pollIntervalMinutes.value) || 0,
        maxRetries: Number(maxRetries.value) || 0,
        errors,
    };
}

function collectParamDefRows(container, requireUniqueFlag) {
    const errors = [];
    const parameters = [];

    for (const row of container.children) {
        const name = row._nameInput.value.trim();
        row._nameInput.classList.toggle('error', !name);
        if (!name) { errors.push('Parameter name cannot be empty'); continue; }

        const type = row._typeSelect.value;
        const paramDef = { name, type };
        if (type === 'dropdown') {
            paramDef.options = row._optionsInput.value.split(',').map((o) => o.trim()).filter(Boolean);
        }
        if (requireUniqueFlag) {
            paramDef.is_unique_between_tickets = row._uniqueCheckbox.checked;
        }

        parameters.push(paramDef);
    }

    return { parameters, errors };
}

function collectEnvDefRows(container) {
    const errors = [];
    const environments = [];

    for (const row of container.children) {
        const name = row._nameInput.value.trim();
        const process = row._processInput.value.trim();

        row._nameInput.classList.toggle('error', !name);
        row._processInput.classList.toggle('error', !process);

        if (!name) errors.push('Environment name cannot be empty');
        if (!process) errors.push('Environment promotion process cannot be empty');

        if (name && process) environments.push({ name, promotion_process: process });
    }

    return { environments, errors };
}

function collectJobsConfigFromForm() {
    const errors = [];
    const jobSpecific = {};

    for (const card of document.getElementById('jobsList').children) {
        const name = card._nameInput.value.trim();
        card._nameInput.classList.toggle('error', !name);
        if (!name) { errors.push('Job name cannot be empty'); continue; }

        const { parameters, errors: paramErrors } = collectParamDefRows(card._paramsList, false);
        const { environments, errors: envErrors } = collectEnvDefRows(card._envsList);

        errors.push(...paramErrors, ...envErrors);
        jobSpecific[name] = { parameters, environments };
    }

    return { jobSpecific, errors };
}

export function collectSettingsFromForm() {
    const requiredFields = collectRequiredFieldsFromForm();
    const { parameters: generalParameters, errors: generalParamErrors } =
        collectParamDefRows(document.getElementById('generalParamsList'), true);
    const { environments: generalEnvironments, errors: generalEnvErrors } =
        collectEnvDefRows(document.getElementById('generalEnvsList'));
    const { jobSpecific, errors: jobErrors } = collectJobsConfigFromForm();

    const settings = {
        jenkins: { base_url: requiredFields.baseUrl, username: requiredFields.username },
        notification_connectors: { teams: { webhook_url: document.getElementById('teamsWebhookUrl').value.trim() } },
        job_run_config: {
            poll_interval_minutes: requiredFields.pollIntervalMinutes,
            max_retries: requiredFields.maxRetries,
        },
        jobs_config: {
            general: { parameters: generalParameters, environments: generalEnvironments },
            job_specific: jobSpecific,
        },
    };

    const errors = [...requiredFields.errors, ...generalParamErrors, ...generalEnvErrors, ...jobErrors];

    return { settings, errors: [...new Set(errors)] };
}
