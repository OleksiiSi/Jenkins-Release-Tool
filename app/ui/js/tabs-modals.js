export function showTab(name) {
    const main = document.getElementById('mainView');
    const log = document.getElementById('logView');
    const settings = document.getElementById('settingsView');
    const logBtn = document.getElementById('logTabBtn');
    const settingsBtn = document.getElementById('settingsBtn');

    main.classList.add('hidden');

    log.classList.remove('active');
    logBtn.classList.remove('active');

    settings.classList.remove('active');
    settingsBtn.classList.remove('active');

    switch (name) {
        case 'log':
            log.classList.add('active');
            logBtn.classList.add('active');
            break;

        case 'settings':
            settings.classList.add('active');
            settingsBtn.classList.add('active');
            break;

        default:
            main.classList.remove('hidden');
            break;
    }
}

export function showModal(id) {
    document.activeElement.blur();
    document.getElementById(id).classList.add('show');
}

export function hideModal(id) {
    document.getElementById(id).classList.remove('show');
}
