import { render, screen, waitFor, fireEvent } from '@testing-library/react';

// Inline factory (the reliable jest.mock shape here). A closure flag flips the
// order's status to CONFIRMED after a PATCH so the UI update is observable.
jest.mock('../hooks/APIHandler', () => {
  let confirmed = false;
  return () => ({
    loading: false,
    error: '',
    callApi: async ({ method }) => {
      if (method === 'PATCH') {
        confirmed = true;
        return { status: 200, data: { data: { id: 1, status: 'CONFIRMED' } } };
      }
      return {
        status: 200,
        data: { data: [{ id: 1, order_code: 'FD-1', status: confirmed ? 'CONFIRMED' : 'PLACED', guest_name: 'A', total: '150.00', items: [] }] },
      };
    },
  });
});

import VendorOrders from './VendorOrders';

test('lists vendor orders and advances status', async () => {
  render(<VendorOrders />);
  await waitFor(() => expect(screen.getByText('FD-1')).toBeInTheDocument());
  expect(screen.getByText('PLACED')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
  await waitFor(() => expect(screen.getByText('CONFIRMED')).toBeInTheDocument());
});
