export async function saveToken() {
    const input = document.getElementById('tokenInput');

    if (!input.value) { alert('Enter a token before saving'); return; }

    const status = await window.pywebview.api.save_token(input.value);
    updateTokenStatusUI(status.saved);
}

export function changeToken() {
    const tokenInput = document.getElementById('tokenInput');

    tokenInput.disabled = false;
    tokenInput.value = '';
    tokenInput.placeholder = 'Paste new Jenkins API token';
    tokenInput.focus();

    document.getElementById('saveTokenBtn').style.display = '';
    document.getElementById('changeTokenBtn').style.display = 'none';
}

export function updateTokenStatusUI(saved) {
    const tokenStatusIndicatorElement = document.getElementById('tokenStatus');
    const tokenInput = document.getElementById('tokenInput');

    tokenStatusIndicatorElement.textContent = saved ? '● saved in keyring' : '● not saved';
    tokenStatusIndicatorElement.style.color = saved ? 'var(--ok)' : 'var(--warn)';

    tokenInput.disabled = saved;
    tokenInput.value = saved ? '••••••••••••••••' : '';
    tokenInput.placeholder = saved ? '' : 'Paste Jenkins API token';

    document.getElementById('saveTokenBtn').style.display = saved ? 'none' : '';
    document.getElementById('changeTokenBtn').style.display = saved ? '' : 'none';
}
