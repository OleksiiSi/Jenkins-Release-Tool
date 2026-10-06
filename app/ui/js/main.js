import {setAppConfig} from './app-config.js';
import {updateTicketCount, addTicket, confirmRemoveTicket} from './tickets/ticket-list.js';
import {
    renderSettingsForm,
    addGeneralParamRow,
    addGeneralEnvRow,
    addJobConfigCard
} from './settings/settings-render.js';
import {onSaveClicked, confirmSaveAndRestart, confirmReset} from './settings/settings-actions.js';
import {updateTokenStatusUI, saveToken, changeToken} from './token.js';
import {setRunInProgress, runAll} from './run.js';
import {refreshConnectionChips} from './connection.js';
import {pollTick, clearLog} from './log.js';
import {showTab, showModal, hideModal} from './tabs-modals.js';

window.addEventListener('pywebviewready', init);

async function init() {
    const settings = await window.pywebview.api.get_settings();

    setAppConfig(settings);
    renderSettingsForm(settings);

    const tokenStatus = await window.pywebview.api.get_token_status();
    updateTokenStatusUI(tokenStatus.saved);

    const finished = await window.pywebview.api.is_runner_finished();
    setRunInProgress(!finished);

    refreshConnectionChips().catch(console.error);
    updateTicketCount();

    wireStaticControls();

    pollTick().catch(console.error);
    setInterval(() => pollTick().catch(console.error), 2000);
    setInterval(() => refreshConnectionChips().catch(console.error), 30000);
}

function wireStaticControls() {
    document.getElementById('logTabBtn').addEventListener('click', () => showTab('log'));
    document.getElementById('settingsBtn').addEventListener('click', () => showTab('settings'));
    document.getElementById('exitBtn').addEventListener('click', () => showModal('exitModal'));
    document.getElementById('addTicketBtn').addEventListener('click', addTicket);
    document.getElementById('tokenErrorBannerLink').addEventListener('click', (event) => { event.preventDefault(); showTab('settings');} );
    document.getElementById('runBtn').addEventListener('click', runAll);
    document.getElementById('logClearBtn').addEventListener('click', clearLog);
    document.getElementById('saveTokenBtn').addEventListener('click', saveToken);
    document.getElementById('changeTokenBtn').addEventListener('click', changeToken);
    document.getElementById('addGeneralParamBtn').addEventListener('click', () => addGeneralParamRow());
    document.getElementById('addGeneralEnvBtn').addEventListener('click', () => addGeneralEnvRow());
    document.getElementById('addJobConfigBtn').addEventListener('click', () => addJobConfigCard());
    document.getElementById('resetSettingsBtn').addEventListener('click', () => showModal('resetModal'));
    document.getElementById('saveSettingsBtn').addEventListener('click', onSaveClicked);

    document.querySelectorAll('.back-btn').forEach((button) => {
        button.addEventListener('click', () => showTab('main'));
    });

    document.querySelectorAll('.modal-btn-cancel').forEach((button) => {
        button.addEventListener('click', () => hideModal(button.closest('.modal-overlay').id));
    });

    const modalConfirmHandlers = {
        restartModal: confirmSaveAndRestart,
        removeTicketModal: confirmRemoveTicket,
        exitModal: confirmExitApp,
        resetModal: confirmReset,
    };
    document.querySelectorAll('.modal-btn-confirm').forEach((button) => {
        const modalId = button.closest('.modal-overlay').id;
        button.addEventListener('click', modalConfirmHandlers[modalId]);
    });
}

async function confirmExitApp() {
    hideModal('exitModal');
    await window.pywebview.api.exit_app();
}
