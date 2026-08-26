export async function refreshConnectionChips() {
    const status = await window.pywebview.api.get_connection_status();

    setStatusChip('jenkinsChip', status.jenkins);
    setStatusChip('teamsChip', status.teams);
}

function setStatusChip(chipId, isStatusOk) {
    const statusChipElement = document.getElementById(chipId);

    statusChipElement.classList.remove('ok', 'fail');
    statusChipElement.classList.add(isStatusOk ? 'ok' : 'fail');
}
