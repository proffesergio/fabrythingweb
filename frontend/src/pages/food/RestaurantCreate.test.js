import { render, screen, fireEvent, waitFor } from '@testing-library/react';

jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn() }));

// Records the POST body on a global so the test can assert the owner payload.
jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: async ({ url, method, body }) => {
    if (method === 'POST') {
      global.__lastPost = { url, body };
      return { status: 201, data: { data: { id: 5, name: body.name } } };
    }
    return { status: 200, data: { data: [] } };
  },
}));

import ManageRestaurants from './ManageRestaurants';

test('create form posts a restaurant with an owner login payload', async () => {
  render(<ManageRestaurants />);
  fireEvent.click(screen.getByRole('button', { name: /add restaurant/i }));
  fireEvent.change(screen.getByLabelText(/restaurant name/i), { target: { value: 'Star Kitchen' } });
  fireEvent.change(screen.getByLabelText(/owner username/i), { target: { value: 'starowner' } });
  fireEvent.change(screen.getByLabelText(/owner email/i), { target: { value: 'star@x.com' } });
  fireEvent.change(screen.getByLabelText(/owner password/i), { target: { value: 'pass12345' } });
  fireEvent.click(screen.getByRole('button', { name: /^create$/i }));
  await waitFor(() => expect(global.__lastPost).toBeTruthy());
  expect(global.__lastPost.url).toBe('food/admin/restaurants/');
  expect(global.__lastPost.body.name).toBe('Star Kitchen');
  expect(global.__lastPost.body.owner.username).toBe('starowner');
});
