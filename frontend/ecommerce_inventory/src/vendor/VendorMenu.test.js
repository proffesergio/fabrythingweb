import { render, screen } from '@testing-library/react';
import VendorMenu from './VendorMenu';

jest.mock('../hooks/APIHandler', () => () => ({
    callApi: jest.fn().mockResolvedValue({ data: { data: [] } }),
    loading: false,
}));

test('renders Add Category control with an empty category list', async () => {
    render(<VendorMenu />);
    expect(await screen.findByRole('button', { name: /Add Category/i })).toBeInTheDocument();
    expect(screen.getByText(/No categories yet/i)).toBeInTheDocument();
});
