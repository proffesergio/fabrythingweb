import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MemoryRouter } from 'react-router-dom';
import cartReducer from '../../redux/reducer/cartSlice';
import StorefrontLayout from './StorefrontLayout';

jest.mock('../../hooks/APIHandler', () => () => ({ callApi: jest.fn().mockResolvedValue({ data: {} }), loading: false }));

// Minimal store — avoids importing the full app store (see FoodLayout.test.js
// for the same rationale: keeps axios ESM / thunk wiring out of this render).
const store = configureStore({ reducer: { cart: cartReducer } });

const renderLayout = () =>
  render(
    <Provider store={store}>
      <MemoryRouter>
        <StorefrontLayout />
      </MemoryRouter>
    </Provider>
  );

test('renders Facebook link to the fabrything page', async () => {
  renderLayout();
  const fb = await screen.findByRole('link', { name: /facebook/i });
  expect(fb).toHaveAttribute('href', 'https://www.facebook.com/fabrything');
  expect(fb).toHaveAttribute('target', '_blank');
});

test('renders Messenger link to the fabrything messenger', async () => {
  renderLayout();
  const messenger = await screen.findByRole('link', { name: /messenger/i });
  expect(messenger).toHaveAttribute('href', 'https://m.me/fabrything');
  expect(messenger).toHaveAttribute('target', '_blank');
});
