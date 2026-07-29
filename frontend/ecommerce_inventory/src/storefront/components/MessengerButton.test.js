import { render, screen, waitFor } from '@testing-library/react';

const mockCallApi = jest.fn();
jest.mock('../../hooks/APIHandler', () => () => ({ callApi: mockCallApi, loading: false, error: null }));

import MessengerButton from './MessengerButton';

beforeEach(() => { mockCallApi.mockReset(); });

test('renders nothing when messenger_page_id is empty (dormant default)', async () => {
    mockCallApi.mockResolvedValue({ data: { data: { messenger_page_id: '' } } });
    const { container } = render(<MessengerButton />);

    // Let the config fetch resolve, then assert nothing rendered.
    await waitFor(() => expect(mockCallApi).toHaveBeenCalledWith({ url: 'store/config/' }));
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
});

test('renders nothing when the config response has no messenger_page_id at all', async () => {
    mockCallApi.mockResolvedValue({ data: { data: {} } });
    const { container } = render(<MessengerButton />);

    await waitFor(() => expect(mockCallApi).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
});

test('renders an accessible link to m.me with the ref param when configured', async () => {
    mockCallApi.mockResolvedValue({ data: { data: { messenger_page_id: 'fabrything' } } });
    render(<MessengerButton />);

    const link = await screen.findByRole('link', { name: /message us on facebook messenger/i });
    expect(link).toHaveAttribute('href', 'https://m.me/fabrything?ref=website_floating_button');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
});

test('works with a numeric Page ID the same way as a username', async () => {
    mockCallApi.mockResolvedValue({ data: { data: { messenger_page_id: '109876543210123' } } });
    render(<MessengerButton />);

    const link = await screen.findByRole('link', { name: /message us on facebook messenger/i });
    expect(link).toHaveAttribute('href', 'https://m.me/109876543210123?ref=website_floating_button');
});
