import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

const mockCallApi = jest.fn();
jest.mock('../../hooks/APIHandler', () => () => ({ callApi: mockCallApi, loading: false, error: null }));

import DealsPage from './DealsPage';

const ITEM = {
    id: 1, program: 'rokomari', program_label: 'Rokomari', title: 'Perfume A', brand: 'Brand',
    image: '/api/media/a/', original_price: '590.00', current_price: '554.00',
    link_type: 'CART', go_url: '/api/store/partner-picks/1/r/', display_order: 0,
};

const renderPage = () => render(<MemoryRouter><DealsPage /></MemoryRouter>);

beforeEach(() => { mockCallApi.mockReset(); });

test('fetches the deals placement and renders each item through the shared product card, badged and new-tab', async () => {
    mockCallApi.mockResolvedValue({ data: { data: [ITEM] } });
    renderPage();

    await waitFor(() => expect(mockCallApi).toHaveBeenCalledWith({
        url: 'store/partner-picks/', params: { placement: 'deals' },
    }));
    expect(await screen.findByText('Perfume A')).toBeInTheDocument();
    expect(screen.getByText(/via rokomari/i)).toBeInTheDocument();

    // The whole card is the click-tracking redirect link (same ProductCard
    // real products use, via its `affiliate` prop) -- not a separate "Shop
    // Now" button, and it must open in a new tab per the owner's honest-
    // labelling requirement.
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', ITEM.go_url);
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
});

test('shows the discounted price struck through against the original', async () => {
    mockCallApi.mockResolvedValue({ data: { data: [ITEM] } });
    renderPage();
    expect(await screen.findByText('৳554')).toBeInTheDocument();
    expect(screen.getByText('৳590')).toBeInTheDocument();
});

test('shows an empty state when there are no deals', async () => {
    mockCallApi.mockResolvedValue({ data: { data: [] } });
    renderPage();
    expect(await screen.findByText(/no deals right now/i)).toBeInTheDocument();
});
