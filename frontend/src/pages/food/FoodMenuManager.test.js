import { render, screen, waitFor, fireEvent } from '@testing-library/react';

// Controllable mock: tests reprogram mockCallApi; defaultApi is the baseline.
const mockCallApi = jest.fn();
jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: (...args) => mockCallApi(...args),
}));
jest.mock('react-toastify', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const defaultApi = async ({ url, method, body }) => {
  if (method === 'POST' && url.includes('categories')) {
    global.__catPost = body;
    return { status: 201, data: { data: { id: 7, name: body.name, restaurant: body.restaurant } } };
  }
  if (url.startsWith('food/admin/restaurants')) {
    return { status: 200, data: { data: [{ id: 3, name: 'Star Kitchen' }] } };
  }
  if (url.startsWith('food/admin/categories')) {
    return { status: 200, data: { data: [{ id: 1, name: 'Main', restaurant: 3 }] } };
  }
  if (url.startsWith('food/admin/items')) {
    return { status: 200, data: { data: [{ id: 10, name: 'Biriyani', price: '120.00', category_id: 1,
      image: 'https://cdn.example.com/b.jpg', tags: [], available_days: [] }] } };
  }
  return { status: 200, data: { data: [] } };
};

beforeEach(() => mockCallApi.mockImplementation(defaultApi));
afterEach(() => jest.clearAllMocks());

import FoodMenuManager from './FoodMenuManager';

test('selecting a restaurant lists its items and adding a category posts restaurant', async () => {
  render(<FoodMenuManager />);
  // restaurant loads and auto-selects the first one -> its items show
  await waitFor(() => expect(screen.getByText(/Biriyani/)).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText(/new category/i), { target: { value: 'Drinks' } });
  fireEvent.click(screen.getByRole('button', { name: /add category/i }));
  await waitFor(() => expect(global.__catPost).toBeTruthy());
  expect(global.__catPost.name).toBe('Drinks');
  expect(global.__catPost.restaurant).toBe(3);
});


test('renders a thumbnail for an item that has an image', async () => {
  render(<FoodMenuManager />);
  const thumb = await screen.findByAltText('Biriyani');
  expect(thumb).toHaveAttribute('src', 'https://cdn.example.com/b.jpg');
});

test('shows the failing field inline when the backend rejects the item', async () => {
  mockCallApi.mockImplementation(async (args) => {
    if (args.url === 'food/admin/items/' && args.method === 'POST') {
      return { status: 400, data: { message: 'Validation error',
        field_errors: { image: ['Enter a valid URL.'] } } };
    }
    return defaultApi(args);
  });

  render(<FoodMenuManager />);
  fireEvent.click(await screen.findByRole('button', { name: /add item/i }));
  fireEvent.change(screen.getByLabelText(/Name \(English\)/i), { target: { value: 'Tehari' } });
  fireEvent.change(screen.getByLabelText(/^Price/i), { target: { value: '180' } });
  fireEvent.click(screen.getByRole('button', { name: /^save$/i }));

  expect(await screen.findByText(/Enter a valid URL/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /^save$/i })).toBeInTheDocument();
});
