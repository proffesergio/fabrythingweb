import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import cartReducer from '../../redux/reducer/cartSlice';
import ProductDetail from './ProductDetail';

let mockProducts;
beforeAll(() => {
  window.IntersectionObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});
jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  callApi: async ({ url }) => ({ data: { data: mockProducts[url.split('/')[2]] } }),
}));
jest.mock('../components/ProductCard', () => ({ product }) => {
  const { Link } = require('react-router-dom');
  return <Link to={`/product/${product.slug}`}>{product.name}</Link>;
});
const product = (id) => ({
  id, name: `Product ${id}`, slug: `product-${id}`, image: [],
  initial_selling_price: 100, review_count: 0,
  variants: [{ id, size: '', effective_price: '100', stock_quantity: 20, in_stock: true }],
});
function renderDetail() {
  return render(<Provider store={configureStore({ reducer: { cart: cartReducer } })}>
    <MemoryRouter initialEntries={['/product/product-1']}>
      <Routes><Route path="/product/:slug" element={<ProductDetail />} /></Routes>
    </MemoryRouter>
  </Provider>);
}
test('offers eight suggestions, excluding the current product', async () => {
  mockProducts = { 'product-1': { ...product(1), related_products: Array.from({ length: 11 }, (_, i) => product(i + 1)) } };
  renderDetail();
  await screen.findByText('You May Also Like');
  const suggestions = screen.getAllByRole('link', { name: /^Product / });
  expect(suggestions).toHaveLength(8);
  expect(suggestions[0]).toHaveAttribute('href', '/product/product-2');
  expect(screen.queryByRole('link', { name: 'Product 1' })).not.toBeInTheDocument();
});
test('following a suggestion resets quantity before adding the next product to the cart', async () => {
  mockProducts = {
    'product-1': { ...product(1), related_products: [product(2)] },
    'product-2': { ...product(2), related_products: [] },
  };
  renderDetail();
  await screen.findByRole('button', { name: 'Add to Cart - ৳100' });
  userEvent.click(screen.getByTestId('AddIcon').closest('button'));
  expect(await screen.findByRole('button', { name: 'Add to Cart - ৳200' })).toBeInTheDocument();
  userEvent.click(screen.getByRole('link', { name: 'Product 2' }));
  await waitFor(() => expect(screen.getByRole('heading', { name: 'Product 2' })).toBeInTheDocument());
  expect(screen.getByRole('button', { name: 'Add to Cart - ৳100' })).toBeInTheDocument();
  expect(screen.queryByText('You May Also Like')).not.toBeInTheDocument();
});
