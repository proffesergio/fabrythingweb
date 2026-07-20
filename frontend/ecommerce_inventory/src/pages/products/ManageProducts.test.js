import { render, screen, waitFor } from '@testing-library/react';

jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn() }));
jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: async () => ({
    status: 200,
    data: { data: { data: [
      { id: 1, name: 'Cotton Shirt', sku: 'FT-1', brand: 'Aarong', category_id: '#3 Shirts',
        image: ['https://x/img.jpg'], initial_selling_price: 900, discount_price: 700, status: 'ACTIVE' },
    ], totalItems: 1, totalPages: 1 } },
  }),
}));
// Child dialogs hit the API too; stub them out.
jest.mock('./ManageReview', () => () => null);
jest.mock('./ManageQuestions', () => () => null);

import ManageProducts from './ManageProducts';

test('renders products in a curated table', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());
  expect(screen.getByText('#3 Shirts')).toBeInTheDocument();
  expect(screen.getByText('৳700')).toBeInTheDocument();
});
