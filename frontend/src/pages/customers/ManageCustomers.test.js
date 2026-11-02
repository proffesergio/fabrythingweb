import { render, screen, waitFor } from '@testing-library/react';

jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn() }));
jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: async () => ({
    status: 200,
    data: { data: { data: [
      { id: 1, username: 'karim', email: 'karim@x.com', phone: '017', order_count: 3, total_spent: 540, date_joined: '2026-01-01T00:00:00Z' },
    ], totalPages: 1 } },
  }),
}));

import ManageCustomers from './ManageCustomers';

test('lists customers with order counts', async () => {
  render(<ManageCustomers />);
  await waitFor(() => expect(screen.getByText('karim')).toBeInTheDocument());
  expect(screen.getByText('karim@x.com')).toBeInTheDocument();
  expect(screen.getByText('3')).toBeInTheDocument();
});
