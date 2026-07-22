import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import store from '../../redux/store/store';

// `mock`-prefixed so jest's out-of-scope guard allows it inside the factory.
const mockToastInfo = jest.fn();
jest.mock('react-toastify', () => ({ toast: { info: (...a) => mockToastInfo(...a) } }));

let mockData;
jest.mock('../../hooks/useCachedApi', () => () => ({
  data: mockData, loading: false, revalidating: false, error: null, refetch: jest.fn(),
}));

let mockLang = 'en';
jest.mock('../context/FoodLocationContext', () => ({
  useFoodLocation: () => ({ lang: mockLang }),
}));

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: () => ({ slug: 'r1' }),
}));

import RestaurantDetail from './RestaurantDetail';

const menu = (over = {}) => ({
  id: 1, slug: 'r1', display_name: 'Dhaka Fast Food', cuisine_type: 'Fast Food',
  avg_prep_minutes: 25, base_delivery_fee: '30.00', min_order_amount: '0.00',
  is_open: true, is_open_now: true, next_open: null, opening_hours: [],
  categories: [{
    id: 9, display_name: 'Burgers', items: [
      { id: 101, display_name: 'Beef Burger', effective_price: '250', price: '250',
        option_groups: [], tags: [] },
    ],
  }],
  ...over,
});

const renderMenu = () => render(
  <Provider store={store}><MemoryRouter><RestaurantDetail /></MemoryRouter></Provider>
);

beforeEach(() => {
  mockToastInfo.mockClear();
  mockLang = 'en';
  mockData = menu();
  store.dispatch({ type: 'foodCart/clearFoodCart' });
});

describe('an open restaurant', () => {
  test('adds a dish to the bag', () => {
    renderMenu();
    fireEvent.click(screen.getByRole('button', { name: /add/i }));
    expect(store.getState().foodCart.items).toHaveLength(1);
  });
});

describe('a closed restaurant', () => {
  beforeEach(() => {
    mockData = menu({
      is_open_now: false,
      next_open: { weekday: 2, open_time: '10:30', days_ahead: 1 },
      opening_hours: [{ weekday: 2, open_time: '10:30', close_time: '22:00', is_closed: false }],
    });
  });

  test('offers no Add button — the dish cannot reach the bag', () => {
    renderMenu();
    expect(screen.queryByRole('button', { name: /^add$/i })).not.toBeInTheDocument();
    expect(screen.getAllByText('Closed Now').length).toBeGreaterThan(0);
  });

  test('tapping a dish explains when they reopen instead of doing nothing', () => {
    // A card that silently refuses to respond reads as a broken site; the toast
    // is the whole point of leaving the card tappable.
    renderMenu();
    fireEvent.click(screen.getByText('Beef Burger'));
    expect(store.getState().foodCart.items).toHaveLength(0);
    expect(mockToastInfo).toHaveBeenCalledWith(
      expect.stringContaining('opens tomorrow at 10:30 AM'), expect.anything());
    expect(mockToastInfo).toHaveBeenCalledWith(
      expect.stringContaining('Dhaka Fast Food'), expect.anything());
  });

  test('the banner names the reopening time and the weekly schedule', () => {
    renderMenu();
    expect(screen.getByText(/Opens tomorrow at 10:30 AM/)).toBeInTheDocument();
    expect(screen.getByText(/Wednesday · 10:30 AM – 10:00 PM/)).toBeInTheDocument();
  });

  test('speaks Bangla when the customer does', () => {
    mockLang = 'bn';
    renderMenu();
    expect(screen.getAllByText('এখন বন্ধ').length).toBeGreaterThan(0);
    fireEvent.click(screen.getByText('Beef Burger'));
    expect(mockToastInfo).toHaveBeenCalledWith(
      expect.stringContaining('আগামীকাল সকাল ১০:৩০'), expect.anything());
  });

  test('a restaurant with no hours at all still says something honest', () => {
    mockData = menu({ is_open_now: false, next_open: null, opening_hours: [] });
    renderMenu();
    expect(screen.getByText(/Closed right now/)).toBeInTheDocument();
  });
});
