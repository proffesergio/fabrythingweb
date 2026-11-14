import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import ManageCustomers from './ManageCustomers';

const mockCallApi = jest.fn();
beforeEach(() => mockCallApi.mockImplementation(async ({url}) => url.endsWith('/export/')
  ? {status: 200, data: 'id,username\n1,karim\n'}
  : ({
    status: 200,
    data: { data: { data: [
      { id: 1, username: 'karim', email: 'karim@x.com', phone: '017', order_count: 3, total_spent: 540, date_joined: '2026-01-01T00:00:00Z' },
    ], totalPages: 1 } },
  })));

jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn() }));
jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: (...args) => mockCallApi(...args),
}));

test('lists customers with order counts', async () => {
  render(<ManageCustomers />);
  expect(await screen.findByText('karim')).toBeInTheDocument();
  expect(screen.getByText('karim@x.com')).toBeInTheDocument();
  expect(screen.getByText('3')).toBeInTheDocument();
});

test('downloads all search matches without sending the visible page', async () => {
  const click = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  URL.createObjectURL = jest.fn(() => 'blob:customer-export');
  URL.revokeObjectURL = jest.fn();
  render(<ManageCustomers />);
  fireEvent.change(screen.getByPlaceholderText('Search by name, email, or phone'), {target: {value: 'karim'}});
  fireEvent.click(screen.getByRole('button', {name: 'Export CSV'}));
  await waitFor(() => expect(click).toHaveBeenCalled());
  expect(mockCallApi).toHaveBeenCalledWith(expect.objectContaining({url: 'store/admin/customers/export/', params: {file_type: 'csv', search: 'karim'}}));
  expect(URL.createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
  click.mockRestore();
});
