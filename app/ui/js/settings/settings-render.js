import { paramDefRowTemplate, envDefRowTemplate, jobConfigCardTemplate } from '../templates.js';

export function renderSettingsForm(settings) {
    document.getElementById('jenkinsBaseUrl').value = settings.jenkins.base_url;
    document.getElementById('jenkinsUsername').value = settings.jenkins.username;
    document.getElementById('pollIntervalMinutes').value = settings.job_run_config.poll_interval_minutes;
    document.getElementById('maxRetries').value = settings.job_run_config.max_retries;
    document.getElementById('teamsWebhookUrl').value = settings.notification_connectors.teams.webhook_url;

    document.getElementById('generalParamsList').innerHTML = '';
    for (const paramDef of settings.jobs_config.general.parameters) {
        addGeneralParamRow(paramDef);
    }

    document.getElementById('generalEnvsList').innerHTML = '';
    for (const environmentDefinition of settings.jobs_config.general.environments) {
        addGeneralEnvRow(environmentDefinition);
    }

    document.getElementById('jobsList').innerHTML = '';
    for (const [jobName, jobDef] of Object.entries(settings.jobs_config.job_specific)) {
        addJobConfigCard(jobName, jobDef);
    }
}

function buildParamDefRow(parameterDefinition, showUniqueFlag) {
    const row = paramDefRowTemplate.content.firstElementChild.cloneNode(true);

    const nameInput = row.querySelector('.param-def-name');
    const typeSelect = row.querySelector('.param-def-type');
    const optionsInput = row.querySelector('.param-def-options');
    const uniqueWrap = row.querySelector('.param-def-unique-wrap');
    const uniqueCheckbox = row.querySelector('.param-def-unique');
    const removeBtn = row.querySelector('.list-row-remove');

    nameInput.value = parameterDefinition.name || '';
    typeSelect.value = parameterDefinition.type || 'string';

    optionsInput.value = (parameterDefinition.options || []).join(', ');
    optionsInput.style.display = typeSelect.value === 'dropdown' ? '' : 'none';

    uniqueWrap.style.display = showUniqueFlag ? '' : 'none';
    uniqueCheckbox.checked = !!parameterDefinition.is_unique_between_tickets;

    typeSelect.onchange = () => {
        optionsInput.style.display = typeSelect.value === 'dropdown' ? '' : 'none';
    };

    removeBtn.onclick = () => row.remove();

    row._nameInput = nameInput;
    row._typeSelect = typeSelect;
    row._optionsInput = optionsInput;
    row._uniqueCheckbox = uniqueCheckbox;

    return row;
}

export function addGeneralParamRow(parameterDefinition = {}) {
    document.getElementById('generalParamsList').appendChild(buildParamDefRow(parameterDefinition, true));
}

function addJobParamRow(container, parameterDefinition = {}) {
    container.appendChild(buildParamDefRow(parameterDefinition, false));
}

function buildEnvDefRow(environmentDefinition) {
    const row = envDefRowTemplate.content.firstElementChild.cloneNode(true);

    const nameInput = row.querySelector('.env-def-name');
    const processInput = row.querySelector('.env-def-process');
    const removeBtn = row.querySelector('.list-row-remove');

    nameInput.value = environmentDefinition.name || '';
    processInput.value = environmentDefinition.promotion_process || '';
    removeBtn.onclick = () => row.remove();

    row._nameInput = nameInput;
    row._processInput = processInput;

    return row;
}

export function addGeneralEnvRow(environmentDefinition = {}) {
    document.getElementById('generalEnvsList').appendChild(buildEnvDefRow(environmentDefinition));
}

function addJobEnvRow(container, environmentDefinition = {}) {
    container.appendChild(buildEnvDefRow(environmentDefinition));
}

function buildJobConfigCard(jobName, jobDef) {
    const card = jobConfigCardTemplate.content.firstElementChild.cloneNode(true);

    const head = card.querySelector('.ticket-card-head');
    const nameInput = card.querySelector('.job-name-input');
    const removeBtn = card.querySelector('.icon-btn');
    const paramsList = card.querySelector('.job-parameters-list');
    const envsList = card.querySelector('.job-environments-list');
    const addButtons = card.querySelectorAll('.list-add-btn');

    head.onclick = (event) => {
        if (event.target === nameInput) return;
        card.classList.toggle('expanded');
    };

    nameInput.value = jobName;
    nameInput.onclick = (event) => event.stopPropagation();

    removeBtn.onclick = (event) => { event.stopPropagation(); card.remove(); };

    for (const paramDef of jobDef.parameters || []) addJobParamRow(paramsList, paramDef);
    for (const environmentDefinition of jobDef.environments || []) addJobEnvRow(envsList, environmentDefinition);

    addButtons[0].onclick = () => addJobParamRow(paramsList, {});
    addButtons[1].onclick = () => addJobEnvRow(envsList, {});

    card._nameInput = nameInput;
    card._paramsList = paramsList;
    card._envsList = envsList;

    return card;
}

export function addJobConfigCard(jobName = '', jobDef = { parameters: [], environments: [] }) {
    document.getElementById('jobsList').appendChild(buildJobConfigCard(jobName, jobDef));
}
