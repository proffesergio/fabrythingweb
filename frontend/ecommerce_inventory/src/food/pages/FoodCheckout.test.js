import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MemoryRouter } from 'react-router-dom';
import foodCartReducer, { addFoodItem } from '../redux/foodCartSlice';

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('react-toastify', () => ({ toast: { success: jest.fn(), error: jest.fn(), info: jest.fn() } }));

// Inline factory (no external ref) — the reliable jest.mock pattern here.
jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: async () => ({ data: { data: { order_code: 'FD-ABC123' } }, status: 201 }),
}));
jest.mock('../context/FoodLocationContext', () => ({
  useFoodLocation: () => ({ zoneId: '1', zones: [{ id: 1, name: 'Zone 1' }], coords: null, detectLocation: jest.fn() }),
}));

import FoodCheckout from './FoodCheckout';

function makeStore() {
  const store = configureStore({ reducer: { foodCart: foodCartReducer } });
  store.dispatch(addFoodItem({
    lineId: 'l1', restaurantId: 1, restaurantSlug: 'r1', restaurantName: 'R1',
    itemId: 10, name: 'Biriyani', unitPrice: 120, quantity: 1, selectedOptions: [],
  }));
  return store;
}

test('places a COD order and navigates to tracking', async () => {
  render(
    <Provider store={makeStore()}>
      <MemoryRouter><FoodCheckout /></MemoryRouter>
    </Provider>
  );
  fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'Karim' } });
  fireEvent.change(screen.getByLabelText(/phone/i), { target: { value: '017' } });
  fireEvent.change(screen.getByLabelText(/address/i), { target: { value: 'Village Rd' } });
  fireEvent.click(screen.getByRole('button', { name: /place order/i }));
  await waitFor(() => expect(mockNavigate).toHaveBeenCalled());
  expect(mockNavigate.mock.calls[0][0]).toBe('/food/order/FD-ABC123');
});
