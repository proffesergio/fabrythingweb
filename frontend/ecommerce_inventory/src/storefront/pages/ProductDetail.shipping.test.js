/* Shipping fee is shown more prominently on the product detail page than
 * the card's quiet caption -- a labeled delivery box near the price, always
 * present (falls back to the store's flat rate), per docs/SHIPPING_FEES.md.
 */
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

test('shows a prominent "Free delivery" box when effective_shipping_fee is 0', async () => {
  mockProduct = { ...baseProduct, effective_shipping_fee: 0 };
  renderDetail();
  expect(await screen.findByText('Free delivery')).toBeInTheDocument();
});

test('shows the resolved delivery fee (own override or store flat rate)', async () => {
  mockProduct = { ...baseProduct, effective_shipping_fee: 250 };
  renderDetail();
  expect(await screen.findByText('Delivery: ৳250')).toBeInTheDocument();
});

test('falls back to showing the store rate rather than nothing when unset', async () => {
  mockProduct = { ...baseProduct, effective_shipping_fee: 60 };
  renderDetail();
  expect(await screen.findByText('Delivery: ৳60')).toBeInTheDocument();
});
