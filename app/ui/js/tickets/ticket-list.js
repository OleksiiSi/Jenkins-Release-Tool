import { tickets, ticketPendingRemoval, removeTicket, setTicketPendingRemoval } from '../session-state.js';
import { renderTicketCard } from './ticket-card.js';
import { hideModal } from '../tabs-modals.js';

export function createTicketState() {
    return {
        ticketId: '',
        generalParamValues: {},
        selectedJobs: new Set(),
        jobParamValues: {},
        jobEnvSelections: {},
        selectedGeneralEnvironments: new Set(),
    };
}

export function addTicket() {
    const ticketState = createTicketState();
    tickets.push(ticketState);

    document.getElementById('ticketsList').appendChild(renderTicketCard(ticketState));

    updateTicketCount();
    renumberTicketPlaceholders();
}

// Keeps each card's ticket-ID placeholder ("Ticket 1", "Ticket 2", ...) in
// sync with its position, matching the fallback label core/validation.py
// uses for a ticket whose ID is left blank - a transparent hint, not a value.
export function renumberTicketPlaceholders() {
    const cards = document.getElementById('ticketsList').children;

    [...cards].forEach((card, index) => {
        card.querySelector('.ticket-id-input').placeholder = `Ticket ${index + 1}`;
    });
}

export function updateTicketCount() {
    const count = tickets.length;
    document.getElementById('ticketCount').textContent = `${count}`;
    document.getElementById('ticketsHeader').textContent = `Tickets (${count})`;
}

export function confirmRemoveTicket() {
    hideModal('removeTicketModal');
    if (!ticketPendingRemoval) return;

    const { ticketState, card } = ticketPendingRemoval;

    removeTicket(ticketState);
    card.remove();
    updateTicketCount();
    renumberTicketPlaceholders();

    setTicketPendingRemoval(null);
}
