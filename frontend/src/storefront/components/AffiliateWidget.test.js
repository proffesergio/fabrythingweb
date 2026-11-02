import { render, screen, waitFor, act } from '@testing-library/react';

const mockCallApi = jest.fn();
jest.mock('../../hooks/APIHandler', () => () => ({ callApi: mockCallApi, loading: false, error: null }));

import AffiliateWidget from './AffiliateWidget';

function respond(data) {
    return Promise.resolve({ data: { data } });
}

const ITEM_A = {
    id: 1, program: 'rokomari', program_label: 'Rokomari', title: 'Perfume A', brand: 'Brand',
    image: '/api/media/a/', original_price: '590.00', current_price: '554.00',
    link_type: 'CART', go_url: '/api/store/partner-picks/1/r/', display_order: 0,
};
const ITEM_B = {
    ...ITEM_A, id: 2, title: 'Perfume B', go_url: '/api/store/partner-picks/2/r/',
};

function setVisibilityState(state) {
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => state });
}

function setReducedMotion(matches) {
    window.matchMedia = jest.fn().mockImplementation((query) => ({
        matches, media: query, addListener: jest.fn(), removeListener: jest.fn(),
    }));
}

async function advanceAndFlush(ms) {
    await act(async () => {
        jest.advanceTimersByTime(ms);
        await Promise.resolve();
        await Promise.resolve();
    });
}

beforeEach(() => {
    mockCallApi.mockReset();
    setVisibilityState('visible');
    setReducedMotion(false);
    jest.useFakeTimers();
});

afterEach(() => {
    jest.useRealTimers();
});

test('renders nothing while there are no items', async () => {
    mockCallApi.mockReturnValue(respond([]));
    const { container } = render(<AffiliateWidget placement="sidebar" />);
    await waitFor(() => expect(mockCallApi).toHaveBeenCalledWith({
        url: 'store/partner-picks/', params: { placement: 'sidebar' },
    }));
    expect(container).toBeEmptyDOMElement();
});

test('fetches by category instead of placement when category is passed', async () => {
    mockCallApi.mockReturnValue(respond([ITEM_A]));
    render(<AffiliateWidget category="beauty-health" />);
    await waitFor(() => expect(mockCallApi).toHaveBeenCalledWith({
        url: 'store/partner-picks/', params: { category: 'beauty-health' },
    }));
});

test('every item is badged as a partner link and opens in a new tab safely', async () => {
    // The card itself is the link now — there is no separate "Shop Now"
    // button, because only that button used to be clickable and tapping the
    // photo or the title (what people actually do) did nothing.
    mockCallApi.mockReturnValue(respond([ITEM_A]));
    render(<AffiliateWidget placement="sidebar" />);

    const link = await screen.findByRole('link');
    // Falls back to the tracked /r/ path when the fixture carries no
    // target_url; a real payload sends the shopper straight to the partner.
    expect(link).toHaveAttribute('href', '/api/store/partner-picks/1/r/');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link.getAttribute('rel')).toContain('noopener');
    // `sponsored` marks a paid/affiliate link so search engines do not read it
    // as an editorial endorsement.
    expect(link.getAttribute('rel')).toContain('sponsored');
    expect(screen.getByText(/via Rokomari/i)).toBeInTheDocument();
});

test('links straight at the partner when a target url is available', async () => {
    mockCallApi.mockReturnValue(respond([{ ...ITEM_A, target_url: 'https://rkmri.co/abc123/' }]));
    render(<AffiliateWidget placement="sidebar" />);

    const link = await screen.findByRole('link');
    expect(link).toHaveAttribute('href', 'https://rkmri.co/abc123/');
});

test('rotates to the next item on a timer', async () => {
    mockCallApi.mockReturnValue(respond([ITEM_A, ITEM_B]));
    render(<AffiliateWidget placement="sidebar" />);

    await screen.findByText('Perfume A');
    expect(screen.queryByText('Perfume B')).not.toBeInTheDocument();

    await advanceAndFlush(5000);
    expect(await screen.findByText('Perfume B')).toBeInTheDocument();
    expect(screen.queryByText('Perfume A')).not.toBeInTheDocument();
});

test('pauses rotation while the tab is hidden and resumes when visible again', async () => {
    mockCallApi.mockReturnValue(respond([ITEM_A, ITEM_B]));
    render(<AffiliateWidget placement="sidebar" />);
    await screen.findByText('Perfume A');

    setVisibilityState('hidden');
    await act(async () => { document.dispatchEvent(new Event('visibilitychange')); });

    // Rotation must not advance while hidden, even past the interval delay.
    await advanceAndFlush(10000);
    expect(screen.getByText('Perfume A')).toBeInTheDocument();

    setVisibilityState('visible');
    await act(async () => { document.dispatchEvent(new Event('visibilitychange')); });
    await advanceAndFlush(5000);
    expect(await screen.findByText('Perfume B')).toBeInTheDocument();
});

test('clears its interval on unmount (no post-unmount state updates)', async () => {
    mockCallApi.mockReturnValue(respond([ITEM_A, ITEM_B]));
    const { unmount } = render(<AffiliateWidget placement="sidebar" />);
    await screen.findByText('Perfume A');

    const clearSpy = jest.spyOn(window, 'clearInterval');
    unmount();
    expect(clearSpy).toHaveBeenCalled();
    clearSpy.mockRestore();
});

test('respects prefers-reduced-motion by never starting the rotation timer', async () => {
    setReducedMotion(true);
    mockCallApi.mockReturnValue(respond([ITEM_A, ITEM_B]));
    render(<AffiliateWidget placement="sidebar" />);

    // Both items render statically instead of one rotating item.
    await screen.findByText('Perfume A');
    expect(screen.getByText('Perfume B')).toBeInTheDocument();

    await advanceAndFlush(20000);
    // Still both present -- nothing "rotated away".
    expect(screen.getByText('Perfume A')).toBeInTheDocument();
    expect(screen.getByText('Perfume B')).toBeInTheDocument();
});
