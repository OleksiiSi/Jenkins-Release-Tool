import { jobsConfig, generalEnvironmentsConfig } from './app-config.js';
import { tickets, setRunInProgressFlag, clearTickets } from './session-state.js';
import { updateTicketCount } from './tickets/ticket-list.js';

function buildJobRequest(jobName, ticketState) {
    const jobDef = jobsConfig[jobName];

    const parameters = { ...ticketState.generalParamValues, ...(ticketState.jobParamValues[jobName] || {}) };

    const environments = {};
    for (const envName of ticketState.selectedGeneralEnvironments) {
        const environmentDefinition = generalEnvironmentsConfig.find((env) => env.name === envName);
        if (environmentDefinition) environments[environmentDefinition.name] = environmentDefinition.promotion_process;
    }

    for (const envName of ticketState.jobEnvSelections[jobName] || []) {
        const environmentDefinition = jobDef.environments.find((env) => env.name === envName);
        if (environmentDefinition) environments[environmentDefinition.name] = environmentDefinition.promotion_process;
    }

    return { job_name: jobName, parameters, environments };
}

export async function runAll() {
    const ticketRequests = tickets.map((ticketState) => ({
        ticket_id: ticketState.ticketId,
        jobs: [...ticketState.selectedJobs].map((jobName) => buildJobRequest(jobName, ticketState)),
    }));

    const runResult = await window.pywebview.api.run_all(ticketRequests);

    const tokenBanner = document.getElementById('tokenErrorBanner');
    const errorBanner = document.getElementById('errorBanner');

    tokenBanner.classList.remove('show');
    errorBanner.classList.remove('show');

    if (runResult.token_missing) {
        tokenBanner.classList.add('show');
    }

    if (runResult.errors.length) {
        const errorList = document.getElementById('errorList');
        errorList.innerHTML = '';

        for (const error of runResult.errors) {
            const errorListItem = document.createElement('li');
            errorListItem.textContent = error;

            errorList.appendChild(errorListItem);
        }

        errorBanner.classList.add('show');
    }

    if (runResult.token_missing || runResult.errors.length) {
        return;
    }

    clearTickets();
    document.getElementById('ticketsList').innerHTML = '';
    updateTicketCount();

    setRunInProgress(true);
}

export function setRunInProgress(inProgress) {
    setRunInProgressFlag(inProgress);

    document.getElementById('runStatus').textContent = inProgress ? 'Running…' : 'Ready to run';
}
