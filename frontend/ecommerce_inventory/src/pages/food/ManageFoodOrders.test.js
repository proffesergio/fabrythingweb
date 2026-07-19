import { render, screen, waitFor, fireEvent } from '@testing-library/react';

// Inline factory; a closure flag flips the order to CONFIRMED after a PATCH.
jest.mock('../../hooks/APIHandler', () => {
  let confirmed = false;
  return () => ({
    loading: false,
    error: '',
    callApi: async ({ url, method }) => {
      if (method === 'PATCH') { confirmed = true; return { status: 200, data: { data: { id: 1, status: 'CONFIRMED' } } }; }
      if (url.includes('/orders/1/')) {
        return { status: 200, data: { data: { id: 1, order_code: 'FD-1', status: confirmed ? 'CONFIRMED' : 'PLACED', restaurant_name: 'R1', guest_name: 'A', guest_phone: '017', delivery_address: 'addr', total: '150.00', items: [{ id: 9, item_name: 'Biriyani', quantity: 1, line_total: '120.00', selected_options: [] }], allowed_transitions: confirmed ? ['PREPARING', 'CANCELLED'] : ['CONFIRMED', 'CANCELLED'] } } };
      }
      return { status: 200, data: { data: [{ id: 1, order_code: 'FD-1', status: confirmed ? 'CONFIRMED' : 'PLACED', restaurant_name: 'R1', guest_name: 'A', total: '150.00', created_at: '2026-07-19T10:00:00Z' }] } };
    },
  });
});

import ManageFoodOrders from './ManageFoodOrders';

test('lists orders, opens detail, advances status', async () => {
  render(<ManageFoodOrders />);
  await waitFor(() => expect(screen.getByText('FD-1')).toBeInTheDocument());
  fireEvent.click(screen.getByText('FD-1'));
  await waitFor(() => expect(screen.getByText(/Biriyani/)).toBeInTheDocument());
  fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
  await waitFor(() => expect(screen.getAllByText('CONFIRMED').length).toBeGreaterThan(0));
});
