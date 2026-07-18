import { render, screen } from '@testing-library/react';
import ManageRestaurants from './ManageRestaurants';

jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
}));

jest.mock('../../hooks/APIHandler', () => () => ({
  callApi: jest.fn().mockResolvedValue({ data: { data: [] } }),
  loading: false,
}));

test('renders restaurants heading', async () => {
  render(<ManageRestaurants />);
  expect(await screen.findByRole('heading', { name: /Restaurants/i })).toBeInTheDocument();
});
