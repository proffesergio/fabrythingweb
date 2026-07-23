import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

const mockCallApi = jest.fn();
jest.mock('../../hooks/APIHandler', () => () => ({ callApi: mockCallApi, loading: false, error: null }));

let mockLang = 'en';
jest.mock('../context/FoodLocationContext', () => ({
  useFoodLocation: () => ({ lang: mockLang, zones: [{ id: 1, name: 'Bancharampur' }] }),
}));

jest.mock('react-toastify', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

import BecomePartner from './BecomePartner';

const renderPage = () => render(<MemoryRouter><BecomePartner /></MemoryRouter>);

beforeEach(() => { mockCallApi.mockReset(); mockLang = 'en'; localStorage.clear(); });

test('a shop owner can apply without an account', async () => {
  mockCallApi.mockResolvedValue({
    status: 201,
    data: { data: { access: 'tok', restaurant: { status: 'PENDING' } } },
  });
  renderPage();
  fireEvent.click(screen.getByRole('button', { name: /submit application/i }));
  await waitFor(() => expect(screen.getByText(/Application received/)).toBeInTheDocument());
  // Signed in straight away, so the menu can be built while approval is pending.
  expect(localStorage.getItem('token')).toBe('tok');
});

test('a server field error lands under the field it belongs to', async () => {
  // The whole reason the endpoint returns field_errors: a message under the
  // wrong input is worse than no message.
  mockCallApi.mockResolvedValue({
    status: 400,
    data: { field_errors: { email: ['An account already uses this email.'] } },
  });
  renderPage();
  fireEvent.click(screen.getByRole('button', { name: /submit application/i }));
  await waitFor(() =>
    expect(screen.getByText('An account already uses this email.')).toBeInTheDocument());
  expect(screen.queryByText(/Application received/)).not.toBeInTheDocument();
});

test('an error with no field attribution is still shown, never swallowed', async () => {
  mockCallApi.mockResolvedValue({ status: 500, data: { message: 'Server exploded' } });
  renderPage();
  fireEvent.click(screen.getByRole('button', { name: /submit application/i }));
  await waitFor(() => expect(screen.getByText('Server exploded')).toBeInTheDocument());
});

test('the page speaks Bangla for the owners it is aimed at', () => {
  mockLang = 'bn';
  renderPage();
  expect(screen.getByText('পার্টনার হোন')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'আবেদন জমা দিন' })).toBeInTheDocument();
});
