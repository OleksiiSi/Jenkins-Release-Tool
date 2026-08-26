import { runInProgress } from './session-state.js';
import { setRunInProgress } from './run.js';

export async function pollTick() {
    const logs = await window.pywebview.api.get_new_logs();

    if (logs.length) appendLogs(logs);

    if (runInProgress) {
        const isRunFinished = await window.pywebview.api.is_runner_finished();
        if (isRunFinished) setRunInProgress(false);
    }
}

function appendLogs(entries) {
    const logBox = document.getElementById('logBox');
    const atBottom = logBox.scrollHeight - logBox.scrollTop - logBox.clientHeight < 4;

    for (const entry of entries) {
        const entryLine = document.createElement('div');
        entryLine.className = 'log-line';

        const entryTimestamp = document.createElement('span');
        entryTimestamp.className = 'ts';
        entryTimestamp.textContent = `[${entry.timestamp}]`;

        const entryMessage = document.createElement('span');
        entryMessage.className = entry.level + '-line';
        entryMessage.textContent = ' ' + entry.message;

        entryLine.append(entryTimestamp, entryMessage);
        logBox.appendChild(entryLine);
    }

    if (atBottom) logBox.scrollTop = logBox.scrollHeight;
}

export function clearLog() {
    document.getElementById('logBox').innerHTML = '';
}
