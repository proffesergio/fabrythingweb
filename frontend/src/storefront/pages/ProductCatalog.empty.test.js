import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// The shop page rendered "No products found" whenever the request failed,
// because callApi resolves to null on any error and the handler only acted on
// success. On Render's free tier a cold start hangs for ~50s, so a customer
// opening the shop first thing in the morning was told the catalogue was
// EMPTY. 213 products exist; nothing about the query was wrong.
const mockCallApi = jest.fn();
jest.mock('../../hooks/APIHandler', () => () => ({ callApi: mockCallApi, loading: false, error: '' }));
// A STABLE reference. Returning a fresh array each call would re-run any
// effect keyed on it — which is exactly the loop the component was refactored
// to avoid, and it hangs the test runner rather than failing it.
const mockStableCategories = [];
jest.mock('../../hooks/useCachedApi', () => ({
  __esModule: true,
  default: () => ({ data: mockStableCategories, loading: false, error: null }),
}));
jest.mock('../components/ProductCard', () => ({ __esModule: true, default: ({ product }) => <div>{product.name}</div> }));

import ProductCatalog from './ProductCatalog';

const renderShop = () => render(<MemoryRouter><ProductCatalog /></MemoryRouter>);

const productPage = (items) => ({
  status: 200,
  data: { data: { data: items, totalPages: 1, currentPage: 1, totalItems: items.length } },
});

beforeEach(() => { mockCallApi.mockReset(); });

test('shows products when the API returns them', async () => {
  mockCallApi.mockResolvedValue(productPage([{ id: 1, name: 'Digital Thermometer', slug: 'dt' }]));
  renderShop();
  await waitFor(() => expect(screen.getByText('Digital Thermometer')).toBeInTheDocument());
});

test('a failed request is reported as a failure, never as an empty catalogue', async () => {
  mockCallApi.mockResolvedValue(null);   // what callApi does on any non-2xx / network error
  renderShop();

  await waitFor(() => expect(screen.getByText(/could not load/i)).toBeInTheDocument());
  // The lie this test exists to prevent.
  expect(screen.queryByText(/no products found/i)).not.toBeInTheDocument();
});

test('a genuinely empty result still says so', async () => {
  mockCallApi.mockResolvedValue(productPage([]));
  renderShop();
  await waitFor(() => expect(screen.getByText(/no products found/i)).toBeInTheDocument());
  expect(screen.queryByText(/could not load/i)).not.toBeInTheDocument();
});

test('a failure offers a retry that re-requests', async () => {
  mockCallApi.mockResolvedValue(null);
  renderShop();
  const retry = await screen.findByRole('button', { name: /try again/i });
  const before = mockCallApi.mock.calls.length;
  retry.click();
  await waitFor(() => expect(mockCallApi.mock.calls.length).toBeGreaterThan(before));
});
