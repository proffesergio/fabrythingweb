import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: async () => ({
    status: 200,
    data: {
      data: {
        order_code: 'FD-ABC123', status: 'PREPARING', restaurant_name: 'R1', total: '150.00',
        eta_minutes: 45, items: [{ id: 1, item_name: 'Biriyani', quantity: 1, line_total: '120.00', selected_options: [] }],
      },
    },
  }),
}));

import FoodOrderTrack from './FoodOrderTrack';

test('renders order code and current status', async () => {
  render(
    <MemoryRouter initialEntries={['/food/order/FD-ABC123']}>
      <Routes><Route path="/food/order/:code" element={<FoodOrderTrack />} /></Routes>
    </MemoryRouter>
  );
  await waitFor(() => expect(screen.getByText(/FD-ABC123/)).toBeInTheDocument());
  expect(screen.getByText(/preparing/i)).toBeInTheDocument();
});
