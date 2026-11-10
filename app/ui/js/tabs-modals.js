const TAB_VIEWS = {
    log: { viewId: 'logView', buttonId: 'logTabBtn' },
    settings: { viewId: 'settingsView', buttonId: 'settingsBtn' },
    help: { viewId: 'helpView', buttonId: 'helpBtn' },
};

export function showTab(name) {
    document.getElementById('mainView').classList.toggle('hidden', name in TAB_VIEWS);

    for (const [tabName, { viewId, buttonId }] of Object.entries(TAB_VIEWS)) {
        document.getElementById(viewId).classList.toggle('active', tabName === name);
        document.getElementById(buttonId).classList.toggle('active', tabName === name);
    }
}

export function showModal(id) {
    document.activeElement.blur();
    document.getElementById(id).classList.add('show');
}

export function hideModal(id) {
    document.getElementById(id).classList.remove('show');
}
