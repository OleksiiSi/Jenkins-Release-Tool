import { generalParametersConfig, generalEnvironmentsConfig, jobsConfig } from '../app-config.js';
import { setTicketPendingRemoval } from '../session-state.js';
import { showModal } from '../tabs-modals.js';
import { ticketCardTemplate, checkboxRowTemplate, jobCheckboxRowTemplate } from '../templates.js';
import { renderParamInputList } from './param-input.js';

export function renderTicketCard(renderedTicketState) {
    const newCard = ticketCardTemplate.content.firstElementChild.cloneNode(true);

    const head = newCard.querySelector('.ticket-card-head');
    const idInput = newCard.querySelector('.ticket-id-input');
    const summary = newCard.querySelector('.ticket-summary');
    const removeBtn = newCard.querySelector('.icon-btn');
    const generalParamsList = newCard.querySelector('.general-params-list');
    const jobsList = newCard.querySelector('.jobs-checkbox-list');
    const envsList = newCard.querySelector('.environments-checkbox-list');

    head.onclick = () => newCard.classList.toggle('expanded');

    idInput.value = renderedTicketState.ticketId;
    idInput.onclick = (event) => event.stopPropagation();
    idInput.oninput = () => { renderedTicketState.ticketId = idInput.value; };

    removeBtn.onclick = (event) => {
        event.stopPropagation();

        setTicketPendingRemoval({ ticketState: renderedTicketState, card: newCard });
        showModal('removeTicketModal');
    };

    function updateSummary() {
        const selectedJobsCount = renderedTicketState.selectedJobs.size;
        const jobSummaryText = `${selectedJobsCount} job${selectedJobsCount === 1 ? '' : 's'}`;
        const envSummaryText = renderedTicketState.selectedGeneralEnvironments.size
            ? [...renderedTicketState.selectedGeneralEnvironments].join(', ')
            : 'no environments';

        summary.textContent = `${jobSummaryText} → ${envSummaryText}`;
    }

    renderParamInputList(generalParamsList, generalParametersConfig, renderedTicketState.generalParamValues, updateSummary);
    fillCheckboxList(
        envsList,
        generalEnvironmentsConfig.map((env) => env.name),
        renderedTicketState.selectedGeneralEnvironments,
        updateSummary
    );

    fillJobsCheckboxList(jobsList, renderedTicketState, updateSummary);

    updateSummary();

    return newCard;
}

export function fillCheckboxList(checkboxList, checkboxLabels, selectedValuesSet, onChange) {
    for (const checkboxLabel of checkboxLabels) {
        const newCheckboxRow = checkboxRowTemplate.content.firstElementChild.cloneNode(true);
        const newCheckboxInput = newCheckboxRow.querySelector('input[type="checkbox"]');
        const newCheckboxLabel = newCheckboxRow.querySelector('span');

        newCheckboxLabel.textContent = checkboxLabel;
        newCheckboxInput.onchange = () => {
            if (newCheckboxInput.checked) selectedValuesSet.add(checkboxLabel); else selectedValuesSet.delete(checkboxLabel);
            onChange();
        };

        checkboxList.appendChild(newCheckboxRow);
    }
}

export function fillJobsCheckboxList(jobsListContainer, ticketState, onChange) {
    for (const jobName of Object.keys(jobsConfig)) {
        const row = jobCheckboxRowTemplate.content.firstElementChild.cloneNode(true);
        const checkbox = row.querySelector('input[type="checkbox"]');
        const label = row.querySelector('.job-checkbox-label');
        const paramsBlock = row.querySelector('.job-params-block');

        label.textContent = jobName;
        checkbox.checked = ticketState.selectedJobs.has(jobName);
        paramsBlock.style.display = checkbox.checked ? '' : 'none';

        if (!(jobName in ticketState.jobParamValues)) ticketState.jobParamValues[jobName] = {};
        if (!(jobName in ticketState.jobEnvSelections)) ticketState.jobEnvSelections[jobName] = new Set();

        renderJobParamsBlock(paramsBlock, jobName, ticketState, onChange);

        checkbox.onchange = () => {
            if (checkbox.checked) ticketState.selectedJobs.add(jobName); else ticketState.selectedJobs.delete(jobName);
            paramsBlock.style.display = checkbox.checked ? '' : 'none';
            onChange();
        };

        jobsListContainer.appendChild(row);
    }
}

export function renderJobParamsBlock(paramsBlock, jobName, ticketState, onChange) {
    paramsBlock.innerHTML = '';

    const jobDef = jobsConfig[jobName];

    if (jobDef.parameters.length) {
        const paramsRow = document.createElement('div');
        paramsRow.className = 'field-row';
        const paramsLabel = document.createElement('label');
        paramsLabel.textContent = 'Parameters';
        const paramsContainer = document.createElement('div');
        renderParamInputList(paramsContainer, jobDef.parameters, ticketState.jobParamValues[jobName], onChange);
        paramsRow.appendChild(paramsLabel);
        paramsRow.appendChild(paramsContainer);
        paramsBlock.appendChild(paramsRow);
    }

    if (jobDef.environments.length) {
        const envsRow = document.createElement('div');
        envsRow.className = 'field-row';
        const envsLabel = document.createElement('label');
        envsLabel.textContent = 'Environments';
        const envsContainer = document.createElement('div');
        envsContainer.className = 'checkbox-list';
        fillCheckboxList(
            envsContainer,
            jobDef.environments.map((env) => env.name),
            ticketState.jobEnvSelections[jobName],
            onChange
        );
        envsRow.appendChild(envsLabel);
        envsRow.appendChild(envsContainer);
        paramsBlock.appendChild(envsRow);
    }
}
