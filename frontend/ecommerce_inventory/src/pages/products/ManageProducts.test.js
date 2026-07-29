import { render, screen, waitFor, fireEvent } from '@testing-library/react';

jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn() }));
jest.mock('react-toastify', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
// Child dialogs hit the API too; stub them out.
jest.mock('./ManageReview', () => () => null);
jest.mock('./ManageQuestions', () => () => null);

const mockCalls = [];
let mockQuickUpdateResult = null; // set per-test: { status, data }
let mockBulkResult = null; // set per-test: { status, data }
let mockProductsListResult = null; // override per-test for products/ GET (e.g. category count probe)

const categoryTree = [
  { id: 3, slug: 'shirts', name: 'Shirts', children: [
    { id: 5, slug: 'shirts-formal', name: 'Formal Shirts', children: [] },
  ] },
];

const baseProduct = {
  id: 1, name: 'Cotton Shirt', sku: 'FT-1', brand: 'Aarong', category_id: '#3 Shirts',
  image: ['https://x/img.jpg'], initial_selling_price: 900, discount_price: 700,
  shipping_fee: null, status: 'ACTIVE', total_stock: 12, variant_count: 1,
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
      // openBulkDialog's category-count probe asks for pageSize:1 -- keep it
      // distinct from the main list fetch (pageSize:12) so a test can select
      // a category and see a realistic "N products in <category>" count.
      if (opts.params?.pageSize === 1) {
        return { status: 200, data: { data: { data: [], totalItems: 7, totalPages: 7 } } };
      }
      if (mockProductsListResult) return mockProductsListResult;
      return { status: 200, data: { data: { data: [baseProduct], totalItems: 1, totalPages: 1 } } };
    }
    if (opts.url === `products/admin/${baseProduct.id}/quick-update/`) {
      return mockQuickUpdateResult;
    }
    if (opts.url === 'products/admin/shipping-fee/bulk/') {
      return mockBulkResult;
    }
    return { status: 200, data: { data: {} } };
  },
}));

import ManageProducts from './ManageProducts';
import { toast } from 'react-toastify';

beforeEach(() => {
  mockCalls.length = 0;
  mockQuickUpdateResult = null;
  mockBulkResult = null;
  mockProductsListResult = null;
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

  const toggle = screen.getByRole('checkbox', { name: /Toggle availability for Cotton Shirt/i });
  expect(toggle).toBeChecked();
  fireEvent.click(toggle);

  await waitFor(() => expect(toast.success).toHaveBeenCalled());
  const patchCall = mockCalls.find((c) => c.url === 'products/admin/1/quick-update/');
  expect(patchCall.body).toEqual({ status: 'INACTIVE' });
  expect(screen.getByRole('checkbox', { name: /Toggle availability for Cotton Shirt/i })).not.toBeChecked();
});

test('a failed availability toggle leaves the switch in its previous state', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());

  mockQuickUpdateResult = { status: 403, data: { errors: ['Forbidden'], message: 'Forbidden' } };

  const toggle = screen.getByRole('checkbox', { name: /Toggle availability for Cotton Shirt/i });
  fireEvent.click(toggle);

  await waitFor(() => expect(toast.error).toHaveBeenCalled());
  expect(screen.getByRole('checkbox', { name: /Toggle availability for Cotton Shirt/i })).toBeChecked();
});

test('shipping fee column is inline-editable like price and discount', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());

  // No fee set yet -- the field is blank with a "store rate" placeholder,
  // not "0" (0 is a distinct, real "ships free" value).
  const shippingInput = screen.getByPlaceholderText('store rate');
  expect(shippingInput).toHaveValue(null);

  mockQuickUpdateResult = {
    status: 200,
    data: {
      data: {
        id: 1, initial_selling_price: 900, discount_price: 700, status: 'ACTIVE', shipping_fee: 250,
        variants: [{ id: 10, sku: 'FT-1-DEF', size: '', color: '', stock_quantity: 12, price: 900, discount_price: 700 }],
      },
    },
  };

  fireEvent.change(shippingInput, { target: { value: '250' } });
  fireEvent.click(await screen.findByLabelText(/Save Cotton Shirt/i));

  await waitFor(() => expect(toast.success).toHaveBeenCalled());
  const patchCall = mockCalls.find((c) => c.url === 'products/admin/1/quick-update/');
  expect(patchCall.rawError).toBe(true);
  expect(patchCall.body).toEqual({ shipping_fee: 250 });
});

test('a rejected shipping fee edit surfaces the field error', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());

  mockQuickUpdateResult = {
    status: 400,
    data: {
      errors: ['Cannot be negative.'],
      field_errors: { shipping_fee: ['Cannot be negative.'] },
      message: 'Validation error',
    },
  };

  fireEvent.change(screen.getByPlaceholderText('store rate'), { target: { value: '-10' } });
  fireEvent.click(await screen.findByLabelText(/Save Cotton Shirt/i));

  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Validation error'));
  expect(await screen.findByText('Cannot be negative.')).toBeInTheDocument();
});

test('bulk shipping fee applies to checked rows via product_ids, with a confirmation count', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());

  fireEvent.click(screen.getByLabelText('Select Cotton Shirt'));
  fireEvent.click(screen.getByRole('button', { name: /Bulk shipping fee/i }));

  const alert = await screen.findByRole('alert');
  expect(alert).toHaveTextContent('1 selected product');

  mockBulkResult = { status: 200, data: { data: { updated: 1, shipping_fee: 300 } } };
  fireEvent.change(screen.getByLabelText('Shipping fee'), { target: { value: '300' } });
  fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

  await waitFor(() => expect(toast.success).toHaveBeenCalled());
  const bulkCall = mockCalls.find((c) => c.url === 'products/admin/shipping-fee/bulk/');
  expect(bulkCall.rawError).toBe(true);
  expect(bulkCall.body).toEqual({ shipping_fee: 300, product_ids: [1] });
});

test('bulk shipping fee falls back to the category filter with a fetched count when nothing is checked', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());

  fireEvent.mouseDown(screen.getByLabelText('Category'));
  fireEvent.click(await screen.findByRole('option', { name: 'Shirts' }));
  await waitFor(() => {
    const productCalls = mockCalls.filter((c) => c.url === 'products/');
    expect(productCalls[productCalls.length - 1].params.category).toBe(3);
  });

  fireEvent.click(screen.getByRole('button', { name: /Bulk shipping fee/i }));

  const alert = await screen.findByRole('alert');
  await waitFor(() => expect(alert).toHaveTextContent('7 products in Shirts'));

  mockBulkResult = { status: 200, data: { data: { updated: 7, shipping_fee: 120 } } };
  fireEvent.change(screen.getByLabelText('Shipping fee'), { target: { value: '120' } });
  fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

  await waitFor(() => expect(toast.success).toHaveBeenCalled());
  const bulkCall = mockCalls.find((c) => c.url === 'products/admin/shipping-fee/bulk/');
  expect(bulkCall.body).toEqual({ shipping_fee: 120, category: 3 });
});

test('the bulk shipping fee button is disabled with no selection and no category filter', async () => {
  render(<ManageProducts />);
  await waitFor(() => expect(screen.getByText('Cotton Shirt')).toBeInTheDocument());
  expect(screen.getByRole('button', { name: /Bulk shipping fee/i })).toBeDisabled();
});
