import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

const mockCalls = [];

// 8 restaurants: NEAR_LIMIT is 6, so 6 land in "Nearest" and 2 in "Also available".
const makeRestaurant = (id) => ({
  id, slug: `r${id}`, display_name: `Place ${id}`, cover_image: '', cuisine_type: 'Bengali',
  avg_prep_minutes: 25, base_delivery_fee: '30.00', is_open_now: true, distance_km: id * 0.5,
});
const ALL = Array.from({ length: 8 }, (_, i) => makeRestaurant(i + 1));

let mockRows = ALL;

// FoodHome reads through useCachedApi (stale-while-revalidate over localStorage),
// which returns the unwrapped payload — for a paginated list that is
// { data: [...], totalPages, totalItems }.
jest.mock('../../hooks/useCachedApi', () => (url, opts) => {
  mockCalls.push({ url, params: opts?.params });
  return { data: { data: mockRows }, loading: false, revalidating: false, error: null, refetch: jest.fn() };
});

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

beforeEach(() => { mockCalls.length = 0; mockRows = ALL; });

const renderHome = () => render(<MemoryRouter><FoodHome /></MemoryRouter>);

test('renders both discovery rows', async () => {
  renderHome();
  await waitFor(() => expect(screen.getByText('Nearest to your area')).toBeInTheDocument());
  expect(screen.getByText('Also available')).toBeInTheDocument();
});

test('shows the nearest restaurant in the first row', async () => {
  renderHome();
  await waitFor(() => expect(screen.getByText('Place 1')).toBeInTheDocument());
});

test('every restaurant reaches the page, not just the nearest handful', async () => {
  // The whole point of the second row: nothing is stranded off the homepage.
  renderHome();
  await waitFor(() => expect(screen.getByText('Place 1')).toBeInTheDocument());
  ALL.forEach((r) => expect(screen.getByText(r.display_name)).toBeInTheDocument());
});

test('asks the API to sort by distance from the pin, in one request', async () => {
  renderHome();
  await waitFor(() => expect(mockCalls.length).toBeGreaterThan(0));
  expect(mockCalls[0].params).toMatchObject({ sort: 'distance', lat: 23.75, lng: 90.78 });
  // One endpoint, one query shape — the rows are a client-side split.
  expect(new Set(mockCalls.map((c) => c.url))).toEqual(new Set(['food/restaurants/']));
});

test('does not repeat a restaurant across the two rows', async () => {
  renderHome();
  await waitFor(() => expect(screen.getByText('Place 1')).toBeInTheDocument());
  ALL.forEach((r) => expect(screen.getAllByText(r.display_name)).toHaveLength(1));
});

test('the second row is hidden when everything fits in the first', async () => {
  mockRows = ALL.slice(0, 3);
  renderHome();
  await waitFor(() => expect(screen.getByText('Place 1')).toBeInTheDocument());
  expect(screen.queryByText('Also available')).not.toBeInTheDocument();
});
