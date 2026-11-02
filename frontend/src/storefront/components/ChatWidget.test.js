import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';

async function advanceAndFlush(ms) {
    await act(async () => {
        jest.advanceTimersByTime(ms);
        // Let any microtasks queued by the timer callback (the mocked,
        // already-resolved callApi promise chain) settle before continuing.
        await Promise.resolve();
        await Promise.resolve();
    });
}

const mockCallApi = jest.fn();
jest.mock('../../hooks/APIHandler', () => () => ({ callApi: mockCallApi, loading: false, error: null }));

const mockIsAuthenticated = jest.fn(() => true);
jest.mock('../../utils/Helper', () => ({
    isAuthenticated: () => mockIsAuthenticated(),
}));

import ChatWidget from './ChatWidget';

const THREAD = { id: 1, kind: 'GENERAL', status: 'OPEN', unread_count: 0 };

function respond(data, status = 200) {
    return Promise.resolve({ status, data: { data } });
}

beforeEach(() => {
    mockCallApi.mockReset();
    mockIsAuthenticated.mockReturnValue(true);
    // jsdom has no scrollIntoView implementation.
    Element.prototype.scrollIntoView = jest.fn();
    jest.useFakeTimers();
});

afterEach(() => {
    jest.useRealTimers();
});

/**
 * Reproduces the owner's reported symptom end-to-end at the component level:
 * a customer has a thread open; a staff reply lands (simulated by the poll
 * response changing, exactly like a real GET .../messages/?after=<cursor>
 * poll would after an admin posts through the admin inbox); the widget's
 * OPEN_POLL_MS interval must pick it up and render it without the customer
 * touching anything.
 */
test('a staff reply that arrives on a background poll appears in the open thread', async () => {
    let afterCursorSeen = [];
    let pollCount = 0;

    mockCallApi.mockImplementation(({ url, method }) => {
        if (url === 'chat/threads/updates/') return respond({ total_unread: 0 });
        if (url === 'chat/threads/' && (method === undefined || method === 'GET')) {
            return respond([THREAD]);
        }
        if (url === `chat/threads/${THREAD.id}/read/`) return respond({ unread_count: 0 });

        if (url.startsWith(`chat/threads/${THREAD.id}/messages/`)) {
            if (url === `chat/threads/${THREAD.id}/messages/`) {
                // initial load, no cursor
                return respond({
                    messages: [
                        { id: 10, thread_id: 1, sender_id: 5, sender_role: 'CUSTOMER', sender_name: 'cust1', body: 'hello', created_at: '2026-07-27T10:00:00Z' },
                    ],
                    latest_id: 10,
                });
            }
            const match = url.match(/after=(.+)$/);
            const after = match ? match[1] : null;
            afterCursorSeen.push(after);

            if (after === 'null' || after === 'undefined') {
                throw new Error(`poll sent a literal "${after}" cursor -- cursor was clobbered`);
            }

            pollCount += 1;
            if (pollCount === 1) {
                // First poll after the initial load: nothing new yet -- mirrors the
                // real backend, which reports latest_id: null on an empty result.
                return respond({ messages: [], latest_id: null });
            }
            // Second poll, still using the same (correctly preserved) cursor:
            // the staff reply has now landed.
            return respond({
                messages: [
                    { id: 11, thread_id: 1, sender_id: 9, sender_role: 'STAFF', sender_name: 'admin1', body: "we're on it", created_at: '2026-07-27T10:00:05Z' },
                ],
                latest_id: 11,
            });
        }
        return respond({});
    });

    render(<ChatWidget />);

    fireEvent.click(screen.getByRole('button', { name: /chat with us/i }));

    // Open the one existing thread. "General question" also appears as the
    // composer's selected Kind value, so find the actual clickable list row
    // by its "Open" status text, which only the conversation list renders.
    await screen.findByText('Open');
    const threadButton = screen.getAllByRole('button').find((btn) => btn.textContent.includes('Open'));
    expect(threadButton).toBeTruthy();
    fireEvent.click(threadButton);

    await screen.findByText('hello');

    // Advance past the first poll tick (no new messages -- cursor must survive).
    await advanceAndFlush(4000);
    // Advance past the second poll tick -- the staff reply should now be there.
    await advanceAndFlush(4000);

    await waitFor(() => expect(screen.getByText("we're on it")).toBeInTheDocument());

    // The cursor sent on every poll after the initial load must always be the
    // last known-good id (10, then 10 again since nothing new arrived, never
    // a literal "null"/"undefined").
    expect(afterCursorSeen).toEqual(['10', '10']);
});

/**
 * Pins the unread badge lifecycle wired to the existing
 * `customer_unread_count` / `chat/threads/updates/` badge endpoint: it must
 * appear on the closed launcher once staff has replied, and clear as soon as
 * the customer opens that conversation (which POSTs .../read/).
 */
test('unread badge appears after a staff reply and clears once the thread is opened', async () => {
    let badgeUnread = 0;
    const unreadThread = { ...THREAD, unread_count: 0 };

    mockCallApi.mockImplementation(({ url, method }) => {
        if (url === 'chat/threads/updates/') return respond({ total_unread: badgeUnread });
        if (url === 'chat/threads/' && (method === undefined || method === 'GET')) {
            return respond([unreadThread]);
        }
        if (url === `chat/threads/${THREAD.id}/read/`) {
            badgeUnread = 0;
            unreadThread.unread_count = 0;
            return respond({ unread_count: 0 });
        }
        if (url.startsWith(`chat/threads/${THREAD.id}/messages/`)) {
            return respond({ messages: [], latest_id: null });
        }
        return respond({});
    });

    render(<ChatWidget />);

    // Nothing unread yet: no badge content rendered on the launcher.
    await advanceAndFlush(0);
    expect(screen.queryByText('3')).not.toBeInTheDocument();

    // Simulate a staff reply landing while the panel is closed: the next
    // idle badge poll reports a nonzero total_unread.
    badgeUnread = 3;
    unreadThread.unread_count = 3;
    await advanceAndFlush(45000);
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument());

    // Opening the launcher and the conversation marks it read; the badge
    // clears via the same refreshBadge() call the read POST triggers.
    fireEvent.click(screen.getByRole('button', { name: /chat with us/i }));
    await screen.findByText('Open');
    const threadButton = screen.getAllByRole('button').find((btn) => btn.textContent.includes('Open'));
    fireEvent.click(threadButton);

    // Let the read POST -> refreshBadge promise chain settle (two async
    // hops deep). MUI's Badge keeps the last badgeContent node around under
    // an "invisible" class for its exit transition rather than unmounting it
    // immediately, so the real assertion is "hidden", not "gone from the DOM".
    await advanceAndFlush(0);
    await advanceAndFlush(0);
    expect(screen.getByText('3')).toHaveClass('MuiBadge-invisible');
});
