import { render, screen, waitFor, fireEvent } from '@testing-library/react';

jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn() }));
jest.mock('react-toastify', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
// Child dialogs hit the API too; stub them out.
jest.mock('./ManageReview', () => () => null);
jest.mock('./ManageQuestions', () => () => null);

const mockCalls = [];
let mockQuickUpdateResult = null; // set per-test: { status, data }

const categoryTree = [
  { id: 3, slug: 'shirts', name: 'Shirts', children: [
    { id: 5, slug: 'shirts-formal', name: 'Formal Shirts', children: [] },
  ] },
];

const baseProduct = {
  id: 1, name: 'Cotton Shirt', sku: 'FT-1', brand: 'Aarong', category_id: '#3 Shirts',
  image: ['https://x/img.jpg'], initial_selling_price: 900, discount_price: 700,
  status: 'ACTIVE', total_stock: 12, variant_count: 1,
};

jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: async (opts) => {
    mockCalls.push(opts);
    if (opts.url === 'products/categories/') {
      return { status: 200, data: { data: { data: categoryTree } } };
    }
    if (opts.url === 'products/') {
      return { status: 200, data: { data: { data: [baseProduct], totalItems: 1, totalPages: 1 } } };
    }
    if (opts.url === `products/admin/${baseProduct.id}/quick-update/`) {
      return mockQuickUpdateResult;
    }
    return { status: 200, data: { data: {} } };
  },
}));

import ManageProducts from './ManageProducts';
import { toast } from 'react-toastify';

beforeEach(() => {
  mockCalls.length = 0;
  mockQuickUpdateResult = null;
  toast.success.mockClear();
  toast.error.mockClear();
});

test('renders products with inline-editable price, discount and stock', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());
  expect(screen.getByText('#3 Shirts')).toBeInTheDocument();
  expect(screen.getByDisplayValue('900')).toBeInTheDocument();
  expect(screen.getByDisplayValue('700')).toBeInTheDocument();
  expect(screen.getByDisplayValue('12')).toBeInTheDocument();
  // No unsaved change yet -- the save icon must not be visible.
  expect(screen.queryByLabelText(/Save Cotton Shirt/i)).not.toBeInTheDocument();
});

test('category filter refetches the list scoped to the chosen category', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());

  fireEvent.mouseDown(screen.getByLabelText('Category'));
  fireEvent.click(await screen.findByRole('option', { name: 'Shirts' }));

  await waitFor(() => {
    const productCalls = mockCalls.filter((c) => c.url === 'products/');
    expect(productCalls[productCalls.length - 1].params.category).toBe(3);
  });
});

test('nests child categories under their parent in the filter dropdown', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());
  fireEvent.mouseDown(screen.getByLabelText('Category'));
  expect(await screen.findByRole('option', { name: /Formal Shirts/ })).toBeInTheDocument();
});

test('editing the price and saving updates the row and confirms success', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());

  mockQuickUpdateResult = {
    status: 200,
    data: {
      data: {
        id: 1, initial_selling_price: 950, discount_price: 700, status: 'ACTIVE',
        variants: [{ id: 10, sku: 'FT-1-DEF', size: '', color: '', stock_quantity: 12, price: 950, discount_price: 700 }],
      },
    },
  };

  fireEvent.change(screen.getByDisplayValue('900'), { target: { value: '950' } });
  fireEvent.click(await screen.findByLabelText(/Save Cotton Shirt/i));

  await waitFor(() => expect(toast.success).toHaveBeenCalled());
  expect(screen.getByDisplayValue('950')).toBeInTheDocument();
  // Once the server confirms the save, the row is clean again.
  expect(screen.queryByLabelText(/Save Cotton Shirt/i)).not.toBeInTheDocument();

  const patchCall = mockCalls.find((c) => c.url === 'products/admin/1/quick-update/');
  expect(patchCall.rawError).toBe(true);
  expect(patchCall.body).toEqual({ initial_selling_price: 950 });
});

test('a rejected price edit surfaces the field error instead of a silent no-op', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());

  mockQuickUpdateResult = {
    status: 400,
    data: {
      errors: ['Must be greater than 0.'],
      field_errors: { initial_selling_price: ['Must be greater than 0.'] },
      message: 'Validation error',
    },
  };

  fireEvent.change(screen.getByDisplayValue('900'), { target: { value: '0' } });
  fireEvent.click(await screen.findByLabelText(/Save Cotton Shirt/i));

  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Validation error'));
  expect(await screen.findByText('Must be greater than 0.')).toBeInTheDocument();
  // The row must still show the change as unsaved -- the save affordance
  // stays put rather than pretending the edit went through.
  expect(screen.getByLabelText(/Save Cotton Shirt/i)).toBeInTheDocument();
});

test('toggling availability calls quick-update and flips the switch on success', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());

  mockQuickUpdateResult = {
    status: 200,
    data: { data: { id: 1, initial_selling_price: 900, discount_price: 700, status: 'INACTIVE', variants: [] } },
  };

  const toggle = screen.getByRole('checkbox');
  expect(toggle).toBeChecked();
  fireEvent.click(toggle);

  await waitFor(() => expect(toast.success).toHaveBeenCalled());
  const patchCall = mockCalls.find((c) => c.url === 'products/admin/1/quick-update/');
  expect(patchCall.body).toEqual({ status: 'INACTIVE' });
  expect(screen.getByRole('checkbox')).not.toBeChecked();
});

test('a failed availability toggle leaves the switch in its previous state', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());

  mockQuickUpdateResult = { status: 403, data: { errors: ['Forbidden'], message: 'Forbidden' } };

  const toggle = screen.getByRole('checkbox');
  fireEvent.click(toggle);

  await waitFor(() => expect(toast.error).toHaveBeenCalled());
  expect(screen.getByRole('checkbox')).toBeChecked();
});
