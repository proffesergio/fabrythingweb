/* Size chart on the product detail page -- shown only for fashion items that
 * actually have one (catalog.Products.size_chart), never an empty table, with
 * INCH/CM tabs where CM is computed from the stored inch values (x 2.54)
 * rather than sourced separately. Matches the "Size chart - In inches
 * (Expected Deviation < 3%)" reference the owner asked to match.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
  id: 1, name: 'Womens Premium Tops - Estrella', slug: 'estrella',
  image: ['https://x/img.jpg'],
  initial_selling_price: 1190, discount_price: null, discount_percentage: 0,
  variants: [
    { id: 10, size: 'M', color: '', price: '1190.00', discount_price: null, effective_price: '1190.00', stock_quantity: 5, in_stock: true },
    { id: 11, size: 'L', color: '', price: '1190.00', discount_price: null, effective_price: '1190.00', stock_quantity: 5, in_stock: true },
  ],
  specifications: {}, highlights: [],
};

const renderDetail = () => {
  const store = configureStore({ reducer: { cart: cartReducer } });
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/product/estrella']}>
        <Routes>
          <Route path="/product/:slug" element={<ProductDetail />} />
        </Routes>
      </MemoryRouter>
    </Provider>
  );
};

test('hides the Size Chart button entirely when size_chart is empty', async () => {
  mockProduct = { ...baseProduct, available_sizes: ['M', 'L'], size_chart: {} };
  renderDetail();
  await waitFor(() => expect(screen.getByText('Select Size')).toBeInTheDocument());
  expect(screen.queryByText('Size Chart')).not.toBeInTheDocument();
});

test('shows the chart with the deviation heading and INCH/CM tabs when data exists', async () => {
  mockProduct = {
    ...baseProduct,
    available_sizes: ['M', 'L'],
    size_chart: {
      M: { chest: 36, length: 30, sleeve: 21 },
      L: { chest: 38, length: 31, sleeve: 21 },
    },
  };
  renderDetail();
  userEvent.click(await screen.findByText('Size Chart'));

  expect(await screen.findByText('Size chart')).toBeInTheDocument();
  expect(screen.getByText(/Expected Deviation < 3%/)).toBeInTheDocument();
  expect(screen.getByText('INCH')).toBeInTheDocument();
  expect(screen.getByText('CM')).toBeInTheDocument();
  // Inch values shown by default, with the inch mark.
  expect(screen.getByText('36"')).toBeInTheDocument();
  expect(screen.getByText('chest')).toBeInTheDocument();
});

test('CM tab computes centimeters from the stored inch values (x 2.54)', async () => {
  mockProduct = {
    ...baseProduct,
    available_sizes: ['M'],
    size_chart: { M: { chest: 36 } },
  };
  renderDetail();
  userEvent.click(await screen.findByText('Size Chart'));
  userEvent.click(await screen.findByText('CM'));
  // 36 * 2.54 = 91.44, rounded to one decimal -> 91.4
  expect(await screen.findByText('91.4 cm')).toBeInTheDocument();
});
