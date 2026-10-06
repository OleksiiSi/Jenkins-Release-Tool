export let tickets = [];
export let runInProgress = false;
export let ticketPendingRemoval = null;

export function removeTicket(ticketState) {
    tickets = tickets.filter((ticket) => ticket !== ticketState);
}

export function clearTickets() {
    tickets = [];
}

export function setRunInProgressFlag(value) {
    runInProgress = value;
}

export function setTicketPendingRemoval(value) {
    ticketPendingRemoval = value;
}
