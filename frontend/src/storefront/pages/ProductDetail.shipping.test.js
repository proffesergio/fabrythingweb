/* Detail delivery declarations must match regional checkout rates and explicit free promos. */
import { render, screen, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import cartReducer from '../../redux/reducer/cartSlice';
import ProductDetail from './ProductDetail';

let mockProduct;

jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  callApi: async () => ({ data: { data: mockProduct } }),
}));

const baseProduct = {
  id: 1, name: 'Cotton Shirt', slug: 'cotton-shirt', image: ['https://x/img.jpg'],
  initial_selling_price: 900, discount_price: null, discount_percentage: 0,
  variants: [{ id: 10, size: '', color: '', price: '900.00', discount_price: null, effective_price: '900.00', stock_quantity: 5, in_stock: true }],
  available_sizes: [], size_chart: {}, specifications: {}, highlights: [],
};

const renderDetail = () => {
  const store = configureStore({ reducer: { cart: cartReducer } });
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/product/cotton-shirt']}>
        <Routes>
          <Route path="/product/:slug" element={<ProductDetail />} />
        </Routes>
      </MemoryRouter>
    </Provider>
  );
};

test('a zero product fee still declares regional delivery without a free promo', async () => {
  mockProduct = { ...baseProduct, effective_shipping_fee: 0 };
  renderDetail();
  expect(await screen.findByText('Inside Dhaka')).toBeInTheDocument();
  expect(screen.queryByText('Free delivery')).not.toBeInTheDocument();
});

test('declares regional rates instead of a legacy flat fee', async () => {
  mockProduct = { ...baseProduct, effective_shipping_fee: 250 };
  renderDetail();
  expect(await screen.findByText('Inside Dhaka')).toBeInTheDocument();
  expect(screen.getByText('BDT 70')).toBeInTheDocument();
  expect(screen.getByText('Outside Dhaka')).toBeInTheDocument();
  expect(screen.getByText('BDT 120')).toBeInTheDocument();
  expect(screen.getByText(/Product-specific charges/)).toBeInTheDocument();
});

test('does not advertise the old flat 60 taka delivery rate', async () => {
  mockProduct = { ...baseProduct, effective_shipping_fee: 60 };
  renderDetail();
  expect(await screen.findByText('Inside Dhaka')).toBeInTheDocument();
  expect(screen.queryByText('Delivery: ৳60')).not.toBeInTheDocument();
});

// free_shipping is the explicit per-product promo flag (distinct from
// shipping_fee == 0) -- see docs/SHIPPING_FEES.md.
test('shows "Free delivery" when free_shipping is true, even with a nonzero effective_shipping_fee', async () => {
  mockProduct = { ...baseProduct, free_shipping: true, effective_shipping_fee: 60 };
  renderDetail();
  expect(await screen.findByText('Free delivery')).toBeInTheDocument();
  expect(screen.queryByText(/^Delivery: /)).not.toBeInTheDocument();
});
