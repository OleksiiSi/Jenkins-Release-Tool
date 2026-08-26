// Mutable session state - as opposed to app-config.js, which is settings-
// derived config loaded once and not user-mutated during the session.
//
// Whole-variable reassignment (as opposed to in-place mutation, e.g.
// tickets.push(...)) must happen inside this module for other modules to see
// the update, since ES module bindings only let the defining module rebind
// an exported `let` - importers get a live read-only view.

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
