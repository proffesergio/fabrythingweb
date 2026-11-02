import { render, screen, waitFor } from '@testing-library/react';

const mockCallApi = jest.fn();
jest.mock('../hooks/APIHandler', () => () => ({ callApi: mockCallApi, loading: false, error: null }));

import WhatsAppButton from './WhatsAppButton';

beforeEach(() => { mockCallApi.mockReset(); });

test('renders nothing when whatsapp_chat_number is empty (dormant default)', async () => {
    mockCallApi.mockResolvedValue({ data: { data: { whatsapp_chat_number: '' } } });
    const { container } = render(<WhatsAppButton />);

    await waitFor(() => expect(mockCallApi).toHaveBeenCalledWith({ url: 'store/config/' }));
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
});

test('renders nothing when the config response has no whatsapp_chat_number at all', async () => {
    mockCallApi.mockResolvedValue({ data: { data: {} } });
    const { container } = render(<WhatsAppButton />);

    await waitFor(() => expect(mockCallApi).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
});

test('renders an accessible link to wa.me with the correct number when configured', async () => {
    mockCallApi.mockResolvedValue({ data: { data: { whatsapp_chat_number: '8801842168117' } } });
    render(<WhatsAppButton />);

    const link = await screen.findByRole('link', { name: /chat with us on whatsapp/i });
    expect(link).toHaveAttribute('href', 'https://wa.me/8801842168117');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
});

test('appends a prefilled text param when prefilledMessage is given', async () => {
    mockCallApi.mockResolvedValue({ data: { data: { whatsapp_chat_number: '8801842168117' } } });
    render(<WhatsAppButton prefilledMessage="Hi, I have a question" />);

    const link = await screen.findByRole('link', { name: /chat with us on whatsapp/i });
    expect(link).toHaveAttribute('href', 'https://wa.me/8801842168117?text=Hi%2C%20I%20have%20a%20question');
});
