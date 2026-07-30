import { render, screen, waitFor } from '@testing-library/react';

const mockCallApi = jest.fn();
jest.mock('../../hooks/APIHandler', () => () => ({ callApi: mockCallApi, loading: false, error: null }));

import DealsPage from './DealsPage';

const ITEM = {
    id: 1, program: 'rokomari', program_label: 'Rokomari', title: 'Perfume A', brand: 'Brand',
    image: '/api/media/a/', original_price: '590.00', current_price: '554.00',
    link_type: 'CART', go_url: '/api/store/affiliate/1/go/', display_order: 0,
};

beforeEach(() => { mockCallApi.mockReset(); });

test('fetches the deals placement and renders each item as a partner-badged link', async () => {
    mockCallApi.mockResolvedValue({ data: { data: [ITEM] } });
    render(<DealsPage />);

    await waitFor(() => expect(mockCallApi).toHaveBeenCalledWith({
        url: 'store/affiliate/', params: { placement: 'deals' },
    }));
    expect(await screen.findByText('Perfume A')).toBeInTheDocument();
    const link = screen.getByRole('link', { name: /shop now/i });
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
});

test('shows an empty state when there are no deals', async () => {
    mockCallApi.mockResolvedValue({ data: { data: [] } });
    render(<DealsPage />);
    expect(await screen.findByText(/no deals right now/i)).toBeInTheDocument();
});
