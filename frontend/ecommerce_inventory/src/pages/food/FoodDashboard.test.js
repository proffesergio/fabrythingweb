import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: async () => ({
    status: 200,
    data: {
      data: {
        orders: { today: 3, this_month: 12, total: 40 },
        revenue: { today: 500, this_month: 4200 },
        status_distribution: { PLACED: 2, DELIVERED: 30, CANCELLED: 8 },
        restaurants: { active: 5, pending: 2, total: 7 },
        revenue_trend: [{ date: '2026-07-18', total: 300 }, { date: '2026-07-19', total: 500 }],
        top_restaurants: [{ name: 'Star Kitchen', orders: 10, revenue: 1500 }],
        recent_orders: [{ id: 1, order_code: 'FD-XYZ', restaurant_name: 'Star Kitchen', total: '120.00', status: 'DELIVERED' }],
      },
    },
  }),
}));

import FoodDashboard from './FoodDashboard';

test('renders KPI values and a recent order', async () => {
  render(<MemoryRouter><FoodDashboard /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText('FD-XYZ')).toBeInTheDocument());
  expect(screen.getByText('40')).toBeInTheDocument(); // total orders KPI
  expect(screen.getAllByText('Star Kitchen').length).toBeGreaterThan(0);
});
