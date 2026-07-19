import { render, screen, waitFor, fireEvent } from '@testing-library/react';

// Inline factory; records category POST and returns a restaurant + its menu.
jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: async ({ url, method, body }) => {
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
      return { status: 200, data: { data: [{ id: 10, name: 'Biriyani', price: '120.00', category_id: 1 }] } };
    }
    return { status: 200, data: { data: [] } };
  },
}));

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
