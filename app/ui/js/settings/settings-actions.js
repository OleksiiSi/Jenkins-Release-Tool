import { collectSettingsFromForm } from './settings-collect.js';
import { showModal, hideModal } from '../tabs-modals.js';

export function onSaveClicked() {
    const { errors } = collectSettingsFromForm();

    if (errors.length) {
        alert('Fix the following before saving:\n' + errors.map((error) => `- ${error}`).join('\n'));
        return;
    }

    showModal('restartModal');
}

export async function confirmSaveAndRestart() {
    const { settings, errors } = collectSettingsFromForm();

    hideModal('restartModal');
    if (errors.length) {
        alert('Fix the following before saving:\n' + errors.map((error) => `- ${error}`).join('\n'));
        return;
    }

    await window.pywebview.api.save_settings(settings);
    await window.pywebview.api.restart_app();
}

export async function confirmReset() {
    hideModal('resetModal');

    await window.pywebview.api.reset_settings();
    await window.pywebview.api.restart_app();
}
