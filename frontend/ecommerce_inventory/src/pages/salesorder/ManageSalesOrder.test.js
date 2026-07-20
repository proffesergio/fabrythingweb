import { render, screen, waitFor, fireEvent } from '@testing-library/react';

jest.mock('react-toastify', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

// Inline factory; a flag flips status to CONFIRMED after a PATCH.
jest.mock('../../hooks/APIHandler', () => {
  let confirmed = false;
  return () => ({
    loading: false,
    error: '',
    callApi: async ({ url, method }) => {
      if (method === 'PATCH') { confirmed = true; return { status: 200, data: { data: { id: 1, status: 'CONFIRMED' } } }; }
      if (url.includes('/orders/1/')) {
        return { status: 200, data: { data: {
          id: 1, order_number: 'ORD-ABC', status: confirmed ? 'CONFIRMED' : 'PENDING_VERIFICATION',
          status_display: confirmed ? 'Confirmed' : 'Pending Verification', total_amount: 320,
          contact_name: 'Karim', contact_phone: '017', shipping_address: { address: 'Village Rd', city: 'Rajshahi' },
          items: [{ id: 5, product_name: 'Cotton Shirt', quantity: 2, line_total: 320 }],
          status_logs: [{ from_status: '', to_status: 'PENDING_VERIFICATION', created_at: '2026-07-19T10:00:00Z' }],
          allowed_transitions: confirmed ? ['OUT_FOR_DELIVERY', 'CANCELED'] : ['CONFIRMED', 'CANCELED'],
        } } };
      }
      return { status: 200, data: { data: { data: [{
        id: 1, order_number: 'ORD-ABC', status: 'PENDING_VERIFICATION', status_display: 'Pending Verification',
        contact_name: 'Karim', item_count: 2, total_amount: 320, created_at: '2026-07-19T10:00:00Z',
      }], totalItems: 1 } } };
    },
  });
});

import ManageSalesOrder from './ManageSalesOrder';

test('lists COD orders, opens detail, advances status', async () => {
  render(<ManageSalesOrder />);
  await waitFor(() => expect(screen.getByText('ORD-ABC')).toBeInTheDocument());
  fireEvent.click(screen.getByRole('button', { name: /view/i }));
  await waitFor(() => expect(screen.getByText(/Cotton Shirt/)).toBeInTheDocument());
  fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
  await waitFor(() => expect(screen.getAllByText(/Confirmed/i).length).toBeGreaterThan(0));
});
