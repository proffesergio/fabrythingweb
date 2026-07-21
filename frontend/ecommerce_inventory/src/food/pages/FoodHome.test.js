import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

const mockCalls = [];

const NEAR = {
  id: 1, slug: 'r1', display_name: 'Tasty', cover_image: '', cuisine_type: 'Bengali',
  avg_prep_minutes: 25, base_delivery_fee: '30.00', is_open: true, distance_km: 0.8,
};
const POPULAR = {
  id: 2, slug: 'r2', display_name: 'Crowd Favourite', cover_image: '', cuisine_type: 'Biryani',
  avg_prep_minutes: 30, base_delivery_fee: '40.00', is_open: true, distance_km: 4.2,
};

jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: async ({ url, params }) => {
    mockCalls.push({ url, params });
    if (!String(url).startsWith('food/restaurants')) return { data: { data: [] } };
    // Mirror the backend: `sort=popular` returns the popular row, honouring
    // `exclude` so a restaurant never appears in both rows.
    if (params?.sort === 'popular') {
      const excluded = String(params.exclude || '').split(',');
      return { data: { data: { data: [NEAR, POPULAR].filter((r) => !excluded.includes(String(r.id))) } } };
    }
    return { data: { data: { data: [NEAR] } } };
  },
}));

jest.mock('../context/FoodLocationContext', () => ({
  useFoodLocation: () => ({
    zoneId: '1',
    zones: [{ id: 1, name: 'Zone 1' }],
    currentZone: { id: 1, name: 'Zone 1', center_lat: '23.75', center_lng: '90.78' },
    lang: 'en',
    coords: { lat: 23.75, lng: 90.78 },
    detectLocation: jest.fn(),
  }),
}));

import FoodHome from './FoodHome';

beforeEach(() => { mockCalls.length = 0; });

const renderHome = () => render(<MemoryRouter><FoodHome /></MemoryRouter>);

test('renders both discovery rows', async () => {
  renderHome();
  await waitFor(() => expect(screen.getByText('Nearest to your area')).toBeInTheDocument());
  expect(screen.getByText('Restaurants you may also like')).toBeInTheDocument();
});

test('shows the nearest restaurant in the first row', async () => {
  renderHome();
  await waitFor(() => expect(screen.getByText('Tasty')).toBeInTheDocument());
});

test('asks the API to sort the first row by distance from the pin', async () => {
  renderHome();
  await waitFor(() => expect(mockCalls.length).toBeGreaterThan(0));
  expect(mockCalls[0].params).toMatchObject({ sort: 'distance', lat: 23.75, lng: 90.78 });
});

test('does not repeat a restaurant across the two rows', async () => {
  renderHome();
  await waitFor(() => expect(screen.getByText('Crowd Favourite')).toBeInTheDocument());
  // "Tasty" is in the nearest row, so the suggestions request must exclude it
  // and it must appear exactly once on the page.
  const popularCall = mockCalls.find((c) => c.params?.sort === 'popular');
  expect(popularCall.params.exclude).toBe('1');
  expect(screen.getAllByText('Tasty')).toHaveLength(1);
});
