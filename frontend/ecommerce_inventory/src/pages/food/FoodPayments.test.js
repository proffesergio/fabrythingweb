import { render, screen, waitFor, fireEvent } from '@testing-library/react';

const calls = [];

jest.mock('react-toastify', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const ROW = {
  id: 7, order_id: 70, order_code: 'FD-7', order_total: '570.00', payment_method: 'COD',
  restaurant_name: 'Kacchi Ghor', customer_name: 'A', customer_phone: '017',
  delivered_at: '2026-07-20T10:00:00Z', rider: 1, rider_name: 'Karim',
  commission_rate: '15.00', food_net: '500.00', delivery_fee: '50.00', tip: '20.00',
  commission_amount: '75.00', restaurant_payout: '425.00', rider_base_pay: '40.00',
  rider_payout: '60.00', platform_revenue: '85.00',
  customer_payment_status: 'PENDING', rider_cash_status: 'PENDING',
  rider_payout_status: 'PENDING', restaurant_payout_status: 'PENDING',
  customer_payment_at: null, rider_cash_at: null,
  rider_payout_at: null, restaurant_payout_at: null,
  is_fully_settled: false, notes: '',
};

jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: async (opts) => {
    calls.push(opts);
    if (opts.url.includes('summary')) {
      return { status: 200, data: { data: {
        orders: 1, gross: '500.00', platform_revenue: '85.00', commission: '75.00',
        outstanding: { customer_payment: '570.00', rider_cash: '570.00',
                       rider_payout: '60.00', restaurant_payout: '425.00' },
        counts: { customer_payment: 1, rider_cash: 1, rider_payout: 1, restaurant_payout: 1 },
      } } };
    }
    if (opts.method === 'POST') return { status: 200, data: { data: { ...ROW, rider_payout_status: 'SETTLED' } } };
    // Paginated envelope: {data:{data:[...], totalPages}}.
    return { status: 200, data: { data: { data: [ROW], totalPages: 1 } } };
  },
}));

import FoodPayments from './FoodPayments';

beforeEach(() => { calls.length = 0; });

test('shows what is owed to each party', async () => {
  render(<FoodPayments />);
  await waitFor(() => expect(screen.getByText('FD-7')).toBeInTheDocument());
  expect(screen.getByText('Owed to riders')).toBeInTheDocument();
  expect(screen.getByText('৳60.00')).toBeInTheDocument();
  expect(screen.getByText('Owed to restaurants')).toBeInTheDocument();
  expect(screen.getByText('৳425.00')).toBeInTheDocument();
});

test('names who delivered the order', async () => {
  render(<FoodPayments />);
  await waitFor(() => expect(screen.getByText('Karim')).toBeInTheDocument());
});

test('expanding a row breaks the order total into its splits', async () => {
  render(<FoodPayments />);
  await waitFor(() => expect(screen.getByText('FD-7')).toBeInTheDocument());
  fireEvent.click(screen.getAllByRole('button')[screen.getAllByRole('button').findIndex(() => false) + 0]
    || screen.getAllByRole('button')[0]);
  await waitFor(() => expect(screen.getByText('What the customer paid')).toBeInTheDocument());
  expect(screen.getByText('Who gets what')).toBeInTheDocument();
  expect(screen.getByText(/after 15.00% commission/)).toBeInTheDocument();
});

test('marking a leg paid posts the leg name', async () => {
  render(<FoodPayments />);
  await waitFor(() => expect(screen.getByText('FD-7')).toBeInTheDocument());
  // The four status chips are clickable shortcuts for settling each leg.
  fireEvent.click(screen.getAllByText('Pending')[2]);
  await waitFor(() => {
    const post = calls.find((c) => c.method === 'POST');
    expect(post).toBeTruthy();
    expect(post.url).toContain('/settlements/7/leg/');
    expect(post.body.leg).toBe('rider_payout');
    expect(post.body.settled).toBe(true);
  });
});
