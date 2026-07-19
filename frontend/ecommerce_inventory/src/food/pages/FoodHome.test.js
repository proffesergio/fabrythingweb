import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

const RESTAURANT = {
  id: 1, slug: 'r1', display_name: 'Tasty', cover_image: '', cuisine_type: 'Bengali',
  avg_prep_minutes: 25, base_delivery_fee: '30.00', is_open: true,
};

jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: async ({ url }) =>
    String(url).startsWith('food/restaurants')
      ? { data: { data: { data: [RESTAURANT] } } }
      : { data: { data: [] } },
}));
jest.mock('../context/FoodLocationContext', () => ({
  useFoodLocation: () => ({ zoneId: '1', zones: [{ id: 1, name: 'Zone 1' }], lang: 'en', detectLocation: jest.fn() }),
}));

import FoodHome from './FoodHome';

test('renders restaurant cards for the selected zone', async () => {
  render(<MemoryRouter><FoodHome /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText('Tasty')).toBeInTheDocument());
});
