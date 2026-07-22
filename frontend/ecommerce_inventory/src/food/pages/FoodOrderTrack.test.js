import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

// Leaflet needs DOM APIs jsdom doesn't implement; LiveTrackMap guards itself with
// try/catch, so stub it here to keep these tests about what the customer is told.
jest.mock('../components/LiveTrackMap', () => () => <div data-testid="live-map" />);

const BASE = {
  order_code: 'FD-ABC123', status: 'PREPARING', restaurant_name: 'R1', total: '150.00',
  eta_minutes: 45, items: [{ id: 1, item_name: 'Biriyani', quantity: 1, line_total: '120.00', selected_options: [] }],
};

let mockOrder = BASE;

jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: async () => ({ status: 200, data: { data: mockOrder } }),
}));

import FoodOrderTrack from './FoodOrderTrack';

beforeEach(() => { mockOrder = BASE; });

const renderTrack = () => render(
  <MemoryRouter initialEntries={['/food/order/FD-ABC123']}>
    <Routes><Route path="/food/order/:code" element={<FoodOrderTrack />} /></Routes>
  </MemoryRouter>
);

test('renders order code and current status', async () => {
  renderTrack();
  await waitFor(() => expect(screen.getByText(/FD-ABC123/)).toBeInTheDocument());
  expect(screen.getByText(/preparing/i)).toBeInTheDocument();
});

test('no rider card before one is assigned', async () => {
  renderTrack();
  await waitFor(() => expect(screen.getByText(/FD-ABC123/)).toBeInTheDocument());
  expect(screen.queryByRole('link', { name: /call/i })).not.toBeInTheDocument();
});

test('shows rider name and a tap-to-call link once assigned', async () => {
  mockOrder = { ...BASE, rider_name: 'Karim', rider_phone: '01712345678' };
  renderTrack();
  await waitFor(() => expect(screen.getByText('Karim')).toBeInTheDocument());
  expect(screen.getByRole('link', { name: /call/i })).toHaveAttribute('href', 'tel:01712345678');
  // Still only PREPARING — the live map belongs to OUT_FOR_DELIVERY.
  expect(screen.queryByTestId('live-map')).not.toBeInTheDocument();
});

test('shows the live map once out for delivery', async () => {
  mockOrder = {
    ...BASE, status: 'OUT_FOR_DELIVERY', rider_name: 'Karim', rider_phone: '01712345678',
    rider_lat: '23.77', rider_lng: '90.78', delivery_lat: '23.78', delivery_lng: '90.79',
    rider_last_seen_at: new Date().toISOString(),
  };
  renderTrack();
  await waitFor(() => expect(screen.getByTestId('live-map')).toBeInTheDocument());
  // The rider card's own heading — /on the way/ alone also matches the progress
  // track's "On the way" step label.
  expect(screen.getByText(/your rider is on the way/i)).toBeInTheDocument();
});

test('says so when the rider pin is stale rather than presenting it as current', async () => {
  mockOrder = {
    ...BASE, status: 'OUT_FOR_DELIVERY', rider_name: 'Karim', rider_phone: '01712345678',
    rider_lat: '23.77', rider_lng: '90.78',
    rider_last_seen_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
  };
  renderTrack();
  await waitFor(() => expect(screen.getByText(/last known position/i)).toBeInTheDocument());
});

test('handles an assigned rider whose location is unavailable', async () => {
  mockOrder = { ...BASE, status: 'OUT_FOR_DELIVERY', rider_name: 'Karim', rider_phone: '01712345678' };
  renderTrack();
  await waitFor(() => expect(screen.getByText('Karim')).toBeInTheDocument());
  expect(screen.queryByTestId('live-map')).not.toBeInTheDocument();
  expect(screen.getByText(/live location isn/i)).toBeInTheDocument();
});
